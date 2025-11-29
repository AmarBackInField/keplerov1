import asyncio
import os
from livekit import api
from dotenv import load_dotenv

load_dotenv()

async def main():
    lk_api = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET")
    )
    
    print("=" * 60)
    print("CHECKING SIP CONFIGURATION")
    print("=" * 60)
    print(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    print()
    
    # List all SIP trunks
    print("📞 SIP INBOUND TRUNKS:")
    print("-" * 60)
    try:
        response = await lk_api.sip.list_sip_inbound_trunk(api.ListSIPInboundTrunkRequest())
        if not response.items:
            print("  ⚠️  No trunks found!")
        for trunk in response.items:
            print(f"  ✓ Trunk ID: {trunk.sip_trunk_id}")
            print(f"    Name: {trunk.name}")
            print(f"    Numbers: {list(trunk.numbers)}")
            print(f"    Allowed Numbers: {list(trunk.allowed_numbers)}")
            print(f"    Krisp Enabled: {trunk.krisp_enabled}")
            print()
    except Exception as e:
        print(f"  ❌ Error listing trunks: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # List all dispatch rules
    print("📋 SIP DISPATCH RULES:")
    print("-" * 60)
    try:
        response = await lk_api.sip.list_sip_dispatch_rule(api.ListSIPDispatchRuleRequest())
        if not response.items:
            print("  ⚠️  No dispatch rules found!")
        for rule in response.items:
            print(f"  ✓ Rule ID: {rule.sip_dispatch_rule_id}")
            print(f"    Name: {rule.name}")
            print(f"    Trunk IDs: {list(rule.trunk_ids)}")
            if rule.rule.HasField('dispatch_rule_direct'):
                direct = rule.rule.dispatch_rule_direct
                print(f"    Type: Direct Dispatch")
                print(f"    Room Name: {direct.room_name}")
                print(f"    Pin: {direct.pin if direct.pin else 'None'}")
            elif rule.rule.HasField('dispatch_rule_individual'):
                print(f"    Type: Individual Dispatch")
                print(f"    Room Prefix: {rule.rule.dispatch_rule_individual.room_prefix}")
            print()
    except Exception as e:
        print(f"  ❌ Error listing dispatch rules: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 60)
    print("CHECKING YOUR LOCAL CONFIG FILES:")
    print("=" * 60)
    
    # Check local config files
    import json
    from pathlib import Path
    
    inbound_trunk_file = Path(__file__).parent.parent.parent.parent / "inbound-trunk.json"
    dispatch_rule_file = Path(__file__).parent.parent.parent.parent / "dispatch-rule.json"
    
    if inbound_trunk_file.exists():
        with open(inbound_trunk_file) as f:
            trunk_config = json.load(f)
        print(f"📄 inbound-trunk.json:")
        print(f"    {json.dumps(trunk_config, indent=2)}")
        print()
    
    if dispatch_rule_file.exists():
        with open(dispatch_rule_file) as f:
            dispatch_config = json.load(f)
        print(f"📄 dispatch-rule.json:")
        print(f"    Trunk IDs: {dispatch_config['dispatch_rule']['trunk_ids']}")
        if 'dispatchRuleDirect' in dispatch_config['dispatch_rule']['rule']:
            room_name = dispatch_config['dispatch_rule']['rule']['dispatchRuleDirect']['roomName']
            print(f"    Room Name: {room_name}")
        print()
    
    await lk_api.aclose()
    print("✅ Check complete!")

if __name__ == "__main__":
    asyncio.run(main())

