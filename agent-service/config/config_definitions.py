from enum import Enum


class STTConfig(Enum):
    DEEPGRAM_NOVA2_EN = {"provider": "deepgram",
                         "model": "nova-2-phonecall", "language": "en"}
    DEEPGRAM_NOVA2_ES = {"provider": "deepgram",
                         "model": "nova-2-phonecall", "language": "fr"}
    ELEVENLABS_STT_EN = {"provider": "elevenlabs_stt",
                         "model": "scribe_v1", "language": "eng"}


class LLMConfig(Enum):
    OPENAI_GPT4O_MINI = {"provider": "openai",
                         "model": "gpt-4o-mini", "temperature": 0.7}
    OPENAI_GPT4_TURBO = {"provider": "openai",
                         "model": "gpt-4-turbo", "temperature": 0.5}


class TTSConfig(Enum):
    CARTESIA_DEFAULT_EN = {"provider": "cartesia", "model": None,
                           "language": "en", "voice": "c99d36f3-5ffd-4253-803a-535c1bc9c306"}
    ELEVENLABS_RACHEL_EN = {"provider": "elevenlabs", "model": "eleven_multilingual_v2",
                            "language": None, "voice": "JBFqnCBsd6RMkjVDRZzb"}
    OPENAI_ALLOY_TTS = {"provider": "openai_tts",
                        "model": "tts-1", "language": None, "voice": "alloy"}


DEFAULT_SETTINGS = {
    "stt_config_key": "DEEPGRAM_NOVA2_EN",
    "llm_config_key": "OPENAI_GPT4O_MINI",
    "tts_config_key": "CARTESIA_DEFAULT_EN",
    "stt_model_override": None, "stt_language_override": None,
    "llm_model_override": None, "llm_temperature_override": None,
    "tts_model_override": None, "tts_language_override": None, "tts_voice_override": None,
    "assistant_instructions": "You are a helpful assistant.",
    "welcome_message": "Welcome, how can I help you?",
}
