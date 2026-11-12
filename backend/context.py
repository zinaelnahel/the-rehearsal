"""Conversation context and role instructions shared by demo and live workflows."""
import re
from backend.text import normalize as plain

CONTEXT_RULES = ('Respect the stated relationship, scenario and intended outcome. A final breakup is final, not a trial separation: never suggest a break, reconciliation or negotiation of that decision. Do not assume compromise, continued contact or agreement is desired. For boundary-setting goals, a clear no can be sufficient: do not require an apology, detailed justification or an alternative offer, or invent a family relationship or history. Do not supply a reason for refusal that the user has not given. Keep sensitive scenes sincere. Never diagnose or claim to treat anxiety. Stay respectful and adapt to the stated situation. Do not diagnose or claim to provide therapy or emergency support. ')

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
