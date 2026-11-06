"""Opt-in feedback snapshots. Never persist session IDs, source or dialogue text."""
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import logging
import os
from pathlib import Path
import secrets
import sqlite3

from fastapi import HTTPException

FIELDS=('rating','reason','kind','scenario','language','style','mode','model',
        'frontend_build','backend_build','response_version','turns','goals',
        'practised_goals','confirmed_goals','unresolved_goals','withheld_replies',
        'measured_turns','turn_latency_ms')
NUMERIC=set(FIELDS[11:])


def enabled():
    return os.getenv('FEEDBACK_ENABLED','true').lower()=='true'


def retention_days():
    return max(1,min(365,int(os.getenv('FEEDBACK_RETENTION_DAYS','90'))))


def database_path():
    return Path(os.getenv('FEEDBACK_DB_PATH','.runtime/feedback.sqlite3'))


def today():
    return datetime.now(timezone.utc).date()


def connect():
    path=database_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=5)
    try:
        db.row_factory=sqlite3.Row
        columns=','.join(f'{field} {"INTEGER" if field in NUMERIC else "TEXT"} NOT NULL' for field in FIELDS)
        db.execute(f'CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, created_day TEXT NOT NULL, updated_day TEXT NOT NULL, {columns})')
        db.execute('CREATE INDEX IF NOT EXISTS feedback_created ON feedback(created_day)')
        db.commit()
        return db
    except BaseException:
        db.close()
        raise


def purge(db):
    cutoff=(today()-timedelta(days=retention_days()-1)).isoformat()
    db.execute('DELETE FROM feedback WHERE created_day < ?', (cutoff,))


def cleanup():
    if not database_path().exists():return
    try:
        with closing(connect()) as db,db:
            purge(db)
    except (OSError,sqlite3.Error) as error:
        logging.getLogger(__name__).warning('Feedback retention cleanup failed (%s).',type(error).__name__)


@lru_cache(maxsize=1)
def backend_build():
    # Works for an uncommitted local checkout too, without claiming a Git SHA.
    digest=hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        if path.name.startswith('test_'):continue
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return 'sha256:'+digest.hexdigest()[:16]


def snapshot(session,response,kind,rating,reason,frontend_build,live):
    setup=session['setup']
    turns=session['turns']
    goals=session['mission']
    timings=session.get('turn_timings',[])
    return dict(rating=rating,reason=reason or '',kind=kind,
        scenario=setup['scenario'],language=setup['language'],style=setup['level'],
        mode='live' if live else 'demo',model=os.getenv('OPENAI_MODEL','gpt-4.1-mini') if live else 'none',
        frontend_build=frontend_build,backend_build=backend_build(),response_version=response['version'],
        turns=sum(turn['role']=='user' for turn in turns),goals=len(goals),
        practised_goals=sum(goal['achieved'] for goal in goals),
        confirmed_goals=sum(goal['answer_status']=='confirmed' for goal in goals),
        unresolved_goals=sum(goal['answer_status'] in ('unknown','unverified') for goal in goals),
        withheld_replies=sum(bool(turn.get('answer_withheld')) for turn in turns),
        measured_turns=len(timings),turn_latency_ms=sum(timings))


def save(identifier,record):
    if not enabled():raise HTTPException(503,'Shared feedback is disabled. Your rating has not been shared.')
    identifier=identifier or secrets.token_hex(24)
    if set(record)!=set(FIELDS):raise ValueError('Feedback snapshot has unexpected fields.')
    day=today().isoformat()
    values=[identifier,day,day]+[record[key] for key in FIELDS]
    updates=','.join(f'{key}=excluded.{key}' for key in ('updated_day',)+FIELDS)
    try:
        with closing(connect()) as db,db:
            purge(db)
            db.execute(f'INSERT INTO feedback (id,created_day,updated_day,{",".join(FIELDS)}) VALUES ({",".join("?" for _ in values)}) ON CONFLICT(id) DO UPDATE SET {updates}',values)
    except (OSError,sqlite3.Error):
        raise HTTPException(503,'Feedback could not be saved. Please retry; sharing was not confirmed.') from None
    return identifier


def remove(identifier):
    if not identifier:return
    try:
        with closing(connect()) as db,db:
            purge(db)
            db.execute('DELETE FROM feedback WHERE id=?',(identifier,))
    except (OSError,sqlite3.Error):
        raise HTTPException(503,'Shared feedback could not be removed. Please retry before leaving this review.') from None


def summary(rows):
    total=len(rows)
    useful=sum(row['rating']=='up' for row in rows)
    measured=sum(row['measured_turns'] for row in rows)
    return {'ratings':total,'useful':useful,'unhelpful':total-useful,
            'useful_percent':round(100*useful/total,1) if total else None,
            'mean_turn_latency_ms':round(sum(row['turn_latency_ms'] for row in rows)/measured) if measured else None,
            'measured_turns':measured,
            'withheld_replies':sum(row['withheld_replies'] for row in rows),
            'unresolved_goals':sum(row['unresolved_goals'] for row in rows)}


def report(days=30):
    if not 1<=days<=365:raise ValueError('Choose between 1 and 365 days.')
    rows=[]
    if database_path().exists():
        with closing(connect()) as db,db:
            purge(db)
            rows=[dict(row) for row in db.execute('SELECT '+','.join(FIELDS)+' FROM feedback WHERE created_day>=?',((today()-timedelta(days=days-1)).isoformat(),))]
    # Performance summaries use dialogue ratings only, so rating an individual
    # response as well cannot double-count the same conversation's timings.
    dialogue=[row for row in rows if row['kind']=='dialogue']
    result={'days':days,'retention_days':retention_days(),'all_ratings':summary(rows),
            'dialogue_ratings':summary(dialogue),'response_ratings':summary([row for row in rows if row['kind']=='response']),
            'negative_reasons':dict(Counter(row['reason'] or 'not_specified' for row in dialogue if row['rating']=='down')),
            'breakdowns':{}}
    for field in ('scenario','language','style','mode','model','frontend_build','backend_build','response_version'):
        result['breakdowns'][field]={value:summary([row for row in dialogue if row[field]==value]) for value in sorted({row[field] for row in dialogue})}
    return result
