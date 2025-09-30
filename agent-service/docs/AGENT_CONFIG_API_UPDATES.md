# Agent Configuration API Updates

## Overview

The agent configuration API requests now include additional parameters to provide more context about the call:

1. **call_direction** (call_type) - Whether the call is "inbound" or "outbound"
2. **room_name** - The LiveKit room name associated with the call

## Updated API Request Parameters

When fetching agent configuration from the `VOICE_CONFIG_TOKEN_URL`, the following parameters are now sent:

### Query Parameters

- `call_type`: The call direction ("inbound" or "outbound")
- `room_name`: The LiveKit room name for the call

### Example Request

```
GET https://api.your-service.com/voice-config?call_type=inbound&room_name=lk_room_abc123
Authorization: Bearer <JWT_TOKEN>
```

## JWT Token Payload

The JWT token sent in the Authorization header contains:

```json
{
  "phone_number": "+15551234567"
}
```

## Implementation Details

The parameters are added at multiple levels in the configuration fetching process:

1. **APIClient.fetch_agent_config()** - Updated to accept and pass both parameters
2. **fetch_agent_config_by_phone()** in config_fetcher.py - Updated to accept and pass both parameters
3. **get_agent_config_from_db_by_phone()** in database.py - Updated to accept both parameters

## Backward Compatibility

These parameters are optional and the API will function normally if your endpoint doesn't require them. If either parameter is not available, it will be omitted from the request.

## Usage in Your API

Your API endpoint can now use these additional parameters to:

1. Provide different configurations for inbound vs outbound calls
2. Apply room-specific customizations
3. Implement routing logic based on call context
4. Enhanced logging and analytics

### Example Server Implementation

```javascript
app.get('/voice-config', (req, res) => {
  const { call_type, room_name } = req.query;

  // Use call_type to determine configuration
  if (call_type === 'outbound') {
    // Return outbound-specific configuration
  }

  // Use room_name for room-specific settings
  if (room_name.startsWith('support_')) {
    // Return support-specific configuration
  }

  // Return appropriate configuration
  res.json({ config: ... });
});
```
