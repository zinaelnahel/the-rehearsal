"""Provider-reported usage must survive validation failures without saving text."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from backend.model_metrics import ModelMetrics
from backend.main import LocalEmbeddings, model, agent_model


class ModelMetricsTests(unittest.TestCase):
    def test_usage_is_counted_once_and_no_response_content_is_retained(self):
        session = {}
        response = SimpleNamespace(llm_output={'token_usage':{
            'prompt_tokens':12,'completion_tokens':7},'private':'SECRET'},generations=[])
        with patch('backend.model_metrics.time.monotonic',side_effect=[1.0,1.025]):
            with ModelMetrics(session) as metrics:
                metrics.on_llm_end(response)
        self.assertEqual(session['model_usage'],dict(requests=1,failures=0,
            elapsed_ms=25,input_tokens=12,output_tokens=7,usage_reports=1,missing_usage_reports=0))
        self.assertNotIn('SECRET',str(session))

    def test_failed_parse_keeps_usage_and_missing_usage_is_not_a_zero_report(self):
        session = {}
        with self.assertRaises(ValueError):
            with ModelMetrics(session) as metrics:
                metrics.on_llm_end(SimpleNamespace(llm_output=None,generations=[[
                    SimpleNamespace(message=SimpleNamespace(usage_metadata={
                        'input_tokens':3,'output_tokens':2}))]]))
                raise ValueError('invalid output')
        with ModelMetrics(session):
            pass
        stats=session['model_usage']
        self.assertEqual(stats['failures'],1)
        self.assertEqual(stats['requests'],2)
        self.assertEqual(stats['usage_reports'],1)
        self.assertEqual(stats['missing_usage_reports'],1)
        self.assertEqual(stats['input_tokens'],3)

    def test_lexical_embeddings_handle_empty_and_punctuation_queries(self):
        for text in ['', '  ', '?!']:
            vector=LocalEmbeddings().embed_query(text)
            self.assertEqual(len(vector),512)
            self.assertGreater(sum(value*value for value in vector),0)

    def test_real_adapter_records_usage_for_structured_and_tool_requests(self):
        from langchain_openai import ChatOpenAI
        class Output(BaseModel):
            text: str
        requests=[]
        def reply(request):
            requests.append(request)
            return httpx.Response(200,json={'id':'synthetic','object':'chat.completion',
                'created':0,'model':'gpt-4.1-mini','choices':[{'index':0,
                    'message':{'role':'assistant','content':'{"text":"Hello"}'},
                    'finish_reason':'stop'}],
                'usage':{'prompt_tokens':12,'completion_tokens':7,'total_tokens':19}})
        with httpx.Client(transport=httpx.MockTransport(reply)) as client:
            def adapter(**kwargs):
                return ChatOpenAI(api_key='synthetic-no-network',http_client=client,**kwargs)
            session={}
            with patch('backend.main.reserve_call'),patch('langchain_openai.ChatOpenAI',side_effect=adapter):
                self.assertEqual(model(Output,'Instructions',{'text':'Data'},session).text,'Hello')
                agent_model([('user','Hello')],[],session)
        self.assertEqual(len(requests),2)
        self.assertEqual(session['model_usage']['usage_reports'],2)
        self.assertEqual(session['model_usage']['input_tokens'],24)
        self.assertEqual(session['model_usage']['output_tokens'],14)

    def test_real_adapter_counts_usage_even_for_invalid_structured_output(self):
        from langchain_openai import ChatOpenAI
        class Output(BaseModel):
            text: str
        def reply(request):
            return httpx.Response(200,json={'id':'synthetic','object':'chat.completion',
                'created':0,'model':'gpt-4.1-mini','choices':[{'index':0,
                    'message':{'role':'assistant','content':'{"wrong":"field"}'},
                    'finish_reason':'stop'}],
                'usage':{'prompt_tokens':5,'completion_tokens':3,'total_tokens':8}})
        with httpx.Client(transport=httpx.MockTransport(reply)) as client:
            session={}
            with patch('backend.main.reserve_call'),patch('langchain_openai.ChatOpenAI',
                side_effect=lambda **kw: ChatOpenAI(api_key='synthetic-no-network',http_client=client,**kw)):
                with self.assertRaises(HTTPException):
                    model(Output,'Instructions',{},session)
        self.assertEqual(session['model_usage']['failures'],1)
        self.assertEqual(session['model_usage']['usage_reports'],1)
        self.assertEqual(session['model_usage']['input_tokens'],5)
