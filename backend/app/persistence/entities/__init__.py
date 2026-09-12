"""Persistence entities (Entity).

SQLModel ``table=True`` classes — the ONLY place the ORM is used. Used
exclusively from ``persistence/repositories/``, never imported outside this
layer. Each ``XxxEntity`` carries ``to_domain()`` / ``from_domain()`` to
convert to/from its ``domain/`` BO counterpart (``VaultEntity`` is the one
deliberate exception — see its own docstring).

Every entity is imported here so that a single `import
app.persistence.entities` registers the full schema on `SQLModel.metadata`
— this is what Alembic's `env.py` relies on for autogenerate.
"""

from app.persistence.entities.agent_run_entity import AgentRunEntity
from app.persistence.entities.allergy_entity import AllergyEntity
from app.persistence.entities.equipment_entity import EquipmentEntity
from app.persistence.entities.feedback_entity import FeedbackEntity
from app.persistence.entities.fridge_input_entity import (
    FridgeInputEntity,
    FridgeInputItemEntity,
)
from app.persistence.entities.fridge_stock_item_entity import FridgeStockItemEntity
from app.persistence.entities.merge_dismissal_entity import MergeDismissalEntity
from app.persistence.entities.preference_note_entity import PreferenceNoteEntity
from app.persistence.entities.settings_entity import SettingsEntity
from app.persistence.entities.suggestion_entity import (
    AgendaEntryEntity,
    MealPlanEntity,
    SuggestionEntity,
)
from app.persistence.entities.vault_entity import VaultEntity

__all__ = [
    "AgendaEntryEntity",
    "AgentRunEntity",
    "AllergyEntity",
    "EquipmentEntity",
    "FeedbackEntity",
    "FridgeInputEntity",
    "FridgeInputItemEntity",
    "FridgeStockItemEntity",
    "MealPlanEntity",
    "MergeDismissalEntity",
    "PreferenceNoteEntity",
    "SettingsEntity",
    "SuggestionEntity",
    "VaultEntity",
]
