import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import openai
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

# Initialize Firebase using the credentials file
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# /start command: Welcome message
def start(update, context):
    update.message.reply_text("Hello! I am ChatGPT Bot. How can I assist you today?")

# /setinterest command: Store user's interest in Firebase
def set_interest(update, context):
    if not context.args:
        update.message.reply_text("Usage: /setinterest <your_interest>")
        return
    interest = " ".join(context.args)
    user_id = update.message.from_user.id
    db.collection("users").document(str(user_id)).set({"interest": interest}, merge=True)
    update.message.reply_text(f"Your interest '{interest}' has been recorded.")

# /match command: Find another user with a matching interest
def match_user(update, context):
    user_id = update.message.from_user.id
    user_doc = db.collection("users").document(str(user_id)).get()
    if not user_doc.exists or "interest" not in user_doc.to_dict():
        update.message.reply_text("Please set your interest first using the /setinterest command.")
        return
    interest = user_doc.to_dict()["interest"]
    # Query for users with the same interest (excluding the current user)
    users = db.collection("users").where("interest", "==", interest).stream()
    matches = [u.to_dict() for u in users if u.id != str(user_id)]
    if matches:
        # For demonstration, we return a generic match message
        update.message.reply_text(f"Found a match with similar interest: {interest}.")
    else:
        update.message.reply_text("No matching users found at the moment. Please try again later.")

# /events command: Recommend online events based on user interest
def events(update, context):
    user_id = update.message.from_user.id
    user_doc = db.collection("users").document(str(user_id)).get()
    if not user_doc.exists or "interest" not in user_doc.to_dict():
        update.message.reply_text("Please set your interest first using the /setinterest command.")
        return
    interest = user_doc.to_dict()["interest"].lower()
    # Hardcoded sample events for demonstration purposes
    events_data = {
        "online gaming": [
            "Gaming Tournament on 2025-04-15",
            "Virtual LAN Party on 2025-04-20"
        ],
        "virtual reality": [
            "VR Meetup on 2025-04-18",
            "VR Experience Expo on 2025-04-22"
        ],
        "social media": [
            "Social Media Marketing Webinar on 2025-04-16",
            "Influencer Networking Event on 2025-04-21"
        ]
    }
    recommended = events_data.get(interest, ["General online event on 2025-04-19"])
    reply_text = "Recommended events:\n" + "\n".join(recommended)
    update.message.reply_text(reply_text)

# Handler for non-command messages: Forward the text to ChatGPT API and return the answer
import requests

def chat_handler(update, context):
    user_message = update.message.text
    try:
        response = requests.post(
            url="https://genai.hkbu.edu.hk/general/rest",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-o",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_message}
                ]
            }
        )

        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content'].strip()
            update.message.reply_text(reply)
        else:
            logger.error("GenAI API error: %s", response.text)
            update.message.reply_text("Sorry, I couldn't get a valid response from the GPT API.")
    except Exception as e:
        logger.error(" HKBU GPT API error: %s", e)
        update.message.reply_text("Sorry, I encountered an error processing your message.")

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("setinterest", set_interest))
    dispatcher.add_handler(CommandHandler("match", match_user))
    dispatcher.add_handler(CommandHandler("events", events))

    # Add handler for regular messages (non-commands)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, chat_handler))

    # Start the bot using polling
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
