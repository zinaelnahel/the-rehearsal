"""Bounded public-page reading; no logins, proxy evasion or arbitrary URL fetches."""
import ipaddress
import re
import socket
from urllib.parse import urlsplit,urlunsplit,urljoin
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

HOSTS={'idealista.com':'inmueble','idealista.pt':'imovel','idealista.it':'immobile'}
AGENT='TheRehearsal'
FALLBACK='Paste the listing text below, or upload a text PDF of the advert. No listing facts have been imported.'

def listing_url(value):
 try:
  parsed=urlsplit(value.strip())
  host=(parsed.hostname or '').lower().removeprefix('www.')
  if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443) or host not in HOSTS:
   raise ValueError()
  if not re.fullmatch(r'/(?:[a-z]{2}/)?'+HOSTS[host]+r'/\d{5,12}/?',parsed.path): raise ValueError()
  return urlunsplit(('https','www.'+host,parsed.path.rstrip('/')+'/', '', ''))
 except (ValueError,TypeError):
  raise HTTPException(400,'Use a direct HTTPS Idealista listing link from Spain, Portugal or Italy, not a search or login page.') from None

def public_dns(url):
 try:
  addresses=socket.getaddrinfo(urlsplit(url).hostname,443,type=socket.SOCK_STREAM)
  if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses): raise ValueError()
 except (OSError,ValueError):
  raise HTTPException(400,'The listing address could not be resolved to a public website. '+FALLBACK) from None

def read_response(response,limit):
 data=bytearray()
 for chunk in response.iter_bytes():
  data.extend(chunk)
  if len(data)>limit: raise HTTPException(413,'The listing page is too large to import. '+FALLBACK)
 return bytes(data).decode('utf-8',errors='replace')

def parse_listing(html):
 soup=BeautifulSoup(html,'html.parser')
 title=(soup.title.get_text(' ',strip=True) if soup.title else 'Idealista listing')[:160]
 for node in soup(['script','style','noscript','nav','footer','header','form','button','iframe']): node.decompose()
 root=soup.find('main') or soup.find('article') or soup.body
 if root is None: raise HTTPException(422,'No readable listing description was found. '+FALLBACK)
 text='\n'.join(dict.fromkeys(line.strip() for line in root.get_text('\n',strip=True).splitlines() if line.strip()))
 if len(text)<60 or re.search(r'captcha|access denied|verify you are human|enable javascript|datadome',text[:1500],re.I):
  raise HTTPException(422,'The provider returned a verification page rather than the advert. '+FALLBACK)
 if len(text)>100000: raise HTTPException(413,'The readable listing text is too long. '+FALLBACK)
 return title,text

def fetch_listing(value):
 url=listing_url(value)
 public_dns(url)
 try:
  with httpx.Client(timeout=12,follow_redirects=False,headers={'User-Agent':'TheRehearsal/0.5 (user-requested listing preview)'},trust_env=False) as client:
   rules=None
   robots_url='https://'+urlsplit(url).netloc+'/robots.txt'
   with client.stream('GET',robots_url) as response:
    if response.status_code==200:
     rules=RobotFileParser()
     rules.parse(read_response(response,256000).splitlines())
     if not rules.can_fetch(AGENT,url): raise HTTPException(424,'This provider does not allow this automated page read. '+FALLBACK)
    elif response.status_code!=404:
     raise HTTPException(424,'The provider could not permit an automated page read. '+FALLBACK)
   for attempt in range(3):
    with client.stream('GET',url) as response:
     if response.status_code in (301,302,303,307,308):
      if attempt==2: raise HTTPException(424,'The listing redirected too many times. '+FALLBACK)
      destination=listing_url(urljoin(url,response.headers.get('location','')))
      if urlsplit(destination).hostname!=urlsplit(url).hostname:
       raise HTTPException(424,'The listing redirected to a different website. '+FALLBACK)
      public_dns(destination)
      if rules is not None and not rules.can_fetch(AGENT,destination):
       raise HTTPException(424,'The provider does not allow reading the redirected listing. '+FALLBACK)
      url=destination
      continue
     if response.status_code in (401,403,429): raise HTTPException(424,'The provider blocked this automated read. '+FALLBACK)
     if response.status_code!=200: raise HTTPException(424,'The listing is unavailable or has been removed. '+FALLBACK)
     if 'text/html' not in response.headers.get('content-type',''): raise HTTPException(422,'The listing URL did not return a readable web page. '+FALLBACK)
     title,text=parse_listing(read_response(response,2*1024*1024))
     return url,title,text
 except httpx.RequestError:
  raise HTTPException(504,'The listing website did not respond in time. '+FALLBACK) from None
 raise HTTPException(424,'The listing could not be imported. '+FALLBACK)
