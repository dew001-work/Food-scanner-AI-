import os

from google import genai
from google.genai import types

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# --------------------------------------------------
# START COMMAND
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥫 Welcome to Food Scanner AI!\n\n"
        "Send me a clear photo of a packaged food product "
        "and I'll analyze its ingredients and nutrition.\n\n"
        "📸 For best results, photograph the ingredients "
        "and nutrition label clearly."
    )


# --------------------------------------------------
# HELP COMMAND
# --------------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Food Scanner AI\n\n"
        "📸 Send a packaged-food photo to analyze it.\n\n"
        "For best results:\n"
        "• Keep the label clearly visible\n"
        "• Avoid blurry photos\n"
        "• Include the ingredients and nutrition panel"
    )


# --------------------------------------------------
# PHOTO ANALYSIS
# --------------------------------------------------

async def analyze_food_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:
        await update.message.reply_text(
            "🔍 Analyzing your food label...\n\n"
            "Please wait a moment."
        )

        # Get the highest-resolution Telegram photo
        photo = update.message.photo[-1]

        # Get Telegram file
        telegram_file = await photo.get_file()

        # Download image into memory
        image_bytes = await telegram_file.download_as_bytearray()

        # Prompt for Gemini
        prompt = """
You are Food Scanner AI, an assistant that analyzes packaged food
products.

Analyze the provided product image.

Your PRIMARY goal is to accurately read information that is visible
on the package, especially:

1. Product name
2. Ingredients list
3. Nutrition facts
4. Serving size
5. Calories
6. Protein
7. Carbohydrates
8. Total fat
9. Saturated fat
10. Trans fat, if listed
11. Fiber
12. Total sugar / added sugar, if listed
13. Sodium
14. Allergens, if clearly stated

IMPORTANT ACCURACY RULES:

- Do NOT invent nutrition values.
- Do NOT guess numbers that cannot be read.
- If a value cannot be read, say "Not clearly visible".
- Distinguish between values stated on the package and your
  interpretation.
- Do not call a food simply "healthy" or "unhealthy".
- Explain ingredients in simple language.
- Mention notable ingredients or nutritional characteristics.
- If the image is unclear, tell the user what photo they should
  send instead.

Return the answer in a clear Telegram-friendly format.

Use this structure:

🥫 PRODUCT
Product name:

🧾 INGREDIENTS
List the ingredients you can clearly read.

🔬 INGREDIENT EXPLANATION
Explain the important/unfamiliar ingredients simply.

📊 NUTRITION
Serving size:
Calories:
Protein:
Carbohydrates:
Total fat:
Saturated fat:
Trans fat:
Fiber:
Sugar:
Added sugar:
Sodium:

⚠️ WHAT STANDS OUT
Mention notable nutritional or ingredient characteristics.

🚨 ALLERGENS
Only mention allergens that are clearly stated or reliably
identified from the label.

💡 SIMPLE SUMMARY
Give a short, neutral explanation of what the label tells us.

At the end add:

"⚠️ This analysis is based on the information visible in the
image. Always check the original packaging for the official
nutrition and ingredient information."
"""

        # Send image + prompt to Gemini
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(
                    data=bytes(image_bytes),
                    mime_type="image/jpeg",
                ),
                prompt,
            ],
        )

        result = response.text

        if not result:
            result = (
                "⚠️ I couldn't extract readable information "
                "from this image.\n\n"
                "Please send a clearer photo of the ingredients "
                "and nutrition label."
            )

        # Telegram message limit protection
        if len(result) > 4000:
            result = result[:3950] + "\n\n[Response shortened]"

        await update.message.reply_text(result)

    except Exception as error:

        print(f"Food analysis error: {error}")

        await update.message.reply_text(
            "⚠️ Sorry, I couldn't analyze that image.\n\n"
            "Please try again with a clear photo showing the "
            "ingredients and nutrition label."
        )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    app = Application.builder().token(
        TELEGRAM_BOT_TOKEN
    ).build()

    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    # Photos
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
