"""Telegram botni ishga tushiradi (long polling).

    python manage.py runbot

Bot /start ga Web App tugmasi bilan javob beradi va chatdagi menyu tugmasini Web App ga ulaydi.
.env faylida BOT_TOKEN va WEBAPP_URL (https://...) bo'lishi shart.
"""
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from quiz.auth import upsert_user

BUTTON_TEXT = "📝 Testni ochish"
WELCOME = (
    "Assalomu alaykum{name}!\n\n"
    "Imtihonga tayyorlanish uchun testlar shu yerda. "
    "Boshlash uchun pastdagi tugmani bosing."
)


class Command(BaseCommand):
    help = "Telegram botni ishga tushiradi (long polling)."

    def api(self, method, http_timeout=20, **params):
        params = {k: v for k, v in params.items() if v is not None}
        r = requests.post(f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}",
                          json=params, timeout=http_timeout)
        data = r.json()
        if not data.get("ok"):
            raise CommandError(f"Telegram xatosi ({method}): {data.get('description')}")
        return data["result"]

    def handle(self, **opts):
        if not settings.BOT_TOKEN:
            raise CommandError(".env faylida BOT_TOKEN yo'q")
        url = settings.WEBAPP_URL
        if not url.startswith("https://"):
            raise CommandError(".env faylida WEBAPP_URL yo'q yoki https:// bilan boshlanmaydi "
                               "(Telegram Web App faqat HTTPS manzilda ochiladi)")

        while True:  # tarmoq vaqtincha uzilsa bot yiqilmasin — qayta urinamiz
            try:
                me = self.api("getMe")
                self.api("setMyCommands", commands=[{"command": "start", "description": "Testlarni ochish"}])
                self.api("setChatMenuButton",
                         menu_button={"type": "web_app", "text": "Testlar", "web_app": {"url": url}})
                self.api("deleteWebhook")
                break
            except requests.RequestException as e:
                self.stderr.write(f"! Telegram bilan aloqa yo'q, 5 soniyadan keyin qayta urinaman: {e}")
                time.sleep(5)
        self.stdout.write(self.style.SUCCESS(f"@{me['username']} ishlayapti. Web App: {url}  (to'xtatish: Ctrl+C)"))

        offset = None
        while True:
            try:
                updates = self.api("getUpdates", http_timeout=40, offset=offset, timeout=30,
                                   allowed_updates=["message"])
            except (requests.RequestException, CommandError) as e:
                self.stderr.write(f"! {e}")
                time.sleep(3)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                sender = msg.get("from") or {}
                if not msg.get("chat") or sender.get("is_bot") or msg["chat"].get("type") != "private":
                    continue
                try:
                    upsert_user(sender)
                    name = f", {sender['first_name']}" if sender.get("first_name") else ""
                    self.api("sendMessage", chat_id=msg["chat"]["id"], text=WELCOME.format(name=name),
                             reply_markup={"inline_keyboard": [[
                                 {"text": BUTTON_TEXT, "web_app": {"url": url}}]]})
                except Exception as e:  # bitta xabardagi xato botni to'xtatmasin
                    self.stderr.write(f"! {e}")
