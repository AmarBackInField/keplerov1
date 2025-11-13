# Dynamic Configuration System

## Overview

This system separates **static** credentials (API keys, URLs) from **dynamic** call parameters (caller name, instructions, TTS settings) for better flexibility and production readiness.

### Architecture

```
┌─────────────────────┐
│  FastAPI Endpoint   │
│   /outbound         │
└──────────┬──────────┘
           │
           ├─ 1. update_config.json (async)
           │
           ├─ 2. trigger outbound call
           │
           ▼
┌─────────────────────┐
│  LiveKit Agent      │
│  (agent_service.py) │
└──────────┬──────────┘
           │
           ├─ 3. load_dynamic_config()
           │
           ▼
      Uses latest config values
      for the call session
```

## File Structure

```
project_root/
├── .env                    # Static credentials only (API keys, URLs)
├── config.json             # Dynamic parameters (auto-generated, updated per call)
├── routers/
│   └── calls.py            # FastAPI endpoints (calls update_dynamic_config)
└── voice_backend/
    └── outboundService/
        ├── common/
        │   └── update_config.py  # Config management utilities
        └── services/
            └── agent_service.py  # Agent entrypoint (loads config.json)
```

## Configuration Separation

### Static Config (.env)
**These values rarely change and contain sensitive credentials:**

```env
# LiveKit Credentials
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here

# OpenAI/Deepgram/Cartesia API Keys
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...

# Other service credentials
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
```

### Dynamic Config (config.json)
**These values change with each call:**

```json
{
    "caller_name": "John Doe",
    "agent_instructions": "You are a helpful voice AI assistant. The caller's name is John Doe, address them by name.",
    "tts_language": "en",
    "tts_emotion": "Calm",
    "last_updated": 1699999999.123
}
```

## Usage

### 1. API Endpoint (FastAPI)

The `/outbound` endpoint automatically updates `config.json` before triggering the call:

```python
from voice_backend.outboundService.common.update_config import update_config_async

@router.post("/outbound")
async def outbound_call(request: OutboundCallRequest):
    # Update config.json with call-specific parameters
    await update_config_async(
        caller_name=request.name,
        agent_instructions=request.dynamic_instruction,
        tts_language=request.language,
        tts_emotion=request.emotion
    )
    
    # Trigger the call
    await make_outbound_call(phone_number=request.phone_number)
    
    return {"status": "success"}
```

### 2. Agent Service (LiveKit)

The agent service loads the latest config on each room connection:

```python
from common.update_config import load_dynamic_config

async def entrypoint(ctx: agents.JobContext):
    # Load latest dynamic config
    config = load_dynamic_config()
    
    caller_name = config.get("caller_name", "Guest")
    instructions = config.get("agent_instructions", "You are a helpful assistant.")
    language = config.get("tts_language", "en")
    emotion = config.get("tts_emotion", "Calm")
    
    # Use config values for TTS and agent initialization
    tts = cartesia.TTS(language=language, emotion=emotion)
    assistant = Assistant(instructions=instructions)
    
    # ... rest of agent setup
```

### 3. Making API Calls

#### Example 1: Simple Outbound Call

```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "name": "Alice Smith",
    "dynamic_instruction": "You are a cricket coach. Help the caller improve their batting technique.",
    "language": "en",
    "emotion": "Excited"
  }'
```

#### Example 2: Spanish Call with Custom Emotion

```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+34612345678",
    "name": "Carlos García",
    "dynamic_instruction": "Eres un asistente de ventas. Ayuda al cliente con su pedido.",
    "language": "es",
    "emotion": "Calm"
  }'
```

#### Example 3: Using Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/calls/outbound",
    json={
        "phone_number": "+441234567890",
        "name": "Emma Watson",
        "dynamic_instruction": "You are a customer support agent helping with a technical issue.",
        "language": "en",
        "emotion": "Serious"
    }
)

print(response.json())
```

## API Reference

### update_config_async()

Updates the dynamic configuration file asynchronously.

**Parameters:**
- `caller_name` (str, optional): Name of the person being called
- `agent_instructions` (str, optional): Custom instructions for the AI agent
- `tts_language` (str): TTS language code (default: "en")
- `tts_emotion` (str): TTS emotion setting (default: "Calm")
- `additional_params` (dict, optional): Any additional parameters to store

**Returns:** Dict containing the updated configuration

**Example:**
```python
config = await update_config_async(
    caller_name="John Doe",
    agent_instructions="You are a sales assistant.",
    tts_language="en",
    tts_emotion="Excited",
    additional_params={"campaign_id": "CAMP123"}
)
```

### load_dynamic_config()

Loads the current dynamic configuration from config.json.

**Returns:** Dict containing the configuration parameters

**Example:**
```python
config = load_dynamic_config()
caller_name = config.get("caller_name", "Guest")
instructions = config.get("agent_instructions", "Default instructions")
```

### get_config_value()

Gets a specific value from the dynamic configuration.

**Parameters:**
- `key` (str): The configuration key to retrieve
- `default` (any): Default value if key not found

**Returns:** The configuration value or default

**Example:**
```python
emotion = get_config_value("tts_emotion", default="Calm")
```

## Supported TTS Languages

- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `nl` - Dutch
- `pl` - Polish
- `ja` - Japanese
- `zh` - Chinese
- And more...

## Supported TTS Emotions

- `Calm` - Professional and composed
- `Excited` - Energetic and enthusiastic
- `Serious` - Formal and authoritative
- `Friendly` - Warm and approachable
- `Empathetic` - Caring and understanding
- `Neutral` - Balanced and objective

## Error Handling

The system includes comprehensive error handling:

1. **Config file not found**: Automatically creates with defaults
2. **Invalid JSON**: Logs error and uses fallback defaults
3. **Thread safety**: Uses locks to prevent race conditions
4. **Async safety**: Non-blocking operations for FastAPI

## Production Considerations

### Thread Safety
The system uses thread locks (`threading.Lock`) to ensure safe concurrent writes to config.json.

### Async Safety
Both sync and async versions of functions are provided:
- `update_config()` / `update_config_async()`
- `load_dynamic_config()` / `load_dynamic_config_async()`
- `get_config_value()` / `get_config_value_async()`

### Auto-initialization
The config file is automatically created with sensible defaults if it doesn't exist.

### Logging
All operations are logged with clear success/failure indicators:
```
✓ Configuration updated successfully
  - Caller Name: John Doe
  - TTS Language: en
  - TTS Emotion: Calm
```

## Troubleshooting

### Config not updating between calls

**Problem:** Agent uses old configuration values.

**Solution:** 
1. Check that `config.json` exists in project root
2. Verify the agent calls `load_dynamic_config()` in the entrypoint
3. Ensure the API endpoint calls `update_config_async()` before triggering the call

### Permission errors

**Problem:** Cannot write to config.json.

**Solution:**
```bash
# Ensure proper permissions
chmod 644 config.json

# Check file ownership
ls -la config.json
```

### Config file location

The config file is located at: `project_root/config.json`

To verify:
```python
from pathlib import Path
print(Path(__file__).parent.parent.parent.parent / "config.json")
```

## Migration from .env

If you're migrating from the old .env-based system:

1. **Keep** these in .env (static credentials):
   - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
   - OPENAI_API_KEY, DEEPGRAM_API_KEY, etc.
   - Database URLs, service endpoints

2. **Remove** these from .env (now in config.json):
   - AGENT_INSTRUCTIONS
   - CALLER_NAME
   - TTS_LANGUAGE
   - TTS_EMOTION

3. The first call will automatically create `config.json` with defaults.

## Testing

### Unit Tests

```python
import pytest
from voice_backend.outboundService.common.update_config import (
    update_config, load_dynamic_config
)

def test_update_and_load_config():
    # Update config
    config = update_config(
        caller_name="Test User",
        agent_instructions="Test instructions",
        tts_language="en",
        tts_emotion="Calm"
    )
    
    assert config["caller_name"] == "Test User"
    
    # Load config
    loaded = load_dynamic_config()
    assert loaded["caller_name"] == "Test User"
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_outbound_call_updates_config():
    response = client.post("/calls/outbound", json={
        "phone_number": "+1234567890",
        "name": "Test User",
        "language": "en",
        "emotion": "Calm"
    })
    
    assert response.status_code == 200
    
    # Verify config was updated
    from voice_backend.outboundService.common.update_config import load_dynamic_config
    config = load_dynamic_config()
    assert config["caller_name"] == "Test User"
```

## Best Practices

1. **Always update config before triggering calls**: Ensure `update_config_async()` is called before `make_outbound_call()`

2. **Use async versions in FastAPI endpoints**: Use `update_config_async()` and `load_dynamic_config_async()` in async endpoints

3. **Validate input before updating config**: Validate phone numbers and other inputs before updating configuration

4. **Log configuration updates**: Always log when config is updated for debugging

5. **Handle errors gracefully**: Use try-except blocks around config operations with sensible fallbacks

6. **Keep .env secure**: Never commit .env files to version control

7. **Monitor config.json size**: If storing additional parameters, be mindful of file size

## Advanced Usage

### Storing Additional Parameters

```python
await update_config_async(
    caller_name="John Doe",
    agent_instructions="Custom instructions",
    additional_params={
        "campaign_id": "SUMMER2024",
        "customer_tier": "Premium",
        "call_purpose": "Product Demo",
        "previous_interactions": 3
    }
)
```

### Reading Additional Parameters in Agent

```python
config = load_dynamic_config()
campaign_id = config.get("campaign_id", "DEFAULT")
customer_tier = config.get("customer_tier", "Standard")

# Adjust agent behavior based on tier
if customer_tier == "Premium":
    instructions += " Provide priority support with personalized recommendations."
```

## Support

For issues or questions:
1. Check logs in `agent_debug.log`
2. Verify `config.json` contents
3. Test with minimal configuration first
4. Review error messages in API responses

## License

This configuration system is part of the Island AI voice backend service.

