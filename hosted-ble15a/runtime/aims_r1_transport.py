"""AIMS HTTP boundary only; frozen R1 body and encrypted output are untouched."""
import hashlib,json,os,re,ssl,time,urllib.error,urllib.request
from pathlib import Path
import aims_openai_api as AIMS
from r1api.responses import APIError
HERE=Path(__file__).resolve().parent
CA_SHA='2ef52ad56b4803e264045c915e55c236cbfa045b84b81efefc218a19eb44bd2b'

def post_r1(key,body,timeout,client_request_id,journal):
    if body.get('model')!='gpt-6-luna' or body.get('reasoning')!={'mode':'standard','effort':'medium'}:
        raise APIError('Unexpected frozen model settings',stage='preflight')
    if os.environ.get('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')!='https://api.openai.com/v1':
        raise APIError('Unsupported API base',stage='preflight')
    bundle=HERE/'cacert.pem'
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=CA_SHA:raise APIError('CA hash',stage='preflight')
    context=ssl.create_default_context(cafile=str(bundle))
    if context.verify_mode!=ssl.CERT_REQUIRED or not context.check_hostname:raise APIError('TLS policy',stage='preflight')
    os.environ['OPENAI_API_KEY']=key
    AIMS._MAX_ATTEMPTS=1;AIMS._MAX_PROXY_ATTEMPTS=8;AIMS._MAX_ATTEMPT_SECONDS=20
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*a,**k):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler(),NoRedirect(),urllib.request.HTTPSHandler(context=context))
    captured={};attempts=[]
    class Buffered:
        def __init__(self,raw):self.raw=raw
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,*a):return self.raw
    def proxy_open(request,timeout):
        request.add_header('X-Client-Request-Id',client_request_id)
        if request.full_url!='https://api.openai.com/v1/responses':raise APIError('Endpoint mismatch',stage='preflight')
        started=time.monotonic();row={'client_request_id':client_request_id,'attempt':len(attempts)+1}
        attempts.append(row)
        try:
            with opener.open(request,timeout=min(20,timeout))as response:
                server=response.headers.get('x-request-id')
                if not isinstance(server,str)or not re.fullmatch(r'req_[A-Za-z0-9_-]{1,180}',server):server=None
                captured.update(http_status=response.status,server_request_id=server)
                raw=response.read(16_000_001)
                if len(raw)>16_000_000:raise APIError('Response size',stage='read_response_body')
                if response.status!=200:raise APIError('Unexpected HTTP status',stage='http_response',status=response.status)
                captured['response_sha256']=hashlib.sha256(raw).hexdigest()
                row.update(category='HTTP_RESPONSE',http_status=response.status)
                return Buffered(raw)
        except urllib.error.HTTPError as exc:
            row.update(category='HTTP_ERROR',http_status=exc.code);raise
        except(urllib.error.URLError,TimeoutError,ConnectionError)as exc:
            cause,retry=AIMS._connection_failure(exc)
            row.update(category=cause,known_CONNECT_rejection=cause.startswith('proxy HTTP '),retryable=retry);raise
        finally:
            row['seconds']=time.monotonic()-started;journal('deployment_transport_attempt',row)
    AIMS.urlopen=proxy_open
    try:
        parsed=AIMS.post_json('responses',body,timeout=timeout)
        return parsed,{'http_status':captured.get('http_status'),'server_request_id':captured.get('server_request_id')},captured.get('response_sha256')
    except AIMS.OpenAIRequestError as exc:
        # Official safe_summary has fixed status/category strings, never the raw detail.
        code='proxy_connect'if'proxy HTTP 'in exc.safe_summary else'http_response'if': HTTP 'in exc.safe_summary else'connect_write_or_wait_headers'
        statuses=[a['http_status']for a in attempts if'http_status'in a]
        raise APIError('AIMS boundary failure',stage=code,status=statuses[-1]if statuses else None)from None
