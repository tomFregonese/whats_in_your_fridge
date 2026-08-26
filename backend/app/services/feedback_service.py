"""Records post-meal feedback for one suggestion.

Ties into the soft-preferences context (see the project plan): whenever a
comment is given, it's also saved as a `preference_note` (`source =
feedback`) attributed to the dish it's about, so `SuggestionService`'s
system prompt picks it up on future generations the same way it already
does for onboarding/manual notes — no separate wiring needed on that side.

A `liked`-only submission (no comment) is *not* turned into a note: V1
doesn't structure "liked/disliked" as its own signal (see the project
plan's V2 backlog) — only the user's own words become prompt context.
"""

from datetime import UTC, datetime

from app.domain.feedback import Feedback
from app.domain.preference_note import PreferenceNote, PreferenceSource
from app.persistence.repositories.feedback_repository import FeedbackRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.services.exceptions import NotFoundError


class FeedbackService:
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        suggestion_repository: SuggestionRepository,
        preference_repository: PreferenceNoteRepository,
    ) -> None:
        self._feedback_repository = feedback_repository
        self._suggestion_repository = suggestion_repository
        self._preference_repository = preference_repository

    def save(self, suggestion_id: int, *, liked: bool | None, comment: str | None) -> Feedback:
        suggestion = self._suggestion_repository.get_suggestion(suggestion_id)
        if suggestion is None:
            raise NotFoundError(f"Suggestion {suggestion_id} does not exist.")

        saved = self._feedback_repository.upsert(
            Feedback(id=None, suggestion_id=suggestion_id, liked=liked, comment=comment)
        )

        stripped_comment = comment.strip() if comment else None
        if stripped_comment:
            self._preference_repository.add(
                PreferenceNote(
                    id=None,
                    content=self._note_content(
                        dish_name=suggestion.dish_name, liked=liked, comment=stripped_comment
                    ),
                    source=PreferenceSource.FEEDBACK,
                    created_at=datetime.now(UTC),
                )
            )

        return saved

    @staticmethod
    def _note_content(*, dish_name: str, liked: bool | None, comment: str) -> str:
        if liked is True:
            return f'Liked "{dish_name}": {comment}'
        if liked is False:
            return f'Disliked "{dish_name}": {comment}'
        return f'About "{dish_name}": {comment}'
