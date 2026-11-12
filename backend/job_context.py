"""Keep explicit work-arrangement evidence in short interview questions."""
import re
from backend.embeddings import normalize

WORK_ARRANGEMENT = re.compile(
 r'\b(?:remote(?:ly)?|hybrid\w*|homeoffice|home office|telework\w*|'
 r'teletrabaj\w*|remot[oa]s?|hibrid[oa]s?|presencial\w*|'
 r'work(?:ing)? from home|trabajar (?:desde|en) casa|von (?:zu )?hause|'
 r'im buro|in (?:the )?office)\b')


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
