"""Telegram Web App foydalanuvchisini `initData` imzosi orqali tekshirish.

Brauzer har so'rovda `Authorization: tma <initData>` yuboradi. initData Telegram tomonidan
bot tokeni bilan imzolangan, shuning uchun uni qalbakilashtirib bo'lmaydi.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import TelegramUser


def parse_init_data(init_data, bot_token, max_age=None):
    """initData to'g'ri imzolangan bo'lsa undagi `user` lug'atini qaytaradi, aks holda None."""
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    received = pairs.pop("hash", "")
    if not received:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    if max_age:
        try:
            if time.time() - int(pairs.get("auth_date", "0")) > max_age:
                return None
        except ValueError:
            return None
    try:
        user = json.loads(pairs.get("user", ""))
    except ValueError:
        return None
    return user if isinstance(user, dict) and isinstance(user.get("id"), int) else None


def upsert_user(data):
    """Telegram'dan kelgan ma'lumot bo'yicha foydalanuvchini yaratadi yoki yangilaydi."""
    fields = {
        "first_name": (data.get("first_name") or "")[:128],
        "last_name": (data.get("last_name") or "")[:128],
        "username": (data.get("username") or "")[:64],
        "language_code": (data.get("language_code") or "")[:16],
    }
    user, created = TelegramUser.objects.get_or_create(
        tg_id=data["id"], defaults={**fields, "last_seen": timezone.now()})
    if not created:
        changed = [k for k, v in fields.items() if getattr(user, k) != v]
        for k in changed:
            setattr(user, k, fields[k])
        now = timezone.now()
        if user.last_seen is None or (now - user.last_seen).total_seconds() > 60:
            user.last_seen = now
            changed.append("last_seen")
        if changed:
            user.save(update_fields=changed)
    return user


class TelegramAuthentication(authentication.BaseAuthentication):
    keyword = "tma"

    def authenticate_header(self, request):
        return self.keyword

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        data = None
        if header.lower().startswith(self.keyword + " "):
            data = parse_init_data(header[len(self.keyword) + 1:].strip(), settings.BOT_TOKEN,
                                   settings.INITDATA_MAX_AGE)
            if data is None:
                raise exceptions.AuthenticationFailed("Telegram sessiyasi yaroqsiz. Ilovani qayta oching.")
        elif settings.DEBUG and settings.DEV_USER_ID:
            data = {"id": settings.DEV_USER_ID, "first_name": "Sinov", "last_name": "foydalanuvchi"}
        if data is None:
            return None
        user = upsert_user(data)
        if user.is_blocked:
            raise exceptions.AuthenticationFailed("Sizga kirish taqiqlangan.")
        return (user, None)
