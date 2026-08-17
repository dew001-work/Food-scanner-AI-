import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥫 Welcome to Food Scanner AI!\n\n"
        "Send me a photo of a packaged food product "
        "and I'll help you understand its ingredients "
        "and nutrition information.\n\n"
        "🚀 Food analysis is coming next!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Food Scanner AI Help\n\n"
        "Use /start to start the bot.\n"
        "Send a packaged-food photo for analysis."
    )


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("Food Scanner AI is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
