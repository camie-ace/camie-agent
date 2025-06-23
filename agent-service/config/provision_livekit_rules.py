import asyncio
from livekit import api

lkapi = api.LiveKitAPI()
async def main():
  request = api.CreateSIPDispatchRuleRequest(
      rule=api.SIPDispatchRule(
          dispatch_rule_individual=api.SIPDispatchRuleIndividual(
              room_prefix="call-",
          )
      ),
      room_config=api.RoomConfiguration(
          agents=[api.RoomAgentDispatch(
              agent_name="inbound-agent",
              metadata="job dispatch metadata",
          )]
      )
  )
  dispatch = await lkapi.sip.create_sip_dispatch_rule(request)
  print("created dispatch", dispatch)
  await lkapi.aclose()

  # alternatively run this script using the json file inbound_trunk.json from the terminal:
  # lk sip dispatch create dispatch-rule.json

asyncio.run(main())