"""Bounded rental-claim backstops, in addition to independent model review.

These checks catch missing policy/date evidence and explicit inclusion reversals;
they do not establish general entailment or resolve which property a fact concerns.
"""
import re
from backend.demo_answers import plain

PET = r'\b(?:pets?|mascotas?|haustiere?)\b'
DATE = r'\b(?:available|availability|move.in|disponib\w*|entrar|einzug|verfugbar|frei ab)\b'
UTILITY = r'\b(?:utilities|bills|gas|water|electricity|gastos|recibos|agua|luz|strom|wasser|nebenkosten)\b'
INCLUDED = r'\b(?:included|incluid[oa]s?|inbegriffen|enthalten)\b'
NEGATIVE = r'\b(?:not|no|nicht|excluded|excluid[oa]s?)\b'
UNKNOWN = r'\b(?:unknown|unspecified|not (?:specified|stated|confirmed|mentioned)|cannot confirm|can.t confirm|i (?:do not|don.t) have confirmation of whether|no puedo confirmar|no tengo confirmad[oa]|no (?:se )?(?:especifica|indica|menciona)|nicht (?:angegeben|bekannt|bestatigt)|kann.{0,20}nicht bestatigen)\b'


def rental_price_question(text):
    value=plain(text)
    if re.search(r'\b(?:deposit|fianza|kaution|utilities|bills|gastos|nebenkosten)\b',value):
        return False
    return bool(re.search(r'\b(?:cuesta|cuestan|precio|price|kostet|mietpreis)\b|\bhow much\b|\bwie (?:viel|hoch)\b',value))


def unsupported_rental_claim(reply, cited_docs, context_docs):
    """True means withhold; false still requires independent evidence review."""
    cited=' '.join(plain(d.page_content) for d in cited_docs)
    source=' '.join(plain(d.page_content) for d in sorted(context_docs,key=lambda d:d.metadata.get('start',0)))
    for match in re.finditer(r'[^.!?\n]+[.!?]?',plain(reply)):
        sentence=match.group().strip()
        if not sentence or sentence.endswith('?') or re.search(UNKNOWN,sentence):
            continue
        pet_assertion=re.search(PET,sentence) and re.search(r'\b(?:allowed|permitted|prohibited|permit\w*|admit\w*|prohib\w*|erlaubt|gestattet|verboten)\b',sentence)
        date_assertion=re.search(DATE,sentence) and re.search(r'\b(?:from|on|next|tomorrow|today|a partir|proxim\w*|semana|mes|hoy|manana|ab|nachst\w*)\b|\d',sentence)
        if pet_assertion and not re.search(PET,cited):
            return True
        if date_assertion and not re.search(DATE,cited):
            return True
        if re.search(UTILITY,sentence) and re.search(INCLUDED,sentence):
            # Caption context is ordered, allowing a predicate to follow its
            # subject in another timestamp block. Bound the clause length.
            def excluded(value):
                return bool(re.search(NEGATIVE+r'\s+(?:\w+\s+){0,3}'+INCLUDED,value))
            for match in re.finditer(UTILITY+r'.{0,140}?'+INCLUDED,source):
                if excluded(sentence) != excluded(match.group()):
                    return True
    return False
