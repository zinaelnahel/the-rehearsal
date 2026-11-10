"""Extractive listing sections and bounded field-aware retrieval.

No facts are generated: retained text, source ranges and citations come from
the supplied page. Unknown formats retain their text rather than guessing.
"""
import re
from langchain_core.documents import Document
from backend.demo_answers import plain
from backend.source_grounding import rental_price_question

TITLE=re.compile(r'^(?:flat|apartment|studio|house|piso|apartamento|estudio|casa|wohnung|haus).*(?:for rent|en alquiler|zur miete|mieten)',re.I)
HEADINGS={
 'property description':'description','descripcion del inmueble':'description','beschreibung':'description',
 'basic features':'features','caracteristicas basicas':'features','building':'features','edificio':'features',
 'amenities':'features','equipamiento':'features','ausstattung':'features',
 'price':'price','precio':'price','preis':'price','location':'location','ubicacion':'location','lage':'location',
 'photos':'photos','fotos':'photos','floor plans':'photos','planos':'photos',
 'energy performance certificate':'energy','certificado energetico':'energy',
 'ask the advertiser':'contact','professional advertiser':'contact'}
FOOTERS={'idealista services','servicios de idealista','servicios idealista','servizi idealista','servicos idealista'}
AREA=re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m[²2]\b')
MONTHLY_MONEY=re.compile(r'(?:[€$£]\s*\d[\d., ]*|\d[\d., ]*\s*(?:€|\$|£|euros?|eur|dollars?|usd|pounds?|gbp))\s*(?:/\s*(?:month|mes|monat)|(?:per|al|pro)\s+(?:month|mes|monat))',re.I)


def looks_like_listing(text):
 return 'idealista' in plain(text[:1500]) and ('property description' in plain(text) or any(TITLE.search(plain(line.strip())) for line in text.splitlines()))


def listing_documents(text,name):
 lines=text.splitlines()
 start=next((i for i,line in enumerate(lines) if TITLE.search(plain(line.strip()))),0)
 stop=next((i for i in range(start,len(lines)) if plain(lines[i].strip()) in FOOTERS),len(lines))
 documents=[];section='overview';begin=start
 def append(end):
  value='\n'.join(lines[begin:end]).strip()
  if value:
   documents.append(Document(page_content=value,metadata={'source':name,
    'location':f'Sections {begin+1}–{end} ({section})','listing_section':section}))
 for index in range(start,stop):
  heading=HEADINGS.get(plain(lines[index].strip()))
  if heading is not None:
   append(index);begin=index;section=heading
 append(stop)
 if not documents:
  return [Document(page_content=text,metadata={'source':name,'location':'Section 1','listing_section':'overview'})]
 return documents


def trim_pdf_listing_pages(documents):
 """Keep original page metadata while excluding footer material from retrieval."""
 trimmed=[];finished=False
 for document in documents:
  lines=[]
  for line in document.page_content.splitlines():
   if plain(line.strip()) in FOOTERS:finished=True
   if not finished:lines.append(line)
  trimmed.append(Document(page_content='\n'.join(lines),metadata=dict(document.metadata)))
 return trimmed


def query_fields(text):
 value=plain(text);fields=[]
 if rental_price_question(value) or re.search(r'\b(?:rent|miete|alquiler)\b',value):fields.append('price')
 if re.search(r'\b(?:utilities|bills|included|includes?|gastos|incluye|incluid\w*|nebenkosten|enthalten|inklusive)\b',value):fields.append('utilities')
 if re.search(r'\b(?:lease|contract|duration|contrato|duracion|estancia|vertrag\w*|mietdauer|laufzeit)\b',value):fields.append('lease')
 if re.search(r'\b(?:available|availability|disponib\w*|mudar\w*|mudanza|einzieh\w*|einzug|verfug\w*)\b',value) or ('price' not in fields and re.search(r'\b(?:when|cuando|wann)\b',value)):fields.append('availability')
 if re.search(r'\b(?:pets?|mascotas?|haustiere?)\b',value):fields.append('pets')
 if re.search(r'\b(?:deposit|fianza|kaution)\b',value):fields.append('deposit')
 if re.search(r'\b(?:size|big|square|met(?:er|re)s|metros?|superficie|tamano|wohnflache|quadratmeter|gross)\b',value):fields.append('area')
 if not fields and re.search(r'\b(?:conditions|condiciones|bedingungen)\b',value):fields=['price','utilities','availability','lease']
 return fields


def field_score(doc,field):
 text=plain(doc.page_content);section=doc.metadata.get('listing_section')
 if field=='price':return 5 if MONTHLY_MONEY.search(text) and section=='price' else 4 if MONTHLY_MONEY.search(text) else 0
 patterns={
  'utilities':r'\b(?:utilities|bills|water|electricity|gas|gastos|suministros|agua|electricidad|nebenkosten|wasser|strom)\b',
  'availability':r'\b(?:available|availability|disponib\w*|verfugbar|einzug)\b',
  'lease':r'\b(?:short.term|long.term|lease|minimum stay|length of stay|duration|temporada|corta estancia|larga estancia|duracion|mietdauer|mindest\w*|kurzzeit\w*)\b',
  'pets':r'\b(?:pets?|mascotas?|haustiere?)\b','deposit':r'\b(?:deposit|fianza|kaution)\b'}
 if field=='area':return 3 if AREA.search(text) else 0
 return 3 if re.search(patterns[field],text) else 0


def retrieve_listing(session,query,base):
 chunks=session.get('listing_chunks',[])
 if not chunks:return base
 anchors=[];seen=set()
 fields=query_fields(query)
 if 'price' in fields and 'utilities' not in fields:fields.append('utilities')
 for field in fields:
  ranked=sorted(((field_score(doc,field),i,doc) for i,doc in enumerate(chunks)),key=lambda item:(-item[0],item[1]))
  for score,_,doc in ranked[:2]:
   if score and doc.metadata['id'] not in seen:
    anchors.append(doc);seen.add(doc.metadata['id'])
 anchors=(anchors+base)[:6]
 selected={doc.metadata['id']:doc for doc in anchors}
 positions={doc.metadata['id']:i for i,doc in enumerate(chunks)}
 for doc in anchors:
  index=positions.get(doc.metadata['id'])
  if index is None:continue
  # Keep field labels, their values, limits and neighboring sentences together.
  for nearby in chunks[max(0,index-1):index+2]:selected.setdefault(nearby.metadata['id'],nearby)
 return list(selected.values())[:16]


def area_conflict(chunks):
 values={}
 for doc in chunks:
  text=plain(doc.page_content)
  for match in AREA.finditer(text):
   prefix=re.split(r'[.!?\n;]',text[:match.start()])[-1][-60:]
   if re.search(r'\b(?:terrace|balcony|garden|terraza|balcon|garten|balkon|terrasse|storage|trastero|garage|garaje)\b',prefix):continue
   value=match[1].replace(',','.')
   values.setdefault(value,set()).add(doc.metadata['id'])
 if len(values)<2:return None
 return {'values':sorted(values,key=float),'source_ids':sorted({identifier for ids in values.values() for identifier in ids})}
