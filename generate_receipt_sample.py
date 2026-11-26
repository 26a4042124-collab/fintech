"""
Script tạo ảnh hóa đơn mẫu để test OCR scanner
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_receipt_sample():
    """Tạo ảnh hóa đơn mẫu bằng Pillow"""
    
    # Kích thước giống hóa đơn thật
    width, height = 400, 600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Font (dùng font mặc định nếu không có font tiếng Việt)
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 30
    
    # Header - Tên cửa hàng
    store_name = "HIGHLANDS COFFEE"
    bbox = draw.textbbox((0, 0), store_name, font=font_large)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), store_name, fill='black', font=font_large)
    y += 40
    
    # Địa chỉ
    addr = "123 Nguyen Hue, Q1, TP.HCM"
    bbox = draw.textbbox((0, 0), addr, font=font_small)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), addr, fill='gray', font=font_small)
    y += 30
    
    # Ngày giờ
    date_str = "15/01/2024  10:30 AM"
    draw.text((20, y), date_str, fill='black', font=font_small)
    y += 40
    
    # Đường kẻ
    draw.line([(20, y), (width-20, y)], fill='gray', width=1)
    y += 20
    
    # Items
    items = [
        ("Ca phe sua da", "1", "35.000"),
        ("Banh mi que", "2", "15.000"),
        ("Tra dao", "1", "45.000"),
    ]
    
    for name, qty, price in items:
        # Tên món
        draw.text((20, y), name, fill='black', font=font_medium)
        y += 25
        
        # Số lượng và giá
        qty_price = f"{qty} x {price}"
        draw.text((40, y), qty_price, fill='gray', font=font_small)
        y += 30
    
    # Đường kẻ
    y += 10
    draw.line([(20, y), (width-20, y)], fill='gray', width=1)
    y += 20
    
    # Tổng cộng
    total_text = "TONG CONG:"
    total_amount = "110.000 VND"
    
    draw.text((20, y), total_text, fill='black', font=font_medium)
    
    bbox = draw.textbbox((0, 0), total_amount, font=font_large)
    x = width - 20 - (bbox[2] - bbox[0])
    draw.text((x, y), total_amount, fill='black', font=font_large)
    y += 50
    
    # Footer
    y += 30
    footer = "Cam on quy khach!"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), footer, fill='gray', font=font_small)
    
    # Lưu file
    output_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'receipt_sample.jpg')
    img.save(output_path, 'JPEG', quality=90)
    
    print(f"✓ Đã tạo ảnh hóa đơn mẫu: {output_path}")
    return output_path


if __name__ == '__main__':
    create_receipt_sample()
