import os
import requests
import subprocess
import random
import re
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from pymediainfo import MediaInfo

# =========================
# TELEGRAM CONFIG
# =========================

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

client = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

# =========================
# PATH
# =========================

BASE = os.path.dirname(os.path.abspath(__file__))

VIDEO_DIR = os.path.join(BASE, "downloads", "videos")
IMAGE_DIR = os.path.join(BASE, "downloads", "images")
XNXX_DIR = os.path.join(BASE, "downloads", "xnxx")

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(XNXX_DIR, exist_ok=True)

# =========================
# USER AGENT
# =========================

USER_AGENTS = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
"Mozilla/5.0 (X11; Linux x86_64)",
"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
"Mozilla/5.0 (Linux; Android 13)"
]

def headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.xnxx.com/"
    }

# =========================
# DOWNLOAD FILE
# =========================

def download_file(url, path):

    r = requests.get(url, headers=headers(), stream=True)

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

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

    await event.reply("🔎 Fetching TikTok...")

    data = get_tiktok(url)

    if not data:
        await event.reply("❌ Tidak bisa mengambil video")
        return

    if data.get("images"):

        files = []

        for i, img in enumerate(data["images"]):

            path = os.path.join(IMAGE_DIR, f"{data['id']}_{i}.jpg")

            download_file(img, path)

            files.append(path)

        await client.send_file(event.chat_id, files)

    else:

        video = data["play"]

        path = os.path.join(VIDEO_DIR, f"{data['id']}.mp4")

        download_file(video, path)

        await client.send_file(event.chat_id, path)

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

    await event.reply("🔎 Fetching X media...")

    data = get_x_data(url)

    if not data:
        await event.reply("❌ Media tidak ditemukan")
        return

    media_list = data.get("media_extended", [])

    if not media_list:
        await event.reply("❌ Tidak ada media")
        return

    files = []

    tweet_id = url.split("/")[-1]

    for i, media in enumerate(media_list):

        if media["type"] == "image":

            img = media["url"] + "?name=orig"

            path = os.path.join(IMAGE_DIR, f"{tweet_id}_{i}.jpg")

            download_file(img, path)

            files.append(path)

        elif media["type"] == "video":

            m3u8 = media["url"]

            path = os.path.join(VIDEO_DIR, f"{tweet_id}.mp4")

            subprocess.run([
                "ffmpeg",
                "-loglevel","error",
                "-y",
                "-i",m3u8,
                "-c","copy",
                path
            ])

            files.append(path)

    if files:
        await client.send_file(event.chat_id, files)

# =========================
# XNXX FUNCTIONS
# =========================

def extract_title(url):

    path = urlparse(url).path
    return path.split("/")[-1]


def get_video_stream(url):

    try:

        r = requests.get(url, headers=headers(), timeout=20)

        html = r.text

        # HLS
        m3u8 = re.search(r'https://[^"\']+\.m3u8[^"\']*', html)

        if m3u8:
            return ("m3u8", m3u8.group(0))

        # MP4 fallback
        mp4 = re.search(r'https://[^"\']+\.mp4[^"\']*', html)

        if mp4:
            return ("mp4", mp4.group(0))

        return (None,None)

    except:
        return (None,None)


def generate_thumbnail(video):

    thumb = video + ".jpg"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-ss","00:00:03",
        "-i",video,
        "-vframes","1",
        "-q:v","2",
        thumb
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb


def get_video_metadata(video):

    media_info = MediaInfo.parse(video)

    for track in media_info.tracks:

        if track.track_type == "Video":

            duration = int(track.duration / 1000)
            width = track.width
            height = track.height

            return duration,width,height

    return 0,0,0


async def handle_xn(event, url):

    await event.reply("🔎 Mencari stream video...")

    stream_type, stream_url = get_video_stream(url)

    if not stream_url:
        await event.reply("❌ Stream tidak ditemukan")
        return

    filename = extract_title(url)

    output = os.path.join(XNXX_DIR, filename + ".mp4")

    await event.reply("📥 Downloading video...")

    if stream_type == "m3u8":

        subprocess.run([
            "ffmpeg",
            "-loglevel","error",
            "-y",
            "-i",stream_url,
            "-c","copy",
            "-bsf:a","aac_adtstoasc",
            output
        ])

    else:

        download_file(stream_url, output)

    duration,width,height = get_video_metadata(output)

    thumb = generate_thumbnail(output)

    await client.send_file(
        event.chat_id,
        output,
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

# =========================
# COMMANDS
# =========================

@client.on(events.NewMessage(pattern=r"^/start"))
async def start(event):

    await event.reply(
        "Downloader Bot\n\n"
        "/tt <link> → TikTok\n"
        "/x <link> → X/Twitter\n"
        "/xn <link> → XNXX"
    )


@client.on(events.NewMessage(pattern=r"^/tt "))
async def tt(event):

    url = event.message.text.split(" ",1)[1]
    await handle_tt(event, url)


@client.on(events.NewMessage(pattern=r"^/x "))
async def x(event):

    url = event.message.text.split(" ",1)[1]
    await handle_x(event, url)


@client.on(events.NewMessage(pattern=r"^/xn "))
async def xn(event):

    url = event.message.text.split(" ",1)[1]
    await handle_xn(event, url)


print("Bot running...")

client.run_until_disconnected()