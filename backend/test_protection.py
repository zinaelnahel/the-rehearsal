import os
import subprocess
import unittest
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from backend import abuse, budget
from backend.parser_process import parse_document


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        abuse.requests.clear()
        abuse.active = 0
        abuse.clients.clear()

    def test_rate_expiry_and_concurrent_release(self):
        with patch.dict(os.environ, {'API_REQUESTS_PER_MINUTE': '2', 'API_MAX_CONCURRENT': '1'}):
            with patch('backend.abuse.time.monotonic', return_value=0):
                self.assertTrue(abuse.admit())
                self.assertFalse(abuse.admit())
                abuse.release()
                self.assertTrue(abuse.admit())
                abuse.release()
                self.assertFalse(abuse.admit())
            with patch('backend.abuse.time.monotonic', return_value=61):
                self.assertTrue(abuse.admit())
                abuse.release()

    def test_parser_timeout_and_secret_filtering(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'API_PROXY_TOKEN': 'secret'}):
            with patch('backend.parser_process.subprocess.run', side_effect=subprocess.TimeoutExpired('parser', 12)) as run:
                with self.assertRaisesRegex(ValueError, 'timed out'):
                    parse_document(b'%PDF-', 'pdf', 'private.pdf')
                self.assertNotIn('OPENAI_API_KEY', run.call_args.kwargs['env'])
                self.assertNotIn('API_PROXY_TOKEN', run.call_args.kwargs['env'])

    def test_malformed_document_in_real_worker(self):
        with self.assertRaisesRegex(ValueError, 'Could not read'):
            parse_document(b'%PDF-invalid', 'pdf', 'broken.pdf')

    def test_client_throttle_does_not_block_another_client(self):
        with patch.dict(os.environ, {'API_CLIENT_REQUESTS_PER_MINUTE': '1'}):
            self.assertTrue(abuse.admit('client-a'))
            abuse.release()
            self.assertFalse(abuse.admit('client-a'))
            self.assertTrue(abuse.admit('client-b'))
            abuse.release()

    def test_budget_is_atomic_and_survives_new_connections(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            'PROVIDER_BUDGET_PATH': str(Path(folder)/'budget.sqlite3'),
            'PROVIDER_DAILY_BUDGET_USD':'0.30','PROVIDER_CALL_RESERVATION_USD':'0.10'}):
            def attempt(_):
                try:
                    budget.reserve()
                    return True
                except HTTPException as exc:
                    self.assertEqual(exc.status_code, 429)
                    return False
            with ThreadPoolExecutor(max_workers=6) as pool:
                self.assertEqual(sum(pool.map(attempt, range(8))), 3)
            self.assertFalse(attempt(None))

    def test_budget_storage_failure_and_input_limit_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'PROVIDER_BUDGET_PATH': folder}):
            with self.assertRaises(HTTPException) as caught:
                budget.reserve()
            self.assertEqual(caught.exception.status_code, 503)
        with patch.dict(os.environ, {'MODEL_MAX_INPUT_BYTES': '3'}):
            with self.assertRaises(HTTPException):
                budget.check_input('éé')

    def test_required_sandbox_refuses_unsupported_host(self):
        import sys
        if sys.platform == 'linux':
            self.skipTest('Unsupported-host check is for non-Linux development')
        with patch.dict(os.environ, {'PARSER_SANDBOX': 'required'}):
            with self.assertRaises(HTTPException) as caught:
                parse_document(b'%PDF-', 'pdf', 'file.pdf')
            self.assertEqual(caught.exception.status_code,503)
            self.assertIn('Secure document parsing is unavailable',caught.exception.detail)
