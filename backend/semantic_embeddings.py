"""Offline benchmark candidate. Not selected by production application configuration."""
import json
from pathlib import Path
import numpy as np
from langchain_core.embeddings import Embeddings


class LocalSemanticEmbeddings(Embeddings):
    """Pinned ONNX encoder with masked mean pooling; no downloads during loading.

    Uses the model card's 128-token sentence-transformer limit. The quantized
    export is a candidate to measure, not an assumed equivalent quality upgrade.
    """
    def __init__(self, directory, manifest=None):
        from scripts.download_embedding_model import MANIFEST,verify_file
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.manifest=json.loads(Path(manifest or MANIFEST).read_text())
        directory=Path(directory)
        for entry in self.manifest['files']:
            if not verify_file(directory/entry['path'],entry):
                raise ValueError('Missing or changed model data. Run scripts/download_embedding_model.py explicitly.')
        self.tokenizer=Tokenizer.from_file(str(directory/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=self.manifest['max_tokens'])
        padding=self.tokenizer.padding
        if not padding:raise ValueError('Pinned tokenizer does not define padding.')
        self.tokenizer.enable_padding(**padding)
        options=ort.SessionOptions()
        options.intra_op_num_threads=1
        options.inter_op_num_threads=1
        options.add_session_config_entry('session.intra_op.allow_spinning','0')
        self.session=ort.InferenceSession(str(directory/self.manifest['files'][0]['path']),
            sess_options=options,providers=['CPUExecutionProvider'])
        self.inputs={item.name for item in self.session.get_inputs()}
        self.truncated_texts=0

    @staticmethod
    def pool(hidden, mask):
        weights=mask[:,:,None].astype(np.float32)
        vectors=(hidden*weights).sum(axis=1)/np.maximum(weights.sum(axis=1),1)
        return vectors/np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-12)

    def embed_documents(self, texts):
        vectors=[]
        # Dynamic int8 activation quantization can vary with other batch items.
        # Single-text inference makes query/document vectors independent of batch
        # composition; measure the resulting throughput rather than hiding drift.
        for offset in range(len(texts)):
            encoded=self.tokenizer.encode_batch(texts[offset:offset+1])
            self.truncated_texts+=sum(bool(item.overflowing) for item in encoded)
            feed={'input_ids':np.asarray([item.ids for item in encoded],dtype=np.int64),
                  'attention_mask':np.asarray([item.attention_mask for item in encoded],dtype=np.int64),
                  'token_type_ids':np.asarray([item.type_ids for item in encoded],dtype=np.int64)}
            outputs=self.session.run(None,{name:value for name,value in feed.items() if name in self.inputs})
            hidden=outputs[0]
            if hidden.ndim!=3 or hidden.shape[-1]!=self.manifest['dimensions']:
                raise ValueError('Unexpected model output; expected per-token hidden states.')
            vectors.extend(self.pool(hidden,feed['attention_mask']).tolist())
        return vectors

    def embed_query(self, text):
        return self.embed_documents([text])[0]
