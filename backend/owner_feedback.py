"""Owner-only aggregate reports; never expose sessions, source text or raw rows."""
import os
import secrets
from fastapi import APIRouter,Header,HTTPException,Query
from backend import feedback

router=APIRouter()

@router.get('/api/owner/feedback')
def owner_report(days:int=Query(default=30,ge=1,le=365),owner_token:str=Header(default='',alias='x-feedback-owner-token')):
 expected=os.getenv('FEEDBACK_OWNER_TOKEN','')
 if len(expected)<32:raise HTTPException(503,'Owner feedback access has not been configured.')
 if not secrets.compare_digest(owner_token,expected):raise HTTPException(401,'Owner authentication required.')
 return {**feedback.report(days),'storage':'temporary','storage_notice':'This free Render service uses temporary storage. Download reports before a redeploy or service replacement.'}
