import imaplib
import email
from email.header import decode_header

# Connect to IMAP
imap = imaplib.IMAP4_SSL("mail001.enigma.htb")
imap.login("kevin", "Enigma2024!")
imap.select("INBOX")

# Search all emails
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
                subject = subject.decode()
            from_ = decode_header(msg.get("From"))[0][0]
            if isinstance(from_, bytes):
                from_ = from_.decode()
            print(f"From: {from_}, Subject: {subject}")

imap.close()
imap.logout()
