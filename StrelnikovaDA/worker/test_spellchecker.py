import sys
import time
import unittest

sys.path.insert(0, '/app')

from app import app, init_db  # noqa: E402
from logic.spellchecker import SpellCheckService  # noqa: E402


class SpellCheckerUnitTests(unittest.TestCase):
    def test_direct_spellcheck(self):
        service = SpellCheckService()
        result = service.check_text('Превет мир', 'auto')
        self.assertIn('Привет', result['corrected_text'])
        self.assertGreaterEqual(result['mistakes_count'], 1)


class WorkerApiTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()

    def test_create_and_complete_task(self):
        response = self.client.post('/tasks/spellcheck', json={'text': 'This sentense has erors', 'language': 'auto'})
        self.assertEqual(response.status_code, 202)
        task_id = response.get_json()['task_id']

        for _ in range(10):
            status_response = self.client.get(f'/tasks/{task_id}')
            payload = status_response.get_json()
            if payload['status'] == 'done':
                self.assertIn('sentence', payload['result']['corrected_text'].lower())
                return
            time.sleep(1)

        self.fail('Task was not completed in time')


if __name__ == '__main__':
    unittest.main()
