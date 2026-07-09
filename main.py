import os
import json
import uuid
import random
import string
import time
import hashlib
import re
import threading
import asyncio
import base64
from datetime import timedelta
from typing import Optional, Dict, Literal

import aiohttp
import requests as http_requests
import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask, request, send_file, render_template_string, make_response

ADMIN_ID = 763815168894828576
PANEL_CHANNEL_ID = 1524464161113899082
FILESHARE_PANEL_CHANNEL_ID = 1524475681247985756
PASSWORD_PANEL_CHANNEL_ID = 1524494565778788513
IPLOOKUP_PANEL_CHANNEL_ID = 1524496790890479727
TIER_PANEL_CHANNEL_ID = 1524500874309800097
TIER_DATA_CHANNEL_ID = 1524525967811547348
PASSWORD_BREACH_PANEL_CHANNEL_ID = 1524531064544956548
CALCULATOR_PANEL_CHANNEL_ID = 1524538850947633343
UNIT_CONVERTER_PANEL_CHANNEL_ID = 1524538893053989058
CURRENCY_CONVERTER_PANEL_CHANNEL_ID = 1524538928231747624
USER_INFO_PANEL_CHANNEL_ID = 1524539019562717385
CRYPTO_LOOKUP_PANEL_CHANNEL_ID = 1524539205039161554
TRANSLATOR_PANEL_CHANNEL_ID = 1524539284227620864
TIER_ALLOWED_USERS = [763815168894828576, 529014657537540096]
CATEGORY_ID = 1524464161113899080
NEW_FEATURES_CATEGORY_ID = 1524540870848807073
MAILTM_BASE = "https://api.mail.tm"
FILESHARE_URL = os.getenv("FILESHARE_URL", "http://localhost:5000")
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fileshare_sessions.json")
TOKEN = "MTUyNDQ3Mjc5NTIwNjEyMzcyMQ.GHyx83.z0ZjR3gFXBq4e5rqB_49Mu_4yHjknn81MCedD8"

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
EXPIRY_SECONDS = 3 * 60 * 60
os.makedirs(UPLOAD_DIR, exist_ok=True)

files_db = {}
password_configs: Dict[int, Dict] = {}
_bot_instance: Optional['Bot'] = None


def generate_password(length: int, use_upper: bool, use_lower: bool, use_numbers: bool, use_special: bool) -> str:
    charset = ""
    if use_upper:
        charset += string.ascii_uppercase
    if use_lower:
        charset += string.ascii_lowercase
    if use_numbers:
        charset += string.digits
    if use_special:
        charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not charset:
        charset = string.ascii_letters + string.digits
    return "".join(random.choice(charset) for _ in range(length))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FileDrop</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { width: 100%%; max-width: 500px; padding: 40px; }
        h1 { font-size: 2rem; margin-bottom: 8px; text-align: center; }
        .subtitle { color: #888; text-align: center; margin-bottom: 40px; font-size: 0.9rem; }
        .drop-zone { border: 2px dashed #333; border-radius: 12px; padding: 60px 20px; text-align: center; cursor: pointer; transition: all 0.2s; margin-bottom: 20px; }
        .drop-zone:hover, .drop-zone.dragover { border-color: #5865F2; background: rgba(88,101,242,0.05); }
        .drop-zone p { color: #888; font-size: 1.1rem; }
        .drop-zone .icon { font-size: 3rem; margin-bottom: 12px; }
        input[type="file"] { display: none; }
        .btn { width: 100%%; padding: 14px; background: #5865F2; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        .btn:hover { background: #4752c4; }
        .btn:disabled { background: #333; color: #666; cursor: not-allowed; }
        .result { margin-top: 30px; background: #111; border: 1px solid #222; border-radius: 12px; padding: 24px; text-align: center; }
        .result .label { color: #888; font-size: 0.8rem; margin-bottom: 8px; }
        .result .filename { color: #888; font-size: 0.85rem; margin-bottom: 12px; }
        .result .expiry { color: #666; font-size: 0.75rem; margin-top: 12px; }
        .copy-btn { padding: 10px 24px; background: #222; color: #fff; border: 1px solid #333; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
        .copy-btn:hover { background: #333; }
        .progress { width: 100%%; height: 4px; background: #222; border-radius: 2px; margin-top: 16px; display: none; }
        .progress.show { display: block; }
        .progress .bar { height: 100%%; background: #5865F2; border-radius: 2px; width: 0%%; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <h1>FileDrop</h1>
        <p class="subtitle">Upload a file, get a link. Files expire after 3 hours.</p>
        {% if uploaded %}
        <div class="result">
            <div class="label">FILE UPLOADED</div>
            <p style="color:#888;margin:12px 0">Your file has been uploaded successfully. The download link has been sent to Discord.</p>
            <div class="expiry">Link expires in 3 hours</div>
        </div>
        {% else %}
        <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
            <input type="hidden" name="session_id" value="{{ session_id }}">
            <div class="drop-zone" id="dropZone">
                <div class="icon">&#128229;</div>
                <p>Drag & drop a file here or click to browse</p>
            </div>
            <input type="file" id="fileInput" name="file">
            <button type="submit" class="btn" id="uploadBtn" disabled>Upload File</button>
            <div class="progress" id="progress"><div class="bar" id="bar"></div></div>
        </form>
        {% endif %}
    </div>
    <script>
    if (document.getElementById('uploadForm')) {
        var dz = document.getElementById('dropZone');
        var fi = document.getElementById('fileInput');
        var ub = document.getElementById('uploadBtn');
        dz.onclick = function() { fi.click(); };
        dz.ondragover = function(e) { e.preventDefault(); dz.classList.add('dragover'); };
        dz.ondragleave = function() { dz.classList.remove('dragover'); };
        dz.ondrop = function(e) { e.preventDefault(); dz.classList.remove('dragover'); fi.files = e.dataTransfer.files; fi.dispatchEvent(new Event('change')); };
        fi.onchange = function() { if (fi.files.length) { dz.querySelector('p').textContent = fi.files[0].name; ub.disabled = false; } };
        document.getElementById('uploadForm').onsubmit = function(e) {
            e.preventDefault();
            var fd = new FormData(this);
            var xhr = new XMLHttpRequest();
            document.getElementById('progress').classList.add('show');
            ub.disabled = true; ub.textContent = 'Uploading...';
            xhr.upload.onprogress = function(ev) { if (ev.lengthComputable) document.getElementById('bar').style.width = (ev.loaded/ev.total*100)+'%%'; };
            xhr.onload = function() { if (xhr.status===200) document.body.innerHTML = xhr.responseText; };
            xhr.open('POST','/upload'); xhr.send(fd);
        };
    }
    </script>
</body>
</html>"""


flask_app = Flask(__name__)


def load_sessions() -> Dict:
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sessions(data: Dict):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


TIER_DATA_MARKER = "TIER_ACCOUNTS_DATA"


TIER_DATA_MARKER = "TIER_ACCOUNTS_DATA"


async def load_tier_accounts() -> list:
    bot = _bot_instance
    if not bot:
        return []
    channel = bot.get_channel(TIER_DATA_CHANNEL_ID)
    if not channel:
        return []
    try:
        async for message in channel.history(limit=50):
            if message.author == bot.user and TIER_DATA_MARKER in message.content:
                json_str = message.content.split(TIER_DATA_MARKER, 1)[1].strip()
                if json_str.startswith("```json"):
                    json_str = json_str[len("```json"):].strip()
                if json_str.endswith("```"):
                    json_str = json_str[:-3].strip()
                raw = json.loads(json_str)
                return normalize_tier_accounts(raw)
    except Exception as e:
        print(f"[TIER] Error loading accounts: {e}")
    return []


async def save_tier_accounts(data: list):
    bot = _bot_instance
    if not bot:
        return
    channel = bot.get_channel(TIER_DATA_CHANNEL_ID)
    if not channel:
        return
    content = f"{TIER_DATA_MARKER}\n```json\n{json.dumps(data, indent=2)}\n```"
    try:
        async for message in channel.history(limit=50):
            if message.author == bot.user and TIER_DATA_MARKER in message.content:
                await message.edit(content=content)
                return
        await channel.send(content=content)
    except Exception as e:
        print(f"[TIER] Error saving accounts: {e}")


def normalize_tier_accounts(raw: list) -> list:
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append({"name": item, "added_by": 0})
        elif isinstance(item, dict):
            result.append(item)
    return result


def get_tier_account_names(accounts: list) -> list:
    return [a["name"] if isinstance(a, dict) else a for a in accounts]


def random_string(length: int = 10) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def cleanup_files():
    while True:
        now = time.time()
        expired = [fid for fid, info in list(files_db.items()) if now - info["uploaded_at"] > EXPIRY_SECONDS]
        for fid in expired:
            info = files_db.pop(fid, None)
            if info:
                path = os.path.join(UPLOAD_DIR, fid)
                if os.path.exists(path):
                    os.remove(path)
        time.sleep(60)


@flask_app.route("/", defaults={"path": ""})
@flask_app.route("/<path:path>")
def index(path):
    session_id = request.args.get("session", "")
    return render_template_string(HTML_TEMPLATE, session_id=session_id, uploaded=False)


@flask_app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return "No file", 400

    session_id = request.form.get("session_id", "")
    fid = uuid.uuid4().hex[:10]
    save_path = os.path.join(UPLOAD_DIR, fid)
    f.save(save_path)
    files_db[fid] = {"filename": f.filename, "uploaded_at": time.time()}
    link = request.host_url + "d/" + fid

    if session_id:
        sessions = load_sessions()
        session = sessions.get(session_id)
        if session:
            webhook_url = session.get("webhook_url")
            if webhook_url:
                try:
                    embed = {
                        "title": "New File Uploaded",
                        "description": f"**{f.filename}** is ready to download.\n\n[Download File]({link})\n\n*Expires in 3 hours.*",
                        "color": 0x5865F2,
                    }
                    http_requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
                except Exception as e:
                    print(f"Webhook post failed: {e}")

    resp = make_response(render_template_string(HTML_TEMPLATE, session_id=session_id, uploaded=True))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@flask_app.route("/d/<fid>")
def download(fid):
    info = files_db.get(fid)
    if not info:
        return "File not found or expired", 404
    if time.time() - info["uploaded_at"] > EXPIRY_SECONDS:
        files_db.pop(fid, None)
        path = os.path.join(UPLOAD_DIR, fid)
        if os.path.exists(path):
            os.remove(path)
        return "File expired", 404
    path = os.path.join(UPLOAD_DIR, fid)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name=info["filename"])


def get_channel_owner(channel_id: int) -> Optional[int]:
    sessions = load_sessions()
    for sid, data in sessions.items():
        if data.get("channel_id") == channel_id:
            return data.get("owner_id")
    return None


class MailTmClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_domain(self) -> str:
        async with self.session.get(f"{MAILTM_BASE}/domains") as resp:
            data = await resp.json()
            if resp.status != 200 or "hydra:member" not in data or not data["hydra:member"]:
                raise RuntimeError("No domains available from mail.tm")
            return data["hydra:member"][0]["domain"]

    async def create_account(self, address: str, password: str) -> Dict:
        async with self.session.post(f"{MAILTM_BASE}/accounts", json={"address": address, "password": password}) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise RuntimeError(data.get("message", "Failed to create account"))
            return data

    async def get_token(self, address: str, password: str) -> str:
        async with self.session.post(f"{MAILTM_BASE}/token", json={"address": address, "password": password}) as resp:
            data = await resp.json()
            if resp.status != 200 or "token" not in data:
                raise RuntimeError(data.get("message", "Failed to get token"))
            return data["token"]

    async def list_messages(self, token: str) -> Dict:
        headers = {"Authorization": f"Bearer {token}"}
        async with self.session.get(f"{MAILTM_BASE}/messages", headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(data.get("message", "Failed to fetch messages"))
            return data

    async def delete_message(self, token: str, message_id: str) -> None:
        headers = {"Authorization": f"Bearer {token}"}
        async with self.session.delete(f"{MAILTM_BASE}/messages/{message_id}", headers=headers) as resp:
            if resp.status not in (200, 204):
                data = await resp.json()
                raise RuntimeError(data.get("message", "Failed to delete message"))

    async def get_message(self, token: str, message_id: str) -> Dict:
        headers = {"Authorization": f"Bearer {token}"}
        async with self.session.get(f"{MAILTM_BASE}/messages/{message_id}", headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(data.get("message", "Failed to fetch message"))
            return data

    async def delete_account(self, token: str, account_id: str) -> None:
        headers = {"Authorization": f"Bearer {token}"}
        async with self.session.delete(f"{MAILTM_BASE}/accounts/{account_id}", headers=headers) as resp:
            if resp.status not in (200, 202, 204):
                data = await resp.json()
                raise RuntimeError(data.get("message", "Failed to delete account"))


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=["!", "?"], intents=intents, help_command=None)
        self.session: Optional[aiohttp.ClientSession] = None
        self.mailtm: Optional[MailTmClient] = None
        self.user_accounts: Dict[int, list] = {}
        self.channel_accounts: Dict[int, Dict] = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.mailtm = MailTmClient(self.session)
        self.tree.add_command(inbox_command)
        self.tree.add_command(delete_command)
        self.tree.add_command(add_command)
        self.tree.add_command(remove_command)
        self.tree.add_command(deletechannel_command)
        self.tree.add_command(giveaway_command)
        self.tree.add_command(endgiveaway_command)
        self.tree.add_command(help_command)
        self.add_view(TempMailPanelView(self))
        self.add_view(DeleteAccountView(self))
        self.add_view(FileSharePanelView(self))
        self.add_view(FileShareDeleteView())
        self.add_view(PasswordGenPanelView(self))
        self.add_view(PasswordGenConfigView())
        self.add_view(PasswordGenDeleteView())
        self.add_view(TierPanelView(self))
        self.add_view(TierConfigView())
        self.add_view(IPLookupPanelView(self))
        self.add_view(IPLookupConfigView())
        self.add_view(PasswordBreachPanelView(self))
        self.add_view(PasswordBreachConfigView())
        self.add_view(CalculatorPanelView(self))
        self.add_view(CalculatorConfigView())
        self.add_view(UnitConverterPanelView(self))
        self.add_view(UnitConverterConfigView())
        self.add_view(CurrencyConverterPanelView(self))
        self.add_view(CurrencyConverterConfigView())
        self.add_view(UserInfoPanelView(self))
        self.add_view(UserInfoConfigView())
        self.add_view(CryptoLookupPanelView(self))
        self.add_view(CryptoLookupConfigView())
        self.add_view(TranslatorPanelView(self))
        self.add_view(TranslatorConfigView())
        self.poll_messages.start()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    async def on_ready(self):
        await self.tree.sync()
        await self.ensure_panels()
        print(f"Logged in as {self.user}")

    async def ensure_panels(self):
        channel = self.get_channel(PANEL_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            async for message in channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Temp Mail Service":
                        break
            else:
                embed = discord.Embed(
                    title="Temp Mail Service",
                    description="Click the button below to generate your private temp email inbox.",
                    color=discord.Color.green(),
                )
                await channel.send(embed=embed, view=TempMailPanelView(self))

        fs_channel = self.get_channel(FILESHARE_PANEL_CHANNEL_ID)
        if isinstance(fs_channel, discord.TextChannel):
            async for message in fs_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "File Share":
                        break
            else:
                embed = discord.Embed(
                    title="File Share",
                    description="Click the button below to upload a file. Files expire after 3 hours.",
                    color=discord.Color.blurple(),
                )
                await fs_channel.send(embed=embed, view=FileSharePanelView(self))

        pg_channel = self.get_channel(PASSWORD_PANEL_CHANNEL_ID)
        if isinstance(pg_channel, discord.TextChannel):
            async for message in pg_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Password Generator":
                        break
            else:
                embed = discord.Embed(
                    title="Password Generator",
                    description="Click the button below to create a password generator.",
                    color=discord.Color.blurple(),
                )
                await pg_channel.send(embed=embed, view=PasswordGenPanelView(self))

        il_channel = self.get_channel(IPLOOKUP_PANEL_CHANNEL_ID)
        if isinstance(il_channel, discord.TextChannel):
            async for message in il_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "IP Lookup / Geolocation":
                        break
            else:
                embed = discord.Embed(
                    title="IP Lookup / Geolocation",
                    description="Click the button below to look up an IP address and get geolocation info.",
                    color=discord.Color.blurple(),
                )
                await il_channel.send(embed=embed, view=IPLookupPanelView(self))

        tier_channel = self.get_channel(TIER_PANEL_CHANNEL_ID)
        if isinstance(tier_channel, discord.TextChannel):
            async for message in tier_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Tier Tracker":
                        break
            else:
                embed = discord.Embed(
                    title="Tier Tracker",
                    description="Click the button below to create a tier tracker channel.",
                    color=discord.Color.blurple(),
                )
                await tier_channel.send(embed=embed, view=TierPanelView(self))

        pb_channel = self.get_channel(PASSWORD_BREACH_PANEL_CHANNEL_ID)
        if isinstance(pb_channel, discord.TextChannel):
            async for message in pb_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Password Breach Check":
                        break
            else:
                embed = discord.Embed(
                    title="Password Breach Check",
                    description="Click the button below to check if a password has been leaked.",
                    color=discord.Color.red(),
                )
                await pb_channel.send(embed=embed, view=PasswordBreachPanelView(self))

        calc_channel = self.get_channel(CALCULATOR_PANEL_CHANNEL_ID)
        if isinstance(calc_channel, discord.TextChannel):
            async for message in calc_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Calculator":
                        break
            else:
                embed = discord.Embed(
                    title="Calculator",
                    description="Click the button below to calculate a math expression.",
                    color=discord.Color.blue(),
                )
                await calc_channel.send(embed=embed, view=CalculatorPanelView(self))

        unit_channel = self.get_channel(UNIT_CONVERTER_PANEL_CHANNEL_ID)
        if isinstance(unit_channel, discord.TextChannel):
            async for message in unit_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Unit Converter":
                        break
            else:
                embed = discord.Embed(
                    title="Unit Converter",
                    description="Click the button below to convert units.",
                    color=discord.Color.orange(),
                )
                await unit_channel.send(embed=embed, view=UnitConverterPanelView(self))

        curr_channel = self.get_channel(CURRENCY_CONVERTER_PANEL_CHANNEL_ID)
        if isinstance(curr_channel, discord.TextChannel):
            async for message in curr_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Currency Converter":
                        break
            else:
                embed = discord.Embed(
                    title="Currency Converter",
                    description="Click the button below to convert currencies.",
                    color=discord.Color.gold(),
                )
                await curr_channel.send(embed=embed, view=CurrencyConverterPanelView(self))

        ui_channel = self.get_channel(USER_INFO_PANEL_CHANNEL_ID)
        if isinstance(ui_channel, discord.TextChannel):
            async for message in ui_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Discord User Info":
                        break
            else:
                embed = discord.Embed(
                    title="Discord User Info",
                    description="Click the button below to look up a Discord user's profile info.",
                    color=discord.Color.purple(),
                )
                await ui_channel.send(embed=embed, view=UserInfoPanelView(self))

        cl_channel = self.get_channel(CRYPTO_LOOKUP_PANEL_CHANNEL_ID)
        if isinstance(cl_channel, discord.TextChannel):
            async for message in cl_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Crypto Lookup":
                        break
            else:
                embed = discord.Embed(
                    title="Crypto Lookup",
                    description="Click the button below to look up any cryptocurrency by name.",
                    color=discord.Color.orange(),
                )
                await cl_channel.send(embed=embed, view=CryptoLookupPanelView(self))

        tr_channel = self.get_channel(TRANSLATOR_PANEL_CHANNEL_ID)
        if isinstance(tr_channel, discord.TextChannel):
            async for message in tr_channel.history(limit=50):
                if message.author == self.user and message.embeds:
                    if message.embeds[0].title == "Language Translator":
                        break
            else:
                embed = discord.Embed(
                    title="Language Translator",
                    description="Click the button below to translate text between languages.",
                    color=discord.Color.dark_teal(),
                )
                await tr_channel.send(embed=embed, view=TranslatorPanelView(self))

    @tasks.loop(seconds=30)
    async def poll_messages(self):
        await self.wait_until_ready()
        if not self.mailtm:
            return
        for channel_id, account in list(self.channel_accounts.items()):
            token = account.get("token")
            user_id = account.get("owner_id")
            if not token or not user_id:
                continue
            channel = self.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            try:
                data = await self.mailtm.list_messages(token)
            except Exception:
                continue
            messages = data.get("hydra:member", [])
            seen_ids = account.setdefault("seen_ids", set())
            new_messages = [m for m in messages if m.get("id") not in seen_ids]
            if not new_messages:
                continue
            for msg in reversed(new_messages):
                msg_id = msg.get("id")
                if not msg_id:
                    continue
                try:
                    full = await self.mailtm.get_message(token, msg_id)
                except Exception:
                    continue
                seen_ids.add(msg_id)
                await self.send_full_message(channel, user_id, full)

    async def send_full_message(self, channel: discord.TextChannel, user_id: int, message_data: Dict):
        sender = message_data.get("from", {}).get("address", "Unknown")
        subject = message_data.get("subject", "(No subject)")
        text_body = message_data.get("text") or message_data.get("intro") or "(No content)"
        if len(text_body) > 3800:
            text_body = text_body[:3800] + "..."
        embed = discord.Embed(title=subject, description=text_body, color=discord.Color.green())
        embed.add_field(name="From", value=sender, inline=True)
        embed.set_footer(text=f"Message ID: {message_data.get('id', '?')}")
        await channel.send(content=f"<@{user_id}>", embed=embed)


class TempMailPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Create Temp Mail", style=discord.ButtonStyle.success, custom_id="temp_mail_create")
    async def create_temp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not self.bot.mailtm:
            await interaction.followup.send("Mail service not ready.", ephemeral=True)
            return
        try:
            is_admin = interaction.user.id == ADMIN_ID
            if not is_admin:
                existing = self.bot.user_accounts.get(interaction.user.id, [])
                if existing:
                    await interaction.followup.send("You already have a temp mail channel. Only admins can create multiple.", ephemeral=True)
                    return

            domain = await self.bot.mailtm.get_domain()
            local = random_string(10)
            address = f"{local}@{domain}"
            password = random_string(16)
            account = await self.bot.mailtm.create_account(address, password)
            token = await self.bot.mailtm.get_token(address, password)

            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            suffix = random_string(4)
            channel_name = f"temp-mail-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            temp_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            account_entry = {
                "owner_id": interaction.user.id,
                "address": address,
                "password": password,
                "token": token,
                "account_id": account.get("id"),
                "channel_id": temp_channel.id,
                "seen_ids": set(),
            }
            self.bot.user_accounts.setdefault(interaction.user.id, []).append(account_entry)
            self.bot.channel_accounts[temp_channel.id] = account_entry

            embed = discord.Embed(
                title="Your Temp Mail Inbox",
                description=f"Email Address: {address}\nNew emails will be delivered here automatically. Use /delete to remove messages or the button below to close this inbox.",
                color=discord.Color.green(),
            )
            view = DeleteAccountView(self.bot)
            msg = await temp_channel.send(content=interaction.user.mention, embed=embed, view=view)
            await msg.pin()
            await interaction.followup.send(f"Your temp mail channel has been created: {temp_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class FileSharePanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="File Share", style=discord.ButtonStyle.primary, custom_id="file_share_create")
    async def create_fileshare(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            suffix = random_string(4)
            channel_name = f"fileshare-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            fs_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            webhook = await fs_channel.create_webhook(name="FileShare")

            session_id = random_string(12)
            sessions = load_sessions()
            sessions[session_id] = {
                "channel_id": fs_channel.id,
                "webhook_url": webhook.url,
                "owner_id": interaction.user.id,
                "created_at": time.time(),
            }
            save_sessions(sessions)

            upload_url = f"{FILESHARE_URL}/?session={session_id}"
            embed = discord.Embed(
                title="Your File Share Channel",
                description=f"Click the link below to upload a file.\nFiles expire after 3 hours and the download link will be posted here.\n\n[Upload File]({upload_url})",
                color=discord.Color.blurple(),
            )
            view = FileShareDeleteView()
            msg = await fs_channel.send(content=interaction.user.mention, embed=embed, view=view)
            await msg.pin()
            await interaction.followup.send(f"Your file share channel has been created: {fs_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class DeleteAccountView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Delete Temp Mail", style=discord.ButtonStyle.danger, custom_id="temp_mail_delete")
    async def delete_temp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            account = self.bot.channel_accounts.get(interaction.channel_id)
            if not account:
                await interaction.followup.send("No temp mail account found for this channel.", ephemeral=True)
                return
            owner_id = account.get("owner_id")
            if interaction.user.id != owner_id and interaction.user.id != ADMIN_ID:
                await interaction.followup.send("Only the owner or admin can delete this temp mail.", ephemeral=True)
                return
            if not self.bot.mailtm:
                await interaction.followup.send("Mail service not ready.", ephemeral=True)
                return
            account_id = account.get("account_id")
            token = account.get("token")
            if account_id and token:
                await self.bot.mailtm.delete_account(token, account_id)
            owner_accounts = self.bot.user_accounts.get(owner_id, [])
            owner_accounts = [a for a in owner_accounts if a.get("channel_id") != interaction.channel_id]
            if owner_accounts:
                self.bot.user_accounts[owner_id] = owner_accounts
            else:
                self.bot.user_accounts.pop(owner_id, None)
            self.bot.channel_accounts.pop(interaction.channel_id, None)
            await interaction.followup.send("Temp mail account deleted. This channel will be removed.", ephemeral=True)
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel):
                await asyncio.sleep(2)
                await channel.delete()
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class FileShareDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete File Share", style=discord.ButtonStyle.danger, custom_id="file_share_delete")
    async def delete_fileshare(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            sessions = load_sessions()
            session_to_delete = None
            for sid, data in sessions.items():
                if data.get("channel_id") == interaction.channel_id:
                    session_to_delete = sid
                    break
            is_admin = interaction.user.id == ADMIN_ID
            if session_to_delete:
                owner_id = sessions[session_to_delete].get("owner_id")
                if interaction.user.id != owner_id and not is_admin:
                    await interaction.followup.send("Only the owner or admin can delete this.", ephemeral=True)
                    return
                del sessions[session_to_delete]
                save_sessions(sessions)
            elif not is_admin:
                await interaction.followup.send("No file share session found for this channel.", ephemeral=True)
                return

            await interaction.followup.send("File share deleted. This channel will be removed.", ephemeral=True)
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel):
                await asyncio.sleep(2)
                await channel.delete()
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class PasswordGenPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Password Generator", style=discord.ButtonStyle.primary, custom_id="passgen_create")
    async def create_passgen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            suffix = random_string(4)
            channel_name = f"password-gen-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            pg_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            password_configs[pg_channel.id] = {
                "owner_id": interaction.user.id,
                "length": 16,
                "use_upper": True,
                "use_lower": True,
                "use_numbers": True,
                "use_special": False,
            }

            config = password_configs[pg_channel.id]
            embed = discord.Embed(
                title="Password Generator",
                description="Configure your password settings below, then click Generate.",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Length", value=str(config["length"]), inline=True)
            embed.add_field(name="Uppercase (A-Z)", value="Yes" if config["use_upper"] else "No", inline=True)
            embed.add_field(name="Lowercase (a-z)", value="Yes" if config["use_lower"] else "No", inline=True)
            embed.add_field(name="Numbers (0-9)", value="Yes" if config["use_numbers"] else "No", inline=True)
            embed.add_field(name="Special (!@#)", value="Yes" if config["use_special"] else "No", inline=True)

            view = PasswordGenConfigView()
            msg = await pg_channel.send(content=interaction.user.mention, embed=embed, view=view)
            await msg.pin()
            await interaction.followup.send(f"Your password generator channel has been created: {pg_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class LengthModal(discord.ui.Modal, title="Set Password Length"):
    length_input = discord.ui.TextInput(
        label="Password Length (1-100)",
        placeholder="Enter a number between 1 and 100",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            length = int(self.length_input.value)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
            return
        if length < 1 or length > 100:
            await interaction.response.send_message("Length must be between 1 and 100.", ephemeral=True)
            return

        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        config["length"] = length

        embed = discord.Embed(
            title="Password Generator",
            description="Configure your password settings below, then click Generate.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Length", value=str(config["length"]), inline=True)
        embed.add_field(name="Uppercase (A-Z)", value="Yes" if config["use_upper"] else "No", inline=True)
        embed.add_field(name="Lowercase (a-z)", value="Yes" if config["use_lower"] else "No", inline=True)
        embed.add_field(name="Numbers (0-9)", value="Yes" if config["use_numbers"] else "No", inline=True)
        embed.add_field(name="Special (!@#)", value="Yes" if config["use_special"] else "No", inline=True)

        await interaction.response.edit_message(embed=embed)


class PasswordGenConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="A-Z", style=discord.ButtonStyle.success, custom_id="pg_upper", row=0)
    async def toggle_upper(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can change settings.", ephemeral=True)
            return
        config["use_upper"] = not config["use_upper"]
        button.style = discord.ButtonStyle.success if config["use_upper"] else discord.ButtonStyle.grey
        await self.update_embed(interaction)

    @discord.ui.button(label="a-z", style=discord.ButtonStyle.success, custom_id="pg_lower", row=0)
    async def toggle_lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can change settings.", ephemeral=True)
            return
        config["use_lower"] = not config["use_lower"]
        button.style = discord.ButtonStyle.success if config["use_lower"] else discord.ButtonStyle.grey
        await self.update_embed(interaction)

    @discord.ui.button(label="0-9", style=discord.ButtonStyle.success, custom_id="pg_numbers", row=0)
    async def toggle_numbers(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can change settings.", ephemeral=True)
            return
        config["use_numbers"] = not config["use_numbers"]
        button.style = discord.ButtonStyle.success if config["use_numbers"] else discord.ButtonStyle.grey
        await self.update_embed(interaction)

    @discord.ui.button(label="!@#", style=discord.ButtonStyle.grey, custom_id="pg_special", row=0)
    async def toggle_special(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can change settings.", ephemeral=True)
            return
        config["use_special"] = not config["use_special"]
        button.style = discord.ButtonStyle.success if config["use_special"] else discord.ButtonStyle.grey
        await self.update_embed(interaction)

    @discord.ui.button(label="Set Length", style=discord.ButtonStyle.secondary, custom_id="pg_length", row=1)
    async def set_length(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can change settings.", ephemeral=True)
            return
        await interaction.response.send_modal(LengthModal())

    @discord.ui.button(label="Generate", style=discord.ButtonStyle.green, custom_id="pg_generate", row=2)
    async def generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.send_message("No config found.", ephemeral=True)
            return
        if interaction.user.id != config["owner_id"] and interaction.user.id != ADMIN_ID:
            await interaction.response.send_message("Only the channel owner can generate passwords.", ephemeral=True)
            return
        password = generate_password(
            config["length"],
            config["use_upper"],
            config["use_lower"],
            config["use_numbers"],
            config["use_special"],
        )
        await interaction.response.send_message(f"Your generated password:\n```\n{password}\n```", ephemeral=True)

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="pg_delete_btn", row=3)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = password_configs.get(interaction.channel_id)
        is_admin = interaction.user.id == ADMIN_ID
        if config:
            if interaction.user.id != config["owner_id"] and not is_admin:
                await interaction.followup.send("Only the owner or admin can delete this.", ephemeral=True)
                return
            del password_configs[interaction.channel_id]
        elif not is_admin:
            await interaction.followup.send("No password generator found for this channel.", ephemeral=True)
            return
        await interaction.followup.send("Channel deleted.", ephemeral=True)
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel):
            await asyncio.sleep(2)
            await channel.delete()

    async def update_embed(self, interaction: discord.Interaction):
        config = password_configs.get(interaction.channel_id)
        if not config:
            await interaction.response.edit_message(view=self)
            return
        embed = discord.Embed(
            title="Password Generator",
            description="Configure your password settings below, then click Generate.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Length", value=str(config["length"]), inline=True)
        embed.add_field(name="Uppercase (A-Z)", value="Yes" if config["use_upper"] else "No", inline=True)
        embed.add_field(name="Lowercase (a-z)", value="Yes" if config["use_lower"] else "No", inline=True)
        embed.add_field(name="Numbers (0-9)", value="Yes" if config["use_numbers"] else "No", inline=True)
        embed.add_field(name="Special (!@#)", value="Yes" if config["use_special"] else "No", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)


class PasswordGenDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Password Generator", style=discord.ButtonStyle.danger, custom_id="pg_delete")
    async def delete_passgen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            config = password_configs.get(interaction.channel_id)
            is_admin = interaction.user.id == ADMIN_ID
            if config:
                if interaction.user.id != config["owner_id"] and not is_admin:
                    await interaction.followup.send("Only the owner or admin can delete this.", ephemeral=True)
                    return
                del password_configs[interaction.channel_id]
            elif not is_admin:
                await interaction.followup.send("No password generator found for this channel.", ephemeral=True)
                return

            await interaction.followup.send("Password generator deleted. This channel will be removed.", ephemeral=True)
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel):
                await asyncio.sleep(2)
                await channel.delete()
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class IPLookupPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="IP Lookup", style=discord.ButtonStyle.primary, custom_id="iplookup_create")
    async def create_iplookup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            suffix = random_string(4)
            channel_name = f"ip-lookup-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ip_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            embed = discord.Embed(
                title="IP Lookup / Geolocation",
                description="Click the button below to enter an IP address and get location info.",
                color=discord.Color.blurple(),
            )
            view = IPLookupConfigView()
            msg = await ip_channel.send(content=interaction.user.mention, embed=embed, view=view)
            await msg.pin()
            await interaction.followup.send(f"Your IP lookup channel has been created: {ip_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class IPInputModal(discord.ui.Modal, title="IP Lookup"):
    ip_input = discord.ui.TextInput(
        label="IP Address",
        placeholder="e.g. 8.8.8.8",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=45,
    )

    async def on_submit(self, interaction: discord.Interaction):
        ip = self.ip_input.value.strip()
        await interaction.response.defer(thinking=True)
        try:
            session = interaction.client.session
            async with session.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query") as resp:
                data = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Failed to look up IP: {e}", ephemeral=True)
            return

        if data.get("status") == "fail":
            await interaction.followup.send(f"Lookup failed: {data.get('message', 'Unknown error')}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"IP Lookup: {data.get('query', ip)}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Country", value=data.get("country", "N/A"), inline=True)
        embed.add_field(name="Region", value=data.get("regionName", "N/A"), inline=True)
        embed.add_field(name="City", value=data.get("city", "N/A"), inline=True)
        embed.add_field(name="Zip Code", value=data.get("zip", "N/A"), inline=True)
        embed.add_field(name="Latitude", value=str(data.get("lat", "N/A")), inline=True)
        embed.add_field(name="Longitude", value=str(data.get("lon", "N/A")), inline=True)
        embed.add_field(name="Timezone", value=data.get("timezone", "N/A"), inline=True)
        embed.add_field(name="ISP", value=data.get("isp", "N/A"), inline=True)
        embed.add_field(name="Organization", value=data.get("org", "N/A"), inline=True)
        embed.add_field(name="AS", value=data.get("as", "N/A"), inline=False)

        await interaction.followup.send(embed=embed)


class IPLookupConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter IP", style=discord.ButtonStyle.green, custom_id="iplookup_enter", row=0)
    async def enter_ip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IPInputModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="iplookup_delete", row=0)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("Channel deleted.", ephemeral=True)
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel):
            await asyncio.sleep(2)
            await channel.delete()


GAMEMODE_MAP = {
    "sword":    {"mctiers": "sword",    "pvptiers": "sword",    "subtiers": None},
    "pot":      {"mctiers": "pot",      "pvptiers": "pot",      "subtiers": None},
    "mace":     {"mctiers": "mace",     "pvptiers": "mace",     "subtiers": None},
    "axe":      {"mctiers": "axe",      "pvptiers": "axe",      "subtiers": None},
    "vanilla":  {"mctiers": "vanilla",  "pvptiers": None,       "subtiers": None},
    "uhc":      {"mctiers": "uhc",      "pvptiers": "uhc",      "subtiers": None},
    "nethop":   {"mctiers": "nethop",   "pvptiers": "neth_pot", "subtiers": None},
    "smp":      {"mctiers": "smp",      "pvptiers": "smp",      "subtiers": None},
    "crystal":  {"mctiers": None,       "pvptiers": "crystal",  "subtiers": None},
    "ogv":      {"mctiers": None,       "pvptiers": None,       "subtiers": "og_vanilla"},
    "diasmp":   {"mctiers": None,       "pvptiers": None,       "subtiers": "dia_smp"},
    "minecart": {"mctiers": None,       "pvptiers": None,       "subtiers": "minecart"},
    "bow":      {"mctiers": None,       "pvptiers": None,       "subtiers": "bow"},
    "manhunt":  {"mctiers": None,       "pvptiers": None,       "subtiers": "manhunt"},
    "elytra":   {"mctiers": None,       "pvptiers": None,       "subtiers": "elytra"},
    "trident":  {"mctiers": None,       "pvptiers": None,       "subtiers": "trident"},
    "debuff":   {"mctiers": None,       "pvptiers": None,       "subtiers": "debuff"},
    "bed":      {"mctiers": None,       "pvptiers": None,       "subtiers": "bed"},
    "creeper":  {"mctiers": None,       "pvptiers": None,       "subtiers": "creeper"},
    "speed":    {"mctiers": None,       "pvptiers": None,       "subtiers": "speed"},
}


async def resolve_username(name: str, session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(f"https://api.ashcon.app/mojang/v2/user/{name}") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("username", name)
    except Exception:
        pass
    return name


async def fetch_tier_data(name: str, gamemode: str, session: aiohttp.ClientSession) -> Dict:
    mapping = GAMEMODE_MAP.get(gamemode.lower())
    if not mapping:
        return {}

    results = {}

    if mapping["mctiers"]:
        try:
            url = f"https://mctiers.com/api/v2/profile/by-name/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    gm = mapping["mctiers"]
                    if gm in rankings:
                        r = rankings[gm]
                        results["mctiers"] = {
                            "tier": r.get("tier"),
                            "pos": r.get("pos"),
                            "peak_tier": r.get("peak_tier"),
                            "peak_pos": r.get("peak_pos"),
                            "attained": r.get("attained"),
                            "retired": r.get("retired", False),
                            "region": data.get("region"),
                            "points": data.get("points"),
                            "overall": data.get("overall"),
                        }
        except Exception:
            pass

    if mapping["pvptiers"]:
        try:
            url = f"https://pvptiers.com/api/search_profile/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    gm = mapping["pvptiers"]
                    if gm in rankings:
                        r = rankings[gm]
                        results["pvptiers"] = {
                            "tier": r.get("tier"),
                            "pos": r.get("pos"),
                            "peak_tier": r.get("peak_tier"),
                            "peak_pos": r.get("peak_pos"),
                            "attained": r.get("attained"),
                            "retired": r.get("retired", False),
                            "region": data.get("region"),
                            "points": data.get("points"),
                            "overall": data.get("overall"),
                        }
        except Exception:
            pass

    if mapping["subtiers"]:
        try:
            url = f"https://subtiers.net/api/search_profile/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    gm = mapping["subtiers"]
                    if gm in rankings:
                        r = rankings[gm]
                        results["subtiers"] = {
                            "tier": r.get("tier"),
                            "pos": r.get("pos"),
                            "peak_tier": r.get("peak_tier"),
                            "peak_pos": r.get("peak_pos"),
                            "attained": r.get("attained"),
                            "retired": r.get("retired", False),
                            "region": data.get("region"),
                            "points": data.get("points"),
                            "overall": data.get("overall"),
                        }
        except Exception:
            pass

    return results


def format_tier(tier, pos):
    if tier is None:
        return "N/A"
    return f"{'HT' if pos == 0 else 'LT'}{tier}"


def format_timestamp(ts):
    if not ts:
        return "N/A"
    return f"<t:{ts}:F>"


PLATFORM_GAMEMODES = {
    "mctiers": ["sword", "pot", "mace", "axe", "vanilla", "uhc", "nethop", "smp"],
    "pvptiers": ["sword", "axe", "pot", "neth_pot", "uhc", "smp", "crystal", "mace"],
    "subtiers": ["og_vanilla", "bow", "manhunt", "speed", "dia_smp", "elytra", "trident", "debuff", "bed", "minecart", "creeper"],
}

PLATFORM_GAMEMODE_DISPLAY = {
    "mctiers": {"sword": "Sword", "pot": "Pot", "mace": "Mace", "axe": "Axe", "vanilla": "Vanilla", "uhc": "UHC", "nethop": "NethOP", "smp": "SMP"},
    "pvptiers": {"sword": "Sword", "axe": "Axe", "pot": "Pot", "neth_pot": "Netherite Pot", "uhc": "UHC", "smp": "SMP", "crystal": "Crystal", "mace": "Mace"},
    "subtiers": {"og_vanilla": "OG Vanilla", "bow": "Bow", "manhunt": "Manhunt", "speed": "Speed", "dia_smp": "Diamond SMP", "elytra": "Elytra", "trident": "Trident", "debuff": "Debuff", "bed": "Bed", "minecart": "Minecart", "creeper": "Creeper"},
}


async def fetch_platform_data(name: str, platform: str, session: aiohttp.ClientSession) -> Dict:
    gamemodes = PLATFORM_GAMEMODES.get(platform, {})
    results = {}

    if platform == "mctiers":
        try:
            url = f"https://mctiers.com/api/v2/profile/by-name/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    results["_meta"] = {
                        "region": data.get("region"),
                        "points": data.get("points"),
                        "overall": data.get("overall"),
                    }
                    for gm in gamemodes:
                        if gm in rankings:
                            r = rankings[gm]
                            results[gm] = {
                                "tier": r.get("tier"),
                                "pos": r.get("pos"),
                                "peak_tier": r.get("peak_tier"),
                                "peak_pos": r.get("peak_pos"),
                                "attained": r.get("attained"),
                                "retired": r.get("retired", False),
                            }
        except Exception:
            pass

    elif platform == "pvptiers":
        try:
            url = f"https://pvptiers.com/api/search_profile/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    results["_meta"] = {
                        "region": data.get("region"),
                        "points": data.get("points"),
                        "overall": data.get("overall"),
                    }
                    for gm in gamemodes:
                        if gm in rankings:
                            r = rankings[gm]
                            results[gm] = {
                                "tier": r.get("tier"),
                                "pos": r.get("pos"),
                                "peak_tier": r.get("peak_tier"),
                                "peak_pos": r.get("peak_pos"),
                                "attained": r.get("attained"),
                                "retired": r.get("retired", False),
                            }
        except Exception:
            pass

    elif platform == "subtiers":
        try:
            url = f"https://subtiers.net/api/search_profile/{name}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rankings = data.get("rankings", {})
                    results["_meta"] = {
                        "region": data.get("region"),
                        "points": data.get("points"),
                        "overall": data.get("overall"),
                    }
                    for gm in gamemodes:
                        if gm in rankings:
                            r = rankings[gm]
                            results[gm] = {
                                "tier": r.get("tier"),
                                "pos": r.get("pos"),
                                "peak_tier": r.get("peak_tier"),
                                "peak_pos": r.get("peak_pos"),
                                "attained": r.get("attained"),
                                "retired": r.get("retired", False),
                            }
        except Exception:
            pass

    return results


class TierPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Tier Tracker", style=discord.ButtonStyle.blurple, custom_id="tiertracker_create")
    async def create_tiertracker(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return

            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            for uid in TIER_ALLOWED_USERS:
                member = guild.get_member(uid)
                if member:
                    overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            suffix = random_string(4)
            channel_name = f"tier-tracker-{suffix}".lower()
            tier_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            embed = discord.Embed(
                title="Tier Tracker",
                description=(
                    "Click **Add Account** to add accounts to track.\n"
                    "Click **List Accounts** to see tracked accounts.\n"
                    "Click **Remove Account** to remove accounts.\n\n"
                    "Click **Check Gamemode** to look up tiers across MCTiers, PvPTiers, and Subtiers."
                ),
                color=discord.Color.blurple(),
            )
            view = TierConfigView()
            msg = await tier_channel.send(content=interaction.user.mention, embed=embed, view=view)
            await msg.pin()
            await interaction.followup.send(f"Your tier tracker channel has been created: {tier_channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class TierGamemodeModal(discord.ui.Modal, title="Tier Lookup"):
    gamemode_input = discord.ui.TextInput(
        label="Gamemode or Platform",
        placeholder="e.g. sword, smp, mctiers, pvptiers, subtiers",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return

        gamemode = self.gamemode_input.value.strip().lower()

        is_platform = gamemode in PLATFORM_GAMEMODES
        is_gamemode = gamemode in GAMEMODE_MAP

        if not is_platform and not is_gamemode:
            valid_gm = ", ".join(sorted(GAMEMODE_MAP.keys()))
            valid_plat = ", ".join(sorted(PLATFORM_GAMEMODES.keys()))
            await interaction.response.send_message(
                f"Unknown input `{gamemode}`.\n"
                f"**Gamemodes:** {valid_gm}\n"
                f"**Platforms:** {valid_plat}",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=False, thinking=True)

        accounts = await load_tier_accounts()
        if not accounts:
            await interaction.followup.send("No accounts tracked. Click **Add Account** first.", ephemeral=True)
            return

        session = interaction.client.session
        account_names = get_tier_account_names(accounts)

        if is_platform:
            for account_name in account_names:
                results = await fetch_platform_data(account_name, gamemode, session)
                meta = results.pop("_meta", {})

                platform_label = gamemode.upper()
                embed = discord.Embed(
                    title=f"{account_name} — {platform_label}",
                    color=discord.Color.blurple(),
                )

                if meta:
                    embed.description = (
                        f"**Region:** {meta.get('region', 'N/A')} | "
                        f"**Points:** {meta.get('points', 'N/A')} | "
                        f"**Overall:** #{meta.get('overall', 'N/A')}"
                    )

                display_names = PLATFORM_GAMEMODE_DISPLAY.get(gamemode, {})
                found_any = False
                for gm, r in results.items():
                    found_any = True
                    display = display_names.get(gm, gm)
                    tier_str = format_tier(r.get("tier"), r.get("pos"))
                    peak_str = format_tier(r.get("peak_tier"), r.get("peak_pos"))
                    attained_str = format_timestamp(r.get("attained"))
                    retired = " *(Retired)*" if r.get("retired") else ""
                    embed.add_field(
                        name=display,
                        value=f"{tier_str}{retired} | Peak: {peak_str}\n<t:{r.get('attained', 0)}:d>" if r.get("attained") else f"{tier_str}{retired} | Peak: {peak_str}",
                        inline=True,
                    )

                if not found_any:
                    continue

                await interaction.followup.send(embed=embed)
        else:
            mapping = GAMEMODE_MAP[gamemode]
            for account_name in account_names:
                results = await fetch_tier_data(account_name, gamemode, session)

                embed = discord.Embed(
                    title=f"{account_name} — {gamemode.upper()}",
                    color=discord.Color.blurple(),
                )

                api_labels = {"mctiers": "MCTiers", "pvptiers": "PvPTiers", "subtiers": "Subtiers"}
                found_any = False
                for api_key in ["mctiers", "pvptiers", "subtiers"]:
                    if api_key in results:
                        found_any = True
                        r = results[api_key]
                        tier_str = format_tier(r.get("tier"), r.get("pos"))
                        peak_str = format_tier(r.get("peak_tier"), r.get("peak_pos"))
                        attained_str = format_timestamp(r.get("attained"))
                        retired = " (Retired)" if r.get("retired") else ""
                        embed.add_field(
                            name=api_labels[api_key],
                            value=(
                                f"**Tier:** {tier_str}{retired}\n"
                                f"**Peak:** {peak_str}\n"
                                f"**Attained:** {attained_str}\n"
                                f"**Region:** {r.get('region', 'N/A')}\n"
                                f"**Points:** {r.get('points', 'N/A')} | **Overall:** #{r.get('overall', 'N/A')}"
                            ),
                            inline=True,
                        )

                if not found_any:
                    continue

                await interaction.followup.send(embed=embed)


class TierConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Check Gamemode", style=discord.ButtonStyle.green, custom_id="tier_check", row=0)
    async def check_gamemode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.send_modal(TierGamemodeModal())

    @discord.ui.button(label="Add Account", style=discord.ButtonStyle.blurple, custom_id="tier_add", row=1)
    async def add_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.send_modal(AccountAddModal())

    @discord.ui.button(label="Remove Account", style=discord.ButtonStyle.red, custom_id="tier_remove", row=1)
    async def remove_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.send_modal(AccountRemoveModal())

    @discord.ui.button(label="List Accounts", style=discord.ButtonStyle.grey, custom_id="tier_list", row=1)
    async def list_accounts(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        accounts = await load_tier_accounts()
        if not accounts:
            await interaction.followup.send("No accounts tracked.", ephemeral=True)
            return
        embed = discord.Embed(title="Tracked Accounts", color=discord.Color.blurple())
        lines = []
        for a in accounts:
            name = a["name"] if isinstance(a, dict) else a
            added_by_id = a.get("added_by", 0) if isinstance(a, dict) else 0
            if added_by_id:
                member = interaction.guild.get_member(added_by_id) if interaction.guild else None
                added_str = member.display_name if member else f"<@{added_by_id}>"
                lines.append(f"• **{name}** — added by {added_str}")
            else:
                lines.append(f"• **{name}**")
        embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="tier_delete", row=2)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("Channel deleted.", ephemeral=True)
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel):
            await asyncio.sleep(2)
            await channel.delete()


# ─── Password Breach Check (HaveIBeenPwned k-Anonymity) ─────────────────────

async def check_password_breach(password: str) -> int:
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    session = aiohttp.ClientSession()
    try:
        async with session.get(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={"User-Agent": "DiscordBot-TierTracker/1.0"},
        ) as resp:
            if resp.status != 200:
                return -1
            text = await resp.text()
            for line in text.splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix.strip() == suffix:
                    return int(count.strip())
            return 0
    except Exception:
        return -1
    finally:
        await session.close()


class PasswordBreachPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Password Breach Check", style=discord.ButtonStyle.primary, custom_id="pwbreach_create")
    async def create_pwbreach(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"password-breach-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Password Breach Check",
                description="Click the button below to check if a password has been leaked in data breaches.\nUses the HaveIBeenPwned k-Anonymity API — your full password is never sent.",
                color=discord.Color.red(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=PasswordBreachConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your password breach channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class PasswordBreachModal(discord.ui.Modal, title="Password Breach Check"):
    password_input = discord.ui.TextInput(
        label="Password to check",
        placeholder="Enter a password to check for breaches",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        password = self.password_input.value
        await interaction.response.defer(thinking=True)
        count = await check_password_breach(password)
        if count == -1:
            await interaction.followup.send("Failed to check the breach database. Try again later.", ephemeral=True)
            return
        if count == 0:
            embed = discord.Embed(
                title="Password Breach Check: Safe",
                description="This password was **not found** in any known data breaches.",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Note: This doesn't guarantee the password is secure — just that it hasn't appeared in known breaches.")
        else:
            embed = discord.Embed(
                title="Password Breach Check: PWNED",
                description=f"This password has been seen **{count:,} times** in data breaches!",
                color=discord.Color.red(),
            )
            embed.set_footer(text="Change this password immediately if you use it anywhere.")
        await interaction.followup.send(embed=embed)


class PasswordBreachConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Check Password", style=discord.ButtonStyle.red, custom_id="pwbreach_check", row=0)
    async def check_password(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PasswordBreachModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="pwbreach_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[PWBREACH] Delete error: {e}")


# ─── Calculator ───────────────────────────────────────────────────────────────

class CalculatorPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Calculator", style=discord.ButtonStyle.primary, custom_id="calc_create")
    async def create_calc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"calculator-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Calculator",
                description="Click the button below to calculate a math expression.\nSupported: `+`, `-`, `*`, `/`, `**` (power), `//` (floor div), `%` (mod), parentheses.",
                color=discord.Color.blue(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=CalculatorConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your calculator channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class CalculatorModal(discord.ui.Modal, title="Calculator"):
    expression_input = discord.ui.TextInput(
        label="Math Expression",
        placeholder="e.g. (2 + 3) * 4 / 2",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        expr = self.expression_input.value.strip()
        import ast
        import operator as op
        safe_ops = {
            ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
            ast.Div: op.truediv, ast.FloorDiv: op.floordiv, ast.Pow: op.pow,
            ast.Mod: op.mod, ast.USub: op.neg, ast.UAdd: op.pos,
        }
        def safe_eval(node):
            if isinstance(node, ast.Expression):
                return safe_eval(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in safe_ops:
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                return safe_ops[type(node.op)](left, right)
            if isinstance(node, ast.UnaryOp) and type(node.op) in safe_ops:
                return safe_ops[type(node.op)](safe_eval(node.operand))
            raise ValueError("Unsupported expression")
        try:
            tree = ast.parse(expr, mode="eval")
            result = safe_eval(tree)
            if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
                result = int(result)
            embed = discord.Embed(
                title="Calculator Result",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Expression", value=f"`{expr}`", inline=False)
            embed.add_field(name="Result", value=f"`{result}`", inline=False)
            await interaction.response.send_message(embed=embed)
        except ZeroDivisionError:
            await interaction.response.send_message("Error: Division by zero.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Invalid expression. Use numbers and operators (+, -, *, /, **, //, %).", ephemeral=True)


class CalculatorConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Calculate", style=discord.ButtonStyle.green, custom_id="calc_calc", row=0)
    async def calculate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalculatorModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="calc_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[CALC] Delete error: {e}")


# ─── Unit Converter ──────────────────────────────────────────────────────────

UNIT_CONVERSIONS = {
    "m_to_ft": 3.28084, "ft_to_m": 0.3048,
    "km_to_mi": 0.621371, "mi_to_km": 1.60934,
    "cm_to_in": 0.393701, "in_to_cm": 2.54,
    "kg_to_lb": 2.20462, "lb_to_kg": 0.453592,
    "g_to_oz": 0.035274, "oz_to_g": 28.3495,
    "c_to_f": lambda x: x * 9 / 5 + 32,
    "f_to_c": lambda x: (x - 32) * 5 / 9,
    "c_to_k": lambda x: x + 273.15,
    "k_to_c": lambda x: x - 273.15,
    "f_to_k": lambda x: (x - 32) * 5 / 9 + 273.15,
    "k_to_f": lambda x: (x - 273.15) * 9 / 5 + 32,
}


class UnitConverterPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Unit Converter", style=discord.ButtonStyle.primary, custom_id="unitconv_create")
    async def create_unitconv(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"unit-converter-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Unit Converter",
                description=(
                    "Click the button below to convert units.\n\n"
                    "**Supported conversions:**\n"
                    "Length: `m↔ft`, `km↔mi`, `cm↔in`\n"
                    "Weight: `kg↔lb`, `g↔oz`\n"
                    "Temperature: `°C↔°F↔K`"
                ),
                color=discord.Color.orange(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=UnitConverterConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your unit converter channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class UnitConverterModal(discord.ui.Modal, title="Unit Converter"):
    value_input = discord.ui.TextInput(
        label="Value",
        placeholder="e.g. 100",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=20,
    )
    conversion_input = discord.ui.TextInput(
        label="Conversion (from_to)",
        placeholder="e.g. m_to_ft, kg_to_lb, c_to_f",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = float(self.value_input.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid number.", ephemeral=True)
            return
        conv_key = self.conversion_input.value.strip().lower()
        conv_fn = UNIT_CONVERSIONS.get(conv_key)
        if conv_fn is None:
            await interaction.response.send_message(
                f"Unknown conversion `{conv_key}`.\nUse: `m_to_ft`, `ft_to_m`, `km_to_mi`, `mi_to_km`, `cm_to_in`, `in_to_cm`, `kg_to_lb`, `lb_to_kg`, `g_to_oz`, `oz_to_g`, `c_to_f`, `f_to_c`, `c_to_k`, `k_to_c`, `f_to_k`, `k_to_f`",
                ephemeral=True,
            )
            return
        result = conv_fn(value) if callable(conv_fn) else value * conv_fn
        if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
            result = int(result)
        parts = conv_key.split("_to_")
        embed = discord.Embed(title="Unit Conversion", color=discord.Color.orange())
        embed.add_field(name="Input", value=f"`{value} {parts[0]}`", inline=True)
        embed.add_field(name="Result", value=f"`{result} {parts[1]}`", inline=True)
        await interaction.response.send_message(embed=embed)


class UnitConverterConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Convert", style=discord.ButtonStyle.green, custom_id="unitconv_convert", row=0)
    async def convert(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnitConverterModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="unitconv_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[UNITCONV] Delete error: {e}")


# ─── Currency Converter ──────────────────────────────────────────────────────

class CurrencyConverterPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Currency Converter", style=discord.ButtonStyle.primary, custom_id="currconv_create")
    async def create_currconv(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"currency-converter-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Currency Converter",
                description="Click the button below to convert currencies.\nUses free exchange rates API (exchangerate-api.com).",
                color=discord.Color.gold(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=CurrencyConverterConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your currency converter channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class CurrencyConverterModal(discord.ui.Modal, title="Currency Converter"):
    amount_input = discord.ui.TextInput(
        label="Amount",
        placeholder="e.g. 100",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=20,
    )
    from_input = discord.ui.TextInput(
        label="From Currency (3-letter code)",
        placeholder="e.g. USD",
        style=discord.TextStyle.short,
        min_length=3,
        max_length=3,
    )
    to_input = discord.ui.TextInput(
        label="To Currency (3-letter code)",
        placeholder="e.g. EUR",
        style=discord.TextStyle.short,
        min_length=3,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount_input.value.strip())
        except ValueError:
            await interaction.response.send_message("Invalid amount.", ephemeral=True)
            return
        from_cur = self.from_input.value.strip().upper()
        to_cur = self.to_input.value.strip().upper()
        await interaction.response.defer(thinking=True)
        try:
            session = interaction.client.session
            async with session.get(f"https://api.exchangerate-api.com/v4/latest/{from_cur}") as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"API error. Check currency code `{from_cur}`.", ephemeral=True)
                    return
                data = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Failed to fetch rates: {e}", ephemeral=True)
            return
        rate = data.get("rates", {}).get(to_cur)
        if rate is None:
            await interaction.followup.send(f"Currency `{to_cur}` not found.", ephemeral=True)
            return
        result = amount * rate
        embed = discord.Embed(title="Currency Conversion", color=discord.Color.gold())
        embed.add_field(name="From", value=f"`{amount:,.2f} {from_cur}`", inline=True)
        embed.add_field(name="To", value=f"`{result:,.2f} {to_cur}`", inline=True)
        embed.add_field(name="Rate", value=f"1 {from_cur} = {rate} {to_cur}", inline=False)
        embed.set_footer(text="Rates from exchangerate-api.com")
        await interaction.followup.send(embed=embed)


class CurrencyConverterConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Convert", style=discord.ButtonStyle.green, custom_id="currconv_convert", row=0)
    async def convert(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CurrencyConverterModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="currconv_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[CURRCONV] Delete error: {e}")


# ─── Discord User Info ───────────────────────────────────────────────────────

class UserInfoPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="User Info", style=discord.ButtonStyle.primary, custom_id="userinfo_create")
    async def create_userinfo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"user-info-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Discord User Info",
                description="Click the button below to look up a Discord user's profile info (avatar, banner, roles, etc.).",
                color=discord.Color.purple(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=UserInfoConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your user info channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class UserInfoModal(discord.ui.Modal, title="User Info Lookup"):
    user_input = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="e.g. 763815168894828576 or @user",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_input.value.strip()
        user_id = None
        match = re.search(r'(\d{17,20})', raw)
        if match:
            user_id = int(match.group(1))
        if not user_id:
            await interaction.response.send_message("Invalid user ID or mention.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        try:
            user = await interaction.client.fetch_user(user_id)
        except discord.NotFound:
            await interaction.followup.send(f"User with ID `{user_id}` not found.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Failed to fetch user: {e}", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"User Info: {user.name}",
            color=discord.Color.purple(),
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Username", value=user.name, inline=True)
        embed.add_field(name="Discriminator", value=user.discriminator, inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(user.created_at.timestamp())}:F>\n(<t:{int(user.created_at.timestamp())}:R>)", inline=False)

        if hasattr(user, "banner") and user.banner:
            embed.set_image(url=user.banner.url)
            embed.add_field(name="Banner", value="Shown above", inline=False)

        if hasattr(user, "accent_color") and user.accent_color:
            embed.add_field(name="Accent Color", value=str(user.accent_color), inline=True)

        member = interaction.guild.get_member(user_id) if interaction.guild else None
        if member:
            if member.nick:
                embed.add_field(name="Nickname", value=member.nick, inline=True)
            embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:F>\n(<t:{int(member.joined_at.timestamp())}:R>)", inline=False) if member.joined_at else None
            roles = [r.mention for r in member.roles[1:] if r.name != "@everyone"]
            if roles:
                embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles[:20]) + ("..." if len(roles) > 20 else ""), inline=False)

        await interaction.followup.send(embed=embed)


class UserInfoConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Look Up User", style=discord.ButtonStyle.green, custom_id="userinfo_lookup", row=0)
    async def lookup_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UserInfoModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="userinfo_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[USERINFO] Delete error: {e}")


# ─── BTC/ETH Price ──────────────────────────────────────────────────────────

class CryptoPricePanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="BTC/ETH Price", style=discord.ButtonStyle.primary, custom_id="cryptoprice_create")
    async def create_cryptoprice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"crypto-price-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="BTC/ETH Price",
                description="Click a button below to check the current price of Bitcoin or Ethereum.",
                color=discord.Color.orange(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=CryptoPriceConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your crypto price channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


async def fetch_crypto_price(coin_id: str) -> discord.Embed:
    session = _bot_instance.session
    async with session.get(
        f"https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true", "include_market_cap": "true"},
    ) as resp:
        data = await resp.json()
    coin = data.get(coin_id, {})
    price = coin.get("usd", 0)
    change = coin.get("usd_24h_change", 0)
    mcap = coin.get("usd_market_cap", 0)
    name = coin_id.replace("-", " ").title()
    color = discord.Color.green() if change >= 0 else discord.Color.red()
    embed = discord.Embed(title=f"{name} Price", color=color)
    embed.add_field(name="Price (USD)", value=f"${price:,.2f}", inline=True)
    embed.add_field(name="24h Change", value=f"{change:+.2f}%", inline=True)
    embed.add_field(name="Market Cap", value=f"${mcap:,.0f}", inline=True)
    embed.set_footer(text="Data from CoinGecko")
    return embed


class CryptoPriceConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Bitcoin Price", style=discord.ButtonStyle.green, custom_id="cryptoprice_btc", row=0)
    async def btc_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        embed = await fetch_crypto_price("bitcoin")
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Ethereum Price", style=discord.ButtonStyle.green, custom_id="cryptoprice_eth", row=0)
    async def eth_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        embed = await fetch_crypto_price("ethereum")
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="cryptoprice_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[CRYPTOPRICE] Delete error: {e}")


# ─── Crypto Lookup ──────────────────────────────────────────────────────────

class CryptoLookupPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Crypto Lookup", style=discord.ButtonStyle.primary, custom_id="cryptolookup_create")
    async def create_cryptolookup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"crypto-lookup-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Crypto Lookup",
                description="Click the button below to look up any cryptocurrency by name (e.g. solana, dogecoin, cardano).",
                color=discord.Color.orange(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=CryptoLookupConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your crypto lookup channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class CryptoLookupModal(discord.ui.Modal, title="Crypto Lookup"):
    coin_input = discord.ui.TextInput(
        label="Coin Name",
        placeholder="e.g. solana, dogecoin, cardano",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.coin_input.value.strip().lower()
        await interaction.response.defer(thinking=True)
        try:
            session = interaction.client.session
            headers = {"User-Agent": "Mozilla/5.0 (DiscordBot/CryptoLookup/1.0)"}
            async with session.get(f"https://api.coingecko.com/api/v3/search?query={query}", headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send("API error. Try again later.", ephemeral=True)
                    return
                search_data = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Failed to search: {e}", ephemeral=True)
            return

        coins = search_data.get("coins", [])
        if not coins:
            await interaction.followup.send(f"No coins found for `{query}`.", ephemeral=True)
            return

        coin = coins[0]
        coin_id = coin.get("id")
        coin_name = coin.get("name", "Unknown")
        symbol = coin.get("symbol", "N/A")
        market_cap_rank = coin.get("market_cap_rank", "N/A")

        try:
            headers = {"User-Agent": "Mozilla/5.0 (DiscordBot/CryptoLookup/1.0)"}
            for attempt in range(3):
                async with session.get(
                    f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                    params={"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false", "sparkline": "false"},
                    headers=headers,
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(3)
                        continue
                    if resp.status != 200:
                        price, change, mcap = 0, 0, 0
                        break
                    detail = await resp.json()
                    market = detail.get("market_data", {})
                    price = market.get("current_price", {}).get("usd", 0)
                    change = market.get("price_change_percentage_24h", 0) or 0
                    mcap = market.get("market_cap", {}).get("usd", 0) or 0
                    break
            else:
                price, change, mcap = 0, 0, 0
        except Exception:
            price, change, mcap = 0, 0, 0

        color = discord.Color.green() if change >= 0 else discord.Color.red()
        embed = discord.Embed(title=f"{coin_name} ({symbol.upper()})", color=color)
        embed.add_field(name="Price (USD)", value=f"${price:,.6f}" if price < 1 else f"${price:,.2f}", inline=True)
        embed.add_field(name="24h Change", value=f"{change:+.2f}%", inline=True)
        embed.add_field(name="Market Cap Rank", value=f"#{market_cap_rank}" if market_cap_rank else "N/A", inline=True)
        embed.add_field(name="Market Cap", value=f"${mcap:,.0f}" if mcap else "N/A", inline=True)
        embed.set_footer(text="Data from CoinGecko")
        await interaction.followup.send(embed=embed)


class CryptoLookupConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lookup Coin", style=discord.ButtonStyle.green, custom_id="cryptolookup_lookup", row=0)
    async def lookup_coin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CryptoLookupModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="cryptolookup_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[CRYPTOLOOKUP] Delete error: {e}")


# ─── Language Translator ─────────────────────────────────────────────────────

class TranslatorPanelView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Translator", style=discord.ButtonStyle.primary, custom_id="translator_create")
    async def create_translator(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Guild not found.", ephemeral=True)
                return
            category = guild.get_channel(NEW_FEATURES_CATEGORY_ID)
            if not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send("Category not found.", ephemeral=True)
                return
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            admin_member = guild.get_member(ADMIN_ID)
            if admin_member:
                overwrites[admin_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            lock_role = guild.get_role(1524549659035701288)
            if lock_role:
                overwrites[lock_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            suffix = random_string(4)
            channel_name = f"translator-{interaction.user.name}-{suffix}".lower().replace(" ", "-")
            ch = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            embed = discord.Embed(
                title="Language Translator",
                description=(
                    "Click the button below to translate text between languages.\n\n"
                    "**Just type any language name:** english, spanish, french, german, japanese, arabic, russian, korean, chinese, and many more.\n"
                    "The bot auto-detects the source language."
                ),
                color=discord.Color.dark_teal(),
            )
            msg = await ch.send(content=interaction.user.mention, embed=embed, view=TranslatorConfigView())
            await msg.pin()
            await interaction.followup.send(f"Your translator channel has been created: {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)


class TranslatorModal(discord.ui.Modal, title="Translate"):
    text_input = discord.ui.TextInput(
        label="Text to translate",
        placeholder="Enter text here...",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=1000,
    )
    target_input = discord.ui.TextInput(
        label="Translate to (any language name)",
        placeholder="e.g. english, spanish, german, french, japanese, arabic...",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        text = self.text_input.value.strip()
        target_raw = self.target_input.value.strip().lower()

        LANG_NAMES = {
            "english": "en", "spanish": "es", "french": "fr", "german": "de", "italian": "it",
            "portuguese": "pt", "dutch": "nl", "russian": "ru", "japanese": "ja", "korean": "ko",
            "chinese": "zh", "arabic": "ar", "hindi": "hi", "turkish": "tr", "polish": "pl",
            "swedish": "sv", "danish": "da", "norwegian": "no", "finnish": "fi", "greek": "el",
            "czech": "cs", "romanian": "ro", "hungarian": "hu", "thai": "th", "vietnamese": "vi",
            "indonesian": "id", "malay": "ms", "ukrainian": "uk", "hebrew": "he", "persian": "fa",
            "urdu": "ur", "bengali": "bn", "tamil": "ta", "telugu": "te", "marathi": "mr",
            "gujarati": "gu", "kannada": "kn", "malayalam": "ml", "punjabi": "pa", "swahili": "sw",
            "tagalog": "tl", "latin": "la", "esperanto": "eo", "estonian": "et", "latvian": "lv",
            "lithuanian": "lt", "slovenian": "sl", "slovak": "sk", "croatian": "hr", "serbian": "sr",
            "bulgarian": "bg", "catalan": "ca", "basque": "eu", "galician": "gl", "afrikaans": "af",
            "albanian": "sq", "armenian": "hy", "georgian": "ka", "kazakh": "kk", "uzbek": "uz",
            "azerbaijani": "az", "nepali": "ne", "burmese": "my", "khmer": "km",
            "lao": "lo", "mongolian": "mn", "somali": "so", "amharic": "am",
            "yoruba": "yo", "igbo": "ig", "hausa": "ha", "zulu": "zu", "xhosa": "xh",
            "maori": "mi", "welsh": "cy", "irish": "ga", "icelandic": "is", "maltese": "mt",
            "belarusian": "be", "macedonian": "mk", "bosnian": "bs", "kurdish": "ku", "pashto": "ps",
            "javanese": "jv", "sundanese": "su", "cebuano": "ce",
        }

        target_code = LANG_NAMES.get(target_raw, target_raw)

        await interaction.response.defer(thinking=True)
        try:
            session = interaction.client.session
            async with session.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": target_code, "dt": "t", "q": text},
            ) as resp:
                if resp.status != 200:
                    await interaction.followup.send("Translation API error.", ephemeral=True)
                    return
                data = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Translation failed: {e}", ephemeral=True)
            return

        translated = "".join(part[0] for part in data[0] if part[0])
        detected_lang = data[2] if len(data) > 2 else "unknown"
        if not translated:
            await interaction.followup.send("Translation returned empty.", ephemeral=True)
            return

        embed = discord.Embed(title="Translation", color=discord.Color.dark_teal())
        embed.add_field(name=f"Detected: {detected_lang.upper()} → {target_raw.title()}", value=f"**Original:**\n{text}\n\n**Translated:**\n{translated}", inline=False)
        embed.set_footer(text="Translated via Google Translate")
        await interaction.followup.send(embed=embed)


class TranslatorConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Translate", style=discord.ButtonStyle.green, custom_id="translator_translate", row=0)
    async def translate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TranslatorModal())

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, custom_id="translator_delete", row=1)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await interaction.followup.send("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            print(f"[TRANSLATOR] Delete error: {e}")


@app_commands.command(name="inbox", description="Fetch your temp mail inbox")
async def inbox_command(interaction: discord.Interaction):
    bot: Bot = interaction.client
    account = bot.channel_accounts.get(interaction.channel_id)
    if not account:
        await interaction.response.send_message("This command must be used inside your temp mail channel.", ephemeral=True)
        return
    owner_id = account.get("owner_id")
    if interaction.user.id != owner_id and interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You don't have access to this temp mail channel.", ephemeral=True)
        return
    try:
        data = await bot.mailtm.list_messages(account["token"])
    except Exception as e:
        await interaction.response.send_message(f"Failed to fetch inbox: {e}", ephemeral=True)
        return
    messages = data.get("hydra:member", [])
    if not messages:
        await interaction.response.send_message("Your inbox is empty.", ephemeral=True)
        return
    embed = discord.Embed(title="Inbox", color=discord.Color.blurple())
    for msg in messages[:10]:
        sender = msg.get("from", {}).get("address", "Unknown")
        subject = msg.get("subject", "(No subject)")
        preview = msg.get("intro", "No preview")
        message_id = msg.get("id", "?")
        embed.add_field(name=f"{subject} (ID: {message_id})", value=f"From: {sender}\n{preview}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="delete", description="Delete messages from your temp inbox")
@app_commands.describe(message_id="Message ID to delete or 'all' to delete everything")
async def delete_command(interaction: discord.Interaction, message_id: Optional[str] = None):
    bot: Bot = interaction.client
    account = bot.channel_accounts.get(interaction.channel_id)
    if not account:
        await interaction.response.send_message("This command must be used inside your temp mail channel.", ephemeral=True)
        return
    owner_id = account.get("owner_id")
    if interaction.user.id != owner_id and interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You don't have access to this temp mail channel.", ephemeral=True)
        return
    try:
        if message_id and message_id.lower() == "all":
            data = await bot.mailtm.list_messages(account["token"])
            messages = data.get("hydra:member", [])
            if not messages:
                await interaction.response.send_message("Inbox is already empty.", ephemeral=True)
                return
            for msg in messages:
                await bot.mailtm.delete_message(account["token"], msg["id"])
            await interaction.response.send_message("All messages deleted.", ephemeral=True)
            return
        if not message_id:
            await interaction.response.send_message("Provide a message ID or 'all'.", ephemeral=True)
            return
        await bot.mailtm.delete_message(account["token"], message_id)
        await interaction.response.send_message(f"Deleted message {message_id}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to delete message: {e}", ephemeral=True)


@app_commands.command(name="add", description="Add a user to this file share channel")
@app_commands.describe(user="User to add")
async def add_command(interaction: discord.Interaction, user: discord.Member):
    owner_id = get_channel_owner(interaction.channel_id)
    if not owner_id:
        await interaction.response.send_message("This command only works in file share channels.", ephemeral=True)
        return
    if interaction.user.id != owner_id and interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("Only the channel owner can add users.", ephemeral=True)
        return
    await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
    await interaction.response.send_message(f"Added {user.mention} to this channel.", ephemeral=True)


@app_commands.command(name="remove", description="Remove a user from this file share channel")
@app_commands.describe(user="User to remove")
async def remove_command(interaction: discord.Interaction, user: discord.Member):
    owner_id = get_channel_owner(interaction.channel_id)
    if not owner_id:
        await interaction.response.send_message("This command only works in file share channels.", ephemeral=True)
        return
    if interaction.user.id != owner_id and interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("Only the channel owner can remove users.", ephemeral=True)
        return
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(f"Removed {user.mention} from this channel.", ephemeral=True)


INVITE_LINK = "https://discord.gg/thSzybJDz2"
STAFF_ROLE_ID = 1524549659035701288
ADMIN_IDS = [763815168894828576, 529014657537540096]

active_giveaways = {}


def has_staff_role():
    async def predicate(ctx):
        role = ctx.guild.get_role(STAFF_ROLE_ID)
        if role and role in ctx.author.roles:
            return True
        await ctx.send("You don't have permission to use this command.", delete_after=5)
        return False
    return commands.check(predicate)


@commands.command(name="lock")
@has_staff_role()
async def lock_command(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked. Members can view but not type.")


@commands.command(name="unlock")
@has_staff_role()
async def unlock_command(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")


auto_role_id = None


@commands.command(name="role")
@has_staff_role()
async def role_command(ctx, role: discord.Role):
    await ctx.send(f"Assigning {role.mention} to all members...")
    count = 0
    failed = 0
    for member in ctx.guild.members:
        if member.bot:
            continue
        try:
            await member.add_roles(role)
            count += 1
        except discord.Forbidden:
            failed += 1
    await ctx.send(f"Done. Assigned to **{count}** members. Failed: **{failed}**.")


@commands.command(name="autorole")
@has_staff_role()
async def autorole_command(ctx, role: discord.Role):
    global auto_role_id
    auto_role_id = role.id
    await ctx.send(f"Auto-role set to {role.mention}. New members will receive this role on join.")


async def on_member_join(member):
    if auto_role_id and not member.bot:
        role = member.guild.get_role(auto_role_id)
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass


def parse_duration(duration_str):
    """Parse duration like 10m, 2h, 1d into timedelta"""
    import re
    match = re.match(r'^(\d+)([smhd])$', duration_str.lower())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    return None


@commands.command(name="purge")
@has_staff_role()
async def purge_command(ctx, count: int):
    if count < 1 or count > 100:
        await ctx.send("Pick a number between 1 and 100.", delete_after=5)
        return
    deleted = await ctx.channel.purge(limit=count + 1)
    msg = await ctx.send(f"Purged **{len(deleted) - 1}** messages.")
    await asyncio.sleep(3)
    await msg.delete()


@commands.command(name="ban")
@has_staff_role()
async def ban_command(ctx, member: discord.Member = None, duration: str = None, *, reason: str = None):
    if not member:
        await ctx.send("Usage: `?ban @user [duration] [reason]`", delete_after=5)
        return
    if member.id == ctx.author.id:
        await ctx.send("You can't ban yourself.", delete_after=5)
        return
    if member.guild_permissions.manage_messages and ctx.author.id not in ADMIN_IDS:
        await ctx.send("You can't ban staff.", delete_after=5)
        return
    if ctx.author.id not in ADMIN_IDS and not reason:
        await ctx.send("You must provide a reason. Usage: `?ban @user [duration] reason`", delete_after=5)
        return
    reason = reason or "No reason provided"
    dm_embed = discord.Embed(
        title="You have been banned",
        description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}\n**Duration:** {duration or 'Permanent'}",
        color=discord.Color.red(),
    )
    dm_embed.add_field(name="Invite", value=INVITE_LINK, inline=False)
    if duration:
        td = parse_duration(duration)
        if td:
            until = discord.utils.utcnow() + td
            dm_embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>")
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    if duration:
        td = parse_duration(duration)
        if td:
            await member.ban(reason=f"Banned by {ctx.author} | {reason} | Duration: {duration}")
            await ctx.send(f"🔨 **{member}** banned for **{duration}**. Reason: {reason}")
            await asyncio.sleep(td.total_seconds())
            try:
                await ctx.guild.unban(member, reason="Ban duration expired")
                try:
                    await member.send(embed=discord.Embed(
                        title="Your ban has expired",
                        description=f"**Server:** {ctx.guild.name}\nYour punishment has finished. You may rejoin.",
                        color=discord.Color.green(),
                    ))
                    await member.send(embed=discord.Embed(
                        description=f"Invite: {INVITE_LINK}",
                        color=discord.Color.green(),
                    ))
                except discord.Forbidden:
                    pass
                await ctx.send(f"🔓 **{member}** has been unbanned (ban expired).")
            except Exception:
                pass
            return
    await member.ban(reason=f"Banned by {ctx.author} | {reason}")
    await ctx.send(f"🔨 **{member}** banned permanently. Reason: {reason}")


@commands.command(name="kick")
@has_staff_role()
async def kick_command(ctx, member: discord.Member = None, *, reason: str = None):
    if not member:
        await ctx.send("Usage: `?kick @user [reason]`", delete_after=5)
        return
    if member.id == ctx.author.id:
        await ctx.send("You can't kick yourself.", delete_after=5)
        return
    if member.guild_permissions.manage_messages and ctx.author.id not in ADMIN_IDS:
        await ctx.send("You can't kick staff.", delete_after=5)
        return
    if ctx.author.id not in ADMIN_IDS and not reason:
        await ctx.send("You must provide a reason. Usage: `?kick @user reason`", delete_after=5)
        return
    reason = reason or "No reason provided"
    try:
        await member.send(embed=discord.Embed(
            title="You have been kicked",
            description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}",
            color=discord.Color.orange(),
        ))
        await member.send(embed=discord.Embed(
            description=f"Rejoin here: {INVITE_LINK}",
            color=discord.Color.orange(),
        ))
    except discord.Forbidden:
        pass
    await member.kick(reason=f"Kicked by {ctx.author} | {reason}")
    await ctx.send(f"👢 **{member}** has been kicked. Reason: {reason}")


@commands.command(name="mute")
@has_staff_role()
async def mute_command(ctx, member: discord.Member = None, duration: str = None, *, reason: str = None):
    if not member or not duration:
        await ctx.send("Usage: `?mute @user <duration> [reason]`\nDuration: `10m`, `2h`, `1d`", delete_after=5)
        return
    if member.id == ctx.author.id:
        await ctx.send("You can't mute yourself.", delete_after=5)
        return
    if member.guild_permissions.manage_messages and ctx.author.id not in ADMIN_IDS:
        await ctx.send("You can't mute staff.", delete_after=5)
        return
    if ctx.author.id not in ADMIN_IDS and not reason:
        await ctx.send("You must provide a reason. Usage: `?mute @user <duration> reason`", delete_after=5)
        return
    td = parse_duration(duration)
    if not td:
        await ctx.send("Invalid duration. Use: `10m`, `2h`, `1d`", delete_after=5)
        return
    reason = reason or "No reason provided"
    until = discord.utils.utcnow() + td
    try:
        await member.send(embed=discord.Embed(
            title="You have been muted",
            description=f"**Server:** {ctx.guild.name}\n**Duration:** {duration}\n**Reason:** {reason}\n**Expires:** <t:{int(until.timestamp())}:R>",
            color=discord.Color.greyple(),
        ))
        await member.send(embed=discord.Embed(
            description=f"Invite: {INVITE_LINK}",
            color=discord.Color.greyple(),
        ))
    except discord.Forbidden:
        pass
    await member.timeout(td, reason=f"Muted by {ctx.author} | {reason} | Duration: {duration}")
    await ctx.send(f"🔇 **{member}** muted for **{duration}**. Reason: {reason}")


@commands.command(name="unmute")
@has_staff_role()
async def unmute_command(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("Usage: `?unmute @user`", delete_after=5)
        return
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role, reason=f"Unmuted by {ctx.author}")
    if member.is_timed_out():
        await member.timeout(None, reason=f"Unmuted by {ctx.author}")
    try:
        await member.send(embed=discord.Embed(
            title="You have been unmuted",
            description=f"**Server:** {ctx.guild.name}\nInvite: {INVITE_LINK}",
            color=discord.Color.green(),
        ))
    except discord.Forbidden:
        pass
    await ctx.send(f"🔊 **{member}** has been unmuted.")


@commands.command(name="unban")
@has_staff_role()
async def unban_command(ctx, user_id: int = None):
    if not user_id:
        await ctx.send("Usage: `?unban <userid>`", delete_after=5)
        return
    try:
        user = await ctx.guild.fetch_ban(discord.Object(user_id))
    except discord.NotFound:
        await ctx.send("That user isn't banned.", delete_after=5)
        return
    await ctx.guild.unban(user.user, reason=f"Unbanned by {ctx.author}")
    try:
        await user.user.send(embed=discord.Embed(
            title="You have been unbanned",
            description=f"**Server:** {ctx.guild.name}\nInvite: {INVITE_LINK}",
            color=discord.Color.green(),
        ))
    except discord.Forbidden:
        pass
    await ctx.send(f"🔓 **{user.user}** has been unbanned.")


@app_commands.command(name="giveaway", description="Create a giveaway")
@app_commands.describe(winners="Number of winners", duration="Duration (e.g. 30s, 10m, 2h, 1d)", title="Giveaway title")
@app_commands.default_permissions(manage_messages=True)
async def giveaway_command(interaction: discord.Interaction, winners: int = 1, duration: str = None, title: str = "Giveaway"):
    role = interaction.guild.get_role(STAFF_ROLE_ID)
    if not role or role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    if not duration:
        await interaction.response.send_message("Usage: `/giveaway <winners> <duration> <title>`\nTime examples: `30s`, `10m`, `2h`, `1d`", ephemeral=True)
        return
    td = parse_duration(duration)
    if not td:
        await interaction.response.send_message("Invalid time format. Use: `30s`, `10m`, `2h`, `1d`", ephemeral=True)
        return
    await interaction.response.send_message("Giveaway started!", ephemeral=True)
    end_time = discord.utils.utcnow() + td
    embed = discord.Embed(
        title=title,
        description=f"React with 🎉 to enter!\n\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Started by {interaction.user}")
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")
    active_giveaways[msg.id] = {
        "channel_id": interaction.channel.id,
        "message_id": msg.id,
        "end_time": end_time,
        "winners": winners,
        "title": title,
        "author_id": interaction.user.id,
        "ended": False,
    }
    await asyncio.sleep(td.total_seconds())
    if active_giveaways.get(msg.id, {}).get("ended"):
        return
    active_giveaways[msg.id]["ended"] = True
    try:
        msg = await interaction.channel.fetch_message(msg.id)
    except discord.NotFound:
        return
    users = []
    async for user in msg.reactions[0].users():
        if not user.bot:
            users.append(user)
    if not users:
        embed = discord.Embed(
            title=title,
            description="**No entries** — Giveaway cancelled.",
            color=discord.Color.greyple(),
        )
        await msg.edit(embed=embed)
        return
    winner_count = min(winners, len(users))
    chosen = random.sample(users, winner_count)
    winner_mentions = ", ".join(w.mention for w in chosen)
    embed = discord.Embed(
        title=title,
        description=f"**Winner(s):** {winner_mentions}\n\nCongratulations!",
        color=discord.Color.green(),
    )
    await msg.edit(embed=embed)
    await interaction.channel.send(f"🎉 Congratulations {winner_mentions}! You won **{title}**!")


@app_commands.command(name="endgiveaway", description="End a giveaway early")
@app_commands.describe(message_id="Message ID of the giveaway to end")
@app_commands.default_permissions(manage_messages=True)
async def endgiveaway_command(interaction: discord.Interaction, message_id: str):
    role = interaction.guild.get_role(STAFF_ROLE_ID)
    if not role or role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    msg_id = int(message_id)
    giveaway = active_giveaways.get(msg_id)
    if not giveaway:
        await interaction.response.send_message("Giveaway not found.", ephemeral=True)
        return
    if giveaway["ended"]:
        await interaction.response.send_message("This giveaway already ended.", ephemeral=True)
        return
    giveaway["ended"] = True
    try:
        g_channel = interaction.guild.get_channel(giveaway["channel_id"])
        msg = await g_channel.fetch_message(msg_id)
    except (discord.NotFound, AttributeError):
        await interaction.response.send_message("Giveaway message not found.", ephemeral=True)
        return
    users = []
    async for user in msg.reactions[0].users():
        if not user.bot:
            users.append(user)
    if not users:
        embed = discord.Embed(
            title=giveaway["title"],
            description="**No entries** — Giveaway cancelled.",
            color=discord.Color.greyple(),
        )
        await msg.edit(embed=embed)
        await interaction.response.send_message("Giveaway ended — no entries.")
        return
    winner_count = min(giveaway["winners"], len(users))
    chosen = random.sample(users, winner_count)
    winner_mentions = ", ".join(w.mention for w in chosen)
    embed = discord.Embed(
        title=giveaway["title"],
        description=f"**Winner(s):** {winner_mentions}\n\nCongratulations!",
        color=discord.Color.green(),
    )
    await msg.edit(embed=embed)
    await interaction.response.send_message(f"🎉 Congratulations {winner_mentions}! You won **{giveaway['title']}**!")


@app_commands.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="All available commands",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Staff (Slash Commands)",
        value=(
            "`/giveaway <winners> <duration> <title>` — Create giveaway\n"
            "`/endgiveaway <message_id>` — End giveaway early\n"
            "`/deletechannel` — Delete your private channel"
        ),
        inline=False,
    )
    embed.add_field(
        name="Moderation (Prefix Commands)",
        value=(
            "`?ban @user [duration] [reason]` — Ban a user\n"
            "`?unban <userid>` — Unban a user\n"
            "`?kick @user [reason]` — Kick a user\n"
            "`?mute @user <duration> [reason]` — Timeout a user\n"
            "`?unmute @user` — Remove timeout\n"
            "`?purge <count>` — Delete messages (1-100)\n"
            "`?lock` — Lock channel\n"
            "`?unlock` — Unlock channel"
        ),
        inline=False,
    )
    embed.add_field(
        name="Roles (Prefix Commands)",
        value=(
            "`?role @role` — Assign role to all members\n"
            "`?autorole @role` — Auto-assign role on join"
        ),
        inline=False,
    )
    embed.add_field(
        name="Services (Slash Commands)",
        value=(
            "Use the service panels in the channel list for:\n"
            "Temp Mail, File Share, Password Generator, IP Lookup,\n"
            "Password Breach Check, Calculator, Unit Converter,\n"
            "Currency Converter, User Info, Crypto Lookup,\n"
            "Translator, Tier Tracker, Delete Channel"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="deletechannel", description="Delete your private channel")
async def deletechannel_command(interaction: discord.Interaction):
    is_admin = interaction.user.id == ADMIN_ID

    account = interaction.client.channel_accounts.get(interaction.channel_id)
    if account:
        if interaction.user.id != account.get("owner_id") and not is_admin:
            await interaction.response.send_message("Only the channel owner can delete this.", ephemeral=True)
            return
        try:
            if interaction.client.mailtm:
                account_id = account.get("account_id")
                token = account.get("token")
                if account_id and token:
                    await interaction.client.mailtm.delete_account(token, account_id)
            owner_id = account.get("owner_id")
            owner_accounts = interaction.client.user_accounts.get(owner_id, [])
            owner_accounts = [a for a in owner_accounts if a.get("channel_id") != interaction.channel_id]
            if owner_accounts:
                interaction.client.user_accounts[owner_id] = owner_accounts
            else:
                interaction.client.user_accounts.pop(owner_id, None)
            interaction.client.channel_accounts.pop(interaction.channel_id, None)
            await interaction.response.send_message("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
        return

    sessions = load_sessions()
    for sid, data in list(sessions.items()):
        if data.get("channel_id") == interaction.channel_id:
            if interaction.user.id != data.get("owner_id") and not is_admin:
                await interaction.response.send_message("Only the channel owner can delete this.", ephemeral=True)
                return
            del sessions[sid]
            save_sessions(sessions)
            await interaction.response.send_message("Channel deleted.", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
            return

    if interaction.channel_id in password_configs:
        config = password_configs[interaction.channel_id]
        if interaction.user.id != config.get("owner_id") and not is_admin:
            await interaction.response.send_message("Only the channel owner can delete this.", ephemeral=True)
            return
        del password_configs[interaction.channel_id]
        await interaction.response.send_message("Channel deleted.", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()
        return

    await interaction.response.send_message("This doesn't look like a private channel.", ephemeral=True)


class AccountAddModal(discord.ui.Modal, title="Add Accounts"):
    usernames_input = discord.ui.TextInput(
        label="Usernames (comma-separated)",
        placeholder="e.g. coldified,ItzRealMe",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        names = [n.strip() for n in self.usernames_input.value.split(",") if n.strip()]
        if not names:
            await interaction.response.send_message("No valid usernames provided.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        accounts = await load_tier_accounts()
        existing_names = get_tier_account_names(accounts)
        added = 0
        for name in names:
            if name not in existing_names:
                accounts.append({"name": name, "added_by": interaction.user.id})
                added += 1
        await save_tier_accounts(accounts)
        await interaction.followup.send(f"Added {added} account(s). Total tracked: {len(accounts)}", ephemeral=True)


class AccountRemoveModal(discord.ui.Modal, title="Remove Accounts"):
    usernames_input = discord.ui.TextInput(
        label="Usernames (comma-separated)",
        placeholder="e.g. coldified,ItzRealMe",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in TIER_ALLOWED_USERS:
            await interaction.response.send_message("You don't have access to this.", ephemeral=True)
            return
        names = [n.strip() for n in self.usernames_input.value.split(",") if n.strip()]
        await interaction.response.defer(ephemeral=True, thinking=True)
        accounts = await load_tier_accounts()
        removed = 0
        for name in names:
            for i, acc in enumerate(accounts):
                acc_name = acc["name"] if isinstance(acc, dict) else acc
                if acc_name == name:
                    accounts.pop(i)
                    removed += 1
                    break
        await save_tier_accounts(accounts)
        await interaction.followup.send(f"Removed {removed} account(s). Total tracked: {len(accounts)}", ephemeral=True)


def main():
    global _bot_instance
    token = TOKEN or os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set TOKEN in main.py or DISCORD_TOKEN environment variable")

    flask_thread = threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000))), daemon=True)
    flask_thread.start()
    print("File share web server running on http://localhost:5000")

    cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
    cleanup_thread.start()

    bot = Bot()
    _bot_instance = bot
    bot.add_command(lock_command)
    bot.add_command(unlock_command)
    bot.add_command(role_command)
    bot.add_command(autorole_command)
    bot.add_command(purge_command)
    bot.add_command(ban_command)
    bot.add_command(kick_command)
    bot.add_command(mute_command)
    bot.add_command(unmute_command)
    bot.add_command(unban_command)
    bot.event(on_member_join)
    bot.add_view(TempMailPanelView(bot))
    bot.add_view(DeleteAccountView(bot))
    bot.add_view(FileSharePanelView(bot))
    bot.add_view(FileShareDeleteView())
    bot.add_view(PasswordGenPanelView(bot))
    bot.add_view(PasswordGenConfigView())
    bot.add_view(PasswordGenDeleteView())
    bot.add_view(IPLookupPanelView(bot))
    bot.add_view(IPLookupConfigView())
    bot.add_view(TierPanelView(bot))
    bot.add_view(TierConfigView())
    bot.add_view(PasswordBreachPanelView(bot))
    bot.add_view(PasswordBreachConfigView())
    bot.add_view(CalculatorPanelView(bot))
    bot.add_view(CalculatorConfigView())
    bot.add_view(UnitConverterPanelView(bot))
    bot.add_view(UnitConverterConfigView())
    bot.add_view(CurrencyConverterPanelView(bot))
    bot.add_view(CurrencyConverterConfigView())
    bot.add_view(UserInfoPanelView(bot))
    bot.add_view(UserInfoConfigView())
    bot.add_view(CryptoPricePanelView(bot))
    bot.add_view(CryptoPriceConfigView())
    bot.add_view(CryptoLookupPanelView(bot))
    bot.add_view(CryptoLookupConfigView())
    bot.add_view(TranslatorPanelView(bot))
    bot.add_view(TranslatorConfigView())
    bot.run(token)


if __name__ == "__main__":
    main()
