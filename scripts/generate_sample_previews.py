"""Refresh the public fictional sample text used while the API connects."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    samples={}
    for scenario in ('apartment','interview','course','difficult'):
        samples[scenario]={}
        for language,code in (('English','en'),('German','de'),('Spanish','es')):
            suffix='' if (code=='es' and scenario!='difficult') or (code=='en' and scenario=='difficult') else '.'+code
            samples[scenario][language]=(ROOT/'samples'/f'{scenario}{suffix}.txt').read_text(encoding='utf-8')
    (ROOT/'app/sample-previews.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
