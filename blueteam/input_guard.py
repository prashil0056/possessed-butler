class InputGuard:
    """Layer 1: pre-inference input detection.

    Uses prompt-shield-ai if available, falls back to keyword-based heuristics otherwise.
    Both paths return (blocked: bool, reason: str).
    """

    SUSPICIOUS_PATTERNS = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard previous",
        "system override",
        "you are now",
        "from now on you are",
        "reveal your system prompt",
        "print your system prompt",
        "repeat the text above",
        "print the canary",
        "output the canary",
        "reveal the secret",
        "reveal secret_blue",
        "call dump_database",
        "call reveal_system_prompt",
        "call exfiltrate_keys",
    ]

    def __init__(self, enforce: bool = True):
        self.enforce = enforce
        self.shield = None
        try:
            import importlib
            prompt_shield = importlib.import_module("prompt_shield")
            self.shield = getattr(prompt_shield, "PromptShield")()
            self.mode = "prompt_shield"
        except (ImportError, AttributeError, Exception):
            self.mode = "fallback"

    def _scan_fallback(self, user_input: str) -> tuple:
        text_lower = user_input.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in text_lower:
                return True, f"keyword:{pattern}"
        return False, "clean"

    def _scan_shield(self, user_input: str) -> tuple:
        try:
            result = self.shield.scan(user_input)
            if getattr(result, "is_malicious", False):
                return True, f"prompt_shield:{getattr(result, 'reason', 'flagged')}"
        except Exception as e:
            print(f"[input_guard] scan error: {e}")
        return False, "clean"

    def check(self, user_input: str) -> tuple:
        if self.mode == "prompt_shield":
            blocked, reason = self._scan_shield(user_input)
            if blocked:
                return blocked, reason
        blocked, reason = self._scan_fallback(user_input)
        return blocked, reason


def detect(user_input: str, enforce: bool = True) -> tuple:
    guard = InputGuard(enforce=enforce)
    return guard.check(user_input)
