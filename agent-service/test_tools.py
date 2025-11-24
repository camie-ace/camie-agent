from dotenv import load_dotenv
load_dotenv()

import asyncio
from utils.api_client import get_tools_schema

async def main():
    response = await get_tools_schema(
        ["fb0f2b86-a2bc-423b-a3af-3b9eee86675b", "c340fdc5-66fc-4f23-919b-8f71d33a9b2c"],
        "c00db557-5001-458d-8d97-78cf0af4d10a"
    )
    print(response)

asyncio.run(main())
