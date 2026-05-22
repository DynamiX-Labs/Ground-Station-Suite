# Ground Station - Deepgram Transcription Worker
# Developed by Claude (Anthropic AI) for the Ground Station project
#
# This module connects to Deepgram Streaming API for real-time speech-to-text
# conversion. Extends the base TranscriptionWorker class.
#
# Deepgram is optimized for noisy audio and is well-suited for RF radio communications.
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
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import numpy as np

from audio.transcriptionworker import TranscriptionWorker

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("websockets package not installed. Deepgram transcription will be disabled.")

logger = logging.getLogger("transcription.deepgram")

# Reduce websockets logging verbosity to prevent excessive debug output
logging.getLogger("websockets.client").setLevel(logging.INFO)
logging.getLogger("websockets.protocol").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.INFO)


class DeepgramTranscriptionWorker(TranscriptionWorker):
    """
    Deepgram Streaming API transcription worker.

    Streams audio to Deepgram via WebSocket for real-time transcription.
    Optimized for noisy RF audio with low latency.
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
        google_translate_api_key: Optional[str] = None,
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
            provider_name="deepgram",
            satellite=satellite,
            transmitter=transmitter,
        )

        # Google Translate API key for translating Deepgram transcriptions
        self.google_translate_api_key = google_translate_api_key

        # Deepgram-specific settings
        self.target_sample_rate = 16000  # Deepgram prefers 16kHz
        self.websocket = None
        self.keepalive_task: Optional[asyncio.Task] = None

        # Deepgram API endpoint
        self.websocket_url = self._build_websocket_url()

        # Google Translate API endpoint
        self.translate_api_url = "https://translation.googleapis.com/language/translate/v2"

    def _build_websocket_url(self) -> str:
        """Build Deepgram WebSocket URL with query parameters"""
        base_url = "wss://api.deepgram.com/v1/listen"

        # Query parameters
        params = [
            "model=nova-2",  # Use Nova-2 for best language support
            "encoding=linear16",
            f"sample_rate={self.target_sample_rate}",
            "channels=1",
            "punctuate=true",
            "interim_results=false",  # Only get final transcriptions to avoid repetition
        ]

        # Add language if specified
        if self.language and self.language != "auto":
            # Map language codes to Deepgram format
            # Based on: https://developers.deepgram.com/docs/models-languages-overview
            language_map = {
                "en": "en",
                "en-US": "en-US",
                "en-AU": "en-AU",
                "en-GB": "en-GB",
                "en-IN": "en-IN",
                "en-NZ": "en-NZ",
                "en-CA": "en-CA",
                "en-IE": "en-IE",
                "es": "es",
                "es-419": "es-419",
                "fr": "fr",
                "fr-CA": "fr-CA",
                "de": "de",
                "de-CH": "de-CH",
                "it": "it",
                "pt": "pt",
                "pt-BR": "pt-BR",
                "pt-PT": "pt-PT",
                "nl": "nl",
                "nl-BE": "nl-BE",
                "hi": "hi",
                "hi-Latn": "hi-Latn",
                "ja": "ja",
                "ko": "ko",
                "ko-KR": "ko-KR",
                "zh": "zh",
                "zh-CN": "zh-CN",
                "zh-Hans": "zh-Hans",
                "zh-TW": "zh-TW",
                "zh-Hant": "zh-Hant",
                "zh-HK": "zh-HK",
                "ru": "ru",
                "uk": "uk",
                "tr": "tr",
                "da": "da",
                "da-DK": "da-DK",
                "sv": "sv",
                "sv-SE": "sv-SE",
                "no": "no",
                "fi": "fi",
                "pl": "pl",
                "id": "id",
                "ms": "ms",
                "th": "th",
                "th-TH": "th-TH",
                "vi": "vi",
                "ar": "ar",
                "bg": "bg",
                "ca": "ca",
                "cs": "cs",
                "et": "et",
                "el": "el",  # Greek
                "hu": "hu",
                "lv": "lv",
                "lt": "lt",
                "ro": "ro",
                "sk": "sk",
            }

            if self.language in language_map:
                deepgram_language = language_map[self.language]
                params.append(f"language={deepgram_language}")
            else:
                # Language not supported by Deepgram - don't specify language and let it auto-detect
                logger.warning(
                    f"Language '{self.language}' is not supported by Deepgram. "
                    f"Using auto-detection instead."
                )

        # Note: Deepgram doesn't have built-in translation like Gemini
        # Translation would need to be done as a separate step if needed
        if self.translate_to and self.translate_to != "none":
            logger.warning(
                f"Deepgram does not support built-in translation. "
                f"Translation from {self.language} to {self.translate_to} will be skipped."
            )

        url = f"{base_url}?{'&'.join(params)}"
        return url

    async def _connect(self):
        """Connect to Deepgram WebSocket API"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                raise RuntimeError("websockets package not installed")

            logger.info(f"Connecting to Deepgram with URL: {self.websocket_url}")

            # Connect with authorization header
            # Note: extra_headers is passed as additional_headers in newer websockets versions
            self.websocket = await websockets.connect(
                self.websocket_url,
                additional_headers={"Authorization": f"Token {self.api_key}"},
                ping_interval=5,  # Send ping every 5 seconds
                ping_timeout=10,
            )

            self.connected = True
            self.last_connection_attempt = 0  # Reset backoff

            logger.info(
                f"Connected to Deepgram Streaming API for session {self.session_id[:8]} VFO {self.vfo_number}"
            )

            # Start keepalive task (Deepgram requires messages every 10 seconds)
            self.keepalive_task = asyncio.create_task(self._keepalive_loop())

        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}", exc_info=True)
            self.connected = False
            self.websocket = None
            await self._send_error_to_ui(e)
            raise

    async def _disconnect(self):
        """Disconnect from Deepgram WebSocket API"""
        try:
            # Cancel keepalive task
            if self.keepalive_task and not self.keepalive_task.done():
                self.keepalive_task.cancel()
                try:
                    await self.keepalive_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket
            if self.websocket:
                # Send close message
                try:
                    await self.websocket.send(json.dumps({"type": "CloseStream"}))
                except Exception:
                    pass
                await self.websocket.close()
                self.websocket = None

            self.connected = False
        except Exception as e:
            logger.error(f"Error closing Deepgram connection: {e}")

    async def _keepalive_loop(self):
        """Send keepalive messages to Deepgram every 8 seconds"""
        try:
            while self.connected and self.websocket:
                await asyncio.sleep(8)
                if self.websocket:
                    try:
                        await self.websocket.send(json.dumps({"type": "KeepAlive"}))
                    except Exception:
                        # Connection closed, exit loop
                        break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Keepalive error: {e}")

    def _prepare_audio_payload(self, audio_data: np.ndarray) -> bytes:
        """Preprocess PCM in worker thread to avoid blocking asyncio loop."""
        normalized = self._normalize_audio(audio_data, target_level=0.7)
        resampled = self._resample_audio(normalized, target_rate=16000)
        audio_int16 = np.clip(resampled * 32767, -32768, 32767).astype(np.int16)
        return bytes(audio_int16.tobytes())

    async def _send_audio_to_provider(self, audio_payload: bytes):
        """Send prepared audio payload to Deepgram WebSocket"""
        if self.websocket is None:
            raise RuntimeError("Deepgram WebSocket not connected")

        await self.websocket.send(audio_payload)

    async def _receive_loop(self):
        """Receive transcription results from Deepgram"""
        try:
            while self.running and self.connected and self.websocket:
                try:
                    # Receive message from WebSocket
                    message = await self.websocket.recv()

                    # Parse JSON response
                    response = json.loads(message)

                    # Handle different message types
                    msg_type = response.get("type")

                    if msg_type == "Results":
                        # Transcription result
                        channel = response.get("channel", {})
                        alternatives = channel.get("alternatives", [])

                        if alternatives:
                            alternative = alternatives[
                                0
                            ]  # Use first alternative (highest confidence)
                            transcript = alternative.get("transcript", "").strip()
                            confidence = alternative.get("confidence", 0.0)

                            if transcript:
                                # Determine if this is a final result
                                is_final = response.get("is_final", False)
                                speech_final = response.get("speech_final", False)
                                is_complete = is_final or speech_final

                                # Get language (Deepgram provides detected language)
                                detected_language = (
                                    self.language if self.language != "auto" else "en"
                                )
                                if "language" in channel:
                                    detected_language = channel.get("language", detected_language)

                                # Emit transcription
                                await self._emit_transcription(
                                    text=transcript,
                                    language=detected_language,
                                    is_final=is_complete,
                                    confidence=confidence,
                                )

                    elif msg_type == "Metadata":
                        # Metadata (connection info, model info, etc.)
                        logger.debug(f"Deepgram metadata: {response}")

                    elif msg_type == "UtteranceEnd":
                        # End of utterance detected
                        logger.debug("Deepgram detected end of utterance")

                    elif msg_type == "SpeechStarted":
                        # Speech started event
                        logger.debug("Deepgram detected speech start")

                    elif msg_type == "Error":
                        # Error message
                        error_msg = response.get("message", "Unknown error")
                        logger.error(f"Deepgram error: {error_msg}")
                        self.connected = False
                        break

                except websockets.exceptions.ConnectionClosed:
                    logger.info("Deepgram WebSocket connection closed")
                    self.connected = False
                    break

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Deepgram response: {e}")
                    continue

                except Exception as e:
                    logger.error(f"Receiver error: {e}", exc_info=True)
                    self.connected = False
                    break

        except Exception as e:
            logger.error(f"Deepgram receiver error: {e}")
            self.connected = False

    async def _translate_text(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Translate text using Google Cloud Translation API REST endpoint.

        Args:
            text: Text to translate
            source_lang: Source language code (e.g., "es", "fr")
            target_lang: Target language code (e.g., "en", "de")

        Returns:
            Translated text or None if translation fails
        """
        if not self.google_translate_api_key:
            logger.warning("Google Translate API key not configured, skipping translation")
            return None

        try:
            # Prepare the request payload
            payload = {
                "q": text,
                "target": target_lang,
                "format": "text",
            }

            # Add source language if not auto-detect
            if source_lang and source_lang != "auto":
                payload["source"] = source_lang

            # Make async HTTP request to Google Translate API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.translate_api_url,
                    params={"key": self.google_translate_api_key},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5.0),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text: str = result["data"]["translations"][0]["translatedText"]
                        logger.debug(
                            f"Translated '{text}' from {source_lang} to {target_lang}: '{translated_text}'"
                        )
                        return translated_text
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Google Translate API error (status {response.status}): {error_text}"
                        )
                        return None

        except asyncio.TimeoutError:
            logger.warning("Google Translate API timeout, skipping translation")
            return None
        except Exception as e:
            logger.error(f"Translation error: {e}", exc_info=True)
            return None

    async def _emit_transcription(
        self, text: str, language: str, is_final: bool, confidence: Optional[float] = None
    ):
        """
        Override to add translation step for Deepgram transcriptions.

        Args:
            text: Transcribed text
            language: Detected/configured language code
            is_final: Whether this is a final or partial transcription
            confidence: Optional confidence score (0.0 to 1.0)
        """
        # If translation is requested and enabled
        if self.translate_to and self.translate_to != "none" and self.translate_to != language:
            try:
                translated_text = await self._translate_text(text, language, self.translate_to)
                if translated_text:
                    # Emit translated text with original language preserved
                    await super()._emit_transcription(
                        translated_text, language, is_final, confidence
                    )
                else:
                    # Translation failed, emit original text
                    logger.debug("Translation failed, emitting original text")
                    await super()._emit_transcription(text, language, is_final, confidence)
            except Exception as e:
                logger.warning(f"Translation failed: {e}, emitting original text")
                await super()._emit_transcription(text, language, is_final, confidence)
        else:
            # No translation needed
            await super()._emit_transcription(text, language, is_final, confidence)

    def stop(self):
        """Stop the Deepgram worker"""
        super().stop()

        # Close WebSocket connection
        if self.websocket and self.provider_loop:
            try:
                asyncio.run_coroutine_threadsafe(self._disconnect(), self.provider_loop)
            except Exception as e:
                logger.error(f"Error closing Deepgram WebSocket: {e}")
