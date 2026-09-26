from google import genai

from ..config import GEMINI_API_KEY, GEMINI_WORKOUT_MODEL


class WorkoutPlanConfigurationError(Exception):
    pass


def generate_workout_plan(
    goal: str,
    age: int,
    weight: float,
    intensity: str,
    schedule: int,
    equipment: str,
    limitations: str,
) -> str:
    if not GEMINI_API_KEY:
        raise WorkoutPlanConfigurationError("Gemini API key is not configured")

    prompt = (
        "Create a safe, practical seven-day workout plan based on this profile. "
        "Format it clearly by day, including exercises, sets/reps or duration, and rest days. "
        "Account for experience implied by the requested intensity, provide warm-up/cool-down, "
        "and avoid medical claims. If limitations are supplied, adapt or avoid those movements. "
        "Include a brief note to stop if pain occurs and seek a qualified professional for medical concerns.\n\n"
        f"Goal: {goal}\nAge: {age}\nWeight: {weight} kg\n"
        f"Intensity: {intensity}\nTraining days per week: {schedule}\n"
        f"Available equipment: {equipment or 'No equipment'}\n"
        f"Limitations or movements to avoid: {limitations or 'None provided'}"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_WORKOUT_MODEL,
        contents=prompt,
    )
    plan = (response.text or "").strip()
    if not plan:
        raise RuntimeError("Gemini returned an empty workout plan")

    return plan


def update_workout_plan(original: str, feedback: str) -> str:
    if not GEMINI_API_KEY:
        raise WorkoutPlanConfigurationError("Gemini API key is not configured")

    prompt = (
        "Revise the following workout plan using the user's feedback where safe. "
        "Keep it practical, include appropriate recovery, and do not provide medical advice. "
        "Return only the revised plan.\n\n"
        f"Current plan:\n{original}\n\n"
        f"User feedback:\n{feedback}"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_WORKOUT_MODEL,
        contents=prompt,
    )
    updated_plan = (response.text or "").strip()
    if not updated_plan:
        raise RuntimeError("Gemini returned an empty workout plan")

    return updated_plan