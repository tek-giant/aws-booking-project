import os
import tempfile
import unittest
from unittest.mock import patch

TEMP = tempfile.TemporaryDirectory()
os.environ['LOCAL_DEMO'] = '1'
os.environ['SQLITE_PATH'] = os.path.join(TEMP.name, 'test.sqlite3')
from app import app

class BookingTests(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def post(self, description='Sample booking', amount='45.25'):
        return self.client.post('/', json={'description':description,'amount':amount}, headers={'X-Booking-Form':'1'})

    def test_save_persist_and_escape(self):
        self.assertEqual(self.post('<script>alert(1)</script>').status_code,201)
        page=self.client.get('/')
        self.assertIn(b'45.25',page.data)
        self.assertIn(b'&lt;script&gt;',page.data)
        self.assertNotIn(b'<script>alert(1)</script>',page.data)
        self.assertIn(b'45.25',app.test_client().get('/').data)

    def test_bad_amounts_and_descriptions(self):
        for amount in ['-1','0','NaN','Infinity','1.001','1000000.01']:
            self.assertEqual(self.post(amount=amount).status_code,400)
        self.assertEqual(self.post(description=' ').status_code,400)

    def test_cross_site_and_non_json_rejected(self):
        self.assertEqual(self.client.post('/',data={'description':'x','amount':'1'}).status_code,403)
        self.assertEqual(self.client.post('/',json={'description':'x','amount':'1'},headers={'X-Booking-Form':'1','Sec-Fetch-Site':'cross-site'}).status_code,403)

    def test_database_failure_does_not_break_liveness(self):
        with patch('app.database',side_effect=RuntimeError('secret should not appear')):
            self.assertEqual(self.client.get('/health').status_code,200)
            response=self.client.get('/')
            self.assertEqual(response.status_code,503)
            self.assertNotIn(b'secret should not appear',response.data)
            self.assertEqual(self.post().status_code,503)

if __name__ == '__main__':
    unittest.main()
