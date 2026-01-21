# Gmail FastAPI Service

A FastAPI-based service for Gmail operations including custom emailing, email searching, and thread retrieval.

## Features

1. **Custom Emailing** - Send emails with custom recipients, subject, body, CC, and BCC
2. **Email Searching** - Search emails using Gmail query syntax
3. **Thread Retrieval** - Retrieve n last threads with full message content

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop App)
5. Download the credentials and save as `credentials.json` in the project directory

### 3. Environment Variables (Optional)

Create a `.env` file:

```env
ENCRYPTION_KEY=your_encryption_key_here
MONGODB_URI=your_mongodb_connection_string
```

## Running the Service

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication Flow

### Step 1: Authorize a Gmail Account

Visit: `http://localhost:8000/authorize`

This will redirect you to Google's OAuth page. After authorization, you'll receive your user email.

### Step 2: Use the Email in API Requests

Include the email as a header in all API requests:

```
X-User-Email: your-email@gmail.com
```

## API Endpoints

### 1. Send Custom Email

**POST** `/api/send-email`

**Headers:**
```
X-User-Email: your-email@gmail.com
Content-Type: application/json
```

**Body:**
```json
{
  "to": "recipient@example.com",
  "subject": "Test Email",
  "body": "This is a test email from FastAPI",
  "cc": ["cc1@example.com", "cc2@example.com"],  // Optional
  "bcc": ["bcc1@example.com"]  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "18d1234567890abc",
  "thread_id": "18d1234567890abc",
  "message": "Email sent successfully to recipient@example.com"
}
```

### 2. Search Emails

**POST** `/api/search-emails`

**Headers:**
```
X-User-Email: your-email@gmail.com
Content-Type: application/json
```

**Body:**
```json
{
  "query": "from:someone@example.com subject:important",
  "max_results": 10
}
```

**Gmail Query Examples:**
- `from:user@example.com` - Emails from specific sender
- `subject:meeting` - Emails with "meeting" in subject
- `is:unread` - Unread emails
- `has:attachment` - Emails with attachments
- `after:2024/01/01` - Emails after specific date
- `to:me cc:boss@example.com` - Complex queries

**Response:**
```json
{
  "query": "from:someone@example.com",
  "total_results": 5,
  "emails": [
    {
      "id": "18d1234567890abc",
      "thread_id": "18d1234567890abc",
      "sender": "someone@example.com",
      "subject": "Important Update",
      "date": "Mon, 18 Jan 2026 10:30:00 +0000",
      "snippet": "This is a preview of the email content...",
      "body": "Full email body content..."
    }
  ]
}
```

### 3. Retrieve Last N Threads

**POST** `/api/get-threads`

**Headers:**
```
X-User-Email: your-email@gmail.com
Content-Type: application/json
```

**Body:**
```json
{
  "n": 10
}
```

**Response:**
```json
[
  {
    "thread_id": "18d1234567890abc",
    "message_count": 3,
    "messages": [
      {
        "id": "18d1234567890abc",
        "thread_id": "18d1234567890abc",
        "sender": "user1@example.com",
        "subject": "Discussion Thread",
        "date": "Mon, 18 Jan 2026 10:30:00 +0000",
        "snippet": "First message in thread...",
        "body": "Full body of first message..."
      },
      {
        "id": "18d1234567890def",
        "thread_id": "18d1234567890abc",
        "sender": "user2@example.com",
        "subject": "Re: Discussion Thread",
        "date": "Mon, 18 Jan 2026 11:00:00 +0000",
        "snippet": "Reply to first message...",
        "body": "Full body of second message..."
      }
    ]
  }
]
```

### 4. Get Specific Thread Details

**GET** `/api/get-thread/{thread_id}`

**Headers:**
```
X-User-Email: your-email@gmail.com
```

**Response:**
```json
{
  "thread_id": "18d1234567890abc",
  "message_count": 2,
  "messages": [
    {
      "id": "18d1234567890abc",
      "thread_id": "18d1234567890abc",
      "sender": "user@example.com",
      "subject": "Subject",
      "date": "Mon, 18 Jan 2026 10:30:00 +0000",
      "snippet": "Preview...",
      "body": "Full message body..."
    }
  ]
}
```

### 5. List Connected Users (Admin)

**GET** `/api/connected-users`

**Response:**
```json
{
  "total_users": 3,
  "users": [
    {
      "user_email": "user1@gmail.com",
      "created_at": "2026-01-18T10:00:00"
    }
  ]
}
```

## Example Usage with cURL

### Send Email
```bash
curl -X POST "http://localhost:8000/api/send-email" \
  -H "X-User-Email: your-email@gmail.com" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Hello from FastAPI",
    "body": "This is a test email"
  }'
```

### Search Emails
```bash
curl -X POST "http://localhost:8000/api/search-emails" \
  -H "X-User-Email: your-email@gmail.com" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "is:unread",
    "max_results": 5
  }'
```

### Get Last 10 Threads
```bash
curl -X POST "http://localhost:8000/api/get-threads" \
  -H "X-User-Email: your-email@gmail.com" \
  -H "Content-Type: application/json" \
  -d '{
    "n": 10
  }'
```

## Example Usage with Python

```python
import requests

BASE_URL = "http://localhost:8000"
USER_EMAIL = "your-email@gmail.com"
HEADERS = {
    "X-User-Email": USER_EMAIL,
    "Content-Type": "application/json"
}

# Send Email
response = requests.post(
    f"{BASE_URL}/api/send-email",
    headers=HEADERS,
    json={
        "to": "recipient@example.com",
        "subject": "Test Email",
        "body": "Hello from Python!"
    }
)
print(response.json())

# Search Emails
response = requests.post(
    f"{BASE_URL}/api/search-emails",
    headers=HEADERS,
    json={
        "query": "from:important@example.com",
        "max_results": 10
    }
)
print(response.json())

# Get Last 5 Threads
response = requests.post(
    f"{BASE_URL}/api/get-threads",
    headers=HEADERS,
    json={"n": 5}
)
print(response.json())
```

## Security Notes

1. **Never commit** `credentials.json` or `.env` files to version control
2. Store `ENCRYPTION_KEY` securely in environment variables
3. Use HTTPS in production
4. Implement proper authentication/authorization for production use
5. Set `OAUTHLIB_INSECURE_TRANSPORT=0` in production

## Production Deployment

For production:

1. Set environment variables properly
2. Use a production WSGI server
3. Enable HTTPS
4. Add proper authentication middleware
5. Implement rate limiting
6. Add logging and monitoring

```bash
# Production run example
export OAUTHLIB_INSECURE_TRANSPORT=0
export ENCRYPTION_KEY=your_secure_key
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Troubleshooting

### OAuth Errors
- Ensure `credentials.json` is in the correct location
- Check that Gmail API is enabled in Google Cloud Console
- Verify redirect URI matches in both code and Google Console

### Database Errors
- Check MongoDB connection string
- Ensure network access is allowed in MongoDB Atlas

### Token Expired
- The system automatically refreshes expired tokens
- If issues persist, re-authorize at `/authorize`

## License

MIT License
