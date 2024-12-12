import os
import random
from pymongo import MongoClient
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

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


def add_user(user_id, username):
    """Add a new user to the database."""
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "username": username, "gems": 50, "characters": [], "admin": False})


def is_sudo(user_id):
    """Check if a user has sudo privileges."""
    user = users_collection.find_one({"user_id": user_id})
    return user.get("admin", False) if user else False


def add_sudo(update: Update, context: CallbackContext):
    """Allow the owner to grant sudo privileges to a user."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 1:
        update.message.reply_text("❓ Usage: `/addsudo <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        user_id = int(context.args[0])
        user = users_collection.find_one({"user_id": user_id})

        if not user:
            update.message.reply_text(f"⚠️ User with ID `{user_id}` does not exist.", parse_mode=ParseMode.MARKDOWN)
            return

        users_collection.update_one({"user_id": user_id}, {"$set": {"admin": True}})
        update.message.reply_text(f"✅ User with ID `{user_id}` is now a sudo user.", parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")


def upload_character(update: Update, context: CallbackContext):
    """Allow sudo users or the owner to upload a new character."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID and not is_sudo(user_id):
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 3:
        update.message.reply_text("❓ Usage: `/upload <image_url> <character_name> <rarity>`", parse_mode=ParseMode.MARKDOWN)
        return

    image_url = context.args[0]
    name = context.args[1]
    rarity = context.args[2].capitalize()

    if rarity not in ["Common", "Rare", "Epic", "Legendary", "Mythical"]:
        update.message.reply_text("⚠️ Invalid rarity. Choose from: Common, Rare, Epic, Legendary, Mythical.")
        return

    # Add the character to the database
    character = {"name": name, "rarity": rarity, "image_url": image_url}
    characters_collection.insert_one(character)

    update.message.reply_photo(
        photo=image_url,
        caption=(
            f"✅ **Character Uploaded!**\n\n"
            f"🧩 **Name:** {name}\n"
            f"🏅 **Rarity:** {rarity_with_emoji(rarity)}\n"
            f"🌐 **Image URL:** {image_url}"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


def stats(update: Update, context: CallbackContext):
    """Display bot statistics."""
    total_users = users_collection.count_documents({})
    total_characters = characters_collection.count_documents({})

    update.message.reply_text(
        f"📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"🧩 **Total Characters:** {total_characters}\n",
        parse_mode=ParseMode.MARKDOWN,
    )


def inventory(update: Update, context: CallbackContext):
    """Show the user's inventory."""
    user_id = update.effective_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        update.message.reply_text("🚫 You don't have a profile yet.")
        return

    characters = user_data.get("characters", [])
    inventory_text = "🎒 **Your Inventory:**\n\n"

    if characters:
        for char in characters:
            inventory_text += f"🌟 **{char['name']}** ({rarity_with_emoji(char['rarity'])})\n"
    else:
        inventory_text += "📭 No characters yet. Start grabbing waifus!"

    update.message.reply_text(inventory_text, parse_mode=ParseMode.MARKDOWN)


def profile(update: Update, context: CallbackContext):
    """Show the user's profile."""
    user_id = update.effective_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        update.message.reply_text("🚫 You don't have a profile yet.")
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

    update.message.reply_text(profile_text, parse_mode=ParseMode.MARKDOWN)


def start(update: Update, context: CallbackContext):
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
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def main():
    """Main function to run the bot."""
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Handlers
    dispatcher.add_handler(CommandHandler("addsudo", add_sudo))
    dispatcher.add_handler(CommandHandler("upload", upload_character))
    dispatcher.add_handler(CommandHandler("stats", stats))
    dispatcher.add_handler(CommandHandler("inventory", inventory))
    dispatcher.add_handler(CommandHandler("profile", profile))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
      
