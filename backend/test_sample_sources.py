"""Real sample assets must remain inspectable and grounded in original pages."""
import hashlib
import json
import os
import io
import wave
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.live import RoleReply, EvidenceReview
from backend.family_boundary import FAMILY_PACING, FAMILY_ALTERNATIVE, requester_speaks_as_learner, family_action_observations, FAMILY_BOUNDARY, family_response_stage, recorded_time_reply
from backend import main
from backend.sample_sources import CATALOG, SAMPLES, sample_documents


class RealSampleTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false'}))
  self.enterContext(patch.object(main,'LIVE',False))
  self.enterContext(patch.object(main.abuse,'admit',return_value=True))
  self.client=self.enterContext(TestClient(main.app))
  main.sessions.clear()

 def source(self,sample='interview',language='English'):
  response=self.client.post('/api/sessions',json={'sample':sample,'language':language})
  self.assertEqual(response.status_code,200,response.text)
  return response.json()

 def start(self,sid,scenario='interview'):
  path='/api/sessions/'+sid
  response=self.client.post(path+'/mission',json={'scenario':scenario,'language':'English','feedback_language':'English'})
  self.assertEqual(response.status_code,200,response.text)
  response=self.client.post(path+'/start',json={'goals':[g['text'] for g in response.json()['goals']]})
  self.assertEqual(response.status_code,200,response.text)
  return path

 def test_prepared_video_requires_review_and_edits_drop_timestamps(self):
  data=json.loads((SAMPLES/CATALOG['video']['transcript']).read_text(encoding='utf-8'))
  text='\n\n'.join(part['text'] for part in data['segments'])
  request={'sample_video_text':text}
  self.assertEqual(self.client.post('/api/sessions',json=request).status_code,409)
  for edited in (False,True):
   response=self.client.post('/api/sessions',json={**request,'sample_video_text':text+(' Corrected wording.' if edited else ''),'transcript_confirmed':True})
   self.assertEqual(response.status_code,200,response.text)
   session=main.sessions[response.json()['id']]
   self.assertTrue(session['sample_video'])
   self.assertEqual(session['source_kind'],'text' if edited else 'transcript')
   self.assertEqual(any('start' in d.metadata for d in session['source_documents']),not edited)
   self.assertEqual(next(iter(session['source_chunks'].values())).metadata['url'],data['source_url'])

 def test_real_pdfs_preserve_provenance_and_original_bytes(self):
  for sample in ('interview',):
   with self.subTest(sample=sample):
    result=self.source(sample)
    item=CATALOG[sample]
    session=main.sessions[result['id']]
    self.assertEqual(session['source_kind'],'pdf')
    self.assertEqual(len(session['source_documents']),item['pages'])
    self.assertEqual(result['sample_provenance'],item)
    original=self.client.get(result['original_pdf_url'])
    self.assertEqual(original.headers['content-type'],'application/pdf')
    self.assertEqual(original.content,(SAMPLES/'documents'/item['filename']).read_bytes())
    self.assertTrue(original.content.startswith(b'%PDF-'))
    self.assertNotIn('fictional sample',result['name'])

 def test_language_selection_never_replaces_original_with_fiction(self):
  texts=[]
  for language in ('English','German','Spanish'):
   result=self.source(language=language)
   texts.append([d.page_content for d in main.sessions[result['id']]['source_documents']])
  self.assertEqual(texts[0],texts[1])
  self.assertEqual(texts[0],texts[2])
  self.assertIn('zvoove',texts[0][0])

 def test_job_pdf_preserves_new_role_and_page_evidence(self):
  result=self.source()
  session=main.sessions[result['id']]
  text='\n'.join(d.page_content for d in session['source_documents'])
  for value in ('QA Automation Engineer','Payroll','CI/CD','München','Mandatory: AI-first test data management','Payroll knowledge is not required'):
   self.assertIn(value,text)
  for retired in ('Celonis','DACH','12 meses','RAG'):
   self.assertNotIn(retired,text)
  self.assertFalse(session['sample_video'])
  doc=next(d for d in session['source_chunks'].values() if 'Mandatory: AI-first test data management' in d.page_content)
  inspected=self.client.get('/api/sessions/'+result['id']+'/source/'+doc.metadata['id']).json()
  self.assertEqual(inspected['original_pdf_url'],'/api/samples/interview/document')
  self.assertIsNone(inspected['original_audio_url'])

 def test_manual_job_transcription_is_bound_to_original_pdf(self):
  data=json.loads((SAMPLES/'documents'/CATALOG['interview']['transcription']).read_text(encoding='utf-8'))
  raw,docs=sample_documents('interview')
  self.assertEqual(data['pdf_sha256'],hashlib.sha256(raw).hexdigest())
  self.assertEqual(len(docs),3)
  with patch('backend.sample_sources.hashlib.sha256') as digest:
   digest.return_value.hexdigest.return_value='changed'
   with self.assertRaisesRegex(ValueError,'does not match'):
    sample_documents('interview')

 def test_job_requirement_questions_retrieve_explicit_test_data_requirement(self):
  source=self.source()
  state=main.sessions[source['id']]
  state['setup']={'scenario':'interview'}
  documents=main.search(state,'What is mandatory for AI-first test data management?')
  self.assertLessEqual(len(documents),6)
  self.assertIn('Mandatory: AI-first test data management',' '.join(d.page_content for d in documents))

 def test_remote_questions_retrieve_both_location_and_hybrid_policy(self):
  source=self.source()
  state=main.sessions[source['id']]
  state['setup']={'scenario':'interview'}
  for question in ('Yes, can I work remotely for this position?',
   'Is this role hybrid?', 'Kann ich im Homeoffice arbeiten?',
   'Kann ich von zu Hause arbeiten?', 'Puedo trabajar en remoto?',
   'Puedo teletrabajar?'):
   with self.subTest(question=question):
    documents=main.search(state,question)
    self.assertLessEqual(len(documents),6)
    text=' '.join(d.page_content for d in documents)
    self.assertIn('Remote, DE',text)
    self.assertIn('hybrid work concept',text)

 def test_apartment_sample_cannot_silently_use_a_retired_listing(self):
  self.assertEqual(self.client.post('/api/sessions',json={'sample':'apartment'}).status_code,409)
  self.assertEqual(self.client.get('/api/samples/apartment/document').status_code,404)
  data=json.loads((SAMPLES/CATALOG['video']['transcript']).read_text(encoding='utf-8'))
  source=self.client.post('/api/sessions',json={'sample_video_text':'\n'.join(p['text'] for p in data['segments']),'transcript_confirmed':True}).json()
  state=main.sessions[source['id']]
  self.assertEqual(state['source_kind'],'transcript')
  self.assertTrue(state['sample_video'])
  self.assertNotIn('sample_provenance',state)
  self.assertEqual(source['source_url'],'https://www.youtube.com/watch?v=8YsZZpFW_QU')
  chunks=list(state['source_chunks'].values())
  self.assertTrue(any('vallecas' in d.page_content.lower() for d in chunks))
  self.assertTrue(any('latina' in d.page_content.lower() for d in chunks))
  self.assertTrue(all('start' in d.metadata for d in chunks))

 def test_personal_sample_keeps_fictional_notes(self):
  result=self.source('difficult')
  self.assertIn('fictional sample',result['name'])
  self.assertNotIn('sample_provenance',result)
  self.assertEqual(main.sessions[result['id']]['source_kind'],'text')

 def test_audio_sample_plays_without_speech_provider_and_requires_review(self):
  with patch('backend.main.speech.speech_client',side_effect=AssertionError('Playback must not call OpenAI')):
   audio=self.client.get('/api/samples/difficult/audio')
  self.assertEqual(audio.status_code,200)
  self.assertEqual(audio.headers['content-type'],'audio/wav')
  with wave.open(io.BytesIO(audio.content)) as wav:
   self.assertGreater(wav.getnframes()/wav.getframerate(),10)
   self.assertLess(wav.getnframes()/wav.getframerate(),120)
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(turn['speaker']+': '+turn['text'] for turn in script['turns'])
  request={'sample':'difficult','sample_audio_text':text,'language':'Spanish'}
  self.assertEqual(self.client.post('/api/sessions',json=request).status_code,409)
  response=self.client.post('/api/sessions',json={**request,'transcript_confirmed':True})
  self.assertEqual(response.status_code,200,response.text)
  data=response.json()
  self.assertEqual(data['import_method'],'reviewed_sample_audio')
  session=main.sessions[data['id']]
  self.assertTrue(session['sample_audio'])
  self.assertTrue(session['sample_audio_timed'])
  for turn in script['turns']:self.assertIn(turn['text'],'\n'.join(d.page_content for d in session['source_documents']))
  self.start(data['id'],'difficult')
  self.assertTrue(session['family_boundary'])
  self.assertEqual(session['source_kind'],'transcript')

 def test_audio_review_rejects_mixed_sources_and_empty_text(self):
  request={'sample':'difficult','sample_audio_text':'Reviewed script.','transcript_confirmed':True}
  for extra in ({'sample':'apartment'},{'text':'Other source'},{'sample_audio_text':' '},{'video_url':CATALOG['video']['source_url']}):
   self.assertEqual(self.client.post('/api/sessions',json={**request,**extra}).status_code,400)
  self.assertEqual(self.client.get('/api/samples/apartment/audio').status_code,404)

 def test_audio_example_cannot_reverse_boundary_or_hide_elliptical_refusal(self):
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(t['speaker']+': '+t['text'] for t in script['turns'])
  source=self.client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':text,'transcript_confirmed':True}).json()
  sid=source['id'];path='/api/sessions/'+sid
  mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':'Spanish','feedback_language':'English'}).json()
  self.client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
  doc=next(iter(main.sessions[sid]['source_chunks'].values()))
  bad='Entiendo que tienes trabajo y no puedes ayudar este fin de semana. Te agradecería que me avisaras antes de hacer planes que dependan de tu tiempo para evitar inconvenientes.'
  proposal=RoleReply(reply=bad,citations=[doc.metadata['id']],goal_checks=[],answer_checks=[])
  # Even an overpermissive reviewer and a real citation must not license this.
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.object(main,'LIVE',True),patch.object(main,'search',return_value=[doc]),patch.object(main,'model',side_effect=[proposal,review]*2):
   result=self.client.post(path+'/turn',json={'text':'no puedo tengo trabajo'}).json()
   self.assertEqual(result['turn']['content'],FAMILY_PACING['Spanish']['gentle_followup'])
   self.assertEqual(result['turn']['sources'],[])
   self.assertEqual([g['achieved'] for g in result['goals']],[True,False,False])
   self.assertEqual(result['goals'][0]['evidence'],'no puedo tengo trabajo')
   self.assertEqual(result['goals'][0]['answer_status'],'not_applicable')
   result=self.client.post(path+'/turn',json={'text':'No puedo.'}).json()
   self.assertEqual(result['turn']['content'],FAMILY_PACING['Spanish']['accept'])
   self.assertEqual([g['achieved'] for g in result['goals']],[True,False,True])

 def test_notice_ownership_and_refusal_do_not_accept_unspoken_boundaries(self):
  for text in ('Te agradecería que me avisaras antes de hacer planes.', 'Quisiera que me avisases con antelación.'):
   self.assertTrue(requester_speaks_as_learner(text,'Spanish'))
  self.assertFalse(requester_speaks_as_learner('La próxima vez te preguntaré antes de hacer planes con tu tiempo.','Spanish'))
  session={'family_boundary':True,'setup':{'language':'Spanish','feedback_language':'English'},'mission':[{'id':str(i),'text':t} for i,t in enumerate(FAMILY_BOUNDARY['English']['goals'])],'turns':[]}
  for text in ('No puedo.','no puedo tengo trabajo','No puedo, tengo que trabajar.','no perdon tengo trabajo','No, perdón, tengo trabajo.'):
   self.assertEqual(set(family_action_observations(session,text)),{'0'})
  for text in ('No puedo decir que no.','¿No puedo ayudar?','No puedo traducir esta frase.'):
   self.assertEqual(family_action_observations(session,text),{})

 def test_audio_reply_follows_volunteered_next_week_offer_without_false_warning(self):
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(t['speaker']+': '+t['text'] for t in script['turns'])
  sid=self.client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':text,'transcript_confirmed':True}).json()['id']
  path='/api/sessions/'+sid
  mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':'Spanish','feedback_language':'English'}).json()
  self.client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
  doc=next(iter(main.sessions[sid]['source_chunks'].values()))
  proposal=RoleReply(reply='Entiendo que tienes trabajo. Gracias por decírmelo. ['+doc.metadata['id']+']',citations=[doc.metadata['id']],goal_checks=[],answer_checks=[])
  allowed=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  rejected=EvidenceReview(partner_role_consistent=False,reply_supported=False,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.object(main,'LIVE',True),patch.object(main,'search',return_value=[doc]),patch.object(main,'model',side_effect=[proposal,allowed,proposal,rejected,proposal,allowed]):
   first=self.client.post(path+'/turn',json={'text':'no perdon tengo trabajo'}).json()
   self.assertEqual(first['turn']['sources'],[])
   self.assertEqual(first['turn']['content'],FAMILY_PACING['Spanish']['gentle_followup'])
   self.assertTrue(first['goals'][0]['achieved'])
   offer='que piensas de la semana proxima ? tengo tiempo'
   second=self.client.post(path+'/turn',json={'text':offer}).json()
   self.assertEqual(second['turn']['content'],FAMILY_ALTERNATIVE['Spanish'])
   self.assertEqual(second['turn']['sources'],[])
   self.assertFalse(second['turn']['answer_withheld'])
   self.assertEqual([g['achieved'] for g in second['goals']],[True,False,False])
   third=self.client.post(path+'/turn',json={'text':'Gracias.'}).json()
   self.assertEqual(third['turn']['sources'],[])
   self.assertNotIn('[',third['turn']['content'])

 def test_next_week_offers_are_distinct_from_unavailability(self):
  cases=[('Spanish','que piensas de la semana proxima ? tengo tiempo','La próxima semana no tengo tiempo.'),
         ('English','I have time next week.','I have no time next week.'),
         ('German','Nächste Woche habe ich Zeit.','Nächste Woche habe ich keine Zeit.')]
  for language,available,unavailable in cases:
   session={'setup':{'language':language},'turns':[]}
   self.assertEqual(family_response_stage(session,available),'alternative_offer')
   self.assertNotEqual(family_response_stage(session,unavailable),'alternative_offer')

 def test_voice_message_facts_have_real_playable_citations(self):
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(t['speaker']+': '+t['text'] for t in script['turns'])
  sid=self.client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':text,'transcript_confirmed':True}).json()['id']
  path=self.start(sid,'difficult')
  session=main.sessions[sid]
  self.assertTrue(session['turns'][0]['sources'])
  doc=session['transcript_chunks'][0]
  proposal=RoleReply(reply='The move is on Saturday, from ten to one.',citations=[doc.metadata['id']],goal_checks=[],answer_checks=[])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.object(main,'LIVE',True),patch.object(main,'search',return_value=[doc]),patch.object(main,'model',side_effect=[proposal,review]):
   response=self.client.post(path+'/turn',json={'text':'What time is the move?'})
  self.assertEqual(response.status_code,200,response.text)
  turn=response.json()['turn']
  self.assertEqual(len(turn['sources']),1)
  source=turn['sources'][0]
  self.assertEqual(source['start'],script['turns'][0]['start'])
  self.assertEqual(source['end'],script['turns'][0]['end'])
  self.assertEqual(source['url'],'/api/samples/difficult/audio')
  inspected=self.client.get(path+'/source/'+source['id']).json()
  self.assertEqual(inspected['original_audio_url'],source['url'])
  self.assertTrue(inspected['audio_timed'])
  self.assertIn(source['text'],inspected['sections'][0]['text'])
  with wave.open(str(SAMPLES/'audio/family-boundary.es.wav')) as audio:
   duration=audio.getnframes()/audio.getframerate()
  previous=0
  for part in script['turns']:
   self.assertGreaterEqual(part['start'],previous)
   self.assertGreater(part['end'],part['start'])
   self.assertLessEqual(part['end'],duration)
   previous=part['end']

 def test_edited_voice_message_never_inherits_audio_timestamps(self):
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(t['speaker']+': '+t['text'] for t in script['turns']).replace('coche','camión')
  sid=self.client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':text,'transcript_confirmed':True}).json()['id']
  session=main.sessions[sid]
  self.assertFalse(session['sample_audio_timed'])
  for part in session['source_chunks'].values():
   source=main.evidence(part)
   self.assertNotIn('start',source)
   self.assertNotIn('end',source)
   inspected=self.client.get('/api/sessions/'+sid+'/source/'+source['id']).json()
   self.assertFalse(inspected['audio_timed'])

 def test_short_time_question_after_refusal_answers_recording_not_previous_goal(self):
  script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
  text='\n'.join(t['speaker']+': '+t['text'] for t in script['turns'])
  sid=self.client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':text,'transcript_confirmed':True}).json()['id']
  path='/api/sessions/'+sid
  mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':'Spanish','feedback_language':'English'}).json()
  self.client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
  proposal=RoleReply(reply='Entiendo.',citations=[],goal_checks=[],answer_checks=[])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.object(main,'LIVE',True),patch.object(main,'model',side_effect=[proposal,review]) as model:
   self.client.post(path+'/turn',json={'text':'no puedo tengo trabajo'})
   for question in ('a que hora ?','¿A qué hora?','a que hora'):
    response=self.client.post(path+'/turn',json={'text':question})
    self.assertEqual(response.status_code,200,response.text)
    result=response.json()
    self.assertIn('de diez a una',result['turn']['content'])
    self.assertFalse(result['turn']['answer_withheld'])
    self.assertEqual(result['turn']['sources'][0]['start'],script['turns'][0]['start'])
    self.assertEqual([g['achieved'] for g in result['goals']],[True,False,False])
   self.assertEqual(model.call_count,2)
  session=main.sessions[sid]
  for question in ('¿A qué hora tengo trabajo?','¿A qué hora la próxima semana?','¿A qué hora el domingo?'):
   self.assertIsNone(recorded_time_reply(session,question))
  session['turns']=[{'role':'user','content':'La próxima semana puedo ayudar, tengo tiempo.'},{'role':'assistant','content':'¿Qué día de la próxima semana te vendría bien?'}]
  self.assertIsNone(recorded_time_reply(session,'¿A qué hora?'))

 def test_no_arbitrary_file_or_video_is_served_as_a_pdf(self):
  for key in ('video','unknown','catalog'):
   self.assertEqual(self.client.get('/api/samples/'+key+'/document').status_code,404)

 def test_video_requires_review_and_marks_both_caption_and_paste_paths(self):
  url=CATALOG['video']['source_url']
  for payload in ({'transcript_text':'Synthetic interview example.'},
                  {'transcript':[{'start':0,'end':4,'text':'Synthetic interview example.'}]}):
   with self.subTest(payload=payload):
    request={**payload,'video_url':url}
    self.assertEqual(self.client.post('/api/sessions',json=request).status_code,409)
    response=self.client.post('/api/sessions',json={**request,'transcript_confirmed':True})
    self.assertEqual(response.status_code,200,response.text)
    self.assertTrue(main.sessions[response.json()['id']]['sample_video'])
