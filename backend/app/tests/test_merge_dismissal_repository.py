from sqlmodel import Session

from app.persistence.repositories.merge_dismissal_repository import MergeDismissalRepository


def test_dismissed_pair_is_reported_regardless_of_argument_order(session: Session) -> None:
    repo = MergeDismissalRepository(session)
    repo.dismiss("carottes", "carrots")

    assert repo.is_dismissed("carottes", "carrots") is True
    assert repo.is_dismissed("carrots", "carottes") is True


def test_dismissed_pair_is_case_and_whitespace_insensitive(session: Session) -> None:
    repo = MergeDismissalRepository(session)
    repo.dismiss("  Carottes  ", "CARROTS")

    assert repo.is_dismissed("carottes", "carrots") is True


def test_undismissed_pair_reads_back_false(session: Session) -> None:
    repo = MergeDismissalRepository(session)
    repo.dismiss("carottes", "carrots")

    assert repo.is_dismissed("pommes", "pommes de terre") is False


def test_dismissing_twice_does_not_raise(session: Session) -> None:
    repo = MergeDismissalRepository(session)
    first = repo.dismiss("carottes", "carrots")

    second = repo.dismiss("carrots", "carottes")

    assert second.id == first.id
