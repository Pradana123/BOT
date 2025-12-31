# article_generator.py
import os
import requests

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

def deepseek_chat(system: str, user: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY belum diisi di .env")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(
        f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def generate_article(prompt: str) -> str:
    system = (
        "Kamu penulis artikel SEO berbahasa Indonesia. "
        "Tulis artikel rapi, pakai heading, bullet, dan gaya profesional."
    )
    user = (
        "Buat artikel SEO berdasarkan topik berikut. "
        "Pastikan ada:\n"
        "- Judul\n- Pendahuluan\n- Poin utama (subheading)\n- FAQ singkat\n- Kesimpulan\n\n"
        f"TOPIK:\n{prompt}"
    )
    return deepseek_chat(system, user)
