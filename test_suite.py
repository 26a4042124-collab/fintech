import unittest
import json
from app import app
from modules.auth import authenticate_user, load_users, save_users
from modules.health_scoring import suggest_ratio_by_income

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
        """Test API to update budget ratio (50/30/20) and restore baseline"""
        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        res = self.client.post('/api/user/budget-ratio', json={'needs': 55, 'wants': 25, 'savings': 20})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        # Khôi phục tỷ lệ chuẩn 50/30/20 cho kịch bản demo
        res_restore = self.client.post('/api/user/budget-ratio', json={'needs': 50, 'wants': 30, 'savings': 20})
        self.assertEqual(res_restore.status_code, 200)

    def test_05_consent_management_api(self):
        """Test Open Banking consent revocation and reactivation"""
        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)
        res = self.client.post('/api/consent/revoke', json={'bank_id': 'VCB'})
        self.assertEqual(res.status_code, 200)

        res2 = self.client.post('/api/consent/reauthorize', json={'bank_id': 'VCB'})
        self.assertEqual(res2.status_code, 200)

    def test_06_income_based_budget_suggestions_and_ui(self):
        """Verify dynamic income-based budget allocation replaces hardcoded 50/30/20 across APIs & UI"""
        self.assertEqual(
            (suggest_ratio_by_income(9000000)['needs'], suggest_ratio_by_income(9000000)['wants'], suggest_ratio_by_income(9000000)['savings']),
            (65, 20, 15)
        )
        self.assertEqual(
            (suggest_ratio_by_income(18000000)['needs'], suggest_ratio_by_income(18000000)['wants'], suggest_ratio_by_income(18000000)['savings']),
            (55, 25, 20)
        )
        self.assertEqual(
            (suggest_ratio_by_income(35000000)['needs'], suggest_ratio_by_income(35000000)['wants'], suggest_ratio_by_income(35000000)['savings']),
            (40, 25, 35)
        )

        self.client.post('/login', data={'username': 'nguyen_van_a', 'password': 'password123'}, follow_redirects=True)

        sug_res = self.client.get('/api/user/budget-suggestion?income=9000000')
        self.assertEqual(sug_res.status_code, 200)
        sug_data = sug_res.get_json()
        self.assertEqual(sug_data['suggestion']['needs'], 65)
        self.assertEqual(sug_data['suggestion']['savings'], 15)

        try:
            res = self.client.post('/api/user/budget-ratio', json={
                'monthly_income': 10000000,
                'needs': 65,
                'wants': 20,
                'savings': 15
            })
            self.assertEqual(res.status_code, 200)
            payload = res.get_json()
            self.assertTrue(payload['success'])
            self.assertEqual(payload['monthly_income'], 10000000)
            self.assertEqual(payload['target_amounts'], {'needs': 6500000, 'wants': 2000000, 'savings': 1500000})

            analytics_html = self.client.get('/analytics').data.decode('utf-8')
            self.assertIn('65/20/15', analytics_html)
            self.assertIn('mục tiêu 65%', analytics_html)
            self.assertIn('mục tiêu 20%', analytics_html)
            self.assertIn('mục tiêu 15%', analytics_html)
            self.assertIn('6,500,000đ', analytics_html)
            self.assertNotIn('chuẩn 50%', analytics_html)
            self.assertNotIn('chuẩn 30%', analytics_html)
            self.assertNotIn('chuẩn 20%', analytics_html)

            budgets_html = self.client.get('/budgets').data.decode('utf-8')
            self.assertIn('(65/20/15)', budgets_html)
            self.assertIn('10,000,000đ', budgets_html)

            dash_html = self.client.get('/dashboard').data.decode('utf-8')
            self.assertIn('modal-budget-ratio', dash_html)
            self.assertIn('Tự chia ngân sách', dash_html)
            self.assertIn('1,500,000đ', dash_html)

            goals_html = self.client.get('/goals').data.decode('utf-8')
            self.assertIn('Tự động chuyển <strong>1,500,000đ/tháng</strong>', goals_html)
            self.assertIn('mục tiêu <strong>15%</strong>', goals_html)
            self.assertNotIn('chuẩn 20%', goals_html)

            ai_res = self.client.post('/api/ai/categorize', json={'description': 'Highlands Coffee 45k', 'type': 'OUTFLOW'})
            self.assertEqual(ai_res.status_code, 200)
            self.assertIn('20%', ai_res.get_json().get('bucket_label', ''))

            chat_res = self.client.post('/api/chat', json={'message': 'Tỷ lệ chia ngân sách theo thu nhập của tôi thế nào?'})
            self.assertEqual(chat_res.status_code, 200)
            reply = chat_res.get_json().get('reply', '')
            self.assertIn('65% / 20% / 15%', reply)
            self.assertIn('6,500,000đ', reply)
        finally:
            self.client.post('/api/user/budget-ratio', json={
                'monthly_income': 18000000,
                'needs': 50,
                'wants': 30,
                'savings': 20
            })

    def test_07_register_goals_custom_income_and_ratio(self):
        """Verify onboarding step persists user monthly_income and custom split"""
        test_phone = '0987654399'
        test_email = 'custom_budget_test@example.com'
        original_users = load_users()
        try:
            with self.client.session_transaction() as sess:
                sess['reg_otp_verified'] = True
                sess['reg_phone'] = test_phone
                sess['reg_full_name'] = 'Nguyen Thi Test'
                sess['reg_email'] = test_email
                sess['reg_password'] = 'TestPass123'

            res = self.client.post('/register/goals', data={
                'goals': ['saving'],
                'monthly_income': '9500000',
                'ratio_needs': '60',
                'ratio_wants': '25',
                'ratio_savings': '15'
            }, follow_redirects=False)
            self.assertEqual(res.status_code, 302)

            created = next((u for u in load_users() if u.get('phone') == test_phone), None)
            self.assertIsNotNone(created)
            self.assertEqual(created['monthly_income'], 9500000)
            self.assertEqual(created['budget_ratio'], {'needs': 60, 'wants': 25, 'savings': 15})
        finally:
            save_users(original_users)

if __name__ == '__main__':
    unittest.main()
