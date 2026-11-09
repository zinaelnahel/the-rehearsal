"""Deterministic lexical alias retrieval baseline."""
import hashlib
import re
import unicodedata
from langchain_core.embeddings import Embeddings

def normalize(text):
 return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

class LocalEmbeddings(Embeddings):
 """Deterministic hashed word embeddings; local lexical retrieval, not semantic AI."""
 def embed_query(self, text):
  vector = [0.0] * 512
  aliases = {'cuanto':'precio','cuesta':'precio','coste':'precio','rent':'alquiler','salary':'salario','sueldo':'salario','pets':'mascotas','perro':'mascotas','gato':'mascotas','horas':'horario','cuando':'disponible','availability':'disponible','miete':'alquiler','preis':'precio','cost':'precio','price':'precio','kosten':'precio','kostet':'precio','verfugbar':'disponible','gehalt':'salario','haustiere':'mascotas','arbeitszeiten':'horario','hours':'horario','schedule':'horario','stornierung':'cancelacion','cancellation':'cancelacion','utilities':'gastos','bills':'gastos','nebenkosten':'gastos','included':'incluidos','enthalten':'incluidos'}
  for word in re.findall(r'\w+', normalize(text)):
   if word in ('available','when','wann','entrar','einziehen','move','mudarse'): word='disponible'
   if word=='pet': word='mascotas'
   word = aliases.get(word, word)
   vector[int(hashlib.sha256(word.encode()).hexdigest()[:8],16) % 512] += 1
  # Cosine similarity is undefined for all-zero vectors (empty/punctuation input).
  # A deterministic sentinel keeps these valid without claiming semantic meaning.
  if not any(vector): vector[0] = 1.0
  return vector
 def embed_documents(self, texts):
  return [self.embed_query(t) for t in texts]

