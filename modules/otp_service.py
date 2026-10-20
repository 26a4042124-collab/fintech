"""
FinLab — OTP Service
Gửi mã OTP 6 chữ số qua Gmail SMTP.
Cấu hình qua biến môi trường hoặc file .env:
  MAIL_SENDER   = your_gmail@gmail.com
  MAIL_PASSWORD = xxxx xxxx xxxx xxxx   (Gmail App Password)
"""

import os
import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load .env nếu có
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    load_dotenv(dotenv_path=os.path.abspath(_env_path), override=True)
except ImportError:
    pass

# Đọc từ env
MAIL_SENDER   = os.environ.get('MAIL_SENDER',   '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

# OTP hết hạn sau 5 phút (300 giây)
OTP_EXPIRE_SECONDS = 300


def generate_otp() -> str:
    """Sinh mã OTP 6 chữ số ngẫu nhiên."""
    return str(random.randint(100000, 999999))


def send_otp_email(to_email: str, otp: str) -> dict:
    """
    Gửi email OTP đến địa chỉ to_email.
    Trả về {'success': True} hoặc {'success': False, 'error': '...'}
    """
    # Đọc lại mỗi lần gọi để đảm bảo lấy đúng giá trị sau khi load_dotenv
    mail_sender   = os.environ.get('MAIL_SENDER',   '')
    mail_password = os.environ.get('MAIL_PASSWORD', '')

    if not mail_sender or not mail_password:
        return {
            'success': False,
            'error': 'Chưa cấu hình MAIL_SENDER / MAIL_PASSWORD trong biến môi trường.'
        }

    subject = f'[FinLab] Mã xác thực OTP của bạn: {otp}'

    html_body = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:0 auto;
                background:#0a0a0f;border-radius:20px;padding:32px;color:#ffffff;">
      <div style="text-align:center;margin-bottom:24px;">
        <span style="font-size:36px;">🪙</span>
        <h1 style="font-size:28px;font-weight:900;letter-spacing:-1px;margin:8px 0 0;
                   background:linear-gradient(135deg,#fff 40%,#FF6B35);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          finlab
        </h1>
      </div>

      <p style="color:rgba(255,255,255,0.65);font-size:15px;margin-bottom:24px;line-height:1.6;">
        Bạn vừa yêu cầu tạo tài khoản FinLab.<br>
        Dùng mã OTP dưới đây để xác thực:
      </p>

      <div style="background:linear-gradient(135deg,#1a0f08,#2d1200);
                  border:1px solid rgba(255,107,53,0.3);border-radius:16px;
                  padding:28px;text-align:center;margin-bottom:24px;">
        <div style="font-size:42px;font-weight:900;letter-spacing:10px;color:#FF6B35;">
          {otp}
        </div>
        <div style="font-size:13px;color:rgba(255,255,255,0.45);margin-top:10px;">
          Mã có hiệu lực trong <strong style="color:#FF6B35;">5 phút</strong>
        </div>
      </div>

      <p style="font-size:13px;color:rgba(255,255,255,0.35);line-height:1.6;">
        Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.<br>
        Không chia sẻ mã OTP với bất kỳ ai.
      </p>

      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:20px 0;">
      <p style="font-size:12px;color:rgba(255,255,255,0.25);text-align:center;">
        FinLab · Học viện Ngân hàng · Đồ án CNDVTC 2026
      </p>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f'FinLab <{mail_sender}>'
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(mail_sender, mail_password)
            server.sendmail(mail_sender, to_email, msg.as_bytes())
        return {'success': True}
    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'error': 'Xác thực Gmail thất bại. Kiểm tra lại App Password.'}
    except smtplib.SMTPException as e:
        return {'success': False, 'error': f'Lỗi SMTP: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Không thể gửi email: {str(e)}'}


def is_otp_expired(created_at: float) -> bool:
    """Kiểm tra OTP có hết hạn chưa."""
    return (time.time() - created_at) > OTP_EXPIRE_SECONDS


def verify_otp(session_otp: str, session_created_at: float, input_otp: str) -> dict:
    """
    Xác minh mã OTP người dùng nhập.
    Trả về {'valid': True} hoặc {'valid': False, 'reason': '...'}
    """
    if is_otp_expired(session_created_at):
        return {'valid': False, 'reason': 'Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới!'}
    if input_otp.strip() != session_otp:
        return {'valid': False, 'reason': 'Mã OTP không đúng. Vui lòng thử lại!'}
    return {'valid': True}
