import os
import importlib
from typing import Any, Dict, Type, Optional

# Import commonly used plugins directly
from livekit.plugins import openai, cartesia, deepgram, elevenlabs

from config.config_definitions import STTConfig, LLMConfig, TTSConfig, DEFAULT_SETTINGS

# Plugin provider mappings - maps provider names to their module and class
PLUGIN_MAPPINGS = {
    # STT Plugins
    "deepgram": {"module": "livekit.plugins.deepgram", "class_name": "STT"},
    "elevenlabs_stt": {"module": "livekit.plugins.elevenlabs", "class_name": "STT"},

    # LLM Plugins
    "openai": {"module": "livekit.plugins.openai", "class_name": "LLM"},
    # Example
    "anthropic": {"module": "livekit.plugins.anthropic", "class_name": "LLM"},

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
    config_key_str = user_settings.get(
        "stt_config_key", DEFAULT_SETTINGS["stt_config_key"])
    try:
        base_config = STTConfig[config_key_str].value
    except KeyError:
        print(
            f"Warning: Invalid STT config key '{config_key_str}'. Falling back to default.")
        base_config = STTConfig[DEFAULT_SETTINGS["stt_config_key"]].value

    final_config = _apply_overrides_to_config(
        base_config, user_settings, "stt")
    provider = final_config["provider"]

    # Define parameter mappings based on provider
    if provider == "deepgram":
        param_mapping = {"model": "model", "language": "language"}
        api_key = "DEEPGRAM_API_KEY"
    elif provider == "elevenlabs_stt":
        param_mapping = {"model": "model_id", "language": "language_code"}
        api_key = "ELEVEN_API_KEY"
    else:
        print(
            f"Warning: Unsupported STT provider '{provider}'. Falling back to default Deepgram.")
        fallback_config = STTConfig.DEEPGRAM_NOVA2_EN.value
        return deepgram.STT(model=fallback_config["model"], language=fallback_config["language"])

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=final_config,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate STT plugin for provider '{provider}'. Using fallback.")
        fallback_config = STTConfig.DEEPGRAM_NOVA2_EN.value
        return deepgram.STT(model=fallback_config["model"], language=fallback_config["language"])

    return plugin


def create_llm_plugin(user_settings: Dict[str, Any]):
    config_key_str = user_settings.get(
        "llm_config_key", DEFAULT_SETTINGS["llm_config_key"])
    try:
        base_config = LLMConfig[config_key_str].value
    except KeyError:
        print(
            f"Warning: Invalid LLM config key '{config_key_str}'. Falling back to default.")
        base_config = LLMConfig[DEFAULT_SETTINGS["llm_config_key"]].value

    final_config = _apply_overrides_to_config(
        base_config, user_settings, "llm")
    provider = final_config["provider"]

    # Define parameter mappings based on provider
    if provider == "openai":
        param_mapping = {"model": "model", "temperature": "temperature"}
        api_key = "OPENAI_API_KEY"
    elif provider == "anthropic":  # Example of another provider
        param_mapping = {"model": "model_name", "temperature": "temperature"}
        api_key = "ANTHROPIC_API_KEY"
    else:
        print(
            f"Warning: Unsupported LLM provider '{provider}'. Falling back to default OpenAI.")
        fallback_config = LLMConfig.OPENAI_GPT4O_MINI.value
        return openai.LLM(model=fallback_config["model"], temperature=fallback_config.get("temperature"))

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=final_config,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate LLM plugin for provider '{provider}'. Using fallback.")
        fallback_config = LLMConfig.OPENAI_GPT4O_MINI.value
        return openai.LLM(model=fallback_config["model"], temperature=fallback_config.get("temperature"))

    return plugin


def create_tts_plugin(user_settings: Dict[str, Any]):
    config_key_str = user_settings.get(
        "tts_config_key", DEFAULT_SETTINGS["tts_config_key"])
    try:
        base_config = TTSConfig[config_key_str].value
    except KeyError:
        print(
            f"Warning: Invalid TTS config key '{config_key_str}'. Falling back to default.")
        base_config = TTSConfig[DEFAULT_SETTINGS["tts_config_key"]].value

    final_config = _apply_overrides_to_config(
        base_config, user_settings, "tts")
    provider = final_config["provider"]

    # Define parameter mappings based on provider
    if provider == "cartesia":
        param_mapping = {"language": "language", "voice": "voice"}
        api_key = "CARTESIA_API_KEY"
    elif provider == "elevenlabs":
        param_mapping = {"model": "model_id", "voice": "voice_id"}
        api_key = "ELEVEN_API_KEY"
    elif provider == "openai_tts":
        param_mapping = {"model": "model", "voice": "voice"}
        api_key = "OPENAI_API_KEY"
    else:
        print(
            f"Warning: Unsupported TTS provider '{provider}'. Falling back to default Cartesia.")
        fallback_config = TTSConfig.ELEVENLABS_UNKNOWN_FR.value
        return cartesia.TTS(language=fallback_config["language"], voice=fallback_config["voice"])

    # Try to instantiate the configured plugin
    plugin = _instantiate_configured_plugin(
        provider=provider,
        api_key_env_var=api_key,
        config_params=final_config,
        provider_param_mapping=param_mapping
    )

    # Fallback if instantiation failed
    if plugin is None:
        print(
            f"Failed to instantiate TTS plugin for provider '{provider}'. Using fallback.")
        fallback_config = TTSConfig.CARTESIA_DEFAULT_EN.value
        return cartesia.TTS(language=fallback_config["language"], voice=fallback_config["voice"])

    return plugin
