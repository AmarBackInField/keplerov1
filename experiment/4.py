"""
Meta Business / Facebook Messenger OAuth Integration

This module handles:
1. Facebook OAuth authentication
2. Getting User Access Token
3. Getting Page Access Token (for Messenger)
4. Sending messages via Messenger on behalf of users
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from cryptography.fernet import Fernet

# Initialize FastAPI app
app = FastAPI(
    title="Meta Messenger API Service",
    description="FastAPI service for Facebook/Meta Messenger OAuth and messaging",
    version="1.0.0"
)

# ============================================
# CONFIGURATION - Update these with your values
# ============================================

# Meta App Credentials (Get from https://developers.facebook.com/apps → Your App → Settings → Basic)
# TODO: Replace with your actual values or set as environment variables
META_APP_ID = os.getenv('META_APP_ID', '860152246958629')  # Found in: App Settings → Basic → App ID
META_APP_SECRET = os.getenv('META_APP_SECRET', 'e846aabbbe1f948face1b1679fff9e19')  # Found in: App Settings → Basic → App Secret (click Show)

# Callback URL - Must be added in Meta Developer Console:
# Go to: Your App → Use Cases → Messenger → Configure → Callback URL
# Or: Your App → Facebook Login → Settings → Valid OAuth Redirect URIs
REDIRECT_URI = os.getenv('META_REDIRECT_URI', 'https://unnumbered-debasedly-cyndi.ngrok-free.dev/auth/callback')

# MongoDB Configuration
MONGODB_URI = os.getenv(
    'MONGODB_URI',
    "mongodb+srv://pythonProd:pythonfindiy25@findiy-main.t5gfeq.mongodb.net/Findiy_Production_Python?retryWrites=true&w=majority&appName=Findiy-main"
)
DB_NAME = "Findiy_Production_Python"
COLLECTION_NAME = "meta_messenger_tokens"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Encryption key for storing tokens securely
DEFAULT_ENCRYPTION_KEY = "nybmG4fqyl5PZkymPJHsgBCCqxvf1jqwpENm-0-crVo="
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY).encode()
cipher = Fernet(ENCRYPTION_KEY)

# Meta Graph API Base URL
GRAPH_API_URL = "https://graph.facebook.com/v18.0"

# Required permissions for Messenger
# For Facebook Login for Business, use only these scopes:
# - pages_messaging: Send messages from Pages
# - pages_manage_metadata: Get Page information
# - pages_show_list: List pages user manages
# Note: public_profile is automatically included
SCOPES = [
    "pages_show_list",
    "pages_messaging",
    "pages_manage_metadata"
]


# ============================================
# Pydantic Models
# ============================================

class SendMessageRequest(BaseModel):
    recipient_id: str  # Facebook Page-scoped ID (PSID) of the recipient
    message_text: str
    page_id: str  # The Page ID to send from


class SendMessageResponse(BaseModel):
    success: bool
    recipient_id: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class PageInfo(BaseModel):
    page_id: str
    page_name: str
    access_token_exists: bool


class UserConnectionStatus(BaseModel):
    connected: bool
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    pages: Optional[List[PageInfo]] = None


# ============================================
# Helper Functions
# ============================================

def encrypt_token(token: str) -> str:
    """Encrypt sensitive token data"""
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt token data"""
    return cipher.decrypt(encrypted_token.encode()).decode()


def save_user_tokens(user_id: str, user_data: dict):
    """Save user and page tokens to MongoDB"""
    # Encrypt sensitive tokens
    encrypted_data = {
        'user_id': user_id,
        'user_name': user_data.get('user_name'),
        'email': user_data.get('email'),
        'access_token': encrypt_token(user_data['access_token']),
        'token_expires_at': user_data.get('token_expires_at'),
        'pages': [],
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    # Encrypt page tokens
    if 'pages' in user_data:
        for page in user_data['pages']:
            encrypted_data['pages'].append({
                'page_id': page['page_id'],
                'page_name': page['page_name'],
                'access_token': encrypt_token(page['access_token']),
                'category': page.get('category', '')
            })
    
    collection.update_one(
        {'user_id': user_id},
        {'$set': encrypted_data},
        upsert=True
    )
    print(f"✅ Tokens saved for user {user_id}")


def get_user_tokens(user_id: str) -> Optional[dict]:
    """Retrieve user tokens from MongoDB"""
    doc = collection.find_one({'user_id': user_id})
    
    if not doc:
        return None
    
    try:
        decrypted_data = {
            'user_id': doc['user_id'],
            'user_name': doc.get('user_name'),
            'email': doc.get('email'),
            'access_token': decrypt_token(doc['access_token']),
            'token_expires_at': doc.get('token_expires_at'),
            'pages': []
        }
        
        for page in doc.get('pages', []):
            decrypted_data['pages'].append({
                'page_id': page['page_id'],
                'page_name': page['page_name'],
                'access_token': decrypt_token(page['access_token']),
                'category': page.get('category', '')
            })
        
        return decrypted_data
    except Exception as e:
        print(f"Error decrypting tokens: {e}")
        return None


def get_page_access_token(user_id: str, page_id: str) -> Optional[str]:
    """Get page access token for a specific page"""
    user_data = get_user_tokens(user_id)
    
    if not user_data:
        return None
    
    for page in user_data.get('pages', []):
        if page['page_id'] == page_id:
            return page['access_token']
    
    return None


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token"""
    token_url = f"{GRAPH_API_URL}/oauth/access_token"
    
    params = {
        'client_id': META_APP_ID,
        'client_secret': META_APP_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': code
    }
    
    response = requests.get(token_url, params=params)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code for token: {response.json()}"
        )
    
    return response.json()


def get_long_lived_token(short_lived_token: str) -> dict:
    """Exchange short-lived token for long-lived token (60 days)"""
    token_url = f"{GRAPH_API_URL}/oauth/access_token"
    
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': META_APP_ID,
        'client_secret': META_APP_SECRET,
        'fb_exchange_token': short_lived_token
    }
    
    response = requests.get(token_url, params=params)
    
    if response.status_code != 200:
        # Return original token if exchange fails
        return {'access_token': short_lived_token, 'expires_in': 3600}
    
    return response.json()


def get_user_info(access_token: str) -> dict:
    """Get user profile information"""
    url = f"{GRAPH_API_URL}/me"
    
    params = {
        'fields': 'id,name,email',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get user info: {response.json()}"
        )
    
    return response.json()


def get_user_pages(access_token: str) -> List[dict]:
    """Get list of pages the user manages"""
    url = f"{GRAPH_API_URL}/me/accounts"
    
    params = {
        'fields': 'id,name,access_token,category',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Failed to get pages: {response.json()}")
        return []
    
    data = response.json()
    return data.get('data', [])


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Meta Messenger API Service",
        "version": "1.0.0",
        "endpoints": {
            "authorize": "/auth/login - Start OAuth flow",
            "callback": "/auth/callback - OAuth callback (automatic)",
            "status": "/auth/status/{user_id} - Check connection status",
            "pages": "/api/pages/{user_id} - List connected pages",
            "send_message": "/api/send-message - Send Messenger message",
            "webhook": "/webhook - Messenger webhook endpoint"
        },
        "setup_instructions": {
            "step_1": "Configure META_APP_ID and META_APP_SECRET environment variables",
            "step_2": "Set REDIRECT_URI to match your Meta App callback URL",
            "step_3": "Visit /auth/login to start the OAuth flow",
            "step_4": "After authorization, use /api/send-message to send messages"
        }
    }


@app.get("/auth/login")
async def authorize():
    """
    Step 1: Redirect user to Facebook Login Dialog
    
    This initiates the OAuth flow. The user will be redirected to Facebook
    to log in and grant permissions.
    """
    # Build authorization URL
    auth_url = "https://www.facebook.com/v18.0/dialog/oauth"
    
    scope_string = ",".join(SCOPES)
    
    params = {
        'client_id': META_APP_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': scope_string,
        'response_type': 'code',
        'state': 'meta_auth_state'  # In production, use a random state for CSRF protection
    }
    
    # Construct full URL
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_auth_url = f"{auth_url}?{query_string}"
    
    return RedirectResponse(url=full_auth_url)


@app.get("/auth/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Step 2: Handle OAuth callback from Facebook
    
    Facebook redirects here with an authorization code.
    We exchange it for an access token and fetch user/page info.
    """
    # Handle error from Facebook
    if error:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": error,
                "error_description": error_description
            }
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")
    
    try:
        # Step 2a: Exchange code for short-lived token
        token_data = exchange_code_for_token(code)
        short_lived_token = token_data['access_token']
        
        # Step 2b: Exchange for long-lived token (valid for 60 days)
        long_lived_data = get_long_lived_token(short_lived_token)
        access_token = long_lived_data['access_token']
        expires_in = long_lived_data.get('expires_in', 5184000)  # Default 60 days
        
        # Step 2c: Get user information
        user_info = get_user_info(access_token)
        user_id = user_info['id']
        user_name = user_info.get('name', 'Unknown')
        email = user_info.get('email', '')
        
        # Step 2d: Get pages the user manages
        pages = get_user_pages(access_token)
        
        # Prepare page data
        page_data = []
        for page in pages:
            page_data.append({
                'page_id': page['id'],
                'page_name': page['name'],
                'access_token': page['access_token'],  # This is the Page Access Token!
                'category': page.get('category', '')
            })
        
        # Step 2e: Save everything to database
        user_data = {
            'user_name': user_name,
            'email': email,
            'access_token': access_token,
            'token_expires_at': datetime.utcnow() + timedelta(seconds=expires_in),
            'pages': page_data
        }
        
        save_user_tokens(user_id, user_data)
        
        # Return success response
        return {
            "success": True,
            "message": "Facebook account connected successfully!",
            "user_id": user_id,
            "user_name": user_name,
            "email": email,
            "pages_connected": len(page_data),
            "pages": [{"id": p['page_id'], "name": p['page_name']} for p in page_data],
            "note": "Use the user_id in API requests. Page access tokens are stored securely."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback error: {str(e)}")


@app.get("/auth/status/{user_id}", response_model=UserConnectionStatus)
async def check_connection_status(user_id: str):
    """
    Check if a user is connected and get their page list
    """
    user_data = get_user_tokens(user_id)
    
    if not user_data:
        return UserConnectionStatus(connected=False)
    
    pages = [
        PageInfo(
            page_id=page['page_id'],
            page_name=page['page_name'],
            access_token_exists=bool(page.get('access_token'))
        )
        for page in user_data.get('pages', [])
    ]
    
    return UserConnectionStatus(
        connected=True,
        user_id=user_data['user_id'],
        user_name=user_data.get('user_name'),
        pages=pages
    )


@app.get("/api/pages/{user_id}")
async def list_user_pages(user_id: str):
    """
    List all Facebook Pages connected for a user
    """
    user_data = get_user_tokens(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please authorize at /auth/login"
        )
    
    pages = [
        {
            "page_id": page['page_id'],
            "page_name": page['page_name'],
            "category": page.get('category', 'Unknown')
        }
        for page in user_data.get('pages', [])
    ]
    
    return {
        "user_id": user_id,
        "user_name": user_data.get('user_name'),
        "total_pages": len(pages),
        "pages": pages
    }


@app.post("/api/send-message", response_model=SendMessageResponse)
async def send_messenger_message(request: SendMessageRequest):
    """
    Send a message via Facebook Messenger
    
    - **recipient_id**: The Page-scoped ID (PSID) of the recipient
    - **message_text**: The text message to send
    - **page_id**: The Facebook Page ID to send from
    
    Note: The recipient must have an existing conversation with the Page.
    """
    # Find the user who owns this page
    page_doc = collection.find_one({'pages.page_id': request.page_id})
    
    if not page_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Page {request.page_id} not found. Please authorize at /auth/login"
        )
    
    # Get the page access token
    page_token = None
    for page in page_doc.get('pages', []):
        if page['page_id'] == request.page_id:
            try:
                page_token = decrypt_token(page['access_token'])
            except:
                page_token = None
            break
    
    if not page_token:
        raise HTTPException(
            status_code=401,
            detail="Page access token not found or invalid"
        )
    
    # Send message via Messenger Platform Send API
    send_url = f"{GRAPH_API_URL}/{request.page_id}/messages"
    
    payload = {
        'recipient': {'id': request.recipient_id},
        'message': {'text': request.message_text},
        'messaging_type': 'RESPONSE',
        'access_token': page_token
    }
    
    try:
        response = requests.post(send_url, json=payload)
        result = response.json()
        
        if response.status_code == 200:
            return SendMessageResponse(
                success=True,
                recipient_id=result.get('recipient_id', request.recipient_id),
                message_id=result.get('message_id')
            )
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            return SendMessageResponse(
                success=False,
                recipient_id=request.recipient_id,
                error=error_msg
            )
            
    except Exception as e:
        return SendMessageResponse(
            success=False,
            recipient_id=request.recipient_id,
            error=str(e)
        )


@app.get("/webhook")
async def webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Webhook verification endpoint for Facebook
    
    Facebook will send a GET request to verify your webhook.
    Set your verify token in the Meta App Dashboard.
    """
    VERIFY_TOKEN = os.getenv('META_VERIFY_TOKEN', 'my_verify_token')
    
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        print("Webhook verified!")
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook_receive(request: dict):
    """
    Webhook endpoint to receive messages from Facebook Messenger
    
    When someone sends a message to your Page, Facebook sends it here.
    """
    print(f"Received webhook: {request}")
    
    # Process incoming messages
    if request.get('object') == 'page':
        for entry in request.get('entry', []):
            page_id = entry.get('id')
            
            for event in entry.get('messaging', []):
                sender_id = event.get('sender', {}).get('id')
                
                if 'message' in event:
                    message_text = event['message'].get('text', '')
                    print(f"Received message from {sender_id}: {message_text}")
                    
                    # Here you can:
                    # 1. Store the message
                    # 2. Process it with AI
                    # 3. Send an automated response
                    
    return {"status": "ok"}


@app.get("/api/connected-users")
async def list_connected_users():
    """List all connected Facebook accounts (Admin endpoint)"""
    try:
        users = list(collection.find(
            {},
            {
                'user_id': 1,
                'user_name': 1,
                'email': 1,
                'created_at': 1,
                'pages': {'$slice': ['$pages', 0]},  # Just get page count
                '_id': 0
            }
        ))
        
        # Format response
        formatted_users = []
        for user in users:
            page_count = len(collection.find_one({'user_id': user['user_id']}).get('pages', []))
            formatted_users.append({
                'user_id': user['user_id'],
                'user_name': user.get('user_name'),
                'email': user.get('email'),
                'connected_at': user.get('created_at'),
                'pages_count': page_count
            })
        
        return {
            "total_users": len(formatted_users),
            "users": formatted_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")


@app.get("/api/conversations/{page_id}")
async def get_conversations(page_id: str):
    """
    Get all conversations and PSIDs for a Facebook Page
    
    - **page_id**: The Facebook Page ID
    
    Returns list of conversations with participant PSIDs
    """
    # Find the page token
    page_doc = collection.find_one({'pages.page_id': page_id})
    
    if not page_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_id} not found. Please authorize at /auth/login"
        )
    
    # Get the page access token
    page_token = None
    for page in page_doc.get('pages', []):
        if page['page_id'] == page_id:
            try:
                page_token = decrypt_token(page['access_token'])
            except:
                page_token = None
            break
    
    if not page_token:
        raise HTTPException(
            status_code=401,
            detail="Page access token not found or invalid"
        )
    
    # Fetch conversations from Graph API
    conversations_url = f"{GRAPH_API_URL}/{page_id}/conversations"
    
    params = {
        'fields': 'participants,updated_time,message_count',
        'access_token': page_token
    }
    
    try:
        response = requests.get(conversations_url, params=params)
        result = response.json()
        
        if response.status_code != 200:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
        
        conversations = result.get('data', [])
        
        # Extract PSIDs from conversations
        formatted_conversations = []
        all_psids = []
        
        for conv in conversations:
            participants = conv.get('participants', {}).get('data', [])
            
            # Filter out the page itself from participants
            user_participants = [
                {
                    'psid': p['id'],
                    'name': p.get('name', 'Unknown')
                }
                for p in participants
                if p['id'] != page_id
            ]
            
            for p in user_participants:
                if p['psid'] not in [x['psid'] for x in all_psids]:
                    all_psids.append(p)
            
            formatted_conversations.append({
                'conversation_id': conv.get('id'),
                'participants': user_participants,
                'message_count': conv.get('message_count', 0),
                'updated_time': conv.get('updated_time')
            })
        
        return {
            "page_id": page_id,
            "total_conversations": len(formatted_conversations),
            "total_unique_users": len(all_psids),
            "all_psids": all_psids,
            "conversations": formatted_conversations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")


@app.get("/api/psids/{page_id}")
async def get_all_psids(page_id: str):
    """
    Get all unique PSIDs (user IDs) who have messaged a Facebook Page
    
    - **page_id**: The Facebook Page ID
    
    Returns a simple list of PSIDs that can be used for sending messages
    """
    # Find the page token
    page_doc = collection.find_one({'pages.page_id': page_id})
    
    if not page_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_id} not found. Please authorize at /auth/login"
        )
    
    # Get the page access token
    page_token = None
    for page in page_doc.get('pages', []):
        if page['page_id'] == page_id:
            try:
                page_token = decrypt_token(page['access_token'])
            except:
                page_token = None
            break
    
    if not page_token:
        raise HTTPException(
            status_code=401,
            detail="Page access token not found or invalid"
        )
    
    # Fetch conversations from Graph API
    conversations_url = f"{GRAPH_API_URL}/{page_id}/conversations"
    
    params = {
        'fields': 'participants',
        'access_token': page_token
    }
    
    try:
        response = requests.get(conversations_url, params=params)
        result = response.json()
        
        if response.status_code != 200:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
        
        conversations = result.get('data', [])
        
        # Extract unique PSIDs
        psids = []
        
        for conv in conversations:
            participants = conv.get('participants', {}).get('data', [])
            
            for p in participants:
                # Exclude the page itself
                if p['id'] != page_id:
                    psid_entry = {
                        'psid': p['id'],
                        'name': p.get('name', 'Unknown')
                    }
                    if psid_entry['psid'] not in [x['psid'] for x in psids]:
                        psids.append(psid_entry)
        
        return {
            "page_id": page_id,
            "total_users": len(psids),
            "users": psids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PSIDs: {str(e)}")


@app.delete("/api/disconnect/{user_id}")
async def disconnect_user(user_id: str):
    """
    Disconnect a user and remove their stored tokens
    """
    result = collection.delete_one({'user_id': user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    return {
        "success": True,
        "message": f"User {user_id} disconnected successfully"
    }


# ============================================
# Run the application
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("🚀 Starting Meta Messenger API Service")
    print("=" * 60)
    print(f"📱 App ID: {META_APP_ID}")
    print(f"🔗 Callback URL: {REDIRECT_URI}")
    print("=" * 60)
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔄 ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    print("\n⚠️  Make sure to configure:")
    print("   - META_APP_ID (environment variable or in code)")
    print("   - META_APP_SECRET (environment variable)")
    print("   - META_REDIRECT_URI (must match Meta App settings)")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
