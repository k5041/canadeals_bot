import requests
import os

TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Step 1: Create a Telegra.ph post
telegraph_url = "https://api.telegra.ph/createPage"
telegraph_data = {
    "access_token": TELEGRAPH_ACCESS_TOKEN,
    "title": "Test Post",
    "author_name": "TestBot",
    "content": '[{"tag":"p","children":["Test"]}]'
}
response = requests.post(telegraph_url, json=telegraph_data)
post_url = response.json().get("result", {}).get("url", "Failed to create post")

# Step 2: Send message to Telegram Channel
telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
message_data = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": f"Check out this Telegra.ph post: {post_url}"
}
requests.post(telegram_url, data=message_data)

print(f"Post URL: {post_url}")
