"""Shared, locked per-hosted-run USD reserve. Unknown requests keep their reserve."""
from contextlib import contextmanager
from decimal import Decimal
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from .responses import BudgetError

class RunBudget:
    def __init__(self, config, journal):
        self.cap=Decimal(str(config['max_run_usd']))
        ident=config['run_budget_id']
        if self.cap<=0 or not re.fullmatch(r'[a-zA-Z0-9_-]{12,80}',ident):raise BudgetError('Invalid shared budget configuration')
        self.root=Path(config.get('run_budget_root','/tmp/paiec-r1-run-budgets'))/ident
        self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.root.is_symlink() or self.root.stat().st_uid!=os.getuid() or self.root.stat().st_mode&0o077:
            raise BudgetError('Shared budget directory is not private')
        self.journal=journal

    @contextmanager
    def locked(self):
        fd=os.open(self.root/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            path=self.root/'state.json'
            if path.is_symlink():raise BudgetError('Invalid shared budget state')
            state=json.loads(path.read_text()) if path.exists() else {'cap_usd':str(self.cap),'requests':{}}
            if Decimal(state['cap_usd'])!=self.cap:raise BudgetError('Shared budget cap mismatch')
            yield state
            temp_fd,name=tempfile.mkstemp(prefix='state-',dir=self.root)
            try:
                with os.fdopen(temp_fd,'w') as stream:
                    os.fchmod(stream.fileno(),0o600);json.dump(state,stream);stream.flush();os.fsync(stream.fileno())
                os.replace(name,path)
            finally:
                if os.path.exists(name):os.unlink(name)
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)

    def reserve(self,request_id,amount):
        with self.locked() as state:
            held=sum((Decimal(x['held_usd']) for x in state['requests'].values()),Decimal(0))
            if request_id in state['requests']:raise BudgetError('Duplicate request reservation')
            if held+amount>self.cap:raise BudgetError('Aggregate hosted spending ceiling reached')
            state['requests'][request_id]={'held_usd':str(amount),'status':'reserved_or_uncertain'}
        self.journal('run_budget_reserved',{'client_request_id':request_id,'held_total_usd':str(held+amount),'cap_usd':str(self.cap)})

    def settle(self,request_id,known_upper):
        with self.locked() as state:
            row=state['requests'][request_id];reserved=Decimal(row['held_usd'])
            if known_upper<0 or known_upper>reserved:raise BudgetError('Usage upper bound exceeded request reserve')
            row.update(held_usd=str(known_upper),status='completed_usage_upper')
            held=sum((Decimal(x['held_usd']) for x in state['requests'].values()),Decimal(0))
        self.journal('run_budget_settled',{'client_request_id':request_id,'held_total_usd':str(held),'cap_usd':str(self.cap)})
