import copy
import hashlib
import json
import tempfile
import unittest
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

import pilot
import diagnostics as study


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.config = pilot.load_json((pilot.BASE/'config.json').read_text())
        self.fixture = pilot.load_json((pilot.BASE/'counties.json').read_text())
        self.design = pilot.load_json((pilot.BASE/'diagnostics_config.json').read_text())
        self.counties = pilot.validate_inputs(self.config, self.fixture)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.guard = pilot.SpendGuard(self.root, 1)

    def run_one(self, provider=None, **kwargs):
        return pilot.run_once(self.config, self.fixture, provider or pilot.DemoProvider(), self.root,
                              'diagnostic', self.guard, simulated=True, **kwargs)

    def test_original_prompts_identical_to_saved_preupdate_source(self):
        hashes = pilot.load_json((Path(__file__).parent/'fixtures/original_prompt_hashes.json').read_text())['hashes']
        previous = {a: {'claim_amount': D('2000000'), 'claim_percent': D('20'), 'message': 'County '+a} for a in pilot.IDS}
        for protocol in ('baseline','local_need','hidden_count'):
            for a in pilot.IDS:
                for r in (1,2):
                    self.assertEqual(hashlib.sha256(pilot.build_prompt(a,r,self.counties,10000000,previous,protocol).encode()).hexdigest(),hashes[protocol][f'{a}_{r}'])
                    self.assertEqual(hashlib.sha256(pilot.system_prompt(protocol).encode()).hexdigest(),hashes[protocol]['system'])

    def test_controls_change_only_intended_fields(self):
        for a in pilot.IDS:
            base = pilot.build_prompt(a,1,self.counties,10000000)
            pct = pilot.build_prompt(a,1,self.counties,10000000,protocol='percentage_only')
            hidden = pilot.build_prompt(a,1,self.counties,10000000,protocol='hidden_count')
            self.assertEqual(pct.replace('Number of counties sharing the budget: 5\n',''),hidden)
            for no, yes in [('baseline','local_need_usd'),('percentage_only','local_need')]:
                plain = pilot.build_prompt(a,1,self.counties,10000000,protocol=no)
                estimate = pilot.build_prompt(a,1,self.counties,10000000,protocol=yes)
                self.assertEqual('\n'.join(l for l in estimate.split('\n') if not l.startswith('Hypothetical planning estimate')),plain)
            self.assertEqual(pct,base.replace('requested amount','requested percentage of the total budget').replace('claim_amount: your requested percentage of the total budget as a finite non-negative number in USD','claim_percent: your requested percentage of the total budget as a finite non-negative number (100 means the entire budget)'))

    def test_ratios_exact_and_no_automatic_corrections(self):
        for n in ['1','2','10','0.5','0.01','1.25','1.000000000000000000000000000001']:
            claim=F(n)*240000
            m=pilot.estimate_metrics(claim,240000)
            self.assertEqual(F(m['ratio_exact']),F(n))
            self.assertEqual(m['claim_equals_estimate'],n=='1')
            self.assertEqual(m['simple_multiple'],n if n in pilot.SIMPLE_MULTIPLES else None)
        self.assertEqual(pilot.estimate_metrics(0,0)['estimate_metric_reason'],'zero_estimate')
        self.assertTrue(pilot.estimate_metrics(0,0)['claim_equals_estimate'])
        self.assertFalse(pilot.estimate_metrics(1,0)['claim_equals_estimate'])
        self.assertIsNone(pilot.estimate_metrics(1,None)['claim_equals_estimate'])
        self.assertEqual(pilot.estimate_metrics(None,10)['estimate_metric_reason'],'missing_output')

    def test_dispersion_and_partial_ordering(self):
        self.assertEqual(pilot.dispersion([20]*5)['population_sd'],'0')
        self.assertEqual(pilot.dispersion([1,2,3,4,5])['population_sd'],str(D(2).sqrt()))
        claims={a:{'claim_amount':D(v),'message':'m'} for a,v in zip(pilot.IDS,[2800000,2800000,2500000,2500000,2200000])}
        rounds={'1':claims,'2':copy.deepcopy(claims)}
        m=pilot.research_metrics(rounds,10000000,self.counties,'hidden_count')
        for f in ('population','overdose_deaths'):
            self.assertEqual(m['rounds']['1']['ordering'][f],{'ordered_pair_count':10,'increasing':0,'equal':2,'decreasing':8,'nonincreasing':True})
        self.assertFalse(m['rounds']['1']['ordering']['death_rate_per_100k']['nonincreasing'])
        del rounds['1']['E']
        m=pilot.research_metrics(rounds,10000000,self.counties,'hidden_count')
        self.assertIsNone(m['rounds']['1']['dispersion_pp'])
        self.assertIsNone(m['rounds']['1']['ordering']['population'])
        self.assertEqual(m['paired_count'],4)

    def test_equivalent_formats_and_underclaims(self):
        usd={a:{'claim_amount':D(self.counties[a]['overdose_deaths']*10000),'message':'m'} for a in pilot.IDS}
        pct={a:pilot.parse_claim(json.dumps({'claim_percent':float(v['claim_amount']/100000),'message':'m'}),'local_need',10000000) for a,v in usd.items()}
        allocation=pilot.allocate({a:v['claim_amount'] for a,v in usd.items()},10000000)
        a=pilot.research_metrics({'1':usd,'2':usd},10000000,self.counties,'local_need_usd',allocation)
        b=pilot.research_metrics({'1':pct,'2':pct},10000000,self.counties,'local_need',allocation)
        self.assertEqual(a,b)
        self.assertEqual(a['rounds']['2']['exact_match_count'],5)
        self.assertEqual(a['budget_classification'],'under')
        self.assertEqual(a['unallocated_cents'],143000000)
        self.assertTrue(a['allocated_plus_unallocated_equals_budget'])

    def test_schedule_fixed_counts_and_blocks(self):
        slots=study.schedule(self.design)
        self.assertEqual(slots,study.schedule(self.design))
        self.assertEqual(len(slots),56)
        self.assertEqual(sum(1 if s['role']=='stress_focal' else 10 for s in slots),533)
        for b in range(1,11):
            self.assertEqual({s['condition'] for s in slots if s['block']==b},set(study.CONDITIONS))
        self.assertEqual(len({s['slot_id'] for s in slots}),56)

    def test_message_exposure_counts_records_not_retries(self):
        self.assertEqual(pilot.message_exposure('A',1)['neighbor_message_count'],0)
        self.assertEqual(pilot.message_exposure('A',2)['neighbor_sender_ids'],['B','E'])
        star={'A':['B','C','D','E'], **{a:['A'] for a in 'BCDE'}}
        self.assertEqual(pilot.message_exposure('A',2,star)['neighbor_message_count'],4)
        self.assertEqual(pilot.message_exposure('B',2,star)['neighbor_message_count'],1)
        calls=[]
        def fail_once(req):
            calls.append(req)
            if len(calls)==7: raise pilot.ApiFailure('connection')
            return pilot.DemoProvider()(req)
        with patch('pilot.time.sleep'):
            # Explicit injected sleep: run_once's default is bound at definition time.
            s=self.run_one(fail_once,sleep=lambda _:None)
        records=study.read_calls(self.root,{'run_id':s['run_id']})
        retried=[r for r in records if r['agent_id']=='B' and r['round']==2]
        self.assertEqual(len(retried),2)
        self.assertEqual([r['neighbor_message_count'] for r in retried],[2,2])
        self.assertEqual(s['started_logical_calls'],10)

    def test_stress_isolation_and_no_fabricated_allocation(self):
        parent=self.run_one()
        # Match persisted artifact types used by the real runner.
        parent=pilot.load_json((self.root/parent['run_id']/'summary.json').read_text())
        focal=study.focal_state(parent,self.design['stress_suffix'])
        result=self.run_one(focal=focal,identity={'slot_id':'probe'})
        calls=study.read_calls(self.root,{'run_id':result['run_id']})
        natural=study.read_calls(self.root,{'run_id':parent['run_id']})[5]
        original=parent['rounds']['1']['claims']['E']['message']
        expected=natural['request']['input'][0]['content'].replace(json.dumps(original),json.dumps(original+' '+self.design['stress_suffix']))
        self.assertEqual(calls[0]['request']['input'][0]['content'],expected)
        self.assertEqual(result['total_api_attempts'],1)
        self.assertEqual(result['completed_logical_calls'],1)
        self.assertEqual(result['rounds']['1']['observed_claim_count'],0)
        self.assertIsNone(result['allocation_cents'])
        self.assertEqual(result['allocation_status'],'not_applicable_focal_probe')
        self.assertEqual(calls[0]['experiment_identity'],{'slot_id':'probe'})

    def test_focal_empty404_and_identity_mismatch(self):
        parent=self.run_one()
        parent=pilot.load_json((self.root/parent['run_id']/'summary.json').read_text())
        focal=study.focal_state(parent,self.design['stress_suffix'])
        def fail(req): raise pilot.ApiFailure('api_status',404,body={'unparsed_error':''})
        s=self.run_one(fail,focal=focal,identity={'slot_id':'S1'})
        old=(self.root/s['run_id']/'calls.jsonl').read_bytes()
        with self.assertRaises(ValueError):
            self.run_one(focal=focal,identity={'slot_id':'S2'},resume_from=s['run_id'])
        changed=copy.deepcopy(focal);changed['suffix']+=' Changed'
        with self.assertRaises(ValueError):
            self.run_one(focal=changed,identity={'slot_id':'S1'},resume_from=s['run_id'])
        done=self.run_one(focal=focal,identity={'slot_id':'S1'},resume_from=s['run_id'])
        self.assertEqual(done['total_api_attempts'],2)
        self.assertEqual(done['completed_logical_calls'],1)
        self.assertTrue((self.root/s['run_id']/'calls.jsonl').read_bytes().startswith(old))
        self.assertFalse(done['cost_complete'])
        self.assertEqual(len(self.guard.data['reservations']),1)

    def test_runner_failure_retained_without_replacement(self):
        d=copy.deepcopy(self.design);d['runs_per_condition']=2
        folder,m=study.create_batch(self.root,self.config,self.fixture,d,'repeated',True,self.guard)
        calls=[]
        def malformed_first(req):
            calls.append(req);reply=pilot.DemoProvider()(req)
            if len(calls)==1: reply['body']['output'][0]['content'][0]['text']='invalid'
            return reply
        study.execute_batch(self.root,folder,m,malformed_first,self.guard)
        self.assertEqual([s['status'] for s in m['slots']].count('incomplete'),1)
        self.assertEqual([s['status'] for s in m['slots']].count('completed'),9)
        self.assertEqual(len(calls),91)
        r=pilot.load_json((folder/'results.json').read_text())
        self.assertEqual(r['operational_totals_only']['unusable_response_count'],1)
        self.assertEqual(len(r['runs']),10)

    def test_batch_continuation_and_saved_slot_identity(self):
        d=copy.deepcopy(self.design);d['runs_per_condition']=1
        folder,m=study.create_batch(self.root,self.config,self.fixture,d,'repeated',True,self.guard)
        def fail(req): raise pilot.ApiFailure('api_status',404,body={'unparsed_error':''})
        study.execute_batch(self.root,folder,m,fail,self.guard)
        slot=study.validate_continuation(self.root,folder,m,self.config,self.fixture,d,True)
        changed=copy.deepcopy(m);changed['slots'][0]['condition']='F9'
        with self.assertRaises(ValueError):study.validate_continuation(self.root,folder,changed,self.config,self.fixture,d,True)
        changed=copy.deepcopy(m);changed['slots'][0]['status']='running'
        with self.assertRaises(ValueError):study.validate_continuation(self.root,folder,changed,self.config,self.fixture,d,True)
        study.execute_batch(self.root,folder,m,pilot.DemoProvider(),self.guard,continue_slot=slot)
        r=pilot.load_json((folder/'results.json').read_text())
        self.assertEqual(r['operational_totals_only']['total_api_attempts'],51)
        self.assertEqual(r['slot_status_counts'],{'completed':5})
        with self.assertRaises(ValueError):study.validate_continuation(self.root,folder,m,self.config,self.fixture,d,True)

    def test_all_zero_and_tiny_change(self):
        zero={a:{'claim_amount':D(0),'message':'m'} for a in pilot.IDS}
        second=copy.deepcopy(zero);second['A']['claim_amount']=D('1e-40')
        m=pilot.research_metrics({'1':zero,'2':second},10000000,self.counties,'baseline',dict.fromkeys(pilot.IDS,0))
        self.assertTrue(m['claim_changes']['A']['changed'])
        self.assertEqual(m['budget_classification'],'under')
        self.assertEqual(m['unallocated_cents'],1000000000)

    def test_missing_parent_and_malformed_stress_stay_missing(self):
        parent=self.run_one()
        parent=pilot.load_json((self.root/parent['run_id']/'summary.json').read_text())
        missing=copy.deepcopy(parent);del missing['rounds']['1']['claims']['E']
        self.assertIsNone(study.focal_state(missing,self.design['stress_suffix']))
        focal=study.focal_state(parent,self.design['stress_suffix'])
        def malformed(req):
            reply=pilot.DemoProvider()(req)
            reply['body']['output'][0]['content'][0]['text']='invalid'
            return reply
        result=self.run_one(malformed,focal=focal)
        self.assertEqual(result['run_status'],'incomplete')
        self.assertEqual(result['rounds']['2']['claims'],{})
        self.assertIsNone(result['allocation_cents'])
        self.assertEqual(result['total_api_attempts'],1)


if __name__ == '__main__':
    unittest.main()
