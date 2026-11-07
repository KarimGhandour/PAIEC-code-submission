"""Direct stateless Responses transport; one counted HTTP attempt, zero retries."""
import copy
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal

ENDPOINT = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-6-luna'
MAX_REQUESTS = 15
MAX_OUTPUT = 32000
# The 12-hour cache-write and long-context/Fast sensitivity rates are held even
# when default 30-minute caching is requested. This is a ceiling, not an invoice.
INPUT_CEILING_PER_M = Decimal('0.50')
OUTPUT_CEILING_PER_M = Decimal('0.75')
REGIONAL_CEILING = Decimal('1.10')


class APIError(RuntimeError):
    def __init__(self, message, *, stage='unknown', status=None, api_type=None,
                 api_code=None, retry_after=None, server_request_id=None,
                 response_sha256=None):
        super().__init__(message)
        self.stage = stage
        self.status = status
        self.api_type = api_type
        self.api_code = api_code
        self.retry_after = retry_after
        self.server_request_id = server_request_id
        self.response_sha256 = response_sha256


class BudgetError(APIError):
    pass


class InputEnvelopeError(APIError):
    """Unsent context-size admission failure; not a financial overspend."""
    pass


def credential(config):
    value = os.environ.get('OPENAI_API_KEY') or (config.get('api_keys') or {}).get('OPENAI_API_KEY')
    if not value or not isinstance(value, str):
        raise APIError('API credential unavailable', stage='credential')
    return value


def _hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def _wire(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _safe(value, key=None):
    value = str(value or '')[:1000]
    if key:
        value = value.replace(key, '[credential redacted]')
    value = re.sub(r'(?i)bearer\s+[^\s,;]+', 'Bearer [redacted]', value)
    value = re.sub(r'sk-[A-Za-z0-9_\-]+', '[credential redacted]', value)
    return ''.join(c if c.isprintable() else ' ' for c in value)[:500]


def _failure(exc, key=None):
    chain = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen and len(chain) < 5:
        seen.add(id(current))
        # Only our own APIError text is controlled; library exception strings may
        # contain request URLs, headers or other arbitrary sensitive data.
        chain.append({'class': type(current).__name__,
                      'message': _safe(current, key) if isinstance(current, APIError)
                      else '[library detail withheld]'})
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return {'exception_chain': chain, 'stage': getattr(exc, 'stage', 'controller_or_transport'),
            'http_status': getattr(exc, 'status', None), 'api_error_type': getattr(exc, 'api_type', None),
            'api_error_code': getattr(exc, 'api_code', None),
            'retry_after': _safe(getattr(exc, 'retry_after', None), key) or None,
            'server_request_id': _safe(getattr(exc, 'server_request_id', None), key) or None,
            'response_sha256': getattr(exc, 'response_sha256', None)}


def _public_response(response):
    """Keep usable action and usage diagnostics; never persist opaque reasoning."""
    result = {k: response.get(k) for k in ('id', 'status', 'model', 'service_tier',
                                          'reasoning', 'usage', 'prompt_cache_retention')}
    result['output'] = []
    for item in response.get('output', []):
        if item.get('type') == 'reasoning':
            result['output'].append({'type': 'reasoning', 'id': item.get('id'),
                                     'encrypted_content_present': bool(item.get('encrypted_content'))})
        elif item.get('type') == 'message':
            result['output'].append({'type': 'message', 'id': item.get('id'),
                                     'phase': item.get('phase'), 'status': item.get('status'),
                                     'role': item.get('role'), 'content': item.get('content')})
        else:
            result['output'].append({'type': item.get('type')})
    return result


def _published_standard_estimate(usage):
    """Only price a write when the API identifies its 30m/12h token class."""
    detail = usage.get('input_tokens_details') or {}
    total = usage.get('input_tokens')
    output = usage.get('output_tokens')
    cached = detail.get('cached_tokens', 0)
    written = detail.get('cache_write_tokens', 0)
    classes = detail.get('cache_write_tokens_details') or {}
    w30 = classes.get('ttl_30m_tokens', 0)
    w12 = classes.get('ttl_12h_tokens', 0)
    if not all(type(x) is int and x >= 0 for x in (total, output, cached, written, w30, w12)):
        return None
    if cached + written > total or w30 + w12 != written:
        return None
    cost = (Decimal(total - cached - written) * Decimal('.10') +
            Decimal(cached) * Decimal('.01') +
            Decimal(w30) * Decimal('.125') +
            Decimal(w12) * Decimal('.25') +
            Decimal(output) * Decimal('.50')) / 1_000_000
    return str(cost)


class ResponsesClient:
    """A fresh client per forecast; all returned reasoning and message items replay intact."""
    def __init__(self, config, journal, *, post=None):
        self.config = config
        self.effort = config.get('ble15_reasoning_effort', 'medium')
        self.requested_tier = config.get('ble15_service_tier', 'default')
        if (self.effort not in ('medium', 'low') or self.requested_tier not in ('default', 'fast')
                or (self.effort == 'low' and self.requested_tier == 'fast')):
            raise APIError('Unregistered BLE15 configuration', stage='preflight')
        self.price_multiplier = Decimal(2 if self.requested_tier == 'fast' else 1)
        self.journal = journal
        self.post = post
        self.history = []
        self.calls = 0
        self.cap = Decimal(str(config.get('max_forecast_usd', 0)))
        self.reserved = Decimal(0)
        self.actual_upper = Decimal(0)
        self.output_cap = int(config.get('max_output_tokens', MAX_OUTPUT))
        if not 4096 <= self.output_cap <= MAX_OUTPUT:
            raise APIError('Output token ceiling outside approved transport range', stage='preflight')
        self.key = None
        self.run_budget = None
        if config.get('max_run_usd') is not None:
            from .run_budget import RunBudget
            self.run_budget = RunBudget(config,journal)
        if post is None:
            if config.get('enable_paid_inference') is not True:
                raise APIError('Paid inference not authorized', stage='authorization')
            self.key = credential(config)
            if self.run_budget is None:
                raise APIError('Aggregate hosted spending guard is required', stage='authorization')

    def _post(self, body, timeout, client_request_id):
        # urllib's direct opener has no SDK retries; disable proxy and redirects.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        raw = _wire(body)
        request = urllib.request.Request(
            ENDPOINT, data=raw,
            headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
                     'X-Client-Request-Id': client_request_id}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        stage = 'connect_write_or_wait_headers'
        try:
            with opener.open(request, timeout=timeout) as response:
                meta = {'http_status': response.status,
                        'server_request_id': response.headers.get('x-request-id'),
                        'retry_after': response.headers.get('Retry-After')}
                stage = 'read_response_body'
                data = response.read(16_000_001)
                if len(data) > 16_000_000:
                    raise APIError('Response body limit exceeded', stage=stage,
                                   status=response.status, server_request_id=meta['server_request_id'])
                stage = 'decode_json'
                try:
                    parsed = json.loads(data)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise APIError('Malformed JSON response', stage=stage,
                                   status=response.status, server_request_id=meta['server_request_id'],
                                   response_sha256=_hash_bytes(data)) from exc
                return parsed, meta, _hash_bytes(data)
        except urllib.error.HTTPError as exc:
            raw_error = exc.read(64_001)
            details = {}
            try:
                details = json.loads(raw_error[:64_000])
            except (ValueError, UnicodeDecodeError):
                pass
            error = details.get('error', {}) if isinstance(details, dict) else {}
            if not isinstance(error, dict):
                error = {}
            raise APIError('HTTP failure (provider message withheld)', stage='http_response',
                           status=exc.code, api_type=_safe(error.get('type'), self.key) or None,
                           api_code=_safe(error.get('code'), self.key) or None,
                           retry_after=exc.headers.get('Retry-After'),
                           server_request_id=exc.headers.get('x-request-id'),
                           response_sha256=_hash_bytes(raw_error)) from None
        except APIError:
            raise
        except Exception as exc:
            raise APIError('Transport ' + type(exc).__name__, stage=stage) from exc

    def call(self, instructions, payload, schema, timeout):
        if timeout <= 0:
            raise APIError('Forecast deadline reached', stage='preflight')
        if self.calls >= MAX_REQUESTS:
            raise APIError('Request limit reached', stage='preflight')
        # Do not append a new user message if preflight/budget validation fails.
        history = [*self.history, {'role': 'user', 'content': payload}]
        body = {'model': MODEL, 'instructions': instructions, 'input': copy.deepcopy(history),
                'reasoning': {'mode': 'standard', 'effort': self.effort}, 'store': False,
                'include': ['reasoning.encrypted_content'], 'tools': [],
                'text': {'format': {'type': 'json_schema', 'name': 'r1_typed_action',
                                    'strict': True, 'schema': schema}},
                'max_output_tokens': self.output_cap, 'service_tier': self.requested_tier}
        raw = _wire(body)
        upper = len(raw) + 4096
        if upper > 250000:
            raise InputEnvelopeError('Conservative input ceiling exceeded', stage='preflight')
        reserve = (Decimal(upper) * INPUT_CEILING_PER_M +
                   Decimal(self.output_cap) * OUTPUT_CEILING_PER_M) * REGIONAL_CEILING * self.price_multiplier / 1_000_000
        if self.cap <= 0 or self.reserved + reserve > self.cap:
            raise BudgetError('Forecast spending cap reached', stage='preflight')
        request_id = str(uuid.uuid4())
        if self.run_budget is not None:self.run_budget.reserve(request_id,reserve)
        self.reserved += reserve
        self.calls += 1
        start_wall = time.time()
        self.journal('request_started', {'request': self.calls, 'client_request_id': request_id,
                                        'started_at': start_wall, 'request_sha256': _hash_bytes(raw),
                                        'request_bytes': len(raw), 'input_items': len(history),
                                        'maximum_reserved_usd': str(reserve),
                                        'cumulative_reserved_usd': str(self.reserved),
                                        'sdk_retries': 0, 'http_attempts': 1})
        self.history = history
        started = time.monotonic()
        try:
            returned = self.post(body, min(240, timeout)) if self.post else self._post(body, min(240, timeout), request_id)
            response, meta, raw_hash = returned if isinstance(returned, tuple) and len(returned) == 3 else (returned, {}, None)
            from ble15_runtime import validate_envelope
            actual_tier = validate_envelope(response, meta, MODEL, self.effort, self.requested_tier, APIError)
            duration = time.monotonic() - started
            response_hash = raw_hash or _hash_bytes(_wire(response))
            self.journal('response_received', {'request': self.calls, 'client_request_id': request_id,
                                               'server_request_id': meta.get('server_request_id'),
                                               'http_status': meta.get('http_status'),
                                               'ended_at': time.time(), 'seconds': duration,
                                               'response_sha256': response_hash,
                                               'response': _public_response(response)})
            usage = response.get('usage') or {}
            if all(type(usage.get(k)) is int and usage[k] >= 0 for k in ['input_tokens', 'output_tokens']):
                cost_upper = (Decimal(usage['input_tokens']) * INPUT_CEILING_PER_M +
                              Decimal(usage['output_tokens']) * OUTPUT_CEILING_PER_M) * REGIONAL_CEILING * self.price_multiplier / 1_000_000
                self.actual_upper += cost_upper
                self.journal('usage', {'request': self.calls, 'client_request_id': request_id,
                                       'usage': usage, 'actual_cost_unknown': True,
                                       'actual_service_tier': actual_tier,
                                       'requested_service_tier': self.requested_tier,
                                       'published_standard_estimate_usd': _published_standard_estimate(usage),
                                       'known_usage_upper_usd': str(cost_upper),
                                       'cumulative_known_usage_upper_usd': str(self.actual_upper),
                                       'uncertain_request_reserve_usd': '0',
                                       'effective_reasoning_context': (response.get('reasoning') or {}).get('context', 'not returned')})
            if response.get('status') != 'completed':
                raise APIError('Incomplete/refused response', stage='validate_response')
            model = response.get('model', '')
            if not re.fullmatch(re.escape(MODEL) + r'(?:-\d{4}-\d{2}-\d{2})?', model):
                raise APIError('Unexpected response model', stage='validate_response')
            if response.get('service_tier') not in ({'default'} if self.requested_tier == 'default' else {'default', 'fast', 'priority'}):
                raise APIError('Unexpected service tier', stage='validate_response')
            rr = response.get('reasoning') or {}
            if rr.get('mode', 'standard') != 'standard' or rr.get('effort', self.effort) != self.effort:
                raise APIError('Reasoning settings changed', stage='validate_response')
            output = response.get('output')
            if not isinstance(output, list):
                raise APIError('Missing native response output', stage='validate_response')
            messages = []
            for item in output:
                if item.get('type') == 'reasoning':
                    if not item.get('encrypted_content'):
                        raise APIError('Missing encrypted reasoning state', stage='validate_response')
                elif item.get('type') == 'message' and item.get('role') == 'assistant':
                    content = item.get('content', [])
                    if any(x.get('type') != 'output_text' for x in content):
                        raise APIError('Refusal/unknown output content', stage='validate_response')
                    messages.append(''.join(x['text'] for x in content))
                else:
                    raise APIError('Unauthorized native output item', stage='validate_response')
            if len(messages) != 1:
                raise APIError('Expected one typed assistant response', stage='validate_response')
            self.history.extend(copy.deepcopy(output))
            if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ['input_tokens', 'output_tokens']):
                raise APIError('Missing usage accounting', stage='validate_response')
            if usage['input_tokens'] > upper or usage['output_tokens'] > self.output_cap:
                raise APIError('Usage exceeded reserved envelope', stage='validate_response')
            if self.run_budget is not None:self.run_budget.settle(request_id,cost_upper)
            estimate = _published_standard_estimate(usage)
            factor = Decimal(2 if actual_tier in ('fast', 'priority') else 1)
            self.journal('response_validated', {'response_id': response['id'],
                'client_request_id': request_id, 'server_request_id': meta.get('server_request_id'),
                'requested_model': MODEL, 'returned_model': model, 'reasoning_effort': self.effort,
                'requested_service_tier': self.requested_tier, 'actual_service_tier': actual_tier,
                'tier_downgraded': self.requested_tier == 'fast' and actual_tier == 'default',
                'usage': usage, 'seconds': duration, 'http_status': meta.get('http_status'),
                'published_effective_tier_estimate_usd': str(Decimal(estimate)*factor) if estimate is not None else None})
            return messages[0]
        except Exception as exc:
            data = _failure(exc, self.key)
            stage = data['stage']
            data.update(request=self.calls, client_request_id=request_id, ended_at=time.time(),
                        seconds=time.monotonic() - started, request_sha256=_hash_bytes(raw),
                        completion_status=('http_error' if stage == 'http_response' else
                                           'response_rejected' if stage == 'validate_response' else
                                           'transport_uncertain'),
                        uncertain_request_reserve_usd=str(reserve),
                        no_automatic_retry=True)
            self.journal('request_failed', data)
            raise
