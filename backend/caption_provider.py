"""Optional native-caption service; fixed endpoint, bounded response, no AI mode."""
import json
import os
import re
import time
from types import SimpleNamespace
import httpx
from backend import budget
from fastapi import HTTPException
from pydantic import BaseModel, Field


class CaptionChunk(BaseModel):
    text: str = Field(max_length=4000)
    offset: float = Field(ge=0,allow_inf_nan=False)
    duration: float = Field(ge=0,allow_inf_nan=False)
    lang: str | None = None


def enabled():
    return bool(os.getenv('SUPADATA_API_KEY','').strip())


def fetch_native(identifier, language_code, deadline):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',identifier):
        raise ValueError('Invalid YouTube identifier')
    key=os.getenv('SUPADATA_API_KEY','').strip()
    if not key:raise HTTPException(503,'The optional caption service is not configured.')
    remaining=deadline-time.monotonic()
    if remaining<=0:raise HTTPException(504,'Caption import timed out. Paste the transcript instead.')
    budget.reserve()
    try:
        with httpx.Client(timeout=min(remaining,20),trust_env=False,follow_redirects=False) as client:
            with client.stream('GET','https://api.supadata.ai/v1/transcript',
                headers={'x-api-key':key,'Accept':'application/json'},params={
                    'url':'https://www.youtube.com/watch?v='+identifier,
                    'lang':language_code,'mode':'native','text':'false','chunkSize':50}) as response:
                if response.status_code in (401,403):
                    raise HTTPException(503,'The caption service rejected its server credentials. Paste the transcript instead.')
                if response.status_code==429:
                    raise HTTPException(429,'The caption service quota or rate limit was reached. Paste the transcript or retry later.')
                if response.status_code in (206,404):
                    raise HTTPException(422,'No existing captions were available from the caption service. Paste the transcript instead.')
                if response.status_code!=200:
                    raise HTTPException(424,'The caption service could not return existing captions. Paste the transcript instead.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic()>=deadline:
                        raise HTTPException(504,'Caption import timed out. Paste the transcript instead.')
                    raw.extend(chunk)
                    if len(raw)>2*1024*1024:
                        raise HTTPException(413,'The caption response is too large. Paste a selected excerpt instead.')
        data=json.loads(raw)
        if data.get('lang')!=language_code:
            raise HTTPException(422,'Existing captions were returned in a different language. Change the conversation language or paste the transcript.')
        content=data.get('content')
        if not isinstance(content,list) or not content or len(content)>5000:
            raise ValueError('Missing timestamped content')
        chunks=[CaptionChunk.model_validate(item) for item in content]
        if any(c.lang is not None and c.lang!=language_code for c in chunks):
            raise ValueError('Mixed caption languages')
        return [SimpleNamespace(text=c.text,start=c.offset/1000,duration=c.duration/1000) for c in chunks]
    except HTTPException:raise
    except httpx.TimeoutException:
        raise HTTPException(504,'The caption service timed out. Paste the transcript or retry later.') from None
    except Exception:
        # Never echo upstream bodies, request headers or credential-bearing errors.
        raise HTTPException(424,'The caption service returned unusable captions. Paste the transcript instead.') from None
