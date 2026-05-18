import unittest
from unittest.mock import patch

from app import app


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch('app.worker_request')
    def test_create_task_validation(self, _mock_worker_request):
        response = self.client.post('/api/tasks/spellcheck', json={'text': '', 'language': 'auto'})
        self.assertEqual(response.status_code, 400)

    @patch('app.worker_request')
    def test_create_task_proxy(self, mock_worker_request):
        mock_worker_request.return_value = (202, {'task_id': '123', 'status': 'queued'})
        response = self.client.post('/api/tasks/spellcheck', json={'text': 'hello', 'language': 'en'})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()['task_id'], '123')


if __name__ == '__main__':
    unittest.main()
