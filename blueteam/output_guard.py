class OutputGuard:
    """Layer 3: post-response leak detection.

    Catches canary leaks, secret phrase leaks, and forbidden tool calls
    after the butler has generated its response.
    """

    def __init__(self, canary_tokens=None, secret_phrases=None, forbidden_tools=None):
        self.canary_tokens = canary_tokens or []
        self.secret_phrases = secret_phrases or []
        self.forbidden_tools = forbidden_tools or []

    def check(self, output_text: str, tool_calls=None) -> tuple:
        """Returns (blocked: bool, reason: str)."""
        tool_calls = tool_calls or []

        for token in self.canary_tokens:
            if token in output_text:
                return True, f"canary_leak:{token}"

        text_lower = output_text.lower()
        for phrase in self.secret_phrases:
            if phrase.lower() in text_lower:
                return True, f"secret_leak:{phrase}"

        for tool in tool_calls:
            if tool in self.forbidden_tools:
                return True, f"forbidden_tool:{tool}"

        return False, "clean"

    def sanitize(self, output_text: str) -> str:
        """Redact canary and secret content from output. Use as fallback when block isn't possible."""
        redacted = output_text
        for token in self.canary_tokens:
            redacted = redacted.replace(token, "[REDACTED_CANARY]")
        for phrase in self.secret_phrases:
            redacted = redacted.replace(phrase, "[REDACTED_SECRET]")
        return redacted
