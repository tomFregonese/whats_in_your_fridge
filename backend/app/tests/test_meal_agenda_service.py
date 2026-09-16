from app.domain.suggestion import AgendaStorage
from app.services.meal_agenda_service import DishForAgenda, build_agenda


def test_empty_dishes_yields_empty_agenda() -> None:
    assert build_agenda([], days=5, freezer_capacity_slots=None) == []


def test_non_positive_days_yields_empty_agenda() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Soup", fridge_days=3, freezer_friendly=False)
    ]

    assert build_agenda(dishes, days=0, freezer_capacity_slots=None) == []


def test_single_dish_within_fridge_life_stays_fresh_every_day() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Soup", fridge_days=5, freezer_friendly=False)
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    assert [e.day_index for e in agenda] == [0, 1, 2]
    assert all(e.suggestion_id == 1 for e in agenda)
    assert all(e.storage == AgendaStorage.FRESH for e in agenda)


def test_most_perishable_dish_scheduled_first() -> None:
    # Two dishes, two days: the 1-day dish must land on day 0 (eaten
    # immediately), the 5-day dish on day 1 — not insertion order.
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Stew", fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, dish_name="Salad", fridge_days=1, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day[0] == 2
    assert by_day[1] == 1


def test_more_dishes_than_days_shares_a_day() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Dish 1", fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, dish_name="Dish 2", fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=3, dish_name="Dish 3", fridge_days=5, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    day_indexes = sorted(e.day_index for e in agenda)
    assert day_indexes == [0, 0, 1]


def test_fewer_dishes_than_days_repeats_across_remaining_days_with_a_warning() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Pasta", fridge_days=5, freezer_friendly=False)
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    assert [e.suggestion_id for e in agenda] == [1, 1, 1]
    assert [e.day_index for e in agenda] == [0, 1, 2]
    # The first occurrence is a fresh placement — no "no variant" warning.
    assert agenda[0].warning is None
    # Every subsequent occurrence is a literal repeat — always flagged,
    # even while the food is still safe to eat (this is a variety
    # requirement, not a food-safety one).
    for entry in agenda[1:]:
        assert entry.warning is not None
        assert '"Pasta"' in entry.warning
        assert "no new variant" in entry.warning.lower()


def test_dish_past_fridge_life_goes_to_freezer_when_friendly_and_capacity_allows() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Chili", fridge_days=2, freezer_friendly=True)
    ]

    agenda = build_agenda(dishes, days=5, freezer_capacity_slots=5)

    assert [e.storage for e in agenda] == [
        AgendaStorage.FRESH,
        AgendaStorage.FRESH,
        AgendaStorage.FRESH,
        AgendaStorage.FROZEN,
        AgendaStorage.FROZEN,
    ]
    # Every repeat past the first placement is flagged as a literal repeat
    # now, even once it's frozen — see the test above.
    assert agenda[0].warning is None
    for entry in agenda[1:]:
        assert entry.warning is not None
        assert "no new variant" in entry.warning.lower()


def test_dish_past_fridge_life_is_at_risk_when_not_freezer_friendly() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Salad", fridge_days=1, freezer_friendly=False)
    ]

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
        DishForAgenda(suggestion_id=1, dish_name="Dish 1", fridge_days=0, freezer_friendly=True),
        DishForAgenda(suggestion_id=2, dish_name="Dish 2", fridge_days=0, freezer_friendly=True),
        DishForAgenda(suggestion_id=3, dish_name="Dish 3", fridge_days=0, freezer_friendly=True),
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=1)

    storages = [e.storage for e in agenda]
    assert storages == [AgendaStorage.FRESH, AgendaStorage.FROZEN, AgendaStorage.AT_RISK]
    at_risk = agenda[2]
    assert at_risk.warning is not None
    assert "no freezer space left" in at_risk.warning


def test_entries_are_sorted_by_day_index() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Dish 1", fridge_days=1, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, dish_name="Dish 2", fridge_days=5, freezer_friendly=False),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    assert [e.day_index for e in agenda] == sorted(e.day_index for e in agenda)


# --- Leftover-transformation chains ---


def test_leftover_transformation_is_scheduled_right_after_its_source() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Pasta", fridge_days=5, freezer_friendly=False),
        DishForAgenda(
            suggestion_id=2,
            dish_name="Pasta gratin",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        ),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    by_day = {e.day_index: e for e in agenda}
    assert by_day[0].suggestion_id == 1
    assert by_day[1].suggestion_id == 2
    # A fresh transformation, not a literal repeat — no "no variant" warning.
    assert by_day[1].warning is None


def test_multi_level_leftover_chain_is_flattened_in_order() -> None:
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Pasta", fridge_days=5, freezer_friendly=False),
        DishForAgenda(
            suggestion_id=2,
            dish_name="Pasta salad",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        ),
        DishForAgenda(
            suggestion_id=3,
            dish_name="Pasta gratin",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=2,
        ),
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day == {0: 1, 1: 2, 2: 3}
    assert all(e.warning is None for e in agenda)


def test_chain_placed_before_a_shorter_root_chain_when_more_perishable() -> None:
    # The chain rooted at the 1-day dish must come first, day-for-day,
    # ahead of the standalone 5-day dish — chains are ordered by their
    # root's perishability, same rule as plain dishes.
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Stew", fridge_days=5, freezer_friendly=False),
        DishForAgenda(suggestion_id=2, dish_name="Salad", fridge_days=1, freezer_friendly=False),
        DishForAgenda(
            suggestion_id=3,
            dish_name="Salad soup",
            fridge_days=1,
            freezer_friendly=False,
            leftover_of_suggestion_id=2,
        ),
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day == {0: 2, 1: 3, 2: 1}


def test_leftover_link_to_unknown_dish_is_dropped() -> None:
    dishes = [
        DishForAgenda(
            suggestion_id=1,
            dish_name="Pasta gratin",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=999,
        )
    ]

    agenda = build_agenda(dishes, days=1, freezer_capacity_slots=None)

    assert [e.suggestion_id for e in agenda] == [1]
    assert agenda[0].warning is None


def test_self_referential_leftover_link_is_dropped() -> None:
    dishes = [
        DishForAgenda(
            suggestion_id=1,
            dish_name="Pasta",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        )
    ]

    agenda = build_agenda(dishes, days=1, freezer_capacity_slots=None)

    assert [e.suggestion_id for e in agenda] == [1]


def test_cyclical_leftover_link_is_dropped() -> None:
    # 1 claims to reuse 2's leftovers, and 2 claims to reuse 1's — accepting
    # both would create a cycle. Dish 1 is processed first (lower id), so
    # its claim (1 is a child of 2) is accepted; 2's reverse claim would
    # close the cycle and is dropped, leaving 2 as the root and 1 as its
    # one valid child.
    dishes = [
        DishForAgenda(
            suggestion_id=1,
            dish_name="Pasta",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=2,
        ),
        DishForAgenda(
            suggestion_id=2,
            dish_name="Pasta gratin",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        ),
    ]

    agenda = build_agenda(dishes, days=2, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day == {0: 2, 1: 1}


def test_only_first_claim_on_a_shared_parent_is_kept() -> None:
    # Both 2 and 3 claim to reuse 1's leftovers — only 2 (lower id) is kept
    # as a chained child, 3 is degraded to its own root.
    dishes = [
        DishForAgenda(suggestion_id=1, dish_name="Pasta", fridge_days=5, freezer_friendly=False),
        DishForAgenda(
            suggestion_id=2,
            dish_name="Pasta gratin",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        ),
        DishForAgenda(
            suggestion_id=3,
            dish_name="Pasta soup",
            fridge_days=5,
            freezer_friendly=False,
            leftover_of_suggestion_id=1,
        ),
    ]

    agenda = build_agenda(dishes, days=3, freezer_capacity_slots=None)

    by_day = {e.day_index: e.suggestion_id for e in agenda}
    assert by_day[0] == 1
    assert by_day[1] == 2
    assert by_day[2] == 3
    # Dish 3 was degraded to a root — not a literal repeat.
    assert agenda[2].warning is None
