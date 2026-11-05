"""Single-instance admission control; no IP addresses or user content retained."""
import os
import time
from collections import deque

requests = deque()
active = 0
clients = {}

def admit(client=None):
    global active
    now = time.monotonic()
    while requests and requests[0] <= now - 60:
        requests.popleft()
    if active >= int(os.getenv('API_MAX_CONCURRENT', '12')) or len(requests) >= int(os.getenv('API_REQUESTS_PER_MINUTE', '300')):
        return False
    expired = [key for key, times in clients.items() if not times or times[-1] <= now-60]
    for key in expired:
        del clients[key]
    if client:
        if client not in clients and len(clients) >= 10000:
            return False
        times = clients.setdefault(client, deque())
        while times and times[0] <= now-60:
            times.popleft()
        if len(times) >= int(os.getenv('API_CLIENT_REQUESTS_PER_MINUTE', '30')):
            return False
        times.append(now)
    requests.append(now)
    active += 1
    return True

def release():
    global active
    active -= 1
