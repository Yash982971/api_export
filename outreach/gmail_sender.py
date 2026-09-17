import smtplib
import os
import csv
import mimetypes
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders

import config
from processing.duplicate_checker import is_already_contacted
from processing.validator import validate_email
from outreach.google_sheets_tracker import track_sent_email_to_sheets

def send_email(recipient_email, company_name, subject, body_text, attachment_path=None, poster_image_path=None, buyer_website=""):
    """
    Sends outreach email via Gmail SMTP with:
    1. Short B2B description text with recipient personalization.
    2. Embedded product poster image (assets/product_poster.jpg) displayed directly INSIDE the email body via CID.
    3. Original PPT file (assets/singing_bowl_product.pptx) attached as a downloadable file at the bottom.
    """
    if not recipient_email:
        return False, "Recipient email is missing."
        
    # Validate recipient email format
    is_valid, status_msg = validate_email(recipient_email)
    if not is_valid:
        return False, f"Invalid email format ({recipient_email}): {status_msg}"
        
    # Check if already contacted in sent_log.csv
    if is_already_contacted(recipient_email):
        log_campaign_event(recipient_email, company_name, subject, "Skipped", "Already contacted previously")
        return False, "Skipped: Email was already contacted previously."
        
    sender_email = config.GMAIL_EMAIL
    app_password = config.GMAIL_APP_PASSWORD
    
    if not sender_email or not app_password:
        log_campaign_event(recipient_email, company_name, subject, "Failed", "Gmail credentials not configured in .env")
        return False, "Gmail credentials (GMAIL_EMAIL, GMAIL_APP_PASSWORD) are missing in .env."
        
    # Resolve poster image path (assets/product_poster.jpg)
    if not poster_image_path:
        poster_image_path = os.path.join(config.BASE_DIR, 'assets', 'product_poster.jpg')
        
    # Resolve PPT/PDF attachment path (assets/singing_bowl_product.pdf)
    if not attachment_path:
        attachment_path = os.path.join(config.BASE_DIR, 'assets', 'singing_bowl_product.pdf')
        if not os.path.exists(attachment_path):
            attachment_path = config.get_attachment_path()

    try:
        # Outer message is MIMEMultipart('mixed') for body + attachments
        msg = MIMEMultipart('mixed')
        msg['From'] = f"OM Enterprise <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Inner message is MIMEMultipart('related') for HTML body + inline CID poster image
        msg_related = MIMEMultipart('related')
        
        # Convert plain text newlines to HTML <br> tags
        body_html_formatted = body_text.replace('\n', '<br>')
        
        # HTML template embedding poster image via CID:product_poster directly inside email body
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; font-size: 14px; color: #222222; line-height: 1.6;">
            <div>
              {body_html_formatted}
            </div>
            <br>
            <div style="margin-top: 15px; margin-bottom: 20px; text-align: left;">
              <img src="cid:product_poster" alt="OM Enterprise Singing Bowls Product Poster" style="max-width: 100%; height: auto; border: 1px solid #cccccc; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            </div>
          </body>
        </html>
        """
        
        # 1. Attach HTML body
        msg_related.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # 2. Attach inline poster image (assets/product_poster.jpg)
        if os.path.exists(poster_image_path):
            with open(poster_image_path, 'rb') as f:
                img_data = f.read()
            img_part = MIMEImage(img_data, _subtype='jpeg')
            img_part.add_header('Content-ID', '<product_poster>')
            img_part.add_header('Content-Disposition', 'inline', filename='product_poster.jpg')
            msg_related.attach(img_part)
            
        msg.attach(msg_related)

        # 3. Attach original PPT file (singing_bowl_product.pptx) directly as downloadable attachment
        if os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            content_type, _ = mimetypes.guess_type(attachment_path)
            if not content_type:
                content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                
            main_type, sub_type = content_type.split('/', 1)
            
            with open(attachment_path, "rb") as f:
                pptx_bytes = f.read()
                
            attach_part = MIMEBase(main_type, sub_type)
            attach_part.set_payload(pptx_bytes)
            encoders.encode_base64(attach_part)
            attach_part.add_header('Content-Disposition', 'attachment', filename=filename)
            attach_part.add_header('Content-Type', content_type, name=filename)
            msg.attach(attach_part)
                
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        
        sent_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_campaign_event(recipient_email, company_name, subject, "Sent", f"Inline poster embedded + PPT attached: {os.path.basename(attachment_path)}")

        # ── Google Sheets tracking (non-blocking) ─────────────────────────────
        sheets_ok, sheets_msg = track_sent_email_to_sheets(
            email=recipient_email,
            company_name=company_name,
            website=buyer_website,
            sent_timestamp=sent_ts,
        )
        if sheets_ok:
            print(f"[GmailSender] Google Sheet updated: {sheets_msg}")
        else:
            print(f"[GmailSender] Google Sheet update FAILED (email still sent): {sheets_msg}")
        # ─────────────────────────────────────────────────────────────────────

        sheet_note = " | Sheet: Updated" if sheets_ok else " | Sheet: Failed (see logs)"
        return True, f"Email sent successfully with inline poster and {os.path.basename(attachment_path)} attached!{sheet_note}"
        
    except Exception as e:
        error_msg = str(e)
        print(f"[GmailSender] Error sending email to {recipient_email}: {error_msg}")
        log_campaign_event(recipient_email, company_name, subject, "Failed", f"SMTP Error: {error_msg}")
        return False, f"Failed to send email: {error_msg}"

def log_campaign_event(email, company_name, subject, status, notes=""):
    """
    Appends an entry to data/sent_log.csv.
    """
    os.makedirs(os.path.dirname(config.SENT_LOG_CSV_PATH), exist_ok=True)
    file_exists = os.path.exists(config.SENT_LOG_CSV_PATH)
    
    try:
        with open(config.SENT_LOG_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["email", "company_name", "subject", "sent_date", "status", "notes"])
            writer.writerow([
                email,
                company_name,
                subject,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status,
                notes
            ])
    except Exception as e:
        print(f"[GmailSender] Failed to write to sent_log.csv: {e}")
