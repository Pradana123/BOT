# catalog_generator.py
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

def generate_catalog(prompt: str) -> str:
    system = (
        "Kamu copywriter katalog produk berbahasa Indonesia. "
        "Buat katalog yang rapi dan mudah dipakai sales/marketplace."
    )
    user = (
        "Buat 1 halaman katalog produk dari instruksi berikut. "
        "Kalau detail kurang, buat template tabel produk + tanyakan data yang kurang.\n\n"
        "Format yang disarankan:\n"
        "- Judul\n- Ringkasan\n- Tabel/daftar produk (Nama | Harga | Keunggulan | Cocok untuk)\n"
        "- CTA (cara order)\n\n"
        f"INSTRUKSI:\n{prompt}"
    )
    return deepseek_chat(system, user)
