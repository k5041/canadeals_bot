import requests
import os
import xml.etree.ElementTree as ET
import bleach
from bs4 import BeautifulSoup

# Constants
RSS_FEED_URL = "https://www.yyzdeals.com/atom/1"
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# API URLs
TELEGRAPH_CREATE_URL = "https://api.telegra.ph/createPage"
TELEGRAPH_EDIT_URL = "https://api.telegra.ph/editPage"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

ALLOWED_TAGS = [
    'a', 'aside', 'b', 'blockquote', 'br', 'code', 'em', 'figcaption',
    'figure', 'h3', 'h4', 'hr', 'i', 'iframe', 'img', 'li', 'ol', 'p',
    'pre', 's', 'strong', 'u', 'ul', 'video'
]

SOURCES = ['href', 'src']

ALLOWED_ATTRIBUTES = {
    'a': SOURCES,
    'iframe': SOURCES,
    'img': SOURCES,
    'video': SOURCES,
}

UNWANTED_TEXT_BLOCK = """Can't find this deal anymore? Prices change as 
deals sell out. The key is to be among the first 
to know when an amazing deal is posted.

Click here for tips on how to never miss a deal 
again."""

posted_articles = {}

def html_to_content(html):
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True, strip_comments=True).strip()
    soup = BeautifulSoup(clean, "html.parser")

    def inner(tag):
        if tag.name is None:
            if not tag.string.strip():
                return None
            return tag.string.strip()

        node = {"tag": tag.name}
        if tag.attrs:
            node["attrs"] = tag.attrs

        children = tag.children
        if children:
            child_list = []
            for child in children:
                result = inner(child)
                if result is not None:
                    child_list.append(result)
            node['children'] = child_list

        return node

    return inner(soup)['children']

def clean_content(html_content):
    """ Remove unwanted text from the content. """
    html_content = html_content.replace(UNWANTED_TEXT_BLOCK, "").strip()
    unwanted_text = "<h2>Sign up for YYZ Deals Alerts</h2>"
    if unwanted_text in html_content:
        html_content = html_content.split(unwanted_text)[0]
    return html_content

def create_telegraph_post(title, content):
    """ Create a new Telegra.ph post. """
    formatted_content = html_to_content(content)
    response = requests.post(TELEGRAPH_CREATE_URL, json={
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "title": title,
        "author_name": "YYZ Deals Bot",
        "content": formatted_content,
    })
    if response.status_code == 200 and "result" in response.json():
        return response.json()["result"]["url"]
    return None

def edit_telegraph_post(path, title, content):
    """ Edit an existing Telegra.ph post. """
    formatted_content = html_to_content(content)
    response = requests.post(TELEGRAPH_EDIT_URL, json={
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "path": path,
        "title": title,
        "content": formatted_content,
    })
    if response.status_code == 200 and "result" in response.json():
        return response.json()["result"]["url"]
    return None

def get_last_10_messages():
    """ Fetch the last 10 messages from the Telegram channel. """
    response = requests.get(f"{TELEGRAM_API_URL}/getUpdates")
    if response.status_code == 200:
        messages = response.json().get("result", [])[-10:]
        parsed_messages = {}
        for msg in messages:
            if "message" in msg and "text" in msg["message"]:
                text = msg["message"]["text"]
                title = text.split("\n")[0].replace("📢 *", "").replace("*", "").strip()
                if "[Read More](" in text:
                    telegraph_url = text.split("[Read More](")[-1].split(")")[0]
                    parsed_messages[title] = {"message_id": msg["message"]["message_id"], "telegraph_url": telegraph_url}
        return parsed_messages
    return {}

def check_feed():
    """ Process RSS feed and post updates to Telegram. """
    global posted_articles
    posted_articles = get_last_10_messages()
    response = requests.get(RSS_FEED_URL)
    root = ET.fromstring(response.content)
    
    for entry in root.findall(".//entry"):
        title = entry.find("title").text.strip()
        content_html = clean_content(entry.find("content").text)

        if title in posted_articles:
            old_telegraph_url = posted_articles[title]["telegraph_url"]
            telegraph_path = old_telegraph_url.split("/telegraph/")[-1]
            new_telegraph_url = edit_telegraph_post(telegraph_path, title, content_html)
            if new_telegraph_url:
                requests.post(f"{TELEGRAM_API_URL}/editMessageText", data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "message_id": posted_articles[title]["message_id"],
                    "text": f"📢 *{title}*\n[Read More]({new_telegraph_url})",
                    "parse_mode": "Markdown"
                })
        else:
            telegraph_url = create_telegraph_post(title, content_html)
            if telegraph_url:
                message_text = f"📢 *{title}*\n[Read More]({telegraph_url})"
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message_text,
                    "parse_mode": "Markdown"
                })

if __name__ == "__main__":
    check_feed()
