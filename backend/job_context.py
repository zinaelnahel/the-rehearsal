"""Keep explicit work-arrangement evidence in short interview questions."""
import re
from backend.embeddings import normalize
from backend.demo_answers import asks_question
from backend.citation_focus import focused_documents

WORK_ARRANGEMENT = re.compile(
 r'\b(?:remote(?:ly)?|hybrid\w*|homeoffice|home office|telework\w*|'
 r'teletrabaj\w*|remot[oa]s?|hibrid[oa]s?|presencial\w*|'
 r'work(?:ing)? from home|trabajar (?:desde|en) casa|von (?:zu )?hause|'
 r'im buro|in (?:the )?office)\b')

SALARY = re.compile(r'\b(?:salary|pay|wages?|compensation|salario|sueldo|remuneracion|gehalt|vergutung|lohn)\b')
BENEFITS = re.compile(r'\b(?:benefits?|perks?|beneficios|prestaciones|vorteile|zusatzleistungen)\b')


def benefit_excerpts(session):
    """Return complete bullets under an explicit benefits heading with chunk evidence."""
    chunks = session.get('source_chunks', {})
    results = []
    for source in session.get('source_documents', chunks.values()):
        active = False
        for line in source.page_content.splitlines():
            line = line.strip()
            if normalize(line) in {'your benefits', 'benefits', 'beneficios', 'tus beneficios', 'ihre vorteile', 'deine vorteile'}:
                active = True
                continue
            if not active or not line:
                continue
            if not line.startswith(('-', '•')):
                active = False
                continue
            match = next((doc for doc in chunks.values() if line in doc.page_content), None)
            if match and all(existing[0] != line for existing in results):
                results.append((line, match))
    return results

# Extract whole, explicitly labelled fields only. Never infer a remote policy
# from a question, an arbitrary mention, or a clipped part of a source sentence.
ARRANGEMENT_FIELD = re.compile(
 r'^(?:remote\s*,\s*[a-z]{2}\s*\|\s*[^\n]{1,100}|'
 r'(?:work(?:ing)? arrangement|work model|remote work|arbeitsmodell|arbeitsort|'
 r'modalidad de trabajo|teletrabajo)\s*:\s*[^\n]{1,200})$', re.I)
SALARY_FIELD = re.compile(
 r'^(?:salary|pay|wage|compensation|salario|sueldo|remuneraci[oó]n|gehalt|verg[uü]tung|lohn)\s*:\s*[^\n]{1,200}$', re.I)


def mixed_job_answer(session, query, docs):
    """Bounded extractive recovery, not semantic verification or goal credit.

    Preserve a complete labelled work-arrangement field when a model reply was
    rejected or omitted it. Quote source text unchanged, including restrictions
    or negation. Salary is handled separately and is never inferred from silence.
    Only server-owned session chunks can supply an excerpt and its citation.
    """
    if not asks_question(query) or not work_arrangement_question(query) or not SALARY.search(normalize(query)):
        return None
    chunks = session.get('source_chunks', {})
    full_lines = {line.strip() for doc in session.get('source_documents', chunks.values())
                  for line in doc.page_content.splitlines()}
    work_fields = {}
    salary_fields = {}
    for doc in [*docs, *chunks.values()]:
        identifier = doc.metadata['id']
        original = chunks.get(identifier)
        if original is None or original.page_content != doc.page_content:
            continue
        for line in doc.page_content.splitlines():
            line = line.strip()
            if line not in full_lines:
                continue
            if ARRANGEMENT_FIELD.fullmatch(line):
                work_fields.setdefault(line, doc)
            if SALARY_FIELD.fullmatch(line):
                salary_fields.setdefault(line, doc)
    if len(work_fields) != 1 or len(salary_fields) > 1:
        return None
    work = next(iter(work_fields.items()))
    salary = next(iter(salary_fields.items())) if salary_fields else None
    language = session['setup']['language']
    labels = {
        'English': ('For the work arrangement, the advert states', 'For salary, the advert states', "I don't have a confirmed salary figure."),
        'German': ('Zum Arbeitsmodell steht in der Anzeige', 'Zum Gehalt steht in der Anzeige', 'Eine bestätigte Gehaltsangabe liegt mir nicht vor.'),
        'Spanish': ('Sobre la modalidad de trabajo, el anuncio indica', 'Sobre el salario, el anuncio indica', 'No tengo una cifra salarial confirmada.')
    }[language]
    text = f'{labels[0]}: «{work[0]}» [{work[1].metadata["id"]}].'
    cited = [work[1]]
    if salary:
        text += f' {labels[1]}: «{salary[0]}» [{salary[1].metadata["id"]}].'
        if salary[1] not in cited:
            cited.append(salary[1])
    else:
        text += ' ' + labels[2]
    if BENEFITS.search(normalize(query)):
        benefits = benefit_excerpts(session)
        label, unknown = {
            'English': ('Listed benefits include', 'I do not have confirmed benefits details.'),
            'German': ('Zu den aufgeführten Vorteilen gehören', 'Bestätigte Angaben zu Zusatzleistungen liegen mir nicht vor.'),
            'Spanish': ('Los beneficios indicados incluyen', 'No tengo detalles confirmados sobre los beneficios.')
        }[language]
        if benefits:
            text += ' ' + label + ': ' + ' '.join(
                f'«{line}» [{doc.metadata["id"]}].' for line, doc in benefits)
            for _, doc in benefits:
                if doc not in cited:
                    cited.append(doc)
        else:
            text += ' ' + unknown
    return text, focused_documents(cited, reply=text)


def work_arrangement_question(query):
    return bool(WORK_ARRANGEMENT.search(normalize(query)))


def retrieve_job_context(session, query, found):
    """Prioritise at most two actual source chunks; never create policy facts."""
    if not work_arrangement_question(query):
        return found
    anchors = [doc for doc in session.get('source_chunks', {}).values()
               if WORK_ARRANGEMENT.search(normalize(doc.page_content))]
    selected = {doc.metadata['id']: doc for doc in anchors[:2] + found}
    return list(selected.values())[:6]
