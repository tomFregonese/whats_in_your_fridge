from sqlalchemy import ColumnElement
from sqlmodel import Session, select

from app.domain.feedback import Feedback
from app.persistence.entities.feedback_entity import FeedbackEntity


class FeedbackRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_suggestion(self, suggestion_id: int) -> Feedback | None:
        entity = self._get_entity(suggestion_id)
        return entity.to_domain() if entity is not None else None

    def upsert(self, feedback: Feedback) -> Feedback:
        """At most one feedback row per suggestion (DB-enforced — see
        `FeedbackEntity.suggestion_id`'s `unique=True`): updates the
        existing row in place if the user changes their mind, rather than
        erroring on a second submission.
        """
        existing = self._get_entity(feedback.suggestion_id)
        if existing is None:
            entity = FeedbackEntity.from_domain(feedback)
            self._session.add(entity)
        else:
            existing.liked = feedback.liked
            existing.comment = feedback.comment
            entity = existing

        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def _get_entity(self, suggestion_id: int) -> FeedbackEntity | None:
        # Same class-level field access typing gap noted elsewhere.
        condition: ColumnElement[bool] = (
            FeedbackEntity.suggestion_id == suggestion_id  # type: ignore[assignment]
        )
        return self._session.exec(select(FeedbackEntity).where(condition)).first()
