"""Small, explicit context safeguards shared by demo and live workflows."""
import re
import unicodedata

def plain(text):
 return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

def safety_concern(text):
 return bool(re.search(r'\b(fear|afraid|scared|unsafe|threat\w*|coerci\w*|violence|abuse|stalking|immediate danger|angst|bedroh\w*|gewalt|notigen|miedo|amenaz\w*|coaccion\w*|violencia|peligro)\b', plain(text)) or re.search(r'(will not|won.t|would not|does not|doesn.t) let me leave|took my (phone|passport)|lasst mich nicht.{0,30}(raus|verlassen|aus dem)|handy (weggenommen|genommen)|no me deja salir|me ha quitado el (telefono|pasaporte)', plain(text)))

SAFETY = {
 'English': 'Let’s pause the rehearsal. Your safety matters more than finding the right words. If you are in immediate danger, contact local emergency services if you can do so safely. Consider reaching someone you trust or a local support service, using a device that is safe for you. You do not have to confront the other person or continue this scene. This app is conversation practice, not therapy or emergency support.',
 'German': 'Pausieren wir die Übung. Deine Sicherheit ist wichtiger als die richtigen Worte. Bei unmittelbarer Gefahr kontaktiere den örtlichen Notruf, wenn das sicher möglich ist. Wende dich nach Möglichkeit an eine vertraute Person oder eine lokale Beratungsstelle und nutze ein sicheres Gerät. Du musst die andere Person nicht konfrontieren oder diese Szene fortsetzen. Diese App bietet Gesprächsübungen, keine Therapie oder Notfallhilfe.',
 'Spanish': 'Paremos el ensayo. Tu seguridad importa más que encontrar las palabras adecuadas. Si hay peligro inmediato, contacta con los servicios de emergencia locales si puedes hacerlo de forma segura. Considera acudir a alguien de confianza o a un servicio de apoyo local, desde un dispositivo seguro. No tienes que confrontar a la otra persona ni continuar esta escena. Esta aplicación sirve para practicar conversaciones, no ofrece terapia ni asistencia de emergencia.'
}

CONTEXT_RULES = ('Respect the stated relationship, scenario and intended outcome. A final breakup is final, not a trial separation: never suggest a break, reconciliation or negotiation of that decision. Do not assume compromise, continued contact or agreement is desired. For boundary-setting goals, a clear no can be sufficient: do not require an apology, detailed justification or an alternative offer, or invent a family relationship or history. Do not supply a reason for refusal that the user has not given. Keep sensitive scenes sincere. Never diagnose or claim to treat anxiety. If fear, threats, coercion or safety concerns appear, stop ordinary role-play and prioritize calm safety support; never encourage confrontation. ')

def is_final_breakup(text):
 return bool(re.search(r'\b(break\s?up|end (?:the|my|our) relationship|trenn\w*|schluss machen|ruptura|terminar (?:la|mi|nuestra) relacion)\b', plain(text)))

BREAKUP = {
 'English': {
  'goals': ['State clearly that you are ending the relationship', 'Express your boundary without inviting negotiation', 'State what contact, if any, you want next'],
  'starters': ['I am ending our relationship. This is my decision.', 'I understand this is difficult, but my decision is final.', 'I do not want further contact.'],
  'opening': 'You said you wanted to talk. What is it?',
  'reply': 'That is difficult to hear. Are you saying your decision is final?',
  'patterns': [r'ending|end our|break.?up', r'final|decision|not negotiat', r'contact|space|belongings'],
  'vocabulary': 'Decision · boundary · contact · belongings'},
 'German': {
  'goals': ['Klar sagen, dass du die Beziehung beendest', 'Deine Grenze ohne Verhandlungsangebot ausdrücken', 'Sagen, welchen Kontakt du künftig möchtest, falls überhaupt'],
  'starters': ['Ich beende unsere Beziehung. Das ist meine Entscheidung.', 'Ich verstehe, dass das schwer ist, aber meine Entscheidung steht fest.', 'Ich möchte keinen weiteren Kontakt.'],
  'opening': 'Du wolltest mit mir sprechen. Worum geht es?',
  'reply': 'Das ist schwer zu hören. Steht deine Entscheidung fest?',
  'patterns': [r'beende|trenn|schluss', r'fest|entscheidung|verhandel', r'kontakt|abstand|sachen'],
  'vocabulary': 'Entscheidung · Grenze · Kontakt · persönliche Sachen'},
 'Spanish': {
  'goals': ['Decir claramente que terminas la relación', 'Expresar tu límite sin invitar a negociar', 'Indicar qué contacto quieres después, si lo quieres'],
  'starters': ['Termino nuestra relación. Es mi decisión.', 'Entiendo que es difícil, pero mi decisión es definitiva.', 'No quiero mantener el contacto.'],
  'opening': 'Querías hablar conmigo. ¿Qué pasa?',
  'reply': 'Es difícil escuchar eso. ¿Tu decisión es definitiva?',
  'patterns': [r'termino|terminar|ruptura', r'definitiv|decision|negoci', r'contacto|espacio|cosas'],
  'vocabulary': 'Decisión · límite · contacto · pertenencias'}
}
