"""
Dynamic model factory for creating STT, LLM, and TTS instances based on configuration

Supported providers:
- STT:
  - Deepgram: Supports model and language parameters
  - ElevenLabs: Supports language_code parameter and optional sample_rate, channels

- LLM:
  - OpenAI: Supports model, temperature, max_completion_tokens, timeout

- TTS:
  - ElevenLabs: Supports model, voice_id, language and voice_settings (similarity_boost, stability, style, speed)
  - Cartesia: Supports model, voice, speed, pitch
"""

import os
import logging
from typing import Any, Dict, Optional

from livekit.plugins import (
    openai,
    deepgram,
    elevenlabs,
    cartesia,
)
from livekit.plugins.elevenlabs import VoiceSettings
from config.config_definitions import TTSConfig

# Configure logging
logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating AI model instances dynamically from configuration

    Each create_* method accepts a configuration dictionary with provider-specific
    parameters. The factory handles parameter mapping and defaults appropriate for 
    each provider, ensuring consistent interfaces while allowing for provider-specific
    optimizations.

    Configuration parameters follow a unified schema where possible, with provider-specific
    mappings handled internally (e.g., 'voice' parameter is mapped to 'voice_id' for ElevenLabs).
    """

    @staticmethod
    def create_stt(config):
        """Create an STT instance based on configuration

        Args:
            config: Dictionary containing STT configuration parameters
                - provider: 'deepgram' or 'elevenlabs' (default: 'deepgram')
                - model: Model name (for Deepgram, default: 'nova-3')
                - language: Language code (for Deepgram, default: 'multi')
                - language_code: Language code (for ElevenLabs, default: 'auto')
                - sample_rate: Sample rate in Hz (for ElevenLabs, optional)
                - channels: Number of audio channels (for ElevenLabs, optional)

        Returns:
            An STT instance from the specified provider
        """
        provider = config.get("provider", "").lower()

        if not provider:
            logger.warning("No STT provider specified, defaulting to deepgram")
            provider = "deepgram"

        if provider == "deepgram":
            model = config.get("model", "nova-3")
            language = config.get("language", "multi")
            logger.info(
                f"Creating Deepgram STT with model={model}, language={language}")
            return deepgram.STT(model=model, language=language)
        elif provider == "elevenlabs":
            model = config.get("model", "speech-recognition-1")
            language = config.get("language", "auto")

            # Build kwargs dictionary with only defined optional parameters
            kwargs = {}
            for param in ["sample_rate", "channels"]:
                if config.get(param) is not None:
                    kwargs[param] = config.get(param)

            logger.info(
                f"Creating ElevenLabs STT with model={model}, language={language}, kwargs={kwargs}")
            return elevenlabs.STT(language_code=language)
        else:
            logger.warning(
                f"Unsupported STT provider: {provider}, defaulting to deepgram")
            return deepgram.STT(model="nova-3", language="multi")

    @staticmethod
    def create_llm(config):
        """Create an LLM instance based on configuration

        Args:
            config: Dictionary containing LLM configuration parameters
                - provider: 'openai' (default: 'openai')
                - model: Model name (default: 'gpt-4o-mini')
                - temperature: Sampling temperature (default: 0.7)
                - max_completion_tokens: Maximum tokens in completion (optional)
                - timeout: Request timeout in seconds (optional)

        Returns:
            An LLM instance from the specified provider
        """
        provider = config.get("provider", "").lower()

        if not provider:
            logger.warning("No LLM provider specified, defaulting to openai")
            provider = "openai"

        if provider == "openai":
            model = config.get("model", "gpt-4o-mini")
            temperature = config.get("temperature", 0.7)

            # Build kwargs dictionary with only defined optional parameters
            kwargs = {}
            for param in ["max_completion_tokens", "timeout"]:
                if config.get(param) is not None:
                    kwargs[param] = config.get(param)

            logger.info(
                f"Creating OpenAI LLM with model={model}, temperature={temperature}, kwargs={kwargs}")
            return openai.LLM(model=model, temperature=temperature, **kwargs)
        else:
            logger.warning(
                f"Unsupported LLM provider: {provider}, defaulting to openai")
            return openai.LLM(model="gpt-4o-mini", temperature=0.7)

    @staticmethod
    def create_tts(config):
        """Create a TTS instance based on configuration

        Args:
            config: Dictionary containing TTS configuration parameters
                - provider: 'elevenlabs' or 'cartesia' (default: 'elevenlabs')

                For ElevenLabs:
                - model: Model name (default: 'eleven_turbo_v2_5')
                - voice: Voice ID (mapped to voice_id, default: 'EXAVITQu4vr4xnSDxMaL')
                - language: Language code (default: 'en')
                - similarity_boost: Voice similarity setting (optional, float)
                - stability: Voice stability setting (optional, float)
                - style: Voice style setting (optional, float)
                - speed: Speech speed setting (optional, float)

                Note: Voice settings are properly converted to a VoiceSettings instance

                For Cartesia:
                - model: Model name (default: 'cartesia-tts-1')
                - voice: Voice name (default: 'female-01')
                - speed: Speech speed setting (optional)
                - pitch: Voice pitch setting (optional)

        Returns:
            A TTS instance from the specified provider
        """
        provider = config.get("provider", "").lower()

        if not provider:
            logger.warning(
                "No TTS provider specified, defaulting to cartesia")
            provider = "cartesia"

        if provider == "elevenlabs":
            model = config.get("model", "eleven_turbo_v2_5")
            voice_id = config.get("voice", "EXAVITQu4vr4xnSDxMaL")
            language = config.get("language", "en")

            # Extract voice settings parameters
            stability = config.get("stability")
            similarity_boost = config.get("similarity_boost")
            style = config.get("style")
            speed = config.get("speed")

            # Create VoiceSettings instance with only defined parameters
            voice_settings_kwargs = {}
            if stability is not None:
                voice_settings_kwargs["stability"] = stability
            if similarity_boost is not None:
                voice_settings_kwargs["similarity_boost"] = similarity_boost
            if style is not None:
                voice_settings_kwargs["style"] = style
            if speed is not None:
                voice_settings_kwargs["speed"] = speed

            # Create VoiceSettings instance if any settings are specified
            voice_settings = VoiceSettings(
                **voice_settings_kwargs) if voice_settings_kwargs else None

            logger.info(
                f"Creating ElevenLabs TTS with model={model}, voice_id={voice_id}, language={language}, voice_settings={voice_settings_kwargs}")

            # Pass voice_settings as an instance or None
            if voice_settings:
                return elevenlabs.TTS(model=model, language=language, voice_id=voice_id, voice_settings=voice_settings)
            else:
                return elevenlabs.TTS(model=model, language=language, voice_id=voice_id)
        elif provider == "cartesia":
            model = config.get("model", "cartesia-tts-1")
            voice = config.get("voice", "female-01")

            # Build kwargs dictionary with only defined optional parameters
            kwargs = {}
            for param in ["speed", "pitch"]:
                if config.get(param) is not None:
                    kwargs[param] = config.get(param)

            logger.info(
                f"Creating Cartesia TTS with model={model}, voice={voice}, kwargs={kwargs}")
            return cartesia.TTS(model=model, voice=voice, **kwargs)
        else:
            logger.warning(
                f"Unsupported TTS provider: {provider}, defaulting to cartesia")
            # Use default model and voice_id without any voice settings
            return cartesia.TTS(model=TTSConfig.CARTESIA_DEFAULT_FR.value["model"], language=TTSConfig.CARTESIA_DEFAULT_FR.value["language"], voice=TTSConfig.CARTESIA_DEFAULT_FR.value["voice"])


def create_model_components(config: Dict[str, Any]):
    """Create all model components based on configuration

    Args:
        config: Dictionary containing all configuration settings with sections:
            - stt: Speech-to-Text configuration
            - llm: Language Model configuration
            - tts: Text-to-Speech configuration

    Returns:
        Dictionary with instantiated model components:
            - stt: Speech-to-Text instance
            - llm: Language Model instance
            - tts: Text-to-Speech instance
    """
    stt_config = config.get("stt", {})
    llm_config = config.get("llm", {})
    tts_config = config.get("tts", {})

    return {
        "stt": ModelFactory.create_stt(stt_config),
        "llm": ModelFactory.create_llm(llm_config),
        "tts": ModelFactory.create_tts(tts_config),
    }
