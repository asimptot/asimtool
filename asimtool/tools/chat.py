"""Conversational AI chat with history management."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

import g4f

from ..core.provider import Provider, _resolve_providers, DEFAULT_PROVIDER_NAMES


def _clean_branding(text: str) -> str:
    """Remove provider-specific branding from responses."""
    text = text.replace("I'm Aria", "I'm Merlin")
    text = text.replace("I am Aria", "I am Merlin")
    text = text.replace("Aria, your", "Merlin, your")
    text = text.replace("from Opera", "")
    text = text.replace(", powered by cutting-edge AI models from OpenAI and Google", "")
    text = text.replace("powered by cutting-edge AI models from OpenAI and Google", "")
    text = text.replace("your friendly AI assistant from Opera", "your AI assistant")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _needs_web_search(text: str) -> bool:
    """Detect if the message needs web search (real-time info)."""
    text_lower = text.lower()
    keywords = [
        "ara ", "araştır", "search", "google", "bul ", "find ",
        "web'de", "internette", "online",
        "haber", "haberler", "son dakika", "güncel", "bugünkü haber",
        "döviz", "borsa", "hisse", "kripto", "bitcoin", "ethereum",
        "hava durumu", "weather", "forecast",
        "fiyat", "price", "rate", "kur",
        "latest", "breaking", "current event", "recent",
        "live", "canlı", "şu an kaç", "şu anki",
        "kim kazandı", "kim seçildi", "maç sonucu", "skor",
    ]
    return any(kw in text_lower for kw in keywords)


class Chat:
    """Stateful conversational AI assistant.

    Maintains conversation history and supports web search
    auto-detection, speaking practice mode, and language routing.

    Parameters
    ----------
    assistant_name : str
        Name the assistant uses (default ``"Merlin"``).
    model : str
        g4f model identifier (default ``"gpt-4o"``).
    provider : Provider, optional
        Custom provider.
    max_history : int
        Maximum number of messages to retain (default 30).

    Example
    -------
    >>> from asimtool.tools import Chat
    >>> chat = Chat()
    >>> reply = chat.send("Hello! What can you do?")
    >>> print(reply)
    >>> reply = chat.send("Tell me a joke")
    >>> print(reply)
    >>> chat.clear()
    """

    def __init__(
        self,
        assistant_name: str = "Merlin",
        model: str = "gpt-4o",
        provider: Provider | None = None,
        max_history: int = 30,
    ):
        self.assistant_name = assistant_name
        self.model = model
        self.max_history = max_history
        self._history: List[Dict[str, str]] = []
        self._providers = (
            provider.providers if provider else _resolve_providers(DEFAULT_PROVIDER_NAMES)
        )
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        now = datetime.now()
        system_prompt = (
            f"IMPORTANT: You are {self.assistant_name}, a helpful AI assistant. "
            f"Your name is {self.assistant_name} and ONLY {self.assistant_name}. "
            f"Never introduce yourself as any other name. "
            f"Today is {now.strftime('%B %d, %Y')}. "
            "When providing code examples, ALWAYS use markdown code blocks with the language specified. "
            "Provide clear, accurate, and concise responses."
        )
        self._history = [{"role": "system", "content": system_prompt}]

    @property
    def history(self) -> List[Dict[str, str]]:
        """Return a copy of the conversation history."""
        return list(self._history)

    @property
    def message_count(self) -> int:
        return len(self._history)

    def clear(self) -> None:
        """Clear conversation history and reinitialise system prompt."""
        self._init_system_prompt()

    def send(
        self,
        message: str,
        *,
        response_language: str = "English",
        speaking_practice: bool = False,
        web_search: bool | None = None,
    ) -> str:
        """Send a message and get a response.

        Parameters
        ----------
        message : str
            User message.
        response_language : str
            Desired response language.
        speaking_practice : bool
            Enable speaking-practice mode.
        web_search : bool, optional
            Force web search on/off. ``None`` means auto-detect.

        Returns
        -------
        str
            Assistant response.
        """
        if not message.strip():
            raise ValueError("Message cannot be empty.")

        if message.lower() in ("exit", "clear", "reset"):
            self.clear()
            return "Conversation history cleared."

        # Build the user prompt
        if speaking_practice:
            lang_instruction = (
                f"[SPEAKING PRACTICE MODE — You are a friendly native-speaker conversation partner helping the user practice {response_language}. "
                f"Rules: 1) NEVER repeat what the user said. "
                f"2) Respond naturally — ask a follow-up question or share a related thought. "
                f"3) Keep your response short: 2-3 sentences maximum. "
                f"4) Respond ONLY in {response_language}. "
                f"5) If the user makes a mistake, briefly note the correct form.] "
                f"{message}"
            )
        elif response_language and response_language != "English":
            lang_instruction = f"[Please respond in {response_language}] {message}"
        else:
            lang_instruction = message

        self._history.append({"role": "user", "content": lang_instruction})

        # Trim history if too long
        if len(self._history) > self.max_history:
            system = self._history[0]
            self._history = [system] + self._history[-(self.max_history - 1):]

        # Auto-detect web search
        if web_search is None:
            web_search = _needs_web_search(message)

        # Try providers
        for provider in self._providers:
            try:
                response = g4f.ChatCompletion.create(
                    model=self.model,
                    messages=self._history,
                    web_search=web_search,
                    provider=provider,
                )

                text = ""
                if isinstance(response, dict) and "choices" in response:
                    text = response["choices"][0]["message"]["content"]
                elif isinstance(response, str):
                    text = response

                text = _clean_branding(text.strip())

                if text:
                    self._history.append({"role": "assistant", "content": text})
                    return text

            except Exception:
                continue

        raise RuntimeError("All providers failed to respond.")
