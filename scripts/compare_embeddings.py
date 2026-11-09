"""Paired local retrieval comparison; no model generation, provider calls or downloads."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.document_parser import MemoryLoader
from backend.embeddings import LocalEmbeddings

DATASETS=['evaluation/rag-dataset.json','evaluation/quality-release-dataset.json','evaluation/retrieval-challenge.json']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases():
    corpora={};cases=[];counts={}
    splitter=RecursiveCharacterTextSplitter(chunk_size=700,chunk_overlap=100)
    for name in DATASETS:
        data=json.loads((ROOT/name).read_text(encoding='utf-8'))
        suite=Path(name).stem
        if isinstance(data,dict):
            for corpus in data['corpora']:
                identifier=suite+':'+corpus['id']
                docs=[Document(page_content=p['text'],metadata={'evidence_id':p['id']}) for p in corpus['passages']]
                corpora[identifier]=splitter.split_documents(docs)
            for row in data['queries']:
                cases.append({**row,'suite':suite,'corpus':suite+':'+row['corpus_id']})
            counts[suite]={'raw':len(data['queries']),'unique':len(data['queries'])}
        else:
            seen=set();unique=0
            for row in data:
                signature=(row['document'],row['question'],row['evidence'])
                if signature in seen:continue
                seen.add(signature);unique+=1
                identifier=hashlib.sha256(row['document'].encode()).hexdigest()
                if identifier not in corpora:
                    docs=list(MemoryLoader(row['document'].encode(),'text','fictional').lazy_load())
                    corpora[identifier]=splitter.split_documents(docs)
                relevant=[str(i) for i,d in enumerate(corpora[identifier]) if row['evidence'] in d.page_content]
                if not relevant:raise ValueError('No labeled evidence in chunks: '+row['id'])
                cases.append({'id':row['id'],'suite':suite,'language':row['language'],
                    'source_language':row.get('source_language','unspecified'),'category':row.get('category','baseline'),
                    'question':row['question'],'corpus':identifier,'relevant_ids':relevant})
            counts[suite]={'raw':len(data),'unique':unique}
    for identifier,docs in corpora.items():
        for i,doc in enumerate(docs):doc.metadata['chunk_id']=str(i)
    for case in cases:
        if case['suite']=='retrieval-challenge':
            case['relevant_ids']=[d.metadata['chunk_id'] for d in corpora[case['corpus']]
                if d.metadata['evidence_id'] in case['relevant_ids']]
        if not case['relevant_ids']:raise ValueError('Missing reference label: '+case['id'])
    return corpora,cases,counts


def rank_vectors(documents,query,relevant):
    matrix=np.asarray(documents,dtype=np.float32);query=np.asarray(query,dtype=np.float32)
    scores=(matrix@query)/(np.maximum(np.linalg.norm(matrix,axis=1),1e-12)*max(float(np.linalg.norm(query)),1e-12))
    if not np.isfinite(scores).all():raise ValueError('Nonfinite embedding scores')
    order=np.argsort(-scores,kind='stable')
    rank=next(i+1 for i,index in enumerate(order) if str(index) in relevant)
    return rank,[str(index) for index in order[:4]],int(np.isclose(scores,scores.max()).sum()),bool(scores.max()<=0)


def summarize(rows):
    if not rows:return {'queries':0}
    return {'queries':len(rows),'top_1':sum(r['rank']==1 for r in rows)/len(rows),
        'recall_at_4':sum(r['rank']<=4 for r in rows)/len(rows),
        'mrr':sum(1/r['rank'] for r in rows)/len(rows),
        'median_query_ms':statistics.median(r['query_ms'] for r in rows),
        'p95_query_ms':float(np.percentile([r['query_ms'] for r in rows],95)),
        'tied_top_scores':sum(r['top_score_ties']>1 for r in rows),
        'no_positive_similarity':sum(r['no_positive_similarity'] for r in rows),
        'corpora_larger_than_top_k':sum(r['chunks']>4 for r in rows)}


def peak_rss_bytes():
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
                (name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.K32GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        result=Counters();result.cb=ctypes.sizeof(result)
        if not kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(result),result.cb):
            raise OSError('Cannot measure process memory')
        return result.PeakWorkingSetSize
    import resource
    maximum=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum if sys.platform=='darwin' else maximum*1024)


def worker(candidate,directory,repeats):
    corpora,cases,counts=load_cases()
    start=time.perf_counter()
    if candidate=='lexical':encoder=LocalEmbeddings()
    else:
        from backend.semantic_embeddings import LocalSemanticEmbeddings
        encoder=LocalSemanticEmbeddings(directory)
    load_ms=(time.perf_counter()-start)*1000
    encoder.embed_query('A fictional rental listing.')  # Identical warmup, excluded from query timings.
    indexes={};index_ms=0
    for identifier,docs in corpora.items():
        start=time.perf_counter();indexes[identifier]=encoder.embed_documents([d.page_content for d in docs])
        index_ms+=(time.perf_counter()-start)*1000
    rows=[]
    for case in cases:
        times=[]
        for _ in range(repeats):
            start=time.perf_counter()
            rank,top,ties,no_signal=rank_vectors(indexes[case['corpus']],encoder.embed_query(case['question']),case['relevant_ids'])
            times.append((time.perf_counter()-start)*1000)
        rows.append({**case,'rank':rank,'top_4':top,'chunks':len(corpora[case['corpus']]),
            'top_score_ties':ties,'no_positive_similarity':no_signal,'query_ms':statistics.median(times)})
    groups={suite:summarize([r for r in rows if r['suite']==suite]) for suite in counts}
    challenge=[r for r in rows if r['suite']=='retrieval-challenge']
    for lang in ('English','German','Spanish'):
        groups['challenge_query_'+lang]=summarize([r for r in challenge if r['language']==lang])
    groups['challenge_cross_language']=summarize([r for r in challenge if r['language']!=r['source_language']])
    groups['challenge_same_language']=summarize([r for r in challenge if r['language']==r['source_language']])
    return {'candidate':candidate,'load_ms':load_ms,'index_ms':index_ms,
        'peak_process_rss_bytes':peak_rss_bytes(),'dataset_counts':counts,
        'truncated_encodings':getattr(encoder,'truncated_texts',0),
        'summary':summarize(rows),'groups':groups,'cases':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-directory',type=Path,default=ROOT/'.runtime/embedding-model')
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/embedding-comparison.json')
    parser.add_argument('--worker',choices=['lexical','semantic'])
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.worker:
        args.output.write_text(json.dumps(worker(args.worker,args.model_directory,args.repeats),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        return
    results={}
    for candidate in ('lexical','semantic'):
        target=args.output.with_name(args.output.stem+'-'+candidate+'.json')
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',candidate,
            '--model-directory',str(args.model_directory),'--repeats',str(args.repeats),'--output',str(target)],cwd=ROOT,check=True)
        results[candidate]=json.loads(target.read_text(encoding='utf-8'))
    left=results['lexical']['cases'];right=results['semantic']['cases']
    assert [(r['suite'],r['id']) for r in left]==[(r['suite'],r['id']) for r in right]
    changes=Counter('semantic_better' if b['rank']<a['rank'] else 'lexical_better' if a['rank']<b['rank'] else 'same_rank' for a,b in zip(left,right))
    report={'run_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
        'python':platform.python_version(),
        'dependencies':{name:version(name) for name in ['numpy','onnxruntime','tokenizers','langchain-core','langchain-text-splitters']},
        'model':json.loads((ROOT/'evaluation/embedding-model.json').read_text()),
        'dataset_sha256':{name:sha(ROOT/name) for name in DATASETS},
        'source_sha256':{name:sha(ROOT/name) for name in ['backend/embeddings.py','backend/semantic_embeddings.py',
            'backend/document_parser.py','backend/requirements.lock','scripts/compare_embeddings.py','scripts/download_embedding_model.py']},
        'method':{'same_corpora_queries_labels':True,'chunk_size':700,'chunk_overlap':100,'top_k':4,
            'tie_break':'source order, reported tied top scores','timing':'median of repeated warm query embeddings plus cosine ranking; no query cache',
            'memory':'separate candidate processes; peak process RSS, not deployment incremental memory',
            'provider_calls':0,'semantic_inference_batch_size':1,'repeats':args.repeats},
        'rank_changes':dict(changes),'candidates':results,
        'limitations':['Author-authored synthetic labels; no independent human review.',
            'Deduplicated language-style copies, but translated/paraphrased cases remain correlated.',
            'Retrieval ranking only; does not establish answer quality or goal-scoring quality.',
            'Warm CPU timings on this machine are not hosted latency estimates.',
            'Quantized ONNX candidate with 128-token truncation; not a comparison of all semantic models.',
            'Existing short corpora can make recall@4 trivial; corpus sizes and challenge results are reported.']}
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for name,result in results.items():print(name,json.dumps(result['summary']), 'peak MiB',round(result['peak_process_rss_bytes']/1024**2,1))
    print('Paired rank changes:',dict(changes));print('Report:',args.output)


if __name__=='__main__':main()
