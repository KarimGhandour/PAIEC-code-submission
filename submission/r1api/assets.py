"""Materialize the hash-bound, losslessly compressed SQLite once per container."""
from functools import lru_cache
import fcntl,hashlib,json,os,tempfile,lzma
from pathlib import Path
import pyarrow as pa
from .util import file_sha
DATA=Path(__file__).resolve().parents[1]/'data'
CACHE_ROOT=Path('/tmp/paiec-r1-assets')

@lru_cache(maxsize=1)
def hydrated_corpus():
    manifest=json.loads((DATA/'compact_assets.json').read_text())
    # Import lazily: the DB module's frozen expected hash is available by now.
    from .db import FROZEN_CORPUS_SHA
    expected=FROZEN_CORPUS_SHA
    if manifest.get('format')!='r1-compact-assets-v1' or manifest.get('database_sha256')!=expected:
        raise PermissionError('Compact assets do not match frozen corpus')
    size=manifest['database_bytes']
    if type(size) is not int or not 0<size<=12_636_401_664:raise PermissionError('Invalid decoded corpus bound')
    root=CACHE_ROOT/expected
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.is_symlink() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:
        raise PermissionError('Unsafe shared asset cache')
    target=root/'corpus.sqlite'
    fd=os.open(root/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        if target.exists():
            if target.is_symlink() or target.stat().st_size!=size:raise PermissionError('Invalid shared corpus')
            # AuditedDB still verifies the complete hash once in every process.
            return target
        names={'xz':'evidence.xz.bin','zstd':'evidence.zstd.bin'}
        codec=manifest.get('codec')
        if codec not in names or manifest.get('packed')!=names[codec]:raise PermissionError('Invalid packed asset codec/path')
        packed=DATA/names[codec]
        if file_sha(packed)!=manifest['packed_sha256']:raise PermissionError('Packed corpus hash mismatch')
        tmpfd,name=tempfile.mkstemp(prefix='decode-',dir=root)
        try:
            h=hashlib.sha256();count=0
            source=lzma.open(packed,'rb') if codec=='xz' else pa.CompressedInputStream(str(packed),'zstd')
            with os.fdopen(tmpfd,'wb') as out,source:
                for chunk in iter(lambda:source.read(4*1024*1024),b''):
                    count+=len(chunk)
                    if count>size:raise PermissionError('Decoded corpus exceeds bound')
                    out.write(chunk);h.update(chunk)
                out.flush();os.fsync(out.fileno())
            if count!=size or h.hexdigest()!=expected:raise PermissionError('Decoded corpus hash mismatch')
            os.chmod(name,0o444);os.replace(name,target)
        finally:
            if os.path.exists(name):os.unlink(name)
        return target
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
