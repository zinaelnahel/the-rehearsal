import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend import feedback,main


class SharedFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.folder=self.enterContext(tempfile.TemporaryDirectory(prefix='rehearsal-feedback-'))
        self.db=Path(self.folder)/'feedback.sqlite3'
        self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory',
            'REHEARSAL_AGENT_ENABLED':'false','FEEDBACK_ENABLED':'true',
            'FEEDBACK_DB_PATH':str(self.db),'FEEDBACK_RETENTION_DAYS':'90'}))
        self.enterContext(patch('backend.main.LIVE',False))
        self.client=self.enterContext(TestClient(main.app))
        self.sid=self.client.post('/api/sessions',json={'text':'Private marker SECRET_DOCUMENT_491. Monthly rent is 850 euros.'}).json()['id']
        self.path='/api/sessions/'+self.sid
        self.client.post(self.path+'/mission',json={'scenario':'apartment','language':'English','feedback_language':'English','level':'Everyday'})
        self.client.post(self.path+'/start',json={'goals':['Ask about rent']})
        self.client.post(self.path+'/turn',json={'text':'How much is the rent? SECRET_LEARNER_271'})
        self.review=self.client.post(self.path+'/finish').json()
        self.url=self.path+'/responses/'+self.review['feedback_id']+'/feedback'

    def rate(self,**kwargs):
        return self.client.put(self.url,json={'rating':'down','reason':'speed',**kwargs})

    def rows(self):
        if not self.db.exists():return []
        with closing(sqlite3.connect(self.db)) as db:
            db.row_factory=sqlite3.Row
            return [dict(row) for row in db.execute('SELECT * FROM feedback')]

    def test_session_only_by_default_and_explicit_opt_in_required(self):
        response=self.rate()
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['shared'])
        self.assertFalse(self.db.exists())

    def test_quality_ratings_share_update_withdraw_and_clear_with_the_vote(self):
        quality={'relevance':'pass','continuity':'fail','grounding':'uncertain'}
        self.assertEqual(self.rate(quality=quality).status_code,200)
        self.assertFalse(self.db.exists())
        saved=main.sessions[self.sid]['ratings'][self.review['feedback_id']]
        self.assertEqual(saved['quality'],quality)
        self.assertEqual(self.rate(quality=quality,share_for_improvement=True).status_code,200)
        self.assertEqual(json.loads(self.rows()[0]['quality']),quality)
        report=feedback.report()
        self.assertEqual(report['quality_ratings']['continuity']['fail'],1)
        self.assertEqual(report['quality_ratings']['memory']['unrated'],1)
        self.assertEqual(report['quality_ratings']['grounding']['uncertain'],1)
        self.assertEqual(report['quality_by_language']['English']['relevance']['pass'],1)
        self.assertEqual(self.rate(quality={'memory':'fail'},share_for_improvement=True).status_code,200)
        self.assertEqual(json.loads(self.rows()[0]['quality']),{'memory':'fail'})
        self.assertEqual(self.rate(quality=quality,share_for_improvement=False).status_code,200)
        self.assertEqual(self.rows(),[])
        self.assertEqual(self.rate(rating=None,reason=None).status_code,200)
        self.assertNotIn(self.review['feedback_id'],main.sessions[self.sid]['ratings'])

    def test_quality_rejects_free_text_unknown_dimensions_and_response_ratings(self):
        for quality in ({'memory':'a private explanation'},{'private_text':'fail'},{'grounding':None}):
            self.assertEqual(self.rate(quality=quality).status_code,422)
        self.assertEqual(self.rate(rating=None,reason=None,quality={'memory':'pass'}).status_code,400)
        response_id=main.sessions[self.sid]['turns'][0]['id']
        response_url=self.path+'/responses/'+response_id+'/feedback'
        self.assertEqual(self.client.put(response_url,json={'rating':'up','quality':{'memory':'fail'}}).status_code,400)
        self.assertFalse(self.db.exists())

    def test_existing_database_is_migrated_without_losing_old_votes(self):
        self.assertEqual(self.rate(share_for_improvement=True).status_code,200)
        identifier=self.rows()[0]['id']
        with closing(sqlite3.connect(self.db)) as db,db:
            db.execute('ALTER TABLE feedback DROP COLUMN quality')
        self.assertEqual(feedback.report()['dialogue_ratings']['ratings'],1)
        self.assertEqual(self.rows()[0]['id'],identifier)
        self.assertEqual(json.loads(self.rows()[0]['quality']),{})
        self.assertEqual(feedback.report()['quality_ratings']['memory']['unrated'],1)
        self.assertEqual(self.rate(quality={'memory':'pass'},share_for_improvement=True).status_code,200)
        self.assertEqual(json.loads(self.rows()[0]['quality']),{'memory':'pass'})

    def test_shared_feedback_survives_session_deletion_without_private_text_or_ids(self):
        response=self.rate(share_for_improvement=True)
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json()['shared'])
        self.client.delete(self.path)
        rows=self.rows()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['kind'],'dialogue')
        self.assertEqual(rows[0]['reason'],'speed')
        self.assertEqual(rows[0]['measured_turns'],1)
        raw=self.db.read_bytes()
        for secret in (self.sid,self.review['feedback_id'],'SECRET_DOCUMENT_491','SECRET_LEARNER_271','How much is the rent?'):
            self.assertNotIn(secret.encode(),raw)
        self.assertEqual(set(rows[0]),{'id','created_day','updated_day',*feedback.FIELDS})
        with patch('backend.main.sessions',{}):
            self.assertEqual(feedback.report()['dialogue_ratings']['ratings'],1)

    def test_idempotent_updates_and_withdrawal(self):
        for reason in ('speed','tone','fact'):
            response=self.rate(share_for_improvement=True,reason=reason)
            self.assertEqual(response.status_code,200,response.text)
        original=self.rows()[0]['id']
        self.assertEqual(len(self.rows()),1)
        self.assertEqual(self.rows()[0]['reason'],'fact')
        self.assertEqual(self.rate(share_for_improvement=True,rating='up',reason=None).status_code,200)
        self.assertEqual(self.rows()[0]['id'],original)
        self.assertEqual(self.rows()[0]['rating'],'up')
        response=self.rate(share_for_improvement=False)
        self.assertFalse(response.json()['shared'])
        self.assertEqual(self.rows(),[])
        self.assertEqual(main.sessions[self.sid]['ratings'][self.review['feedback_id']]['rating'],'down')

    def test_clear_removes_both_copies_and_repeated_clear_is_safe(self):
        self.rate(share_for_improvement=True)
        for _ in range(2):
            response=self.rate(rating=None,reason=None,share_for_improvement=True)
            self.assertEqual(response.status_code,200)
            self.assertFalse(response.json()['shared'])
        self.assertEqual(self.rows(),[])
        self.assertEqual(main.sessions[self.sid]['ratings'],{})

    def test_no_arbitrary_text_build_values_or_other_sessions(self):
        self.assertEqual(self.rate(text='Private feedback').status_code,422)
        self.assertEqual(self.rate(frontend_build='<script>private</script>').status_code,422)
        self.assertEqual(self.rate(rating='up',reason='speed').status_code,400)
        self.assertEqual(self.client.put(self.url.replace(self.sid,'another-session'),json={'rating':'up','share_for_improvement':True}).status_code,404)
        self.assertFalse(self.db.exists())

    def test_storage_failure_does_not_claim_success_or_change_previous_rating(self):
        self.rate(rating='up',reason=None)
        with patch('backend.feedback.connect',side_effect=sqlite3.OperationalError('Unavailable')):
            response=self.rate(share_for_improvement=True)
        self.assertEqual(response.status_code,503)
        self.assertEqual(main.sessions[self.sid]['ratings'][self.review['feedback_id']]['rating'],'up')
        self.assertFalse(main.sessions[self.sid]['shared_feedback'])

    def test_failed_removal_keeps_shared_receipt_for_retry(self):
        self.rate(share_for_improvement=True)
        with patch('backend.feedback.connect',side_effect=sqlite3.OperationalError('Unavailable')):
            response=self.rate(share_for_improvement=False)
        self.assertEqual(response.status_code,503)
        self.assertEqual(len(self.rows()),1)
        self.assertTrue(main.sessions[self.sid]['shared_feedback'])
        self.assertEqual(self.rate(share_for_improvement=False).status_code,200)
        self.assertEqual(self.rows(),[])

    def test_disabled_collection_rejects_sharing_but_allows_removal(self):
        self.rate(share_for_improvement=True)
        with patch.dict(os.environ,{'FEEDBACK_ENABLED':'false'}):
            self.assertEqual(self.rate(share_for_improvement=True).status_code,503)
            self.assertEqual(self.rate(share_for_improvement=False).status_code,200)
        self.assertEqual(self.rows(),[])

    def test_retention_purges_expired_rows_but_keeps_boundary(self):
        self.rate(share_for_improvement=True)
        from datetime import timedelta
        with closing(sqlite3.connect(self.db)) as db,db:
            db.execute('UPDATE feedback SET created_day=?',((feedback.today()-timedelta(days=89)).isoformat(),))
        self.assertEqual(feedback.report(90)['dialogue_ratings']['ratings'],1)
        with closing(sqlite3.connect(self.db)) as db,db:
            db.execute('UPDATE feedback SET created_day=?',((feedback.today()-timedelta(days=90)).isoformat(),))
        feedback.cleanup()
        self.assertEqual(self.rows(),[])

    def test_aggregate_report_and_separate_process_access(self):
        self.rate(share_for_improvement=True)
        result=feedback.report()
        self.assertEqual(result['negative_reasons'],{'speed':1})
        self.assertEqual(result['dialogue_ratings']['useful_percent'],0)
        self.assertEqual(result['breakdowns']['language']['English']['ratings'],1)
        self.assertNotIn(self.sid,json.dumps(result))
        self.assertNotIn(self.rows()[0]['id'],json.dumps(result))
        html=Path(self.folder)/'report.html'
        report=Path(self.folder)/'report.json'
        completed=subprocess.run([sys.executable,'scripts/report_feedback.py','--html',str(html),'--json',str(report)],capture_output=True,text=True,timeout=30)
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertIn('Too slow',html.read_text(encoding='utf-8'))
        self.assertEqual(json.loads(report.read_text())['dialogue_ratings']['ratings'],1)

    def test_response_ratings_do_not_double_count_dialogue_metrics(self):
        self.rate(share_for_improvement=True)
        response_id=main.sessions[self.sid]['turns'][-1]['id']
        self.client.put(self.path+'/responses/'+response_id+'/feedback',json={'rating':'up','share_for_improvement':True})
        report=feedback.report()
        self.assertEqual(report['all_ratings']['ratings'],2)
        self.assertEqual(report['dialogue_ratings']['ratings'],1)
        self.assertEqual(report['dialogue_ratings']['measured_turns'],1)
        self.assertEqual(report['response_ratings']['ratings'],1)

    def test_retry_resets_turn_measurements(self):
        self.assertEqual(len(main.sessions[self.sid]['turn_timings']),1)
        self.client.post(self.path+'/retry',json={'goal_id':'0'})
        self.assertEqual(main.sessions[self.sid]['turn_timings'],[])
