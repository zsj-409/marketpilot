"""Prompt contracts and deterministic rendering."""

from hashlib import sha256
from string import Template

from pydantic import BaseModel, ConfigDict, Field


class PromptSpec(BaseModel):
    """A versioned prompt template."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=20)
    description: str = Field(min_length=1, max_length=1000)
    template: str = Field(min_length=1, max_length=20000)


class RenderedPrompt(BaseModel):
    """A deterministic rendered prompt with metadata."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    text: str
    prompt_hash: str = Field(min_length=64, max_length=64)


class PromptRegistry:
    """Store and render versioned prompts."""

    def __init__(self, prompts: dict[str, PromptSpec] | None = None) -> None:
        self._prompts = prompts or {}

    def register(self, prompt: PromptSpec) -> None:
        if prompt.name in self._prompts:
            raise ValueError(f"prompt already registered: {prompt.name}")
        self._prompts[prompt.name] = prompt

    def get(self, name: str) -> PromptSpec:
        try:
            return self._prompts[name]
        except KeyError as exc:
            raise KeyError(f"unknown prompt: {name}") from exc

    def render(self, name: str, variables: dict[str, str]) -> RenderedPrompt:
        prompt = self.get(name)
        try:
            text = Template(prompt.template).substitute(variables)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"failed to render prompt {name}: {exc}") from exc
        return RenderedPrompt(
            name=prompt.name,
            version=prompt.version,
            text=text,
            prompt_hash=sha256(text.encode()).hexdigest(),
        )

    def names(self) -> list[str]:
        return sorted(self._prompts)
