"""Atomic, persistent daily provider reservations; failed calls are never refunded.

The configured reservation is an operator ceiling per request, not a price quote.
Provider account billing limits remain the final financial control.
"""
from datetime import datetime, timezone
from contextlib import closing
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import sqlite3
from fastapi import HTTPException


def reserve():
    if os.getenv('PROVIDER_DAILY_BUDGET_ENABLED','true').lower() == 'false':
        return
    try:
        limit = Decimal(os.getenv('PROVIDER_DAILY_BUDGET_USD', '10'))
        charge = Decimal(os.getenv('PROVIDER_CALL_RESERVATION_USD', '0.10'))
        if not limit.is_finite() or not charge.is_finite() or limit < 0 or charge <= 0:
            raise ValueError()
        ceiling, cost = int(limit * 1_000_000), int(charge * 1_000_000)
        if cost < 1:
            raise ValueError()
        path = Path(os.getenv('PROVIDER_BUDGET_PATH', '.runtime/provider-budget.sqlite3'))
        path.parent.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).date().isoformat()
        with closing(sqlite3.connect(path, timeout=5)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS budget (day TEXT PRIMARY KEY, reserved INTEGER NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO budget VALUES (?, 0)', (day,))
            used = db.execute('SELECT reserved FROM budget WHERE day=?', (day,)).fetchone()[0]
            if used + cost > ceiling:
                raise HTTPException(429, 'The daily provider allowance has been reached. Try tomorrow or use offline demo mode.')
            db.execute('UPDATE budget SET reserved=reserved+? WHERE day=?', (cost, day))
            db.execute('DELETE FROM budget WHERE day < ?', (day,))
    except HTTPException:
        raise
    except (OSError, sqlite3.Error, ValueError, InvalidOperation):
        raise HTTPException(503, 'Provider budget protection is unavailable. External processing is paused.') from None


def check_input(payload):
    if len(payload.encode('utf-8')) > int(os.getenv('MODEL_MAX_INPUT_BYTES', '160000')):
        raise HTTPException(413, 'This scene is too large for the AI allowance. Shorten the source or start a new scene.')
