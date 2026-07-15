import imaplib
import email
from email.header import decode_header
import sys

# Connect to IMAP
try:
    imap = imaplib.IMAP4_SSL("mail001.enigma.htb")
    imap.login("kevin", "Enigma2024!")
    imap.select("INBOX")
    
    # Search all emails
    status, messages = imap.search(None, "ALL")
    email_ids = messages[0].split()
    
    print(f"Total emails: {len(email_ids)}")
    
    # Get the last 10 emails (most recent)
    for email_id in email_ids[-10:]:
        status, msg_data = imap.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
                from_ = decode_header(msg.get("From"))[0][0]
                if isinstance(from_, bytes):
                    from_ = from_.decode('utf-8', errors='ignore')
                print(f"\nFrom: {from_}")
                print(f"Subject: {subject}")
                
                # Get the body
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            print(f"Body preview: {body[:200]}...")
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    print(f"Body preview: {body[:200]}...")
    
    imap.close()
    imap.logout()
    
except Exception as e:
    print(f"Error: {e}")
