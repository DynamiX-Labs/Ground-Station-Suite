# Ground Station - Gemini Transcription Worker
# Developed by Claude (Anthropic AI) for the Ground Station project
#
# This module connects to Google Gemini Live API for real-time speech-to-text
# conversion with optional translation. Extends the base TranscriptionWorker class.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import base64
import logging
import time
from typing import Any, Dict, Optional

import numpy as np

from audio.transcriptionworker import TranscriptionWorker

try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-genai package not installed. Gemini transcription will be disabled.")

try:
    from langdetect import LangDetectException, detect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logging.warning("langdetect package not installed. Language detection will be disabled.")

logger = logging.getLogger("transcription.gemini")

# Reduce websockets logging verbosity to prevent API key exposure
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)


class GeminiTranscriptionWorker(TranscriptionWorker):
    """
    Gemini Live API transcription worker.

    Streams audio to Google Gemini Live API for real-time transcription
    and optional translation.
    """

    def __init__(
        self,
        transcription_queue,
        sio,
        loop,
        api_key: str,
        session_id: str,
        vfo_number: int,
        language: str = "auto",
        translate_to: str = "none",
        satellite: Optional[Dict[str, Any]] = None,
        transmitter: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            transcription_queue=transcription_queue,
            sio=sio,
            loop=loop,
            api_key=api_key,
            session_id=session_id,
            vfo_number=vfo_number,
            language=language,
            translate_to=translate_to,
            provider_name="gemini",
            satellite=satellite,
            transmitter=transmitter,
        )

        # Gemini-specific settings
        self.target_sample_rate = 16000  # Gemini requires 16kHz
        self.gemini_client = None
        self.gemini_session = None
        self.gemini_session_context = None

        # Type assertion for mypy (initialized in parent class)
        self.connected: bool

        # Periodic flush to force transcription processing
        self.last_flush_time = 0.0
        self.flush_interval = 2.5  # Force transcription every 2.5 seconds

    async def _connect(self):
        """Connect to Gemini Live API"""
        try:
            if not GEMINI_AVAILABLE:
                raise RuntimeError("google-genai package not installed")

            # Initialize client
            self.gemini_client = genai.Client(api_key=self.api_key)

            # Create session config for audio transcription
            config: dict = {
                "response_modalities": ["AUDIO"],
                # Use input transcription stream for clean, narration-free text.
                "input_audio_transcription": {},
            }
            output_constraints = (
                "Output rules: Return ONLY the final transcript text for the current speech segment. "
                "Do NOT explain, analyze, describe your process, or mention translation steps. "
                "Do NOT use markdown, headings, bullet points, or labels. "
                "Do NOT include phrases like 'analyzing', 'refining', 'transcribing', or similar meta commentary. "
                "If speech is unclear, use [inaudible] only where needed."
            )

            # Build system instruction based on language and translation settings
            if self.translate_to != "none":
                if self.language != "auto":
                    system_instruction = (
                        f"Transcribe and translate RF radio communications from {self.language} to {self.translate_to}. "
                        f"Output ONLY the {self.translate_to} translation. "
                        f"Do NOT include the original {self.language} text. "
                        f"Do NOT add language codes or markers. "
                        f"Keep words intact - do not split words with spaces between characters. "
                        f"\n\n"
                        f"Audio characteristics: RF radio with static noise and varying signal quality. "
                        f"Squelch is not applied. Ignore static noise and only transcribe actual speech. "
                        f"Mark unclear words with [inaudible]. "
                        f"Preserve numbers, callsigns, and codes exactly as spoken. "
                        f"Identify and label different speakers if multiple voices are present. "
                        f"{output_constraints}"
                    )
                else:
                    system_instruction = (
                        f"Transcribe and translate RF radio communications to {self.translate_to}. "
                        f"Output ONLY the {self.translate_to} translation. "
                        f"Do NOT include the original text. "
                        f"Do NOT add language codes or markers. "
                        f"Keep words intact - do not split words with spaces between characters. "
                        f"\n\n"
                        f"Audio characteristics: RF radio with static noise and varying signal quality. "
                        f"Squelch is not applied. Ignore static noise and only transcribe actual speech. "
                        f"Mark unclear words with [inaudible]. "
                        f"Preserve numbers, callsigns, and codes exactly as spoken. "
                        f"Identify and label different speakers if multiple voices are present. "
                        f"{output_constraints}"
                    )
                config["system_instruction"] = system_instruction
            elif self.language != "auto":
                system_instruction = (
                    f"Transcribe the audio to text. Audio language: {self.language}. "
                    f"Keep words intact - do not split words with spaces between characters. "
                    f"This is RF radio communication audio with intermittent static noise and varying signal quality. "
                    f"Squelch is not applied. Ignore static noise and only transcribe actual speech. "
                    f"Mark unclear words with [inaudible]. "
                    f"Preserve numbers, callsigns, and codes exactly as spoken. "
                    f"Identify and label different speakers if multiple voices are present. "
                    f"{output_constraints}"
                )
                config["system_instruction"] = system_instruction
            else:
                system_instruction = (
                    "Transcribe the audio to text. "
                    "Keep words intact - do not split words with spaces between characters. "
                    "This is RF radio communication audio with intermittent static noise and varying signal quality. "
                    "Squelch is not applied. Ignore static noise and only transcribe actual speech. "
                    "Mark unclear words with [inaudible]. "
                    "Preserve numbers, callsigns, and codes exactly as spoken. "
                    "Identify and label different speakers if multiple voices are present. "
                    f"{output_constraints}"
                )
                config["system_instruction"] = system_instruction

            if self.gemini_client is None:
                raise RuntimeError("Gemini client not initialized")

            # Connect to Live API
            # Gemini Live model code from current Gemini API docs
            model = "gemini-2.5-flash-native-audio-preview-12-2025"
            session_context = self.gemini_client.aio.live.connect(model=model, config=config)

            # Enter the async context manager
            self.gemini_session = await session_context.__aenter__()
            self.gemini_session_context = session_context
            self.connected = True
            self.last_connection_attempt = 0  # Reset backoff

            logger.info(
                f"Connected to Gemini Live API for session {self.session_id[:8]} VFO {self.vfo_number} using {model}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}", exc_info=True)
            self.connected = False
            self.gemini_session = None
            await self._send_error_to_ui(e)
            raise

    async def _disconnect(self):
        """Disconnect from Gemini Live API"""
        try:
            if self.gemini_session_context:
                await self.gemini_session_context.__aexit__(None, None, None)
                self.gemini_session_context = None
            self.gemini_session = None
            self.connected = False
        except Exception as e:
            logger.error(f"Error closing Gemini connection: {e}")

    def _prepare_audio_payload(self, audio_data: np.ndarray) -> str:
        """Preprocess PCM in worker thread to avoid blocking asyncio loop."""
        normalized = self._normalize_audio(audio_data, target_level=0.7)
        resampled = self._resample_audio(normalized, target_rate=16000)
        audio_int16 = np.clip(resampled * 32767, -32768, 32767).astype(np.int16)
        audio_pcm = bytes(audio_int16.tobytes())
        return base64.b64encode(audio_pcm).decode("utf-8")

    async def _send_audio_to_provider(self, audio_payload: str):
        """Send prepared audio payload to Gemini Live API"""
        if self.gemini_session is None:
            raise RuntimeError("Gemini session not established")

        # Check if we need to flush (force partial transcription)
        current_time = time.time()
        should_flush = (current_time - self.last_flush_time) > self.flush_interval

        # Stream audio
        await self.gemini_session.send(
            input={"media_chunks": [{"data": audio_payload, "mime_type": "audio/pcm;rate=16000"}]},
            end_of_turn=should_flush,
        )

        if should_flush:
            self.last_flush_time = current_time

    async def _receive_loop(self):
        """Receive transcription results from Gemini"""
        try:
            # Wait for session to be established
            while not self.gemini_session and self.running and self.connected:
                await asyncio.sleep(0.1)

            if not self.gemini_session:
                logger.debug("Receiver loop exiting: no session established")
                return

            # Receive responses
            while self.running and self.connected:
                try:
                    received_any = False
                    async for response in self._iter_provider_responses():
                        received_any = True
                        if not response:
                            continue

                        text, is_complete = self._extract_transcription_from_response(response)
                        if text:
                            detected_language = self._determine_detected_language(text)
                            await self._emit_transcription(
                                text=text, language=detected_language, is_final=is_complete
                            )

                    if not received_any:
                        await asyncio.sleep(0.05)

                except Exception as e:
                    error_str = str(e).lower()
                    # Check for recoverable errors
                    if (
                        "deadline" in error_str
                        or "timeout" in error_str
                        or "1000 (ok)" in error_str
                    ):
                        logger.debug(f"Receiver closed: {e}")
                        self.connected = False
                        break
                    else:
                        logger.error(f"Receiver error: {e}")
                        self.connected = False
                        break

        except Exception as e:
            if self.gemini_session:
                logger.error(f"Gemini receiver error: {e}")
            self.connected = False

    async def _iter_provider_responses(self):
        """Yield provider responses using public SDK APIs when available."""
        if self.gemini_session is None:
            return

        if hasattr(self.gemini_session, "receive"):
            async for response in self.gemini_session.receive():
                yield response
            return

        if hasattr(self.gemini_session, "_receive"):
            yield await self.gemini_session._receive()
            return

        raise RuntimeError("Gemini session does not expose a receive API")

    def _extract_transcription_from_response(self, response: Any) -> tuple[str, bool]:
        """
        Extract transcription text from a Gemini Live response.

        Supports both modern input transcription stream and legacy model_turn text output.
        """
        server_content = getattr(response, "server_content", None)

        # Preferred path: input transcription stream.
        input_transcription = None
        if server_content:
            if hasattr(server_content, "input_transcription"):
                input_transcription = server_content.input_transcription
            elif isinstance(server_content, dict):
                input_transcription = server_content.get(
                    "input_transcription"
                ) or server_content.get("inputTranscription")

        if input_transcription:
            if isinstance(input_transcription, dict):
                text = (input_transcription.get("text") or "").strip()
                is_complete = bool(input_transcription.get("finished"))
            else:
                text = (getattr(input_transcription, "text", None) or "").strip()
                is_complete = bool(getattr(input_transcription, "finished", False))

            if not is_complete and server_content:
                is_complete = getattr(server_content, "turn_complete", False) or (
                    isinstance(server_content, dict) and bool(server_content.get("turn_complete"))
                )
            return text, is_complete

        # Legacy fallback: model_turn text parts.
        model_turn = getattr(server_content, "model_turn", None) if server_content else None
        parts = getattr(model_turn, "parts", None)
        if parts:
            text_parts = [part.text.strip() for part in parts if getattr(part, "text", None)]
            text = " ".join(text_parts).strip()
            is_complete = bool(getattr(server_content, "turn_complete", False))
            return text, is_complete

        return "", False

    def _determine_detected_language(self, text: str) -> str:
        """Determine language for outgoing transcription payload."""
        if self.translate_to and self.translate_to != "none":
            return self.language if self.language and self.language != "auto" else "unknown"
        if self.language and self.language != "auto":
            return str(self.language)

        if LANGDETECT_AVAILABLE and text:
            try:
                return str(detect(text))
            except LangDetectException:
                return "unknown"

        return "unknown"

    def stop(self):
        """Stop the Gemini worker"""
        super().stop()

        # Close Gemini session
        if self.gemini_session_context and self.provider_loop:
            try:
                asyncio.run_coroutine_threadsafe(self._disconnect(), self.provider_loop)
            except Exception as e:
                logger.error(f"Error closing Gemini session: {e}")
