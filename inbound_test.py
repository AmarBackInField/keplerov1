import os
import asyncio
from datetime import datetime
from livekit import api
from dotenv import load_dotenv

load_dotenv()

async def monitor_calls():
    """Monitor rooms in real-time to see when calls come in."""
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET")
    )
    
    try:
        print("=" * 70)
        print("LIVEKIT CALL MONITOR - Real-time Room Detection")
        print("=" * 70)
        print(f"Server: {os.getenv('LIVEKIT_URL')}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Check dispatch rules first
        print("\n📋 Checking SIP Configuration...")
        try:
            dispatch_rules = await livekit_api.sip.list_sip_dispatch_rule(
                api.ListSIPDispatchRuleRequest()
            )
            
            if len(dispatch_rules.items) == 0:
                print("⚠ No dispatch rules found!")
            else:
                for rule in dispatch_rules.items:
                    print(f"\n✓ Dispatch Rule: {rule.name}")
                    print(f"   Room Pattern: {rule.room_prefix}<caller>{rule.room_suffix}")
                    print(f"   Target Agent: {rule.agent_name or 'NONE SPECIFIED'}")
                    
                    if not rule.agent_name:
                        print("   ⚠ WARNING: No agent assigned to this rule!")
                    elif rule.agent_name != "inbound-agent":
                        print(f"   ⚠ WARNING: Agent name is '{rule.agent_name}', expected 'inbound-agent'")
        except Exception as e:
            print(f"⚠ Could not check dispatch rules: {e}")
        
        # Check SIP trunks
        print("\n📞 Checking SIP Trunks...")
        try:
            trunks = await livekit_api.sip.list_sip_trunk(
                api.ListSIPTrunkRequest()
            )
            
            if len(trunks.items) == 0:
                print("⚠ No SIP trunks found!")
            else:
                for trunk in trunks.items:
                    print(f"\n✓ SIP Trunk: {trunk.name}")
                    print(f"   Numbers: {trunk.numbers if trunk.numbers else 'None'}")
                    print(f"   Trunk ID: {trunk.sip_trunk_id}")
        except Exception as e:
            print(f"⚠ Could not check trunks: {e}")
        
        # Initial room check
        print("\n" + "=" * 70)
        print("Checking for Active Rooms...")
        print("=" * 70)
        
        rooms = await livekit_api.room.list_rooms(api.ListRoomsRequest())
        
        if len(rooms.rooms) == 0:
            print("No active rooms currently")
        else:
            print(f"Found {len(rooms.rooms)} active room(s):")
            for room in rooms.rooms:
                print(f"\n  Room: {room.name}")
                print(f"    Participants: {room.num_participants}")
                print(f"    Created: {room.creation_time}")
        
        # Start monitoring
        print("\n" + "=" * 70)
        print("🔴 MONITORING STARTED - Waiting for incoming calls...")
        print("=" * 70)
        print("Instructions:")
        print("  1. Make sure your agent is running: python agent_service.py")
        print("  2. Dial: +390620199287")
        print("  3. Watch for room creation and participant join events below")
        print("\nPress Ctrl+C to stop monitoring\n")
        
        seen_rooms = {room.name for room in rooms.rooms}
        
        while True:
            await asyncio.sleep(2)
            
            current_rooms = await livekit_api.room.list_rooms(api.ListRoomsRequest())
            
            # Check for new rooms
            for room in current_rooms.rooms:
                if room.name not in seen_rooms:
                    print("\n" + "🔔" * 35)
                    print(f"NEW CALL DETECTED: {room.name}")
                    print("🔔" * 35)
                    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Get detailed participant info
                    try:
                        participants = await livekit_api.room.list_participants(
                            api.ListParticipantsRequest(room=room.name)
                        )
                        
                        print(f"\nParticipants ({len(participants.participants)}):")
                        
                        agent_found = False
                        sip_found = False
                        
                        for p in participants.participants:
                            identity = p.identity
                            kind = p.kind.name if hasattr(p.kind, 'name') else str(p.kind)
                            
                            print(f"  • {identity}")
                            print(f"      Kind: {kind}")
                            print(f"      Name: {p.name}")
                            print(f"      State: {p.state.name if hasattr(p.state, 'name') else p.state}")
                            
                            if "agent" in identity.lower():
                                agent_found = True
                            if identity == "sip-caller":
                                sip_found = True
                        
                        print("\n" + "-" * 70)
                        if sip_found and agent_found:
                            print("✅ SUCCESS: Both SIP caller and agent are in the room!")
                            print("   Your agent should now be handling the call.")
                        elif sip_found and not agent_found:
                            print("❌ PROBLEM: SIP caller joined but NO AGENT detected!")
                            print("\nTroubleshooting:")
                            print("   1. Is agent_service.py running? Check that terminal.")
                            print("   2. Check agent logs for 'ENTRYPOINT TRIGGERED'")
                            print("   3. Verify agent_name='inbound-agent' in your code")
                            print("   4. Check dispatch rule points to correct agent name")
                        elif not sip_found:
                            print("⚠ Room created but no SIP participant yet...")
                        
                        print("-" * 70 + "\n")
                        
                    except Exception as e:
                        print(f"⚠ Could not get participant details: {e}")
                    
                    seen_rooms.add(room.name)
            
            # Check for closed rooms
            current_room_names = {room.name for room in current_rooms.rooms}
            closed_rooms = seen_rooms - current_room_names
            
            if closed_rooms:
                for room_name in closed_rooms:
                    print(f"\n📴 Call ended: {room_name}")
                    seen_rooms.remove(room_name)
                
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Monitoring stopped by user")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await livekit_api.aclose()

if __name__ == "__main__":
    asyncio.run(monitor_calls())