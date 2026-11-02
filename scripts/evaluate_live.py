"""Real-provider smoke evaluation. Fictional data only; no keys in reports."""
import json
import time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
from backend.main import app,model_calls,model as original_model
from backend.live import RoleReply, bind_assessments

cases={
 'English':{'negation':'I am not going to ask whether internet is included.','question':'Is internet included in the rent?','followup':'And when could I move in?','phrase':'Können wir nächsten Donnerstag am Nachmittag besichtigen?','translation_word':'thursday'},
 'German':{'negation':'Ich werde nicht fragen, ob Internet enthalten ist.','question':'Ist Internet in der Miete enthalten?','followup':'Und ab wann könnte ich einziehen?','phrase':'Could we arrange a viewing next Thursday afternoon?','translation_word':'donnerstag'},
 'Spanish':{'negation':'No voy a preguntar si internet está incluido.','question':'¿Está incluido internet en el alquiler?','followup':'¿Y cuándo podría entrar?','phrase':'Could we arrange a viewing next Thursday afternoon?','translation_word':'jueves'}
}
report={'provider_calls':True,'cases':[],'passed':False}
def traced_model(schema,system,data,session=None):
 result=original_model(schema,system,data,session=session)
 if schema is RoleReply or 'goal_assessments' in schema.model_fields:
  canonical=bind_assessments(result,session['mission'])
  report['last_proposal']={'reply':canonical.model_dump(),'retrieved_ids':[d['id'] for d in data['retrieved_passages']]}
 return result
def require(response):
 if response.status_code!=200:
  raise AssertionError('Endpoint failed with '+str(response.status_code)+': '+str(response.json().get('detail','')))
 return response.json()

if __name__=='__main__':
 Path('.runtime').mkdir(exist_ok=True)
 try:
  with patch('backend.main.LIVE',True),patch('backend.main.model',traced_model),patch.dict('os.environ',{'API_PROXY_TOKEN':''}),TestClient(app) as client:
   for language,case in cases.items():
    started=time.monotonic()
    row={'language':language,'checks':[],'turns':[]}
    report['cases'].append(row)
    session=require(client.post('/api/sessions',json={'text':'Fictional flat listing.\nMonthly rent is 1375 euros.\nThe flat is available from 15 December.\nUtilities and internet are included in the rent.\nNo pet policy is specified.'}))
    path='/api/sessions/'+session['id']
    try:
     mission=require(client.post(path+'/mission',json={'scenario':'apartment','goal':'Ask whether internet is included and when I can move in.','language':language,'feedback_language':'English','level':'B1','external_model_consent':True}))
     assert len(mission['goals']) in range(1,6)
     require(client.post(path+'/start',json={'goals':['Ask whether internet is included in rent','Ask when I can move in']}))
     data=require(client.post(path+'/turn',json={'text':case['negation']}))
     assert not data['goals'][0]['achieved'],'Negated goal was incorrectly marked achieved'
     row['checks'].append('negated custom goal rejected')
     print(language,': negation PASS',flush=True)
     for question in (case['question'],case['followup']):
      data=require(client.post(path+'/turn',json={'text':question}))
      row['turns'].append({'learner':question,'reply':data['turn']['content'],'sources':data['turn']['sources'],'goals':data['goals']})
     assert data['goals'][0]['achieved'],'Custom internet question not assessed'
     assert data['goals'][0]['answer_status']=='confirmed','Supported custom answer not verified'
     assert data['goals'][1]['achieved'],'Contextual availability follow-up not assessed'
     assert '15' in data['turn']['content'],'Available date missing from contextual follow-up'
     row['checks']+=['custom goal detected with source support','contextual follow-up answered']
     print(language,': custom goal + follow-up PASS',flush=True)
     hint=require(client.post(path+'/hint',json={'kind':'translation','text':case['phrase']}))
     assert case['phrase'] in hint['text']
     assert case['translation_word'] in hint['text'].lower(),'Translation did not address supplied phrase'
     row['translation']=hint['text']
     row['checks'].append('actual phrase translated')
     debrief=require(client.post(path+'/finish'))
     assert debrief['phrases']
     assert all(f['quote'] in ' '.join([case['negation'],case['question'],case['followup']]) for f in debrief['feedback'])
     row['debrief']=debrief
     require(client.post(path+'/retry',json={'goal_id':'0'}))
     row['checks']+=['debrief quotes checked','targeted retry available']
    finally:
     assert require(client.delete(path))['deleted']
     assert client.get(path+'/status').status_code==404
    row['checks'].append('server deletion verified')
    row['seconds']=round(time.monotonic()-started,1)
    print(language,': translation, debrief, replay, deletion PASS',flush=True)
   report['passed']=True
 except Exception as exc:
  report['error']=str(exc)[:500]
  print('LIVE EVALUATION FAILED:',type(exc).__name__,str(exc)[:300],flush=True)
 finally:
  report['model_call_count']=len(model_calls)
  Path('.runtime/live-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print('Real-provider evaluation:', 'PASS' if report['passed'] else 'FAIL','calls:',len(model_calls),flush=True)
 if not report['passed']: raise SystemExit(1)
