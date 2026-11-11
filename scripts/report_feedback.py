"""Owner-only aggregate CLI feedback report. No raw-row export."""
import argparse
from html import escape
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from backend import feedback

LIMITS=('Opt-in ratings describe participating rated takes, not all visitors or unique people. '
        'They are product feedback, not verified factual accuracy, training labels or evidence of causal improvement. '
        'Performance summaries use whole-dialogue ratings only; repeated takes may come from the same visitor. '
        'Mean latency covers successful server chat turns only, excluding speech, network time and failed requests. '
        'Small groups are noisy; compare matching mode/model/scenario and offline evaluations before drawing conclusions.')
REASONS={'realism':"Did not feel realistic",'unanswered':"Did not answer the question",'fact':"Reported factual error",'tone':"Tone felt off",'speed':"Too slow",'other':"Other",'not_specified':"No category"}
QUALITY={'relevance':'Responded to the learner','memory':'Remembered earlier answers',
         'continuity':'Conversation flowed naturally','role_consistency':'Stayed in character',
         'grounding':'Source details seemed accurate','language_agreement':'Language sounded natural'}


def render_html(data):
    def table(headers,rows):
        head=''.join('<th>'+escape(str(value))+'</th>' for value in headers)
        body=''.join('<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in row)+'</tr>' for row in rows)
        return '<div class="table-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>' if rows else '<p>No shared ratings yet.</p>'
    overview=data['dialogue_ratings']
    percent=overview['useful_percent']
    latency=overview['mean_turn_latency_ms']
    sections=[table(['Whole-dialogue ratings','Useful','Unhelpful','Useful %','Mean chat turn'],[[overview['ratings'],overview['useful'],overview['unhelpful'],str(percent)+'%' if percent is not None else '—',str(latency)+' ms' if latency is not None else 'Not measured']])]
    sections.append('<h2>Why a rehearsal was unhelpful</h2>'+table(['Category','Ratings'],[(REASONS.get(key,key),value) for key,value in sorted(data['negative_reasons'].items(),key=lambda item:-item[1])]))
    sections.append('<h2>Optional conversation quality ratings</h2><p>Participant impressions, not verified accuracy or expert benchmark labels. Not sure and unrated answers are shown separately.</p>'+table(
        ['Question','Yes','No','Not sure','Unrated'],
        [[QUALITY[key],values['pass'],values['fail'],values['uncertain'],values['unrated']]
         for key,values in data['quality_ratings'].items()]))
    for dimension,groups in data['breakdowns'].items():
        sections.append('<h2>By '+escape(dimension.replace('_',' '))+'</h2>'+table(['Group','Ratings','Useful','Unhelpful','Useful %','Mean chat turn'],[
            [key,value['ratings'],value['useful'],value['unhelpful'],str(value['useful_percent'])+'%',str(value['mean_turn_latency_ms'])+' ms' if value['mean_turn_latency_ms'] is not None else 'Not measured'] for key,value in groups.items()]))
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>The Rehearsal — feedback report</title><style>body{font:16px/1.6 system-ui;margin:40px auto;padding:0 20px;max-width:1050px;background:#171916;color:#e9e6dc}h1,h2{color:#e3b66f}p{max-width:900px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;margin:18px 0 30px}td,th{padding:12px;text-align:left;border-bottom:1px solid #424637}th{background:#252820}small{color:#b0b2a7}</style><main><h1>The Rehearsal: shared feedback</h1><p>Last '+str(data['days'])+' days. Retention: up to '+str(data['retention_days'])+' days. Total ratings: '+str(data['all_ratings']['ratings'])+'; individual-response ratings: '+str(data['response_ratings']['ratings'])+'.</p><p>'+escape(LIMITS)+'</p>'+''.join(sections)+'<h2>How to use this report</h2><p>Prioritize the most common negative categories. Reproduce the issue using fictional fixtures; a “fact” rating is a report to investigate, not a confirmed hallucination. Add a regression case, make the change and compare the next version under similar conditions. Shared feedback contains no conversation text, so it cannot reconstruct the original interaction.</p><small>Owner-generated aggregate report. Regenerate it to see new ratings. No personal feedback text or raw records are included.</small></main></html>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days',type=int,default=30)
    parser.add_argument('--html',type=Path,help='Write a standalone HTML report.')
    parser.add_argument('--json',type=Path,help='Write aggregate JSON; never raw records.')
    args=parser.parse_args()
    if not 1<=args.days<=365:parser.error('--days must be between 1 and 365')
    data=feedback.report(args.days)
    for destination,content in ((args.html,render_html(data)),(args.json,json.dumps(data,indent=2)+'\n')):
        if destination:
            if destination.resolve()==feedback.database_path().resolve():parser.error('Report output must not overwrite the feedback database.')
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(content,encoding='utf-8')
            print('Report:',destination.resolve())
    print(json.dumps(data['dialogue_ratings'],indent=2))
    print(LIMITS)


if __name__=='__main__':main()
