import secrets
import string


def generate_canary() -> str:
    """Generate a random canary token like CANARY_a7f3x9k2."""
    alphabet = string.ascii_lowercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"CANARY_{token}"


def plant_canary(system_prompt: str, canary: str = None) -> tuple:
    """Plant a canary token into a system prompt. Returns (new_prompt, canary)."""
    if canary is None:
        canary = generate_canary()
    new_prompt = system_prompt.rstrip() + f"\n\nCanary token: {canary}\n"
    return new_prompt, canary


def detect_canary_leak(output_text: str, canary: str) -> bool:
    """Return True if the canary token appears in the output text."""
    return canary in output_text
