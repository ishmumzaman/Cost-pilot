import copy
import hashlib
import json
import random
import tempfile
import unittest
from unittest.mock import patch
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path

import pilot
import followup


class Update2Tests(unittest.TestCase):
    def setUp(self):
        self.config = pilot.load_json((pilot.BASE / 'config.json').read_text())
        self.fixture = pilot.load_json((pilot.BASE / 'counties.json').read_text())
        self.counties = pilot.validate_inputs(self.config, self.fixture)

    def test_claim_caps_and_budget_conservation(self):
        rng = random.Random(17)
        for _ in range(500):
            claims = {a: D(rng.randrange(1000)) / 1000 for a in pilot.IDS}
            budget = D(rng.randrange(1, 500)) / 100
            result = pilot.allocate(claims, budget)
            self.assertTrue(all(0 <= result[a] <= F(claims[a])*100 for a in pilot.IDS))
            available = int(budget*100)
            self.assertEqual(sum(result.values()), min(available, sum(int(v*100) for v in claims.values())))
            self.assertEqual(result,pilot.allocate(dict(reversed(list(claims.items()))),budget))

    def test_largest_fraction_wins_not_largest_claim(self):
        claims = dict(zip(pilot.IDS,[D('0.04'),D('0.03'),D('0.02'),D('0.01'),0]))
        self.assertEqual(pilot.allocate(claims,D('.03')),dict(zip(pilot.IDS,[1,1,1,0,0])))

    def test_subcent_caps_and_zero_claims(self):
        self.assertEqual(pilot.allocate(dict.fromkeys(pilot.IDS,D('.006')),D('.02')),dict.fromkeys(pilot.IDS,0))
        self.assertEqual(pilot.allocate(dict.fromkeys(pilot.IDS,0),10),dict.fromkeys(pilot.IDS,0))
        claims = dict(zip(pilot.IDS,[D('0.009'),D('0.04'),0,0,0]))
        self.assertEqual(pilot.allocate(claims,D('.04')),dict(zip(pilot.IDS,[0,4,0,0,0])))

    def test_percent_parsing_exact_units(self):
        value = '2.123456789012345678901234567890123'
        parsed = pilot.parse_claim('{"claim_percent":'+value+',"message":"m"}', 'local_need', 10000000)
        self.assertEqual(F(parsed['claim_amount']),F(value)*100000)
        self.assertEqual(parsed['claim_percent'],D(value))
        self.assertEqual(pilot.parse_claim('{"claim_percent":120,"message":"m"}','hidden_count',100)['claim_amount'],120)
        for raw in ('{"claim_amount":2,"message":"m"}', '{"claim_percent":"2%","message":"m"}',
                    '{"claim_percent":-1,"message":"m"}', '{"claim_percent":true,"message":"m"}',
                    '{"claim_percent":NaN,"message":"m"}', '{"claim_percent":1,"message":"m","claim_amount":1}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                pilot.parse_claim(raw,'hidden_count',10000000)

    def test_variants_only_show_own_reference_and_hide_count(self):
        for a in pilot.IDS:
            local = pilot.build_prompt(a,1,self.counties,10000000,protocol='local_need')
            hidden = pilot.build_prompt(a,1,self.counties,10000000,protocol='hidden_count')
            self.assertIn(f"${self.counties[a]['overdose_deaths']*10000:,}",local)
            self.assertIn('Number of counties sharing the budget: 5',local)
            self.assertNotIn('Number of counties',hidden)
            self.assertNotIn('Hypothetical planning estimate',hidden)
            self.assertIn('claim_percent:',hidden)
            for other in set(pilot.IDS)-{a}:
                self.assertNotIn(f"${self.counties[other]['overdose_deaths']*10000:,}",local)
            self.assertNotIn('fair',pilot.system_prompt('local_need').lower())

    def test_percent_round_two_context_and_source_snapshot(self):
        for protocol in ('local_need','hidden_count'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                summary = pilot.run_once(self.config,self.fixture,pilot.DemoProvider(),root,'diagnostic',
                                          pilot.SpendGuard(root,1),simulated=True,protocol=protocol)
                self.assertEqual(summary['run_status'],'completed')
                folder = root/summary['run_id']
                snap = json.loads((folder/'config.json').read_text())
                self.assertEqual(snap['protocol'],protocol)
                self.assertEqual(hashlib.sha256((folder/'pilot_source.py').read_bytes()).hexdigest(),snap['source_sha256'])
                self.assertIsInstance(summary['utc_minus_monotonic_seconds'],float)
                records = [json.loads(line) for line in (folder/'calls.jsonl').read_text().splitlines()]
                self.assertEqual(len(records),10)
                for record in records[5:]:
                    prompt = record['request']['input'][0]['content']
                    self.assertNotIn('claim_amount',prompt)
                    if protocol=='hidden_count': self.assertNotIn('Number of counties',prompt)
                    for a in pilot.IDS:
                        self.assertEqual(f'"agent_id": "{a}"' in prompt,a in [record['agent_id']]+pilot.NEIGHBORS[record['agent_id']])
                self.assertEqual(summary['allocation_sum_cents']+summary['unallocated_cents'],1000000000)

    def test_followup_fixed_schedule_and_shared_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('config.json','counties.json','requirements.txt'):
                (root/name).write_bytes((pilot.BASE/name).read_bytes())
            ledger_root=root/'runs'/'live'
            ledger_root.mkdir(parents=True)
            pilot.write_json(ledger_root/'spend.json',{'known_cost_usd':'0.01','reservations':{'old_unknown':'0.01'}})
            with patch('pilot.BASE',root),patch('pilot.OpenAIProvider',return_value=pilot.DemoProvider()),patch.dict('os.environ',{'OPENAI_API_KEY':'mock-key'}):
                self.assertEqual(followup.main(['--live']),0)
            folder=next(ledger_root.glob('update2_*'))
            result=pilot.load_json((folder/'results.json').read_text())
            self.assertEqual(result['completed_runs'],2)
            self.assertEqual([r['protocol'] for r in result['runs']],['local_need','hidden_count'])
            self.assertEqual(result['operational_totals_only']['total_api_attempts'],20)
            self.assertNotIn('projections_usd',result['operational_totals_only'])
            ledger=pilot.load_json((ledger_root/'spend.json').read_text())
            self.assertEqual(ledger['reservations'],{'old_unknown':'0.01'})
            self.assertGreater(D(ledger['known_cost_usd']),D('0.01'))

    def test_diagnostic_precision_and_need_order(self):
        claims={a:{'claim_amount':D(n),'message':'m'} for a,n in zip(pilot.IDS,[240000,610000,920000,2050000,4750000])}
        s={'rounds':{'1':{'claims':claims},'2':{'claims':claims}}}
        result=followup.analyze(s,self.fixture,10000000)['1']
        self.assertEqual(result['concordant_death_pairs'],10)
        self.assertEqual(result['noninteger_percent_count'],5)
        self.assertEqual(result['total_claim_percent'],'85.7')
        del s['rounds']['1']['claims']['E']
        result=followup.analyze(s,self.fixture,10000000)['1']
        self.assertIsNone(result['concordant_death_pairs'])
        self.assertIsNone(result['total_claim_percent'])

    def test_explicit_empty404_continuation_preserves_accepted_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);guard=pilot.SpendGuard(root,1);calls=[]
            def fail_seventh(request):
                calls.append(request)
                if len(calls)==7: raise pilot.ApiFailure('api_status',404,body={'unparsed_error':''})
                return pilot.DemoProvider()(request)
            first=pilot.run_once(self.config,self.fixture,fail_seventh,root,'diagnostic',guard,simulated=True,protocol='local_need')
            folder=root/first['run_id'];original=(folder/'calls.jsonl').read_bytes()
            self.assertEqual(first['completed_logical_calls'],6)
            changed=copy.deepcopy(self.config)
            changed['max_output_tokens']=1024
            with self.assertRaises(ValueError):
                pilot.run_once(changed,self.fixture,fail_seventh,root,'diagnostic',guard,simulated=True,protocol='local_need',resume_from=first['run_id'])
            self.assertEqual(len(calls),7)
            continued=[]
            def remaining(request):
                continued.append(request)
                return pilot.DemoProvider()(request)
            final=pilot.run_once(self.config,self.fixture,remaining,root,'diagnostic',guard,simulated=True,protocol='local_need',resume_from=first['run_id'])
            self.assertEqual(len(continued),4)
            self.assertEqual(final['run_status'],'completed')
            self.assertEqual(final['total_api_attempts'],11)
            self.assertEqual(final['retry_count'],1)
            self.assertEqual(final['api_failed_attempts'],1)
            self.assertFalse(final['cost_complete'])
            self.assertEqual(len(guard.data['reservations']),1)
            self.assertTrue((folder/'calls.jsonl').read_bytes().startswith(original))
            self.assertEqual(final['rounds']['1'],first['rounds']['1'])
            self.assertEqual(final['rounds']['2']['claims']['A'],first['rounds']['2']['claims']['A'])
            self.assertEqual(len(final['execution_segments']),2)
            self.assertEqual(final['wall_clock_seconds'],sum(s['monotonic_seconds'] for s in final['execution_segments']))
            with self.assertRaises(ValueError):
                pilot.run_once(self.config,self.fixture,remaining,root,'diagnostic',guard,simulated=True,protocol='local_need',resume_from=first['run_id'])

    def test_followup_report_supports_fractional_dollar_budget(self):
        config=copy.deepcopy(self.config)
        config['allocation_budget_usd']=0.03
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            s=pilot.run_once(config,self.fixture,pilot.DemoProvider(),root,'diagnostic',pilot.SpendGuard(root,1),simulated=True,protocol='hidden_count')
            self.assertEqual(s['run_status'],'completed')
            report_dir=root/'report';report_dir.mkdir()
            report=followup.write_results(report_dir,config,self.fixture,[s],None,True)
            self.assertEqual(report['runs'][0]['diagnostics']['1']['claim_percent_of_budget']['A'],'10')


if __name__ == '__main__':
    unittest.main()
