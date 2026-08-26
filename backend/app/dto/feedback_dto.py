from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator

from app.domain.feedback import Feedback


class FeedbackDtoIn(BaseModel):
    liked: bool | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def _require_liked_or_comment(self) -> Self:
        if self.liked is None and not (self.comment and self.comment.strip()):
            raise ValueError("Provide a thumbs up/down or a comment.")
        return self


class FeedbackDtoOut(BaseModel):
    id: int
    suggestion_id: int
    liked: bool | None
    comment: str | None

    @classmethod
    def from_domain(cls, feedback: Feedback) -> FeedbackDtoOut:
        assert feedback.id is not None, "FeedbackDtoOut requires a persisted Feedback"
        return cls(
            id=feedback.id,
            suggestion_id=feedback.suggestion_id,
            liked=feedback.liked,
            comment=feedback.comment,
        )
