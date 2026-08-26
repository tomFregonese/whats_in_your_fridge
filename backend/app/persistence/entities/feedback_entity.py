from __future__ import annotations

from sqlmodel import Field, SQLModel

from app.domain.feedback import Feedback


class FeedbackEntity(SQLModel, table=True):
    __tablename__ = "feedback"

    id: int | None = Field(default=None, primary_key=True)
    suggestion_id: int = Field(foreign_key="suggestion.id", unique=True)
    liked: bool | None = None
    comment: str | None = None

    def to_domain(self) -> Feedback:
        return Feedback(
            id=self.id,
            suggestion_id=self.suggestion_id,
            liked=self.liked,
            comment=self.comment,
        )

    @classmethod
    def from_domain(cls, feedback: Feedback) -> FeedbackEntity:
        return cls(
            id=feedback.id,
            suggestion_id=feedback.suggestion_id,
            liked=feedback.liked,
            comment=feedback.comment,
        )
