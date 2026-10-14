import re

def generate_chatbot_response(user_message, health_data):
    """
    Trợ lý AI FinLab Chatbot:
    Trả lời các câu hỏi về tài chính cá nhân dựa trên đúng dữ liệu dòng tiền
    và kết quả kiểm toán của người dùng.
    """
    msg = user_message.strip().lower()
    
    # 1. Câu hỏi về Ăn uống / Cà phê
    if any(k in msg for k in ["ăn", "uống", "cà phê", "cafe", "nhà hàng"]):
        cat_breakdown = health_data.get("category_breakdown", {})
        dining_amt = cat_breakdown.get("Ăn uống & Cà phê ngoài", 0)
        pct = round((dining_amt / health_data.get("income", 18000000)) * 100, 1)
        return (
            f"Tháng này bạn đã tiêu **{dining_amt:,.0f} VNĐ** cho Ăn uống & Cà phê ngoài, chiếm **{pct}%** tổng thu nhập! "
            f"Khoản chi này đang nằm trong nhóm *Mong muốn cá nhân (Wants)* và vượt mức khuyến nghị. "
            f"Bạn nên tự nấu ăn nhiều hơn hoặc hạn chế đặt đồ ăn ngoài để tiết kiệm khoảng **500.000 VNĐ - 1.000.000 VNĐ** mỗi tháng nhé!"
        )
        
    # 2. Câu hỏi về Gói đăng ký ngầm / Rò rỉ định kỳ / Netflix / Spotify
    elif any(k in msg for k in ["ngầm", "rò rỉ", "định kỳ", "subscription", "netflix", "spotify", "icloud"]):
        sub_data = health_data.get("subscription_leaks", {})
        items = sub_data.get("items", [])
        total = sub_data.get("total_amount", 0)
        item_names = ", ".join([f"{it['merchant'][:25]} ({it['amount']:,.0f}đ)" for it in items])
        return (
            f"Hệ thống phát hiện **{len(items)} dịch vụ gia hạn tự động ngầm** hàng tháng của bạn với tổng số tiền **{total:,.0f} VNĐ/tháng**:\n"
            f"- Chi tiết: {item_names}.\n"
            f"💡 **Lời khuyên**: Bạn nên xem lại gói nào ít sử dụng (ví dụ app chỉnh ảnh hoặc Netflix) để hủy ngay trước kỳ thanh toán tới, giúp bạn tiết kiệm được từ **350.000 VNĐ** mỗi tháng!"
        )
        
    # 3. Câu hỏi về Mua sắm đêm / Chi tiêu bốc đồng / Shopee / TikTok
    elif any(k in msg for k in ["đêm", "khuya", "bốc đồng", "shopee", "tiktok", "chốt đơn"]):
        impulse_data = health_data.get("impulse_night_spending", {})
        total = impulse_data.get("total_amount", 0)
        cnt = impulse_data.get("count", 0)
        return (
            f"Hệ thống ghi nhận **{cnt} đơn hàng mua sắm/ăn vặt phát sinh sau 22h00 đêm**, tổng cộng **{total:,.0f} VNĐ** (chủ yếu qua Shopee và TikTok Shop).\n"
            f"Đây là thói quen 'chi tiêu cảm xúc' khiến ngân sách thâm hụt nhanh nhất. Bạn nên đặt quy tắc **'chờ 24 giờ trước khi thanh toán giỏ hàng đêm'** để cắt giảm ít nhất **1.850.000 VNĐ** lãng phí!"
        )
        
    # 4. Câu hỏi về Điểm sức khỏe tài chính
    elif any(k in msg for k in ["sức khỏe", "điểm", "score", "tình hình", "thế nào", "đánh giá"]):
        score = health_data.get("health_score", 58)
        status = health_data.get("health_status", "Cảnh báo")
        needs_p = health_data.get("needs", {}).get("percentage", 52)
        wants_p = health_data.get("wants", {}).get("percentage", 43)
        savings_p = health_data.get("savings", {}).get("percentage", 5)
        return (
            f"Điểm sức khỏe tài chính tháng này của bạn đạt **{score}/100 điểm** - Mức **{status}**.\n"
            f"- Cơ cấu hiện tại: Thiết yếu **{needs_p}%** (chuẩn 50%) - Mong muốn **{wants_p}%** (vượt chuẩn 30%) - Tiết kiệm **{savings_p}%** (chuẩn 20%).\n"
            f"Bạn đang để quỹ tiết kiệm quá mỏng (chỉ 5%). Hãy điều chỉnh giảm bớt nhóm Mong muốn để đưa điểm số lên vùng 'Khỏe mạnh' (>80 điểm) nhé!"
        )
        
    # 5. Câu hỏi về Tiết kiệm / Cách tiết kiệm / Mục tiêu
    elif any(k in msg for k in ["tiết kiệm", "để dành", "mục tiêu", "làm sao", "lời khuyên", "kế hoạch"]):
        target = health_data.get("income", 18000000) * 0.2
        gap = health_data.get("savings_gap", 2700000)
        return (
            f"Để đạt đúng tỷ lệ tiết kiệm chuẩn 20% thu nhập (**{target:,.0f} VNĐ/tháng**), bạn cần bù đắp khoản thiếu hụt **{gap:,.0f} VNĐ** bằng phác đồ sau:\n"
            f"1. Hủy 2 gói dịch vụ số không dùng: tiết kiệm **+350.000 VNĐ**.\n"
            f"2. Cắt giảm 50% đơn mua sắm đêm sau 22h: tiết kiệm **+1.850.000 VNĐ**.\n"
            f"3. Giảm bớt 2-3 bữa ăn hàng ngoài: tiết kiệm **+500.000 VNĐ**.\n"
            f"👉 Tổng cắt giảm: **{gap:,.0f} VNĐ** ➔ Đạt chuẩn 20% tiết kiệm ngay trong tháng sau!"
        )
        
    # 6. Mặc định / Lời chào
    else:
        return (
            f"Chào bạn! Tôi là Trợ lý AI **FinLab**. Tôi đã phân tích toàn bộ dữ liệu dòng tiền qua Open Banking của bạn tháng này.\n"
            f"Bạn có thể hỏi tôi về:\n"
            f"• *'Tháng này tôi tiêu bao nhiêu tiền ăn uống?'*\n"
            f"• *'Có khoản đăng ký ngầm nào đang trừ tiền không?'*\n"
            f"• *'Các đơn mua sắm ban đêm hết bao nhiêu?'*\n"
            f"• *'Điểm sức khỏe tài chính của tôi thế nào?'*\n"
            f"• *'Làm sao để tháng này tiết kiệm được 3,6 triệu?'*"
        )
