"""
Dynamic model factory for creating STT, LLM, and TTS instances based on configuration
"""

import os
import logging
from typing import Any, Dict, Optional

from livekit.plugins import (
    openai,
    deepgram,
    elevenlabs,
)

# Configure logging
logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating AI model instances dynamically from configuration"""

    @staticmethod
    def create_stt(config):
        """Create an STT instance based on configuration"""
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
        else:
            logger.warning(
                f"Unsupported STT provider: {provider}, defaulting to deepgram")
            return deepgram.STT(model="nova-3", language="multi")

    @staticmethod
    def create_llm(config):
        """Create an LLM instance based on configuration"""
        provider = config.get("provider", "").lower()

        if not provider:
            logger.warning("No LLM provider specified, defaulting to openai")
            provider = "openai"

        if provider == "openai":
            model = config.get("model", "gpt-4o-mini")
            temperature = config.get("temperature", 0.7)

            # Build kwargs dictionary with only defined optional parameters
            kwargs = {}
            for param in ["max_tokens", "top_p", "frequency_penalty", "presence_penalty"]:
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
        """Create a TTS instance based on configuration"""
        provider = config.get("provider", "").lower()

        if not provider:
            logger.warning(
                "No TTS provider specified, defaulting to elevenlabs")
            provider = "elevenlabs"

        if provider == "elevenlabs":
            model = config.get("model", "eleven_monolingual_v1")
            voice = config.get("voice", "Adam")

            # Build kwargs dictionary with only defined optional parameters
            kwargs = {}
            for param in ["similarity_boost", "stability"]:
                if config.get(param) is not None:
                    kwargs[param] = config.get(param)

            logger.info(
                f"Creating ElevenLabs TTS with model={model}, voice={voice}, kwargs={kwargs}")
            return elevenlabs.TTS(model=model, voice=voice, **kwargs)
        else:
            logger.warning(
                f"Unsupported TTS provider: {provider}, defaulting to elevenlabs")
            return elevenlabs.TTS(model="eleven_monolingual_v1", voice="Adam")


def create_model_components(config: Dict[str, Any]):
    """Create all model components based on configuration"""
    stt_config = config.get("stt", {})
    llm_config = config.get("llm", {})
    tts_config = config.get("tts", {})

    return {
        "stt": ModelFactory.create_stt(stt_config),
        "llm": ModelFactory.create_llm(llm_config),
        "tts": ModelFactory.create_tts(tts_config),
    }
