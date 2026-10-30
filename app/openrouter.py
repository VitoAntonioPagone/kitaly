import os
import json
import time
from typing import Optional

import requests
from requests.exceptions import RequestException, Timeout
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT = (3, 8)
OPENROUTER_MAX_ATTEMPTS = 2


def _clean_translation(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) >= 2:
        if (cleaned[0] == '"' and cleaned[-1] == '"') or (cleaned[0] == "“" and cleaned[-1] == "”"):
            cleaned = cleaned[1:-1].strip()
    return cleaned


def normalize_translation(value) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = _clean_translation(value)
    return value if value and value.lower() not in {'none', 'null'} else None


def translate_to_italian(text: str) -> Optional[str]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        current_app.logger.warning("OpenRouter API key not configured.")
        return None

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
        current_app.logger.warning("OpenRouter model not configured (OPENROUTER_MODEL).")
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Translate the following English text to Italian. "
                    "Return only the translation, no quotes. "
                    "Important lexical rule: when the English word 'vest' appears in football/apparel context, "
                    "translate it as 'canotta' or 'canottiera' (never 'gilet').\n\n"
                    f"{text}"
                ),
            }
        ],
        "temperature": 0.2,
    }

    for attempt in range(1, OPENROUTER_MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                OPENROUTER_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=OPENROUTER_TIMEOUT,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_seconds = 1
                if retry_after and retry_after.isdigit():
                    wait_seconds = min(int(retry_after), 2)
                if attempt < OPENROUTER_MAX_ATTEMPTS:
                    time.sleep(wait_seconds)
                    continue
                current_app.logger.warning("OpenRouter rate limited after %s attempts.", attempt)
                return None

            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            translated = normalize_translation(content)
            if not translated:
                current_app.logger.warning("OpenRouter returned an empty translation.")
            return translated
        except Timeout:
            if attempt < OPENROUTER_MAX_ATTEMPTS:
                continue
            current_app.logger.warning("OpenRouter request timed out after %s attempts.", attempt)
            return None
        except RequestException as exc:
            current_app.logger.warning("OpenRouter translation failed: %s", exc)
            return None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            current_app.logger.warning("OpenRouter returned an invalid translation response.")
            return None


def get_or_translate_description(shirt) -> Optional[str]:
    cached = normalize_translation(shirt.descrizione_ita)
    if cached:
        return cached
    source = shirt.descrizione
    if not source or not source.strip():
        return None

    previous_cache = shirt.descrizione_ita
    translated = normalize_translation(translate_to_italian(source))
    if not translated:
        return source

    try:
        # Only cache against the exact source that was translated. A concurrent
        # edit or manually supplied translation must not be overwritten.
        model = type(shirt)
        updated = db.session.query(model).filter(
            model.id == shirt.id,
            model.descrizione == source,
            model.descrizione_ita == previous_cache,
        ).update({model.descrizione_ita: translated}, synchronize_session=False)
        db.session.commit()
        db.session.refresh(shirt)
        if updated:
            return translated
        return normalize_translation(shirt.descrizione_ita) or shirt.descrizione
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not cache Italian translation for shirt %s.", shirt.id)
        return translated
