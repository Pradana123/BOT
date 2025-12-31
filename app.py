# app.py
import os
import threading
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from article_generator import generate_article
from catalog_generator import generate_catalog

# =========================
# Load environment
# =========================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di .env")

TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# =========================
# App
# =========================
app = FastAPI()

# =========================
# Helpers
# =========================
SEEN_MESSAGES = set()

def seen_before(message_id: int) -> bool:
    if message_id in SEEN_MESSAGES:
        return True
    SEEN_MESSAGES.add(message_id)
    return False

def extract_message(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return update.get("message") or update.get("edited_message")

def get_text_or_caption(msg: Dict[str, Any]) -> Optional[str]:
    return msg.get("text") or msg.get("caption")

def tg_send_chat_action(chat_id: int, action: str = "typing") -> None:
    # "typing" = indikator loading di Telegram
    try:
        requests.post(
            f"{TG_API}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
            timeout=10,
        )
    except Exception:
        pass

def tg_send_message(
    chat_id: int,
    text: str,
    reply_to_message_id: Optional[int] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    # default None biar aman dari error "can't parse entities"
    parse_mode: Optional[str] = None,
) -> None:
    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=30)
        if r.status_code >= 400:
            print("sendMessage failed:", r.status_code, r.text)
    except Exception as e:
        print("sendMessage exception:", repr(e))

def tg_send_long_message(chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
    """Telegram limit text ~4096 chars. Split safely."""
    CHUNK = 3800  # leave headroom
    if len(text) <= CHUNK:
        tg_send_message(chat_id, text, reply_markup=reply_markup)
        return
    for i in range(0, len(text), CHUNK):
        part = text[i:i + CHUNK]
        tg_send_message(chat_id, part, reply_markup=reply_markup if i == 0 else None)

def start_typing_loop(chat_id: int, stop_event: threading.Event, every_seconds: int = 4) -> None:
    while not stop_event.is_set():
        tg_send_chat_action(chat_id, "typing")
        stop_event.wait(every_seconds)

# =========================
# Menu & State
# =========================
BTN_ARTICLE = "📝 Buat Artikel"
BTN_CATALOG = "🛍️ Katalog Produk"

MAIN_MENU = {
    "keyboard": [[{"text": BTN_ARTICLE}, {"text": BTN_CATALOG}]],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

CHAT_STATE: Dict[int, Dict[str, Any]] = {}

# =========================
# Routes
# =========================
@app.get("/")
def root():
    return {"ok": True}

@app.post("/telegram")
async def telegram_webhook(req: Request):
    update = await req.json()
    msg = extract_message(update)
    if not msg:
        return JSONResponse({"ok": True})

    message_id = int(msg.get("message_id", 0))
    if message_id and seen_before(message_id):
        return JSONResponse({"ok": True})

    chat_id = int(msg["chat"]["id"])
    text = (get_text_or_caption(msg) or "").strip()

    def send_menu():
        tg_send_message(chat_id, "👋 Halo! Mau buat apa?", reply_markup=MAIN_MENU)

    # --- menu selection
    if text == "/start":
        CHAT_STATE.pop(chat_id, None)
        send_menu()
        return JSONResponse({"ok": True})

    if text == BTN_ARTICLE:
        CHAT_STATE[chat_id] = {"mode": "article"}
        tg_send_message(chat_id, "Kirim topik artikel ✍️", reply_markup=MAIN_MENU)
        return JSONResponse({"ok": True})

    if text == BTN_CATALOG:
        CHAT_STATE[chat_id] = {"mode": "catalog"}
        tg_send_message(chat_id, "Kirim detail katalog produk 🛍️", reply_markup=MAIN_MENU)
        return JSONResponse({"ok": True})

    state = CHAT_STATE.get(chat_id)
    if not state:
        send_menu()
        return JSONResponse({"ok": True})

    # --- processing with loading + error message
    stop = threading.Event()
    t = threading.Thread(target=start_typing_loop, args=(chat_id, stop), daemon=True)
    t.start()

    try:
        if state["mode"] == "article":
            content = generate_article(text)
            tg_send_long_message(chat_id, f"✅ Artikel siap:\n\n{content}", reply_markup=MAIN_MENU)
            return JSONResponse({"ok": True})

        if state["mode"] == "catalog":
            content = generate_catalog(text)
            tg_send_long_message(chat_id, f"✅ Katalog siap:\n\n{content}", reply_markup=MAIN_MENU)
            return JSONResponse({"ok": True})

        tg_send_message(chat_id, "Mode tidak dikenal. Ketik /start untuk mulai lagi.", reply_markup=MAIN_MENU)
        return JSONResponse({"ok": True})

    except Exception as e:
        print("ERROR:", repr(e))
        tg_send_message(
            chat_id,
            "❌ Terjadi error saat memproses pesan kamu.\n\n"
            f"Detail: {e}\n\n"
            "Coba lagi, atau ketik /start untuk ulang.",
            reply_markup=MAIN_MENU,
        )
        return JSONResponse({"ok": True})

    finally:
        stop.set()
        CHAT_STATE.pop(chat_id, None)
