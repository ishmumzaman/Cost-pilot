import copy
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pilot


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


class ScriptedProvider:
    version = 'test'

    def __init__(self, actions=(), clock=None):
        self.actions = list(actions)
        self.requests = []
        self.clock = clock

    def __call__(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.clock:
            self.clock.now += 0.25
        if self.actions:
            action = self.actions.pop(0)
            if isinstance(action, BaseException):
                raise action
            if callable(action):
                return action(request)
            return copy.deepcopy(action)
        return pilot.DemoProvider()(request)


def response(text='{"claim_amount": 1000000, "message": "Evidence from my county."}', **overrides):
    body = {
        'model': 'gpt-5.6-luna', 'status': 'completed', 'service_tier': 'default',
        'output': [{'type': 'message', 'status': 'completed', 'content': [{'type': 'output_text', 'text': text}]}],
        'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130,
                  'input_tokens_details': {'cached_tokens': 20, 'cache_write_tokens': 30}}
    }
    body.update(overrides)
    return {'body': body, 'http_status': 200, 'request_id': 'req_test'}


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.config = pilot.load_json((pilot.BASE/'config.json').read_text())
        self.fixture = pilot.load_json((pilot.BASE/'counties.json').read_text())
        self.counties = pilot.validate_inputs(self.config, self.fixture)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.clock = FakeClock()

    def tearDown(self):
        self.tmp.cleanup()

    def run_pilot(self, actions=(), limit=None, kind='measured', secret=''):
        provider = ScriptedProvider(actions, self.clock)
        guard = pilot.SpendGuard(self.root, limit or self.config['api_spend_limit_usd'])
        summary = pilot.run_once(self.config, self.fixture, provider, self.root, kind, guard,
                                 simulated=True, sleep=self.clock.sleep, clock=self.clock, secret=secret)
        path = self.root/summary['run_id']
        calls_path = path/'calls.jsonl'
        records = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
        saved = json.loads((path/'summary.json').read_text())
        self.assertEqual(saved['run_status'], summary['run_status'])
        self.assertEqual(len(records), summary['total_api_attempts'])
        return summary, records, provider, guard

    def test_fixture_and_synthetic_rates(self):
        self.assertEqual(list(self.counties), list('ABCDE'))
        self.assertTrue(self.fixture['synthetic'])

    def test_bad_fixtures(self):
        for field, value in [('population', True), ('death_rate_per_100k', 1), ('svi', 1.1), ('poverty_percent', -1)]:
            fixture = copy.deepcopy(self.fixture)
            fixture['counties'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                pilot.validate_inputs(self.config, fixture)
        self.fixture['counties'][0]['id'] = 'B'
        with self.assertRaises(ValueError):
            pilot.validate_inputs(self.config, self.fixture)

    def test_bad_configs_rejected_before_calls(self):
        for field, value in [('model','another-model'), ('temperature',0), ('max_attempts',4),
                             ('max_output_tokens',True), ('request_timeout_seconds',0),
                             ('allocation_budget_usd',0), ('allocation_budget_usd',1.001),
                             ('api_spend_limit_usd','NaN'), ('measured_runs',0)]:
            config = copy.deepcopy(self.config)
            config[field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                pilot.validate_inputs(config, self.fixture)

    def test_parser_rejects_invalid_outputs(self):
        cases = ['null', '[]', 'true', '{}', '{"claim_amount": true, "message":"m"}',
                 '{"claim_amount": "123", "message":"m"}', '{"claim_amount": -1, "message":"m"}',
                 '{"claim_amount": NaN, "message":"m"}', '{"claim_amount": Infinity, "message":"m"}',
                 '{"claim_amount": 1, "message":null}', '{"claim_amount": 1, "message":"  "}',
                 '{"claim_amount": 1, "message":"m", "extra": 0}',
                 '{"claim_amount": 1, "claim_amount": 2, "message":"m"}',
                 '```json\n{"claim_amount": 1, "message":"m"}\n```',
                 '{"claim_amount": 1, "message":"m"} trailing']
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                pilot.parse_claim(text)

    def test_parser_preserves_decimal_and_extreme_claims(self):
        for n in ('0', '1.123456789012345678901234567890123', '1e400'):
            value = pilot.parse_claim('{"claim_amount":'+n+',"message":"  kept  "}')
            self.assertEqual(value['claim_amount'],Decimal(n))
            self.assertEqual(value['message'],'  kept  ')

    def test_allocator_under_over_and_zero_individual(self):
        for base in (Decimal('10000000'), Decimal('1e400')):
            claims = {a: base*i for i,a in enumerate(pilot.IDS)}
            allocation = pilot.allocate(claims,10000000)
            self.assertEqual(sum(allocation.values()),1000000000)
            self.assertEqual(allocation['A'],0)
            self.assertTrue(all(v>=0 for v in allocation.values()))
            self.assertEqual(allocation['E'],400000000)
        claims = {a: Decimal('0.001')*i for i,a in enumerate(pilot.IDS)}
        self.assertEqual(pilot.allocate(claims,10000000),dict.fromkeys(pilot.IDS,0))
        self.assertEqual(pilot.allocate(dict.fromkeys(pilot.IDS,100),10000000),dict.fromkeys(pilot.IDS,10000))

    def test_rounding_tiebreak_and_budget(self):
        result = pilot.allocate(dict.fromkeys(pilot.IDS,Decimal(1)),Decimal('0.03'))
        self.assertEqual(result, {'A':1,'B':1,'C':1,'D':0,'E':0})
        expected = {'A':200000000,'B':141666667,'C':258333333,'D':166666667,'E':233333333}
        self.assertEqual(pilot.allocate(dict(zip(pilot.IDS,[2400000,1700000,3100000,2000000,2800000])),10000000),expected)

    def test_allocator_rejects_invalid_sets(self):
        for claims in ({'A':1}, {**dict.fromkeys(pilot.IDS,1),'A':True},
                       {**dict.fromkeys(pilot.IDS,1),'B':-1}):
            with self.subTest(claims=claims),self.assertRaises(ValueError):
                pilot.allocate(claims,10000000)

    def test_round_one_contains_only_own_data(self):
        prompt = pilot.build_prompt('A',1,self.counties,10000000)
        self.assertIn('45000',prompt)
        for n in ('95000','180000','360000','720000'):
            self.assertNotIn(n,prompt)
        self.assertNotIn('fair', pilot.SYSTEM.lower())
        self.assertIn('B, E',prompt)

    def test_round_two_visibility_and_numeric_claims(self):
        previous = {a:{'claim_amount':Decimal(i)+Decimal('0.001'),'message':'MARKER_'+a} for i,a in enumerate(pilot.IDS)}
        before = copy.deepcopy(previous)
        for agent in pilot.IDS:
            prompt = pilot.build_prompt(agent,2,self.counties,10000000,previous)
            for a in pilot.IDS:
                self.assertEqual('MARKER_'+a in prompt, a==agent or a in pilot.NEIGHBORS[agent])
            self.assertNotIn('"claim_amount": "',prompt)
        self.assertEqual(previous,before)
        with self.assertRaises(ValueError):
            pilot.build_prompt('A',2,self.counties,10000000,{'A':previous['A']})

    def test_request_settings(self):
        body = pilot.request_body(self.config,'prompt')
        self.assertEqual(body['reasoning'],{'effort':'none'})
        self.assertEqual(body['max_output_tokens'],512)
        self.assertEqual(body['tools'],[])
        self.assertFalse(body['stream'])
        for absent in ('temperature','previous_response_id','conversation','prompt_cache_options'):
            self.assertNotIn(absent,body)
        self.assertEqual(body['text'],{'format':{'type':'text'}})

    def test_cost_categories_no_double_counting(self):
        metrics = pilot.usage_cost(response()['body']['usage'],self.config['pricing'],'gpt-5.6-luna','default')
        expected = (Decimal(50)*Decimal('.2') + Decimal(20)*Decimal('.02') + Decimal(30)*Decimal('.25') + Decimal(30)*Decimal('1.2'))/1000000
        self.assertEqual(Decimal(metrics['estimated_cost_usd']),expected)
        self.assertEqual(metrics['billing_tokens']['ordinary_input'],50)

    def test_unknown_usage_not_zero(self):
        self.assertIsNone(pilot.usage_cost(None,self.config['pricing'])['input_tokens'])
        usage = response()['body']['usage']
        del usage['input_tokens_details']['cache_write_tokens']
        metrics = pilot.usage_cost(usage,self.config['pricing'],'gpt-5.6-luna')
        self.assertTrue(metrics['usage_complete'])
        self.assertEqual(metrics['input_tokens'],100)
        self.assertIsNone(metrics['estimated_cost_usd'])

    def test_inconsistent_usage_and_model_pricing(self):
        for update in ({'total_tokens':131}, {'input_tokens':True},
                       {'input_tokens_details':{'cached_tokens':99,'cache_write_tokens':99}}):
            usage = response()['body']['usage']
            usage.update(update)
            self.assertIsNone(pilot.usage_cost(usage,self.config['pricing'],'gpt-5.6-luna')['estimated_cost_usd'])
        for model, tier in [('changed-model','default'),('gpt-5.6-luna','priority')]:
            self.assertIsNone(pilot.usage_cost(response()['body']['usage'],self.config['pricing'],model,tier)['estimated_cost_usd'])

    def test_complete_protocol(self):
        summary, records, provider, guard = self.run_pilot()
        self.assertEqual(summary['run_status'],'completed')
        self.assertEqual(summary['completed_logical_calls'],10)
        self.assertEqual(summary['total_api_attempts'],10)
        self.assertEqual(summary['wall_clock_seconds'],2.5)
        self.assertEqual(summary['paired_claim_count'],5)
        self.assertEqual(summary['allocation_sum_cents'],850000000)
        self.assertEqual(summary['unallocated_cents'],150000000)
        self.assertEqual(len(guard.data['reservations']),0)
        self.assertEqual([r['round'] for r in records],[1]*5+[2]*5)
        # Own previous output and neighbor statements come exclusively from Round 1.
        for rec in records[5:]:
            prompt = rec['request']['input'][0]['content']
            for county in set(pilot.NEIGHBORS[rec['agent_id']]+[rec['agent_id']]):
                amount = 1000000+pilot.IDS.index(county)*300000
                self.assertIn(str(amount),prompt)
        self.assertEqual(summary['rounds']['1']['claim_budget_ratio'],'0.8')
        self.assertEqual(summary['rounds']['2']['claim_budget_ratio'],'0.85')

    def test_rate_limit_recovered_counted_and_backoff_timed(self):
        summary, records, provider, guard = self.run_pilot([pilot.ApiFailure('api_status',429,5)])
        self.assertEqual(summary['run_status'],'completed')
        self.assertEqual(summary['total_api_attempts'],11)
        self.assertEqual(summary['api_failed_attempts'],1)
        self.assertEqual(summary['failed_logical_calls'],0)
        self.assertEqual(summary['retry_count'],1)
        self.assertEqual(summary['rate_limit_count'],1)
        self.assertIsNone(records[0]['parse_success'])
        self.assertIsNone(records[0]['input_tokens'])
        self.assertEqual(records[1]['retry_wait_before_seconds'],5)
        self.assertEqual(records[0]['logical_call_id'],records[1]['logical_call_id'])
        self.assertEqual(summary['wall_clock_seconds'],7.75)
        self.assertFalse(summary['cost_complete'])
        self.assertIsNone(summary['estimated_cost_usd'])
        self.assertEqual(len(guard.data['reservations']),1)
        reloaded = pilot.SpendGuard(self.root,1)
        self.assertEqual(guard.committed,reloaded.committed)

    def test_exhausted_retries_stop_run_and_allocation(self):
        summary, records, provider, guard = self.run_pilot([pilot.ApiFailure('timeout')]*3)
        self.assertEqual(summary['run_status'],'incomplete')
        self.assertEqual(summary['failed_logical_calls'],1)
        self.assertEqual(len(records),3)
        self.assertEqual(self.clock.waits,[2,4])
        self.assertIsNone(summary['allocation_cents'])
        self.assertIsNone(summary['rounds']['1']['claim_budget_ratio'])
        self.assertEqual(summary['parse_failure_count'],0)

    def test_nonretryable_error_stops_without_retry(self):
        summary, records, *_ = self.run_pilot([pilot.ApiFailure('api_status',401,body={'error':{'message':'bad key'}})])
        self.assertEqual(len(records),1)
        self.assertTrue(summary['fatal_batch_error'])
        self.assertEqual(self.clock.waits,[])

    def test_quota_error_and_retry_after(self):
        error = pilot.ApiFailure('api_status',429,body={'error':{'code':'insufficient_quota'}})
        self.assertFalse(error.transient)
        self.assertTrue(error.fatal)
        self.assertEqual(pilot.retry_after_seconds({'retry-after-ms':'2500'}),2.5)
        self.assertEqual(pilot.retry_after_seconds({'retry-after':'5'}),5)
        self.assertIsNone(pilot.retry_after_seconds({'retry-after':'NaN'}))
        summary, records, *_ = self.run_pilot([pilot.ApiFailure('api_status',429,3600)])
        self.assertEqual(summary['failure_reason'],'retry_after_exceeds_wait_limit')
        self.assertEqual(summary['run_status'],'interrupted')
        self.assertEqual(len(records),1)
        self.assertEqual(self.clock.waits,[])

    def test_malformed_billed_response_not_repaired(self):
        summary, records, *_ = self.run_pilot([response('not json')])
        self.assertEqual(len(records),1)
        self.assertEqual(summary['parse_failure_count'],1)
        self.assertEqual(summary['api_failed_attempts'],0)
        self.assertTrue(summary['cost_complete'])
        self.assertGreater(Decimal(summary['estimated_cost_usd']),0)
        self.assertEqual(records[0]['raw_text'],'not json')
        self.assertIsNone(summary['allocation_cents'])

    def test_second_round_failure_keeps_first_round(self):
        actions = [lambda request: pilot.DemoProvider()(request)]*7+[response('bad')]
        summary, records, *_ = self.run_pilot(actions)
        self.assertEqual(summary['run_status'],'incomplete')
        self.assertEqual(summary['rounds']['1']['observed_claim_count'],5)
        self.assertEqual(summary['rounds']['2']['observed_claim_count'],2)
        self.assertEqual(summary['paired_claim_count'],2)
        self.assertIsNone(summary['rounds']['2']['claim_budget_ratio'])
        self.assertIsNone(summary['allocation_cents'])
        self.assertEqual(len(records),8)

    def test_all_zero_claims_leave_entire_budget(self):
        summary, records, *_ = self.run_pilot([response('{"claim_amount":0,"message":"zero"}')]*10)
        self.assertTrue(summary['conversation_complete'])
        self.assertEqual(summary['allocation_status'],'allocated_with_surplus')
        self.assertEqual(summary['run_status'],'completed')
        self.assertEqual(summary['rounds']['2']['claim_budget_ratio'],'0')
        self.assertEqual(summary['failed_logical_calls'],0)
        self.assertEqual(summary['allocation_cents'],dict.fromkeys(pilot.IDS,0))
        self.assertEqual(summary['unallocated_cents'],1000000000)

    def test_refusal_and_truncation_never_accepted(self):
        cases = [response(status='incomplete',incomplete_details={'reason':'max_output_tokens'}),
                 response(output=[{'type':'message','content':[{'type':'refusal','refusal':'No.'}]}])]
        for reply in cases:
            with self.subTest(reply=reply):
                summary, records, *_ = self.run_pilot([reply])
                self.assertEqual(summary['run_status'],'incomplete')
                self.assertEqual(len(records),1)
                self.assertEqual(summary['unusable_response_count'],1)
                self.assertIsNone(summary['allocation_cents'])

    def test_interrupt_inflight_retains_unknown_record(self):
        summary, records, _, guard = self.run_pilot([KeyboardInterrupt()])
        self.assertEqual(summary['run_status'],'interrupted')
        self.assertIsNone(records[0]['api_success'])
        self.assertEqual(summary['unknown_outcome_attempts'],1)
        self.assertFalse(summary['cost_complete'])
        self.assertEqual(len(guard.data['reservations']),1)

    def test_interrupt_during_backoff_saves_summary(self):
        def interrupt_sleep(seconds):
            self.clock.now += 1
            raise KeyboardInterrupt()
        self.clock.sleep = interrupt_sleep
        summary, records, *_ = self.run_pilot([pilot.ApiFailure('timeout')])
        self.assertEqual(summary['run_status'],'interrupted')
        self.assertEqual(summary['retry_wait_seconds'],1)
        self.assertEqual(summary['retry_count'],0)
        self.assertEqual(len(records),1)

    def test_unexpected_exception_recorded(self):
        summary, records, *_ = self.run_pilot([RuntimeError('sensitive exception')])
        self.assertEqual(summary['run_status'],'incomplete')
        self.assertTrue(summary['fatal_batch_error'])
        self.assertEqual(records[0]['error'],'unexpected_RuntimeError')
        self.assertNotIn('sensitive exception',json.dumps(records))

    def test_spend_guard_prevents_calls_and_persists_unknowns(self):
        summary, records, provider, _ = self.run_pilot(limit='0.005')
        self.assertEqual(summary['failure_reason'],'spending_limit')
        self.assertEqual(records,[])
        self.assertEqual(provider.requests,[])
        self.run_pilot([pilot.ApiFailure('timeout')]*3,limit='0.02')
        guard = pilot.SpendGuard(self.root,'0.02')
        self.assertEqual(guard.committed,Decimal('.02'))
        self.assertFalse(guard.reserve('new',pilot.request_body(self.config,'prompt'),self.config))

    def test_unique_artifact_directories_and_secret_redaction(self):
        secret = 'sk-test-secret-value'
        first, records, *_ = self.run_pilot([response('{"claim_amount":1,"message":"'+secret+'"}')],secret=secret)
        second, *_ = self.run_pilot()
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertNotIn(secret,(self.root/first['run_id']/'calls.jsonl').read_text())
        self.assertNotIn(secret,(self.root/first['run_id']/'summary.json').read_text())

    def test_report_retains_failures_and_correct_denominators(self):
        good, *_ = self.run_pilot()
        bad, *_ = self.run_pilot([response('invalid')])
        batch = self.root/'batch'
        batch.mkdir()
        report = pilot.write_report(batch,self.config,self.fixture,[good,bad],5,None,True)
        metrics = report['all_measured_runs']
        self.assertEqual(metrics['started'],2)
        self.assertEqual(metrics['completed'],1)
        self.assertEqual(metrics['total_api_attempts'],11)
        self.assertEqual(metrics['parse_failure_count'],1)
        self.assertEqual(metrics['parsed_response_count'],11)
        self.assertEqual(report['not_started_measured_runs'],3)
        self.assertEqual(Decimal(metrics['effective_cost_per_completed_run_usd']),Decimal(good['estimated_cost_usd'])+Decimal(bad['estimated_cost_usd']))
        self.assertIn('SIMULATED OFFLINE DEMO',(batch/'report.md').read_text())
        self.assertIn(bad['run_id'],(batch/'report.md').read_text())

    def test_extreme_claims_do_not_break_report(self):
        summary, *_ = self.run_pilot([response('{"claim_amount":1e400,"message":"large claim"}')]*10)
        self.assertEqual(summary['run_status'],'completed')
        batch = self.root/'batch'
        batch.mkdir()
        pilot.write_report(batch,self.config,self.fixture,[summary],5,None,True)
        self.assertNotIn('Infinity',(batch/'report.json').read_text())

    def test_sdk_transport_contract_no_live_network(self):
        import httpx
        import openai
        seen = []
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200,json=response()['body'],headers={'x-request-id':'req_mock'})
        provider = pilot.OpenAIProvider(self.config,'not-a-real-key')
        provider.client.close()
        provider.client = openai.OpenAI(api_key='not-a-real-key',max_retries=0,
                                       http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            reply = provider(pilot.request_body(self.config,'prompt'))
            self.assertEqual(reply['request_id'],'req_mock')
            self.assertEqual(reply['http_status'],200)
            self.assertEqual(reply['body']['usage']['input_tokens_details']['cache_write_tokens'],30)
            self.assertEqual(seen[0]['model'],'gpt-5.6-luna')
            self.assertEqual(len(seen),1)
        finally:
            provider.close()

    def test_sdk_no_hidden_retries(self):
        import httpx
        import openai
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429,json={'error':{'code':'rate_limit_exceeded'}},headers={'retry-after':'3','x-request-id':'req_mock_429'})
        provider = pilot.OpenAIProvider(self.config,'not-a-real-key')
        provider.client.close()
        provider.client = openai.OpenAI(api_key='not-a-real-key',max_retries=0,
                                       http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            with self.assertRaises(pilot.ApiFailure) as error:
                provider(pilot.request_body(self.config,'prompt'))
            self.assertEqual(len(calls),1)
            self.assertEqual(error.exception.status,429)
            self.assertEqual(error.exception.retry_after,3)
        finally:
            provider.close()

    def test_cli_live_without_key_never_dispatches(self):
        import os
        with patch.dict(os.environ, {}, clear=True), patch('pilot.OpenAIProvider') as provider:
            with self.assertRaises(SystemExit) as caught:
                pilot.main(['--live'])
            self.assertEqual(caught.exception.code,2)
            provider.assert_not_called()

    def test_measured_failure_is_not_replaced(self):
        import os
        provider = ScriptedProvider([lambda req: pilot.DemoProvider()(req)]*10 + [response('bad')])
        config_path, counties_path = pilot.BASE/'config.json', pilot.BASE/'counties.json'
        with patch('pilot.BASE',self.root), patch('pilot.OpenAIProvider',return_value=provider), patch.dict(os.environ,{'OPENAI_API_KEY':'local-mock-key'}):
            result = pilot.main(['--live','--config',str(config_path),'--counties',str(counties_path)])
        self.assertEqual(result,1)
        self.assertEqual(len(provider.requests),51)  # 10 smoke + 1 failed measured + 40 successful
        report_path = next((self.root/'runs'/'live').glob('batch_*/report.json'))
        report = json.loads(report_path.read_text())
        self.assertEqual(report['all_measured_runs']['started'],5)
        self.assertEqual(report['all_measured_runs']['completed'],4)
        self.assertEqual(report['not_started_measured_runs'],0)

    def test_failed_smoke_stops_measured_batch(self):
        import os
        provider = ScriptedProvider([pilot.ApiFailure('api_status',401)])
        config_path, counties_path = pilot.BASE/'config.json', pilot.BASE/'counties.json'
        with patch('pilot.BASE',self.root), patch('pilot.OpenAIProvider',return_value=provider), patch.dict(os.environ,{'OPENAI_API_KEY':'local-mock-key'}):
            result = pilot.main(['--live','--config',str(config_path),'--counties',str(counties_path)])
        self.assertEqual(result,1)
        self.assertEqual(len(provider.requests),1)
        report = json.loads(next((self.root/'runs'/'live').glob('batch_*/report.json')).read_text())
        self.assertEqual(report['not_started_measured_runs'],5)
        self.assertEqual(report['all_measured_runs']['started'],0)

    def test_report_unknown_cost_disables_projections(self):
        summary, *_ = self.run_pilot([pilot.ApiFailure('connection')])
        batch = self.root/'batch'
        batch.mkdir()
        report = pilot.write_report(batch,self.config,self.fixture,[summary],5,None,True)
        self.assertFalse(report['all_measured_runs']['cost_complete'])
        self.assertIsNone(report['all_measured_runs']['projections_usd'])
        self.assertIsNone(report['all_measured_runs']['effective_cost_per_completed_run_usd'])


if __name__ == '__main__':
    unittest.main()
