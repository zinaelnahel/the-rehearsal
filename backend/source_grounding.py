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
    return bool(re.search(r'\b(?:cuesta|cuesto|cuestan|precio|price|kostet|mietpreis)\b|\bhow much\b|\bwie (?:viel|hoch)\b',value))


LEASE_REF=r'\b(?:lease|tenancy|contract|duration|term|stay|contrato|duracion|estancia|plazo|minim\w*|vertrag\w*|mietdauer|laufzeit|mindest\w*)\b'
PERIOD=re.compile(r'\b(\d+|one|two|three|six|twelve|a|un|uno|una|dos|tres|seis|doce|ein|eine|einen|einem|eins|zwei|drei|sechs|zwolf)[ -]+(months?|years?|mes(?:es)?|anos?|monate?n?|jahre?n?)\b')
NUMBERS={'one':1,'a':1,'un':1,'uno':1,'una':1,'ein':1,'eine':1,'einen':1,'einem':1,'eins':1,'two':2,'dos':2,'zwei':2,'three':3,'tres':3,'drei':3,'six':6,'seis':6,'sechs':6,'twelve':12,'doce':12,'zwolf':12}


def lease_periods(text):
    periods=set()
    for match in PERIOD.finditer(text):
        count=int(match[1]) if match[1].isdigit() else NUMBERS[match[1]]
        periods.add(count*12 if match[2].startswith(('year','ano','jahr')) else count)
    return periods


def unsupported_lease_claim(reply,cited):
    supported=set()
    split=r'[.!?;\n]+|\b(?:and|y|und|but|pero|aber)\b'
    for clause in re.split(split,cited):
        if re.search(LEASE_REF,clause) and not re.search(r'\b(?:deposit|fianza|kaution)\b',clause):
            supported.update(lease_periods(clause))
    for sentence in re.finditer(r'[^.!?\n]+[.!?]?',plain(reply)):
        if sentence.group().endswith('?'):continue
        for clause in re.split(split,sentence.group()):
            if re.search(UNKNOWN,clause):continue
            if re.search(LEASE_REF,clause) and not lease_periods(clause)<=supported:
                return True
    return False


def unsupported_rental_claim(reply, cited_docs, context_docs):
    """True means withhold; false still requires independent evidence review."""
    cited=' '.join(plain(d.page_content) for d in cited_docs)
    source=' '.join(plain(d.page_content) for d in sorted(context_docs,key=lambda d:d.metadata.get('start',0)))
    if unsupported_lease_claim(reply,'\n'.join(plain(d.page_content) for d in cited_docs)):
        return True
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
