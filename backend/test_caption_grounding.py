"""Regression checks for fragmented rental captions and overconfident review."""
import unittest
from unittest.mock import Mock
from langchain_core.documents import Document
from backend.main import caption_context, evidence
from backend.live import rehearse, RoleReply, EvidenceReview
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
