import os
import time
from openai import OpenAI
from anthropic import Anthropic


class LLMClient:
    """Unified LLM wrapper. Works with OpenAI, Groq (via OPENAI_BASE_URL), and Anthropic."""

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or os.getenv("DEFAULT_PROVIDER", "openai")
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            base_url = os.getenv("OPENAI_BASE_URL")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            self.client = Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Use 'openai' or 'anthropic'.")

    def chat(self, system: str, user: str, max_retries: int = 3) -> str:
        """Send a chat completion request. Returns the text response."""
        last_error = None
        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    )
                    return resp.choices[0].message.content

                resp = self.client.messages.create(
                    model=self.model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    max_tokens=1024,
                )
                return resp.content[0].text

            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

        raise last_error