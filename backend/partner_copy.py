"""In-character uncertainty, without invented answers or promises to act."""
import re
from backend.demo_answers import plain
from backend.source_grounding import rental_price_question


def uncertain_reply(language, scenario, text):
    topic='general'
    if scenario=='apartment':
        value=plain(text)
        topics=[]
        if re.search(r'\b(?:pets?|mascotas?|haustiere?)\b',value):
            topics.append('pets')
        if re.search(r'\b(?:move[ -]?in|moving|availability|available|mudarm\w*|mudars\w*|mudanza|entrar|disponib\w*|einzieh\w*|einzug|verfugbar)\b',value):
            topics.append('move_in')
        if rental_price_question(text):
            topics.append('rent')
        if re.search(r'\b(?:lease|contract|duration|contrato|duracion|estancia|vertrag\w*|mietdauer|laufzeit)\b',value):
            topics.append('lease')
        topic=topics[0] if len(topics)==1 else 'apartment'
    return {
        'English':{
            'general':"I don't have that confirmed yet.",
            'apartment':"I don't have that detail confirmed for this flat yet.",
            'pets':"I don't have confirmation of whether pets are allowed in this flat.",
            'move_in':"I don't have a confirmed move-in date for this flat yet.",
            'lease':"I don't have the available lease lengths confirmed for this flat.",
            'rent':"I don't have a confirmed rent amount for this flat yet."},
        'German':{
            'general':'Das kann ich noch nicht bestätigen.',
            'apartment':'Diese Angabe kann ich für diese Wohnung noch nicht bestätigen.',
            'pets':'Ob Haustiere in dieser Wohnung erlaubt sind, kann ich noch nicht bestätigen.',
            'move_in':'Einen Einzugstermin kann ich für diese Wohnung noch nicht bestätigen.',
            'lease':'Die möglichen Mietlaufzeiten kann ich für diese Wohnung noch nicht bestätigen.',
            'rent':'Die Höhe der Miete kann ich für diese Wohnung noch nicht bestätigen.'},
        'Spanish':{
            'general':'Todavía no tengo esa información confirmada.',
            'apartment':'Todavía no tengo ese dato confirmado para este piso.',
            'pets':'No tengo confirmado si se permiten mascotas en este piso.',
            'move_in':'Todavía no tengo una fecha de entrada confirmada para este piso.',
            'lease':'No tengo confirmadas las opciones de duración del contrato para este piso.',
            'rent':'Todavía no tengo el importe del alquiler confirmado para este piso.'}
    }[language][topic]
