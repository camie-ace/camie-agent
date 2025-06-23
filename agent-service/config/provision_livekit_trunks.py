import asyncio
import os
from dotenv import load_dotenv

from livekit import api
load_dotenv()

TRUNK_NAME = os.getenv("TRUNK_NAME", "My SIP Trunk")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+15105550100")
KRISP_ENABLED_STR = os.getenv("KRISP_ENABLED", "true")
KRISP_ENABLED = KRISP_ENABLED_STR.lower() in ("true", "1", "yes", "y")


async def main():
  livekit_api = api.LiveKitAPI()

  trunk = api.SIPInboundTrunkInfo(
      name=TRUNK_NAME,
      numbers=[PHONE_NUMBER],
      krisp_enabled=KRISP_ENABLED,
  )

  request = api.CreateSIPInboundTrunkRequest(
      trunk=trunk
  )

  trunk = await livekit_api.sip.create_sip_inbound_trunk(request)

  await livekit_api.aclose()

  # alternatively run this script using the json file inbound_trunk.json from the terminal:
  # lk sip inbound create inbound-trunk.json

asyncio.run(main())