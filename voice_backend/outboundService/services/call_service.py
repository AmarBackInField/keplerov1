import asyncio
import time
import uuid
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest
import os
import json
# Configuration
SIP_TRUNK_ID = "ST_vEtSehKXAp4d"
PARTICIPANT_IDENTITY = "sip-caller"
PARTICIPANT_NAME = "Phone Caller"
CALL_TIMEOUT = 60
from dotenv import load_dotenv
load_dotenv()
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
print("LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET:", LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

async def make_outbound_call(
    phone_number: str,
    sip_trunk_id: str = SIP_TRUNK_ID,
    room_name: str = None,
    user_id: str = None
):
    """
    Make an outbound call to the specified phone number.
    Creates a unique room for each call.
    
    Args:
        phone_number: The phone number to call (e.g., "+1234567890")
        sip_trunk_id: SIP trunk ID
        room_name: Optional room name (generates unique one if not provided)
        user_id: Optional user ID for multi-tenant config isolation
    
    Returns:
        tuple: (participant_info, room_name) if successful
    """
    # Generate unique room name if not provided
    if not room_name:
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        room_name = f"outbound-call-{timestamp}-{unique_id}"
    
    print("=" * 60)
    print("INITIATING OUTBOUND CALL")
    print("=" * 60)
    print(f"📱 Phone Number: {phone_number}")
    print(f"🏠 Room Name: {room_name}")
    print(f"📡 SIP Trunk: {sip_trunk_id}")
    if user_id:
        print(f"👤 User ID (multi-tenant): {user_id}")
    print("=" * 60)
    print("LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET:", LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    # Connect to LiveKit API
    print("Connecting to LiveKit API...")
    livekit_api = api.LiveKitAPI(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET, url=LIVEKIT_URL)
    
    # Build room metadata with user_id for multi-tenant support
    room_metadata = {"agent_name": "voice-assistant"}
    if user_id:
        room_metadata["user_id"] = user_id
    
    # Create the room first (optional but recommended)
    try:
        print(f"Creating room: {room_name}")
        await livekit_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                empty_timeout=60,  # Room closes after 60 seconds if empty
                max_participants=10,
                metadata=json.dumps(room_metadata)
            )
        )
        print(f"✓ Room created: {room_name}")
    except Exception as e:
        print(f"Note: Room creation message: {e}")
        # Room might already exist, continue anyway
    
    # Wait a moment for the agent to connect to the room
    print("Waiting for agent to join room...")
    await asyncio.sleep(3)
    
    # Create SIP participant request
    request = CreateSIPParticipantRequest(
        sip_trunk_id=sip_trunk_id,
        sip_call_to=phone_number,
        room_name=room_name,
        participant_identity=PARTICIPANT_IDENTITY,
        participant_name=PARTICIPANT_NAME,
        krisp_enabled=True,
        wait_until_answered=True
    )
    
    try:
        print(f"📱 Calling {phone_number}...")
        
        start_time = time.time()
        participant = await livekit_api.sip.create_sip_participant(request)
        connection_time = time.time() - start_time
        
        print(f"✓ Call connected in {connection_time:.2f} seconds")
        print(f"* Participant ID: {participant.participant_id}")
        print(f"* SIP Call ID: {participant.sip_call_id}")
        print(f"* Room: {participant.room_name}")
        print("-" * 60)
        print("✓ Call is active - AI assistant should be speaking")
        print("=" * 60)
        
        return participant, room_name
        
    except Exception as e:
        print(f"✗ Error creating SIP participant: {e}")
        print("⚠ Troubleshooting checklist:")
        print("   1. Verify agent is running: python outbound_agent.py")
        print("   2. Check SIP trunk ID is correct")
        print("   3. Verify phone number format: +[country][number]")
        print("   4. Confirm LiveKit credentials in .env")
        print("   5. Check SIP trunk is properly configured")
        raise
    finally:
        await livekit_api.aclose()


async def make_multiple_calls(
    phone_numbers: list,
    delay_seconds: int = 30,
    sip_trunk_id: str = SIP_TRUNK_ID
):
    """
    Make multiple outbound calls with delay between each.
    
    Args:
        phone_numbers: List of phone numbers to call
        delay_seconds: Delay between calls in seconds
        sip_trunk_id: SIP trunk ID
    """
    print(f"Starting campaign: {len(phone_numbers)} calls")
    print(f"Delay between calls: {delay_seconds} seconds")
    print("=" * 60)
    
    results = []
    
    for i, phone_number in enumerate(phone_numbers, 1):
        print(f"\nCall {i}/{len(phone_numbers)}")
        
        try:
            participant, room = await make_outbound_call(
                phone_number=phone_number,
                sip_trunk_id=sip_trunk_id
            )
            results.append({
                "phone_number": phone_number,
                "status": "success",
                "room": room,
                "participant_id": participant.participant_id
            })
        except Exception as e:
            results.append({
                "phone_number": phone_number,
                "status": "failed",
                "error": str(e)
            })
        
        # Wait before next call (except after last call)
        if i < len(phone_numbers):
            print(f"Waiting {delay_seconds} seconds before next call...")
            await asyncio.sleep(delay_seconds)
    
    # Print summary
    print("\n" + "=" * 60)
    print("CAMPAIGN SUMMARY")
    print("=" * 60)
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"Total calls: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    return results


# Example usage
if __name__ == "__main__":
    # Single call example
    async def single_call_example():
        await make_outbound_call("+1234567890")
    
    # Multiple calls example
    async def multiple_calls_example():
        contacts = [
            "+1234567890",
            "+0987654321",
        ]
        await make_multiple_calls(contacts, delay_seconds=30)
    
    # Run single call
    asyncio.run(single_call_example())
    
    # Or run multiple calls
    # asyncio.run(multiple_calls_example())