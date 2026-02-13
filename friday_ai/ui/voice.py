"""Voice I/O - Voice input and output for the TUI."""

import asyncio
import sys
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class VoiceInput:
    """Voice input handler using speech recognition."""

    def __init__(self, engine: str = "auto"):
        """Initialize voice input.

        Args:
            engine: Recognition engine to use ("sphinx", "google", "whisper", "auto").
        """
        self.engine = engine
        self._recognizer = None
        self._is_listening = False

    async def initialize(self) -> bool:
        """Initialize the voice recognition engine.

        Returns:
            True if initialization was successful.
        """
        try:
            # Try to import speech recognition
            import speech_recognition as sr

            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True

            logger.info(f"Voice input initialized with engine: {self.engine}")
            return True

        except ImportError:
            logger.warning("speech_recognition not installed. Voice input unavailable.")
            return False

    async def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input.

        Args:
            timeout: Maximum time to listen in seconds.

        Returns:
            Recognized text or None.
        """
        if not self._recognizer:
            return None

        try:
            import speech_recognition as sr

            # Show listening indicator
            print("\n\033[96m🎤 Listening...\033[0m", flush=True)
            sys.stdout.flush()

            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source)
                audio = self._recognizer.listen(source, timeout=timeout)

            # Clear the listening indicator
            print("\r\033[F\033[K", end="", flush=True)

            # Recognize using specified engine
            if self.engine == "sphinx":
                return self._recognizer.recognize_sphinx(audio)
            elif self.engine == "google":
                return self._recognizer.recognize_google(audio)
            elif self.engine == "whisper":
                try:
                    return self._recognizer.recognize_whisper(audio)
                except AttributeError:
                    return self._recognizer.recognize_google(audio)
            else:
                # Auto-detect
                return self._recognizer.recognize_google(audio)

        except KeyboardInterrupt:
            logger.info("Voice input interrupted by user")
            # Clear the listening indicator on interrupt
            print("\r\033[F\033[K", end="", flush=True)
            return None
        except Exception as e:
            logger.error(f"Voice recognition error: {e}")
            # Clear the listening indicator on error
            print("\r\033[F\033[K", end="", flush=True)
            return None

    async def listen_continuous(
        self,
        on_result: Callable[[str], None],
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Listen continuously for voice input.

        Args:
            on_result: Callback when text is recognized.
            on_error: Callback on errors.
        """
        if not self._recognizer:
            return

        try:
            import speech_recognition as sr

            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source)
                self._is_listening = True

                # Show listening indicator
                print("\n\033[96m🎤 Listening continuously (Press Ctrl+C to stop)...\033[0m", flush=True)
                sys.stdout.flush()

                while self._is_listening:
                    try:
                        audio = self._recognizer.listen(source, timeout=1)
                        text = self._recognizer.recognize_google(audio)
                        if text:
                            on_result(text)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        if on_error:
                            on_error(e)

        except KeyboardInterrupt:
            # User interrupted
            print("\n\033[90mStopped listening.\033[0m", flush=True)
        except Exception as e:
            logger.error(f"Continuous listening error: {e}")
            # Clear the listening indicator on error
            print("\n\033[90mStopped listening due to error.\033[0m", flush=True)
        finally:
            # Final cleanup
            self._is_listening = False

    def stop(self) -> None:
        """Stop listening."""
        self._is_listening = False


class VoiceOutput:
    """Voice output handler using text-to-speech."""

    def __init__(self, engine: str = "auto", rate: int = 150, voice: Optional[str] = None):
        """Initialize voice output.

        Args:
            engine: TTS engine to use ("pyttsx3", "gtts", "auto").
            rate: Speech rate (words per minute).
            voice: Voice to use (if supported).
        """
        self.engine = engine
        self.rate = rate
        self.voice = voice
        self._engine = None

    async def initialize(self) -> bool:
        """Initialize the TTS engine.

        Returns:
            True if initialization was successful.
        """
        try:
            # Try pyttsx3 first (offline)
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)

            if self.voice:
                voices = self._engine.getProperty("voices")
                for v in voices:
                    if self.voice.lower() in v.name.lower():
                        self._engine.setProperty("voice", v.id)
                        break

            logger.info("Voice output initialized with pyttsx3")
            return True

        except ImportError:
            try:
                # Try gTTS (online)
                from gtts import gTTS

                self._engine = "gtts"
                logger.info("Voice output initialized with gTTS")
                return True
            except ImportError:
                logger.warning("No TTS engine available. Voice output unavailable.")
                return False

    async def speak(self, text: str, blocking: bool = True) -> None:
        """Speak the given text.

        Args:
            text: Text to speak.
            blocking: Whether to wait for speech to complete.
        """
        if not self._engine:
            return

        if self._engine == "gtts":
            # gTTS (online)
            try:
                from gtts import gTTS
                import io

                tts = gTTS(text=text, lang="en")
                audio_data = io.BytesIO()
                tts.write_to_fp(audio_data)
                audio_data.seek(0)

                # Play using pygame or similar
                # For now, just log
                logger.info(f"Would speak (gTTS): {text[:50]}...")

            except Exception as e:
                logger.error(f"gTTS error: {e}")

        else:
            # pyttsx3 (offline)
            try:
                self._engine.say(text)
                if blocking:
                    self._engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")

    async def speak_streaming(
        self,
        text: str,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Speak text with chunk callbacks.

        Args:
            text: Full text to speak.
            on_chunk: Called for each chunk spoken.
        """
        # Simple chunking by sentences
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            if sentence.strip():
                await self.speak(sentence, blocking=True)
                if on_chunk:
                    on_chunk(sentence)

    def set_rate(self, rate: int) -> None:
        """Set speech rate.

        Args:
            rate: Words per minute.
        """
        self.rate = rate
        if self._engine and self._engine != "gtts":
            self._engine.setProperty("rate", rate)

    def stop(self) -> None:
        """Stop speaking."""
        if self._engine and self._engine != "gtts":
            try:
                self._engine.stop()
            except Exception:
                pass


class VoiceManager:
    """Manager for voice input and output."""

    def __init__(self):
        """Initialize the voice manager."""
        self.input = VoiceInput()
        self.output = VoiceOutput()
        self._is_enabled = False

    async def initialize(self) -> bool:
        """Initialize both input and output.

        Returns:
            True if both are available.
        """
        input_ok = await self.input.initialize()
        output_ok = await self.output.initialize()

        self._is_enabled = input_ok and output_ok
        return self._is_enabled

    async def voice_to_text(self, timeout: int = 5) -> Optional[str]:
        """Convert voice to text.

        Args:
            timeout: Maximum listening time.

        Returns:
            Recognized text or None.
        """
        if not self._is_enabled:
            return None
        return await self.input.listen(timeout=timeout)

    async def text_to_voice(self, text: str) -> None:
        """Convert text to speech.

        Args:
            text: Text to speak.
        """
        if not self._is_enabled:
            return
        await self.output.speak(text)

    async def voice_conversation(self, prompt: str) -> str:
        """Have a voice conversation.

        Args:
            prompt: Prompt to speak before listening.

        Returns:
            User's spoken response.
        """
        await self.text_to_voice(prompt)
        return await self.voice_to_text() or ""

    def is_available(self) -> bool:
        """Check if voice I/O is available.

        Returns:
            True if voice features are enabled.
        """
        return self._is_enabled

    def get_status(self) -> dict:
        """Get voice manager status.

        Returns:
            Status dictionary.
        """
        return {
            "enabled": self._is_enabled,
            "input_engine": self.input.engine if self.input._recognizer else None,
            "output_engine": self.output.engine if self.output._engine else None,
        }
