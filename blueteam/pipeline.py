import yaml
from dotenv import load_dotenv

load_dotenv()

from blueteam.input_guard import InputGuard
from blueteam.isolation import wrap_user_input, tag_untrusted, build_hardened_system
from blueteam.output_guard import OutputGuard


class DefensePipeline:
    """Chains three defense layers: input_guard -> isolation -> output_guard.

    Call .protect(user_input, butler_fn) to run a defended request.
    butler_fn is any callable that takes a string and returns a dict with
    {"response": str, "tool_calls": list}.
    """

    def __init__(self, config_path: str = "blueteam/configs/defense.yaml"):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        self.enforce = cfg.get("enforce", True)
        self.canary_tokens = cfg.get("canary_tokens", [])
        self.secret_phrases = cfg.get("secret_phrases", [])
        self.forbidden_tools = cfg.get("forbidden_tools", [])

        self.input_guard = InputGuard(enforce=self.enforce)
        self.output_guard = OutputGuard(
            canary_tokens=self.canary_tokens,
            secret_phrases=self.secret_phrases,
            forbidden_tools=self.forbidden_tools,
        )

    def protect(self, user_input: str, butler_fn, system_prompt: str = None) -> dict:
        """Run a defended request end-to-end.

        Returns:
            {
                "blocked": bool,
                "block_layer": None | "input" | "output",
                "reason": str,
                "response": str | None,
                "original_input": str,
            }
        """
        # L1: input guard
        input_blocked, input_reason = self.input_guard.check(user_input)
        if input_blocked and self.enforce:
            return {
                "blocked": True,
                "block_layer": "input",
                "reason": input_reason,
                "response": None,
                "original_input": user_input,
            }

        # L2: isolation — wrap input before sending to butler
        wrapped = wrap_user_input(user_input)

        # Call the butler
        try:
            butler_output = butler_fn(wrapped)
        except Exception as e:
            return {
                "blocked": False,
                "block_layer": None,
                "reason": f"butler_error:{e}",
                "response": None,
                "original_input": user_input,
            }

        response_text = butler_output.get("response", "")
        tool_calls = butler_output.get("tool_calls", [])

        # L3: output guard
        output_blocked, output_reason = self.output_guard.check(response_text, tool_calls)
        if output_blocked and self.enforce:
            sanitized = self.output_guard.sanitize(response_text)
            return {
                "blocked": True,
                "block_layer": "output",
                "reason": output_reason,
                "response": sanitized,
                "original_input": user_input,
            }

        return {
            "blocked": False,
            "block_layer": None,
            "reason": "clean",
            "response": response_text,
            "original_input": user_input,
        }
