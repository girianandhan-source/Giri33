from google import genai

from ..config import GEMINI_API_KEY, GEMINI_TIP_MODEL


class NutritionTipConfigurationError(Exception):
    pass


def generate_nutrition_tip_with_flash(goal: str) -> str:
    if not GEMINI_API_KEY:
        raise NutritionTipConfigurationError("Gemini API key is not configured")

    prompt = (
        "Give one practical, general nutrition tip for someone with this fitness goal: "
        f"{goal}\n"
        "Keep it concise and safe. Do not diagnose or prescribe treatment; "
        "mention professional advice for medical dietary needs."
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_TIP_MODEL,
        contents=prompt,
    )
    tip = (response.text or "").strip()
    if not tip:
        raise RuntimeError("Gemini returned an empty nutrition tip")

    return tip