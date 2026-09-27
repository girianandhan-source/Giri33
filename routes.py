import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.ai.nutrition import (
	NutritionTipConfigurationError,
	generate_nutrition_tip_with_flash,
)
from app.ai.workout import (
	WorkoutPlanConfigurationError,
	generate_workout_plan,
	update_workout_plan as revise_workout_plan,
)
from app.config import ADMIN_TOKEN, BASE_DIR
from app.database import (
	get_all_users_with_plans,
	get_original_plan,
	save_plan,
	save_user,
	save_user_with_plan,
	update_plan,
)


router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "templates")
admin_security = HTTPBasic()
logger = logging.getLogger(__name__)


class UserSaveRequest(BaseModel):
	user_id: int = Field(gt=0)
	name: str = Field(min_length=1, max_length=120)
	age: int = Field(ge=1, le=120)
	weight: float = Field(gt=0, le=700)
	goal: str = Field(min_length=1, max_length=500)
	intensity: str = Field(min_length=1, max_length=40)


class WorkoutPlanGenerateRequest(BaseModel):
	user_id: int = Field(gt=0)
	name: str = Field(min_length=1, max_length=120)
	age: int = Field(ge=18, le=100)
	weight: float = Field(gt=0, le=700)
	goal: str = Field(min_length=3, max_length=500)
	intensity: str = Field(pattern="^(beginner|moderate|advanced)$")
	schedule: int = Field(ge=2, le=6)
	equipment: str = Field(default="", max_length=300)
	limitations: str = Field(default="", max_length=500)


class WorkoutPlanSaveRequest(BaseModel):
	user_id: int = Field(gt=0)
	plan: str = Field(min_length=1)


class WorkoutPlanUpdateRequest(BaseModel):
	updated_text: str = Field(min_length=1)


class FeedbackRequest(BaseModel):
	feedback: str = Field(min_length=3, max_length=1000)


def verify_admin(credentials: HTTPBasicCredentials = Depends(admin_security)) -> None:
	if not ADMIN_TOKEN:
		raise HTTPException(status_code=503, detail="Admin access is not configured")

	valid_username = secrets.compare_digest(credentials.username, "admin")
	valid_token = secrets.compare_digest(credentials.password, ADMIN_TOKEN)
	if not valid_username or not valid_token:
		raise HTTPException(
			status_code=401,
			detail="Invalid admin credentials",
			headers={"WWW-Authenticate": "Basic"},
		)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
	return templates.TemplateResponse(request, "index.html", {})


@router.post("/api/plans/generate")
def generate_and_save_plan(request: WorkoutPlanGenerateRequest):
	try:
		plan = generate_workout_plan(
			goal=request.goal,
			age=request.age,
			weight=request.weight,
			intensity=request.intensity,
			schedule=request.schedule,
			equipment=request.equipment,
			limitations=request.limitations,
		)
	except WorkoutPlanConfigurationError as error:
		raise HTTPException(status_code=503, detail=str(error)) from error
	except Exception as error:
		logger.exception("Gemini workout-plan generation failed")
		raise HTTPException(
			status_code=502,
			detail="The workout plan service is temporarily unavailable",
		) from error

	save_user_with_plan(
		user_id=request.user_id,
		name=request.name,
		age=request.age,
		weight=request.weight,
		goal=request.goal,
		intensity=request.intensity,
		schedule=request.schedule,
		plan=plan,
	)
	return {"user_id": request.user_id, "plan": plan}


@router.post("/api/users")
def save_user_profile(user: UserSaveRequest):
	save_user(
		user.user_id,
		user.name,
		user.age,
		user.weight,
		user.goal,
		user.intensity,
	)
	return {"status": "saved", "user_id": user.user_id}


@router.post("/api/plans")
def save_workout_plan(request: WorkoutPlanSaveRequest):
	try:
		save_plan(request.user_id, request.plan)
	except ValueError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error
	return {"status": "saved", "user_id": request.user_id}


@router.post("/update-plan/{user_id}", response_model=dict)
def update_user_plan(user_id: int, data: FeedbackRequest):
	original = get_original_plan(user_id)
	if not original:
		raise HTTPException(status_code=404, detail="Original plan not found for this user")

	try:
		updated = revise_workout_plan(original, data.feedback)
	except WorkoutPlanConfigurationError as error:
		raise HTTPException(status_code=503, detail=str(error)) from error
	except Exception as error:
		raise HTTPException(
			status_code=502,
			detail="The workout plan service is temporarily unavailable",
		) from error

	if not update_plan(user_id, updated):
		raise HTTPException(status_code=404, detail="Workout plan no longer exists")

	return {"updated_plan": updated}


@router.put("/api/plans/{user_id}", dependencies=[Depends(verify_admin)])
def update_workout_plan(user_id: int, request: WorkoutPlanUpdateRequest):
	if not update_plan(user_id, request.updated_text):
		raise HTTPException(status_code=404, detail="No workout plan found for this user")
	return {"status": "updated", "user_id": user_id}


@router.get(
	"/view-all-users",
	response_class=HTMLResponse,
	dependencies=[Depends(verify_admin)],
)
def view_all_users(request: Request):
	return templates.TemplateResponse(
		request,
		"all_users.html",
		{"users": get_all_users_with_plans()},
	)


@router.get("/nutrition-tip")
def get_flash_tip(goal: str = Query(min_length=2, max_length=200)):
	try:
		tip = generate_nutrition_tip_with_flash(goal)
	except NutritionTipConfigurationError as error:
		raise HTTPException(status_code=503, detail=str(error)) from error
	except Exception as error:
		raise HTTPException(
			status_code=502,
			detail="The nutrition tip service is temporarily unavailable",
		) from error

	return {"goal": goal, "nutrition_tip": tip}
