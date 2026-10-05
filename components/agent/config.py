"""config — which model plays which part, and what a request may spend.

Read from one file, `config/agent.yaml` (or wherever UNITI_AGENT_CONFIG
points). Nothing else in the agent names a provider or a model: the builder
and the accountant are handed whatever the file says, and a test hands them a
model of its own instead.

    parts     builder, accountant: a model, and optional settings for it
    timeout   seconds one call to a model may take, whichever part makes it
    budget    requests, tokens and dollars one request from the person may
              spend, every part together
    prices    dollars per million tokens, by model
    history   how long a conversation grows, in tokens the provider counted
              for its last call, before readings read again since are cleared
              (`clear_above`; `conversation.cleared`)

A part can be given another model for one run (`with_models`), which is how an
eval compares two models on the same part without editing the file.
"""

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
FILE = ROOT / "config" / "agent.yaml"

PARTS = ("builder", "accountant")

# Where clearing starts when the file does not say: well short of what the
# models take, long enough that an ordinary request never reaches it.
CLEAR_ABOVE = 100_000


@dataclass(frozen=True)
class Part:
    """One part of the agent, and the model that plays it."""

    name: str
    model: object
    settings: dict = field(default_factory=dict)

    @property
    def label(self):
        """The model's name as the file writes it, for prices and reports."""
        return self.model if isinstance(self.model, str) \
            else getattr(self.model, "model_name", type(self.model).__name__)


@dataclass(frozen=True)
class Budget:
    """What one request may spend. None is no limit on that measure."""

    requests: int | None = None
    tokens: int | None = None
    dollars: float | None = None


@dataclass(frozen=True)
class Config:
    parts: dict
    budget: Budget = Budget()
    prices: dict = field(default_factory=dict)
    timeout: float | None = None
    clear_above: int | None = CLEAR_ABOVE

    def part(self, name):
        return self.parts[name]

    def settings(self, name):
        """What the framework is handed for a part's calls, or None."""
        settings = dict(self.parts[name].settings)
        if self.timeout is not None:
            settings.setdefault("timeout", self.timeout)
        return settings or None

    def cost(self, part, usage):
        """What a run's `usage` cost in dollars, or None when the part's model
        has no price here. Input the provider served from its cache is charged
        at the `cached` price where one is written, else as any input."""
        price = self.prices.get(self.parts[part].label)
        if price is None:
            return None
        cached = cached_tokens(usage)
        return ((usage.input_tokens - cached) * price["input"]
                + cached * price.get("cached", price["input"])
                + usage.output_tokens * price["output"]) / 1e6

    def with_models(self, **models):
        """The same configuration with some parts played by other models.
        A model a test builds is taken as it is; a name gets no settings,
        because the settings in the file were written for another model."""
        parts = dict(self.parts)
        for name, model in models.items():
            if model is None:
                continue
            if name not in PARTS:
                raise ValueError(f"no part called {name}; the parts are {', '.join(PARTS)}")
            parts[name] = Part(name, model, {} if isinstance(model, str)
                               and model != parts[name].model else parts[name].settings)
        return replace(self, parts=parts)


def load(path=None):
    """The configuration in the file, checked for what the agent needs."""
    path = Path(path or os.environ.get("UNITI_AGENT_CONFIG") or FILE)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    given = raw.get("parts") or {}
    missing = [name for name in PARTS if not (given.get(name) or {}).get("model")]
    if missing:
        raise ValueError(f"{path}: no model for {', '.join(missing)}; each of "
                         f"{', '.join(PARTS)} needs `model: provider:name`")
    parts = {name: Part(name, given[name]["model"], dict(given[name].get("settings") or {}))
             for name in PARTS}
    budget = Budget(**{k: v for k, v in (raw.get("budget") or {}).items()
                       if k in ("requests", "tokens", "dollars")})
    prices = {model: {k: float(p[k]) for k in ("input", "cached", "output") if k in p}
              for model, p in (raw.get("prices") or {}).items()}
    timeout = raw.get("timeout")
    history = raw.get("history") or {}
    clear_above = history.get("clear_above", CLEAR_ABOVE)
    return Config(parts=parts, budget=budget, prices=prices,
                  timeout=None if timeout is None else float(timeout),
                  clear_above=None if clear_above is None else int(clear_above))


def cached_tokens(usage):
    """Input tokens the provider served from its cache: the framework's own
    count, or the provider's where the framework has none."""
    return usage.cache_read_tokens or (usage.details or {}).get("cached_content_tokens", 0)


def unlimited(**models):
    """A configuration with no file behind it: every part on the model given,
    nothing priced, nothing limited. What tests build agents from."""
    return Config(parts={name: Part(name, models.get(name)) for name in PARTS})


__all__ = ["Budget", "CLEAR_ABOVE", "Config", "PARTS", "Part", "cached_tokens", "load", "unlimited"]
