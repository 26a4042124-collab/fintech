import math
from datetime import datetime

def compute_financial_health(
    enriched_transactions, 
    total_income=18000000, 
    target_ratio=None, 
    category_budgets=None, 
    round_up_config=None,
    savings_goals=None
):
    """
    Thuật toán nâng cao tính toán Sức khỏe tài chính, Phân bổ ngân sách linh hoạt,
    Dự báo dòng tiền cuối tháng, Quản lý hạn mức danh mục & Làm tròn tiền lẻ Micro-investing.
    """
    if target_ratio is None:
        target_ratio = {"needs": 50, "wants": 30, "savings": 20}
    
    bench_needs = target_ratio.get("needs", 50)
    bench_wants = target_ratio.get("wants", 30)
    bench_savings = target_ratio.get("savings", 20)

    if round_up_config is None:
        round_up_config = {"enabled": True, "step": 10000, "accumulated_total": 0}
        
    round_up_step = round_up_config.get("step", 10000)
    if round_up_step not in [10000, 50000]:
        round_up_step = 10000

    total_needs = 0
    total_wants = 0
    total_savings = 0
    total_expense = 0
    
    subscription_items = []
    night_impulse_items = []
    category_breakdown = {}
    
    # Biến tính toán làm tròn tiền lẻ Micro-investing
    round_up_txns_count = 0
    monthly_round_up_total = 0
    round_up_history = []
    
    # Theo dõi ngày giao dịch để tính Burn Rate dòng tiền
    txn_days = []
    
    for t in enriched_transactions:
        ts_str = t.get("timestamp", "")
        if len(ts_str) >= 10:
            try:
                txn_days.append(int(ts_str[8:10]))
            except Exception:
                pass
                
        if t.get("type") == "OUTFLOW":
            amt = t.get("amount", 0)
            total_expense += amt
            bucket = t.get("ai_bucket")
            cat = t.get("ai_category", "Khác")
            
            # Gom theo rổ ngân sách
            if bucket == "NEEDS":
                total_needs += amt
            elif bucket == "WANTS":
                total_wants += amt
            elif bucket == "SAVINGS":
                total_savings += amt
                
            # Phân bổ chi tiết danh mục
            category_breakdown[cat] = category_breakdown.get(cat, 0) + amt
            
            # Quét Subscription Leaks
            if t.get("is_subscription"):
                subscription_items.append({
                    "id": t.get("id"),
                    "name": cat,
                    "merchant": t.get("description"),
                    "amount": amt,
                    "bank": t.get("bank"),
                    "timestamp": t.get("timestamp")
                })
                
            # Quét Impulse Spending ban đêm
            if t.get("is_night_spending"):
                night_impulse_items.append({
                    "id": t.get("id"),
                    "merchant": t.get("description"),
                    "amount": amt,
                    "timestamp": t.get("timestamp"),
                    "category": cat
                })
                
            # Tính toán Micro-investing Làm tròn tiền lẻ
            rem = amt % round_up_step
            if rem > 0:
                ru_val = round_up_step - rem
                round_up_txns_count += 1
                monthly_round_up_total += ru_val
                if len(round_up_history) < 5:
                    round_up_history.append({
                        "txn_id": t.get("id"),
                        "merchant": t.get("description"),
                        "amount": amt,
                        "rounded_amount": amt + ru_val,
                        "spare_change": ru_val
                    })

    # Thu nhập chuẩn
    income_val = total_income if total_income > 0 else 18000000
    
    # Tính tỷ lệ phần trăm thực tế so với thu nhập
    pct_needs = round((total_needs / income_val) * 100, 1)
    pct_wants = round((total_wants / income_val) * 100, 1)
    pct_savings = round((total_savings / income_val) * 100, 1)
    
    # Thuật toán chấm điểm sức khỏe tài chính dựa trên tỷ lệ tùy chọn người dùng đã cấu hình
    score = 100
    if pct_needs > bench_needs:
        score -= (pct_needs - bench_needs) * 1.5
    if pct_wants > bench_wants:
        score -= (pct_wants - bench_wants) * 2.0  # Phạt việc tiêu quá đà cho Wants
    if pct_savings < bench_savings:
        score -= (bench_savings - pct_savings) * 2.5 # Phạt việc thiếu hụt quỹ tiết kiệm
        
    score = max(10, min(100, int(round(score))))
    
    # Phân loại mức độ cảnh báo
    if score >= 80:
        status_label = "Khỏe mạnh (Tốt)"
        status_color = "success"
    elif score >= 50:
        status_label = "Cảnh báo (Cần tối ưu)"
        status_color = "warning"
    else:
        status_label = "Báo động (Thâm hụt rủi ro)"
        status_color = "danger"
        
    total_sub_leak = sum(item["amount"] for item in subscription_items)
    total_night_impulse = sum(item["amount"] for item in night_impulse_items)
    
    target_savings = int(income_val * (bench_savings / 100.0))
    savings_gap = max(0, target_savings - total_savings)
    
    # ======================================================================
    # TÍNH NĂNG 4: THUẬT TOÁN DỰ BÁO DÒNG TIỀN CUỐI THÁNG (CASHFLOW FORECAST)
    # ======================================================================
    current_day = max(txn_days) if txn_days else 25
    current_day = max(1, min(30, current_day))
    
    daily_burn_rate = round(total_expense / current_day, 0)
    projected_expense = int(daily_burn_rate * 30)
    projected_net = income_val - projected_expense
    is_deficit_risk = projected_expense > income_val
    
    if is_deficit_risk:
        deficit_amount = projected_expense - income_val
        day_broke = min(30, max(1, int(income_val / daily_burn_rate))) if daily_burn_rate > 0 else 30
        forecast_status = "BÁO ĐỘNG NGUY CƠ CẠN VÍ"
        forecast_color = "danger"
        forecast_message = (
            f"Với tốc độ chi tiêu {daily_burn_rate:,.0f} đ/ngày, dự kiến đến ngày {day_broke} bạn sẽ "
            f"dùng hết số dư và thâm hụt {deficit_amount:,.0f} VNĐ vào cuối tháng!"
        )
    else:
        surplus_amount = income_val - projected_expense
        day_broke = None
        deficit_amount = 0
        forecast_status = "THẶNG DƯ AN TOÀN"
        forecast_color = "success"
        forecast_message = (
            f"Với tốc độ chi tiêu {daily_burn_rate:,.0f} đ/ngày, dự phóng cuối tháng bạn sẽ còn "
            f"thặng dư an toàn {surplus_amount:,.0f} VNĐ để chuyển vào Quỹ tích lũy."
        )

    cashflow_forecast = {
        "current_day": current_day,
        "daily_burn_rate": daily_burn_rate,
        "projected_expense": projected_expense,
        "projected_net": projected_net,
        "is_deficit_risk": is_deficit_risk,
        "deficit_amount": deficit_amount if is_deficit_risk else 0,
        "surplus_amount": surplus_amount if not is_deficit_risk else 0,
        "day_broke": day_broke,
        "forecast_status": forecast_status,
        "forecast_color": forecast_color,
        "forecast_message": forecast_message
    }

    # ======================================================================
    # TÍNH NĂNG 5: HẠN MỨC CHI TIÊU & CẢNH BÁO THEO DANH MỤC
    # ======================================================================
    if not category_budgets:
        category_budgets = {
            "Ăn uống & Cà phê ngoài": 3500000,
            "Mua sắm cá nhân": 1500000,
            "Nhà ở & Hóa đơn tiện ích": 5000000,
            "Thực phẩm & Đi chợ": 4000000,
            "Đi lại & Xăng xe": 1000000,
            "Giải trí & Phim ảnh": 800000
        }
        
    budget_alerts = []
    category_status_summary = {"safe": 0, "warning": 0, "danger": 0}
    
    for cat_name, limit_amt in category_budgets.items():
        spent = category_breakdown.get(cat_name, 0)
        pct = round((spent / limit_amt) * 100, 1) if limit_amt > 0 else 0
        
        if pct >= 100:
            status = "danger"
            label = "Vượt ngân sách!"
            tag_class = "badge-danger"
            category_status_summary["danger"] += 1
        elif pct >= 80:
            status = "warning"
            label = "Sắp chạm trần (80%-99%)"
            tag_class = "badge-warning"
            category_status_summary["warning"] += 1
        else:
            status = "safe"
            label = "Trong hạn mức"
            tag_class = "badge-success"
            category_status_summary["safe"] += 1
            
        budget_alerts.append({
            "category": cat_name,
            "limit": limit_amt,
            "spent": spent,
            "percentage": pct,
            "status": status,
            "label": label,
            "tag_class": tag_class,
            "remaining": max(0, limit_amt - spent),
            "overspent": max(0, spent - limit_amt)
        })

    # Sắp xếp danh mục cảnh báo: danger lên đầu, sau đó warning, rồi safe
    budget_alerts.sort(key=lambda x: (0 if x["status"] == "danger" else (1 if x["status"] == "warning" else 2), -x["percentage"]))

    # ======================================================================
    # TÍNH NĂNG 2: MỤC TIÊU TÀI CHÍNH (SAVINGS GOALS FORECAST)
    # ======================================================================
    processed_goals = []
    # Tốc độ tích lũy thực tế: nếu total_savings có thì lấy, hoặc ước tính từ target_savings
    monthly_savings_speed = total_savings if total_savings >= 500000 else max(1000000, int(target_savings * 0.75))
    
    if savings_goals:
        for g in savings_goals:
            tgt = g.get("target_amount", 1)
            cur = g.get("current_amount", 0)
            pct = min(100, round((cur / tgt) * 100, 1)) if tgt > 0 else 0
            rem = max(0, tgt - cur)
            
            if rem == 0:
                months_needed = 0
                ai_forecast = "🎉 Mục tiêu này đã hoàn thành 100%! Bạn có thể thiết lập thêm mục tiêu mới."
            elif monthly_savings_speed > 0:
                months_needed = round(rem / monthly_savings_speed, 1)
                months_int = math.ceil(rem / monthly_savings_speed)
                ai_forecast = (
                    f"Với tốc độ tích lũy hiện tại ({monthly_savings_speed:,.0f} đ/tháng), "
                    f"bạn sẽ hoàn thành mục tiêu này sau khoảng {months_needed} tháng nữa (dự kiến ~{months_int} tháng)."
                )
            else:
                months_needed = 99
                ai_forecast = "Chưa có dòng tiền tích lũy đều đặn. Hãy kích hoạt Heo đất hoặc cắt giảm Wants để tạo quỹ!"
                
            processed_goals.append({
                **g,
                "percentage": pct,
                "remaining_amount": rem,
                "months_needed": months_needed,
                "ai_forecast": ai_forecast
            })

    # ======================================================================
    # TÍNH NĂNG 3: HEODAT ROUND-UP STATS
    # ======================================================================
    round_up_stats = {
        "enabled": round_up_config.get("enabled", True),
        "step": round_up_step,
        "transactions_count": round_up_txns_count,
        "monthly_round_up_total": monthly_round_up_total,
        "accumulated_total": round_up_config.get("accumulated_total", 0),
        "target_goal_id": round_up_config.get("target_goal_id"),
        "recent_rounds": round_up_history
    }

    # ======================================================================
    # PHÁC ĐỒ HÀNH ĐỘNG DỰA TRÊN TỶ LỆ TÙY CHỌN & CÁC CẢNH BÁO MỚI
    # ======================================================================
    recommendations = [
        f"Mục tiêu tiết kiệm tùy chọn {bench_savings}% thu nhập: {target_savings:,.0f} VNĐ. "
        f"Thực tế bạn để dành được {total_savings:,.0f} VNĐ ({pct_savings}%). Bạn đang thiếu hụt {savings_gap:,.0f} VNĐ.",
        
        f"Cảnh báo tốc độ đốt tiền: Trung bình {daily_burn_rate:,.0f} VNĐ/ngày. "
        f"{'Cần cắt giảm chi tiêu ngay để tránh cạn ví vào cuối tháng!' if is_deficit_risk else 'Dòng tiền duy trì ổn định, tiếp tục giữ vững phong độ!'}",
        
        f"Phát hiện {len(subscription_items)} khoản dịch vụ số định kỳ trừ ngầm {total_sub_leak:,.0f} VNĐ/tháng "
        f"(Netflix, Spotify, iCloud...). Khuyến nghị hủy các gói ít sử dụng để tiết kiệm ngay ~350.000 VNĐ.",
        
        f"Ghi nhận {len(night_impulse_items)} đơn mua sắm đêm sau 22h00 tổng cộng {total_night_impulse:,.0f} VNĐ. "
        f"Khuyến nghị áp dụng quy tắc 'chờ 24 giờ' để tiết kiệm thêm ~1.850.000 VNĐ.",
        
        f"Đã gom được {monthly_round_up_total:,.0f} VNĐ tiền lẻ làm tròn từ {round_up_txns_count} giao dịch. "
        f"Bạn có thể chuyển ngay vào hũ Mục tiêu tài chính để kích hoạt lãi kép micro-investing!"
    ]

    return {
        "income": income_val,
        "total_expense": total_expense,
        "net_remaining": income_val - total_expense,
        "target_ratio": {
            "needs": bench_needs,
            "wants": bench_wants,
            "savings": bench_savings
        },
        "needs": {
            "amount": total_needs,
            "percentage": pct_needs,
            "benchmark_pct": bench_needs
        },
        "wants": {
            "amount": total_wants,
            "percentage": pct_wants,
            "benchmark_pct": bench_wants
        },
        "savings": {
            "amount": total_savings,
            "percentage": pct_savings,
            "benchmark_pct": bench_savings
        },
        "health_score": score,
        "health_status": status_label,
        "health_color": status_color,
        "subscription_leaks": {
            "count": len(subscription_items),
            "total_amount": total_sub_leak,
            "list": subscription_items
        },
        "impulse_night_spending": {
            "count": len(night_impulse_items),
            "total_amount": total_night_impulse,
            "list": night_impulse_items
        },
        "category_breakdown": category_breakdown,
        "cashflow_forecast": cashflow_forecast,
        "category_budgets": budget_alerts,
        "category_status_summary": category_status_summary,
        "savings_goals": processed_goals,
        "round_up": round_up_stats,
        "recommendations": recommendations,
        "savings_gap": savings_gap
    }
