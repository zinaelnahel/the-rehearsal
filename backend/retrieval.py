"""Session-scoped Chroma persistence. Conversations are intentionally not persisted."""
import hashlib
import os
import threading
import time
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langsmith import traceable

LOCK = threading.RLock()
PREFIX = 'rehearsal-'


@lru_cache(maxsize=4)
def client(path):
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))


def database():
    return client(str(Path(os.getenv('CHROMA_PATH', '.runtime/chroma')).resolve()))


def collection_name(sid):
    return PREFIX + hashlib.sha256(sid.encode()).hexdigest()[:40]


class PersistentStore:
    def __init__(self, sid, embeddings, create=False, ttl=3600):
        self.embeddings = embeddings
        self.name = collection_name(sid)
        self.ttl = ttl
        with LOCK:
            db = database()
            if create:
                self.collection = db.create_collection(self.name, embedding_function=None,
                    metadata={'expires_at': time.time() + ttl, 'embedding': 'local-hash-512-v1',
                              'hnsw:space': 'cosine'})
            else:
                self.collection = db.get_collection(self.name, embedding_function=None)

    def add_documents(self, docs):
        with LOCK:
            self.collection.add(ids=[d.metadata['id'] for d in docs],
                documents=[d.page_content for d in docs], metadatas=[d.metadata for d in docs],
                embeddings=self.embeddings.embed_documents([d.page_content for d in docs]))

    @traceable(name='retrieve_evidence', run_type='retriever')
    def similarity_search(self, query, k=4):
        with LOCK:
            count = self.collection.count()
            if not count:
                return []
            found = self.collection.query(query_embeddings=[self.embeddings.embed_query(query)],
                n_results=min(k, count), include=['documents', 'metadatas'])
            return [Document(page_content=text, metadata=metadata)
                    for text, metadata in zip(found['documents'][0], found['metadatas'][0])]

    def touch(self):
        with LOCK:
            metadata = dict(self.collection.metadata)
            # Chroma treats even re-supplying the same legacy index setting as
            # an attempt to change the distance function during metadata updates.
            metadata.pop('hnsw:space', None)
            metadata['expires_at'] = time.time() + self.ttl
            self.collection.modify(metadata=metadata)

    def delete(self):
        with LOCK:
            database().delete_collection(self.name)


def build_store(sid, embeddings, docs, ttl=3600):
    if os.getenv('VECTOR_STORE', 'chroma') == 'memory':
        store = InMemoryVectorStore(embeddings)
        store.add_documents(docs)
        return store
    if os.getenv('VECTOR_STORE', 'chroma') != 'chroma':
        raise ValueError('VECTOR_STORE must be chroma or memory.')
    store = PersistentStore(sid, embeddings, create=True, ttl=ttl)
    try:
        store.add_documents(docs)
    except Exception:
        store.delete()
        raise
    return store


def purge_expired(now=None):
    if os.getenv('VECTOR_STORE', 'chroma') == 'memory':
        return
    with LOCK:
        db = database()
        for entry in db.list_collections():
            name = entry if isinstance(entry, str) else entry.name
            if not name.startswith(PREFIX):
                continue
            collection = db.get_collection(name, embedding_function=None)
            if collection.metadata.get('expires_at', 0) <= (now if now is not None else time.time()):
                db.delete_collection(name)


def delete_persisted(sid):
    """Also allow a caller holding its bearer ID to delete after an app restart."""
    if os.getenv('VECTOR_STORE', 'chroma') == 'memory':
        return
    with LOCK:
        db = database()
        names = {entry if isinstance(entry, str) else entry.name for entry in db.list_collections()}
        if collection_name(sid) in names:
            db.delete_collection(collection_name(sid))
