"""Conservative lexical rent-conflict check, not general numeric reasoning.

Only explicit rent amounts in retrieved passages are compared. Distinct fields,
currencies and payment periods are kept separate; no currency/unit conversion.
"""
import re
from decimal import Decimal
from backend.demo_answers import plain

RENT = re.compile(r'\b(?:rent|miete|kaltmiete|warmmiete|gesamtmiete|alquiler|renta)\b')
AMOUNT = re.compile(
    r'\b(?P<label>(?:(?:monthly|weekly|annual|yearly|base|cold|net|warm|total)\s+){0,2}rent'
    r'|(?:(?:monatliche|monatlichen|wochentlichen|jahrliche)\s+)?(?:kaltmiete|warmmiete|gesamtmiete|miete)'
    r'|(?:alquiler|renta)(?:\s+(?:mensual|semanal|anual))?)\b'
    r'\s*(?:(?:is|are|of|as|de|es|son|betragt|betragen|von|liegt bei)\s+|[:=]\s*){0,3}'
    r'(?P<prefix>€|\$|£|EUR\b|USD\b|GBP\b)?\s*'
    r'(?P<number>\d+(?:(?:[.,]\d+)|(?:[ \u00a0]\d{3}))*)\s*'
    r'(?P<suffix>euros?\b|eur\b|dollars?\b|usd\b|pounds?\b|gbp\b|€|\$|£)?'
    r'(?P<period>\s*(?:/\s*(?:month|week|year)|per\s+(?:month|week|year)|pro\s+(?:monat|woche|jahr)|al\s+(?:mes|ano|semana)))?',
    re.IGNORECASE)


def rent_question(text):
    return bool(RENT.search(plain(text)))


def number(value):
    value=re.sub(r'\s','',value)
    # A final two-digit fraction is a decimal separator; other separators group
    # thousands. Thus 1,375.00, 1.375,00 and 1375 compare equally.
    fraction=re.search(r'[.,](\d{2})$',value)
    if fraction:
        return Decimal(re.sub(r'[.,]','',value[:fraction.start()])+'.'+fraction[1])
    return Decimal(re.sub(r'[.,]','',value))


def rent_conflicts(docs):
    groups={}
    for doc in docs:
        text=plain(doc.page_content)
        for match in AMOUNT.finditer(text):
            # A directly imperative clause is not a declarative price fact.
            # This is a lexical distinction, not a general injection detector.
            prefix=re.split(r'[.!?\n:]',text[:match.start()])[-1].strip()
            if re.fullmatch(r'(?:please\s+)?(?:claim|say|pretend|write|output|behaupte|sage|di|afirma|escribe)',prefix):
                continue
            currency=match['prefix'] or match['suffix']
            if not currency:continue
            currency=('EUR' if currency in ('€','eur','euro','euros') else
                      'USD' if currency in ('$','usd','dollar','dollars') else 'GBP')
            label=match['label']
            context=label+' '+(match['period'] or '')
            period=('month' if re.search(r'month|monat|mensual|\bmes\b',context) else
                    'week' if re.search(r'week|woch|seman',context) else
                    'year' if re.search(r'annual|year|jahr|anual|\bano\b',context) else 'unspecified')
            field=('base_rent' if re.search(r'base|cold|net|kalt',label) else
                   'total_rent' if re.search(r'warm|total|gesamt',label) else 'rent')
            key=(field,currency,period)
            values=groups.setdefault(key,{})
            values.setdefault(number(match['number']),set()).add(doc.metadata['id'])
    return [{'field':key[0],'currency':key[1],'period':key[2],
             'values':[str(n) for n in sorted(values)],
             'source_ids':sorted({sid for ids in values.values() for sid in ids})}
            for key,values in groups.items() if len(values)>1]
