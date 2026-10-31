import yaml
from shared.llm_client import LLMClient


class ButlerSim:
    """Configurable LLM butler simulator. Loads a YAML config, responds to input,
    detects tool calls by keyword, and logs every interaction."""

    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.config_path = config_path
        self.llm = LLMClient(
            provider=self.config.get("provider"),
            model=self.config.get("model"),
        )
        self.system_prompt = self.config["system_prompt"]
        self.tools = self.config.get("tools", [])
        self.call_log = []

    def respond(self, user_input: str) -> dict:
        """Send user input to the butler. Returns dict with response text and detected tool calls."""
        full_system = self.system_prompt
        if self.tools:
            full_system += "\n\nAvailable tools: " + ", ".join(self.tools)

        response = self.llm.chat(full_system, user_input)
        response_lower = response.lower()

        # Simple keyword-based tool call detection
        tool_calls = [t for t in self.tools if f"call {t}" in response_lower or f"{t}(" in response_lower]

        record = {
            "input": user_input,
            "response": response,
            "tool_calls": tool_calls,
            "config": self.config_path,
        }
        self.call_log.append(record)

        return {"response": response, "tool_calls": tool_calls}

    def reset_log(self) -> None:
        self.call_log = []

    def get_log(self) -> list:
        return list(self.call_log)