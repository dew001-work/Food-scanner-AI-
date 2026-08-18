import os
import json
from typing import Optional, List

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
# STRUCTURED FOOD DATA
# ============================================================

class Nutrition(BaseModel):
    serving_size: Optional[str] = Field(
        default=None,
        description="Serving size exactly as written on the package."
    )

    calories_kcal: Optional[float] = Field(
        default=None,
        description="Calories as visibly stated on the package."
    )

    protein_g: Optional[float] = Field(
        default=None,
        description="Protein in grams as visibly stated."
    )

    carbohydrates_g: Optional[float] = Field(
        default=None,
        description="Carbohydrates in grams as visibly stated."
    )

    total_fat_g: Optional[float] = Field(
        default=None,
        description="Total fat in grams as visibly stated."
    )

    saturated_fat_g: Optional[float] = Field(
        default=None,
        description="Saturated fat in grams as visibly stated."
    )

    trans_fat_g: Optional[float] = Field(
        default=None,
        description="Trans fat in grams as visibly stated."
    )

    fiber_g: Optional[float] = Field(
        default=None,
        description="Fiber in grams as visibly stated."
    )

    sugar_g: Optional[float] = Field(
        default=None,
        description="Total sugar in grams as visibly stated."
    )

    added_sugar_g: Optional[float] = Field(
        default=None,
        description="Added sugar in grams as visibly stated."
    )

    sodium_mg: Optional[float] = Field(
        default=None,
        description="Sodium in milligrams as visibly stated."
    )


class FoodAnalysis(BaseModel):
    product_name: Optional[str] = Field(
        default=None,
        description="Product name only if clearly readable."
    )

    brand: Optional[str] = Field(
        default=None,
        description="Brand only if clearly readable."
    )

    category: Optional[str] = Field(
        default=None,
        description="General product category if reasonably identifiable."
    )

    ingredients: List[str] = Field(
        default_factory=list,
        description="Ingredients clearly readable on the package."
    )

    ingredient_explanations: List[str] = Field(
        default_factory=list,
        description="Simple explanations of notable ingredients actually visible."
    )

    nutrition: Nutrition

    allergens: List[str] = Field(
        default_factory=list,
        description="Allergens clearly stated or clearly identifiable from the label."
    )

    notable_points: List[str] = Field(
        default_factory=list,
        description="Important observations based only on visible information."
    )

    image_quality: str = Field(
        description="Image quality: clear, partly_clear, or unclear."
    )

    confidence: str = Field(
        description="Overall extraction confidence: high, medium, or low."
    )

    needs_better_photo: bool = Field(
        description="True if important information cannot be reliably read."
    )


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
        "and I'll analyze the ingredients and nutrition.\n\n"
        "💡 For the best result, photograph the back of the "
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
# FORMAT FOOD ANALYSIS
# ============================================================

def format_analysis(data: FoodAnalysis) -> str:

    nutrition = data.nutrition

    product_name = (
        data.product_name
        if data.product_name
        else "Not clearly visible"
    )

    brand = (
        data.brand
        if data.brand
        else "Not clearly visible"
    )

    category = (
        data.category
        if data.category
        else "Not clearly identified"
    )

    ingredients_text = (
        "\n".join(f"• {item}" for item in data.ingredients)
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

    serving = (
        nutrition.serving_size
        if nutrition.serving_size
        else "Not clearly visible"
    )

    def value(number, unit=""):
        if number is None:
            return "Not clearly visible"
        return f"{number:g}{unit}"

    quality_icon = {
        "clear": "🟢",
        "partly_clear": "🟡",
        "unclear": "🔴"
    }.get(data.image_quality, "🟡")

    confidence_icon = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🔴"
    }.get(data.confidence, "🟡")

    result = f"""
🥫 PRODUCT

Product: {product_name}
Brand: {brand}
Category: {category}


🧾 INGREDIENTS

{ingredients_text}


🔬 INGREDIENT EXPLANATION

{explanations_text}


📊 NUTRITION

Serving size: {serving}

Calories: {value(nutrition.calories_kcal, " kcal")}
Protein: {value(nutrition.protein_g, " g")}
Carbohydrates: {value(nutrition.carbohydrates_g, " g")}
Total fat: {value(nutrition.total_fat_g, " g")}
Saturated fat: {value(nutrition.saturated_fat_g, " g")}
Trans fat: {value(nutrition.trans_fat_g, " g")}
Fiber: {value(nutrition.fiber_g, " g")}
Sugar: {value(nutrition.sugar_g, " g")}
Added sugar: {value(nutrition.added_sugar_g, " g")}
Sodium: {value(nutrition.sodium_mg, " mg")}


⚠️ WHAT STANDS OUT

{notable_text}


🚨 ALLERGENS

{allergens_text}


📷 SCAN QUALITY

{quality_icon} Image: {data.image_quality}
{confidence_icon} Extraction confidence: {data.confidence}
"""

    if data.needs_better_photo:
        result += """
    
📸 BETTER PHOTO RECOMMENDED

Some important information could not be reliably read.

Please send a clearer photo showing the full ingredients
and nutrition label.
"""

    result += """
    
⚠️ IMPORTANT

This analysis is based only on information visible in the
provided image. It does not replace the official product label
or professional medical/nutrition advice.
"""

    return result.strip()


# ============================================================
# ANALYZE PHOTO
# ============================================================

async def analyze_food_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        await update.message.reply_text(
            "🔍 Reading your food label...\n\n"
            "I'm extracting the information first, "
            "then checking it before showing you the result."
        )

        # ----------------------------------------------------
        # GET TELEGRAM IMAGE
        # ----------------------------------------------------

        photo = update.message.photo[-1]

        telegram_file = await photo.get_file()

        image_bytes = await telegram_file.download_as_bytearray()

        # ----------------------------------------------------
        # GEMINI INSTRUCTIONS
        # ----------------------------------------------------

        prompt = """
You are Food Scanner AI.

Your job is to extract information from a packaged-food
product image.

This is an INFORMATION EXTRACTION task first.
Do not guess.

STRICT RULES:

1. Only report information that is visible or clearly readable.
2. If the product name cannot be read, return null.
3. If the brand cannot be read, return null.
4. If ingredients are not visible, return an empty list.
5. NEVER invent ingredients.
6. NEVER invent nutrition numbers.
7. NEVER estimate a nutrition number from appearance.
8. NEVER invent a serving size.
9. Keep the serving size exactly as printed.
10. Do not convert grams to teaspoons, tablespoons, cups,
    servings, or other units.
11. Do not assume the product type means a particular ingredient.
12. Do not identify a specific oil, grain, sweetener, etc.
    unless the label supports it.
13. Do not treat your general knowledge as something written
    on the package.
14. If a nutrition value is not readable, return null.
15. If an ingredient is only partially readable, do not guess
    the missing text.
16. Allergens should only be reported if clearly stated or
    reliably identifiable from visible ingredients.
17. Do not diagnose medical conditions.
18. Do not claim that a food will cause or prevent a disease.
19. Do not simply label food "healthy" or "unhealthy".
20. notable_points must be based on visible facts.

IMPORTANT:

Separate LABEL FACTS from INTERPRETATION.

For ingredient_explanations:
Explain only notable ingredients that are actually visible.

For notable_points:
Mention useful observations such as:
- high/low amount of a nutrient relative to the declared values
- presence of added sugar if explicitly listed
- presence of trans fat if explicitly listed
- presence of allergens
- fortification
- unusual additives

Do not invent health effects.

IMAGE QUALITY:

"clear" = important information can be read reliably.

"partly_clear" = some important information can be read,
but some information is missing or difficult to read.

"unclear" = the label cannot be reliably analyzed.

CONFIDENCE:

"high" = most important information is clearly readable.

"medium" = useful information is readable but some information
is uncertain or missing.

"low" = important information is difficult to read.

needs_better_photo should be true whenever important information
cannot be reliably extracted.

Return ONLY the structured JSON requested by the schema.
"""


        # ----------------------------------------------------
        # GEMINI STRUCTURED OUTPUT
        # ----------------------------------------------------

        response = gemini_client.models.generate_content(

            model="gemini-3.6-flash",

            contents=[
                types.Part.from_bytes(
                    data=bytes(image_bytes),
                    mime_type="image/jpeg",
                ),
                prompt,
            ],

            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FoodAnalysis,
            ),
        )

        # ----------------------------------------------------
        # PARSE STRUCTURED RESULT
        # ----------------------------------------------------

        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        data = FoodAnalysis.model_validate_json(
            response.text
        )

        # ----------------------------------------------------
        # FORMAT TELEGRAM RESPONSE
        # ----------------------------------------------------

        result = format_analysis(data)

        # Telegram message size protection
        if len(result) > 4000:
            result = result[:3950] + "\n\n[Response shortened]"

        await update.message.reply_text(result)

    except Exception as error:

        print(
            f"Food analysis error: "
            f"{type(error).__name__}: {error}"
        )

        await update.message.reply_text(
            "⚠️ I couldn't reliably analyze this image.\n\n"
            "Please send a clearer photo showing the full "
            "ingredients list and nutrition panel."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    app = Application.builder().token(
        TELEGRAM_BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            analyze_food_photo
        )
    )

    print("Food Scanner AI is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
