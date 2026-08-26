"""Variety/dedup context for the prompt.

V1: a simple exclusion list of recently suggested dish *names*, injected
into the system prompt with an explicit instruction to vary. Semantic
(embeddings) dedup for reworded near-duplicates ("chicken curry" vs
"coconut curry chicken") is deliberately deferred — see the project plan —
which is exactly why this sits behind the `DedupProvider` interface: a
future embeddings-based implementation can replace
`RecentDishNamesDedupProvider` without `agent/loop.py` or
`agent/prompts.py` changing at all.
"""

from typing import Protocol


class DedupProvider(Protocol):
    def get_exclusion_context(self) -> str:
        """Returns prompt-ready text describing what to avoid repeating,
        or `""` if there's no history yet (nothing to exclude).
        """
        ...


class _DishNameSource(Protocol):
    """What `RecentDishNamesDedupProvider` needs from a repository —
    narrower than depending on the concrete `SuggestionRepository` class,
    so a test fake satisfies it just by having the right method.
    """

    def list_recent_dish_names(self, limit: int) -> list[str]: ...


class RecentDishNamesDedupProvider:
    """V1 implementation: the last `history_window_n` dish names."""

    def __init__(self, repository: _DishNameSource, history_window_n: int) -> None:
        self._repository = repository
        self._history_window_n = history_window_n

    def get_exclusion_context(self) -> str:
        names = self._repository.list_recent_dish_names(limit=self._history_window_n)
        unique_names = list(dict.fromkeys(names))  # preserve order, drop repeats
        if not unique_names:
            return ""

        listed = ", ".join(f'"{name}"' for name in unique_names)
        return (
            f"Recently suggested dishes to avoid repeating: {listed}. "
            "Vary your suggestions — don't propose the same dish again."
        )
