import gspread
import time
import threading
import secrets
import string
import os
import smtplib
import mimetypes
import pymysql
import logging
from email.message import EmailMessage
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

def get_db_connection():
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor
        )
        logging.info("✅ Successfully connected to the MySQL database!")
        return conn
    except pymysql.err.OperationalError as e:
        logging.error(f"❌ Database Connection Failed: {e}")
        return None
    except pymysql.MySQLError as e:
        logging.error(f"❌ MySQL Error: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ Unexpected Error while connecting to DB: {e}")
        return None

# Set to keep track of already synced emails
synced_emails = set()

def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

def send_email_smtp(recipient_email, subject, html_content, images={}):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient_email
        msg.set_content("This email contains an HTML body. Please enable HTML viewing.")
        msg.add_alternative(html_content, subtype="html")

        for img_path, cid in images.items():
            try:
                with open(img_path, "rb") as img_file:
                    img_data = img_file.read()
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if mime_type:
                        maintype, subtype = mime_type.split("/")
                        msg.add_attachment(img_data, maintype=maintype, subtype=subtype,
                                           filename=os.path.basename(img_path), cid=cid)
            except Exception as img_error:
                logging.warning(f"⚠️ Warning: Failed to attach image {img_path} - {img_error}")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info(f"✅ Email successfully sent to {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error("❌ Authentication Error: Check your email and password in .env file.")
        return False

    except smtplib.SMTPException as smtp_error:
        logging.error(f"❌ SMTP Exception: {smtp_error}")
        return False

    except Exception as e:
        logging.error(f"❌ General Email Sending Error: {e}")
        return False

def send_credentials_email(to_email, name, username, password):
    subject = "🛡️ Your Admin Credentials for Waste Management System"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f7f7f7; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
          <h2 style="color: #2E8B57;">Welcome, {name}!</h2>
          <p>You have been successfully registered as an Admin in the <strong>Waste Management System</strong>.</p>
          <p>Here are your credentials:</p>
          <ul style="line-height: 1.6;">
            <li><strong>Username (Email):</strong> {username}</li>
            <li><strong>Password:</strong> {password}</li>
          </ul>
          <p style="margin-top: 20px;">Please keep this information safe and confidential.</p>
          <hr style="margin: 30px 0;">
          <p style="font-size: 13px; color: #999;">This is an automated email from the Waste Management System. Please do not reply.</p>
        </div>
      </body>
    </html>
    """
    send_email_smtp(to_email, subject, html_content)

def run_google_form_sync_loop(interval=1):
    def sync_loop():
        while True:
            try:
                scope = [
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                    "https://www.googleapis.com/auth/drive.readonly"
                ]
                creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_PATH, scope)
                client = gspread.authorize(creds)
                sheet = client.open("Admin Registration Responses").sheet1
                records = sheet.get_all_records()

                if not records:
                    print("⚠️ No records found in the Google Form.")
                    time.sleep(interval)
                    continue

                conn = get_db_connection()
                if not conn:
                    print("❌ Unable to connect to the database.")
                    time.sleep(interval)
                    continue

                cursor = conn.cursor()

                for i, row in enumerate(records, 1):
                    name = str(row.get("Name", "")).strip()
                    email = str(row.get("Email", "")).strip()
                    phone = str(row.get("Phone Number", "")).strip()
                    gender = str(row.get("Gender", "")).strip()
                    address = str(row.get("Address", "")).strip()
                    blood_group = str(row.get("Blood Group", "")).strip()


                    if not email:
                        continue

                    if email in synced_emails:
                        continue

                    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
                    if cursor.fetchone():
                        synced_emails.add(email)
                        continue

                    password = generate_password()

                    try:
                        cursor.execute("""
                            INSERT INTO admins (name, email, password, phone, gender, address, blood_group)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (name, email, password, phone, gender, address, blood_group))
                        conn.commit()

                        send_credentials_email(email, name, email, password)
                        synced_emails.add(email)
                        print(f"✅ Record {i} added & email sent to {email}")

                    except Exception as insert_error:
                        print(f"❌ Insert error for {email}: {insert_error}")

                cursor.close()
                conn.close()

            except Exception as e:
                print(f"❌ Sync loop error: {e}")

            time.sleep(interval)

    threading.Thread(target=sync_loop, daemon=True).start()
    print("🔁 Google Form background sync started...")

if __name__ == "__main__":
    run_google_form_sync_loop(interval=10)
    while True:
        time.sleep(10)  # Keep the main thread alive
