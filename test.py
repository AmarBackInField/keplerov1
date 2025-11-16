import asyncio
from livekit.api import LiveKitAPI, ListRoomsRequest, DeleteRoomRequest

async def delete_all_rooms():
    # Your LiveKit credentials
    LIVEKIT_URL = "wss://incruiter-kcxtv094.livekit.cloud"
    LIVEKIT_API_KEY = "APISLfT6uXeNgs9"
    LIVEKIT_API_SECRET = "oe2moextGRiwwqxfDpZdZU7taFgsXQXFVY0MOoeSaazA"
    
    # Initialize LiveKit API
    async with LiveKitAPI(
        LIVEKIT_URL,
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET
    ) as lkapi:
        try:
            # List all active rooms
            print("Fetching all active rooms...")
            response = await lkapi.room.list_rooms(ListRoomsRequest())
            rooms = response.rooms  # Access the .rooms attribute
            
            if not rooms:
                print("No active rooms found.")
                return
            
            print(f"\nFound {len(rooms)} active room(s):")
            for room in rooms:
                print(f"  - {room.name} (SID: {room.sid}, Participants: {room.num_participants})")
            
            # Confirm deletion
            print("\n⚠️  WARNING: This will delete ALL rooms and disconnect all participants!")
            confirm = input("Type 'DELETE' to confirm: ")
            
            if confirm != "DELETE":
                print("Deletion cancelled.")
                return
            
            # Delete each room
            print("\nDeleting rooms...")
            deleted_count = 0
            failed_count = 0
            
            for room in rooms:
                try:
                    await lkapi.room.delete_room(DeleteRoomRequest(room=room.name))
                    print(f"  ✓ Deleted: {room.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ✗ Failed to delete {room.name}: {e}")
                    failed_count += 1
            
            print(f"\n{'='*50}")
            print(f"Summary:")
            print(f"  Successfully deleted: {deleted_count}")
            print(f"  Failed: {failed_count}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(delete_all_rooms())