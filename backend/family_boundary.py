"""Fictional family-boundary sample, separate from custom difficult conversations."""
import re
from backend.context import plain


def requester_speaks_as_learner(text, language):
 """Narrow fail-closed check for the known requester/decliner role contract.

 This is not general role classification. Second-person acknowledgement of the
 learner's refusal remains valid; first-person refusal by the requester does not.
 """
 patterns={
  'English':r"\b(?:i|we)\s+(?:cannot|can['’]t|won['’]t|am unable to)\s+(?:help|come|make it)\b|\bmy answer (?:is|remains) (?:still )?no\b|\b(?:please )?(?:do not|don['’]t) ask me again\b|\b(?:ask|check with) me\b[^.!?]{0,70}\b(?:my time|in advance|before)\b|\b(?:tell|warn|notify|let) me\b[^.!?]{0,50}\b(?:in advance|ahead of time)\b",
  'German':r'\bich kann\b[^.!?]{0,70}\bnicht helfen\b|\bich habe keine zeit\b|\bmeine antwort (?:ist|bleibt) nein\b|\bfrag mich nicht (?:noch einmal|wieder)\b|\bfrag mich\b[^.!?]{0,70}\b(?:meine zeit|bevor|vorher)\b|\b(?:sag|gib|informier)\w* mir\b[^.!?]{0,50}\b(?:vorher|im voraus|rechtzeitig)\b',
  'Spanish':r'\bno (?:te )?puedo ayudar(?:te)?\b|\bno estoy disponible\b|\bmi respuesta (?:es|sigue siendo) no\b|\bno me (?:lo )?(?:pidas|preguntes) (?:otra vez|de nuevo)\b|\b(?:preguntame|me preguntes)\b[^.!?]{0,70}\b(?:mi tiempo|antes)\b|\b(?:avisame|me avises)\b[^.!?]{0,50}\b(?:anticipacion|antelacion|antes)\b'
 }
 return bool(re.search(patterns[language],plain(text)))

def family_intents(text, language):
 query=plain(text).strip().strip('.!')
 if query in ('no','no thanks','no thank you','nein','nein danke','no gracias'):
  return [0]
 return [i for i,pattern in enumerate(FAMILY_BOUNDARY[language]['patterns']) if re.search(pattern,query)]

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
