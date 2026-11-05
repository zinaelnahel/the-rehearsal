"""Run inside the production Linux image; nonzero means deployment must stop."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import io
import zipfile
from backend.parser_sandbox import confine


def main():
    # The sentinel is created before confinement, like application session data.
    with tempfile.TemporaryDirectory() as folder:
        sentinel = Path(folder)/'private.txt'
        sentinel.write_text('synthetic secret')
        read_attempt = str(sentinel)
        # Cleanup cannot run in this process after filesystem writes are denied.
        code = '''
import json, socket, subprocess, sys
from backend.parser_sandbox import confine
confine()
checks={}
for name,operation in (
 ('private_file',lambda:open(sys.argv[1]).read()),
 ('filesystem_write',lambda:open(sys.argv[1]+'-new','w')),
 ('network_socket',lambda:socket.socket()),
 ('subprocess',lambda:subprocess.run([sys.executable,'-c','pass']))):
 try:
  operation()
  checks[name]=False
 except PermissionError:
  checks[name]=True
print(json.dumps(checks))
raise SystemExit(0 if all(checks.values()) else 1)
'''
        result = subprocess.run([sys.executable, '-c', code, read_attempt],
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            print('Parser sandbox verification failed; do not enable document uploads.')
            raise SystemExit(1)
        print(result.stdout.strip())
    # Verify normal document imports under the exact production worker policy,
    # not just denial of malicious operations in a lightweight process.
    from backend.parser_process import parse_document
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer=PdfWriter()
    page=writer.add_blank_page(width=300,height=300)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content=DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 20 200 Td (Fictional rent is 1375 euros.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    pdf=io.BytesIO();writer.write(pdf)
    docx=io.BytesIO()
    with zipfile.ZipFile(docx,'w') as archive:
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fictional rent is 1375 euros.</w:t></w:r></w:p></w:body></w:document>')
    os.environ['PARSER_SANDBOX']='required'
    for raw,kind in [(pdf.getvalue(),'pdf'),(docx.getvalue(),'docx')]:
        docs=parse_document(raw,kind,'fictional.'+kind)
        if not docs or '1375' not in docs[0].page_content:
            raise SystemExit('Sandboxed '+kind+' import failed')
    print('Production sandbox: real PDF and DOCX imports passed.')


if __name__ == '__main__':
    main()
