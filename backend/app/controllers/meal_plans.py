from fastapi import APIRouter, Depends

from app.dependencies import get_meal_plan_service
from app.dto.suggestion_dto import MealPlanDtoOut
from app.services.meal_plan_service import MealPlanService

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


@router.get("")
def list_meal_plans(
    service: MealPlanService = Depends(get_meal_plan_service),
) -> list[MealPlanDtoOut]:
    return [MealPlanDtoOut.from_domain(meal_plan) for meal_plan in service.list_all()]


@router.get("/{meal_plan_id}")
def get_meal_plan(
    meal_plan_id: int,
    service: MealPlanService = Depends(get_meal_plan_service),
) -> MealPlanDtoOut:
    return MealPlanDtoOut.from_domain(service.get(meal_plan_id))
