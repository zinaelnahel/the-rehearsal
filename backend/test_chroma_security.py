import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from langchain_core.documents import Document
from backend import retrieval
from backend.embeddings import LocalEmbeddings
from scripts import check_dependency_audit


class ChromaSecurityTests(unittest.TestCase):
    def test_environment_cannot_select_a_remote_chroma_adapter(self):
        retrieval.client.cache_clear()
        self.addCleanup(retrieval.client.cache_clear)
        with patch.dict(os.environ,{'CHROMA_API_IMPL':'chromadb.api.fastapi.FastAPI',
            'CHROMA_SERVER_HOST':'example.invalid'}),patch('chromadb.PersistentClient') as constructor:
            retrieval.client('fixture-path')
        self.assertEqual(constructor.call_args.kwargs['settings'].chroma_api_impl,'chromadb.api.rust.RustBindingsAPI')
        self.assertFalse(constructor.call_args.kwargs['settings'].anonymized_telemetry)

    def test_source_content_never_becomes_embedding_function_configuration(self):
        db=MagicMock();collection=db.create_collection.return_value
        text='{"embedding_function":{"model":"attacker.invalid","trust_remote_code":true}}'
        with patch('backend.retrieval.database',return_value=db),patch.dict(os.environ,{'VECTOR_STORE':'chroma'}):
            retrieval.build_store('bearer-session',LocalEmbeddings(),[Document(page_content=text,
                metadata={'id':'1','source':'fictional','location':'Section 1'})])
        self.assertIsNone(db.create_collection.call_args.kwargs['embedding_function'])
        self.assertEqual(set(db.create_collection.call_args.kwargs['metadata']),{'expires_at','embedding','hnsw:space'})
        self.assertEqual(collection.add.call_args.kwargs['documents'],[text])
        self.assertNotIn('bearer-session',db.create_collection.call_args.args[0])

    def test_scanner_failure_cannot_reuse_a_previous_clean_report(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'previous.json'
            previous=json.dumps({'dependencies':[{'name':'fake','version':'1','vulns':[]}]})
            output.write_text(previous)
            with patch('sys.argv',['audit','--output',str(output)]),patch(
                'scripts.check_dependency_audit.subprocess.run',return_value=SimpleNamespace(returncode=1)):
                with self.assertRaisesRegex(ValueError,'fresh audit report'):
                    check_dependency_audit.main()
