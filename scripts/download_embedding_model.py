"""Explicit download of pinned ONNX/tokenizer data; no remote Python or pickle."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import httpx

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'evaluation/embedding-model.json'


def verify_file(path, entry):
    if not path.is_file() or path.stat().st_size != entry['size']:
        return False
    with path.open('rb') as source:
        return hashlib.file_digest(source,'sha256').hexdigest()==entry['sha256']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.runtime/embedding-model')
    args=parser.parse_args()
    config=json.loads(MANIFEST.read_text())
    args.directory.mkdir(parents=True,exist_ok=True)
    with httpx.Client(follow_redirects=True,timeout=httpx.Timeout(60,connect=20)) as client:
        for entry in config['files']:
            destination=args.directory/entry['path']
            if verify_file(destination,entry):
                print('Verified cached file:',entry['path'],flush=True)
                continue
            destination.parent.mkdir(parents=True,exist_ok=True)
            temporary=destination.with_suffix(destination.suffix+'.partial')
            url=f"https://huggingface.co/{config['model']}/resolve/{config['revision']}/{entry['path']}"
            print('Downloading:',entry['path'],entry['size'],'bytes',flush=True)
            try:
                size=0
                with client.stream('GET',url) as response,temporary.open('wb') as target:
                    response.raise_for_status()
                    for block in response.iter_bytes(1024*1024):
                        size+=len(block)
                        if size>entry['size']:raise ValueError('Model file exceeded its pinned size')
                        target.write(block)
                if not verify_file(temporary,entry):raise ValueError('Model file checksum differs from the pinned manifest')
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
    print('Pinned model data verified. No inference provider was called.')


if __name__=='__main__':main()
