import os
import time
import logging
import feedparser
import requests
from telegram import Bot

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RSS_FEED_URL = os.getenv("RSS_FEED_URL")

# Telegraph API
TELEGRAPH_API_URL = "https://api.telegra.ph/createPage"
TELEGRAPH_AUTHOR_NAME = os.getenv("TELEGRAPH_AUTHOR_NAME")
TELEGRAPH_AUTHOR_URL = os.getenv("TELEGRAPH_AUTHOR_URL")

# Store posted articles {link: message_id}
posted_articles = {}

def fetch_rss():
    """Fetches and parses the RSS feed."""
    feed = feedparser.parse(RSS_FEED_URL)
    return feed.entries

def clean_content(summary):
    """Removes unwanted text from the summary."""
    unwanted_text = "Sign up for YYZ Deals Alerts"
    if unwanted_text in summary:
        summary = summary.split(unwanted_text)[0].strip()
    return summary

def create_telegraph_post(title, content):
    """Creates a Telegraph post and returns the post URL."""
    response = requests.post(TELEGRAPH_API_URL, json={
        "access_token": "YOUR_TELEGRAPH_ACCESS_TOKEN",
        "title": title,
        "author_name": TELEGRAPH_AUTHOR_NAME,
        "author_url": TELEGRAPH_AUTHOR_URL,
        "content": [{"tag": "p", "children": [content]}],
    })
    
    if response.status_code == 200:
        return response.json().get("result", {}).get("url")
    else:
        logging.error(f"Telegraph Error: {response.text}")
        return None

def post_to_telegram(bot, entry):
    """Sends a new RSS entry to Telegram."""
    title = entry.title
    link = entry.link
    summary = clean_content(entry.summary if hasattr(entry, "summary") else "No description available.")
    
    telegraph_url = create_telegraph_post(title, summary)
    if not telegraph_url:
        return
    
    message = f"**{title}**\n[Read more]({telegraph_url})"
    sent_message = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
    
    # Store the message ID to track updates
    posted_articles[link] = sent_message.message_id

def update_telegram_post(bot, entry):
    """Updates an already posted message if content changes."""
    title = entry.title
    link = entry.link
    summary = clean_content(entry.summary if hasattr(entry, "summary") else "No description available.")
    
    telegraph_url = create_telegraph_post(title, summary)
    if not telegraph_url:
        return
    
    message = f"**{title}**\n[Read more]({telegraph_url})"
    
    if link in posted_articles:
        bot.edit_message_text(chat_id=TELEGRAM_CHAT_ID, message_id=posted_articles[link], text=message, parse_mode="Markdown")

def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    while True:
        try:
            entries = fetch_rss()
            for entry in entries:
                if entry.link not in posted_articles:
                    post_to_telegram(bot, entry)
                else:
                    update_telegram_post(bot, entry)

            # Sleep for 10 minutes before checking again
            time.sleep(600)
        
        except Exception as e:
            logging.error(f"Error fetching or sending RSS updates: {e}")
            time.sleep(60)  # Retry after 1 minute

if __name__ == "__main__":
    main()
