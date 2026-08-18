import os
from typing import Optional, List, Dict

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# STRUCTURED NUTRITION DATA
# ============================================================

class NutrientValue(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    basis: Optional[str] = None
    rda_percent: Optional[float] = None


class NutritionData(BaseModel):

    # Energy
    energy: Optional[NutrientValue] = None

    # Main macros
    protein: Optional[NutrientValue] = None
    carbohydrate: Optional[NutrientValue] = None
    total_sugars: Optional[NutrientValue] = None
    added_sugars: Optional[NutrientValue] = None

    # Fat
    total_fat: Optional[NutrientValue] = None
    saturated_fat: Optional[NutrientValue] = None
    trans_fat: Optional[NutrientValue] = None
    monounsaturated_fat: Optional[NutrientValue] = None
    polyunsaturated_fat: Optional[NutrientValue] = None
    omega_3: Optional[NutrientValue] = None
    omega_6: Optional[NutrientValue] = None

    # Other nutrition
    fiber: Optional[NutrientValue] = None
    cholesterol: Optional[NutrientValue] = None
    sodium: Optional[NutrientValue] = None

    # Flexible additional nutrients
    additional_nutrients: Dict[str, NutrientValue] = Field(
        default_factory=dict
    )


class FoodAnalysis(BaseModel):

    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None

    ingredients: List[str] = Field(
        default_factory=list
    )

    ingredient_explanations: List[str] = Field(
        default_factory=list
    )

    allergens: List[str] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # SERVING INFORMATION
    # --------------------------------------------------------

    serving_size_value: Optional[float] = None
    serving_size_unit: Optional[str] = None
    servings_per_container: Optional[float] = None

    # The label basis used by the nutrition table.
    # Examples:
    # "per 100 g"
    # "per 100 ml"
    # "per serving"
    # "per portion"
    nutrition_basis: Optional[str] = None

    nutrition: NutritionData

    notable_points: List[str] = Field(
        default_factory=list
    )

    image_quality: str
    confidence: str
    needs_better_photo: bool


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🥫 Welcome to Food Scanner AI!\n\n"
        "📸 Send me a clear photo of a packaged food label "
        "and I'll analyze its ingredients and nutrition.\n\n"
        "💡 For best results, photograph the back of the "
        "package showing the ingredients and nutrition panel."
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📖 Food Scanner AI\n\n"
        "📸 Send a packaged-food photo to analyze it.\n\n"
        "Best results:\n"
        "• Good lighting\n"
        "• No blur\n"
        "• Entire nutrition table visible\n"
        "• Ingredients list visible\n"
        "• Keep the camera straight"
    )


# ============================================================
# PYTHON CALCULATIONS
# ============================================================

def calculate_per_serving(
    nutrient: Optional[NutrientValue],
    serving_value: Optional[float],
    serving_unit: Optional[str]
) -> Optional[float]:

    if nutrient is None:
        return None

    if nutrient.value is None:
        return None

    if serving_value is None:
        return None

    basis = (nutrient.basis or "").lower()

    # Only calculate automatically when the label basis
    # is clearly per 100 g or per 100 ml.
    if "100 g" in basis and serving_unit:
        if serving_unit.lower() == "g":
            return nutrient.value * serving_value / 100

    if "100 ml" in basis and serving_unit:
        if serving_unit.lower() == "ml":
            return nutrient.value * serving_value / 100

    return None


# ============================================================
# FORMATTING HELPERS
# ============================================================

def format_value(
    nutrient: Optional[NutrientValue]
) -> str:

    if nutrient is None or nutrient.value is None:
        return "Not clearly visible"

    unit = nutrient.unit or ""

    return f"{nutrient.value:g} {unit}".strip()


def format_rda(
    nutrient: Optional[NutrientValue]
) -> str:

    if nutrient is None:
        return ""

    if nutrient.rda_percent is None:
        return ""

    return f" ({nutrient.rda_percent:g}% RDA)"


def calculated_value_text(
    nutrient: Optional[NutrientValue],
    serving_value: Optional[float],
    serving_unit: Optional[str]
) -> str:

    calculated = calculate_per_serving(
        nutrient,
        serving_value,
        serving_unit
    )

    if calculated is None:
        return "Not available"

    unit = nutrient.unit or ""

    return f"{calculated:g} {unit}".strip()


# ============================================================
# FORMAT ANALYSIS
# ============================================================

def format_analysis(
    data: FoodAnalysis
) -> str:

    n = data.nutrition

    product = data.product_name or "Not clearly visible"
    brand = data.brand or "Not clearly visible"
    category = data.category or "Not clearly identified"

    # --------------------------------------------------------
    # INGREDIENTS
    # --------------------------------------------------------

    ingredients_text = (
        "\n".join(
            f"• {item}"
            for item in data.ingredients
        )
        if data.ingredients
        else "Not clearly visible"
    )

    explanations_text = (
        "\n".join(
            f"• {item}"
            for item in data.ingredient_explanations
        )
        if data.ingredient_explanations
        else "No additional ingredient explanation available."
    )

    allergens_text = (
        ", ".join(data.allergens)
        if data.allergens
        else "None clearly identified from the image"
    )

    notable_text = (
        "\n".join(
            f"• {item}"
            for item in data.notable_points
        )
        if data.notable_points
        else "Nothing notable could be reliably determined."
    )

    # --------------------------------------------------------
    # SERVING
    # --------------------------------------------------------

    if (
        data.serving_size_value is not None
        and data.serving_size_unit
    ):
        serving_text = (
            f"{data.serving_size_value:g} "
            f"{data.serving_size_unit}"
        )
    else:
        serving_text = "Not clearly visible"

    servings_text = ""

    if data.servings_per_container is not None:
        servings_text = (
            f"\nServings per container: "
            f"{data.servings_per_container:g}"
        )

    basis = data.nutrition_basis or "Not clearly visible"

    # --------------------------------------------------------
    # NUTRITION TABLE
    # --------------------------------------------------------

    nutrition_text = f"""
📊 NUTRITION

Nutrition basis: {basis}

Serving size: {serving_text}{servings_text}

Per label basis:

Calories: {format_value(n.energy)}
Protein: {format_value(n.protein)}
Carbohydrates: {format_value(n.carbohydrate)}
Total sugars: {format_value(n.total_sugars)}
Added sugars: {format_value(n.added_sugars)}

Total fat: {format_value(n.total_fat)}
Saturated fat: {format_value(n.saturated_fat)}
Trans fat: {format_value(n.trans_fat)}
Monounsaturated fat: {format_value(n.monounsaturated_fat)}
Polyunsaturated fat: {format_value(n.polyunsaturated_fat)}

Omega-3: {format_value(n.omega_3)}
Omega-6: {format_value(n.omega_6)}

Fiber: {format_value(n.fiber)}
Cholesterol: {format_value(n.cholesterol)}
Sodium: {format_value(n.sodium)}
"""

    # --------------------------------------------------------
    # PER-SERVING CALCULATIONS
    # --------------------------------------------------------

    calculated_lines = []

    if data.serving_size_value is not None:

        calculated_lines.append(
            f"Calories: "
            f"{calculated_value_text(n.energy, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Protein: "
            f"{calculated_value_text(n.protein, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Carbohydrates: "
            f"{calculated_value_text(n.carbohydrate, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Total fat: "
            f"{calculated_value_text(n.total_fat, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Saturated fat: "
            f"{calculated_value_text(n.saturated_fat, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Trans fat: "
            f"{calculated_value_text(n.trans_fat, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Total sugars: "
            f"{calculated_value_text(n.total_sugars, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Added sugars: "
            f"{calculated_value_text(n.added_sugars, data.serving_size_value, data.serving_size_unit)}"
        )

        calculated_lines.append(
            f"Sodium: "
            f"{calculated_value_text(n.sodium, data.serving_size_value, data.serving_size_unit)}"
        )

    if calculated_lines:
        nutrition_text += (
            "\n\n"
            "🧮 CALCULATED PER SERVING\n\n"
            + "\n".join(
                calculated_lines
            )
            + "\n\n"
            "ℹ️ Calculated by Food Scanner AI "
            "from the label's declared values."
        )

    # --------------------------------------------------------
    # RDA
    # --------------------------------------------------------

    rda_items = []

    for name, nutrient in [
        ("Calories", n.energy),
        ("Added sugar", n.added_sugars),
        ("Total fat", n.total_fat),
        ("Saturated fat", n.saturated_fat),
        ("Trans fat", n.trans_fat),
        ("Sodium", n.sodium),
    ]:

        rda = format_rda(nutrient)

        if rda:
            rda_items.append(
                f"• {name}{rda}"
            )

    if rda_items:
