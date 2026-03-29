import os
import asyncio
import requests
import subprocess
import random
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

# =========================
# TELEGRAM CONFIG
# =========================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

client = TelegramClient("bot", api_id, api_hash)

# =========================
# TEMP STORAGE
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
    return {"User-Agent": random.choice(USER_AGENTS)}

# =========================
# DOWNLOAD
# =========================

def download_file(url, path):

    r = requests.get(url, headers=headers(), stream=True)

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

def cleanup(path):

    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass

# =========================
# VIDEO METADATA (FFPROBE)
# =========================

def get_video_metadata(video):

    try:

        cmd = [
            "ffprobe",
            "-v","error",
            "-select_streams","v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of","default=noprint_wrappers=1:nokey=1",
            video
        ]

        result = subprocess.check_output(cmd).decode().split()

        width = int(result[0])
        height = int(result[1])
        duration = int(float(result[2]))

        return duration,width,height

    except:

        return 0,0,0

# =========================
# THUMBNAIL
# =========================

def generate_thumbnail(video):

    thumb = video + ".jpg"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-ss","00:00:02",
        "-i",video,
        "-frames:v","1",
        thumb
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb

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
        await event.reply("Failed to fetch video")
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

        thumb = generate_thumbnail(path)

        duration,width,height = get_video_metadata(path)

        await client.send_file(
            event.chat_id,
            path,
            thumb=thumb,
            supports_streaming=True,
            attributes=[
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ]
        )

        cleanup(path)
        cleanup(thumb)

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
        await event.reply("Media not found")
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

        elif media["type"] == "video":

            video_url = media["url"]

            path = os.path.join(VIDEO_DIR, f"{tweet_id}.mp4")

            subprocess.run([
                "ffmpeg",
                "-y",
                "-i",video_url,
                "-c","copy",
                path
            ])

            thumb = generate_thumbnail(path)

            duration,width,height = get_video_metadata(path)

            await client.send_file(
                event.chat_id,
                path,
                thumb=thumb,
                supports_streaming=True,
                attributes=[
                    DocumentAttributeVideo(
                        duration=duration,
                        w=width,
                        h=height,
                        supports_streaming=True
                    )
                ]
            )

            cleanup(path)
            cleanup(thumb)

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
# RUN BOT
# =========================

async def main():

    await client.start(bot_token=bot_token)

    print("Bot running on Koyeb 🚀")

    await client.run_until_disconnected()


asyncio.run(main())
