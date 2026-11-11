"""Bind reviewed timestamps to an actual transcription without retaining audio."""
import hashlib
import hmac
import json
import secrets
import time

_KEY = secrets.token_bytes(32)

def digest(segments):
    return hashlib.sha256(json.dumps(segments, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def issue(segments):
    payload = str(int(time.time()) + 7200) + ':' + digest(segments)
    return payload + ':' + hmac.new(_KEY, payload.encode(), hashlib.sha256).hexdigest()

def unchanged(receipt, segments):
    try:
        expiry, fingerprint, signature = receipt.split(':')
        payload = expiry + ':' + fingerprint
        expected = hmac.new(_KEY, payload.encode(), hashlib.sha256).hexdigest()
        return (hmac.compare_digest(signature, expected) and int(expiry) >= time.time()
                and hmac.compare_digest(fingerprint, digest(segments)))
    except (ValueError, TypeError, AttributeError):
        return False
