import os
import importlib
from typing import Any, Dict, Type, Optional

# Import commonly used plugins directly
from livekit.plugins import openai, cartesia, deepgram, elevenlabs

from config.config_definitions import STTConfig, LLMConfig, TTSConfig

# Plugin provider mappings - maps provider names to their module and class
PLUGIN_MAPPINGS = {
    # STT Plugins
    "deepgram": {"module": "livekit.plugins.deepgram", "class_name": "STT"},
    # "mistral": {"module": "livekit.plugins.mistral", "class_name": "STT"},
    "elevenlabs_stt": {"module": "livekit.plugins.elevenlabs", "class_name": "STT"},

    # LLM Plugins
    "openai": {"module": "livekit.plugins.openai", "class_name": "LLM"},
    # "anthropic": {"module": "livekit.plugins.anthropic", "class_name": "LLM"},
    # "mistral_llm": {"module": "livekit.plugins.mistralai", "class_name": "LLM"},

    # TTS Plugins
    "cartesia": {"module": "livekit.plugins.cartesia", "class_name": "TTS"},
    "elevenlabs": {"module": "livekit.plugins.elevenlabs", "class_name": "TTS"},
    "openai_tts": {"module": "livekit.plugins.openai", "class_name": "TTS"},
}


def _apply_overrides_to_config(base_config: Dict[str, Any], user_settings: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    final_config = base_config.copy()
    possible_overrides = {
        "model": "model_override",
        "language": "language_override",
        "temperature": "temperature_override",
        "voice": "voice_override"
    }
    for internal_key, override_suffix in possible_overrides.items():
        user_override_key = f"{prefix}_{override_suffix}"
        if user_override_key in user_settings and user_settings[user_override_key] is not None:
            final_config[internal_key] = user_settings[user_override_key]
    return final_config


def _get_plugin_class(provider: str) -> Optional[Type[Any]]:
    """
    Dynamically get the plugin class based on provider name.
    Falls back to static imports for common plugins.
    """
    # Check if we have a mapping for this provider
    if provider not in PLUGIN_MAPPINGS:
        print(
            f"Warning: Unknown provider '{provider}'. No plugin mapping available.")
        return None

    mapping = PLUGIN_MAPPINGS[provider]
    module_name = mapping["module"]
    class_name = mapping["class_name"]

    # Fast path for already imported modules
    if provider == "deepgram":
        return deepgram.STT
    elif provider == "openai" and class_name == "LLM":
        return openai.LLM
    elif provider == "openai_tts" or (provider == "openai" and class_name == "TTS"):
        return openai.TTS
    elif provider == "cartesia":
        return cartesia.TTS
    elif provider == "elevenlabs" and class_name == "TTS":
        return elevenlabs.TTS

    # Dynamic import for other providers
    try:
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name)
        return plugin_class
    except (ImportError, AttributeError) as e:
        print(f"Error loading plugin for provider '{provider}': {e}")
        return None


def _instantiate_configured_plugin(
    provider: str,
    api_key_env_var: Optional[str],
    config_params: Dict[str, Any],
    provider_param_mapping: Dict[str, str]
) -> Optional[Any]:
    """
    Instantiates a plugin by provider name, checking API key and mapping parameters.
    """
    # Get the plugin class
    plugin_class = _get_plugin_class(provider)
    if not plugin_class:
        return None

    # Check API key if required
    if api_key_env_var and not os.getenv(api_key_env_var):
        print(
            f"Warning: Environment variable {api_key_env_var} not set for {provider}.")

    # Map generic parameters to provider-specific parameters
    constructor_kwargs = {}
    for generic_key, plugin_kwarg_name in provider_param_mapping.items():
        if generic_key in config_params and config_params[generic_key] is not None:
            constructor_kwargs[plugin_kwarg_name] = config_params[generic_key]

    # Instantiate the plugin
    try:
        return plugin_class(**constructor_kwargs)
    except Exception as e:
        print(
            f"Error instantiating plugin {plugin_class.__name__} with params {constructor_kwargs}: {e}")
        return None


def create_stt_plugin(user_settings: Dict[str, Any]):
    provider = user_settings["provider"]

    # Define parameter mappings based on provider
    if provider == "deepgram":
        param_mapping = {"model": "model", "language": "language"}
        api_key = "DEEPGRAM_API_KEY"
    elif provider == "elevenlabs_stt" or "elevenlabs" in provider:
        param_mapping = {"model": "model_id", "language": "language_code"}
        api_key = "ELEVEN_API_KEY"
    # elif provider == "mistral":
    #     param_mapping = {"model": "model", "language": "language"}
    #     api_key = "MISTRAL_API_KEY"
    else:
        print(
            f"Warning: Unsupported STT provider '{provider}'. Falling back to default Deepgram.")
        # Use stable French model to avoid Deepgram auto-fallback warnings
        fallback_config = STTConfig.DEEPGRAM_NOVA2_FR.value
        return deepgram.STT(model=fallback_config["model"], language=fallback_config["language"])

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=user_settings,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate STT plugin for provider '{provider}'. Using fallback.")
        # Use stable French model to avoid Deepgram auto-fallback warnings
        return deepgram.STT(model="nova-2", language="fr")

    return plugin


def create_llm_plugin(user_settings: Dict[str, Any]):
    base_config = {
        "provider": user_settings.get('llm', 'openai'),
        "model": user_settings.get('llm_model', 'gpt-4o-mini')
    }

    provider = base_config["provider"]

    # Define parameter mappings based on provider
    if provider == "openai":
        param_mapping = {"model": "model", "temperature": "temperature"}
        api_key = "OPENAI_API_KEY"
    # elif provider == "anthropic":
    #     param_mapping = {"model": "model", "temperature": "temperature"}
    #     api_key = "ANTHROPIC_API_KEY"
    # elif provider == "mistral_llm" or "mistral" in provider:
    #     param_mapping = {"model": "model", "temperature": "temperature"}
    #     api_key = "MISTRAL_API_KEY"
    else:
        print(
            f"Warning: Unsupported LLM provider '{provider}'. Falling back to default OpenAI.")
        fallback_config = LLMConfig.OPENAI_GPT4O_MINI.value
        return openai.LLM(model=fallback_config["model"], temperature=fallback_config.get("temperature", 0))

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=base_config,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate LLM plugin for provider '{provider}'. Using fallback.")
        fallback_config = LLMConfig.OPENAI_GPT4O_MINI.value
        return openai.LLM(model=fallback_config["model"], temperature=fallback_config.get("temperature"))

    return plugin


def create_model_instance(model_type: str, config: Dict[str, Any]):
    """Create a model instance of the specified type using the plugin factory.
    This provides compatibility with the old ModelFactory interface.

    Args:
        model_type: Type of model to create ('stt', 'llm', or 'tts')
        config: Configuration dictionary for the model, using the backend configuration format

    Returns:
        An instance of the specified model type
    """
    if model_type == "stt":
        return create_stt_plugin(config)
    elif model_type == "llm":
        return create_llm_plugin(config)
    elif model_type == "tts":
        return create_tts_plugin(config)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def create_tts_plugin(user_settings: Dict[str, Any]):
    base_config = {**user_settings}
    # If custom voice ID is provided, use it instead of the default voice
    if user_settings.get("custom_voice_id"):
        base_config["voice"] = user_settings["custom_voice_id"]

    provider = base_config["provider"]

    # Define parameter mappings based on provider
    if provider == "cartesia":
        param_mapping = {"language": "language", "voice": "voice"}
        api_key = "CARTESIA_API_KEY"
    elif provider == "elevenlabs":
        param_mapping = {"model": "model", "voice": "voice_id"}
        api_key = "ELEVEN_API_KEY"
    elif provider == "openai_tts":
        param_mapping = {"model": "model", "voice": "voice"}
        api_key = "OPENAI_API_KEY"
    else:
        print(
            f"Warning: Unsupported TTS provider '{provider}'. Falling back to default Cartesia.")
        fallback_config = TTSConfig.CARTESIA_DEFAULT_FR.value
        return cartesia.TTS(language=fallback_config["language"], voice=fallback_config["voice"])

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=base_config,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate TTS plugin for provider '{provider}'. Using fallback.")
        fallback_config = TTSConfig.CARTESIA_DEFAULT_FR.value
        return cartesia.TTS(language=fallback_config["language"], voice=fallback_config["voice"])

    return plugin


# Factory interface matching the old ModelFactory


class ModelFactory:
    """Deprecated: Use create_*_plugin functions directly instead"""

    @staticmethod
    def create_stt(config: Dict[str, Any]):
        return create_model_instance("stt", config)

    @staticmethod
    def create_llm(config: Dict[str, Any]):
        return create_model_instance("llm", config)

    @staticmethod
    def create_tts(config: Dict[str, Any]):
        return create_model_instance("tts", config)