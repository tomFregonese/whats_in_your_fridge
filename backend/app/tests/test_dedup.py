from app.agent.dedup import RecentDishNamesDedupProvider


class _FakeRepository:
    def __init__(self, names: list[str]) -> None:
        self._names = names
        self.requested_limit: int | None = None

    def list_recent_dish_names(self, limit: int) -> list[str]:
        self.requested_limit = limit
        return self._names[:limit]


def test_get_exclusion_context_empty_with_no_history() -> None:
    provider = RecentDishNamesDedupProvider(_FakeRepository([]), history_window_n=10)

    assert provider.get_exclusion_context() == ""


def test_get_exclusion_context_lists_dish_names() -> None:
    provider = RecentDishNamesDedupProvider(
        _FakeRepository(["Carrot soup", "Vegetable fried rice"]), history_window_n=10
    )

    context = provider.get_exclusion_context()

    assert "Carrot soup" in context
    assert "Vegetable fried rice" in context
    assert "vary" in context.lower()


def test_get_exclusion_context_deduplicates_repeated_names() -> None:
    provider = RecentDishNamesDedupProvider(
        _FakeRepository(["Carrot soup", "Carrot soup", "Carrot soup"]), history_window_n=10
    )

    context = provider.get_exclusion_context()

    assert context.count("Carrot soup") == 1


def test_get_exclusion_context_passes_history_window_as_limit() -> None:
    repository = _FakeRepository(["a", "b", "c"])
    provider = RecentDishNamesDedupProvider(repository, history_window_n=2)

    provider.get_exclusion_context()

    assert repository.requested_limit == 2
