"""Pasted-page regression: source fields must survive boilerplate and language changes."""
import os
import unittest
from unittest.mock import patch,Mock
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend import main as api
from backend.live import RoleReply,GoalCheck,AnswerCheck,EvidenceReview,rehearse
from backend.listing_context import area_conflict
from backend.source_grounding import unsupported_rental_claim

LISTING='''Skip to main content
Idealista logo
Owners
Find property
Mortgages
Add your listing for free
Flat / apartment for rent in Fictional Street, 31
2,400 €/month 31 m² 1 bed.
Short-term rental
Property description
Available starting in December 2026.
This magnificent 80 m² apartment includes high-speed Wi-Fi.
All utilities are included up to €80: water, electricity, and gas.
Weekly cleaning service and 24/7 emergency support.
Contact us indicating the move-in date and desired length of stay.
Basic features
31 m² built
1 bedroom
1 bathroom
Price
Property price:
2,400 €/month
2 months deposit
Location
Fictional Street, 31
Madrid
idealista services
Long-term rentals in Spain
Guarantee 12 months rent with insurance
Normally the minimum lease is one year.
'''


class ListingContextTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory',
   'API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}))
  self.enterContext(patch.object(api,'LIVE',False))
  api.sessions.clear();self.client=self.enterContext(TestClient(api.app))
  response=self.client.post('/api/sessions',json={'text':LISTING})
  self.assertEqual(response.status_code,200,response.text)
  self.sid=response.json()['id'];self.session=api.sessions[self.sid]
  self.session['setup']={'scenario':'apartment','language':'Spanish','level':'B2'}

 def test_price_availability_and_caps_are_retrieved_in_three_languages(self):
  for question in ['¿Cuánto cuesto el piso, el mes?','How much is the rent per month?','Wie viel kostet die Wohnung pro Monat?']:
   with self.subTest(question=question):
    docs=api.search(self.session,question);text='\n'.join(d.page_content for d in docs)
    self.assertIn('2,400 €/month',text)
    self.assertIn('included up to €80',text)
    self.assertNotIn('minimum lease is one year',text)
  for question in ['¿Cuándo puedo mudarme al piso?','When is the apartment available?','Wann kann ich in die Wohnung einziehen?']:
   with self.subTest(question=question):
    self.assertIn('Available starting in December 2026','\n'.join(d.page_content for d in api.search(self.session,question)))

 def test_cleaning_keeps_real_uncertainties_and_citable_context(self):
  text='\n'.join(d.page_content for d in self.session['listing_chunks'])
  self.assertNotIn('Mortgages',text);self.assertNotIn('insurance',text)
  self.assertIn('Short-term rental',text);self.assertIn('2 months deposit',text)
  self.assertEqual(self.session['listing_area_conflict']['values'],['31','80'])
  focus=next(d for d in api.search(self.session,'monthly rent') if d.metadata['listing_section']=='price')
  response=self.client.get('/api/sessions/'+self.sid+'/source/'+focus.metadata['id'])
  self.assertEqual(response.status_code,200,response.text)
  self.assertIn('Property price:',str(response.json()['sections']))
  self.assertIn('2,400 €/month',response.json()['focus']['text'])

 def test_general_paste_of_same_page_uses_listing_reader(self):
  response=self.client.post('/api/sessions',json={'text':LISTING})
  self.assertTrue(api.sessions[response.json()['id']]['listing_chunks'])

 def test_generic_lease_minimum_is_withheld_even_with_approving_reviewer(self):
  question='opciones de duración del contrato.'
  self.session['mission']=[{'id':'0','text':'Ask about lease duration','achieved':False,'evidence':''}]
  docs=api.search(self.session,question)
  proposal=RoleReply(reply='Sobre la duración del contrato, normalmente se ofrece un mínimo de un año, pero no tengo detalles específicos para este piso.',citations=[],
   goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=question)],
   answer_checks=[AnswerCheck(goal_id='0',status='unknown',source_id='',source_quote='')])
  review=EvidenceReview(reply_supported=True,partner_role_consistent=True,accepted_goal_ids=['0'],verified_answer_goal_ids=[])
  text,sources,updates,withheld=rehearse(self.session,question,docs,Mock(side_effect=[proposal,review]),api.evidence)
  self.assertTrue(withheld);self.assertEqual(sources,[])
  self.assertNotIn('un año',text);self.assertEqual(updates['0']['status'],'unknown')

 def test_json_escaped_quote_is_repaired_only_against_exact_cited_listing_text(self):
  from backend.live import answer_quote_sources
  doc=next(d for d in self.session['listing_chunks'] if d.metadata['listing_section']=='price')
  identifier=doc.metadata['id']
  encoded=doc.page_content.replace('\n',r'\\n')
  answer=AnswerCheck(goal_id='0',status='supported',source_id=identifier,source_quote=encoded)
  self.assertEqual(answer_quote_sources(answer,[doc],[identifier]),[identifier])
  self.assertNotIn(r'\n',answer.source_quote)
  wrong=answer.model_copy(update={'source_quote':encoded.replace('2,400','1,200')})
  self.assertEqual(answer_quote_sources(wrong,[doc],[identifier]),[])
  self.assertEqual(answer_quote_sources(answer,[doc],[]),[])

 def test_lease_guard_requires_duration_not_deposit_or_general_practice(self):
  for reply in ['Normally the minimum lease is one year, but I do not have specifics for this flat.',
   'Normalmente la duración mínima del contrato es un año, pero no tengo detalles.',
   'Normalerweise beträgt die Mindestmietdauer ein Jahr.']:
   self.assertTrue(unsupported_rental_claim(reply,[],[]))
  deposit=[Document(page_content='Deposit: 12 months.',metadata={'id':'1'})]
  self.assertTrue(unsupported_rental_claim('The minimum lease is one year.',deposit,deposit))
  actual=[Document(page_content='Minimum lease: 12 months.',metadata={'id':'1'})]
  self.assertFalse(unsupported_rental_claim('The minimum lease is one year.',actual,actual))
  self.assertFalse(unsupported_rental_claim('Is the minimum lease one year?',[],[]))

 def test_conflicting_floor_areas_cannot_be_confirmed_by_two_models(self):
  question='¿Qué tamaño tiene el piso?'
  self.session['mission']=[{'id':'0','text':'Ask about the apartment size','achieved':False,'evidence':''}]
  docs=api.search(self.session,question)
  focus=next(d for d in docs if '31 m² built' in d.page_content)
  proposal=RoleReply(reply='El piso tiene 31 m².',citations=[focus.metadata['id']],
   goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=question)],
   answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id=focus.metadata['id'],source_quote='31 m² built')])
  review=EvidenceReview(reply_supported=True,partner_role_consistent=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  reply,sources,updates,withheld=rehearse(self.session,question,docs,Mock(side_effect=[proposal,review]),api.evidence)
  self.assertTrue(withheld);self.assertIn('31 / 80 m²',reply)
  self.assertEqual(updates['0']['status'],'unknown');self.assertGreaterEqual(len(sources),2)
  self.assertIsNone(area_conflict([Document(page_content='Apartment: 80 m². Terrace: 10 m².',metadata={'id':'1'})]))
