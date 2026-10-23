import unittest
import json
from app import app
from modules.auth import authenticate_user, load_users

class FinLabComprehensiveTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_user_login_and_dashboard_sidebar(self):
        """Test regular user login and verify modern vertical sidebar layout"""
        res = self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        dash_res = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.data.decode('utf-8')

        # Check Canva Redesign Mobile & Widget components
        self.assertIn('app-wrapper', html)
        self.assertIn('top-bar', html)
        self.assertIn('page-content', html)
        self.assertIn('chat-window', html)

    def test_02_admin_required_guard(self):
        """Test regular user cannot access admin portal routes"""
        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        res = self.client.get('/admin')
        self.assertIn(res.status_code, [302, 403])

    def test_03_admin_portal_routes(self):
        """Test admin login and access to all 5 admin pages"""
        res = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        for route in ['/admin', '/admin/users', '/admin/categories', '/admin/audit-logs', '/admin/settings']:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200, f'Route {route} failed with {r.status_code}')

    def test_04_budget_ratio_api(self):
        """Test API to update budget ratio (50/30/20)"""
        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        res = self.client.post('/api/user/budget-ratio', json={'needs': 55, 'wants': 25, 'savings': 20})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

    def test_05_consent_management_api(self):
        """Test Open Banking consent revocation and reactivation"""
        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        res = self.client.post('/api/consent/revoke', json={'bank_id': 'VCB'})
        self.assertEqual(res.status_code, 200)

        res2 = self.client.post('/api/consent/reauthorize', json={'bank_id': 'VCB'})
        self.assertEqual(res2.status_code, 200)

if __name__ == '__main__':
    unittest.main()
