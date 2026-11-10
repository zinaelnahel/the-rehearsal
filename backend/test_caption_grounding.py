"""Regression checks for fragmented rental captions and overconfident review."""
import unittest
from unittest.mock import Mock
from langchain_core.documents import Document
from backend.main import caption_context, evidence
from backend.live import rehearse, RoleReply, EvidenceReview, AnswerCheck, GoalCheck, answer_quote_sources
from backend.source_grounding import unsupported_rental_claim


def caption(identifier,start,text):
    return Document(page_content=text,metadata={'id':str(identifier),'start':start,
        'end':start+4,'source':'Reviewed video transcript','location':str(start)})


class CaptionGroundingTests(unittest.TestCase):
    def setUp(self):
        self.docs=[caption(19,75,'y que me dice del precio'),
            caption(20,79.27,'cuesta menos de mil euros'),
            caption(21,82,'y los recibos del gas y del agua estan'),
            caption(22,85.25,'incluidos en el alquiler esto no es'),
            caption(23,89,'normal en un piso de alquiler')]

    def test_retrieval_restores_missing_caption_subject_without_merging_times(self):
        result=caption_context({'transcript_chunks':self.docs},[self.docs[1],self.docs[3]])
        self.assertEqual([d.metadata['id'] for d in result],['20','22','19','21','23'])
        self.assertEqual(result[1].metadata['start'],85.25)
        self.assertIn('gas y del agua',result[3].page_content)

    def test_unsupported_claims_withheld_even_when_independent_reviewer_passes(self):
        session={'setup':{'scenario':'apartment','language':'Spanish','level':'B2'},
            'mission':[],'turns':[]}
        cases=[('En este piso no se permiten mascotas.',[]),
            ('Se permiten mascotas.',[]),
            ('Los gastos no estan incluidos en ese precio.',['20','22']),
            ('El piso esta disponible para entrar a partir del proximo mes.',[])]
        for reply,citations in cases:
            with self.subTest(reply=reply):
                call=Mock(side_effect=[RoleReply(reply=reply,citations=citations,
                    goal_checks=[],answer_checks=[]),EvidenceReview(reply_supported=True,
                    partner_role_consistent=True,accepted_goal_ids=[],verified_answer_goal_ids=[])])
                text,sources,updates,withheld=rehearse(session,'Si, por favor.',self.docs,call,evidence)
                self.assertTrue(withheld)
                self.assertEqual(sources,[])
                self.assertNotEqual(text,reply)

    def test_supported_and_unknown_answers_are_allowed_by_backstop(self):
        for reply in ('Los recibos del gas y del agua estan incluidos en el alquiler.',
            'No puedo confirmar si se permiten mascotas.',
            'La politica de mascotas no se menciona.',
            'Quieres saber si se permiten mascotas?'):
            with self.subTest(reply=reply):
                self.assertFalse(unsupported_rental_claim(reply,self.docs,self.docs))
        policy=[caption(1,0,'No se permiten mascotas.')]
        self.assertFalse(unsupported_rental_claim('No se permiten mascotas.',policy,policy))

    def test_non_transcript_search_context_is_unchanged(self):
        self.assertEqual(caption_context({},self.docs),self.docs)

    def test_exact_cross_caption_quote_keeps_all_supporting_timestamps(self):
        text='¿Cuándo cuesta el apartamento?'
        quote='cuesta menos de mil euros y los recibos del gas y del agua estan incluidos en el alquiler'
        proposal=RoleReply(reply='Cuesta menos de mil euros; el gas y el agua estan incluidos.',
            citations=['20','21','22'],goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=text)],
            answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='20',source_quote=quote)])
        review=EvidenceReview(reply_supported=True,partner_role_consistent=True,
            accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
        goal={'id':'0','text':'Ask about rent and bills','achieved':False,'evidence':''}
        session={'setup':{'scenario':'apartment','language':'Spanish','level':'B2'},
            'mission':[goal],'turns':[],'transcript_chunks':self.docs}
        reply,sources,updates,withheld=rehearse(session,text,self.docs,Mock(side_effect=[proposal,review]),evidence)
        self.assertFalse(withheld)
        self.assertEqual(updates['0']['status'],'confirmed')
        self.assertEqual(updates['0']['ids'],['20','21','22'])
        self.assertEqual([d.metadata['start'] for d in sources],[79.27,82,85.25])

    def test_cross_caption_quote_requires_exact_contiguous_cited_evidence(self):
        def check(quote,docs,citations,source_id='20'):
            return answer_quote_sources(AnswerCheck(goal_id='0',status='supported',
                source_id=source_id,source_quote=quote),docs,citations)
        self.assertEqual(check('cuesta menos de mil euros incluidos en el alquiler',
            [self.docs[1],self.docs[3]],['20','22']),[])
        quote='cuesta menos de mil euros y los recibos del gas y del agua estan incluidos en el alquiler'
        self.assertEqual(check(quote,self.docs,['20','22']),[])
        self.assertEqual(check(quote.replace('mil','dos mil'),self.docs,['20','21','22']),[])
        self.assertEqual(check('incluidos en el alquiler',self.docs,['20','21','22']),['22'])
        self.assertEqual(check('incluidos en el alquiler',self.docs,['20','21']),[])
        self.assertEqual(check(quote,self.docs,['19','20','21','22'],source_id='19'),[])
        for fragments in [('Gas and water are','included in the rent.'),
            ('Gas und Wasser sind','in der Miete enthalten.'),
            ('El gas y el agua están','incluidos en el alquiler.')]:
            docs=[caption(1,0,fragments[0]),caption(2,4,fragments[1])]
            self.assertEqual(check(' '.join(fragments),docs,['1','2'],source_id='1'),['1','2'])

    def test_price_typo_changes_retrieval_query_without_changing_learner_text(self):
        from backend.main import search
        store=Mock();store.similarity_search.return_value=[]
        session={'store':store,'setup':{'scenario':'apartment'}}
        original='¿Cuándo cuesta el apartamento?'
        search(session,original)
        self.assertEqual(store.similarity_search.call_args.args[0],'¿cuánto cuesta el apartamento?')
        self.assertEqual(original,'¿Cuándo cuesta el apartamento?')
        search(session,'¿Cuándo puedo mudarme al apartamento?')
        self.assertEqual(store.similarity_search.call_args.args[0],'¿Cuándo puedo mudarme al apartamento?')

    def test_repeated_price_question_cannot_advance_to_availability(self):
        text='¿Cuánto cuesta el piso?'
        goal={'id':'0','text':'Ask about rent','achieved':True,'evidence':'¿Cuándo cuesta el apartamento?'}
        session={'setup':{'scenario':'apartment','language':'Spanish','level':'B2'},
            'mission':[goal],'turns':[],'transcript_chunks':self.docs}
        def proposal(reply):
            return RoleReply(reply=reply,citations=['20'],
                goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote=text)],
                answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='20',source_quote='cuesta menos de mil euros')])
        def review():
            return EvidenceReview(reply_supported=True,partner_role_consistent=True,
                accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
        for corrected in (True,False):
            with self.subTest(corrected=corrected):
                bad=proposal('El piso esta disponible para entrar la semana que viene.')
                second=proposal('Cuesta menos de mil euros.') if corrected else bad.model_copy(deep=True)
                call=Mock(side_effect=[bad,review(),second,review()])
                reply,sources,updates,withheld=rehearse(session,text,self.docs,call,evidence)
                self.assertEqual(call.call_count,4,'At most one correction with a fresh independent review')
                self.assertIn('server_question_focus',call.call_args_list[0].args[2])
                self.assertIn('server_correction',call.call_args_list[2].args[2])
                self.assertNotIn('semana que viene',reply)
                self.assertEqual(withheld,not corrected)
                if corrected:
                    self.assertEqual(updates['0']['status'],'confirmed')
                    self.assertEqual(updates['0']['evidence'],text)
                    self.assertEqual([d.metadata['id'] for d in sources],['20'])
                else:
                    self.assertNotEqual(updates['0']['status'],'confirmed')
                    self.assertEqual(sources,[])
                self.assertEqual(goal['evidence'],'¿Cuándo cuesta el apartamento?','Rejected proposals cannot mutate session state')
