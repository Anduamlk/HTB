import imaplib
import email
from email.header import decode_header

imap = imaplib.IMAP4_SSL("mail001.enigma.htb")
imap.login("sarah", "Enigma2024!")
imap.select("INBOX")

status, messages = imap.search(None, "ALL")
email_ids = messages[0].split()

print(f"Total emails: {len(email_ids)}")

for email_id in email_ids:
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
            
            # Get the full body
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        print(f"\nBody:\n{body}")
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                print(f"\nBody:\n{body}")

imap.close()
imap.logout()
