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
    print("CHECKING OUTBOUND SIP TRUNKS")
    print("=" * 60)
    
    try:
        response = await lk_api.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        if not response.items:
            print("WARNING: No outbound trunks found!")
        else:
            for trunk in response.items:
                print(f"\n[TRUNK] {trunk.sip_trunk_id}")
                print(f"  Name: {trunk.name}")
                print(f"  Address: {trunk.address}")
                print(f"  Transport: {trunk.transport}")
                print(f"  Numbers: {list(trunk.numbers)}")
                print(f"  Auth Username: {trunk.auth_username}")
                print(f"  Metadata: {trunk.metadata}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    await lk_api.aclose()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

