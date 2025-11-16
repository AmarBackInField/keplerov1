import asyncio
from livekit import api
from dotenv import load_dotenv
import os

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

AGENT_IDENTITY = os.getenv("PARTICIPANT_IDENTITY", "agent")  # your agent’s identity

async def main():
    client = api.LiveKitAPI(
        LIVEKIT_URL,
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET
    )

    print("\n=============================")
    print("📡 LIVEKIT STATUS DASHBOARD")
    print("=============================\n")

    # 1. List Rooms
    rooms = await client.room.list_rooms(api.ListRoomsRequest())
    print(f"🏠 Total Active Rooms: {len(rooms.rooms)}\n")

    for room in rooms.rooms:
        print(f"--- Room: {room.name} ---")
        print(f"• Creation Time: {room.creation_time}")
        print(f"• Turn: {room.turn_password}")
        
        # 2. List Participants
        participants = await client.room.list_participants(
            api.ListParticipantsRequest(room=room.name)
        )

        print(f"👥 Participants: {len(participants.participants)}")

        agent_found = False

        for p in participants.participants:
            print(f"   - {p.identity} ({p.sid})")
            if p.identity == AGENT_IDENTITY:
                agent_found = True

        if agent_found:
            print("   ✔ Agent is ACTIVE in this room\n")
        else:
            print("   ❌ Agent NOT found in this room\n")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
