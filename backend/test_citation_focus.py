import unittest
from langchain_core.documents import Document
from backend.citation_focus import focused_documents
from backend.live import scene_reply_schema, bind_assessments


class CitationFocusTests(unittest.TestCase):
    def test_excerpts_must_belong_to_the_identified_passage(self):
        doc = Document(page_content='Context. Salary: EUR 60,000. Other details.', metadata={'id': '1'})
        result = focused_documents([doc], [
            {'source_id': '1', 'quote': 'Salary: EUR 60,000.'},
            {'source_id': '1', 'quote': 'Salary: EUR 90,000.'},
            {'source_id': '2', 'quote': 'Other details.'}])
        self.assertEqual(result[0].metadata['highlights'], ['Salary: EUR 60,000.'])
        self.assertNotIn('highlights', doc.metadata)

    def test_excerpts_survive_provider_schema_binding(self):
        result = scene_reply_schema(0, ('1',)).model_validate({
            'reply': 'The salary is EUR 60,000. [1]', 'citations': ['1'],
            'goal_assessments': {},
            'citation_excerpts': [{'source_id': '1', 'quote': 'Salary: EUR 60,000.'}]})
        reply = bind_assessments(result, [])
        self.assertEqual(reply.citation_excerpts[0].quote, 'Salary: EUR 60,000.')
