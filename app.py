import os
import asyncio
import requests
import subprocess
import random
import re
import threading
from urllib.parse import urlparse
from flask import Flask

from telethon import TelegramClient, events

# =========================
# TELEGRAM CONFIG
# =========================

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

if not api_id:
    raise ValueError("API_ID belum diset di Secrets")

api_id = int(api_id)

client = TelegramClient("bot", api_id, api_hash)

# =========================
# TEMP STORAGE (Spaces safe)
# =========================

BASE = "/tmp"

VIDEO_DIR = os.path.join(BASE, "videos")
IMAGE_DIR = os.path.join(BASE, "images")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# =========================
# USER AGENT
# =========================

USER_AGENTS = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
"Mozilla/5.0 (X11; Linux x86_64)",
"Mozilla/5.0 (Linux; Android 13)"
]

def headers():
    return {
        "User-Agent": random.choice(USER_AGENTS)
    }

# =========================
# DOWNLOAD
# =========================

def download_file(url, path):

    r = requests.get(url, headers=headers(), stream=True)

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

# =========================
# CLEAN FILE
# =========================

def cleanup(path):

    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass

# =========================
# TIKTOK
# =========================

def get_tiktok(url):

    try:

        r = requests.get(
            "https://tikwm.com/api/",
            params={"url": url},
            headers=headers()
        )

        return r.json()["data"]

    except:

        return None


async def handle_tt(event, url):

    await event.reply("Fetching TikTok...")

    data = get_tiktok(url)

    if not data:
        await event.reply("Gagal mengambil video")
        return

    if data.get("images"):

        files = []

        for i, img in enumerate(data["images"]):

            path = os.path.join(IMAGE_DIR, f"{data['id']}_{i}.jpg")

            download_file(img, path)

            files.append(path)

        await client.send_file(event.chat_id, files)

        for f in files:
            cleanup(f)

    else:

        video = data["play"]

        path = os.path.join(VIDEO_DIR, f"{data['id']}.mp4")

        download_file(video, path)

        await client.send_file(event.chat_id, path)

        cleanup(path)

# =========================
# X / TWITTER
# =========================

def get_x_data(url):

    api = url.replace("x.com", "api.vxtwitter.com")

    try:
        r = requests.get(api, headers=headers())
        return r.json()
    except:
        return None


async def handle_x(event, url):

    await event.reply("Fetching X media...")

    data = get_x_data(url)

    if not data:
        await event.reply("Media tidak ditemukan")
        return

    media_list = data.get("media_extended", [])

    files = []

    tweet_id = url.split("/")[-1]

    for i, media in enumerate(media_list):

        if media["type"] == "image":

            img = media["url"] + "?name=orig"

            path = os.path.join(IMAGE_DIR, f"{tweet_id}_{i}.jpg")

            download_file(img, path)

            files.append(path)

    if files:

        await client.send_file(event.chat_id, files)

        for f in files:
            cleanup(f)

# =========================
# COMMANDS
# =========================

@client.on(events.NewMessage(pattern=r"^/start"))
async def start(event):

    await event.reply(
        "Downloader Bot\n\n"
        "/tt <link> → TikTok\n"
        "/x <link> → X/Twitter"
    )


@client.on(events.NewMessage(pattern=r"^/tt "))
async def tt(event):

    url = event.message.text.split(" ",1)[1]

    await handle_tt(event, url)


@client.on(events.NewMessage(pattern=r"^/x "))
async def x(event):

    url = event.message.text.split(" ",1)[1]

    await handle_x(event, url)

# =========================
# RUN TELEGRAM BOT
# =========================

async def start_bot():

    await client.start(bot_token=bot_token)

    print("Bot running...")

    await client.run_until_disconnected()


def run_bot():

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(start_bot())

# =========================
# FLASK SERVER (Spaces)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram Downloader Bot Running"


threading.Thread(target=run_bot).start()

app.run(host="0.0.0.0", port=7860)