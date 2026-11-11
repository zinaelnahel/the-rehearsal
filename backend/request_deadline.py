"""One shared wall-clock allowance across sequential provider calls."""
import time
from contextvars import ContextVar
from fastapi import HTTPException

deadline=ContextVar('rehearsal_request_deadline',default=None)
TURN_SECONDS=40

def provider_timeout(normal):
 end=deadline.get()
 if end is None:return normal
 remaining=end-time.monotonic()
 if remaining<=0:
  raise HTTPException(504,'This reply took too long. No new message was saved. Retry this message or review the conversation.')
 return min(normal,remaining)
