"""Local browser-test backend: real FFmpeg, synthetic transcription, no provider calls."""
import os
from types import SimpleNamespace


def main():
    os.environ.update(REHEARSAL_MODE='demo',VECTOR_STORE='memory',SPEECH_ENABLED='true',
        API_PROXY_TOKEN='',OPENAI_API_KEY='synthetic-no-network',REHEARSAL_AGENT_ENABLED='false',
        LANGSMITH_TRACING='false',LANGCHAIN_TRACING_V2='false')
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from backend import main as api,speech
    api.reserve_call=lambda *args,**kwargs: None

    def transcribe(**kwargs):
        assert kwargs['file'][0]=='audio.wav'
        assert kwargs['file'][1][:4]==b'RIFF'
        return SimpleNamespace(segments=[SimpleNamespace(start=0,end=1,
            text='The monthly rent is 850 euros.',no_speech_prob=0,avg_logprob=0,compression_ratio=1)])

    speech.speech_client=lambda: SimpleNamespace(audio=SimpleNamespace(
        transcriptions=SimpleNamespace(create=transcribe)))
    import uvicorn
    uvicorn.run(api.app,host='127.0.0.1',port=8031,access_log=False)


if __name__=='__main__':main()
