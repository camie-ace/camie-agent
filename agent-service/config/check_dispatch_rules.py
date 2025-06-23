import asyncio
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv()


async def check_rules():
    livekit_host = os.getenv("LIVEKIT_URL", "").replace(
        "http://", "").replace("https://", "").rstrip('/')
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([livekit_host, livekit_api_key, livekit_api_secret]):
        print("ERROR: Missing LiveKit credentials in .env")
        return "ERROR"

    livekit_api = api.LiveKitAPI(
        url=livekit_host, api_key=livekit_api_key, api_secret=livekit_api_secret)
    try:
        response = await livekit_api.sip.list_sip_dispatch_rule(
            api.ListSIPDispatchRuleRequest()
        )
        if not response.items:  # An empty list/array means no rules
            print("NO_RULES")
            return "NO_RULES"
        else:
            print(f"RULES_EXIST: Found {len(response.items)} rule(s).")
            return "RULES_EXIST"
    except Exception as e:
        print(f"ERROR: Could not list SIP dispatch rules: {e}")
        return "ERROR"
    finally:
        await livekit_api.aclose()

if __name__ == "__main__":
    result = asyncio.run(check_rules())
    # The script will print NO_RULES, RULES_EXIST, or ERROR to stdout
    # The exit code can also be used if preferred, but stdout is simpler for shell script capture
