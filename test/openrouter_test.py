import json
import os
import sys

import requests
from dotenv import load_dotenv


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def main() -> int:
    load_dotenv(".env")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in .env")
        return 1

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:]).strip()
    else:
        text = input("English description: ").strip()

    if not text:
        print("ERROR: empty description")
        return 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    site_url = os.getenv("OPENROUTER_SITE_URL")
    site_name = os.getenv("OPENROUTER_SITE_NAME")
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name

    model = os.getenv("OPENROUTER_MODEL")
    if not model:
        print("ERROR: OPENROUTER_MODEL not set in .env")
        return 1

    print("Model:", model)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Translate the following English text to Italian. "
                    "Return only the translation, no quotes.\n\n"
                    f"{text}"
                ),
            }
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=(3, 12),
    )

    print("Status:", response.status_code)
    if response.status_code != 200:
        print(response.text)
        return 1

    data = response.json()
    translation = data["choices"][0]["message"]["content"].strip()
    print("Translation:", translation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
