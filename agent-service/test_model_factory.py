"""
Test the ModelFactory class in utils.model_factory
"""
import unittest
from unittest.mock import patch, MagicMock

# Import the ModelFactory from the new module
from utils.model_factory import ModelFactory


class TestModelFactory(unittest.TestCase):
    """Test the ModelFactory class functionality"""

    @patch("utils.model_factory.deepgram.STT")
    def test_create_stt(self, mock_stt):
        """Test STT creation with different configurations"""
        # Set up mock
        mock_stt.return_value = MagicMock()

        # Test with deepgram provider
        config = {"provider": "deepgram", "model": "nova-2", "language": "en"}
        ModelFactory.create_stt(config)
        mock_stt.assert_called_with(model="nova-2", language="en")

        # Test with missing provider (should default to deepgram)
        config = {"model": "nova-3", "language": "fr"}
        ModelFactory.create_stt(config)
        mock_stt.assert_called_with(model="nova-3", language="fr")

        # Test with empty config (should use defaults)
        ModelFactory.create_stt({})
        mock_stt.assert_called_with(model="nova-3", language="multi")

    @patch("utils.model_factory.openai.LLM")
    def test_create_llm(self, mock_llm):
        """Test LLM creation with different configurations"""
        # Set up mock
        mock_llm.return_value = MagicMock()

        # Test with openai provider
        config = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.5,
            "max_tokens": 1000,
            "top_p": 0.9
        }
        ModelFactory.create_llm(config)
        mock_llm.assert_called_with(
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            top_p=0.9
        )

        # Test with missing provider (should default to openai)
        config = {"model": "gpt-3.5-turbo", "temperature": 0.8}
        ModelFactory.create_llm(config)
        mock_llm.assert_called_with(model="gpt-3.5-turbo", temperature=0.8)

        # Test with empty config (should use defaults)
        ModelFactory.create_llm({})
        mock_llm.assert_called_with(model="gpt-4o-mini", temperature=0.7)

    @patch("utils.model_factory.elevenlabs.TTS")
    def test_create_tts(self, mock_tts):
        """Test TTS creation with different configurations"""
        # Set up mock
        mock_tts.return_value = MagicMock()

        # Test with elevenlabs provider
        config = {
            "provider": "elevenlabs",
            "model": "eleven_multilingual_v2",
            "voice": "Rachel",
            "similarity_boost": 0.8,
            "stability": 0.7
        }
        ModelFactory.create_tts(config)
        mock_tts.assert_called_with(
            model="eleven_multilingual_v2",
            voice="Rachel",
            similarity_boost=0.8,
            stability=0.7
        )

        # Test with missing provider (should default to elevenlabs)
        config = {"model": "eleven_monolingual_v1", "voice": "Josh"}
        ModelFactory.create_tts(config)
        mock_tts.assert_called_with(
            model="eleven_monolingual_v1", voice="Josh")

        # Test with empty config (should use defaults)
        ModelFactory.create_tts({})
        mock_tts.assert_called_with(
            model="eleven_monolingual_v1", voice="Adam")


if __name__ == "__main__":
    unittest.main()
