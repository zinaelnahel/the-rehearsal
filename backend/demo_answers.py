"""Conservative extractive demo answers. Never generate or translate document facts."""
import re
import unicodedata

def plain(text):
 return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')

# Intent patterns use the document's language, independently of conversation language.
TOPICS = {
 'apartment': [r'alquiler|renta|\brent\b|\bmiete\b', r'disponib|available|availability|verfug|einzug', r'mascota|\bpets?\b|haustier'],
 'interview': [None, r'horario|working hours|schedule|arbeitszeit', r'salario|sueldo|salary|wage|gehalt|lohn'],
 'course': [r'clases|horario|classes|schedule|unterricht|kurszeit', r'cuesta|costs?|price|precio|kostet|kurspreis|kursgebuhr|curso|course|kurs', r'cancel|storn|refund|ruckerstatt']
}
UNKNOWN = r'no se especific|not specified|not stated|nicht angegeben|nicht festgelegt|nicht spezifiziert'
INSTRUCTION = r'ignore|instructions?|system prompt|api.?key|secret|reveal|ignora|instruccion|anweisung|ignoriere|print|execute|pretend|say that|tell the user|di que'
MONEY = r'(?:\d[\d., ]*\s*(?:euros?|eur\b|€|dollars?|usd\b|pounds?|gbp\b)|[€$£]\s*\d)'
DATE = r'\d|december|january|february|march|april|may|june|july|august|september|october|november|diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|dezember|januar|februar|marz|mai|juni|juli|oktober|now|ahora|sofort'

COPY = {
 'English': {'quote':'According to the document: “{text}” [{id}]', 'unknown':'I cannot confirm that from the retrieved passages. Please ask about it in the real conversation.', 'followup':'You can practise asking the other person to clarify this detail.'},
 'German': {'quote':'Im Dokument steht: „{text}“ [{id}]', 'unknown':'Das kann ich anhand der gefundenen Textstellen nicht bestätigen. Bitte fragen Sie im echten Gespräch danach.', 'followup':'Sie können üben, die andere Person um Klärung dieser Angabe zu bitten.'},
 'Spanish': {'quote':'Según el documento: «{text}» [{id}]', 'unknown':'No puedo confirmar ese dato con los fragmentos recuperados. Pregúntalo en la conversación real.', 'followup':'Puedes practicar cómo pedir a la otra persona que aclare este detalle.'}
}

def answer(scenario, language, indexes, docs):
 """Return reply + per-intent status + only passages actually used as support.

 Unknown or conflicting facts never become confirmed. Quotes retain source language.
 This is narrow pattern-based extraction, not general semantic question answering.
 """
 results={}
 parts=[]
 used={}
 for idx in indexes:
  if scenario not in TOPICS or TOPICS[scenario][idx] is None:
   results[idx]={'status':'not_applicable','quote':'','ids':[]}
   continue
  topic=TOPICS[scenario][idx]
  candidates=[]
  for doc in docs:
   for sentence in re.split(r'(?<=[.!?])\s+|\n+',doc.page_content):
    normalized=plain(sentence)
    if not re.search(topic,normalized) or re.search(INSTRUCTION,normalized): continue
    status='unknown' if re.search(UNKNOWN,normalized) else 'confirmed'
    if status=='confirmed':
     money=(scenario,idx) in [('apartment',0),('interview',2),('course',1)]
     if money and not re.search(MONEY,normalized): continue
     if (scenario,idx)==('apartment',1) and not re.search(DATE,normalized): continue
     if (scenario,idx)==('course',0) or (scenario,idx)==('interview',1):
      if not re.search(r'\d|monday|tuesday|wednesday|thursday|friday|lunes|martes|miercoles|jueves|viernes|montag|dienstag|mittwoch|donnerstag|freitag',normalized): continue
     if (scenario,idx)==('apartment',2) and not re.search(r'admit|permit|allowed|prohibit|erlaubt|verboten',normalized): continue
     if (scenario,idx)==('course',2): continue # policy interpretation is outside this demo
    candidates.append((sentence.strip(),doc,status))
  # Ambiguous/conflicting chunks never become a confirmed answer.
  unique={plain(text) for text,_,_ in candidates}
  if len(unique)==1:
   text,doc,status=candidates[0]
   identifier=doc.metadata['id']
   results[idx]={'status':status,'quote':text,'ids':[identifier]}
   parts.append(COPY[language]['quote'].format(text=text,id=identifier))
   if status=='unknown': parts.append(COPY[language]['followup'])
   used[identifier]=doc
  else:
   results[idx]={'status':'unknown','quote':'','ids':[]}
   parts.append(COPY[language]['unknown'])
 return '\n\n'.join(dict.fromkeys(parts)),results,list(used.values())
