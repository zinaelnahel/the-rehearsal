"""Paid, bounded fictional regression for partner/learner role ownership.

No user sessions are accessed. Reports are synthetic model checks, not human reviews.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from backend import main as api
from backend.family_boundary import requester_speaks_as_learner, FAMILY_BOUNDARY
from backend.live import EvidenceReview, bind_assessments


def require(response):
    if response.status_code!=200:
        raise RuntimeError('Endpoint HTTP '+str(response.status_code))
    return response.json()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/family-role-evaluation.json')
    parser.add_argument('--english-repeats',type=int,choices=[1,2],default=2)
    args=parser.parse_args()
    report={'synthetic':True,'human_reviewed':False,'agent_enabled':True,'cases':[],'passed':False,
      'run_at_utc':datetime.now(timezone.utc).isoformat(),'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
      'source_sha256':{name:hashlib.sha256((ROOT/name).read_text(encoding='utf-8').encode()).hexdigest()
        for name in ('backend/live.py','backend/family_boundary.py','scripts/evaluate_family_roles.py')}}
    original=api.model
    captured={}
    def capture(schema,system,data,session=None):
        result=original(schema,system,data,session=session)
        if 'goal_assessments' in schema.model_fields:
            captured['proposed_reply']=bind_assessments(result,session['mission']).reply
        elif schema is EvidenceReview:
            captured['review']=result.model_dump()
        return result
    cases=[
      ('English','Everyday','I am sorry but i have some work to do ',"No, I cannot help this weekend."),
      ('English','Everyday','I am sorry but i have some work to do ',"No, I cannot help this weekend."),
      ('German','B1','Es tut mir leid, aber ich muss arbeiten.','Nein, ich kann dieses Wochenende nicht helfen.'),
      ('Spanish','B2','Lo siento, pero tengo trabajo.','No, no puedo ayudar este fin de semana.')]
    if args.english_repeats==1:cases.pop(1)
    before=len(api.model_calls)
    try:
      with patch.object(api,'LIVE',True),patch.object(api,'model',capture),patch.dict(os.environ,{
          'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'true'}),TestClient(api.app) as client:
        for language,level,soft,clear in cases:
          source=require(client.post('/api/sessions',json={'sample':'difficult','language':language}))
          sid=source['id'];path='/api/sessions/'+sid
          row={'language':language,'level':level,'turns':[]};report['cases'].append(row)
          try:
            mission=require(client.post(path+'/mission',json={'scenario':'difficult','language':language,
              'feedback_language':language,'level':level,'external_model_consent':True}))
            start=require(client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]}))
            assert start['turns'][0]['content']==FAMILY_BOUNDARY[language]['opening']
            for text in [soft,clear]:
              captured.clear()
              result=require(client.post(path+'/turn',json={'text':text}))
              delivered=result['turn']['content']
              assert not requester_speaks_as_learner(delivered,language),'Partner adopted learner refusal'
              assert not re.search(r'shopping|package|supermarket|grocer|einkauf|paket|compras|paquete',delivered,re.I),'Invented errand detail'
              row['turns'].append({'learner':text,'partner':delivered,'withheld':result['turn']['answer_withheld'],**captured})
            review=require(client.post(path+'/finish'))
            assert all(f['quote'] in soft or f['quote'] in clear for f in review['feedback'])
            row['passed']=True
            print(language+' '+level+': requester role and actual-turn review passed',flush=True)
          finally:
            assert require(client.delete(path))['deleted']
            assert client.get(path+'/status').status_code==404
        # The new mandatory role field must also work for a normal factual scene.
        source=require(client.post('/api/sessions',json={'sample':'apartment','language':'English'}))
        path='/api/sessions/'+source['id']
        try:
          mission=require(client.post(path+'/mission',json={'scenario':'apartment','language':'English',
            'feedback_language':'English','level':'Everyday','external_model_consent':True}))
          require(client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]}))
          result=require(client.post(path+'/turn',json={'text':'How much is the monthly rent?'}))
          assert '850' in result['turn']['content'] and result['turn']['sources']
          assert any(g['answer_status']=='confirmed' for g in result['goals'])
          report['rental_regression_passed']=True
        finally:
          assert require(client.delete(path))['deleted']
          assert client.get(path+'/status').status_code==404
        report['passed']=True
    except Exception as exc:
      report['error_type']=type(exc).__name__
      raise
    finally:
      report['provider_calls']=len(api.model_calls)-before
      args.output.parent.mkdir(parents=True,exist_ok=True)
      args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
      print('Synthetic report:',args.output)


if __name__=='__main__':main()
