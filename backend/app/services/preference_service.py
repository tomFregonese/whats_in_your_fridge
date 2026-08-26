from app.domain.preference_note import PreferenceNote
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.services.exceptions import NotFoundError


class PreferenceService:
    def __init__(self, repository: PreferenceNoteRepository) -> None:
        self._repository = repository

    def list_preferences(self) -> list[PreferenceNote]:
        return self._repository.list_all()

    def add_preference(self, note: PreferenceNote) -> PreferenceNote:
        return self._repository.add(note)

    def remove_preference(self, note_id: int) -> None:
        if not self._repository.delete(note_id):
            raise NotFoundError(f"Preference note {note_id} does not exist.")
