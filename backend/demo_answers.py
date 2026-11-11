"""Conservative extractive demo answers. Never generate or translate document facts."""
import re
import unicodedata

def plain(text):
 return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')

# Intent patterns use the document's language, independently of conversation language.
TOPICS = {
 'apartment': [r'alquiler|renta|\brent\b|\bmiete\b', r'disponib|available|availability|verfug|einzug', r'mascota|\bpets?\b|haustier', r'gastos|suministros|utilities|bills|nebenkosten|betriebskosten|electricidad|strom|water|agua|heating|calefaccion|heiz',r'fianza|deposit|kaution'],
 'interview': [None, r'horario|working hours|schedule|arbeitszeit', r'salario|sueldo|salary|wage|gehalt|lohn'],
 'course': [r'clases|horario|classes|schedule|unterricht|kurszeit', r'cuesta|costs?|price|precio|kostet|kurspreis|kursgebuhr|curso|course|kurs', r'cancel|storn|refund|ruckerstatt']
}
UNKNOWN = r'no se especific|not specified|not stated|nicht angegeben|nicht festgelegt|nicht spezifiziert'
INSTRUCTION = r'ignore|instructions?|system prompt|api.?key|secret|reveal|ignora|instruccion|anweisung|ignoriere|print|execute|pretend|say that|tell the user|di que'
MONEY = r'(?:\d[\d., ]*\s*(?:euros?|eur\b|€|dollars?|usd\b|pounds?|gbp\b)|[€$£]\s*\d)'
MONTHLY_PRICE_LINE = re.compile(r'\s*'+MONEY+r'\s*/\s*(?:month|mes|monat)\s*',re.I)
DATE = r'\d|december|january|february|march|april|may|june|july|august|september|october|november|diciembre|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|dezember|januar|februar|marz|mai|juni|juli|oktober|now|ahora|sofort'

COPY = {
 'English': {'quote':'According to the document: “{text}” [{id}]', 'unknown':'I cannot confirm that from the retrieved passages. Please ask about it in the real conversation.', 'followup':'You can practise asking the other person to clarify this detail.'},
 'German': {'quote':'Im Dokument steht: „{text}“ [{id}]', 'unknown':'Das kann ich anhand der gefundenen Textstellen nicht bestätigen. Bitte fragen Sie im echten Gespräch danach.', 'followup':'Sie können üben, die andere Person um Klärung dieser Angabe zu bitten.'},
 'Spanish': {'quote':'Según el documento: «{text}» [{id}]', 'unknown':'No puedo confirmar ese dato con los fragmentos recuperados. Pregúntalo en la conversación real.', 'followup':'Puedes practicar cómo pedir a la otra persona que aclare este detalle.'}
}

EXTRA_STARTERS = {
 'English': {3:'Are utilities included in the rent?',4:'How much is the deposit?'},
 'German': {3:'Sind die Nebenkosten in der Miete enthalten?',4:'Wie hoch ist die Kaution?'},
 'Spanish': {3:'¿Están incluidos los gastos en el alquiler?',4:'¿Cuánto es la fianza?'}
}

# Requirements need policy interpretation, which the extractive demo cannot do.
RENTAL_REQUIREMENTS = r'contract|contrato|vertrag|proof of income|payslip|income requirement|employment|einkommensnachweis|gehaltsnachweis|nomina|justificante de ingresos|guarantor|avalista|burge'
for language, question in {
 'English':'What documents or proof of income are required to rent this flat?',
 'German':'Welche Unterlagen oder Einkommensnachweise brauche ich, um diese Wohnung zu mieten?',
 'Spanish':'¿Qué documentos o justificantes de ingresos necesito para alquilar este piso?'
}.items():
 EXTRA_STARTERS[language][5]=question

def asks_question(text):
 """Recognise common informal questions even without written punctuation."""
 query=plain(text).strip()
 return '?' in query or bool(re.match(
  r'^(?:(?:hi|hello|please|ok|okay)[,!. ]+)?(?:'
  r'who|what|when|where|why|how|do|does|did|is|are|can|could|would|will|must|should|'
  r'i (?:want|would like|need) to know|tell me|'
  r'wer|was|wann|wo|warum|wie|brauche|muss|kann|konnen|ist|sind|'
  r'que|quien|cuando|donde|por que|como|cuanto|necesito|hace falta|puedo|se puede)\b',query))

def detect_intents(scenario, text, patterns):
 """Route the question's subject before broad price/rent words.

 A reference to rent in a utilities question is not a request for the rent amount.
 Unknown subjects must not change the rent mission or leak its previous answer.
 """
 query=plain(text)
 if len(text.split())<3: return []
 if scenario=='apartment':
  if re.search(RENTAL_REQUIREMENTS,query): return [5]
  extras=[idx for idx in (3,4) if re.search(TOPICS['apartment'][idx],query)]
  if extras: return extras
  if re.search(r'internet|wi.?fi|furniture|amueblad|mobliert|parking|aparcamiento|parkplatz|contrato|contract|vertrag|address|direccion|adresse',query): return []
 return [idx for idx,pattern in enumerate(patterns) if re.search(pattern,query)]

def answer(scenario, language, indexes, docs):
 """Return reply + per-intent status + only passages actually used as support.

 Unknown or conflicting facts never become confirmed. Quotes retain source language.
 This is narrow pattern-based extraction, not general semantic question answering.
 """
 results={}
 parts=[]
 used={}
 for idx in indexes:
  if scenario=='apartment' and idx==5:
   results[idx]={'status':'unknown','quote':'','ids':[]}
   parts.append({
    'English':'I cannot reliably confirm the employment or income requirements in this scripted demo. Please check the exact requirements with the landlord or agent; I cannot confirm that a work contract is required.',
    'German':'In dieser skriptbasierten Demo kann ich die Anforderungen an Beschäftigungs- oder Einkommensnachweise nicht zuverlässig bestätigen. Bitte klären Sie die genauen Anforderungen mit der Vermietung; ich kann nicht bestätigen, dass ein Arbeitsvertrag nötig ist.',
    'Spanish':'No puedo confirmar con fiabilidad los requisitos de empleo o ingresos en esta demostración con guion. Consulta los requisitos exactos con el propietario o la agencia; no puedo confirmar que sea obligatorio un contrato de trabajo.'
   }[language])
   continue
  if scenario not in TOPICS or TOPICS[scenario][idx] is None:
   results[idx]={'status':'not_applicable','quote':'','ids':[]}
   continue
  topic=TOPICS[scenario][idx]
  candidates=[]
  for doc in docs:
   for sentence in re.split(r'(?<=[.!?])\s+|\n+',doc.page_content):
    normalized=plain(sentence)
    monthly_price=(scenario,idx)==('apartment',0) and MONTHLY_PRICE_LINE.fullmatch(normalized)
    if not (re.search(topic,normalized) or monthly_price) or re.search(INSTRUCTION,normalized): continue
    status='unknown' if re.search(UNKNOWN,normalized) else 'confirmed'
    if status=='confirmed':
     money=(scenario,idx) in [('apartment',0),('interview',2),('course',1)]
     if money and not re.search(MONEY,normalized): continue
     if (scenario,idx)==('apartment',1) and not re.search(DATE,normalized): continue
     if (scenario,idx)==('course',0) or (scenario,idx)==('interview',1):
      if not re.search(r'\d|monday|tuesday|wednesday|thursday|friday|lunes|martes|miercoles|jueves|viernes|montag|dienstag|mittwoch|donnerstag|freitag',normalized): continue
     if (scenario,idx)==('apartment',2) and not re.search(r'admit|permit|allowed|prohibit|erlaubt|verboten',normalized): continue
     if (scenario,idx)==('apartment',3) and not re.search(r'incluid|included|enthalten|inklusive|excluid|excluded|separat',normalized): continue
     if (scenario,idx)==('apartment',4) and not re.search(MONEY+'|month|mes|monat',normalized): continue
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
