import os
import random
from pymongo import MongoClient
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHARACTER_CHANNEL_ID = int(os.getenv("CHARACTER_CHANNEL_ID"))

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["waifu_bot"]
users_collection = db["users"]
characters_collection = db["characters"]

# Global active character
current_character = None


def rarity_with_emoji(rarity):
    """Add a single emoji to rarity levels."""
    emojis = {
        "Common": "⚪ Common",
        "Rare": "🔵 Rare",
        "Epic": "🟣 Epic",
        "Legendary": "🟡 Legendary",
        "Mythical": "🔴 Mythical",
    }
    return emojis.get(rarity, rarity)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message and list commands."""
    text = (
        "👋 Welcome to **Waifu Bot**! 🎉\n\n"
        "Here's what you can do:\n\n"
        "🌟 **Commands:**\n"
        "  - `/start` or `/help` - Show this help message\n"
        "  - `/grab <character_name>` - Guess and grab the active waifu 💖\n"
        "  - `/inventory` - Show your collected waifus 🎒\n"
        "  - `/profile` - View your profile and gems 💎\n"
        "  - `/upload <image_url> <character_name> <rarity>` - Upload a waifu (sudo only) 🛠️\n"
        "  - `/addsudo <user_id>` - Grant sudo privileges (owner only) 🔑\n"
        "  - `/stats` - View bot statistics 📊\n\n"
        "✨ New waifus will appear in the channel! Use `/grab` to collect them!"
    )
    await update.message.reply_text(text)


async def add_user(user_id, username):
    """Add a new user to the database."""
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "username": username, "gems": 50, "characters": [], "admin": False})


def is_sudo(user_id):
    """Check if a user has sudo privileges."""
    user = users_collection.find_one({"user_id": user_id})
    return user.get("admin", False) if user else False


async def add_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow the owner to grant sudo privileges to a user."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❓ Usage: `/addsudo <user_id>`")
        return

    try:
        user_id = int(context.args[0])
        user = users_collection.find_one({"user_id": user_id})

        if not user:
            await update.message.reply_text(f"⚠️ User with ID `{user_id}` does not exist.")
            return

        users_collection.update_one({"user_id": user_id}, {"$set": {"admin": True}})
        await update.message.reply_text(f"✅ User with ID `{user_id}` is now a sudo user.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")


async def upload_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow sudo users or the owner to upload a new character."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID and not is_sudo(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 3:
        await update.message.reply_text("❓ Usage: `/upload <image_url> <character_name> <rarity>`")
        return

    image_url = context.args[0]
    name = context.args[1]
    rarity = context.args[2].capitalize()

    if rarity not in ["Common", "Rare", "Epic", "Legendary", "Mythical"]:
        await update.message.reply_text("⚠️ Invalid rarity. Choose from: Common, Rare, Epic, Legendary, Mythical.")
        return

    # Add the character to the database
    character = {"name": name, "rarity": rarity, "image_url": image_url}
    characters_collection.insert_one(character)

    await update.message.reply_photo(
        photo=image_url,
        caption=(
            f"✅ **Character Uploaded!**\n\n"
            f"🧩 **Name:** {name}\n"
            f"🏅 **Rarity:** {rarity_with_emoji(rarity)}\n"
            f"🌐 **Image URL:** {image_url}"
        ),
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display bot statistics."""
    total_users = users_collection.count_documents({})
    total_characters = characters_collection.count_documents({})

    await update.message.reply_text(
        f"📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"🧩 **Total Characters:** {total_characters}\n"
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's profile."""
    user_id = update.effective_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        await update.message.reply_text("🚫 You don't have a profile yet.")
        return

    gems = user_data["gems"]
    characters = user_data.get("characters", [])
    profile_text = f"👤 **Profile: {user_data['username']}**\n\n" \
                   f"💎 **Gems:** {gems}\n" \
                   f"🎒 **Characters:**\n"

    if characters:
        for char in characters:
            profile_text += f"🌟 **{char['name']}** ({rarity_with_emoji(char['rarity'])})\n"
    else:
        profile_text += "📭 No characters yet. Start grabbing waifus!"

    await update.message.reply_text(profile_text)


def main():
    """Main function to run the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("addsudo", add_sudo))
    app.add_handler(CommandHandler("upload", upload_character))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("profile", profile))

    # Run the bot
    app.run_polling()


if __name__ == "__main__":
    main()
    
