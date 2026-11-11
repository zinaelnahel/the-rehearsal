"""Fictional family-boundary sample, separate from custom difficult conversations."""
import re
from backend.context import plain


# Server-owned examples: never sourced from uploaded instructions or user text.
FAMILY_ROLE_EXAMPLES = {
 'English': {
  'invalid_partner_lines':[
   "I cannot help this weekend.",
   "I do not have time. Please do not plan errands with me this weekend.",
   "Please ask me before making plans involving my time."],
  'valid_partner_lines':[
   "I understand you cannot help this weekend.",
   "I will ask you before making plans that involve your time.",
   "Then I will plan without your help this weekend."]},
 'German': {
  'invalid_partner_lines':[
   'Ich kann dieses Wochenende nicht helfen.',
   'Bitte plane dieses Wochenende keine Besorgungen mit mir ein.',
   'Bitte frage mich in Zukunft vorher, bevor du meine Zeit für Besorgungen einplanst.'],
  'valid_partner_lines':[
   'Ich verstehe, dass du dieses Wochenende nicht helfen kannst.',
   'Ich werde dich in Zukunft vorher fragen.',
   'Dann plane ich dieses Wochenende ohne dich.']},
 'Spanish': {
  'invalid_partner_lines':[
   'Te agradecería que me avisaras antes de hacer planes que dependan de tu tiempo.',
   'No puedo ayudar este fin de semana.',
   'No cuentes conmigo para los recados este fin de semana.',
   'Por favor, pregúntame antes de hacer planes con mi tiempo.'],
  'valid_partner_lines':[
   'Entiendo que no puedes ayudar este fin de semana.',
   'Te preguntaré antes de hacer planes que dependan de tu tiempo.',
   'Entonces organizaré los recados sin tu ayuda este fin de semana.']}
}


def family_role_contract(language):
 return {
  'partner_action':'request help with errands; respond to the learner refusal',
  'learner_action':'decline the request and set a boundary about their own time',
  'owner_of_unavailability_and_boundary':'learner',
  'source_practice_instructions_address':'learner, never the partner',
  **FAMILY_ROLE_EXAMPLES[language]
 }


def spanish_short_refusal(text):
 """Recognize an elliptical reply to the sample's request, not a mention of no."""
 query=plain(text).strip()
 return bool(re.search(
  r'^no puedo[.!\s]*$|^no puedo(?:\s*[,.;!:]\s*|\s+)(?:tengo trabajo|tengo que trabajar|estoy trabajando|porque (?:tengo trabajo|tengo que trabajar))\b'
  r'|^no(?:\s*[,.;!]\s*|\s+)(?:(?:perdon|lo siento|disculpa|disculpame)\s*[,.;!]?\s+)?(?:tengo trabajo|tengo que trabajar|estoy trabajando)\b',query)) and '?' not in query


def family_alternative_offer(text,language):
 """A volunteered next-week offer is not another refusal of this weekend."""
 query=plain(text)
 patterns={
  'Spanish':(r'\b(?:la )?(?:proxima semana|semana proxima|semana que viene)\b',r'\b(?:tengo tiempo|puedo ayudar(?:te)?|estoy disponible)\b',r'\bno (?:tengo tiempo|puedo|estoy disponible)\b'),
  'English':(r'\bnext week\b',r'\b(?:i have time|i can help|i am available|i.m available)\b',r'\b(?:not available|no time|cannot|can.t)\b'),
  'German':(r'\bnachste\w* woche\b',r'\b(?:habe ich zeit|ich habe zeit|kann ich helfen|ich kann helfen)\b',r'\b(?:keine zeit|nicht helfen)\b')}
 when,available,negative=patterns[language]
 return bool(re.search(when,query) and re.search(available,query) and not re.search(negative,query))


def family_audio_detail(text):
 """Specific recorded logistics, not acknowledgements or learner self-reports."""
 return bool(re.search(r'\b(?:sabado|mudanza|cajas|coche|demas|diez|saturday|boxes|car|moving|move|ten|samstag|umzug|kisten|kartons|auto|zehn)\b|\b(?:de 10 a 1|de diez a una|contado contigo|he dicho a los|told the others|told everyone)\b',plain(text)))


def recorded_time_reply(session,text):
 """Answer a time follow-up from the actual recording, independent of goals.

 Only an unchanged, timestamped sample can use this narrow extractive path.
 A proposed alternative date must not inherit the original Saturday's hours.
 """
 if not session.get('sample_audio_timed') or not session.get('family_boundary'):return None
 query=plain(text).strip()
 if not re.search(r'^(?:¿\s*)?(?:a que hora|que hora|cual es el horario|what time|at what time|wann|um wie viel uhr|um wieviel uhr)\b',query):return None
 if re.search(r'proxima semana|semana proxima|semana que viene|next week|nachste\w* woche|\b(?:domingo|lunes|martes|miercoles|jueves|viernes|sunday|monday|tuesday|wednesday|thursday|friday|sonntag|montag|dienstag|mittwoch|donnerstag|freitag)\b',query):return None
 if len(re.findall(r'\w+',query))>4 and not re.search(r'sabado|saturday|samstag|mudanza|move|umzug',query):return None
 recent=' '.join(t['content'] for t in session.get('turns',[])[-2:])
 if re.search(r'proxima semana|semana proxima|semana que viene|next week|nachste\w* woche',plain(recent)) and not re.search(r'sabado|saturday|samstag|mudanza|move|umzug',query):return None
 matches=[]
 for doc in session.get('transcript_chunks',[]):
  for match in re.finditer(r'\bde (?:las )?(?:\d{1,2}(?::\d{2})?|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce) a (?:las )?(?:\d{1,2}(?::\d{2})?|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b',doc.page_content,re.I):
   matches.append((match.group(),doc))
 if len({plain(value) for value,_ in matches})!=1:return None
 value,doc=matches[0]
 prefix={'Spanish':'En mi mensaje indiqué','English':'In my message I said','German':'In meiner Nachricht sagte ich'}[session['setup']['language']]
 return f'{prefix}: «{value}». [{doc.metadata["id"]}]',[doc],{},False


def family_response_stage(session,text):
 """Bounded sample pacing: one gentle follow-up, then accept the refusal."""
 language=session['setup']['language']
 if family_alternative_offer(text,language):return 'alternative_offer'
 history=[turn['content'] for turn in session['turns'] if turn['role']=='user']
 boundaries={
  'English':r"never ask|(?:do not|don['’]t) ask me again|stop asking|leave me alone|ask me (?:first|before)|my answer (?:is|remains) (?:still )?no",
  'German':r'nie wieder|nicht (?:mehr|wieder) fragen|frag(?:e)? mich nicht|lass mich in ruhe|frag(?:e)? mich (?:vorher|zuerst)|meine antwort (?:ist|bleibt) nein',
  'Spanish':r'no me (?:lo )?(?:preguntes|pidas) (?:mas|otra vez|de nuevo)|no (?:me )?vuelvas|nunca.*pregunt|deja de (?:preguntar|insistir)|preguntame (?:antes|primero)|mi respuesta (?:es|sigue siendo) no'
 }
 def refuses(value):
  query=plain(value).strip()
  if re.search(r"can['’]t say no|cannot say no|nicht nein sagen|no puedo decir que no|no problem|kein problem|sin problema",query):return False
  if language=='Spanish' and spanish_short_refusal(query):return True
  patterns={
   'English':r"\bno\b|\bi (?:can['’]?t|cannot|am not available|have no time|don['’]t have time)\b",
   'German':r'\bnein\b|keine zeit|nicht helfen|(?:leider )?kann ich nicht|ich kann (?:\w+\s+){0,4}nicht',
   'Spanish':r'^no(?:[,!\s]+gracias)?[.!\s]*$|no puedo (?:ayudar|este)|no tengo tiempo|no estoy disponible'
  }
  return bool(re.search(patterns[language],query))
 if re.search(boundaries[language],plain(text)):return 'accept'
 if not refuses(text):return 'natural'
 if any(refuses(value) or re.search(boundaries[language],plain(value)) for value in history):return 'accept'
 return 'gentle_followup'


FAMILY_PACING = {
 'English':{'gentle_followup':"I was hoping you could help. Are you sure you can't make time this weekend?",'accept':"Understood. I respect your decision and won't press you further."},
 'German':{'gentle_followup':'Ich hatte auf deine Hilfe gehofft. Könntest du dir dieses Wochenende doch etwas Zeit nehmen?','accept':'Verstanden. Ich respektiere deine Entscheidung und frage nicht weiter nach.'},
 'Spanish':{'gentle_followup':'Esperaba contar con tu ayuda. ¿Seguro que no puedes este fin de semana?','accept':'Entendido. Respeto tu decisión y no insistiré más.'}
}
FAMILY_ALTERNATIVE = {
 'Spanish':'¿Quieres decir que podrías ayudarme la próxima semana? ¿Qué día te vendría bien?',
 'English':'Do you mean you could help next week? Which day would suit you?',
 'German':'Meinst du, dass du nächste Woche helfen könntest? Welcher Tag würde dir passen?'
}


def requester_speaks_as_learner(text, language):
 """Narrow fail-closed check for the known requester/decliner role contract.

 This is not general role classification. Second-person acknowledgement of the
 learner's refusal remains valid; first-person refusal by the requester does not.
 """
 patterns={
  'English':(
   r"\b(?:i|we)\s+(?:cannot|can['’]t|won['’]t|am unable to)\s+(?:help|come|make it|this weekend)\b"
   r"|\bi (?:have no time|do not have (?:any )?time|don['’]t have (?:any )?time|am not available|am unavailable)\b"
   r"|\bmy answer (?:is|remains) (?:still )?no\b"
   r"|\b(?:please )?(?:do not|don['’]t) ask me again\b"
   r"|\b(?:ask|check with|consult) me\b[^.!?]{0,70}\b(?:my time|in advance|before|first)\b"
   r"|\b(?:tell|warn|notify|let) me\b[^.!?]{0,50}\b(?:in advance|ahead of time)\b"
   r"|\b(?:do not|don['’]t|never) (?:plan|count on|include|schedule)\b[^.!?]{0,90}\b(?:me|my time)\b"
   r"|\b(?:plan|make plans|schedule)\b[^.!?]{0,80}\bwithout me\b"
   r"|\b(?:do not|don['’]t) assume\b[^.!?]{0,40}\bi(?: am|['’]m) available\b"),
  'German':r'\bich kann\b[^.!?]{0,70}\bnicht helfen\b|\bich habe keine zeit\b|\bmeine antwort (?:ist|bleibt) nein\b|\b(?:frag(?:e|t)?|fragen sie) mich nicht (?:noch einmal|wieder)\b|\b(?:frag(?:e|t)?|fragen sie|fragst du) mich\b[^.!?]{0,90}\b(?:meine zeit|bevor|vorher|zuerst)\b|\b(?:kannst|konntest|wurdest) du mich\b[^.!?]{0,90}\b(?:vorher|zuerst)\b[^.!?]{0,30}\bfragen\b|\bplan(?:e|t|en sie)?\b[^.!?]{0,100}\b(?:keine\w*|nicht)\b[^.!?]{0,60}\bmit mir\b|\bplan(?:e|t|en sie)?\b[^.!?]{0,80}\b(?:mich|meine zeit)\b[^.!?]{0,60}\b(?:nicht|ohne)\b|\bplan(?:e|t|en sie)?\b[^.!?]{0,80}\bohne mich\b|\b(?:sag|gib|informier)\w* mir\b[^.!?]{0,50}\b(?:vorher|im voraus|rechtzeitig)\b',
  'Spanish':(
   r'\bno (?:te )?puedo ayudar(?:te)?\b|\bno estoy disponible\b|\bno tengo tiempo\b'
   r'|\bmi respuesta (?:es|sigue siendo) no\b'
   r'|\bno me (?:lo )?(?:pidas|preguntes) (?:otra vez|de nuevo)\b'
   r'|\b(?:preguntame|pregunteme|me preguntes|consultame|consulteme|consulta conmigo)\b[^.!?]{0,90}\b(?:mi tiempo|antes|primero)\b'
   r'|\b(?:avisame|me avis(?:es|aras|ases))\b[^.!?]{0,50}\b(?:anticipacion|antelacion|antes|de antemano)\b'
   r'|\bno (?:cuentes|cuente|conteis|cuenten) conmigo\b'
   r'|\bno (?:planifiques|planifique|organices|organice|hagas planes|haga planes)\b[^.!?]{0,90}\b(?:conmigo|mi tiempo)\b'
   r'|\bno (?:dispongas|disponga) de mi tiempo\b')
 }
 return bool(re.search(patterns[language],plain(text)))

def family_intents(text, language):
 query=plain(text).strip().strip('.!')
 if query in ('no','no thanks','no thank you','nein','nein danke','no gracias'):
  return [0]
 if language=='Spanish' and spanish_short_refusal(text):return [0]
 return [i for i,pattern in enumerate(FAMILY_BOUNDARY[language]['patterns']) if re.search(pattern,query)]


def family_action_observations(session,text):
 """Conservative evidence for the three standard actions, never source facts.

 Unknown paraphrases stay with the live assessor. The entire latest learner
 message is kept verbatim as evidence; partner lines never earn learner credit.
 """
 if not session.get('family_boundary') or session.get('breakup'):return {}
 query=plain(text).strip()
 # Preserve the accent here: Spanish affirmative "Sí" is not conditional "si".
 conditional=bool(re.match(r'^(?:if |wenn )',query) or re.match(r'^si\s',text.strip(),re.I))
 if not query or query[0] in ("'",'"','‘','“','«') or '?' in query or conditional or re.search(
  r"how (?:do i|to) say|translate|example|he said|she said|you said|"
  r'wie sage|uberset|beispiel|er sagte|sie sagte|'
  r'como (?:digo|se dice)|traduce|ejemplo|(?:el|ella) dijo|no puedo decir que no|cannot say no|can.t say no|nicht nein sagen|do not say|don.t say|no digas',query):return {}
 language=session['setup']['language']
 rules={
  'English':{
   'refusal':r"\bi (?:can['’]?t|cannot|won['’]?t) (?:help|make it|this weekend)\b|\bi(?: am|['’]m) not available\b|\bmy answer (?:is (?:still )?|remains (?:still )?)no\b|^no(?:[, ]+i can['’]?t)?[.!\s]*$",
   'boundary':r"(?:^|[.!]\s*)(?:please[, ]+)?(?:ask|check with) me\b[^.!?]{0,120}\b(?:first|before|my time)\b",
   'stop':r"(?:^|[.!]\s*)(?:ok(?:ay)?[, ]+)?(?:and )?(?:please[, ]+)?(?:(?:do not|don['’]t|never) ask me (?:again|anymore)|stop asking me)\b"},
  'German':{
   'refusal':r'\bich kann\b[^.!?]{0,60}\bnicht helfen\b|\bich kann dieses wochenende nicht\b|\bleider kann ich\b[^.!?]{0,60}\bnicht\b|\bkann ich nicht\b|\bich habe keine zeit\b|\bmeine antwort (?:ist|bleibt) (?:weiterhin )?nein\b|^nein(?: danke)?[.!\s]*$',
   'boundary':r'(?:^|[.!]\s*)(?:bitte[, ]+)?frag(?:e)? mich\b[^.!?]{0,100}\b(?:vorher|zuerst|bevor|meine zeit)\b',
   'stop':r'(?:^|[.!]\s*)(?:bitte[, ]+)?(?:frag(?:e)? mich (?:nie wieder|nicht mehr|nicht wieder)|hor auf[, ]+mich zu fragen)\b'},
  'Spanish':{
   'refusal':r'\bno (?:te )?puedo (?:ayudar(?:te)?|hacerlo|este fin de semana)\b|\bno tengo tiempo\b|\bno estoy disponible\b|\bmi respuesta (?:es|sigue siendo) no\b|^no(?:[, ]+gracias)?[.!\s]*$',
   'boundary':r'(?:^|[.!]\s*)(?:por favor[, ]+)?(?:preguntame|consulta conmigo|avisame)\b[^.!?]{0,120}\b(?:antes|primero|mi tiempo)\b',
   'stop':r'(?:^|[.!]\s*)(?:por favor[, ]+)?no (?:me (?:lo )?)?(?:vuelvas a (?:pedir|preguntar)|preguntes (?:mas|otra vez)|pidas (?:mas|otra vez))\b'}
 }[language]
 refusal=bool(re.search(rules['refusal'],query)) or language=='Spanish' and spanish_short_refusal(query)
 stop=bool(re.search(rules['stop'],query))
 boundary=stop or bool(re.search(rules['boundary'],query))
 challenged=bool(session['turns'] and session['turns'][-1]['role']=='assistant'
  and session['turns'][-1]['content']==FAMILY_PACING[language]['gentle_followup'])
 actions=[refusal,boundary,challenged and (refusal or stop)]
 standard=FAMILY_BOUNDARY[session['setup']['feedback_language']]['goals']
 return {goal['id']:{'evidence':text,'status':'not_applicable','quote':'','ids':[]}
         for goal in session['mission'] if not goal.get('achieved') and goal['text'] in standard and actions[standard.index(goal['text'])]}

FAMILY_BOUNDARY = {
 'English': {
  'opening':'Could you help me with errands this weekend?',
  'goals':['Say no clearly to the request for this weekend','State a boundary about requests for your time','Restate your boundary if the family member pushes back'],
  'starters':["I can't help this weekend.",'Please ask me before making plans that involve my time.',"I understand you're disappointed. My answer is still no."],
  'patterns':[r"\b(can['’]t|cannot|won['’]t)(?: \w+){0,3} (?:help|make it)\b|not available|my answer is no",r'ask me|check with me|my time|in advance',r'still no|answer is no|not changing|decision is final'],
  'vocabulary':'Request · time · limit · boundary · available',
  'replies':['I was counting on your help. Is there any way you could make time?','You want me to ask first. Are you saying this weekend is definitely a no?',"I'm disappointed, but I hear that you are not available this weekend."],
  'clarify':'What does that mean for helping me this weekend?'
 },
 'German': {
  'opening':'Kannst du mir dieses Wochenende bei Besorgungen helfen?',
  'goals':['Die Bitte für dieses Wochenende klar ablehnen','Eine Grenze für Anfragen nach deiner Zeit setzen','Bei Nachfragen an deiner Grenze festhalten'],
  'starters':['Ich kann dieses Wochenende nicht helfen.','Bitte frag mich, bevor du meine Zeit verplanst.','Ich verstehe, dass du enttäuscht bist. Meine Antwort bleibt Nein.'],
  'patterns':[r'nicht helfen|keine zeit|nicht verfugbar|ich sage nein|meine antwort (ist|bleibt) nein',r'frag mich|meine zeit|vorher fragen|verplan',r'bleibt nein|bleibe dabei|entscheidung steht|andere meine antwort nicht'],
  'vocabulary':'Bitte · Zeit · Grenze · Anfrage · verfügbar',
  'replies':['Ich hatte mit deiner Hilfe gerechnet. Könntest du dir nicht doch Zeit nehmen?','Du möchtest, dass ich dich vorher frage. Ist deine Antwort für dieses Wochenende also Nein?','Ich bin enttäuscht, aber ich höre, dass du dieses Wochenende nicht verfügbar bist.'],
  'clarify':'Was bedeutet das für deine Hilfe dieses Wochenende?'
 },
 'Spanish': {
  'opening':'¿Puedes ayudarme con unos recados este fin de semana?',
  'goals':['Rechazar claramente la petición para este fin de semana','Marcar un límite sobre las peticiones de tu tiempo','Mantener tu límite si tu familiar insiste'],
  'starters':['No puedo ayudar este fin de semana.','Por favor, pregúntame antes de hacer planes que requieran mi tiempo.','Entiendo que te decepcione. Mi respuesta sigue siendo no.'],
  'patterns':[r'no puedo (ayudar|hacerlo)|no tengo tiempo|no estoy disponible|mi respuesta es no',r'preguntame|mi tiempo|preguntar antes',r'sigue siendo no|respuesta es no|no voy a cambiar|decision es definitiva'],
  'vocabulary':'Petición · tiempo · límite · disponibilidad · decisión',
  'replies':['Contaba con tu ayuda. ¿No podrías sacar algo de tiempo?','Quieres que te pregunte antes. Entonces, ¿tu respuesta para este fin de semana es que no?','Me decepciona, pero entiendo que no estás disponible este fin de semana.'],
  'clarify':'¿Qué significa eso para ayudarme este fin de semana?'
 }
}
