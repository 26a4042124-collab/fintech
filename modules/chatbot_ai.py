import re

def generate_chatbot_response(user_message, health_data):
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
            scopes_txt = []
            if c.get("scopes", {}).get("read_balance"): scopes_txt.append("Xem số dư")
            if c.get("scopes", {}).get("read_transactions"): scopes_txt.append("Xem giao dịch")
            if c.get("scopes", {}).get("analyze_ai"): scopes_txt.append("Phân tích AI")
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
        
    # 8. Câu hỏi về Điểm sức khỏe tài chính & Tỷ lệ tùy chọn
    elif any(k in msg for k in ["sức khỏe", "điểm", "score", "tình hình", "thế nào", "đánh giá", "tỷ lệ"]):
        score = health_data.get("health_score", 58)
        status = health_data.get("health_status", "Cảnh báo")
        needs_p = health_data.get("needs", {}).get("percentage", 52)
        wants_p = health_data.get("wants", {}).get("percentage", 43)
        savings_p = health_data.get("savings", {}).get("percentage", 5)
        return (
            f"Điểm sức khỏe tài chính tháng này của bạn đạt **{score}/100 điểm** - Mức **{status}**.\n\n"
            f"• **Thiết yếu**: Thực tế **{needs_p}%** (Mục tiêu của bạn: {bench_needs}%)\n"
            f"• **Mong muốn**: Thực tế **{wants_p}%** (Mục tiêu của bạn: {bench_wants}%)\n"
            f"• **Tiết kiệm**: Thực tế **{savings_p}%** (Mục tiêu của bạn: {bench_savings}%)\n\n"
            f"Bạn có thể điều chỉnh lại Tỷ lệ ngân sách mong muốn bất kỳ lúc nào tại nút **'Tỷ lệ ngân sách'** trên thanh menu!"
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
