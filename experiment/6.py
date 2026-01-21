"""
Instagram Business API Integration

This module handles:
1. Instagram Business OAuth authentication
2. Getting User Access Token
3. Sending Instagram Direct Messages
4. Receiving messages via webhook
5. Managing Instagram accounts and contacts
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from cryptography.fernet import Fernet

# Initialize FastAPI app
app = FastAPI(
    title="Instagram Business API Service",
    description="FastAPI service for Instagram Business OAuth and messaging",
    version="1.0.0"
)

# ============================================
# CONFIGURATION - Update these with your values
# ============================================

# Meta App Credentials (from https://developers.facebook.com/apps)
META_APP_ID = os.getenv('META_APP_ID', '860152246958629')
META_APP_SECRET = os.getenv('META_APP_SECRET', 'e846aabbbe1f948face1b1679fff9e19')

# Callback URL (must match what's configured in Meta Developer Console)
REDIRECT_URI = os.getenv('META_REDIRECT_URI', 'https://unnumbered-debasedly-cyndi.ngrok-free.dev/instagram/callback')

# MongoDB Configuration
MONGODB_URI = os.getenv(
    'MONGODB_URI',
    "mongodb+srv://pythonProd:pythonfindiy25@findiy-main.t5gfeq.mongodb.net/Findiy_Production_Python?retryWrites=true&w=majority&appName=Findiy-main"
)
DB_NAME = "Findiy_Production_Python"
COLLECTION_NAME = "instagram_tokens"
MESSAGES_COLLECTION = "instagram_messages"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
messages_collection = db[MESSAGES_COLLECTION]

# Encryption key for storing tokens securely
DEFAULT_ENCRYPTION_KEY = "nybmG4fqyl5PZkymPJHsgBCCqxvf1jqwpENm-0-crVo="
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY).encode()
cipher = Fernet(ENCRYPTION_KEY)

# Meta Graph API Base URL
GRAPH_API_URL = "https://graph.facebook.com/v18.0"

# Instagram API Scopes
# Note: Some scopes require App Review for production use
SCOPES = [
    "pages_show_list",           # Required: List user's pages
    "pages_messaging",           # Required: Send/receive messages
    "pages_manage_metadata",     # Required: Manage page settings
    "business_management",       # Required: Access business assets
    # Additional scopes (add after App Review approval):
    # "pages_read_engagement",   # Read page engagement - requires app review
    # "instagram_basic",         # Basic Instagram info - requires app review
    # "instagram_manage_messages", # Instagram DM - requires app review
]

# Webhook Verify Token
VERIFY_TOKEN = os.getenv('INSTAGRAM_VERIFY_TOKEN', 'instagram_verify_token_123')


# ============================================
# Pydantic Models
# ============================================

class SendTextMessageRequest(BaseModel):
    recipient_id: str  # Instagram-scoped user ID (IGSID)
    message: str
    instagram_account_id: str  # Your Instagram Business Account ID


class SendMediaMessageRequest(BaseModel):
    recipient_id: str  # Instagram-scoped user ID
    media_type: str  # "image", "video", "audio", "file"
    media_url: str  # URL of the media
    instagram_account_id: str


class SendTemplateMessageRequest(BaseModel):
    recipient_id: str  # Instagram-scoped user ID
    template_type: str  # "generic", "product", "button"
    instagram_account_id: str
    elements: Optional[List[dict]] = None  # Template elements
    buttons: Optional[List[dict]] = None  # Quick reply buttons


class MessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    recipient_id: str
    error: Optional[str] = None


class InstagramAccount(BaseModel):
    instagram_business_account_id: str
    username: str
    name: str
    profile_picture_url: Optional[str] = None
    page_id: str  # Connected Facebook Page ID


class UserConnectionStatus(BaseModel):
    connected: bool
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    instagram_accounts: Optional[List[InstagramAccount]] = None


class IceBreaker(BaseModel):
    question: str
    payload: str


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
    """Save user and Instagram tokens to MongoDB"""
    encrypted_data = {
        'user_id': user_id,
        'user_name': user_data.get('user_name'),
        'access_token': encrypt_token(user_data['access_token']),
        'token_expires_at': user_data.get('token_expires_at'),
        'instagram_accounts': user_data.get('instagram_accounts', []),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    collection.update_one(
        {'user_id': user_id},
        {'$set': encrypted_data},
        upsert=True
    )
    print(f"✅ Instagram tokens saved for user {user_id}")


def get_user_tokens(user_id: str) -> Optional[dict]:
    """Retrieve user tokens from MongoDB"""
    doc = collection.find_one({'user_id': user_id})
    
    if not doc:
        return None
    
    try:
        return {
            'user_id': doc['user_id'],
            'user_name': doc.get('user_name'),
            'access_token': decrypt_token(doc['access_token']),
            'token_expires_at': doc.get('token_expires_at'),
            'instagram_accounts': doc.get('instagram_accounts', [])
        }
    except Exception as e:
        print(f"Error decrypting tokens: {e}")
        return None


def get_access_token_by_instagram_id(instagram_account_id: str) -> Optional[str]:
    """Get access token for a specific Instagram Account ID"""
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        return None
    
    try:
        return decrypt_token(doc['access_token'])
    except:
        return None


def get_page_access_token(user_access_token: str, page_id: str) -> Optional[str]:
    """Get page access token for a specific page"""
    url = f"{GRAPH_API_URL}/{page_id}"
    params = {
        'fields': 'access_token',
        'access_token': user_access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json().get('access_token')
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
        return {'access_token': short_lived_token, 'expires_in': 3600}
    
    return response.json()


def get_user_info(access_token: str) -> dict:
    """Get user profile information"""
    url = f"{GRAPH_API_URL}/me"
    
    params = {
        'fields': 'id,name',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get user info: {response.json()}"
        )
    
    return response.json()


def get_instagram_business_accounts(access_token: str) -> List[dict]:
    """Get list of Instagram Business Accounts connected to user's Facebook Pages"""
    # First, get the user's pages
    pages_url = f"{GRAPH_API_URL}/me/accounts"
    
    params = {
        'fields': 'id,name,instagram_business_account,access_token',
        'access_token': access_token
    }
    
    response = requests.get(pages_url, params=params)
    
    if response.status_code != 200:
        print(f"Failed to get pages: {response.json()}")
        return []
    
    pages = response.json().get('data', [])
    instagram_accounts = []
    
    for page in pages:
        instagram_account = page.get('instagram_business_account')
        
        if instagram_account:
            ig_id = instagram_account['id']
            page_access_token = page.get('access_token', access_token)
            
            # Get Instagram account details
            ig_url = f"{GRAPH_API_URL}/{ig_id}"
            ig_params = {
                'fields': 'id,username,name,profile_picture_url,followers_count,follows_count,media_count',
                'access_token': page_access_token
            }
            
            ig_response = requests.get(ig_url, params=ig_params)
            
            if ig_response.status_code == 200:
                ig_data = ig_response.json()
                
                instagram_accounts.append({
                    'instagram_business_account_id': ig_id,
                    'username': ig_data.get('username', ''),
                    'name': ig_data.get('name', ''),
                    'profile_picture_url': ig_data.get('profile_picture_url', ''),
                    'followers_count': ig_data.get('followers_count', 0),
                    'follows_count': ig_data.get('follows_count', 0),
                    'media_count': ig_data.get('media_count', 0),
                    'page_id': page['id'],
                    'page_name': page.get('name', ''),
                    'page_access_token': page_access_token
                })
    
    return instagram_accounts


def save_incoming_message(message_data: dict):
    """Save incoming Instagram message to database"""
    messages_collection.insert_one({
        **message_data,
        'received_at': datetime.utcnow()
    })


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Instagram Business API Service",
        "version": "1.0.0",
        "endpoints": {
            "authorize": "/instagram/login - Start OAuth flow",
            "callback": "/instagram/callback - OAuth callback (automatic)",
            "status": "/instagram/status/{user_id} - Check connection status",
            "accounts": "/api/instagram-accounts/{user_id} - List Instagram accounts",
            "send_text": "/api/send-text - Send text message",
            "send_media": "/api/send-media - Send media message",
            "send_template": "/api/send-template - Send template/button message",
            "conversations": "/api/conversations/{instagram_account_id} - List conversations",
            "messages": "/api/messages/{instagram_account_id} - Get message history",
            "profile": "/api/profile/{instagram_account_id} - Get Instagram profile",
            "webhook": "/webhook - Instagram webhook endpoint"
        },
        "setup_instructions": {
            "step_1": "Configure META_APP_ID and META_APP_SECRET",
            "step_2": "Add Instagram product to your Meta App",
            "step_3": "Set REDIRECT_URI to match Meta App callback URL",
            "step_4": "Connect a Facebook Page to an Instagram Business Account",
            "step_5": "Visit /instagram/login to start the OAuth flow",
            "step_6": "Use /api/send-text to send messages"
        }
    }


@app.get("/instagram/login")
async def authorize():
    """
    Step 1: Redirect user to Facebook Login Dialog for Instagram permissions
    """
    auth_url = "https://www.facebook.com/v18.0/dialog/oauth"
    
    scope_string = ",".join(SCOPES)
    
    params = {
        'client_id': META_APP_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': scope_string,
        'response_type': 'code',
        'state': 'instagram_auth_state'
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_auth_url = f"{auth_url}?{query_string}"
    
    return RedirectResponse(url=full_auth_url)


@app.get("/instagram/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Step 2: Handle OAuth callback from Facebook
    """
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
        # Exchange code for token
        token_data = exchange_code_for_token(code)
        short_lived_token = token_data['access_token']
        
        # Get long-lived token
        long_lived_data = get_long_lived_token(short_lived_token)
        access_token = long_lived_data['access_token']
        expires_in = long_lived_data.get('expires_in', 5184000)
        
        # Get user info
        user_info = get_user_info(access_token)
        user_id = user_info['id']
        user_name = user_info.get('name', 'Unknown')
        
        # Get Instagram Business Accounts
        instagram_accounts = get_instagram_business_accounts(access_token)
        
        # Save to database
        user_data = {
            'user_name': user_name,
            'access_token': access_token,
            'token_expires_at': datetime.utcnow() + timedelta(seconds=expires_in),
            'instagram_accounts': instagram_accounts
        }
        
        save_user_tokens(user_id, user_data)
        
        return {
            "success": True,
            "message": "Instagram Business account connected successfully!",
            "user_id": user_id,
            "user_name": user_name,
            "instagram_accounts_connected": len(instagram_accounts),
            "accounts": [
                {
                    "instagram_business_account_id": acc['instagram_business_account_id'],
                    "username": acc['username'],
                    "name": acc['name'],
                    "profile_picture_url": acc.get('profile_picture_url', ''),
                    "followers_count": acc.get('followers_count', 0)
                }
                for acc in instagram_accounts
            ],
            "note": "Use instagram_business_account_id in API requests to send messages."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback error: {str(e)}")


@app.get("/instagram/status/{user_id}", response_model=UserConnectionStatus)
async def check_connection_status(user_id: str):
    """Check if a user is connected and get their Instagram accounts"""
    user_data = get_user_tokens(user_id)
    
    if not user_data:
        return UserConnectionStatus(connected=False)
    
    accounts = [
        InstagramAccount(
            instagram_business_account_id=acc['instagram_business_account_id'],
            username=acc['username'],
            name=acc['name'],
            profile_picture_url=acc.get('profile_picture_url'),
            page_id=acc['page_id']
        )
        for acc in user_data.get('instagram_accounts', [])
    ]
    
    return UserConnectionStatus(
        connected=True,
        user_id=user_data['user_id'],
        user_name=user_data.get('user_name'),
        instagram_accounts=accounts
    )


@app.get("/api/instagram-accounts/{user_id}")
async def list_instagram_accounts(user_id: str):
    """List all Instagram Business accounts for a user"""
    user_data = get_user_tokens(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please authorize at /instagram/login"
        )
    
    return {
        "user_id": user_id,
        "user_name": user_data.get('user_name'),
        "total_accounts": len(user_data.get('instagram_accounts', [])),
        "accounts": user_data.get('instagram_accounts', [])
    }


@app.get("/api/profile/{instagram_account_id}")
async def get_instagram_profile(instagram_account_id: str):
    """Get detailed Instagram Business profile information"""
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {instagram_account_id} not found"
        )
    
    try:
        access_token = decrypt_token(doc['access_token'])
    except:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    # Get Instagram profile details
    url = f"{GRAPH_API_URL}/{instagram_account_id}"
    params = {
        'fields': 'id,username,name,biography,profile_picture_url,followers_count,follows_count,media_count,website',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        error_msg = response.json().get('error', {}).get('message', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
    
    return response.json()


@app.post("/api/send-text", response_model=MessageResponse)
async def send_text_message(request: SendTextMessageRequest):
    """
    Send a text message via Instagram Direct
    
    - **recipient_id**: Instagram-scoped user ID (IGSID) of the recipient
    - **message**: The text message to send
    - **instagram_account_id**: Your Instagram Business Account ID
    
    Note: You can only message users who have messaged you first (within 24-hour window)
    or users who have opted in to receive messages.
    """
    # Find the Instagram account and get page access token
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': request.instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {request.instagram_account_id} not found. Please authorize at /instagram/login"
        )
    
    # Find the specific Instagram account to get page_id
    page_id = None
    page_access_token = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == request.instagram_account_id:
            page_id = acc['page_id']
            page_access_token = acc.get('page_access_token')
            break
    
    if not page_id:
        raise HTTPException(status_code=404, detail="Connected Facebook Page not found")
    
    if not page_access_token:
        try:
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    # Instagram Messaging API endpoint (uses the Page ID, not Instagram ID)
    send_url = f"{GRAPH_API_URL}/{request.instagram_account_id}/messages"
    
    headers = {
        'Authorization': f'Bearer {page_access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'recipient': {
            'id': request.recipient_id
        },
        'message': {
            'text': request.message
        }
    }
    
    try:
        response = requests.post(send_url, headers=headers, json=payload)
        result = response.json()
        
        if response.status_code == 200:
            message_id = result.get('message_id')
            return MessageResponse(
                success=True,
                message_id=message_id,
                recipient_id=request.recipient_id
            )
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            return MessageResponse(
                success=False,
                recipient_id=request.recipient_id,
                error=error_msg
            )
            
    except Exception as e:
        return MessageResponse(
            success=False,
            recipient_id=request.recipient_id,
            error=str(e)
        )


@app.post("/api/send-media", response_model=MessageResponse)
async def send_media_message(request: SendMediaMessageRequest):
    """
    Send a media message via Instagram Direct
    
    - **recipient_id**: Instagram-scoped user ID (IGSID)
    - **media_type**: Type of media ("image", "video", "audio", "file")
    - **media_url**: Public URL of the media file
    - **instagram_account_id**: Your Instagram Business Account ID
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': request.instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {request.instagram_account_id} not found"
        )
    
    # Find page access token
    page_access_token = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == request.instagram_account_id:
            page_access_token = acc.get('page_access_token')
            break
    
    if not page_access_token:
        try:
            page_id = acc['page_id']
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    send_url = f"{GRAPH_API_URL}/{request.instagram_account_id}/messages"
    
    headers = {
        'Authorization': f'Bearer {page_access_token}',
        'Content-Type': 'application/json'
    }
    
    # Map media types to Instagram attachment types
    attachment_type_map = {
        'image': 'image',
        'video': 'video',
        'audio': 'audio',
        'file': 'file'
    }
    
    attachment_type = attachment_type_map.get(request.media_type, 'image')
    
    payload = {
        'recipient': {
            'id': request.recipient_id
        },
        'message': {
            'attachment': {
                'type': attachment_type,
                'payload': {
                    'url': request.media_url
                }
            }
        }
    }
    
    try:
        response = requests.post(send_url, headers=headers, json=payload)
        result = response.json()
        
        if response.status_code == 200:
            message_id = result.get('message_id')
            return MessageResponse(
                success=True,
                message_id=message_id,
                recipient_id=request.recipient_id
            )
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            return MessageResponse(
                success=False,
                recipient_id=request.recipient_id,
                error=error_msg
            )
            
    except Exception as e:
        return MessageResponse(
            success=False,
            recipient_id=request.recipient_id,
            error=str(e)
        )


@app.post("/api/send-template", response_model=MessageResponse)
async def send_template_message(request: SendTemplateMessageRequest):
    """
    Send a template/structured message via Instagram Direct
    
    Supports generic templates with buttons and quick replies.
    
    - **recipient_id**: Instagram-scoped user ID (IGSID)
    - **template_type**: Type of template ("generic", "button")
    - **instagram_account_id**: Your Instagram Business Account ID
    - **elements**: Template elements (for generic template)
    - **buttons**: Quick reply buttons
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': request.instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {request.instagram_account_id} not found"
        )
    
    # Find page access token
    page_access_token = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == request.instagram_account_id:
            page_access_token = acc.get('page_access_token')
            break
    
    if not page_access_token:
        try:
            page_id = acc['page_id']
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    send_url = f"{GRAPH_API_URL}/{request.instagram_account_id}/messages"
    
    headers = {
        'Authorization': f'Bearer {page_access_token}',
        'Content-Type': 'application/json'
    }
    
    # Build template payload based on type
    if request.template_type == "generic" and request.elements:
        message_payload = {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': request.elements
                }
            }
        }
    elif request.buttons:
        # Quick replies
        message_payload = {
            'text': 'Please choose an option:',
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': btn.get('title', ''),
                    'payload': btn.get('payload', '')
                }
                for btn in request.buttons
            ]
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide elements for generic template or buttons for quick replies"
        )
    
    payload = {
        'recipient': {
            'id': request.recipient_id
        },
        'message': message_payload
    }
    
    try:
        response = requests.post(send_url, headers=headers, json=payload)
        result = response.json()
        
        if response.status_code == 200:
            message_id = result.get('message_id')
            return MessageResponse(
                success=True,
                message_id=message_id,
                recipient_id=request.recipient_id
            )
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            return MessageResponse(
                success=False,
                recipient_id=request.recipient_id,
                error=error_msg
            )
            
    except Exception as e:
        return MessageResponse(
            success=False,
            recipient_id=request.recipient_id,
            error=str(e)
        )


@app.get("/api/conversations/{instagram_account_id}")
async def get_conversations(instagram_account_id: str, limit: int = 20):
    """
    Get list of conversations for an Instagram Business account
    
    - **instagram_account_id**: Your Instagram Business Account ID
    - **limit**: Maximum conversations to return (default 20)
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {instagram_account_id} not found"
        )
    
    # Find page access token
    page_access_token = None
    page_id = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == instagram_account_id:
            page_access_token = acc.get('page_access_token')
            page_id = acc.get('page_id')
            break
    
    if not page_access_token:
        try:
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    # Get conversations via the Page's conversations endpoint
    url = f"{GRAPH_API_URL}/{instagram_account_id}/conversations"
    params = {
        'platform': 'instagram',
        'fields': 'participants,messages{message,from,created_time},updated_time',
        'limit': limit,
        'access_token': page_access_token
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    if response.status_code != 200:
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
    
    conversations = result.get('data', [])
    
    formatted_conversations = []
    for conv in conversations:
        participants = conv.get('participants', {}).get('data', [])
        messages = conv.get('messages', {}).get('data', [])
        
        formatted_conversations.append({
            'conversation_id': conv.get('id'),
            'participants': [
                {
                    'id': p.get('id'),
                    'name': p.get('name', 'Instagram User'),
                    'username': p.get('username', '')
                }
                for p in participants
            ],
            'last_message': messages[0] if messages else None,
            'updated_time': conv.get('updated_time')
        })
    
    return {
        "instagram_account_id": instagram_account_id,
        "total_conversations": len(formatted_conversations),
        "conversations": formatted_conversations
    }


@app.get("/api/messages/{instagram_account_id}")
async def get_messages(
    instagram_account_id: str,
    conversation_id: Optional[str] = None,
    limit: int = 50
):
    """
    Get message history for an Instagram Business account
    
    - **instagram_account_id**: Your Instagram Business Account ID
    - **conversation_id**: Optional - filter by specific conversation
    - **limit**: Maximum messages to return (default 50)
    """
    # Check for stored messages first
    query = {'instagram_account_id': instagram_account_id}
    
    if conversation_id:
        query['conversation_id'] = conversation_id
    
    messages = list(
        messages_collection.find(query)
        .sort('received_at', -1)
        .limit(limit)
    )
    
    # Convert ObjectId to string for JSON serialization
    for msg in messages:
        msg['_id'] = str(msg['_id'])
    
    return {
        "instagram_account_id": instagram_account_id,
        "conversation_filter": conversation_id,
        "total_messages": len(messages),
        "messages": messages
    }


@app.get("/api/ice-breakers/{instagram_account_id}")
async def get_ice_breakers(instagram_account_id: str):
    """
    Get configured ice breakers for an Instagram Business account
    
    Ice breakers are pre-set questions shown to users starting a new conversation.
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {instagram_account_id} not found"
        )
    
    # Find page access token
    page_access_token = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == instagram_account_id:
            page_access_token = acc.get('page_access_token')
            break
    
    if not page_access_token:
        try:
            page_id = acc['page_id']
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    url = f"{GRAPH_API_URL}/{instagram_account_id}/messenger_profile"
    params = {
        'fields': 'ice_breakers',
        'access_token': page_access_token
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    if response.status_code != 200:
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
    
    return {
        "instagram_account_id": instagram_account_id,
        "ice_breakers": result.get('data', [{}])[0].get('ice_breakers', [])
    }


@app.post("/api/ice-breakers/{instagram_account_id}")
async def set_ice_breakers(instagram_account_id: str, ice_breakers: List[IceBreaker]):
    """
    Set ice breakers for an Instagram Business account
    
    - **instagram_account_id**: Your Instagram Business Account ID
    - **ice_breakers**: List of ice breaker questions and payloads (max 4)
    """
    if len(ice_breakers) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 ice breakers allowed")
    
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {instagram_account_id} not found"
        )
    
    # Find page access token
    page_access_token = None
    for acc in doc.get('instagram_accounts', []):
        if acc['instagram_business_account_id'] == instagram_account_id:
            page_access_token = acc.get('page_access_token')
            break
    
    if not page_access_token:
        try:
            page_id = acc['page_id']
            user_access_token = decrypt_token(doc['access_token'])
            page_access_token = get_page_access_token(user_access_token, page_id)
        except:
            raise HTTPException(status_code=401, detail="Invalid access token")
    
    url = f"{GRAPH_API_URL}/{instagram_account_id}/messenger_profile"
    
    headers = {
        'Authorization': f'Bearer {page_access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'platform': 'instagram',
        'ice_breakers': [
            {'question': ib.question, 'payload': ib.payload}
            for ib in ice_breakers
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if response.status_code != 200:
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
    
    return {
        "success": True,
        "message": "Ice breakers updated successfully",
        "instagram_account_id": instagram_account_id
    }


@app.get("/webhook")
async def webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Webhook verification endpoint for Instagram
    
    Configure in Meta Developer Console:
    - Callback URL: https://your-domain/webhook
    - Verify Token: instagram_verify_token_123
    """
    if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
        print("✅ Instagram Webhook verified!")
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook_receive(request: Request):
    """
    Webhook endpoint to receive messages from Instagram
    
    When someone sends a message to your Instagram Business account,
    it will be received here.
    """
    try:
        body = await request.json()
        print(f"📩 Received Instagram webhook: {body}")
        
        # Process incoming messages
        if body.get('object') == 'instagram':
            for entry in body.get('entry', []):
                # Get Instagram account ID
                instagram_account_id = entry.get('id')
                
                # Process messaging events
                for messaging_event in entry.get('messaging', []):
                    sender_id = messaging_event.get('sender', {}).get('id')
                    recipient_id = messaging_event.get('recipient', {}).get('id')
                    timestamp = messaging_event.get('timestamp')
                    
                    # Handle different message types
                    message = messaging_event.get('message', {})
                    
                    if message:
                        message_id = message.get('mid')
                        
                        # Text message
                        if 'text' in message:
                            content = message['text']
                            message_type = 'text'
                        # Attachment (image, video, etc.)
                        elif 'attachments' in message:
                            attachments = message['attachments']
                            attachment = attachments[0] if attachments else {}
                            att_type = attachment.get('type', 'unknown')
                            att_url = attachment.get('payload', {}).get('url', '')
                            content = f"[{att_type.capitalize()}] {att_url}"
                            message_type = att_type
                        # Story mention
                        elif 'story_mention' in message:
                            content = "[Story Mention]"
                            message_type = 'story_mention'
                        # Story reply
                        elif 'reply_to' in message:
                            content = f"[Story Reply] {message.get('text', '')}"
                            message_type = 'story_reply'
                        else:
                            content = "[Unknown message type]"
                            message_type = 'unknown'
                        
                        print(f"📱 Instagram message from {sender_id}: {content}")
                        
                        # Save message to database
                        save_incoming_message({
                            'instagram_account_id': recipient_id,
                            'message_id': message_id,
                            'sender_id': sender_id,
                            'message_type': message_type,
                            'message': content,
                            'timestamp': timestamp,
                            'raw_message': message
                        })
                    
                    # Handle postback (button clicks)
                    postback = messaging_event.get('postback', {})
                    if postback:
                        payload = postback.get('payload', '')
                        title = postback.get('title', '')
                        print(f"🔘 Instagram postback from {sender_id}: {title} ({payload})")
                        
                        save_incoming_message({
                            'instagram_account_id': recipient_id,
                            'sender_id': sender_id,
                            'message_type': 'postback',
                            'message': f"[Button: {title}] {payload}",
                            'timestamp': timestamp,
                            'raw_message': postback
                        })
                    
                    # Handle reactions
                    reaction = messaging_event.get('reaction', {})
                    if reaction:
                        emoji = reaction.get('emoji', '')
                        action = reaction.get('action', '')
                        print(f"❤️ Instagram reaction from {sender_id}: {emoji} ({action})")
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/media/{instagram_account_id}")
async def get_media(instagram_account_id: str, limit: int = 25):
    """
    Get recent media posts from an Instagram Business account
    
    - **instagram_account_id**: Your Instagram Business Account ID
    - **limit**: Maximum media to return (default 25)
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {instagram_account_id} not found"
        )
    
    try:
        access_token = decrypt_token(doc['access_token'])
    except:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    url = f"{GRAPH_API_URL}/{instagram_account_id}/media"
    params = {
        'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count',
        'limit': limit,
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    if response.status_code != 200:
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"Graph API error: {error_msg}")
    
    return {
        "instagram_account_id": instagram_account_id,
        "total_media": len(result.get('data', [])),
        "media": result.get('data', [])
    }


@app.get("/api/connected-users")
async def list_connected_users():
    """List all connected Instagram Business accounts (Admin endpoint)"""
    try:
        users = list(collection.find({}, {'_id': 0, 'access_token': 0}))
        
        # Remove page_access_token from accounts for security
        for user in users:
            for acc in user.get('instagram_accounts', []):
                acc.pop('page_access_token', None)
        
        return {
            "total_users": len(users),
            "users": users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")


class UpdateTokenRequest(BaseModel):
    access_token: str
    instagram_account_id: str


@app.post("/api/update-token")
async def update_access_token(request: UpdateTokenRequest):
    """
    Manually update the access token for an Instagram account
    
    Use this to set the token generated from Meta Developer Console.
    
    - **access_token**: The access token from Meta Developer Console
    - **instagram_account_id**: Your Instagram Business Account ID
    """
    doc = collection.find_one({'instagram_accounts.instagram_business_account_id': request.instagram_account_id})
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Instagram account ID {request.instagram_account_id} not found"
        )
    
    # Update the access token
    encrypted_token = encrypt_token(request.access_token)
    
    collection.update_one(
        {'instagram_accounts.instagram_business_account_id': request.instagram_account_id},
        {
            '$set': {
                'access_token': encrypted_token,
                'updated_at': datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Access token updated successfully",
        "instagram_account_id": request.instagram_account_id
    }


@app.delete("/api/disconnect/{user_id}")
async def disconnect_user(user_id: str):
    """Disconnect a user and remove their stored tokens"""
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
    print("🚀 Starting Instagram Business API Service")
    print("=" * 60)
    print(f"📱 App ID: {META_APP_ID}")
    print(f"🔗 Callback URL: {REDIRECT_URI}")
    print(f"🔐 Webhook Verify Token: {VERIFY_TOKEN}")
    print("=" * 60)
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔄 ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    print("\n⚠️  Setup Requirements:")
    print("   1. Add 'Instagram' product to your Meta App")
    print("   2. Add 'Messenger' product (for Instagram messaging)")
    print("   3. Connect a Facebook Page to an Instagram Business/Creator Account")
    print("   4. Configure webhook URL in Meta Developer Console")
    print("   5. Subscribe to 'messages' webhook field for Instagram")
    print("\n📋 For Production (requires App Review):")
    print("   - instagram_basic")
    print("   - instagram_manage_messages")
    print("   - instagram_manage_comments")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
