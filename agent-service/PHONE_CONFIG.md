# Agent Phone Configuration

This document explains how the agent configuration is dynamically loaded based on phone numbers.

## Project Structure

- `agent.py`: Main entry point for the agent
- `utils/config_fetcher.py`: Handles fetching configurations based on phone numbers
- `utils/model_factory.py`: Creates model components dynamically based on configurations
- `test_model_factory.py`: Tests for the model factory functionality

## Process Flow

1. When a job request is received, the agent extracts the phone number from the room name
   (format: `twilio-+12345678901-XXXXX`) through `ctx.job.request.room_name`

2. The phone number is used to create a JWT token using the JWT_SECRET and JWT_ALGORITHM from
   environment variables

3. The token is sent as a Bearer token in the Authorization header to the VOICE_CONFIG_TOKEN_URL
   endpoint

4. The API returns a configuration object in the format:

   ```json
   {
     "phone_number": {
       "outbound": {
         "stt": {
           "provider": "deepgram",
           "model": "nova-3",
           "language": "en"
         },
         "llm": {
           "provider": "openai",
           "model": "gpt-4o-mini",
           "temperature": 0.7
         },
         "tts": {
           "provider": "elevenlabs",
           "model": "eleven_monolingual_v1",
           "voice": "Adam"
         },
         "assistant_instructions": "...",
         "welcome_message": "..."
       },
       "inbound": {
         "stt": { ... },
         "llm": { ... },
         "tts": { ... },
         "assistant_instructions": "...",
         "welcome_message": "..."
       }
     }
   }
   ```

5. The agent selects the appropriate configuration based on the call direction ("inbound" or "outbound")
   specified in the participant metadata

6. The agent dynamically instantiates the appropriate model components (STT, LLM, TTS) based on the
   configuration using the `ModelFactory` class

## Supported Model Providers

### Speech-to-Text (STT)

- **deepgram**: Default provider
  - Required parameters: `model`, `language`
  - Example: `{"provider": "deepgram", "model": "nova-3", "language": "en"}`

### Large Language Model (LLM)

- **openai**: Default provider
  - Required parameters: `model`, `temperature`
  - Optional parameters: `max_tokens`, `top_p`, `frequency_penalty`, `presence_penalty`
  - Example: `{"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.7}`

### Text-to-Speech (TTS)

- **elevenlabs**: Default provider
  - Required parameters: `model`, `voice`
  - Optional parameters: `similarity_boost`, `stability`
  - Example: `{"provider": "elevenlabs", "model": "eleven_monolingual_v1", "voice": "Adam"}`

## Environment Variables

- `JWT_SECRET`: Secret key for JWT token generation
- `JWT_ALGORITHM`: Algorithm for JWT token generation (default: HS256)
- `VOICE_CONFIG_TOKEN_URL`: URL endpoint for fetching voice configurations
- `DEEPGRAM_API_KEY`: API key for Deepgram STT
- `OPENAI_API_KEY`: API key for OpenAI LLM
- `ELEVEN_API_KEY`: API key for ElevenLabs TTS

## Testing

Run the unit tests to verify the phone number extraction and JWT token creation:

```bash
python -m unittest utils.test_config_fetcher
```

To test the model factory functionality:

```bash
python -m unittest test_model_factory
```

## Troubleshooting

### Common Issues

1. **Room Name Access**: If you see an error like `'JobContext' object has no attribute 'room_name'`, make sure you're accessing the room name correctly via `ctx.job.request.room_name` instead of directly from the context.

2. **API Connection Errors**: If configuration retrieval fails, check your network connection and ensure `VOICE_CONFIG_TOKEN_URL` is correctly set and accessible.

3. **JWT Token Issues**: Verify that `JWT_SECRET` and `JWT_ALGORITHM` are properly configured in your environment variables.
