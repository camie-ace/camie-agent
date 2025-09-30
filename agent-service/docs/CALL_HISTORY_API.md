# Call History API Integration

This document explains how the agent service sends call history data to an external API endpoint.

## Overview

When a call ends, the agent service sends the complete call history data to the configured external API endpoint. This allows you to store and analyze call history data in your own database or service.

## Configuration

1. Set the API endpoint URL in your `.env` file:

```
CALL_HISTORY_ENDPOINT=https://your-api.example.com/call-history
```

2. Optionally, if your API requires JWT authentication, set the JWT secret:

```
JWT_SECRET=your_jwt_secret
```

## Data Format

The agent service sends a JSON payload with the following structure:

```json
{
  "call_id": "unique-id-for-the-call",
  "phone_number": "+15551234567",
  "room_name": "livekit-room-name",
  "call_type": "inbound",
  "start_time": "2023-09-20T14:30:00.000Z",
  "end_time": "2023-09-20T14:35:42.123Z",
  "duration_seconds": 342.123,
  "status": "completed",
  "termination_reason": null,
  "agent_config": {
    "stt_config_key": "deepgram",
    "llm_config_key": "openai-gpt4",
    "tts_config_key": "elevenlabs",
    "business_type": "restaurant",
    "language": "english"
  },
  "metrics": {
    "total_user_utterances": 12,
    "total_agent_utterances": 15,
    "longest_user_utterance": 45,
    "longest_agent_utterance": 120,
    "average_user_response_time": 2.3,
    "average_agent_response_time": 1.5,
    "silence_count": 3,
    "interruption_count": 1
  },
  "outcomes": {
    "completion_rate": 0.95,
    "fields_collected": ["name", "phone", "time", "party_size"],
    "final_stage": "confirmation",
    "successful": true,
    "notes": null
  },
  "stage_timeline": [
    {
      "stage": "greeting",
      "timestamp": "2023-09-20T14:30:10.000Z"
    },
    {
      "stage": "information_gathering",
      "timestamp": "2023-09-20T14:31:45.000Z"
    },
    {
      "stage": "confirmation",
      "timestamp": "2023-09-20T14:34:20.000Z"
    }
  ]
}
```

## API Requirements

Your API endpoint should:

1. Accept POST requests with JSON payloads
2. Return HTTP 200 OK for successful processing
3. Return an appropriate error code (4xx or 5xx) if processing fails

## Authentication

The call history data is sent with JWT authentication if JWT_SECRET is configured. The JWT contains:

- `phone_number`: The phone number associated with the call
- `timestamp`: The end time (or start time if end time is not available) of the call

## Error Handling

If the API call fails, the error is logged but does not affect the call flow or user experience. The agent service continues to operate normally even if the call history API is unavailable.

## Testing

You can test your API integration by:

1. Setting up a test API endpoint (for example, using a service like RequestBin)
2. Configuring the agent service to use the test endpoint
3. Making a test call through LiveKit
4. Verifying that the call data is received by your test endpoint

## Implementing Your API

Your API should:

1. Parse the incoming JSON payload
2. Validate the JWT token if authentication is enabled
3. Store the call data in your database
4. Perform any required analytics or post-processing
5. Return a success response

Example server implementation (Node.js/Express):

```javascript
app.post("/call-history", async (req, res) => {
  try {
    // Extract call data from request body
    const callData = req.body

    // Verify JWT if needed
    // const token = req.headers.authorization.split(' ')[1];
    // jwt.verify(token, process.env.JWT_SECRET);

    // Store in database
    await db.collection("call_history").insertOne(callData)

    // Return success
    res.status(200).json({ success: true })
  } catch (error) {
    console.error("Error processing call history:", error)
    res.status(500).json({ success: false, error: error.message })
  }
})
```
