import base64
import os.path
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# REQUIRED SCOPE
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def authenticate_gmail():
    creds = None

    # Load saved token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid creds, do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


# ---------------- SEND EMAIL ----------------
def send_email(service, to, subject, body):
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send_message = {
        'raw': encoded_message
    }

    sent = service.users().messages().send(
        userId='me',
        body=send_message
    ).execute()

    print("✅ Email sent")
    return sent['threadId']


# ---------------- READ EMAILS ----------------
def read_latest_emails(service, max_results=5):
    results = service.users().messages().list(
        userId='me',
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])

    if not messages:
        print("No emails found.")
        return

    for msg in messages:
        message = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata'
        ).execute()

        headers = message['payload']['headers']
        subject = sender = None

        for h in headers:
            if h['name'] == 'Subject':
                subject = h['value']
            if h['name'] == 'From':
                sender = h['value']

        print(f"\n📩 From: {sender}")
        print(f"📌 Subject: {subject}")


# ---------------- READ REPLIES (THREAD) ----------------
def read_thread(service, thread_id):
    thread = service.users().threads().get(
        userId='me',
        id=thread_id
    ).execute()

    print("\n🔁 Thread replies:\n")

    for message in thread['messages']:
        headers = message['payload']['headers']
        for h in headers:
            if h['name'] == 'From':
                print("From:", h['value'])
            if h['name'] == 'Subject':
                print("Subject:", h['value'])


# ---------------- MAIN ----------------
if __name__ == "__main__":
    service = authenticate_gmail()

    # 1️⃣ Send email
    thread_id = send_email(
        service,
        to="someone@example.com",
        subject="Hello from Gmail Agent",
        body="This email was sent programmatically on your behalf."
    )

    # 2️⃣ Read latest inbox emails
    read_latest_emails(service)

    # 3️⃣ Read replies to sent email
    read_thread(service, thread_id)
