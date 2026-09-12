from app.domain.suggestion import AgendaStorage
from app.services.meal_agenda_service import DishForAgenda, build_agenda


def test_empty_dishes_yields_empty_agenda() -> None:
    assert build_agenda([], days=5, freezer_capacity_slots=None) == []


def test_non_positive_days_yields_empty_agenda() -> None:
    dishes = [DishForAgenda(suggestion_id=1, fridge_days=3, freezer_friendly=False)]

    assert build_agenda(dishes, days=0, freezer_capacity_slots=None) == []


def test_single_dish_within_fridge_life_stays_fresh_every_day() -> None:
    dishes = [DishForAgenda(suggestion_id=1, fridge_days=5, freezer_friendly=False)]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    assert [e.day_index for e in agenda] == [0, 1, 2]
    assert all(e.suggestion_id == 1 for e in agenda)
    assert all(e.storage == AgendaStorage.FRESH for e in agenda)


def test_most_perishable_dish_scheduled_first() -> None:
    # Two dishes, two days: the 1-day dish must land on day 0 (eaten
    # immediately), the 5-day dish on day 1 — not insertion order.
    dishes = [
        DishForAgenda(suggestion_id=1, fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, fridge_days=1, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day[0] == 2
    assert by_day[1] == 1


def test_more_dishes_than_days_shares_a_day() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=3, fridge_days=5, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    day_indexes = sorted(e.day_index for e in agenda)
    assert day_indexes == [0, 0, 1]


def test_fewer_dishes_than_days_repeats_across_remaining_days() -> None:
    dishes = [DishForAgenda(suggestion_id=1, fridge_days=5, freezer_friendly=False)]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    assert [e.suggestion_id for e in agenda] == [1, 1, 1]
    assert [e.day_index for e in agenda] == [0, 1, 2]


def test_dish_past_fridge_life_goes_to_freezer_when_friendly_and_capacity_allows() -> None:
    dishes = [DishForAgenda(suggestion_id=1, fridge_days=2, freezer_friendly=True)]

    agenda = build_agenda(dishes, days=5, freezer_capacity_slots=5)

    assert [e.storage for e in agenda] == [
        AgendaStorage.FRESH,
        AgendaStorage.FRESH,
        AgendaStorage.FRESH,
        AgendaStorage.FROZEN,
        AgendaStorage.FROZEN,
    ]
    assert agenda[-1].warning is None


def test_dish_past_fridge_life_is_at_risk_when_not_freezer_friendly() -> None:
    dishes = [DishForAgenda(suggestion_id=1, fridge_days=1, freezer_friendly=False)]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    assert [e.storage for e in agenda] == [
        AgendaStorage.FRESH,
        AgendaStorage.FRESH,
        AgendaStorage.AT_RISK,
    ]
    assert agenda[-1].warning is not None
    assert "doesn't freeze well" in agenda[-1].warning


def test_freezer_capacity_exhausted_falls_back_to_at_risk() -> None:
    # Three freezer-friendly, same-day dishes (fridge_days=0, so only
    # day 0 stays fresh) but only one freezer slot: the second dish past
    # its fridge life gets it, the third is left AT_RISK.
    dishes = [
        DishForAgenda(suggestion_id=1, fridge_days=0, freezer_friendly=True),
        DishForAgenda(suggestion_id=2, fridge_days=0, freezer_friendly=True),
        DishForAgenda(suggestion_id=3, fridge_days=0, freezer_friendly=True),
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=1)

    storages = [e.storage for e in agenda]
    assert storages == [AgendaStorage.FRESH, AgendaStorage.FROZEN, AgendaStorage.AT_RISK]
    at_risk = agenda[2]
    assert at_risk.warning is not None
    assert "no freezer space left" in at_risk.warning


def test_entries_are_sorted_by_day_index() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, fridge_days=1, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, fridge_days=5, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    assert [e.day_index for e in agenda] == sorted(e.day_index for e in agenda)
