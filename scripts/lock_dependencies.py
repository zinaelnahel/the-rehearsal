"""Generate the hashed runtime lock, or verify its input fingerprint in CI."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'backend/requirements.txt'
OUTPUT=ROOT/'backend/requirements.lock'
PREFIX='# requirements.txt SHA256: '


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    fingerprint=PREFIX+hashlib.sha256(INPUT.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    if args.check:
        if fingerprint not in OUTPUT.read_text(encoding='utf-8').splitlines():
            raise SystemExit('Requirements changed. Run python scripts/lock_dependencies.py and review the new lockfile.')
        print('Dependency lock input fingerprint matches.')
        return
    subprocess.run(['uv','pip','compile','backend/requirements.txt','--python-version','3.12',
        '--universal','--generate-hashes','--output-file','backend/requirements.lock',
        '--no-emit-index-url','--quiet'],cwd=ROOT,check=True)
    OUTPUT.write_text(fingerprint+'\n'+OUTPUT.read_text(encoding='utf-8'),encoding='utf-8')


if __name__=='__main__':main()
