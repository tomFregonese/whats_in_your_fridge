"""Business object layer (BO).

Plain classes representing business concepts (``Settings``, ``Allergy``,
``Suggestion``, ``MealPlan``, ...), independent of how they are stored
(``persistence/``) or exposed over HTTP (``dto/``). This is the only layer
``services/`` is allowed to see — never an Entity, never a Dto.
"""
