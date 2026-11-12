"""Opt-in provider-backed retest against the public deployment; deletes its sessions."""
import argparse
import json
import time
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.source_grounding import unsupported_rental_claim


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    base = 'https://the-rehearsal-lab.vercel.app'
    report = {'scope': 'Targeted hosted provider checks, not an independent benchmark', 'cases': [], 'passed': False}
    with httpx.Client(base_url=base, headers={'Origin': base}, timeout=90) as client:
        def call(method, path, body=None):
            response = client.request(method, path, json=body)
            response.raise_for_status()
            return response.json()

        try:
            config = call('GET', '/api/config')
            report['builds'] = {key: config.get(key) for key in ('frontend_build_sha', 'backend_build_sha')}
            assert all(value == args.expected_sha for value in report['builds'].values()), report['builds']
            for scenario in ('apartment', 'interview'):
                if scenario == 'apartment':
                    captions = json.loads((ROOT/'samples/apartment-transcript.es.json').read_text(encoding='utf-8'))
                    body = {'sample_video_text': ' '.join(part['text'] for part in captions['segments']), 'transcript_confirmed': True}
                    questions = ['When is the flat available to move into?', 'Can you let me know when you find out?']
                    goals = ['Ask when the flat is available']
                else:
                    body = {'sample': 'interview', 'language': 'English'}
                    questions = ['Can I work remotely, and what are the salary and benefits?',
                                 'I worked in QA for five years with Playwright and Cypress and used AI for test case generation.',
                                 'yes I did that']
                    goals = ['Ask about remote work', 'Ask about salary and benefits', 'Describe relevant experience']
                source = call('POST', '/api/sessions', body)
                path = '/api/sessions/' + source['id']
                row = {'scenario': scenario, 'turns': []}
                report['cases'].append(row)
                try:
                    started = time.monotonic()
                    call('POST', path+'/mission', {'scenario': scenario, 'language': 'English', 'feedback_language': 'English', 'level': 'Everyday', 'external_model_consent': True})
                    row['mission_seconds'] = round(time.monotonic()-started, 2)
                    call('POST', path+'/start', {'goals': goals})
                    for question in questions:
                        result = call('POST', path+'/turn', {'text': question})
                        turn = result['turn']
                        row['turns'].append({'question': question, **turn})
                        if scenario == 'apartment':
                            assert not unsupported_rental_claim(turn['content'], [], []), turn['content']
                            assert all(goal['answer_status'] != 'confirmed' for goal in result['goals'])
                        elif question == questions[0]:
                            assert 'pension scheme' in turn['content'].lower(), turn['content']
                            assert 'staff discounts' in turn['content'].lower(), turn['content']
                            assert 'remote' in turn['content'].lower(), turn['content']
                            assert 'confirmed salary' in turn['content'].lower(), turn['content']
                            assert turn['sources']
                        elif question == questions[-1]:
                            assert not turn['answer_withheld'], turn['content']
                    review = call('POST', path+'/finish', {})
                    row['review'] = review
                finally:
                    row['deleted'] = call('DELETE', path).get('deleted') is True
                    row['deletion_verified'] = client.get(path+'/status').status_code == 404
                    assert row['deleted'] and row['deletion_verified']
                print(scenario + ': PASS', flush=True)
            report['passed'] = True
        finally:
            output = ROOT/'.runtime/submission-retest-hosted.json'
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
