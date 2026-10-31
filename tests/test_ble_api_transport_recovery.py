"""Offline transport regressions: no sockets, no paid inference."""
import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'submission'
sys.path[:0] = [str(P), str(P / 'src'), str(ROOT / 'scripts')]
from r1api.responses import ResponsesClient, APIError, _published_standard_estimate
from r1api.predictor import Journal, forecast
from r1api.protocol import wire_schema
from test_ble_api_parity_001 import Mock, action
from r1api import predictor as p


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        stop = patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden'))
        stop.start()
        self.addCleanup(stop.stop)
        self.log = Journal(self.tmp.name)

    def test_full_five_action_replay_and_no_opaque_log(self):
        class DB:
            calls = 0
            def find_model(self, *args, **kwargs):
                self.calls += 1
                return json.dumps({'tool': 'find_model', 'evidence': [{'trial': self.calls}]})
            def close(self):
                pass

        db = DB()
        actions = [action('find_model', prob=.60 + .02 * i, model_name='test') for i in range(4)] + [action(prob=.71)]
        mock = Mock(actions)
        value = forecast([{'normalized_name': 'test'}, {'item_content': 'What is 2+2?'}], [],
                         config={'max_forecast_usd': .5}, journal=self.log,
                         client_factory=lambda c, j: ResponsesClient(c, j, post=mock), db_factory=lambda *a: db)
        self.assertEqual(value, .71)
        self.assertEqual(db.calls, 4)
        self.assertEqual(len(mock.requests), 5)
        for n in range(1, 5):
            for item in mock.responses[n-1]['output']:
                self.assertIn(item, mock.requests[n]['input'])
            self.assertEqual(mock.requests[n]['input'][-1]['role'], 'user')
        raw = (self.log.directory / 'audit.jsonl').read_text()
        for i in range(1, 6):
            self.assertNotIn('opaque' + str(i), raw)
        starts = [x for x in self.log.events if x['event'] == 'request_started']
        self.assertEqual(len({x['client_request_id'] for x in starts}), 5)
        self.assertTrue(all(x['sdk_retries'] == 0 and x['http_attempts'] == 1 for x in starts))
        self.assertTrue(all('body' not in x for x in starts))
        self.assertEqual(len([x for x in self.log.events if x['event'] == 'usage']), 5)

    def test_schema_repair_preserves_response_history(self):
        mock = Mock(['bad JSON', action(prob=.62)])
        value = forecast([{'normalized_name': 'test'}, {'item_content': 'A simple question'}], [],
                         config={'max_forecast_usd': .5}, journal=self.log,
                         client_factory=lambda c, j: ResponsesClient(c, j, post=mock))
        self.assertEqual(value, .62)
        self.assertEqual(len(mock.requests), 2)
        for item in mock.responses[0]['output']:
            self.assertIn(item, mock.requests[1]['input'])
        self.assertIn('schema_repair', mock.requests[1]['input'][-1]['content'])

    @unittest.skip('Private data/native records not redistributed; see docs/reproducibility.md')
    def test_preserved_live_turn_replays_exact_encrypted_items(self):
        marker = json.loads((ROOT / 'runs/BLE-API-PARITY-001/first_live_forecast.json').read_text())
        events = [json.loads(line) for line in (Path(marker['journal']) / 'audit.jsonl').read_text().splitlines()]
        original_response = next(x['response'] for x in events if x['event'] == 'response_received')
        original_bodies = [x['body'] for x in events if x['event'] == 'request_started']
        follow = original_bodies[-1]
        calls = []
        def post(body, timeout):
            calls.append(body)
            return original_response if len(calls) == 1 else Mock([action()])(body, timeout)
        client = ResponsesClient({'max_forecast_usd': .5}, self.log, post=post)
        client.call(original_bodies[1]['instructions'], original_bodies[1]['input'][0]['content'],
                    original_bodies[1]['text']['format']['schema'], 30)
        client.call(follow['instructions'], follow['input'][-1]['content'],
                    follow['text']['format']['schema'], 30)
        self.assertEqual(calls[1]['input'], follow['input'])
        self.assertEqual(calls[1]['input'][1:-1], original_response['output'])
        self.assertNotIn('"encrypted_content":', (self.log.directory / 'audit.jsonl').read_text())

    def test_timeout_cause_chain_is_sanitized_without_retry(self):
        key = 'sk-test-secret-never-log'
        def fails(body, timeout):
            try:
                raise TimeoutError('timeout Bearer ' + key)
            except TimeoutError as exc:
                raise APIError('transport failed', stage='read_response_body') from exc
        client = ResponsesClient({'max_forecast_usd': .5}, self.log, post=fails)
        with self.assertRaises(APIError):
            client.call('instructions', 'payload', wire_schema(p.TOOLS), 10)
        raw = (self.log.directory / 'audit.jsonl').read_text()
        self.assertNotIn(key, raw)
        failure = next(x for x in self.log.events if x['event'] == 'request_failed')
        self.assertEqual(failure['stage'], 'read_response_body')
        self.assertEqual([x['class'] for x in failure['exception_chain']], ['APIError', 'TimeoutError'])
        self.assertEqual(failure['completion_status'], 'transport_uncertain')
        self.assertEqual(client.calls, 1)

    def test_http_error_fields_client_id_and_zero_retry(self):
        key = 'sk-test-secret-never-log'
        requests = []
        body = json.dumps({'error': {'type': 'rate_limit_error', 'code': 'slow_down',
                                     'message': 'Bearer ' + key + ' retry later'}}).encode()
        def opener(*args, **kwargs):
            class Stub:
                def open(self, req, timeout):
                    requests.append(req)
                    raise urllib.error.HTTPError(req.full_url, 429, 'rate limited',
                                                 {'x-request-id': 'req-safe', 'Retry-After': '9'}, io.BytesIO(body))
            return Stub()
        client = ResponsesClient({'max_forecast_usd': .5, 'enable_paid_inference': True, 'max_run_usd': 1, 'run_budget_id': 'offline_public_http_001', 'run_budget_root': self.tmp.name,
                                  'api_keys': {'OPENAI_API_KEY': key}}, self.log)
        with patch('urllib.request.build_opener', side_effect=opener):
            with self.assertRaises(APIError):
                client.call('instructions', 'payload', wire_schema(p.TOOLS), 10)
        self.assertEqual(len(requests), 1)
        start = next(x for x in self.log.events if x['event'] == 'request_started')
        self.assertEqual(requests[0].get_header('X-client-request-id'), start['client_request_id'])
        failure = next(x for x in self.log.events if x['event'] == 'request_failed')
        self.assertEqual((failure['http_status'], failure['api_error_type'], failure['api_error_code']),
                         (429, 'rate_limit_error', 'slow_down'))
        self.assertEqual((failure['retry_after'], failure['server_request_id']), ('9', 'req-safe'))
        self.assertEqual(failure['completion_status'], 'http_error')
        self.assertNotIn(key, (self.log.directory / 'audit.jsonl').read_text())

    def test_malformed_http_body_has_hash_and_stage(self):
        class Stub:
            status = 200
            headers = {'x-request-id': 'req-malformed'}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, n):
                return b'{invalid'
        class Opener:
            def open(self, req, timeout):
                return Stub()
        client = ResponsesClient({'max_forecast_usd': .5, 'enable_paid_inference': True, 'max_run_usd': 1, 'run_budget_id': 'offline_public_http_001', 'run_budget_root': self.tmp.name,
                                  'api_keys': {'OPENAI_API_KEY': 'sk-test'}}, self.log)
        with patch('urllib.request.build_opener', return_value=Opener()):
            with self.assertRaises(APIError):
                client.call('instructions', 'payload', wire_schema(p.TOOLS), 10)
        failure = next(x for x in self.log.events if x['event'] == 'request_failed')
        self.assertEqual(failure['stage'], 'decode_json')
        self.assertEqual(failure['server_request_id'], 'req-malformed')
        self.assertEqual(len(failure['response_sha256']), 64)

    @unittest.skip('Private data/native records not redistributed; see docs/reproducibility.md')
    def test_stale_cache_fails_closed_without_sql_access(self):
        from r1api.db import _static_firewall, RUN
        original = (RUN / 'firewall_static_cache.json').read_bytes()
        # Test a temporary cache artifact; never mutate the packaged one.
        temp = Path(self.tmp.name) / 'stale.json'
        bad = json.loads(original)
        bad['corpus_sha256'] = '0' * 64
        temp.write_text(json.dumps(bad))
        protected = json.loads((RUN / 'protected_inputs.json').read_text())
        excluded = json.loads((P / 'r1api/excluded_families.json').read_text())
        policy = json.loads((RUN / 'active_permission_policy.json').read_text())
        with self.assertRaises(PermissionError):
            _static_firewall(temp, protected, excluded, policy, RUN / 'evidence.bin')
        for field in ('policy_file_sha256', 'protected_file_sha256',
                      'excluded_file_sha256', 'blocked_ids_sha256'):
            bad = json.loads(original)
            bad[field] = '0' * 64
            temp.write_text(json.dumps(bad))
            with self.assertRaises(PermissionError, msg=field):
                _static_firewall(temp, protected, excluded, policy, RUN / 'evidence.bin')
        temp.unlink()
        with self.assertRaises(PermissionError):
            _static_firewall(temp, protected, excluded, policy, RUN / 'evidence.bin')

    def test_local_firewall_failure_is_separate_from_transport(self):
        mock = Mock([action('find_model', model_name='test')])
        def broken_db(*args):
            raise PermissionError('stale frozen cache')
        value = forecast([{'normalized_name': 'test'}, {'item_content': 'Question'}], [],
                         config={'max_forecast_usd': .5}, journal=self.log,
                         client_factory=lambda c, j: ResponsesClient(c, j, post=mock),
                         db_factory=broken_db)
        self.assertEqual(value, .5)
        event = next(x for x in self.log.events if x['event'] == 'controller_failed')
        self.assertEqual(event['stage'], 'local_firewall_initialization')
        self.assertEqual(len(mock.requests), 1)

    def test_cache_write_price_is_unknown_without_ttl_breakdown(self):
        unknown = {'input_tokens': 1000, 'output_tokens': 100,
                   'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 900}}
        self.assertIsNone(_published_standard_estimate(unknown))
        known = {'input_tokens': 1000, 'output_tokens': 100,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 900,
                                          'cache_write_tokens_details': {'ttl_30m_tokens': 900,
                                                                         'ttl_12h_tokens': 0}}}
        self.assertEqual(_published_standard_estimate(known), '0.0001725')

    def test_transport_output_cap_and_conservative_reserve(self):
        mock = Mock([action()])
        client = ResponsesClient({'max_forecast_usd': .5, 'max_output_tokens': 8192}, self.log, post=mock)
        client.call('instructions', 'payload', wire_schema(p.TOOLS), 10)
        self.assertEqual(mock.requests[0]['max_output_tokens'], 8192)
        started = next(x for x in self.log.events if x['event'] == 'request_started')
        self.assertGreater(float(started['maximum_reserved_usd']), .006)
        self.assertLessEqual(float(started['maximum_reserved_usd']), .5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
