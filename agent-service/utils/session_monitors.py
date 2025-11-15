"""
Session monitoring utilities for agent call management.

This module handles monitoring of call duration and silence detection,
providing automatic call termination when thresholds are exceeded.
"""

import asyncio
import logging
from typing import Optional
from livekit.agents import AgentSession

logger = logging.getLogger(__name__)


class SessionMonitors:
    """Manages call duration and silence monitoring for agent sessions"""

    def __init__(self, assistant_instance):
        """Initialize the session monitors

        Args:
            assistant_instance: The Assistant instance that owns these monitors
        """
        self._assistant = assistant_instance
        self._call_duration_task: Optional[asyncio.Task] = None
        self._silence_monitor_task: Optional[asyncio.Task] = None
        self._last_voice_activity_time = asyncio.Event()

    def start_monitoring(self,
                         max_call_duration: int = 0,
                         enable_silence_detection: bool = False,
                         silence_duration: int = 60):
        """Start call duration and silence monitoring tasks

        Args:
            max_call_duration: Maximum call duration in seconds (0 = disabled)
            enable_silence_detection: Whether to enable silence detection
            silence_duration: Maximum silence duration in seconds
        """
        if max_call_duration > 0:
            self._call_duration_task = asyncio.create_task(
                self._monitor_call_duration(max_call_duration)
            )

        if enable_silence_detection and silence_duration > 0:
            self._silence_monitor_task = asyncio.create_task(
                self._monitor_silence(silence_duration)
            )

    def setup_voice_activity_handler(self, agent_session: AgentSession):
        """Register voice activity callback with the agent session

        Args:
            agent_session: The LiveKit agent session to monitor
        """
        def on_voice_activity(is_speaking: bool):
            if is_speaking:
                self._last_voice_activity_time.set()
                self._last_voice_activity_time.clear()

        agent_session.on("voice_activity")(on_voice_activity)

    async def cancel_all(self):
        """Cancel all monitoring tasks"""
        if self._call_duration_task and not self._call_duration_task.done():
            self._call_duration_task.cancel()
            logger.info("Cancelled call duration monitoring task")

        if self._silence_monitor_task and not self._silence_monitor_task.done():
            self._silence_monitor_task.cancel()
            logger.info("Cancelled silence monitoring task")

    async def _monitor_call_duration(self, max_duration_seconds: int) -> None:
        """
        Monitor and end call after max duration

        Args:
            max_duration_seconds: Maximum call duration in seconds
        """
        try:
            logger.info(
                f"Call duration monitor started: {max_duration_seconds}s maximum")
            await asyncio.sleep(max_duration_seconds)

            if self._assistant._agent_session:
                logger.info(
                    "Call duration limit reached - sending farewell message")
                # Inform user that call duration limit reached
                await self._assistant._agent_session.generate_reply(
                    instructions="Inform the user that the maximum call duration has been reached and say goodbye politely.",
                    allow_interruptions=False
                )

                # Allow time for the goodbye message to be spoken and heard
                logger.info("Waiting for farewell message to complete")
                await asyncio.sleep(8)

                # End the call
                logger.info("Ending call due to maximum duration exceeded")
                await self._assistant.end_session("max_duration_exceeded")

        except asyncio.CancelledError:
            logger.info("Call duration monitor cancelled")
        except Exception as e:
            logger.exception(f"Error in call duration monitor: {str(e)}")

    async def _monitor_silence(self, silence_duration_seconds: int) -> None:
        """
        Monitor for silence and end call after specified duration

        Args:
            silence_duration_seconds: Maximum silence duration in seconds
        """
        try:
            logger.info(
                f"Silence monitor started: {silence_duration_seconds}s threshold")

            while True:
                # Wait for the silence duration
                try:
                    # Wait for voice activity or timeout
                    await asyncio.wait_for(
                        self._last_voice_activity_time.wait(),
                        timeout=silence_duration_seconds
                    )
                    # If we reach here, there was voice activity, so reset and continue monitoring
                    continue
                except asyncio.TimeoutError:
                    # No voice activity detected within timeout period
                    if self._assistant._agent_session:
                        logger.info(
                            "Silence timeout reached - sending farewell message")
                        # Inform user about silence timeout
                        await self._assistant._agent_session.generate_reply(
                            instructions="Inform the user that due to lack of activity, you need to end the call, and say goodbye politely.",
                            allow_interruptions=False
                        )

                        # Allow time for the goodbye message to be spoken and heard
                        logger.info("Waiting for farewell message to complete")
                        await asyncio.sleep(8)

                        # End the call
                        logger.info("Ending call due to silence timeout")
                        await self._assistant.end_session("silence_timeout")
                        break

        except asyncio.CancelledError:
            logger.info("Silence monitor cancelled")
        except Exception as e:
            logger.exception(f"Error in silence monitor: {str(e)}")
