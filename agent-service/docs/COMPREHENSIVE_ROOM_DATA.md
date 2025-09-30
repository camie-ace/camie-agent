# Comprehensive Room Data Extraction

This document explains how to extract comprehensive room and SIP data from LiveKit contexts, including `sip_from`, `sip_to`, `sip_trunk_id`, and other metadata.

## Overview

The `extract_comprehensive_room_data()` function provides access to all available room and SIP-related data that LiveKit makes available through the job context. This includes:

- Basic room information (name, metadata)
- SIP connection details (from, to, trunk ID)
- Call information (call ID, direction)
- Participant metadata
- Job-related data

## Usage

### Basic Usage

```python
from utils.room_extractor import extract_comprehensive_room_data

async def entrypoint(ctx: agents.JobContext):
    # Extract all available room data
    room_data = extract_comprehensive_room_data(ctx)

    # Access SIP data
    sip_from = room_data.get("sip_from")
    sip_to = room_data.get("sip_to")
    sip_trunk_id = room_data.get("sip_trunk_id")
    call_id = room_data.get("call_id")
    direction = room_data.get("direction")

    print(f"Call from {sip_from} to {sip_to} via trunk {sip_trunk_id}")
```

### Data Structure

The function returns a dictionary with the following structure:

```python
{
    "room_name": "livekit-room-name",           # Room name
    "sip_from": "+15551234567",                 # Calling number
    "sip_to": "+15559876543",                   # Called number
    "sip_trunk_id": "trunk_abc123",             # SIP trunk identifier
    "call_id": "unique-call-id",                # Call session ID
    "direction": "inbound",                     # Call direction
    "participant_metadata": {                   # Parsed participant metadata
        "custom_field": "value"
    },
    "room_metadata": {                          # Parsed room metadata
        "room_setting": "value"
    },
    "job_id": "job-uuid",                       # LiveKit job ID
    "additional_attributes": {                  # Other discovered attributes
        "name": "room-name",
        "request_room_name": "name-from-request"
    }
}
```

### Debugging Available Data

To see all available data in a LiveKit context (useful for debugging):

```python
from utils.room_extractor import log_all_available_data

async def entrypoint(ctx: agents.JobContext):
    # This will log all available attributes and data
    log_all_available_data(ctx)
```

## Data Sources

The function extracts data from multiple sources:

### 1. Participant Metadata

Most SIP providers (including Twilio, LiveKit SIP) store SIP data in participant metadata:

```json
{
  "sip_from": "+15551234567",
  "sip_to": "+15559876543",
  "sip_trunk_id": "trunk123",
  "direction": "inbound"
}
```

### 2. Room Metadata

Some providers store room-level configuration:

```json
{
    "trunk_config": "trunk123",
    "routing_info": {...}
}
```

### 3. Room Name Patterns

SIP data can be encoded in room names:

- `sip-trunk123-from+1234567890-to+0987654321`
- `twilio-trunk-abc123-+1234567890`
- `livekit-sip-trunk456-inbound`

### 4. Job Request Attributes

LiveKit job requests may contain SIP attributes directly.

## Common SIP Data Fields

### Field Mappings

The function looks for SIP data under various field names:

| Data        | Possible Field Names                     |
| ----------- | ---------------------------------------- |
| From Number | `sip_from`, `sipFrom`, `from`            |
| To Number   | `sip_to`, `sipTo`, `to`                  |
| Trunk ID    | `sip_trunk_id`, `sipTrunkId`, `trunk_id` |
| Call ID     | `call_id`, `callId`                      |
| Direction   | `direction`, `call_direction`            |

### Room Name Patterns

The function recognizes these room name patterns:

1. **Full SIP Pattern**: `sip-trunk123-from+1234567890-to+0987654321`
2. **Twilio Pattern**: `twilio-trunk-abc123-+1234567890`
3. **Trunk Patterns**: `trunk_123`, `trk-456`, `sip-trunk-789`

## Integration Examples

### With Call History

```python
# Extract comprehensive data for call history
room_data = extract_comprehensive_room_data(ctx)

# Start call recording with enhanced data
call_id = await start_call_recording(
    phone_number=room_data.get("sip_from", "unknown"),
    room_name=room_data.get("room_name", "unknown"),
    call_type=room_data.get("direction", "inbound")
)

# Store additional SIP data in call record
await update_call_config(call_id, {
    "sip_data": {
        "sip_from": room_data.get("sip_from"),
        "sip_to": room_data.get("sip_to"),
        "sip_trunk_id": room_data.get("sip_trunk_id"),
        "call_id": room_data.get("call_id")
    }
})
```

### With Configuration API

```python
# Use SIP data for configuration requests
room_data = extract_comprehensive_room_data(ctx)

# Enhanced configuration request
agent_config = await get_agent_config_from_room(
    room_name=room_data.get("room_name"),
    participant_metadata={
        "direction": room_data.get("direction"),
        "sip_trunk_id": room_data.get("sip_trunk_id"),
        "sip_from": room_data.get("sip_from")
    }
)
```

## Error Handling

The function is designed to be robust and will not fail if data is unavailable:

- Returns sensible defaults for missing data
- Logs debug information for troubleshooting
- Continues processing even if some data sources fail

## Provider-Specific Notes

### Twilio

- Usually stores SIP data in participant metadata
- Room names often follow: `twilio-trunk-{id}-{number}`

### LiveKit SIP

- May use room metadata for SIP configuration
- Participant metadata typically contains call details

### Custom SIP Providers

- Check both room and participant metadata
- May encode data in room names
- Use `log_all_available_data()` to discover patterns
