"""Real-provider regression: fresh default missions, rent turns and actual-turn review.

Uses only built-in fictional samples. Never reads or retains a real user session.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
from backend.main import app, model as original_model, model_calls
from backend.live import bind_assessments

QUERIES={
 'English':['How much is the rent?','how much it costs','How much does the apartment cost per month?'],
 'German':['Wie hoch ist die Miete?'],
 'Spanish':['¿Cuánto cuesta el alquiler?']
}
FOLLOWUPS={
 'English':'When is the apartment available?',
 'German':'Ab wann ist die Wohnung verfügbar?',
 'Spanish':'¿Cuándo está disponible el piso?'
}

def run(repetitions=2):
 report={'synthetic':True,'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'passed':False,'cases':[]}
 active={}
 def traced(schema,system,data,session=None):
  result=original_model(schema,system,data,session=session)
  if 'goal_assessments' in schema.model_fields:
   active.setdefault('assessments',[]).append(bind_assessments(result,session['mission']).model_dump())
  return result
 def require(response):
  if response.status_code!=200: raise AssertionError(f'HTTP {response.status_code}: '+str(response.json().get('detail','')))
  return response.json()
 def check_turn(data,question):
  assert not data['turn'].get('answer_withheld'),'Ordinary source-backed answer was withheld'
  assert '850' in data['turn']['content'],'Monthly rent missing from partner reply'
  assert data['turn']['sources'],'Rent reply lacks source evidence'
  rent=[g for g in data['goals'] if g['achieved'] and g['evidence'] in question and g['answer_status']=='confirmed' and '850' in g['answer_evidence']]
  assert rent,'Rent question did not produce source-confirmed goal progress'
  return rent[0]
 try:
  with patch('backend.main.LIVE',True),patch('backend.main.model',traced),patch.dict(os.environ,{'API_PROXY_TOKEN':''}),TestClient(app) as client:
   for language,questions in QUERIES.items():
    for repeat in range(repetitions if language=='English' else 1):
     for question in questions:
      started=time.monotonic()
      active={'language':language,'repetition':repeat+1,'question':question,'turns':[]}
      report['cases'].append(active)
      source=require(client.post('/api/sessions',json={'sample':'apartment','language':language}))
      path='/api/sessions/'+source['id']
      try:
       # Keep the actual generated three-goal mission; do not replace it with
       # the hand-edited goals used by the earlier multilingual smoke check.
       mission=require(client.post(path+'/mission',json={'scenario':'apartment','goal':'Feel confident asking about the details before making a decision.','language':language,'feedback_language':'English','level':'Everyday','external_model_consent':True}))
       active['mission']=mission['goals']
       assert len(mission['goals'])==3,'Default mission should contain three goals'
       require(client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]}))
       data=require(client.post(path+'/turn',json={'text':question}))
       active['turns'].append({'user':question,**data})
       rent_goal=check_turn(data,question)
       learner=[question]
       if question==questions[0] and repeat==0:
        followup=FOLLOWUPS[language]
        data=require(client.post(path+'/turn',json={'text':followup}))
        assert not data['turn'].get('answer_withheld'),'Availability answer was withheld'
        assert '1' in data['turn']['content'],'Available date missing'
        assert any(g['achieved'] and g['evidence'] in followup and g['answer_status']=='confirmed' for g in data['goals']),'Follow-up goal did not progress'
        active['turns'].append({'user':followup,**data})
        learner.append(followup)
       review=require(client.post(path+'/finish'))
       active['review']=review
       assert review['feedback'],'Review supplied no feedback on actual user turns'
       assert all(any(note['quote'] in turn for turn in learner) for note in review['feedback']),'Review invented a user quotation'
       assert any(g['achieved'] and '850' in g['answer_evidence'] for g in review['goals']),'Rent progress disappeared in review'
       if language=='English' and repeat==0 and question==questions[0]:
        require(client.post(path+'/retry',json={'goal_id':rent_goal['id']}))
        replay=require(client.post(path+'/turn',json={'text':question}))
        check_turn(replay,question)
        assert len(replay['goals'])==1 and replay['goals'][0]['id']==rent_goal['id'],'Replay changed goal identity'
        active['replay']=replay
       active['passed']=True
       print(f'PASS: {language} / {question} / fresh run {repeat+1}: reply, evidence, goals, actual-turn review',flush=True)
      finally:
       require(client.delete(path))
       assert client.get(path+'/status').status_code==404
      active['seconds']=round(time.monotonic()-started,1)
   report['passed']=True
 except Exception as error:
  report['error']=str(error)
  print('FAIL:',str(error),flush=True)
 finally:
  report['provider_calls']=len(model_calls)
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--repetitions',type=int,choices=range(1,4),default=2)
 parser.add_argument('--report',type=Path,default=Path('.runtime/rent-flow-evaluation.json'))
 args=parser.parse_args()
 result=run(args.repetitions)
 args.report.parent.mkdir(parents=True,exist_ok=True)
 args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Rent-flow evaluation:', 'PASS' if result['passed'] else 'FAIL','calls:',result['provider_calls'],flush=True)
 raise SystemExit(0 if result['passed'] else 1)
