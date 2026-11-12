"""Attach exact supporting excerpts without changing stored source chunks."""
import re


def focused_documents(docs, quotes=(), reply=''):
    literal_quotes = re.findall(r'«([^»]+)»', reply)
    focused = []
    for doc in docs:
        candidates = [item['quote'] for item in quotes if item['source_id'] == doc.metadata['id']]
        candidates += literal_quotes
        excerpts = list(dict.fromkeys(quote for quote in candidates
                                     if quote.strip() and quote in doc.page_content))
        focused.append(doc.model_copy(update={'metadata': {**doc.metadata, 'highlights': excerpts}})
                       if excerpts else doc)
    return focused
