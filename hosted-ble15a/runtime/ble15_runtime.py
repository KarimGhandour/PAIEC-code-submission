"""Small deployment checks; no new inference or retrieval dependencies."""
import fcntl
import shutil
import time


class InitializationFailure(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__('BLE15_INIT_' + code)


def exclusive_lock(fd, timeout=120.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InitializationFailure('LOCK_TIMEOUT') from None
            time.sleep(min(.025, remaining))


def require_disk_space(directory, decoded_bytes, probe=shutil.disk_usage):
    margin = max(64 * 1024 * 1024, decoded_bytes // 100)
    if probe(directory).free < decoded_bytes + margin:
        raise InitializationFailure('INSUFFICIENT_SCRATCH')


def close_readonly_database(database, log):
    """A read-only DB cleanup error must not erase a validated model result.

    Financial/accounting errors retain their original fail-stop semantics.
    No exception text, query, input or label is emitted.
    """
    if database is None:
        return
    try:
        database.close()
    except Exception as exc:
        try:
            log('cleanup_failure', {'stage': 'readonly_database_close',
                                    'reason': type(exc).__name__})
        except Exception:
            pass


def validate_envelope(response, meta, model, effort, requested_tier, error_type):
    """Reject malformed native metadata before dereferencing model output."""
    def reject():
        raise error_type('Invalid response envelope', stage='validate_response')
    if not isinstance(response, dict) or not isinstance(meta, dict):
        reject()
    if meta.get('http_status') not in (None, 200):
        reject()
    if not isinstance(response.get('id'), str) or not response['id']:
        reject()
    actual = response.get('service_tier')
    allowed = {'default'} if requested_tier == 'default' else {'default', 'fast', 'priority'}
    if actual not in allowed:
        reject()
    output = response.get('output')
    if not isinstance(output, list) or not all(isinstance(item, dict) for item in output):
        reject()
    for item in output:
        if item.get('type') == 'message':
            content = item.get('content')
            if not isinstance(content, list) or not all(isinstance(part, dict) for part in content):
                reject()
    return actual
