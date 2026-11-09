import tempfile
from pathlib import Path
import unittest
import numpy as np
from backend.semantic_embeddings import LocalSemanticEmbeddings
from backend.embeddings import LocalEmbeddings
from scripts.compare_embeddings import load_cases,rank_vectors,ROOT


class EmbeddingComparisonTests(unittest.TestCase):
    def test_masked_pooling_ignores_padding_and_normalizes(self):
        hidden=np.asarray([[[3.,4.],[100.,100.]],[[2.,0.],[0.,2.]]])
        mask=np.asarray([[1,0],[1,1]])
        pooled=LocalSemanticEmbeddings.pool(hidden,mask)
        np.testing.assert_allclose(pooled[0],[.6,.8],atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(pooled,axis=1),[1,1],atol=1e-6)
        self.assertTrue(np.isfinite(LocalSemanticEmbeddings.pool(hidden,np.zeros_like(mask))).all())

    def test_reference_ranks_and_ties_are_explicit(self):
        rank,top,ties,_=rank_vectors([[1,0],[0,1],[1,0]],[1,0],['2'])
        self.assertEqual(rank,2)
        self.assertEqual(top,['0','2','1'])
        self.assertEqual(ties,2)
        with self.assertRaises(ValueError):rank_vectors([[np.nan,0]],[1,0],['0'])

    def test_same_dataset_deduplication_and_reference_coverage(self):
        corpora,cases,counts=load_cases()
        self.assertEqual(counts['quality-release-dataset'],{'raw':126,'unique':42})
        challenge=[r for r in cases if r['suite']=='retrieval-challenge']
        self.assertEqual(len(challenge),108)
        self.assertEqual(sum(r['language']!=r['source_language'] for r in challenge),72)
        for row in cases:
            self.assertTrue(set(row['relevant_ids']) <= {d.metadata['chunk_id'] for d in corpora[row['corpus']]})

    def test_model_loader_requires_verified_local_files(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Run scripts/download_embedding_model.py explicitly'):
                LocalSemanticEmbeddings(folder)
        self.assertEqual(len(LocalEmbeddings().embed_query('')),512)

    @unittest.skipUnless((ROOT/'.runtime/embedding-model/tokenizer.json').is_file(),'Explicit model download required; no CI network download')
    def test_downloaded_encoder_is_deterministic_across_batch_padding(self):
        encoder=LocalSemanticEmbeddings(ROOT/'.runtime/embedding-model')
        single=encoder.embed_query('The dog lives here.')
        batched=encoder.embed_documents(['The dog lives here.','This is a much longer unrelated sentence about a school timetable.'])
        self.assertEqual(len(single),384)
        np.testing.assert_allclose(single,batched[0],atol=1e-5)
        self.assertTrue(np.isfinite(batched).all())
