import json
import unittest
from modules.ai_categorizer import categorize_transaction, process_all_transactions
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response
from app import app

class TestFinLabFixes(unittest.TestCase):

    def test_01_icloud_categorization(self):
        # iCloud should be Subscription, WANTS, NOT night spending even at 03:10
        res = categorize_transaction("APPLE.COM/BILL GIA HAN GOI DUNG LUONG ICLOUD 2TB & APP", "2026-10-15 03:10:00", txn_type="OUTFLOW")
        self.assertEqual(res["bucket"], "WANTS")
        self.assertEqual(res["category"], "Dịch vụ số định kỳ (Subscription)")
        self.assertTrue(res["is_subscription"])
        self.assertFalse(res["is_night_spending"], "Subscription at 3am must NOT be tagged as night impulse spending")

    def test_02_netflix_spotify_subscription(self):
        # Netflix at 3am
        res_nf = categorize_transaction("NETFLIX.COM GIA HAN GOI PREMIUM DINH KY HANG THANG", "2026-10-15 03:00:00", txn_type="OUTFLOW")
        self.assertTrue(res_nf["is_subscription"])
        self.assertFalse(res_nf["is_night_spending"])

        # Spotify at 3:05am
        res_sp = categorize_transaction("SPOTIFY VIETNAM GIA HAN GOI INDIVIDUAL HANG THANG", "2026-10-15 03:05:00", txn_type="OUTFLOW")
        self.assertTrue(res_sp["is_subscription"])
        self.assertFalse(res_sp["is_night_spending"])

    def test_03_genuine_night_impulse(self):
        # Shopee order at 23:45
        res_sp = categorize_transaction("SHOPEEPAY CHOT DON AO KHOAC THOI TRANG SHOPEE LIVE", "2026-10-06 23:45:00", txn_type="OUTFLOW")
        self.assertFalse(res_sp["is_subscription"])
        self.assertTrue(res_sp["is_night_spending"])

    def test_04_user_custom_categories(self):
        # Food with accent
        res_food = categorize_transaction("Ăn uống: Bún bò huế", "2026-10-23 12:00:00", txn_type="OUTFLOW")
        self.assertIn("Ăn uống", res_food["category"])
        self.assertEqual(res_food["bucket"], "WANTS")

        # Transport with accent
        res_trans = categorize_transaction("Đi lại: Grab bike", "2026-10-23 12:00:00", txn_type="OUTFLOW")
        self.assertIn("Đi lại", res_trans["category"])
        self.assertEqual(res_trans["bucket"], "NEEDS")

        # Housing bills with accent
        res_house = categorize_transaction("Hóa đơn sinh hoạt: Tiền điện nước", "2026-10-23 12:00:00", txn_type="OUTFLOW")
        self.assertIn("Nhà ở", res_house["category"])
        self.assertEqual(res_house["bucket"], "NEEDS")

    def test_05_health_scoring_and_subscription_leak(self):
        with open("data/mock_transactions.json", "r", encoding="utf-8") as f:
            txns = json.load(f)
        enriched = process_all_transactions(txns)
        health = compute_financial_health(enriched)

        # Keys
        self.assertIn("items", health["subscription_leaks"])
        self.assertIn("list", health["subscription_leaks"])
        self.assertIn("items", health["impulse_night_spending"])
        self.assertIn("list", health["impulse_night_spending"])

        # Count of subscriptions: Netflix, Spotify, iCloud = 3
        self.assertEqual(health["subscription_leaks"]["count"], 3)
        self.assertEqual(len(health["subscription_leaks"]["items"]), 3)
        sub_merchants = [s["merchant"] for s in health["subscription_leaks"]["items"]]
        self.assertTrue(any("ICLOUD" in m for m in sub_merchants))
        self.assertTrue(any("NETFLIX" in m for m in sub_merchants))
        self.assertTrue(any("SPOTIFY" in m for m in sub_merchants))

        # Check total amount
        self.assertEqual(health["subscription_leaks"]["total_amount"], 260000 + 59000 + 290000)

    def test_06_chatbot_responses(self):
        with open("data/mock_transactions.json", "r", encoding="utf-8") as f:
            txns = json.load(f)
        enriched = process_all_transactions(txns)
        health = compute_financial_health(enriched)

        # 1. Total expense chip
        r1 = generate_chatbot_response("Tháng này tôi tiêu bao nhiêu?", health)
        self.assertTrue("Tổng đã chi" in r1 or "Tổng chi tiêu" in r1)
        self.assertIn("Thiết yếu (Needs)", r1)
        self.assertIn("Mong muốn (Wants)", r1)

        # 2. Subscription chip
        r2 = generate_chatbot_response("Có subscription nào đang trừ tiền không?", health)
        self.assertIn("3 dịch vụ", r2)
        self.assertIn("ICLOUD", r2)

        # 3. Dining
        r3 = generate_chatbot_response("Ăn uống tháng này thế nào?", health)
        self.assertIn("Ăn uống & Cà phê ngoài", r3)

        # 4. No false-positive on 'ăn' in băn khoăn
        r4 = generate_chatbot_response("Tôi đang rất băn khoăn về ngân sách", health)
        self.assertNotIn("Ăn uống & Cà phê ngoài", r4)

    def test_07_http_routes_and_sorting(self):
        client = app.test_client()
        client.post("/login", data={"username": "nguyen_van_a", "password": "password123"}, follow_redirects=True)

        # Check dashboard
        dash = client.get("/dashboard")
        self.assertEqual(dash.status_code, 200)

        # Check transactions page
        tx_page = client.get("/transactions")
        self.assertEqual(tx_page.status_code, 200)

        # Check analytics page
        an_page = client.get("/analytics")
        self.assertEqual(an_page.status_code, 200)
        an_html = an_page.data.decode("utf-8")
        self.assertNotIn("rgba(255,255,255,0.65)", an_html, "White text on white card was not fixed!")

        # Check chat api
        chat_res = client.post("/api/chat", json={"message": "Tháng này tôi tiêu bao nhiêu?"})
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.get_json()
        self.assertIn("Tổng đã chi", chat_data.get("reply", ""))

if __name__ == "__main__":
    unittest.main()
