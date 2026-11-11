"""Refresh the public sample previews used while the API connects."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    catalog=json.loads((ROOT/'samples/catalog.json').read_text(encoding='utf-8'))
    samples={}
    for scenario in ('apartment','interview','course','difficult'):
        samples[scenario]={}
        for language,code in (('English','en'),('German','de'),('Spanish','es')):
            if scenario=='difficult':
                audio=json.loads((ROOT/'samples/audio/family-boundary.es.json').read_text(encoding='utf-8'))
                samples[scenario][language]=audio['title']+'\nFictional Spanish voice message; one AI-generated voice.\n'+'\n'.join(turn['speaker']+': '+turn['text'] for turn in audio['turns'])
                continue
            if scenario==catalog['video']['scenario']:
                item=catalog['video']
                samples[scenario][language]=f"{item['title']}\n{item['publisher']} \u00b7 {item['source_language']}\n{item['note']}\n"
                continue
            if scenario in catalog:
                item=catalog[scenario]
                samples[scenario][language]=f"{item['title']}\n{item['publisher']} \u00b7 {item['pages']} page(s) \u00b7 {item['source_language']}\n{item['note']}\n"
                continue
            suffix='' if (code=='es' and scenario!='difficult') or (code=='en' and scenario=='difficult') else '.'+code
            samples[scenario][language]=(ROOT/'samples'/f'{scenario}{suffix}.txt').read_text(encoding='utf-8')
    (ROOT/'app/sample-previews.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
