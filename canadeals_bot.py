import requests
import feedparser
import os

# Constants
RSS_FEED_URL = "https://www.yyzdeals.com/atom/1"
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# API URLs
TELEGRAPH_CREATE_URL = "https://api.telegra.ph/createPage"
TELEGRAPH_EDIT_URL = "https://api.telegra.ph/editPage"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def clean_content(html_content):
    """ Remove unwanted text from the content. """
    unwanted_text = "<h2>Sign up for YYZ Deals Alerts</h2>"
    if unwanted_text in html_content:
        html_content = html_content.split(unwanted_text)[0]
    return html_content


def create_telegraph_post(title, content):
    """ Create a new Telegra.ph post. """
    response = requests.post(TELEGRAPH_CREATE_URL, json={
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "title": title,
        "author_name": "YYZ Deals Bot",
        "content": [{"tag": "p", "children": [content]}],
    })
    if response.status_code == 200 and "result" in response.json():
        return response.json()["result"]["url"]
    return None


def edit_telegraph_post(path, title, content):
    """ Edit an existing Telegra.ph post. """
    response = requests.post(TELEGRAPH_EDIT_URL, json={
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "path": path,
        "title": title,
        "author_name": "YYZ Deals Bot",
        "content": [{"tag": "p", "children": [content]}],
    })
    if response.status_code == 200 and "result" in response.json():
        return response.json()["result"]["url"]
    return None


def get_last_10_messages():
    """ Fetch the last 10 messages from the Telegram channel. """
    response = requests.get(f"{TELEGRAM_API_URL}/getUpdates")
    if response.status_code == 200:
        updates = response.json().get("result", [])
        messages = {}
        for update in updates:
            if "message" in update and "text" in update["message"]:
                title = update["message"]["text"].split("\n")[0].replace("📢 *", "").replace("*", "")
                link = update["message"]["text"].split("[")[1].split("]")[0] if "[" in update["message"]["text"] else None
                messages[title] = {"message_id": update["message"]["message_id"], "telegraph_url": link}
        return messages
    return {}


def check_feed():
    """ Process RSS feed and post updates to Telegram. """
    posted_messages = get_last_10_messages()
    feed = feedparser.parse(RSS_FEED_URL)
    
    # Reverse the feed entries so they are processed in the correct order
    for entry in reversed(feed.entries):
        title = entry.title
        content_html = clean_content(entry.content[0].value)

        # If the post hasn't been posted yet
        if title not in posted_messages:
            # Create new Telegraph post
            telegraph_url = create_telegraph_post(title, content_html)

            if telegraph_url:
                message_text = f"📢 *{title}*\n[Read More]({telegraph_url})"
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message_text,
                    "parse_mode": "Markdown"
                })

        else:
            # Check if content has changed
            old_telegraph_url = posted_messages[title]["telegraph_url"]
            telegraph_path = old_telegraph_url.split("/")[-1]

            updated_telegraph_url = edit_telegraph_post(telegraph_path, title, content_html)

            if updated_telegraph_url and updated_telegraph_url != old_telegraph_url:
                new_message_text = f"📢 *{title}*\n[Updated Post]({updated_telegraph_url})"
                requests.post(f"{TELEGRAM_API_URL}/editMessageText", data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "message_id": posted_messages[title]["message_id"],
                    "text": new_message_text,
                    "parse_mode": "Markdown"
                })



if __name__ == "__main__":
    check_feed()
