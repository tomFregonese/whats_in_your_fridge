from app.domain.allergy import Allergy
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.services.exceptions import NotFoundError


class AllergyService:
    def __init__(self, repository: AllergyRepository) -> None:
        self._repository = repository

    def list_allergies(self) -> list[Allergy]:
        return self._repository.list_all()

    def add_allergy(self, allergy: Allergy) -> Allergy:
        return self._repository.add(allergy)

    def remove_allergy(self, allergy_id: int) -> None:
        if not self._repository.delete(allergy_id):
            raise NotFoundError(f"Allergy {allergy_id} does not exist.")
