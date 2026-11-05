"""Create small, fictional document fixtures for the browser import checks."""
import io
from pathlib import Path
import zipfile
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def main():
    folder=Path('.runtime/fixtures')
    folder.mkdir(parents=True,exist_ok=True)
    writer=PdfWriter()
    page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content=DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 50 700 Td (Fictional listing. Monthly rent is 1375 euros.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    with (folder/'synthetic.pdf').open('wb') as output:writer.write(output)
    with zipfile.ZipFile(folder/'synthetic.docx','w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fictional listing. Monthly rent is 1375 euros.</w:t></w:r></w:p></w:body></w:document>')
    print('Fictional browser fixtures:',folder)


if __name__=='__main__':main()
