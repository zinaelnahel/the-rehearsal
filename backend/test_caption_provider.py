import json
import os
import time
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
import httpx
from fastapi import HTTPException
from backend import caption_provider, video


class CaptionProviderTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch.dict(os.environ,{'SUPADATA_API_KEY':'fictional-test-key'}))

 def invoke(self,data,status=200,inspect=None):
  def handler(request):
   if inspect:inspect(request)
   return httpx.Response(status,json=data)
  client=httpx.Client(transport=httpx.MockTransport(handler))
  with patch.object(caption_provider.httpx,'Client',return_value=client):
   return caption_provider.fetch_native('abcdefghijk','en',time.monotonic()+20)

 def test_native_only_request_and_timestamp_conversion(self):
  def inspect(request):
   self.assertEqual(str(request.url).split('?')[0],'https://api.supadata.ai/v1/transcript')
   self.assertEqual(request.url.params['mode'],'native')
   self.assertEqual(request.url.params['text'],'false')
   self.assertEqual(request.url.params['chunkSize'],'50')
   self.assertEqual(request.headers['x-api-key'],'fictional-test-key')
  result=self.invoke({'lang':'en','content':[{'text':'Fictional caption.','offset':1250,'duration':2000,'lang':'en'}]},inspect=inspect)
  self.assertEqual(result[0].start,1.25);self.assertEqual(result[0].duration,2)

 def test_nearby_provider_captions_keep_individual_timestamps(self):
  result=self.invoke({'lang':'en','content':[
   {'text':'Opening sentence.','offset':200,'duration':2400},
   {'text':'The price is 1420 euros.','offset':3500,'duration':2700},
   {'text':'Closing sentence.','offset':7200,'duration':3000}]})
  segments=video.caption_segments(result)
  self.assertEqual([(s['start'],s['end']) for s in segments],[(0.2,2.6),(3.5,6.2),(7.2,10.2)])
  self.assertEqual(segments[1]['text'],'The price is 1420 euros.')

 def test_provider_errors_and_unavailable_captions_are_sanitized(self):
  for status,expected in ((401,503),(403,503),(429,429),(206,422),(404,422),(202,424),(500,424),(302,424)):
   with self.subTest(status=status),self.assertRaises(HTTPException) as error:
    self.invoke({'secret':'fictional-test-key'},status)
   self.assertEqual(error.exception.status_code,expected)
   self.assertNotIn('fictional-test-key',error.exception.detail)

 def test_mismatched_language_and_invalid_times_are_not_accepted(self):
  for payload in ({'lang':'de','content':[]},{'lang':'en','content':'No real timestamps'},
     {'lang':'en','content':[{'text':'Caption','offset':-1,'duration':10}]},
     {'lang':'en','content':[{'text':'Caption','offset':0,'duration':10,'lang':'es'}]}):
   with self.assertRaises(HTTPException):self.invoke(payload)

 def test_fallback_only_after_direct_failure_and_only_when_configured(self):
  fetched=SimpleNamespace(text='Caption text.',start=0,duration=2)
  reserve=Mock()
  with patch('youtube_transcript_api.YouTubeTranscriptApi.fetch',side_effect=HTTPException(424,'Blocked')),patch.object(caption_provider,'fetch_native',return_value=[fetched]) as provider:
   result=video.import_video('https://youtu.be/abcdefghijk','English',reserve)
   self.assertEqual(result['source_method'],'youtube_captions_supadata')
   self.assertIsNone(result['is_generated'])
   self.assertTrue(result['requires_confirmation'])
   provider.assert_called_once();reserve.assert_not_called()
  with patch.dict(os.environ,{'SUPADATA_API_KEY':''}),patch('youtube_transcript_api.YouTubeTranscriptApi.fetch',side_effect=HTTPException(424,'Blocked')),patch.object(caption_provider,'fetch_native') as provider:
   with self.assertRaises(HTTPException):video.import_video('https://youtu.be/abcdefghijk','English',reserve)
   provider.assert_not_called()
  direct=[fetched]
  class Direct(list):
   is_generated=False
   language_code="en"
  with patch('youtube_transcript_api.YouTubeTranscriptApi.fetch',return_value=Direct(direct)),patch.object(caption_provider,'fetch_native') as provider:
   self.assertEqual(video.import_video('https://youtu.be/abcdefghijk','English',reserve)['source_method'],'youtube_captions')
   provider.assert_not_called()
