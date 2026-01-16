import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this!

# SCOPES
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# OAuth 2.0 credentials from Google Cloud Console
CLIENT_SECRETS_FILE = 'credentials.json'
REDIRECT_URI = 'http://localhost:5000/oauth2callback'  # Must match Google Console


# ---------------- STEP 1: INITIATE OAUTH ----------------
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Get refresh token
        include_granted_scopes='true',
        prompt='consent'  # Force consent to get refresh token
    )
    
    session['state'] = state
    return redirect(authorization_url)


# ---------------- STEP 2: HANDLE CALLBACK ----------------
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    # 🔐 STORE THESE IN YOUR DATABASE (per user)
    user_id = session.get('user_id')  # Your platform's user ID
    
    save_credentials_to_db(user_id, {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    })
    
    return "✅ Gmail connected successfully!"


# ---------------- DATABASE HELPERS ----------------
def save_credentials_to_db(user_id, creds_dict):
    """
    Save to your database (PostgreSQL, MySQL, MongoDB, etc.)
    Store refresh_token ENCRYPTED!
    """
    # Example pseudo-code:
    # db.users.update(
    #     {'id': user_id},
    #     {'gmail_credentials': encrypt(creds_dict)}
    # )
    pass


def get_credentials_from_db(user_id):
    """
    Retrieve user's Gmail credentials from database
    """
    # Example pseudo-code:
    # creds_dict = decrypt(db.users.find_one({'id': user_id})['gmail_credentials'])
    # return creds_dict
    pass


# ---------------- BUILD SERVICE FOR USER ----------------
def get_gmail_service(user_id):
    creds_dict = get_credentials_from_db(user_id)
    
    creds = Credentials(
        token=creds_dict['token'],
        refresh_token=creds_dict['refresh_token'],
        token_uri=creds_dict['token_uri'],
        client_id=creds_dict['client_id'],
        client_secret=creds_dict['client_secret'],
        scopes=creds_dict['scopes']
    )
    
    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update token in database
        save_credentials_to_db(user_id, {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        })
    
    return build('gmail', 'v1', credentials=creds)


# ---------------- SEND EMAIL (YOUR EXISTING FUNCTION) ----------------
def send_email(service, to, subject, body):
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send_message = {'raw': encoded_message}

    sent = service.users().messages().send(
        userId='me',
        body=send_message
    ).execute()

    print("✅ Email sent")
    return sent['threadId']


# ---------------- READ THREAD (YOUR EXISTING FUNCTION) ----------------
def read_thread(service, thread_id):
    thread = service.users().threads().get(
        userId='me',
        id=thread_id
    ).execute()

    replies = []
    for message in thread['messages']:
        headers = message['payload']['headers']
        email_data = {}
        for h in headers:
            if h['name'] == 'From':
                email_data['from'] = h['value']
            if h['name'] == 'Subject':
                email_data['subject'] = h['value']
        replies.append(email_data)
    
    return replies


# ---------------- EXAMPLE: SEND EMAIL ON BEHALF OF USER ----------------
@app.route('/send-campaign')
def send_campaign():
    user_id = session.get('user_id')  # Your logged-in user
    
    service = get_gmail_service(user_id)
    
    thread_id = send_email(
        service,
        to="customer@example.com",
        subject="Hello from our platform",
        body="This email was sent via our platform using your Gmail."
    )
    
    return f"✅ Email sent! Thread ID: {thread_id}"


# ---------------- EXAMPLE: READ REPLIES ----------------
@app.route('/check-replies/<thread_id>')
def check_replies(thread_id):
    user_id = session.get('user_id')
    
    service = get_gmail_service(user_id)
    replies = read_thread(service, thread_id)
    
    return {"replies": replies}


if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for development!
    app.run(debug=True, port=5000)