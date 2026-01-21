import os
import base64
from email.message import EmailMessage
from flask import Flask, request, redirect, session, jsonify, render_template_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pymongo import MongoClient
from datetime import datetime
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = 'change-this-to-random-string-in-production'

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://pythonProd:pythonfindiy25@findiy-main.t5gfeq.mongodb.net/Findiy_Production_Python?retryWrites=true&w=majority&appName=Findiy-main"
DB_NAME = "Findiy_Production_Python"
COLLECTION_NAME = "gmail_test"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Encryption key (IMPORTANT: Store this securely, not in code!)
# For production, use environment variable or secret management
ENCRYPTION_KEY = Fernet.generate_key()  # Generate once and save it!
cipher = Fernet(ENCRYPTION_KEY)

# OAuth Configuration
CLIENT_SECRETS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
REDIRECT_URI = 'http://localhost:5000/oauth2callback'


def encrypt_token(token):
    """Encrypt sensitive token data"""
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token):
    """Decrypt token data"""
    return cipher.decrypt(encrypted_token.encode()).decode()


def save_credentials_to_db(user_email, credentials):
    """Save user credentials to MongoDB"""
    creds_data = {
        'user_email': user_email,
        'token': encrypt_token(credentials.token),
        'refresh_token': encrypt_token(credentials.refresh_token) if credentials.refresh_token else None,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': encrypt_token(credentials.client_secret),
        'scopes': credentials.scopes,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    # Update or insert
    collection.update_one(
        {'user_email': user_email},
        {'$set': creds_data},
        upsert=True
    )
    print(f"✅ Credentials saved for {user_email}")


def get_credentials_from_db(user_email):
    """Retrieve user credentials from MongoDB"""
    doc = collection.find_one({'user_email': user_email})
    
    if not doc:
        return None
    
    # Decrypt sensitive fields
    token = decrypt_token(doc['token'])
    refresh_token = decrypt_token(doc['refresh_token']) if doc.get('refresh_token') else None
    client_secret = decrypt_token(doc['client_secret'])
    
    credentials = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=doc['token_uri'],
        client_id=doc['client_id'],
        client_secret=client_secret,
        scopes=doc['scopes']
    )
    
    return credentials


def get_gmail_service(user_email):
    """Get Gmail service with stored credentials"""
    creds = get_credentials_from_db(user_email)
    
    if not creds:
        return None
    
    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update the refreshed token in database
        save_credentials_to_db(user_email, creds)
    
    return build('gmail', 'v1', credentials=creds)


def get_user_email_from_google(credentials):
    """Get user's email address from Google"""
    service = build('gmail', 'v1', credentials=credentials)
    profile = service.users().getProfile(userId='me').execute()
    return profile['emailAddress']


def get_email_body(message):
    """Extract email body from message payload"""
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode()
            elif part['mimeType'] == 'text/html':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode()
    elif 'body' in message['payload'] and 'data' in message['payload']['body']:
        return base64.urlsafe_b64decode(message['payload']['body']['data']).decode()
    return "No body content"


@app.route('/')
def index():
    user_email = session.get('user_email')
    
    if user_email:
        return f'''
            <h1>Gmail OAuth Platform</h1>
            <p>✅ Connected as: <strong>{user_email}</strong></p>
            <a href="/compose-email"><button>Compose New Email</button></a>
            <br><br>
            <a href="/read-emails"><button>Read Latest Emails</button></a>
            <br><br>
            <a href="/logout"><button>Logout</button></a>
        '''
    else:
        return '''
            <h1>Gmail OAuth Platform</h1>
            <p>Connect your Gmail account to get started:</p>
            <a href="/authorize"><button>Connect Gmail</button></a>
        '''


@app.route('/authorize')
def authorize():
    """Step 1: Redirect user to Google's OAuth page"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    """Step 2: Handle the callback from Google"""
    state = session['state']
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    # Get user's email address
    user_email = get_user_email_from_google(credentials)
    
    # Save credentials to MongoDB
    save_credentials_to_db(user_email, credentials)
    
    # Store user email in session
    session['user_email'] = user_email
    
    return f'''
        <h1>✅ Gmail Connected Successfully!</h1>
        <p>Your Gmail account <strong>{user_email}</strong> is now connected.</p>
        <a href="/"><button>Go to Dashboard</button></a>
    '''


@app.route('/compose-email')
def compose_email():
    """Show email composition form"""
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect('/authorize')
    
    return '''
        <h1>✉️ Compose New Email</h1>
        <form action="/send-email" method="POST">
            <label for="to">To:</label><br>
            <input type="email" id="to" name="to" required style="width: 400px; padding: 5px;"><br><br>
            
            <label for="subject">Subject:</label><br>
            <input type="text" id="subject" name="subject" required style="width: 400px; padding: 5px;"><br><br>
            
            <label for="body">Body:</label><br>
            <textarea id="body" name="body" required rows="10" style="width: 400px; padding: 5px;"></textarea><br><br>
            
            <button type="submit">Send Email</button>
            <a href="/"><button type="button">Cancel</button></a>
        </form>
    '''


@app.route('/send-email', methods=['POST'])
def send_email():
    """Send custom email"""
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect('/authorize')
    
    service = get_gmail_service(user_email)
    
    if not service:
        return redirect('/authorize')
    
    try:
        to = request.form.get('to')
        subject = request.form.get('subject')
        body = request.form.get('body')
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_message = {'raw': encoded_message}
        
        result = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        return f'''
            <h1>✅ Email Sent Successfully!</h1>
            <p><b>To:</b> {to}</p>
            <p><b>Subject:</b> {subject}</p>
            <p><b>Thread ID:</b> {result['threadId']}</p>
            <p><b>Message ID:</b> {result['id']}</p>
            <br>
            <a href="/compose-email"><button>Send Another Email</button></a>
            <a href="/"><button>Back to Dashboard</button></a>
        '''
    
    except Exception as e:
        return f'''
            <h1>❌ Error Sending Email</h1>
            <p>{str(e)}</p>
            <a href="/compose-email"><button>Try Again</button></a>
            <a href="/"><button>Back to Dashboard</button></a>
        '''


@app.route('/read-emails')
def read_emails():
    """Read latest 10 full emails"""
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect('/authorize')
    
    service = get_gmail_service(user_email)
    
    if not service:
        return redirect('/authorize')
    
    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return '<h1>No emails found</h1><a href="/"><button>Back</button></a>'
        
        emails_html = f'''
            <h1>📬 Latest 10 Emails for {user_email}</h1>
            <style>
                .email-card {{
                    border: 1px solid #ddd;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .email-header {{ font-weight: bold; color: #333; }}
                .email-body {{
                    margin-top: 10px;
                    padding: 10px;
                    background-color: white;
                    border-left: 3px solid #4CAF50;
                    white-space: pre-wrap;
                    max-height: 300px;
                    overflow-y: auto;
                }}
            </style>
        '''
        
        for idx, msg in enumerate(messages, 1):
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = sender = date = ''
            
            for h in headers:
                if h['name'] == 'Subject':
                    subject = h['value']
                if h['name'] == 'From':
                    sender = h['value']
                if h['name'] == 'Date':
                    date = h['value']
            
            # Get email body
            body = get_email_body(message)
            
            emails_html += f'''
                <div class="email-card">
                    <div class="email-header">Email #{idx}</div>
                    <p><b>From:</b> {sender}</p>
                    <p><b>Subject:</b> {subject}</p>
                    <p><b>Date:</b> {date}</p>
                    <div class="email-body">
                        <b>Body:</b><br>
                        {body[:1000]}{"..." if len(body) > 1000 else ""}
                    </div>
                    <br>
                    <a href="/read-thread/{message['threadId']}"><button>View Full Thread</button></a>
                </div>
            '''
        
        emails_html += '<br><a href="/"><button>Back to Dashboard</button></a>'
        return emails_html
    
    except Exception as e:
        return f'<h1>❌ Error:</h1><p>{str(e)}</p><a href="/"><button>Back</button></a>'


@app.route('/read-thread/<thread_id>')
def read_thread(thread_id):
    """Read all messages in a thread with full content"""
    user_email = session.get('user_email')
    
    if not user_email:
        return redirect('/authorize')
    
    service = get_gmail_service(user_email)
    
    if not service:
        return redirect('/authorize')
    
    try:
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='full'
        ).execute()
        
        thread_html = f'''
            <h1>🔁 Email Thread ({len(thread["messages"])} messages)</h1>
            <style>
                .thread-message {{
                    border: 1px solid #ddd;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .message-header {{ font-weight: bold; color: #333; }}
                .message-body {{
                    margin-top: 10px;
                    padding: 10px;
                    background-color: white;
                    border-left: 3px solid #2196F3;
                    white-space: pre-wrap;
                }}
            </style>
        '''
        
        for idx, message in enumerate(thread['messages'], 1):
            headers = message['payload']['headers']
            subject = sender = date = ''
            
            for h in headers:
                if h['name'] == 'Subject':
                    subject = h['value']
                if h['name'] == 'From':
                    sender = h['value']
                if h['name'] == 'Date':
                    date = h['value']
            
            # Get email body
            body = get_email_body(message)
            
            thread_html += f'''
                <div class="thread-message">
                    <div class="message-header">Message {idx}</div>
                    <p><b>From:</b> {sender}</p>
                    <p><b>Subject:</b> {subject}</p>
                    <p><b>Date:</b> {date}</p>
                    <div class="message-body">
                        <b>Content:</b><br>
                        {body}
                    </div>
                </div>
            '''
        
        thread_html += '<br><a href="/read-emails"><button>Back to Emails</button></a> '
        thread_html += '<a href="/"><button>Back to Dashboard</button></a>'
        return thread_html
    
    except Exception as e:
        return f'<h1>❌ Error:</h1><p>{str(e)}</p><a href="/"><button>Back</button></a>'


@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user_email', None)
    return redirect('/')


@app.route('/list-connected-users')
def list_connected_users():
    """Admin: List all connected Gmail accounts"""
    users = collection.find({}, {'user_email': 1, 'created_at': 1, '_id': 0})
    
    users_html = '<h1>📋 Connected Gmail Accounts</h1><ul>'
    
    for user in users:
        users_html += f'''
            <li>{user['user_email']} - Connected on {user.get('created_at', 'Unknown')}</li>
        '''
    
    users_html += '</ul><a href="/"><button>Back to Dashboard</button></a>'
    return users_html


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for local development
    
    print("\n" + "="*50)
    print("🔐 IMPORTANT: Save this encryption key!")
    print("="*50)
    print(f"ENCRYPTION_KEY = {ENCRYPTION_KEY.decode()}")
    print("="*50)
    print("⚠️  Store this in environment variable for production!")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000)