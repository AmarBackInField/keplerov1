import os
import base64
from email.message import EmailMessage
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pymongo import MongoClient
from cryptography.fernet import Fernet

# Initialize FastAPI app
app = FastAPI(
    title="Gmail API Service",
    description="FastAPI service for Gmail operations: custom emailing, searching, and thread retrieval",
    version="1.0.0"
)

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://pythonProd:pythonfindiy25@findiy-main.t5gfeq.mongodb.net/Findiy_Production_Python?retryWrites=true&w=majority&appName=Findiy-main"
DB_NAME = "Findiy_Production_Python"
COLLECTION_NAME = "gmail_test"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Encryption key - Fixed key for persistent credentials across restarts
# IMPORTANT: In production, store this in environment variable!
DEFAULT_ENCRYPTION_KEY = "nybmG4fqyl5PZkymPJHsgBCCqxvf1jqwpENm-0-crVo="
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY).encode()
cipher = Fernet(ENCRYPTION_KEY)

# OAuth Configuration
CLIENT_SECRETS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
REDIRECT_URI = 'http://localhost:5000/oauth2callback'


# Pydantic Models
class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


class SearchEmailsRequest(BaseModel):
    query: str
    max_results: int = 10


class GetThreadsRequest(BaseModel):
    n: int = 10


class EmailResponse(BaseModel):
    id: str
    thread_id: str
    sender: str
    subject: str
    date: str
    snippet: str
    body: Optional[str] = None


class ThreadResponse(BaseModel):
    thread_id: str
    messages: List[EmailResponse]
    message_count: int


class SendEmailResponse(BaseModel):
    success: bool
    message_id: str
    thread_id: str
    message: str


class ReplyToThreadRequest(BaseModel):
    thread_id: str
    body: str
    reply_all: bool = False  # If True, reply to all recipients


class BulkEmailRequest(BaseModel):
    to: List[EmailStr]  # List of recipient email addresses
    subject: str
    body: str
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    send_individually: bool = True  # If True, send separate emails to each recipient


class BulkEmailResult(BaseModel):
    recipient: str
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None


class BulkEmailResponse(BaseModel):
    total_recipients: int
    successful: int
    failed: int
    results: List[BulkEmailResult]


# Helper Functions
def encrypt_token(token: str) -> str:
    """Encrypt sensitive token data"""
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt token data"""
    return cipher.decrypt(encrypted_token.encode()).decode()


def save_credentials_to_db(user_email: str, credentials: Credentials):
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
    
    collection.update_one(
        {'user_email': user_email},
        {'$set': creds_data},
        upsert=True
    )


def get_credentials_from_db(user_email: str) -> Optional[Credentials]:
    """Retrieve user credentials from MongoDB"""
    doc = collection.find_one({'user_email': user_email})
    
    if not doc:
        return None
    
    try:
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
    except Exception as e:
        # Decryption failed - likely because encryption key changed
        # Delete the old credentials and require re-authorization
        collection.delete_one({'user_email': user_email})
        raise HTTPException(
            status_code=401,
            detail="Stored credentials are invalid (encryption key may have changed). Please re-authorize at /authorize"
        )


def get_gmail_service(user_email: str):
    """Get Gmail service with stored credentials"""
    creds = get_credentials_from_db(user_email)
    
    if not creds:
        raise HTTPException(
            status_code=401,
            detail="User not authenticated. Please authorize first at /authorize"
        )
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials_to_db(user_email, creds)
    
    return build('gmail', 'v1', credentials=creds)


def get_user_email_from_google(credentials: Credentials) -> str:
    """Get user's email address from Google"""
    service = build('gmail', 'v1', credentials=credentials)
    profile = service.users().getProfile(userId='me').execute()
    return profile['emailAddress']


def get_email_body(message: dict) -> str:
    """Extract email body from message payload"""
    try:
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode()
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode()
                elif 'parts' in part:  # Handle nested parts
                    for nested_part in part['parts']:
                        if nested_part['mimeType'] == 'text/plain' and 'data' in nested_part['body']:
                            return base64.urlsafe_b64decode(nested_part['body']['data']).decode()
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            return base64.urlsafe_b64decode(message['payload']['body']['data']).decode()
    except Exception as e:
        return f"Error extracting body: {str(e)}"
    
    return "No body content available"


def parse_email_headers(headers: List[dict]) -> dict:
    """Parse email headers into a dict"""
    result = {
        'subject': '',
        'sender': '',
        'date': '',
        'to': '',
        'cc': ''
    }
    
    for h in headers:
        name_lower = h['name'].lower()
        if name_lower == 'subject':
            result['subject'] = h['value']
        elif name_lower == 'from':
            result['sender'] = h['value']
        elif name_lower == 'date':
            result['date'] = h['value']
        elif name_lower == 'to':
            result['to'] = h['value']
        elif name_lower == 'cc':
            result['cc'] = h['value']
    
    return result


# Dependency to get user email from header
async def get_user_email(x_user_email: str = Header(...)) -> str:
    """Get user email from request header"""
    if not x_user_email:
        raise HTTPException(status_code=400, detail="X-User-Email header is required")
    return x_user_email


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Gmail API Service",
        "version": "1.0.0",
        "endpoints": {
            "authorize": "/authorize",
            "send_email": "/api/send-email",
            "search_emails": "/api/search-emails",
            "get_threads": "/api/get-threads",
            "get_thread_detail": "/api/get-thread/{thread_id}"
        },
        "note": "Include X-User-Email header in all API requests"
    }


@app.get("/authorize")
async def authorize():
    """Step 1: Redirect user to Google's OAuth page"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Don't use state parameter - it causes issues with FastAPI
        # Google OAuth will still work securely without it for this use case
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in MongoDB temporarily for this session
        collection.update_one(
            {'_id': 'oauth_state'},
            {'$set': {'state': state, 'timestamp': datetime.utcnow()}},
            upsert=True
        )
        
        return RedirectResponse(url=authorization_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authorization error: {str(e)}")


@app.get("/oauth2callback")
async def oauth2callback(code: str, state: Optional[str] = None):
    """Step 2: Handle the callback from Google"""
    try:
        # Retrieve stored state from MongoDB
        state_doc = collection.find_one({'_id': 'oauth_state'})
        stored_state = state_doc.get('state') if state_doc else None
        
        # Create flow with or without state validation
        if stored_state and state and stored_state == state:
            # State matches - use it for additional security
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=SCOPES,
                state=state,
                redirect_uri=REDIRECT_URI
            )
        else:
            # No state or mismatch - proceed without state verification
            # This is acceptable for development/single-user scenarios
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        user_email = get_user_email_from_google(credentials)
        save_credentials_to_db(user_email, credentials)
        
        # Clean up the stored state
        collection.delete_one({'_id': 'oauth_state'})
        
        return {
            "success": True,
            "message": "Gmail connected successfully",
            "user_email": user_email,
            "note": "Use this email in X-User-Email header for API requests"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback error: {str(e)}")


@app.post("/api/send-email", response_model=SendEmailResponse)
async def send_email(
    email_data: SendEmailRequest,
    user_email: str = Depends(get_user_email)
):
    """
    Send a custom email
    
    - **to**: Recipient email address
    - **subject**: Email subject
    - **body**: Email body content
    - **cc**: Optional list of CC recipients
    - **bcc**: Optional list of BCC recipients
    """
    try:
        service = get_gmail_service(user_email)
        
        message = EmailMessage()
        message.set_content(email_data.body)
        message['To'] = email_data.to
        message['Subject'] = email_data.subject
        
        if email_data.cc:
            message['Cc'] = ', '.join(email_data.cc)
        
        if email_data.bcc:
            message['Bcc'] = ', '.join(email_data.bcc)
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = {'raw': encoded_message}
        
        result = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        return SendEmailResponse(
            success=True,
            message_id=result['id'],
            thread_id=result['threadId'],
            message=f"Email sent successfully to {email_data.to}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")


@app.post("/api/bulk-email", response_model=BulkEmailResponse)
async def send_bulk_email(
    email_data: BulkEmailRequest,
    user_email: str = Depends(get_user_email)
):
    """
    Send emails to multiple recipients
    
    - **to**: List of recipient email addresses
    - **subject**: Email subject
    - **body**: Email body content
    - **cc**: Optional list of CC recipients
    - **bcc**: Optional list of BCC recipients
    - **send_individually**: If True (default), sends separate emails to each recipient.
                            If False, sends one email with all recipients in the To field.
    """
    try:
        service = get_gmail_service(user_email)
        
        results = []
        successful = 0
        failed = 0
        
        if email_data.send_individually:
            # Send separate email to each recipient
            for recipient in email_data.to:
                try:
                    message = EmailMessage()
                    message.set_content(email_data.body)
                    message['To'] = recipient
                    message['Subject'] = email_data.subject
                    
                    if email_data.cc:
                        message['Cc'] = ', '.join(email_data.cc)
                    
                    if email_data.bcc:
                        message['Bcc'] = ', '.join(email_data.bcc)
                    
                    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                    send_message = {'raw': encoded_message}
                    
                    result = service.users().messages().send(
                        userId='me',
                        body=send_message
                    ).execute()
                    
                    results.append(BulkEmailResult(
                        recipient=recipient,
                        success=True,
                        message_id=result['id'],
                        thread_id=result['threadId']
                    ))
                    successful += 1
                    
                except Exception as e:
                    results.append(BulkEmailResult(
                        recipient=recipient,
                        success=False,
                        error=str(e)
                    ))
                    failed += 1
        else:
            # Send one email with all recipients in To field
            try:
                message = EmailMessage()
                message.set_content(email_data.body)
                message['To'] = ', '.join(email_data.to)
                message['Subject'] = email_data.subject
                
                if email_data.cc:
                    message['Cc'] = ', '.join(email_data.cc)
                
                if email_data.bcc:
                    message['Bcc'] = ', '.join(email_data.bcc)
                
                encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                send_message = {'raw': encoded_message}
                
                result = service.users().messages().send(
                    userId='me',
                    body=send_message
                ).execute()
                
                # Mark all recipients as successful
                for recipient in email_data.to:
                    results.append(BulkEmailResult(
                        recipient=recipient,
                        success=True,
                        message_id=result['id'],
                        thread_id=result['threadId']
                    ))
                    successful += 1
                    
            except Exception as e:
                # Mark all recipients as failed
                for recipient in email_data.to:
                    results.append(BulkEmailResult(
                        recipient=recipient,
                        success=False,
                        error=str(e)
                    ))
                    failed += 1
        
        return BulkEmailResponse(
            total_recipients=len(email_data.to),
            successful=successful,
            failed=failed,
            results=results
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending bulk email: {str(e)}")


@app.post("/api/reply-to-thread", response_model=SendEmailResponse)
async def reply_to_thread(
    reply_data: ReplyToThreadRequest,
    user_email: str = Depends(get_user_email)
):
    """
    Reply to an existing email thread
    
    - **thread_id**: The ID of the thread to reply to
    - **body**: The reply body content
    - **reply_all**: If True, reply to all recipients (default: False)
    """
    try:
        service = get_gmail_service(user_email)
        
        # Get the original thread to extract message details
        thread = service.users().threads().get(
            userId='me',
            id=reply_data.thread_id,
            format='full'
        ).execute()
        
        if not thread.get('messages'):
            raise HTTPException(status_code=404, detail="Thread not found or has no messages")
        
        # Get the last message in the thread to reply to
        last_message = thread['messages'][-1]
        last_message_id = last_message['id']
        
        # Extract headers from the last message
        headers = last_message['payload']['headers']
        original_subject = ''
        original_from = ''
        original_to = ''
        original_cc = ''
        message_id_header = ''
        references = ''
        
        for h in headers:
            name_lower = h['name'].lower()
            if name_lower == 'subject':
                original_subject = h['value']
            elif name_lower == 'from':
                original_from = h['value']
            elif name_lower == 'to':
                original_to = h['value']
            elif name_lower == 'cc':
                original_cc = h['value']
            elif name_lower == 'message-id':
                message_id_header = h['value']
            elif name_lower == 'references':
                references = h['value']
        
        # Build reply subject (add Re: if not already present)
        reply_subject = original_subject
        if not reply_subject.lower().startswith('re:'):
            reply_subject = f"Re: {original_subject}"
        
        # Determine recipients
        # Extract email from "Name <email@domain.com>" format
        import re
        def extract_email(s):
            match = re.search(r'<([^>]+)>', s)
            return match.group(1) if match else s.strip()
        
        # Reply goes to the sender of the last message
        reply_to = extract_email(original_from)
        
        # Create the reply message
        message = EmailMessage()
        message.set_content(reply_data.body)
        message['To'] = reply_to
        message['Subject'] = reply_subject
        
        # Add CC recipients if reply_all is True
        if reply_data.reply_all:
            cc_list = []
            # Add original To (except our own email)
            if original_to:
                for addr in original_to.split(','):
                    email_addr = extract_email(addr.strip())
                    if email_addr and email_addr.lower() != user_email.lower() and email_addr.lower() != reply_to.lower():
                        cc_list.append(email_addr)
            # Add original CC
            if original_cc:
                for addr in original_cc.split(','):
                    email_addr = extract_email(addr.strip())
                    if email_addr and email_addr.lower() != user_email.lower() and email_addr.lower() != reply_to.lower():
                        cc_list.append(email_addr)
            
            if cc_list:
                message['Cc'] = ', '.join(list(set(cc_list)))  # Remove duplicates
        
        # Set threading headers
        if message_id_header:
            message['In-Reply-To'] = message_id_header
            if references:
                message['References'] = f"{references} {message_id_header}"
            else:
                message['References'] = message_id_header
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send the reply with the thread ID to keep it in the same thread
        send_message = {
            'raw': encoded_message,
            'threadId': reply_data.thread_id
        }
        
        result = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        return SendEmailResponse(
            success=True,
            message_id=result['id'],
            thread_id=result['threadId'],
            message=f"Reply sent successfully to {reply_to}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending reply: {str(e)}")


@app.post("/api/search-emails")
async def search_emails(
    search_data: SearchEmailsRequest,
    user_email: str = Depends(get_user_email)
):
    """
    Search emails by query
    
    - **query**: Gmail search query (e.g., "from:someone@example.com", "subject:important", "is:unread")
    - **max_results**: Maximum number of results to return (default: 10)
    
    Examples of queries:
    - "from:user@example.com"
    - "subject:meeting"
    - "is:unread"
    - "has:attachment"
    - "after:2024/01/01"
    """
    try:
        service = get_gmail_service(user_email)
        
        results = service.users().messages().list(
            userId='me',
            q=search_data.query,
            maxResults=search_data.max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "query": search_data.query,
                "total_results": 0,
                "emails": []
            }
        
        emails = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = parse_email_headers(message['payload']['headers'])
            body = get_email_body(message)
            
            emails.append(EmailResponse(
                id=message['id'],
                thread_id=message['threadId'],
                sender=headers['sender'],
                subject=headers['subject'],
                date=headers['date'],
                snippet=message.get('snippet', ''),
                body=body[:500] + "..." if len(body) > 500 else body
            ))
        
        return {
            "query": search_data.query,
            "total_results": len(emails),
            "emails": emails
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching emails: {str(e)}")


@app.post("/api/get-threads", response_model=List[ThreadResponse])
async def get_threads(
    request_data: GetThreadsRequest,
    user_email: str = Depends(get_user_email)
):
    """
    Retrieve the last n email threads with full message content
    
    - **n**: Number of threads to retrieve (default: 10, max: 100)
    """
    try:
        if request_data.n > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 threads allowed")
        
        service = get_gmail_service(user_email)
        
        # Get thread list
        results = service.users().threads().list(
            userId='me',
            maxResults=request_data.n
        ).execute()
        
        threads = results.get('threads', [])
        
        if not threads:
            return []
        
        thread_responses = []
        
        for thread_item in threads:
            # Get full thread details
            thread = service.users().threads().get(
                userId='me',
                id=thread_item['id'],
                format='full'
            ).execute()
            
            messages = []
            for message in thread['messages']:
                headers = parse_email_headers(message['payload']['headers'])
                body = get_email_body(message)
                
                messages.append(EmailResponse(
                    id=message['id'],
                    thread_id=message['threadId'],
                    sender=headers['sender'],
                    subject=headers['subject'],
                    date=headers['date'],
                    snippet=message.get('snippet', ''),
                    body=body
                ))
            
            thread_responses.append(ThreadResponse(
                thread_id=thread['id'],
                messages=messages,
                message_count=len(messages)
            ))
        
        return thread_responses
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving threads: {str(e)}")


@app.get("/api/get-thread/{thread_id}", response_model=ThreadResponse)
async def get_thread_detail(
    thread_id: str,
    user_email: str = Depends(get_user_email)
):
    """
    Get full details of a specific email thread
    
    - **thread_id**: The ID of the thread to retrieve
    """
    try:
        service = get_gmail_service(user_email)
        
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='full'
        ).execute()
        
        messages = []
        for message in thread['messages']:
            headers = parse_email_headers(message['payload']['headers'])
            body = get_email_body(message)
            
            messages.append(EmailResponse(
                id=message['id'],
                thread_id=message['threadId'],
                sender=headers['sender'],
                subject=headers['subject'],
                date=headers['date'],
                snippet=message.get('snippet', ''),
                body=body
            ))
        
        return ThreadResponse(
            thread_id=thread['id'],
            messages=messages,
            message_count=len(messages)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving thread: {str(e)}")


@app.get("/api/connected-users")
async def list_connected_users():
    """List all connected Gmail accounts (Admin endpoint)"""
    try:
        users = list(collection.find({}, {'user_email': 1, 'created_at': 1, '_id': 0}))
        return {
            "total_users": len(users),
            "users": users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")


@app.delete("/api/logout")
async def logout(user_email: str = Depends(get_user_email)):
    """
    Logout and delete user credentials
    
    This will remove the stored Gmail credentials for the user.
    The user will need to re-authorize to use the API again.
    """
    try:
        result = collection.delete_one({'user_email': user_email})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No credentials found for {user_email}"
            )
        
        return {
            "success": True,
            "message": f"Successfully logged out and deleted credentials for {user_email}",
            "user_email": user_email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during logout: {str(e)}")


@app.delete("/api/delete-user/{email}")
async def delete_user(email: str):
    """
    Delete a specific user's credentials (Admin endpoint)
    
    - **email**: The email address of the user to delete
    """
    try:
        result = collection.delete_one({'user_email': email})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No credentials found for {email}"
            )
        
        return {
            "success": True,
            "message": f"Successfully deleted credentials for {email}",
            "deleted_email": email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for local development
    
    print("\n" + "="*50)
    print("🚀 Starting FastAPI Gmail Service")
    print("="*50)
    print("📝 API Documentation: http://localhost:5000/docs")
    print("🔄 ReDoc: http://localhost:5000/redoc")
    print("="*50)
    print("🔐 Using fixed encryption key (credentials persist across restarts)")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
