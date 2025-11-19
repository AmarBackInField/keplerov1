import asyncio
from twilio.rest import Client
from livekit import api
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime

load_dotenv()


LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

async def create_twilio_sip_trunk(
    account_sid: str,
    auth_token: str,
    friendly_name: str = "MyOutboundTrunk",
    username: str = "agent_user",
    password: str = "StrongPass123"
):
    print("Logging into Twilio...")
    twilio_client = Client(account_sid, auth_token)

    print("Creating SIP Trunk...")
    # Generate unique trunk name to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_trunk_name = f"{friendly_name}_{timestamp}"
    
    sip_trunk = twilio_client.trunking.v1.trunks.create(
        friendly_name=unique_trunk_name
    )
    print(f"✔ Twilio SIP Trunk SID: {sip_trunk.sid}")

    print("Creating Credential List...")
    # Generate unique credential list name to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    credential_list_name = f"{friendly_name}_CredList_{timestamp}_{unique_id}"
    
    credential_list = twilio_client.sip.credential_lists.create(
        friendly_name=credential_list_name
    )
    print(f"✔ Credential List SID: {credential_list.sid}")

    print("Adding Credential Username/Password...")
    credential = twilio_client.sip.credential_lists(credential_list.sid).credentials.create(
        username=username,
        password=password
    )
    print(f"✔ Credential SID: {credential.sid}")

    print("Attaching Credential List to Trunk...")
    twilio_client.trunking.v1.trunks(sip_trunk.sid).credentials_lists.create(
        credential_list_sid=credential_list.sid
    )

    print("✔ Twilio SIP Trunk is fully configured")

    return {
        "trunk_sid": sip_trunk.sid,
        "trunk_name": unique_trunk_name,
        "credential_list_sid": credential_list.sid,
        "credential_list_name": credential_list_name,
        "username": username,
        "password": password,
    }


async def create_livekit_trunk(
    twilio_trunk_sid: str,
    username: str,
    password: str,
    phone_number: str,
    trunk_name: str = "Outbound-Trunk"
):
    print("Creating LiveKit SIP Trunk...")

    lk = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    )

    from livekit.protocol import sip
    
    # Create the trunk info object
    trunk_info = sip.SIPOutboundTrunkInfo()
    trunk_info.name = trunk_name
    trunk_info.metadata = f'{{"provider":"twilio","trunk_sid":"{twilio_trunk_sid}"}}'
    trunk_info.address = f"{twilio_trunk_sid}.pstn.twilio.com"
    trunk_info.auth_username = username
    trunk_info.auth_password = password
    # Add phone number(s) to the trunk
    trunk_info.numbers.append(phone_number)
    
    # Create the request with the trunk info
    request = sip.CreateSIPOutboundTrunkRequest()
    request.trunk.CopyFrom(trunk_info)
    
    # Create the trunk
    trunk = await lk.sip.create_outbound_trunk(request)

    await lk.aclose()
    print(f"✔ LiveKit SIP Trunk Created: {trunk.sip_trunk_id}")
    print(f"   Phone Numbers: {', '.join(trunk_info.numbers)}")
    return trunk.sip_trunk_id


async def create_livekit_trunk_from_address(
    sip_address: str,
    username: str,
    password: str,
    phone_number: str,
    trunk_name: str = "Outbound-Trunk"
):
    """
    Create a LiveKit SIP trunk from an existing Twilio SIP address.
    Use this when you already have a Twilio trunk configured.
    
    Args:
        sip_address: Twilio SIP address (e.g., example.pstn.twilio.com)
        username: SIP username for authentication
        password: SIP password for authentication
        phone_number: Phone number associated with the trunk
        trunk_name: Name for the LiveKit trunk
    
    Returns:
        str: LiveKit trunk ID
    """
    print("Creating LiveKit SIP Trunk from existing Twilio address...")
    
    lk = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET
    )
    
    from livekit.protocol import sip
    
    # Create the trunk info object
    trunk_info = sip.SIPOutboundTrunkInfo()
    trunk_info.name = trunk_name
    trunk_info.metadata = f'{{"provider":"twilio","address":"{sip_address}"}}'
    trunk_info.address = sip_address
    trunk_info.auth_username = username
    trunk_info.auth_password = password
    # Add phone number(s) to the trunk
    trunk_info.numbers.append(phone_number)
    
    # Create the request with the trunk info
    request = sip.CreateSIPOutboundTrunkRequest()
    request.trunk.CopyFrom(trunk_info)
    
    # Create the trunk
    trunk = await lk.sip.create_outbound_trunk(request)
    
    await lk.aclose()
    print(f"✔ LiveKit SIP Trunk Created: {trunk.sip_trunk_id}")
    print(f"   SIP Address: {sip_address}")
    print(f"   Phone Numbers: {', '.join(trunk_info.numbers)}")
    return trunk.sip_trunk_id


async def main():
    print("==== TWILIO CREDENTIAL INPUT ====")
    account_sid = input("Enter Twilio ACCOUNT SID: ").strip()
    auth_token = input("Enter Twilio AUTH TOKEN: ").strip()
    phone_number = input("Enter Phone Number (e.g., +1234567890): ").strip()

    # Step 1 — Create Twilio Trunk
    twilio_data = await create_twilio_sip_trunk(
        account_sid=account_sid,
        auth_token=auth_token,
        friendly_name="OutboundTrunkDemo",
        username="my_agent",
        password="Password@123"
    )

    # Step 2 — Create LiveKit Trunk
    trunk_id = await create_livekit_trunk(
        twilio_trunk_sid=twilio_data["trunk_sid"],
        username=twilio_data["username"],
        password=twilio_data["password"],
        phone_number=phone_number
    )

    print("\n==== FINAL RESULTS ====")
    print("Twilio Trunk SID:", twilio_data["trunk_sid"])
    print("LiveKit Trunk ID:", trunk_id)


if __name__ == "__main__":
    asyncio.run(main())
