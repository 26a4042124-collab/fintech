import json
import os
import re
import sys
import unicodedata


def _strip_accents(text):
    if not text:
        return ""
    s = unicodedata.normalize("NFD", str(text))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _rule_based_response(user_message, health_data):
    """
    Trợ lý AI FinLab Chatbot:
    Trả lời các câu hỏi về tài chính cá nhân dựa trên đúng dữ liệu dòng tiền,
    kết quả kiểm toán rò rỉ, tỷ lệ tùy chọn, dự báo dòng tiền và mục tiêu tài chính của người dùng.
    """
    msg = user_message.strip().lower()
    
    # Lấy thông tin cơ bản
    income = max(float(health_data.get("income", 18000000) or 18000000), 1)
    target_ratio = health_data.get("target_ratio", {"needs": 50, "wants": 30, "savings": 20})
    bench_needs = target_ratio.get("needs", 50)
    bench_wants = target_ratio.get("wants", 30)
    bench_savings = target_ratio.get("savings", 20)
    
    # 0. Câu hỏi về Tổng chi tiêu / Tiêu bao nhiêu / Đã tiêu
    if any(k in msg for k in ["tiêu bao nhiêu", "tổng chi", "chi tiêu tháng", "đã tiêu", "tổng chi tiêu"]):
        tot_exp = health_data.get("total_expense", 0)
        needs_amt = health_data.get("needs", {}).get("amount", 0)
        needs_pct = health_data.get("needs", {}).get("percentage", 0)
        wants_amt = health_data.get("wants", {}).get("amount", 0)
        wants_pct = health_data.get("wants", {}).get("percentage", 0)
        sav_amt = health_data.get("savings", {}).get("amount", 0)
        sav_pct = health_data.get("savings", {}).get("percentage", 0)
        rem = health_data.get("net_remaining", 0)
        burn = health_data.get("cashflow_forecast", {}).get("daily_burn_rate", 0)
        return (
            f"💸 **Tổng kết chi tiêu tháng này của bạn:**\n\n"
            f"• **Tổng đã chi**: **{tot_exp:,.0f} VNĐ** (trên tổng thu nhập {income:,.0f} VNĐ)\n"
            f"• **Thiết yếu (Needs)**: **{needs_amt:,.0f} VNĐ** ({needs_pct}%)\n"
            f"• **Mong muốn (Wants)**: **{wants_amt:,.0f} VNĐ** ({wants_pct}%)\n"
            f"• **Tiết kiệm (Savings)**: **{sav_amt:,.0f} VNĐ** ({sav_pct}%)\n"
            f"• **Số dư ròng còn lại**: **{rem:,.0f} VNĐ**\n\n"
            f"💡 Tốc độ tiêu dùng trung bình hiện tại: **{burn:,.0f} VNĐ/ngày**."
        )

    # 0b. Câu hỏi về Khoản chi bất thường / Rò rỉ / Cảnh báo (Khớp với Chip '⚠️ Bất thường?')
    elif any(k in msg for k in ["bất thường", "chi tiêu bất thường", "có gì lạ", "bất thường không", "cảnh báo"]):
        sub_data = health_data.get("subscription_leaks", {})
        sub_cnt = sub_data.get("count", 0)
        sub_tot = sub_data.get("total_amount", 0)
        imp_data = health_data.get("impulse_night_spending", {})
        imp_cnt = imp_data.get("count", 0)
        imp_tot = imp_data.get("total_amount", 0)
        cat_budgets = health_data.get("category_budgets", [])
        over_items = [c for c in cat_budgets if c.get("status") == "danger"]
        
        reply = "⚠️ **BÁO CÁO CÁC KHOẢN CHI BẤT THƯỜNG & RÒ RỈ:**\n\n"
        has_issue = False
        if sub_cnt > 0:
            has_issue = True
            reply += f"1. **Rò rỉ Subscription ngầm**: Phát hiện **{sub_cnt} dịch vụ định kỳ** tự động trừ thẻ (tổng cộng **{sub_tot:,.0f} VNĐ/tháng**).\n"
        if imp_cnt > 0:
            has_issue = True
            reply += f"2. **Mua sắm đêm bốc đồng**: Ghi nhận **{imp_cnt} đơn sau 22h00** với tổng tiền **{imp_tot:,.0f} VNĐ**.\n"
        if over_items:
            has_issue = True
            reply += f"3. **Vượt hạn mức ngân sách**: {len(over_items)} danh mục ({', '.join([it['category'] for it in over_items])}) đã vượt trần chi tiêu!\n"
        if not has_issue:
            reply += "🎉 Tuyệt vời! AI không phát hiện khoản chi tiêu nào bất thường hoặc vượt hạn mức trong kỳ này."
        else:
            reply += "\n👉 **Lời khuyên**: Bạn nên rà soát lại các gói dịch vụ định kỳ và áp dụng quy tắc chờ 24h trước khi chốt đơn đêm để tối ưu hóa ngân sách!"
        return reply

    # 0c. Câu hỏi về Ngân hàng & Tài khoản liên kết Open Banking
    elif any(k in msg for k in ["ngân hàng liên kết", "tài khoản liên kết", "ví liên kết", "đã kết nối", "kết nối ngân hàng"]):
        consents = health_data.get("consents", [])
        active_c = [c for c in consents if c.get("status") == "ACTIVE"]
        revoked_c = [c for c in consents if c.get("status") == "REVOKED"]
        if not active_c and not revoked_c:
            return (
                "🏦 **Hiện tại bạn chưa liên kết tài khoản ngân hàng nào qua Open Banking.**\n\n"
                "Bạn có thể vào mục **'Ví & Thẻ'** hoặc bấm **'Liên kết Open Banking'** trên Trang chủ để kết nối tài khoản an toàn theo Nghị định 13/2023/NĐ-CP!"
            )
        res = "🏦 **Trạng thái kết nối Open Banking của bạn:**\n\n"
        for c in active_c:
            raw_scopes = c.get("scopes") or {}
            has_scope = (lambda k: raw_scopes.get(k)) if isinstance(raw_scopes, dict) else (lambda k: k in raw_scopes)
            scopes_txt = []
            if has_scope("read_balance"): scopes_txt.append("Xem số dư")
            if has_scope("read_transactions"): scopes_txt.append("Xem giao dịch")
            if has_scope("analyze_ai"): scopes_txt.append("Phân tích AI")
            res += f"• 🟢 **{c.get('bank_name')}** (STK: {c.get('account_no')}): **Đang hoạt động**\n  ↳ Quyền cấp: {', '.join(scopes_txt)}\n  ↳ Hết hạn: {c.get('expires_at')}\n"
        for c in revoked_c:
            res += f"• 🔴 **{c.get('bank_name')}**: **Đã thu hồi quyền (Revoked)**\n"
        res += "\n💡 Bạn có thể bật/tắt từng quyền hoặc cấp lại quyền bất kỳ lúc nào trong **Hồ sơ & Quyền dữ liệu**!"
        return res

    # 1. Câu hỏi về Dự báo Dòng tiền / Cạn ví / Cuối tháng / Burn rate
    elif any(k in msg for k in ["dự báo", "dòng tiền", "cạn ví", "hết tiền", "thâm hụt", "burn rate", "tốc độ tiêu", "cuối tháng"]):
        cf = health_data.get("cashflow_forecast", {})
        burn = cf.get("daily_burn_rate", 0)
        day_broke = cf.get("day_broke")
        is_risk = cf.get("is_deficit_risk", False)
        deficit = cf.get("deficit_amount", 0)
        surplus = cf.get("surplus_amount", 0)
        
        if is_risk:
            return (
                f"⚠️ **CẢNH BÁO DÒNG TIỀN NGUY HIỂM!**\n\n"
                f"Tốc độ đốt tiền trung bình của bạn đang là **{burn:,.0f} VNĐ/ngày**.\n"
                f"• Dự kiến đến **ngày {day_broke}** bạn sẽ cạn ví và thâm hụt **{deficit:,.0f} VNĐ** vào cuối tháng.\n"
                f"👉 **Khuyến nghị khẩn cấp**: Cắt ngay các đơn hàng đêm và giảm 50% tiền ăn hàng quán từ hôm nay để đưa dòng tiền về mức an toàn!"
            )
        else:
            return (
                f"✅ **DÒNG TIỀN DỰ PHÓNG AN TOÀN**\n\n"
                f"Tốc độ chi tiêu trung bình của bạn là **{burn:,.0f} VNĐ/ngày**.\n"
                f"• Dự phóng đến cuối tháng bạn sẽ còn thặng dư **{surplus:,.0f} VNĐ** sau khi thanh toán mọi chi phí.\n"
                f"👉 Bạn nên trích ngay khoản này vào các Hũ Mục tiêu tiết kiệm để không bị tiêu lẹm nhé!"
            )

    # 2. Câu hỏi về Làm tròn tiền lẻ / Micro-investing / Heo đất
    elif any(k in msg for k in ["làm tròn", "tiền lẻ", "heo đất", "micro", "acorns", "tích lũy lẻ"]):
        ru = health_data.get("round_up", {})
        ru_total = ru.get("monthly_round_up_total", 0)
        ru_cnt = ru.get("transactions_count", 0)
        acc = ru.get("accumulated_total", 0)
        step = ru.get("step", 10000)
        return (
            f"🐷 **Tính năng Tích lũy Tiền lẻ (Heo Đất FinLab):**\n\n"
            f"• Quy tắc: Tự động làm tròn chi tiêu lên **{step:,.0f} VNĐ**.\n"
            f"• Tháng này bạn đã gom được **{ru_total:,.0f} VNĐ** tiền lẻ từ **{ru_cnt} giao dịch** chi tiêu.\n"
            f"• Tổng số tiền lẻ đã tích lũy trong Heo đất: **{acc:,.0f} VNĐ**.\n"
            f"💡 *Mẹo nhỏ*: Số tiền này tuy nhỏ nhưng sau 1 năm có thể đạt từ 2 - 3 triệu đồng, rất thích hợp nạp vào Quỹ khẩn cấp!"
        )

    # 3. Câu hỏi về Mục tiêu tài chính / Hũ tích lũy / Laptop / Quỹ khẩn cấp
    elif any(k in msg for k in ["mục tiêu", "hũ", "laptop", "khẩn cấp", "du lịch", "hoàn thành sau"]):
        goals = health_data.get("savings_goals", [])
        if not goals:
            return "Bạn chưa tạo mục tiêu tài chính nào. Hãy bấm nút **+ Thêm Mục Tiêu** trên Bảng điều khiển để AI theo dõi tiến độ giúp bạn nhé!"
            
        res = "🎯 **Tiến độ các Mục tiêu Tài chính của bạn:**\n\n"
        for g in goals:
            cur = g.get("current_amount", 0)
            tgt = g.get("target_amount", 1)
            pct = g.get("percentage", 0)
            res += f"• **{g.get('name')}**: Đã đạt **{pct}%** ({cur:,.0f}đ / {tgt:,.0f}đ).\n  ↳ {g.get('ai_forecast')}\n"
        return res

    # 4. Câu hỏi về Hạn mức chi tiêu theo danh mục
    elif any(k in msg for k in ["hạn mức", "trần", "vượt ngân sách", "danh mục"]):
        cat_budgets = health_data.get("category_budgets", [])
        over_items = [c for c in cat_budgets if c["status"] == "danger"]
        warn_items = [c for c in cat_budgets if c["status"] == "warning"]
        
        reply = "📊 **Báo cáo Giám sát Hạn mức Chi tiêu:**\n\n"
        if over_items:
            reply += "🚨 **Danh mục ĐÃ VƯỢT HẠN MỨC:**\n"
            for it in over_items:
                reply += f"- {it['category']}: Đã tiêu {it['spent']:,.0f}đ / {it['limit']:,.0f}đ (Vượt {it['overspent']:,.0f}đ!)\n"
            reply += "\n"
        if warn_items:
            reply += "⚠️ **Danh mục SẮP CHẠM TRẦN (>80%):**\n"
            for it in warn_items:
                reply += f"- {it['category']}: Đã tiêu {it['spent']:,.0f}đ / {it['limit']:,.0f}đ ({it['percentage']}%)\n"
            reply += "\n"
        if not over_items and not warn_items:
            reply += "🎉 Tuyệt vời! Tất cả các danh mục chi tiêu đều đang nằm trong hạn mức an toàn (<80%).\n"
        return reply

    # 5. Câu hỏi về Ăn uống / Cà phê
    elif any(re.search(r'\b' + re.escape(w) + r'\b', msg) for w in ["ăn", "uống", "ăn uống", "cà phê", "cafe", "nhà hàng", "quán ăn", "trà sữa", "cơm trưa"]):
        cat_breakdown = health_data.get("category_breakdown", {})
        dining_amt = cat_breakdown.get("Ăn uống & Cà phê ngoài", 0)
        pct = round((dining_amt / income) * 100, 1)
        return (
            f"Tháng này bạn đã chi **{dining_amt:,.0f} VNĐ** cho Ăn uống & Cà phê ngoài, chiếm **{pct}%** tổng thu nhập! "
            f"Khoản chi này thuộc nhóm *Mong muốn (Wants)*. "
            f"Nếu tự nấu ăn thêm 2-3 bữa mỗi tuần, bạn sẽ tiết kiệm ngay được khoảng **800.000 VNĐ - 1.200.000 VNĐ** mỗi tháng!"
        )
        
    # 6. Câu hỏi về Gói đăng ký ngầm / Rò rỉ định kỳ / Netflix / Spotify
    elif any(k in msg for k in ["ngầm", "rò rỉ", "định kỳ", "subscription", "netflix", "spotify", "icloud"]):
        sub_data = health_data.get("subscription_leaks", {})
        items = sub_data.get("items") or sub_data.get("list") or []
        total = sub_data.get("total_amount", 0)
        item_names = ", ".join([f"{it['merchant'][:45]} ({it['amount']:,.0f}đ)" for it in items])
        return (
            f"🔍 Hệ thống phát hiện **{len(items)} dịch vụ gia hạn tự động ngầm** hàng tháng của bạn với tổng số tiền **{total:,.0f} VNĐ/tháng**:\n"
            f"- Chi tiết: {item_names or 'Không có'}.\n"
            f"💡 **Khuyến nghị**: Bạn nên rà soát lại gói nào ít sử dụng để hủy ngay trước kỳ thanh toán tới, bảo vệ thêm **{total:,.0f} VNĐ** mỗi tháng!"
        )
        
    # 7. Câu hỏi về Mua sắm đêm / Chi tiêu bốc đồng / Shopee / TikTok
    elif any(k in msg for k in ["đêm", "khuya", "bốc đồng", "shopee", "tiktok", "chốt đơn"]):
        impulse_data = health_data.get("impulse_night_spending", {})
        total = impulse_data.get("total_amount", 0)
        cnt = impulse_data.get("count", 0)
        return (
            f"🌙 Hệ thống ghi nhận **{cnt} đơn hàng mua sắm/ăn vặt sau 22h00 đêm**, tổng cộng **{total:,.0f} VNĐ**.\n"
            f"Đây là thói quen 'chi tiêu cảm xúc' khiến ngân sách thâm hụt nhanh nhất. Áp dụng ngay quy tắc **'chờ 24 giờ trước khi thanh toán giỏ hàng đêm'** để cắt giảm ít nhất **{total:,.0f} VNĐ** lãng phí!"
        )
        
    # 8. Câu hỏi về Điểm sức khỏe tài chính & Tự chia tỷ lệ theo thu nhập
    elif any(k in msg for k in ["sức khỏe", "điểm", "score", "tình hình", "thế nào", "đánh giá", "tỷ lệ", "chia ngân sách", "gợi ý chia", "thu nhập"]):
        score = health_data.get("health_score", 62)
        status = health_data.get("health_status", "Cảnh báo")
        needs_p = health_data.get("needs", {}).get("percentage", 0)
        wants_p = health_data.get("wants", {}).get("percentage", 0)
        savings_p = health_data.get("savings", {}).get("percentage", 0)
        tr = health_data.get("target_ratio", {})
        needs_amt = tr.get("needs_amount", int(round(income * bench_needs / 100.0)))
        wants_amt = tr.get("wants_amount", int(round(income * bench_wants / 100.0)))
        savings_amt = tr.get("savings_amount", int(round(income * bench_savings / 100.0)))
        sugg = health_data.get("income_suggestion", {})
        sugg_line = ""
        if sugg:
            sugg_line = (
                f"\n💡 **Gợi ý theo bậc thu nhập ({sugg.get('bracket', '')})**: "
                f"**{sugg.get('needs')}% / {sugg.get('wants')}% / {sugg.get('savings')}%** — {sugg.get('reason')}\n"
            )
        return (
            f"Điểm sức khỏe tài chính tháng này của bạn đạt **{score}/100 điểm** - Mức **{status}** "
            f"(đối chiếu trên thu nhập **{income:,.0f} VNĐ**).\n\n"
            f"• **Thiết yếu**: Thực tế **{needs_p}%** / mục tiêu bạn chia **{bench_needs}%** ({needs_amt:,.0f}đ)\n"
            f"• **Mong muốn**: Thực tế **{wants_p}%** / mục tiêu bạn chia **{bench_wants}%** ({wants_amt:,.0f}đ)\n"
            f"• **Tiết kiệm**: Thực tế **{savings_p}%** / mục tiêu bạn chia **{bench_savings}%** ({savings_amt:,.0f}đ)\n"
            f"{sugg_line}\n"
            f"Bạn có thể tự chia lại tỷ lệ & thu nhập bất kỳ lúc nào tại mục **'Tự chia ngân sách'** trên menu hoặc trang Ngân sách!"
        )
        
    # 9. Câu hỏi về Tiết kiệm / Cách tiết kiệm / Bù đắp
    elif any(k in msg for k in ["tiết kiệm", "để dành", "làm sao", "lời khuyên", "kế hoạch"]):
        target = income * (bench_savings / 100.0)
        gap = health_data.get("savings_gap", 2700000)
        sub_total = health_data.get("subscription_leaks", {}).get("total_amount", 609000)
        night_total = health_data.get("impulse_night_spending", {}).get("total_amount", 2270000)
        round_total = health_data.get("round_up", {}).get("monthly_round_up_total", 31000)
        sub_cut = min(sub_total, 550000) if sub_total >= 550000 else sub_total
        night_cap = 2000000 if night_total >= 2000000 else night_total
        night_cut = min(night_cap, max(0, gap - sub_cut))
        rem_cut = max(0, gap - sub_cut - night_cut)
        return (
            f"Để đạt đúng tỷ lệ tiết kiệm mục tiêu {bench_savings}% thu nhập (**{target:,.0f} VNĐ/tháng**), bạn cần bù đắp khoản thiếu hụt **{gap:,.0f} VNĐ** bằng phác đồ sau:\n"
            f"1. Rà soát & hủy các gói dịch vụ số ít dùng (trong tổng {sub_total:,.0f}đ): tiết kiệm **+{sub_cut:,.0f} VNĐ**.\n"
            f"2. Cắt giảm mua sắm bốc đồng sau 22h (trong tổng {night_total:,.0f}đ): tiết kiệm **+{night_cut:,.0f} VNĐ**.\n"
            f"3. Kết chuyển từ số dư khả dụng & Heo đất làm tròn ({round_total:,.0f}đ tiền lẻ): bổ sung **+{rem_cut:,.0f} VNĐ**.\n"
            f"👉 Tổng bù đắp tối ưu: **{gap:,.0f} VNĐ** ➔ Đạt chuẩn {bench_savings}% tiết kiệm ngay tháng này!"
        )

    # 10. Câu hỏi về Ngân hàng liên kết / Open Banking
    elif any(k in msg for k in ["ngân hàng", "liên kết", "open banking", "ví liên kết", "ais"]):
        consents = health_data.get("consents", [])
        active_consents = [c for c in consents if c.get("status") == "ACTIVE"]
        if active_consents:
            bank_names = ", ".join([f"**{c.get('bank_name', 'Ngân hàng')}**" for c in active_consents])
            return (
                f"🏦 Bạn hiện đang liên kết thành công với: {bank_names}.\n\n"
                f"• FinLab tự động đồng bộ dữ liệu giao dịch theo chuẩn Open API (Thông tư 64/2024/TT-NHNN) với thời hạn 90 ngày.\n"
                f"• Bạn có toàn quyền quản lý từng phạm vi hoặc **Thu hồi quyền (Revoke Consent)** bất kỳ lúc nào tại mục **'Quyền Dữ liệu Open Banking'** trong trang Cá nhân!"
            )
        else:
            return (
                f"🏦 Bạn hiện chưa có ngân hàng nào kết nối ở trạng thái hoạt động.\n"
                f"Hãy vào mục **Ví & Tài khoản** hoặc **Cá nhân** để liên kết tài khoản ngân hàng an toàn theo Nghị định 13/2023/NĐ-CP!"
            )

    # 11. Câu hỏi về Bảo mật / Quyền riêng tư / Nghị định 13
    elif any(k in msg for k in ["bảo mật", "nghị định 13", "an toàn", "quyền", "consent"]):
        return (
            f"🛡️ **Cam kết Bảo mật & Tuân thủ Pháp lý của FinLab:**\n\n"
            f"• Tuân thủ nghiêm ngặt **Nghị định 13/2023/NĐ-CP** về Bảo vệ dữ liệu cá nhân.\n"
            f"• Tuân thủ **Thông tư 64/2024/TT-NHNN** về Tiêu chuẩn Kỹ thuật Open API ngành Ngân hàng.\n"
            f"• Bạn có toàn quyền bật/tắt từng phạm vi truy cập (`Xem số dư`, `Xem giao dịch`, `Phân tích AI`) hoặc **Thu hồi quyền (Revoke Consent)** bất kỳ lúc nào trong Trung tâm Quản trị Quyền!"
        )
        
    # 11. Mặc định / Lời chào
    else:
        return (
            f"Chào bạn! Tôi là Trợ lý AI **FinLab**. Tôi đã phân tích toàn bộ dữ liệu dòng tiền qua Open Banking của bạn tháng này.\n\n"
            f"Bạn có thể hỏi tôi:\n"
            f"• *'Dự báo dòng tiền cuối tháng của tôi thế nào, có bị cạn ví không?'*\n"
            f"• *'Tháng này tôi gom được bao nhiêu tiền lẻ Heo đất?'*\n"
            f"• *'Tiến độ mục tiêu mua Laptop và Quỹ khẩn cấp ra sao?'*\n"
            f"• *'Các danh mục nào đang vượt hạn mức chi tiêu?'*\n"
            f"• *'Có khoản đăng ký ngầm nào đang trừ tiền không?'*"
        )


# ==========================================================================
# TECH-11: CỔNG ẨN DANH PII (NĐ 13/2023/NĐ-CP) & HYBRID RAG GEMINI + FALLBACK
# ==========================================================================

SYSTEM_PROMPT = """Bạn là Trợ lý Tài chính AI FinLab (tuân thủ Nghị định 13/2023/NĐ-CP & Thông tư 64/2024/TT-NHNN).
QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng đúng các con số có trong dữ liệu JSON và bản nháp hệ thống cung cấp; TUYỆT ĐỐI KHÔNG tự bịa hay suy đoán thêm số tiền mới.
2. Trả lời bằng tiếng Việt tự nhiên, thân thiện, ngắn gọn (tối đa 160 từ), đưa ra 1-2 lời khuyên hành động thực tế.
3. Định dạng hiển thị trên điện thoại: chỉ dùng **in đậm** và gạch đầu dòng `• `, KHÔNG dùng bảng Markdown hay tiêu đề `###`.
4. Giữ nguyên các thẻ ẩn danh như [KHACH_HANG], [SDT_AN_DANH], [STK_AN_DANH], [EMAIL_AN_DANH] nếu có; tuyệt đối không tự suy đoán thông tin cá nhân."""


def mask_pii(text, user_profile=None, consents=None):
    """
    Ẩn danh toàn bộ dữ liệu định danh cá nhân (PII) trước khi gửi ra LLM bên ngoài
    nhằm tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân.
    Trả về tuple: (masked_text, masked_types).
    """
    if not text:
        return "", []
    masked = str(text)
    masked_types = []

    def _sub(pattern, repl, label, flags=0):
        nonlocal masked
        new_text, count = re.subn(pattern, repl, masked, flags=flags)
        if count > 0:
            masked = new_text
            if label not in masked_types:
                masked_types.append(label)

    # 1. Che thông tin định danh lấy từ hồ sơ người dùng (có dấu & không dấu)
    if isinstance(user_profile, dict):
        full_name = str(user_profile.get("full_name") or "").strip()
        if len(full_name) >= 3:
            _sub(re.escape(full_name), "[KHACH_HANG]", "Họ tên", flags=re.IGNORECASE)
            no_acc = _strip_accents(full_name)
            if no_acc.lower() != full_name.lower() and len(no_acc) >= 3:
                _sub(re.escape(no_acc), "[KHACH_HANG]", "Họ tên", flags=re.IGNORECASE)

        username = str(user_profile.get("username") or "").strip()
        if len(username) >= 5 and username.lower() not in ("admin", "guest", "khach"):
            _sub(r"\b" + re.escape(username) + r"\b", "[KHACH_HANG]", "Tên đăng nhập", flags=re.IGNORECASE)

        email = str(user_profile.get("email") or "").strip()
        if len(email) >= 5:
            _sub(re.escape(email), "[EMAIL_AN_DANH]", "Email", flags=re.IGNORECASE)

        phone = str(user_profile.get("phone") or "").strip()
        if len(phone) >= 9:
            _sub(re.escape(phone), "[SDT_AN_DANH]", "SĐT")

    # 2. Che chính xác tất cả số tài khoản ngân hàng trong Open Banking Consents
    for c in (consents or []):
        if isinstance(c, dict):
            acc = str(c.get("account_no") or "").strip()
            if len(acc) >= 6:
                _sub(re.escape(acc), "[STK_AN_DANH]", "Số tài khoản")

    # 3. Che theo mẫu regex chuẩn (tránh che nhầm số tiền VNĐ như 18,000,000 hoặc 45000)
    _sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_AN_DANH]", "Email")
    _sub(r"(?<!\d)(?:\d{4}[-\s]?){3}\d{4}(?!\d)", "[SO_THE_AN_DANH]", "Số thẻ")
    _sub(r"(?<!\d)\d{12}(?!\d)", "[CCCD_AN_DANH]", "CCCD")
    _sub(
        r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)(?:[\s\.-]?\d){8}(?!\d)",
        "[SDT_AN_DANH]",
        "SĐT",
    )
    _sub(
        r"(?i)\b(stk|số tài khoản|so tai khoan|tài khoản|tai khoan|tk)\s*[:#-]?\s*(\d{8,16})\b",
        r"\1 [STK_AN_DANH]",
        "Số tài khoản",
    )

    return masked, masked_types


def _build_safe_financial_context(health_data):
    """
    Chỉ gom các chỉ số tài chính tổng hợp đã được Python tính chính xác (chống ảo giác),
    loại bỏ hoàn toàn thông tin định danh cá nhân (Họ tên, SĐT, Email, STK).
    """
    tr = health_data.get("target_ratio") or {}
    cf = health_data.get("cashflow_forecast") or {}
    sub = health_data.get("subscription_leaks") or {}
    night = health_data.get("impulse_night_spending") or {}
    ru = health_data.get("round_up") or {}

    consents_safe = [
        {"bank_name": c.get("bank_name"), "status": c.get("status")}
        for c in (health_data.get("consents") or [])
        if isinstance(c, dict)
    ]
    goals_safe = [
        {
            "name": g.get("name"),
            "current_vnd": g.get("current_amount", 0),
            "target_vnd": g.get("target_amount", 0),
            "percentage": g.get("percentage", 0),
            "forecast": g.get("ai_forecast", ""),
        }
        for g in (health_data.get("savings_goals") or [])
        if isinstance(g, dict)
    ]
    budgets_safe = [
        {
            "category": b.get("category"),
            "spent_vnd": b.get("spent", 0),
            "limit_vnd": b.get("limit", 0),
            "percentage": b.get("percentage", 0),
            "status": b.get("status", "safe"),
        }
        for b in (health_data.get("category_budgets") or [])
        if isinstance(b, dict)
    ]

    context = {
        "monthly_income_vnd": health_data.get("income", 0),
        "total_expense_vnd": health_data.get("total_expense", 0),
        "net_remaining_vnd": health_data.get("net_remaining", 0),
        "health_score": health_data.get("health_score", 0),
        "health_status": health_data.get("health_status", ""),
        "target_ratio": {
            "needs_pct": tr.get("needs", 50),
            "wants_pct": tr.get("wants", 30),
            "savings_pct": tr.get("savings", 20),
            "needs_vnd": tr.get("needs_amount", 0),
            "wants_vnd": tr.get("wants_amount", 0),
            "savings_vnd": tr.get("savings_amount", 0),
        },
        "income_suggestion": health_data.get("income_suggestion") or {},
        "actual_buckets": {
            "needs": health_data.get("needs") or {},
            "wants": health_data.get("wants") or {},
            "savings": health_data.get("savings") or {},
        },
        "savings_gap_vnd": health_data.get("savings_gap", 0),
        "cashflow_forecast": {
            "daily_burn_rate_vnd": cf.get("daily_burn_rate", 0),
            "is_deficit_risk": cf.get("is_deficit_risk", False),
            "day_broke": cf.get("day_broke"),
            "deficit_vnd": cf.get("deficit_amount", 0),
            "surplus_vnd": cf.get("surplus_amount", 0),
        },
        "subscription_leaks": {
            "count": sub.get("count", 0),
            "total_vnd": sub.get("total_amount", 0),
            "merchants": [
                str(i.get("merchant", ""))[:45]
                for i in (sub.get("items") or sub.get("list") or [])
                if isinstance(i, dict)
            ],
        },
        "night_impulse_spending": {
            "count": night.get("count", 0),
            "total_vnd": night.get("total_amount", 0),
        },
        "round_up_savings": {
            "step_vnd": ru.get("step", 10000),
            "monthly_vnd": ru.get("monthly_round_up_total", 0),
            "transactions_count": ru.get("transactions_count", 0),
            "accumulated_vnd": ru.get("accumulated_total", 0),
        },
        "category_breakdown_vnd": health_data.get("category_breakdown") or {},
        "category_budgets": budgets_safe,
        "savings_goals": goals_safe,
        "connected_banks": consents_safe,
    }

    # Sẵn sàng đón dữ liệu TECH-12 (OCR & CreditTech) khi tích hợp
    if health_data.get("last_ocr_receipt"):
        context["last_ocr_receipt"] = health_data.get("last_ocr_receipt")
    if health_data.get("credit_profile"):
        context["credit_profile"] = health_data.get("credit_profile")

    return context


def _call_gemini_hybrid(masked_question, safe_context_str, masked_rule_draft):
    """
    Gọi Gemini API (Hybrid RAG) với cơ chế dự phòng 2 model và timeout nhanh.
    Trả về (reply_text, model_name) hoặc (None, None) nếu offline/lỗi/hết quota.
    """
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key or api_key in ("your_gemini_api_key_here", "invalid"):
        return None, None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None, None

    primary_model = (os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash-lite").strip()
    fallback_model = (os.environ.get("GEMINI_FALLBACK_MODEL") or "gemini-3.7-flash").strip()
    models_to_try = list(dict.fromkeys([m for m in (primary_model, fallback_model) if m]))

    prompt = (
        "=== DỮ LIỆU TÀI CHÍNH ĐÃ TÍNH BẰNG PYTHON (ĐÃ ẨN DANH PII) ===\n"
        f"{safe_context_str}\n\n"
        "=== BẢN NHÁP SỐ LIỆU CHUẨN TỪ HỆ THỐNG ===\n"
        f"{masked_rule_draft}\n\n"
        "=== CÂU HỎI CỦA NGƯỜI DÙNG (ĐÃ ẨN DANH PII) ===\n"
        f"{masked_question}"
    )

    try:
        client = genai.Client(
            api_key=api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=12000,  # Google yêu cầu tối thiểu 10s (10000ms)
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
            temperature=0.3,
            max_output_tokens=550,
        )
    except Exception as e:
        print(f"[FinLab Chatbot Fallback] Khởi tạo Gemini client lỗi: {e}")
        return None, None

    for model_name in models_to_try:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=cfg,
            )
            text = (getattr(res, "text", None) or "").strip()
            if text:
                return text, model_name
        except Exception as e:
            print(f"[FinLab Chatbot Fallback] Model {model_name} không khả dụng: {e}")

    return None, None


def generate_chatbot_response(
    user_message,
    health_data,
    user_profile=None,
    use_llm=None,
    return_meta=False,
):
    """
    Trợ lý AI FinLab Chatbot — Kiến trúc Hybrid RAG + Ẩn danh PII (NĐ 13/2023/NĐ-CP):
    1. Python tính số liệu tuyệt đối & tạo bản trả lời chuẩn (chống ảo giác + dự phòng offline).
    2. Cổng mask_pii() ẩn danh toàn bộ Họ tên, SĐT, Email, STK, CCCD, Số thẻ.
    3. Gọi Gemini LLM diễn đạt tự nhiên; tự động rơi êm về Offline nếu mất mạng/503/tắt quyền AI.
    """
    health_data = health_data or {}
    consents = health_data.get("consents") or []

    # Tầng 1: Rule-based Python (số liệu chính xác tuyệt đối & fallback offline)
    rule_reply = _rule_based_response(user_message, health_data)

    # Tầng 2: Cổng ẩn danh PII theo Nghị định 13/2023/NĐ-CP
    masked_question, q_masked = mask_pii(user_message, user_profile=user_profile, consents=consents)
    safe_ctx = _build_safe_financial_context(health_data)
    safe_ctx_str, c_masked = mask_pii(
        json.dumps(safe_ctx, ensure_ascii=False),
        user_profile=user_profile,
        consents=consents,
    )
    masked_rule_draft, d_masked = mask_pii(rule_reply, user_profile=user_profile, consents=consents)
    all_masked_fields = sorted(set(q_masked + c_masked + d_masked))

    # Kiểm tra quyền AI Analytics theo Nghị định 13 (nếu user đã tắt thì chỉ chạy offline cục bộ)
    ai_consent_allowed = True
    if isinstance(user_profile, dict):
        ob_consent = user_profile.get("open_banking_consent")
        if isinstance(ob_consent, dict) and ob_consent.get("ai_analytics") is False:
            ai_consent_allowed = False

    # Quyết định bật/tắt tầng LLM
    if use_llm is None:
        in_test_runner = ("unittest" in sys.modules) or ("pytest" in sys.modules)
        offline_flag = os.environ.get("FINLAB_CHATBOT_OFFLINE", "0") == "1"
        use_llm = (not in_test_runner) and (not offline_flag)

    engine = "rule-based-offline"
    fallback_reason = None
    final_reply = rule_reply

    if use_llm and ai_consent_allowed:
        llm_reply, used_model = _call_gemini_hybrid(
            masked_question, safe_ctx_str, masked_rule_draft
        )
        if llm_reply:
            final_reply = llm_reply
            engine = f"gemini-hybrid ({used_model})"
        else:
            fallback_reason = "api_unavailable_or_no_key"
    elif use_llm and not ai_consent_allowed:
        fallback_reason = "ai_consent_disabled"

    meta = {
        "engine": engine,
        "pii_masked": True,
        "masked_fields": all_masked_fields,
        "masked_question": masked_question,
        "ai_consent_allowed": ai_consent_allowed,
        "fallback_reason": fallback_reason,
    }
    return (final_reply, meta) if return_meta else final_reply
