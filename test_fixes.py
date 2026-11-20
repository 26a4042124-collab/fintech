import json
import unittest
from unittest.mock import patch
from modules.ai_categorizer import categorize_transaction, process_all_transactions
from modules.health_scoring import compute_financial_health
from modules.chatbot_ai import generate_chatbot_response, mask_pii
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
        self.assertIn("meta", chat_data)
        self.assertTrue(chat_data["meta"].get("pii_masked"))

    def test_08_pii_masking_decree_13(self):
        """TECH-11: Đảm bảo mask_pii() ẩn danh sạch PII theo NĐ 13 và không làm hỏng số tiền VNĐ"""
        user_profile = {
            "full_name": "Nguyễn Văn A",
            "username": "nguyen_van_a",
            "email": "nguyenvana.fintech@example.com",
            "phone": "0988776655",
        }
        consents = [
            {"bank_name": "Vietcombank", "account_no": "1028475938", "status": "ACTIVE"},
            {"bank_name": "Techcombank", "account_no": "19038475920", "status": "ACTIVE"},
        ]
        raw_text = (
            "Tôi là Nguyễn Văn A (Nguyen Van A), email nguyenvana.fintech@example.com, "
            "SĐT 0988776655, CCCD 001204012345, STK 1028475938 và TK 19038475920, "
            "thẻ 4532-1234-5678-9012. Thu nhập 18,000,000đ, vừa uống cà phê 45000đ."
        )
        masked, fields = mask_pii(raw_text, user_profile=user_profile, consents=consents)

        # Khẳng định KHÔNG còn dữ liệu định danh cá nhân
        for secret in [
            "Nguyễn Văn A",
            "Nguyen Van A",
            "nguyenvana.fintech@example.com",
            "0988776655",
            "001204012345",
            "1028475938",
            "19038475920",
            "4532-1234-5678-9012",
        ]:
            self.assertNotIn(secret, masked, f"PII '{secret}' bị lọt qua mask_pii()!")

        # Khẳng định giữ nguyên số tiền VNĐ để AI không tính sai
        self.assertIn("18,000,000đ", masked)
        self.assertIn("45000đ", masked)
        self.assertIn("[KHACH_HANG]", masked)
        self.assertIn("[SDT_AN_DANH]", masked)
        self.assertIn("[STK_AN_DANH]", masked)
        self.assertIn("[EMAIL_AN_DANH]", masked)
        self.assertIn("[CCCD_AN_DANH]", masked)
        self.assertIn("[SO_THE_AN_DANH]", masked)
        self.assertGreaterEqual(len(fields), 5)

    def test_09_chatbot_hybrid_rag_and_offline_fallback(self):
        """TECH-11: Kiểm chứng Hybrid RAG gửi prompt đã ẩn danh PII, tôn trọng Consent & Fallback Offline"""
        with open("data/mock_transactions.json", "r", encoding="utf-8") as f:
            txns = json.load(f)
        enriched = process_all_transactions(txns)
        health = compute_financial_health(enriched)
        health["consents"] = [
            {"bank_name": "Vietcombank", "account_no": "1028475938", "status": "ACTIVE"}
        ]
        user_profile = {
            "full_name": "Nguyễn Văn A",
            "phone": "0988776655",
            "email": "nguyenvana.fintech@example.com",
            "open_banking_consent": {"ai_analytics": True},
        }
        prompt_with_pii = "Tôi là Nguyễn Văn A, SĐT 0988776655, STK 1028475938. Tháng này tôi tiêu bao nhiêu?"

        # 1. Mock Gemini online: kiểm tra payload gửi lên Gemini KHÔNG chứa bất kỳ PII nào
        captured = {}
        def fake_gemini(masked_q, safe_ctx, masked_draft):
            captured["q"] = masked_q
            captured["ctx"] = safe_ctx
            captured["draft"] = masked_draft
            return "Trả lời từ Gemini Hybrid dựa trên số liệu Python.", "gemini-3.5-flash-lite"

        with patch("modules.chatbot_ai._call_gemini_hybrid", side_effect=fake_gemini):
            reply, meta = generate_chatbot_response(
                prompt_with_pii, health, user_profile=user_profile, use_llm=True, return_meta=True
            )
        self.assertEqual(meta["engine"], "gemini-hybrid (gemini-3.5-flash-lite)")
        self.assertIn("Gemini Hybrid", reply)
        combined_outbound = captured["q"] + captured["ctx"] + captured["draft"]
        for secret in ["Nguyễn Văn A", "0988776655", "1028475938", "nguyenvana.fintech@example.com"]:
            self.assertNotIn(secret, combined_outbound)

        # 2. Mô phỏng mất mạng / 503 (Gemini trả về None, None): rơi êm về Rule-Based Offline
        with patch("modules.chatbot_ai._call_gemini_hybrid", return_value=(None, None)):
            reply_off, meta_off = generate_chatbot_response(
                prompt_with_pii, health, user_profile=user_profile, use_llm=True, return_meta=True
            )
        self.assertEqual(meta_off["engine"], "rule-based-offline")
        self.assertEqual(meta_off["fallback_reason"], "api_unavailable_or_no_key")
        self.assertIn("Tổng đã chi", reply_off)

        # 3. Khi user tắt quyền AI Analytics theo NĐ 13: không gọi LLM bên ngoài
        user_no_ai = dict(user_profile, open_banking_consent={"ai_analytics": False})
        with patch("modules.chatbot_ai._call_gemini_hybrid") as mock_llm:
            _, meta_no_ai = generate_chatbot_response(
                prompt_with_pii, health, user_profile=user_no_ai, use_llm=True, return_meta=True
            )
            mock_llm.assert_not_called()
        self.assertEqual(meta_no_ai["fallback_reason"], "ai_consent_disabled")

if __name__ == "__main__":
    unittest.main()
