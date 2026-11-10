"""Disposable, offline PDF OCR. Native libraries are initialized before sandboxing.

No application imports, provider credentials, network, child processes or file
uploads to third parties. PDF input is read only after OS confinement.
"""
import ctypes as c
import ctypes.util
import json
import os
import sys

os.environ['OMP_THREAD_LIMIT']='1'
os.environ['OMP_NUM_THREADS']='1'

MAX_OCR_PAGES=8
MAX_PIXELS=8_000_000


class Tesseract:
 def __init__(self):
  library=ctypes.util.find_library('tesseract')
  if not library:raise RuntimeError('OCR is unavailable on this host. Paste document text instead.')
  self.lib=c.CDLL(library)
  specs={
   'TessBaseAPICreate':([],c.c_void_p),
   'TessBaseAPIInit3':([c.c_void_p,c.c_char_p,c.c_char_p],c.c_int),
   'TessBaseAPISetPageSegMode':([c.c_void_p,c.c_int],None),
   'TessBaseAPISetVariable':([c.c_void_p,c.c_char_p,c.c_char_p],c.c_int),
   'TessBaseAPISetImage':([c.c_void_p,c.POINTER(c.c_ubyte),c.c_int,c.c_int,c.c_int,c.c_int],None),
   'TessBaseAPIGetUTF8Text':([c.c_void_p],c.c_void_p),
   'TessDeleteText':([c.c_void_p],None),
   'TessBaseAPIClear':([c.c_void_p],None),
   'TessBaseAPIDelete':([c.c_void_p],None)}
  for name,(args,result) in specs.items():
   function=getattr(self.lib,name);function.argtypes=args;function.restype=result
  self.handle=self.lib.TessBaseAPICreate()
  if not self.handle or self.lib.TessBaseAPIInit3(self.handle,None,b'eng+deu+spa'):
   self.close();raise RuntimeError('OCR is unavailable on this host. Paste document text instead.')
  self.lib.TessBaseAPISetPageSegMode(self.handle,3)
  self.lib.TessBaseAPISetVariable(self.handle,b'user_defined_dpi',b'180')

 def read(self,image):
  image=image.convert('RGB');raw=image.tobytes()
  buffer=(c.c_ubyte*len(raw)).from_buffer_copy(raw)
  self.lib.TessBaseAPISetImage(self.handle,buffer,image.width,image.height,3,image.width*3)
  pointer=self.lib.TessBaseAPIGetUTF8Text(self.handle)
  try:return c.string_at(pointer).decode('utf-8',errors='replace').strip() if pointer else ''
  finally:
   if pointer:self.lib.TessDeleteText(pointer)
   self.lib.TessBaseAPIClear(self.handle)

 def close(self):
  if getattr(self,'handle',None):self.lib.TessBaseAPIDelete(self.handle);self.handle=None


def recognize_pdf(raw,indexes,engine):
 import pypdfium2 as pdfium
 documents=[];total=0
 if len(indexes)>MAX_OCR_PAGES:raise ValueError('OCR supports up to 8 image-based pages. Upload a shorter PDF or paste the text.')
 with pdfium.PdfDocument(raw) as pdf:
  if len(pdf)>100:raise ValueError('Use a PDF with at most 100 pages.')
  for index in indexes:
   if not 0<=index<len(pdf):raise ValueError('Invalid OCR page selection.')
   page=pdf[index]
   try:
    width,height=page.get_size();scale=2.5
    if width<=0 or height<=0 or width*height*scale*scale>MAX_PIXELS:
     raise ValueError('A PDF page is too large for OCR. Use a standard page size or paste the text.')
    bitmap=page.render(scale=scale)
    try:
     image=bitmap.to_pil()
     text=engine.read(image)
    finally:bitmap.close()
   finally:page.close()
   total+=len(text)
   if total>100000:raise ValueError('Document text exceeds 100,000 characters.')
   documents.append({'page':index,'text':text})
 return documents


def main():
 engine=None
 try:
  # Load all native/image libraries before reading the untrusted document.
  import pypdfium2
  from PIL import Image
  from backend.parser_sandbox import confine
  if sys.platform=='linux':
   import resource
   resource.setrlimit(resource.RLIMIT_CPU,(30,30))
   resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
  engine=Tesseract()
  if os.getenv('PARSER_SANDBOX')=='required':confine()
  indexes=[int(value) for value in sys.argv[1].split(',') if value]
  raw=sys.stdin.buffer.read(4*1024*1024+1)
  if len(raw)>4*1024*1024:raise ValueError('Maximum upload size is 4 MB.')
  print(json.dumps({'documents':recognize_pdf(raw,indexes,engine)}))
 except (ValueError,RuntimeError) as error:
  print(json.dumps({'error':str(error)}))
 except Exception:
  print(json.dumps({'error':'Could not recognise text in this PDF. Try a clearer copy or paste the listing text.'}))
 finally:
  if engine:engine.close()


if __name__=='__main__':main()
