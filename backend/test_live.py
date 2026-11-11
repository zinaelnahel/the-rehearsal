"""Deterministic contract tests: no provider calls or real credentials."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app,sessions
from backend.live import RoleReply,GoalCheck,AnswerCheck,EvidenceReview,Translation,strict_schema,scene_reply_schema,bind_assessments,scene_review_schema,bind_review
from pydantic import ValidationError
from copy import deepcopy

class LiveTests(unittest.TestCase):
 def setUp(self):
  sessions.clear()
  env=patch.dict(os.environ,{'API_PROXY_TOKEN':'','REHEARSAL_AGENT_ENABLED':'false','VECTOR_STORE':'memory'})
  env.start();self.addCleanup(env.stop)
  self.client=self.enterContext(TestClient(app))
  with patch('backend.main.LIVE',False):
   self.sid=self.client.post('/api/sessions',json={'text':'Monthly rent is 1375 euros. Utilities are included.'}).json()['id']
   self.p='/api/sessions/'+self.sid
   self.client.post(self.p+'/mission',json={'scenario':'apartment','language':'English','feedback_language':'English','level':'Everyday'})
   self.client.post(self.p+'/start',json={'goals':['Ask whether utilities are included']})
  mode=patch('backend.main.LIVE',True)
  mode.start();self.addCleanup(mode.stop)

 def proposal(self,**kwargs):
  values=dict(reply='Utilities are included. [1]',citations=['1'],goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='Are utilities included?')],answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote='Utilities are included.')])
  values.update(kwargs)
  return RoleReply(**values)

 def test_live_mission_separates_feedback_and_conversation_languages(self):
  from backend.main import MissionOutput
  from backend.content import CONTENT
  for conversation in ('Spanish','German'):
   with self.subTest(conversation=conversation):
    with patch('backend.main.LIVE',False):
     sid=self.client.post('/api/sessions',json={'text':'Monthly rent is 850 euros.'}).json()['id']
    expected=CONTENT['apartment']['English']['goals']
    with patch('backend.main.model',return_value=MissionOutput(goals=expected)) as generate:
     response=self.client.post('/api/sessions/'+sid+'/mission',json={
      'scenario':'apartment','language':conversation,'feedback_language':'English',
      'external_model_consent':True})
    self.assertEqual(response.status_code,200,response.text)
    self.assertEqual([g['text'] for g in response.json()['goals']],expected)
    system=generate.call_args.args[1]
    self.assertIn('OUTPUT LANGUAGE: English',system)
    self.assertIn('Write EVERY goals item entirely in English',system)
    self.assertIn('The partner will speak '+conversation,system)
    self.assertEqual(generate.call_args.args[2]['suggested_goals'],expected)
    self.client.delete('/api/sessions/'+sid)

 def test_role_consistency_is_required_and_can_withhold_a_source_supported_reply(self):
  with self.assertRaises(ValidationError):
   EvidenceReview(reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  review=EvidenceReview(partner_role_consistent=False,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[self.proposal(),review]):
   result=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(result.status_code,200,result.text)
  self.assertTrue(result.json()['turn']['answer_withheld'])
  self.assertEqual(result.json()['turn']['sources'],[])
  self.assertNotEqual(result.json()['goals'][0]['answer_status'],'confirmed')

 def test_voice_skips_optional_planning_but_keeps_independent_evidence_review(self):
  review=EvidenceReview(partner_role_consistent=True,reply_supported=False,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.dict(os.environ,{'REHEARSAL_AGENT_ENABLED':'true'}), \
    patch('backend.main.prepare_agent') as planner, \
    patch('backend.main.model',side_effect=[self.proposal(),review]) as calls:
   response=self.client.post(self.p+'/turn',json={'text':'Are utilities included?','interaction_mode':'voice'})
  self.assertEqual(response.status_code,200,response.text)
  planner.assert_not_called()
  self.assertEqual(calls.call_count,2,'Proposal and independent review must both run')
  self.assertIn('one or two short natural sentences',calls.call_args_list[0].args[1])
  self.assertTrue(response.json()['turn']['answer_withheld'])
  self.assertEqual(response.json()['agent_tools'],[])
  self.assertNotEqual(response.json()['goals'][0]['answer_status'],'confirmed')

 def test_text_turn_keeps_optional_planner_and_normal_reply_prompt(self):
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  from backend.main import search
  docs=search(sessions[self.sid],'Are utilities included?')
  with patch.dict(os.environ,{'REHEARSAL_AGENT_ENABLED':'true'}), \
    patch('backend.main.prepare_agent',return_value=([],docs)) as planner, \
    patch('backend.main.model',side_effect=[self.proposal(),review]) as calls:
   response=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(response.status_code,200,response.text)
  planner.assert_called_once()
  self.assertEqual(calls.call_count,2)
  self.assertNotIn('one or two short natural sentences',calls.call_args_list[0].args[1])
  self.assertEqual(response.json()['goals'][0]['answer_status'],'confirmed')

 def test_short_followup_retrieves_the_previous_exchange(self):
  from backend.main import search
  sessions[self.sid]['turns'].extend([
   {'role':'user','content':'What does the rent include?','sources':[]},
   {'role':'assistant','content':'Would you like me to explain the utility bills?','sources':[]}])
  proposal=self.proposal(goal_checks=[],answer_checks=[])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,
   accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch('backend.main.search',wraps=search) as retrieve, \
    patch('backend.main.model',side_effect=[proposal,review]):
   response=self.client.post(self.p+'/turn',json={'text':'Yes, please.'})
  self.assertEqual(response.status_code,200,response.text)
  query=retrieve.call_args.args[1]
  self.assertIn('What does the rent include?',query)
  self.assertIn('explain the utility bills',query)
  self.assertTrue(query.endswith('Yes, please.'))

 def test_custom_goal_requires_exact_quote_and_verified_answer(self):
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[self.proposal(),review]):
   r=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(r.status_code,200,r.text)
  goal=r.json()['goals'][0]
  self.assertTrue(goal['achieved'])
  self.assertEqual(goal['evidence'],'Are utilities included?')
  self.assertEqual(goal['answer_status'],'confirmed')
  self.assertEqual(goal['answer_sources'],['1'])

 def test_interview_self_report_needs_no_document_evidence(self):
  sessions[self.sid]['setup']['scenario']='interview'
  sessions[self.sid]['mission'][0]['text']='Describe your relevant experience'
  text='I worked the past five years in QA.'
  proposal=self.proposal(reply='What kinds of testing did you do?',citations=[],
   goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=text)],
   answer_checks=[AnswerCheck(goal_id='0',status='not_document_question',source_id='',source_quote='')])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,
   accepted_goal_ids=['0'],verified_answer_goal_ids=[])
  with patch('backend.main.model',side_effect=[proposal,review]) as calls:
   response=self.client.post(self.p+'/turn',json={'text':text})
  self.assertEqual(response.status_code,200,response.text)
  result=response.json()
  self.assertEqual(result['turn']['content'],proposal.reply)
  self.assertFalse(result['turn'].get('answer_withheld',False))
  self.assertEqual(result['turn']['sources'],[])
  self.assertEqual(result['goals'][0]['answer_status'],'not_applicable')
  self.assertIn('Learner self-reports',calls.call_args_list[0].args[1])
  self.assertIn('acknowledged as self-reports',calls.call_args_list[1].args[1])

 def test_missing_policy_stays_unknown_even_when_both_models_verify_it(self):
  from langchain_core.documents import Document
  variants=['The pet policy is not specified.', 'Die Haustierregelung ist nicht angegeben.',
            'La politica de mascotas no se especifica.']
  for source in variants:
   with self.subTest(source=source):
    sessions[self.sid]['phase']='chat'
    sessions[self.sid]['mission'][0]['text']='Ask whether pets are allowed'
    proposal=self.proposal(reply='The document does not specify whether pets are allowed. [1]',
     goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='Are pets allowed?')],
     answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote=source)])
    review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
    doc=Document(page_content=source,metadata={'id':'1','location':'Section 1','source':'Synthetic policy'})
    with patch('backend.main.search',return_value=[doc]),patch('backend.main.model',side_effect=[proposal,review]):
     response=self.client.post(self.p+'/turn',json={'text':'Are pets allowed?'})
    self.assertEqual(response.status_code,200,response.text)
    goal=response.json()['goals'][0]
    self.assertTrue(goal['achieved'])
    self.assertEqual(goal['answer_status'],'unknown')
    notes=scene_review_schema(len([t for t in sessions[self.sid]['turns'] if t['role']=='user'])).model_validate(
     {'review_assessments':{},'feedback':[{'learner_turn_id':'turn_0','suggestion':'','explanation':'Clear question.'}],
      'unanswered':[],'phrases':['Are pets allowed?'],'note':'Review.'})
    with patch('backend.main.search',return_value=[doc]),patch('backend.main.model',return_value=notes):
     debrief=self.client.post(self.p+'/finish').json()
    self.assertEqual(debrief['goals'][0]['answer_status'],'unknown')
    self.assertIn('Ask whether pets are allowed',debrief['unanswered'])

 def test_explicit_pet_question_survives_missed_assessments_and_replay(self):
  sessions[self.sid]['mission'][0]['text']='Ask whether pets are allowed'
  proposal=self.proposal(reply='I cannot confirm the pet policy.',citations=[],
   goal_checks=[GoalCheck(goal_id='0',achieved=False,learner_quote='')],
   answer_checks=[])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=False,
   accepted_goal_ids=[],verified_answer_goal_ids=[])
  for replay in (False,True):
   if replay:
    sessions[self.sid]['phase']='debrief'
    replay_response=self.client.post(self.p+'/retry',json={'goal_id':'0'})
    self.assertEqual(replay_response.status_code,200,replay_response.text)
   with patch('backend.main.model',side_effect=[proposal,review]):
    response=self.client.post(self.p+'/turn',json={'text':'Are pets allowed?'})
   self.assertEqual(response.status_code,200,response.text)
   goal=response.json()['goals'][0]
   self.assertTrue(goal['achieved'])
   self.assertEqual(goal['evidence'],'Are pets allowed?')
   self.assertEqual(goal['answer_status'],'unverified')
   self.assertEqual(goal['answer_sources'],[])

 def test_explicit_pet_question_is_not_keyword_matching(self):
  from backend.live import explicit_pet_question
  for text in ['Pets.', 'I will not ask whether pets are allowed.',
               'You asked: Are pets allowed?', 'Pets are allowed.']:
   self.assertFalse(explicit_pet_question(text,'Ask whether pets are allowed'))
  self.assertFalse(explicit_pet_question('Are pets allowed?',
   'Ask whether pets are allowed and negotiate the deposit'))
  for text in ['Are pets allowed?', 'Sind Haustiere erlaubt?', '¿Se permiten mascotas?']:
   self.assertTrue(explicit_pet_question(text,'Ask whether pets are allowed'))

 def test_conflicting_rent_cannot_be_confirmed_by_two_approving_models(self):
  from langchain_core.documents import Document
  source=[Document(page_content=f'Monthly rent is {value} euros.',metadata={
   'id':str(i+1),'location':f'Section {i+1}','source':'Fictional conflicting listing'})
   for i,value in enumerate((1375,1490))]
  sessions[self.sid]['mission'][0]['text']='Ask about monthly rent'
  proposal=self.proposal(reply='The monthly rent is 1375 euros. [1]',
   goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='What is the monthly rent?')],
   answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote=source[0].page_content)])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.search',return_value=source),patch('backend.main.model',side_effect=[proposal,review]):
   response=self.client.post(self.p+'/turn',json={'text':'What is the monthly rent?'})
  self.assertEqual(response.status_code,200,response.text)
  result=response.json()
  self.assertTrue(result['goals'][0]['achieved'])
  self.assertEqual(result['goals'][0]['answer_status'],'unknown')
  self.assertTrue(result['turn']['answer_withheld'])
  self.assertNotIn('1375',result['turn']['content'])
  self.assertEqual(len(result['turn']['sources']),2)

 def test_known_prohibition_is_not_a_missing_policy(self):
  from backend.live import missing_source_answer
  from langchain_core.documents import Document
  for source in ['Pets are not allowed.', 'Haustiere sind nicht erlaubt.', 'No se admiten mascotas.']:
   answer=AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote=source)
   self.assertFalse(missing_source_answer(answer,[Document(page_content=source,metadata={'id':'1'})]))

 def test_missing_policy_backstop_uses_quoted_sentence_not_unrelated_missing_facts(self):
  from backend.live import missing_source_answer
  from langchain_core.documents import Document
  doc=Document(page_content='Rent is 850 euros. The pet policy is not specified.',metadata={'id':'1'})
  def answer(quote): return AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote=quote)
  self.assertTrue(missing_source_answer(answer('pet policy'),[doc]))
  self.assertFalse(missing_source_answer(answer('Rent is 850 euros.'),[doc]))

 def test_reject_fabricated_learner_quote_without_saving(self):
  bad=[self.proposal(goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='This was never said')])]
  for output in bad:
   with patch('backend.main.model',return_value=output):
    r=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
   self.assertEqual(r.status_code,502,r.text)
   self.assertEqual(len(sessions[self.sid]['turns']),1)
   self.assertFalse(sessions[self.sid]['mission'][0]['achieved'])

 def test_invalid_answer_quote_becomes_unknown_without_blocking_valid_question(self):
  questions={'English':'When can I move into the apartment?',
   'German':'Wann kann ich in die Wohnung einziehen?',
   'Spanish':'¿Cuándo puedo mudarme al apartamento?'}
  invalid=[('1','Pets are always allowed.',['1']),
   ('1','Utilities are included.',[]),('missing','Move in next month.',['1']),
   ('1','',['1'])]
  for language,text in questions.items():
   for source_id,quote,citations in invalid:
    with self.subTest(language=language,quote=quote):
     sessions[self.sid]['setup']['language']=language
     sessions[self.sid]['mission'][0]['text']='Ask when the apartment is available'
     proposal=self.proposal(reply='Move in next month.',citations=citations,
      goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=text)],
      answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id=source_id,source_quote=quote)])
     review=EvidenceReview(partner_role_consistent=True,reply_supported=True,
      accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
     with patch('backend.main.model',side_effect=[proposal,review]):
      response=self.client.post(self.p+'/turn',json={'text':text})
     self.assertEqual(response.status_code,200,response.text)
     data=response.json()
     self.assertTrue(data['turn']['answer_withheld'])
     self.assertNotIn('Move in next month',data['turn']['content'])
     for jargon in ('document','Dokument','documento','other person','otra persona'):
      self.assertNotIn(jargon,data['turn']['content'])
     self.assertEqual(data['turn']['sources'],[])
     self.assertTrue(data['goals'][0]['achieved'])
     self.assertEqual(data['goals'][0]['evidence'],text)
     self.assertEqual(data['goals'][0]['answer_status'],'unknown')
     self.assertEqual(data['goals'][0]['answer_sources'],[])

 def test_withhold_unsupported_reply_without_confirming_answer(self):
  review=EvidenceReview(partner_role_consistent=True,reply_supported=False,accepted_goal_ids=['0'],verified_answer_goal_ids=[])
  with patch('backend.main.model',side_effect=[self.proposal(reply='Utilities are included and you can have a free garage.'),review]):
   data=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'}).json()
  self.assertNotIn('garage',data['turn']['content'])
  self.assertTrue(data['turn']['answer_withheld'])
  self.assertTrue(data['goals'][0]['achieved'])
  self.assertEqual(data['goals'][0]['answer_status'],'unverified')
  self.assertEqual(data['turn']['sources'],[])

 def test_semantic_review_can_reject_keyword_only_goal_match(self):
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  proposal=self.proposal(goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='I will not ask about utilities')])
  with patch('backend.main.model',side_effect=[proposal,review]):
   data=self.client.post(self.p+'/turn',json={'text':'I will not ask about utilities'}).json()
  self.assertFalse(data['goals'][0]['achieved'])

 def test_translation_uses_supplied_phrase_and_validates_original(self):
  original='Could we arrange a viewing on Thursday?'
  translated=Translation(original=original,translation='Könnten wir am Donnerstag eine Besichtigung vereinbaren?',explanation='A polite request.')
  with patch('backend.main.model',return_value=translated) as mock:
   r=self.client.post(self.p+'/hint',json={'kind':'translation','text':original})
   self.assertEqual(mock.call_args.args[2]['phrase'],original)
  self.assertIn('Donnerstag',r.json()['text'])
  count=len(sessions[self.sid]['hints'])
  with patch('backend.main.model',return_value=translated):
   r=self.client.post(self.p+'/hint',json={'kind':'translation','text':'Different phrase'})
  self.assertEqual(r.status_code,502)
  self.assertEqual(len(sessions[self.sid]['hints']),count)
  self.assertEqual(self.client.post(self.p+'/hint',json={'kind':'translation','text':''}).status_code,400)

 def test_strict_schema_forbids_extra_fields_recursively(self):
  schema=strict_schema(RoleReply)
  self.assertFalse(schema['additionalProperties'])
  self.assertEqual(set(schema['required']),set(schema['properties']))
  self.assertFalse(schema['$defs']['GoalCheck']['additionalProperties'])

 def scene_payload(self):
  return {'reply':'Utilities are included. [1]','citations':['1'],'goal_assessments':{
   'goal_0':{'achieved':True,'learner_quote':'Are utilities included?','answer_status':'supported','source_id':'1','source_quote':'Utilities are included.'}
  }}

 def test_scene_schema_cannot_generate_goal_ids_or_duplicate_answer_entries(self):
  schema=scene_reply_schema(1,('1',))
  strict=strict_schema(schema)
  self.assertEqual(strict['$defs']['SceneGoalAssessments']['required'],['goal_0'])
  self.assertFalse(strict['$defs']['SceneGoalAssessments']['additionalProperties'])
  self.assertNotIn('goal_id',strict['$defs']['SceneGoalAssessment']['properties'])
  # The provider's strict subset rejects description siblings on $ref nodes.
  def check_refs(value):
   if isinstance(value,dict):
    if '$ref' in value: self.assertEqual(set(value),{'$ref'})
    for nested in value.values(): check_refs(nested)
   elif isinstance(value,list):
    for nested in value: check_refs(nested)
  check_refs(strict)
  for extra in ('Ask whether utilities are included','1','goal_1'):
   payload=self.scene_payload()
   payload['goal_assessments'][extra]=deepcopy(payload['goal_assessments']['goal_0'])
   with self.subTest(extra=extra),self.assertRaises(ValidationError): schema.model_validate(payload)
  payload=self.scene_payload()
  payload['answer_checks']=[{'goal_id':'0'},{'goal_id':'0'}]
  with self.assertRaises(ValidationError): schema.model_validate(payload)

 def test_scene_schema_requires_each_goal_and_limits_source_ids(self):
  with self.assertRaises(ValidationError): scene_reply_schema(2,('1',)).model_validate(self.scene_payload())
  for field in ('source_id','citations'):
   payload=self.scene_payload()
   if field=='source_id': payload['goal_assessments']['goal_0']['source_id']='999'
   else: payload['citations']=['999']
   with self.subTest(field=field),self.assertRaises(ValidationError): scene_reply_schema(1,('1',)).model_validate(payload)

 def test_fixed_assessment_turn_confirms_source_and_tracks_the_actual_user(self):
  generated=scene_reply_schema(1,('1',)).model_validate(self.scene_payload())
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[generated,review]) as model:
   response=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(response.status_code,200,response.text)
  self.assertIn('goal_assessments',model.call_args_list[0].args[0].model_fields)
  self.assertEqual(response.json()['goals'][0]['answer_status'],'confirmed')
  self.assertEqual(response.json()['goals'][0]['evidence'],'Are utilities included?')

 def test_replay_slot_zero_binds_to_original_nonzero_goal_id(self):
  generated=scene_reply_schema(1,('1',)).model_validate(self.scene_payload())
  canonical=bind_assessments(generated,[{'id':'2','text':'Ask whether utilities are included'}])
  self.assertEqual([g.goal_id for g in canonical.goal_checks],['2'])
  self.assertEqual([a.goal_id for a in canonical.answer_checks],['2'])

 def test_fixed_assessments_withhold_fabricated_answer_without_rejecting_question(self):
  payload=self.scene_payload()
  payload['goal_assessments']['goal_0']['source_quote']='Pets are always allowed.'
  generated=scene_reply_schema(1,('1',)).model_validate(payload)
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,
   accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[generated,review]):
   response=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(len(sessions[self.sid]['turns']),3)
  self.assertTrue(response.json()['turn']['answer_withheld'])
  self.assertTrue(response.json()['goals'][0]['achieved'])
  self.assertEqual(response.json()['goals'][0]['answer_status'],'unknown')
  self.assertEqual(response.json()['goals'][0]['answer_sources'],[])

 def test_review_questions_are_grouped_by_goal_not_wording(self):
  mission=[{'id':'0','text':'Ask about availability','achieved':False,'answer_status':'not_assessed'},
   {'id':'1','text':'Ask about deposit and guarantor requirements','achieved':False,'answer_status':'not_assessed'},
   {'id':'2','text':'Ask about rent','achieved':True,'answer_status':'confirmed'}]
  schema=scene_review_schema(0,('0','1','2'))
  for first,second in [('When is the apartment available?','Ask about availability'),
   ('Wann ist die Wohnung verfügbar?','Nach der Verfügbarkeit fragen'),
   ('¿Cuándo está disponible el piso?','Preguntar por la disponibilidad')]:
   with self.subTest(question=first):
    generated=schema.model_validate({'review_assessments':{f'goal_{i}':{'action':'not_performed','learner_turn_id':'','learner_quote':''} for i in range(3)},'feedback':[],'unanswered':[
     {'goal_id':'0','question':first},{'goal_id':'0','question':second},
     {'goal_id':'2','question':'How much is the rent?'},
     {'goal_id':'other','question':'Is parking available?'},
     {'goal_id':'other','question':'Is parking available?'}], 'phrases':[],'note':'Review.'})
    bound=bind_review(generated,[],mission)
    self.assertEqual(bound.unanswered,[first,'Is parking available?',mission[1]['text']])
  with self.assertRaises(ValidationError):
   schema.model_validate({'feedback':[],'unanswered':[{'goal_id':'invented','question':'Anything?'}],'phrases':[],'note':'Review.'})

 def test_finish_preserves_one_open_question_for_an_unknown_goal(self):
  sessions[self.sid]['mission'][0].update(text='Ask about availability',achieved=True,answer_status='unknown')
  generated=scene_review_schema(0,('0',)).model_validate({'review_assessments':{'goal_0':{'action':'not_performed','learner_turn_id':'','learner_quote':''}},'feedback':[],
   'unanswered':[{'goal_id':'0','question':'When is the apartment available?'},
    {'goal_id':'0','question':'Ask about availability'}],'phrases':[],'note':'Review.'})
  with patch('backend.main.model',return_value=generated):
   response=self.client.post(self.p+'/finish')
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(response.json()['unanswered'],['When is the apartment available?'])
  self.assertEqual(response.json()['goals'][0]['answer_status'],'unknown')

 def test_review_requires_real_turn_selection_when_learner_has_spoken(self):
  schema=scene_review_schema(1)
  payload={'review_assessments':{},'feedback':[{'learner_turn_id':'turn_0','suggestion':'','explanation':'The question clearly asks about the cost.'}],'unanswered':[],'phrases':[],'note':'Communication notes.'}
  bound=bind_review(schema.model_validate(payload),['How much is the rent?'])
  self.assertEqual(bound.feedback[0].quote,'How much is the rent?')
  self.assertEqual(bound.feedback[0].suggestion,'')
  for notes in ([],[{'learner_turn_id':'turn_99','suggestion':'','explanation':'Wrong turn'}],[{'quote':'Invented quotation','suggestion':'','explanation':'No generated quotes allowed'}]):
   with self.subTest(notes=notes),self.assertRaises(ValidationError): schema.model_validate({**payload,'feedback':notes})

 def test_review_cannot_invent_feedback_when_learner_has_not_spoken(self):
  schema=scene_review_schema(0)
  empty={'review_assessments':{},'feedback':[],'unanswered':[],'phrases':[],'note':'No learner turns yet.'}
  self.assertEqual(bind_review(schema.model_validate(empty),[]).feedback,[])
  with self.assertRaises(ValidationError): schema.model_validate({**empty,'feedback':[{'learner_turn_id':'turn_0','suggestion':'','explanation':'Invented user turn'}]})

 def test_selected_turn_feedback_is_bound_in_real_finish_endpoint(self):
  # This is a synthetic committed turn, not a provider-generated quotation.
  sessions[self.sid]['turns'].append({'role':'user','content':'No','sources':[]})
  generated=scene_review_schema(1).model_validate({'review_assessments':{},'feedback':[{'learner_turn_id':'turn_0','suggestion':'','explanation':'A direct refusal.'}],'unanswered':[],'phrases':[],'note':'Review.'})
  with patch('backend.main.model',return_value=generated): response=self.client.post(self.p+'/finish')
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(response.json()['feedback'][0]['quote'],'No')

 def test_historical_goal_carry_forward_does_not_rewrite_evidence(self):
  first=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[self.proposal(),first]):
   self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  historical=self.proposal(reply='What else would you like to ask?',citations=[])
  # Overbroad review IDs cannot create fresh observations after normalization.
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=['0','invented'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[historical,review]):
   response=self.client.post(self.p+'/turn',json={'text':'Thank you for explaining.'})
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(response.json()['goals'][0]['evidence'],'Are utilities included?')
  self.assertEqual(response.json()['goals'][0]['answer_status'],'confirmed')

 def test_hourly_budget_rejects_before_provider_request(self):
  from backend.main import model,MissionOutput
  from fastapi import HTTPException
  with patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-not-a-real-key','MODEL_CALLS_PER_HOUR':'0'}),self.assertRaises(HTTPException) as error:
   model(MissionOutput,'No network call should happen.',{})
  self.assertEqual(error.exception.status_code,429)

 def test_old_demo_client_cannot_start_live_mission_without_notice(self):
  sid=self.client.post('/api/sessions',json={'text':'Fictional advert.'}).json()['id']
  with patch('backend.main.model') as call:
   response=self.client.post('/api/sessions/'+sid+'/mission',json={'scenario':'apartment'})
  self.assertEqual(response.status_code,409)
  call.assert_not_called()

if __name__=='__main__': unittest.main()
