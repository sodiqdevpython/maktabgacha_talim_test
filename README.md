# Test bot (Telegram Web App)

Telegram bot ichida ochiladigan test ilovasi: mavzular bo‘yicha testlar, aralash test, ikki xil rejim.
Backend — Django + Django REST Framework, baza — SQLite.

## Ishga tushirish

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py import_questions        # savollar/ papkasidagi Excel fayllardan savollarni yuklaydi
python manage.py createsuperuser         # admin panel uchun login/parol
```

`.env` faylida:

| O‘zgaruvchi  | Nima uchun |
|--------------|------------|
| `BOT_TOKEN`  | BotFather bergan token |
| `WEBAPP_URL` | Ilova ochiladigan **HTTPS** manzil (Telegram faqat HTTPS da ochadi) |
| `DEBUG`      | Serverda `0` bo‘lsin |
| `DEV_USER_ID`| Faqat `DEBUG=1` da: brauzerda Telegramsiz sinash uchun (masalan `1`) |

Ikkita jarayon ishlab turishi kerak:

```bash
python manage.py runserver 0.0.0.0:8000   # sayt + API (serverda gunicorn/waitress ishlating)
python manage.py runbot                   # Telegram bot
```

## Qanday ishlaydi

- **Bosh sahifa** — modullar va mavzular ro‘yxati, tepada «Aralash test».
- **Mashq** rejimi — xato javob qizil bo‘ladi, to‘g‘risi ko‘rsatilmaydi; to‘g‘ri topilmaguncha keyingi savolga o‘tmaydi.
- **Imtihon** rejimi — har savolga bitta urinish: to‘g‘ri bo‘lsa yashil, xato bo‘lsa qizil (to‘g‘risi ko‘rsatiladi) va keyingisiga o‘tadi.
- **Aralash test** — nechta savol kerakligi kiritiladi, savollar barcha mavzulardan teng taqsimlab olinadi.
- Variantlar har safar aralashtiriladi. To‘g‘ri javob brauzerga yuborilmaydi — tekshiruv serverda.
- Tugallanmagan testni bosh sahifadagi «Davom ettirish» orqali davom ettirish mumkin.
- **Reyting** (pastki menyu) — bugun / shu hafta / shu oyda eng ko‘p savol ishlagan foydalanuvchilar.
- **Natijalarim** (pastki menyu) — foydalanuvchining o‘z ko‘rsatkichlari va oxirgi testlari.

## Admin panel

`/admin/` — foydalanuvchilar (kim kirgan, nechta test ishlagan, natijasi), test urinishlari,
mavzular va savollar (tahrirlash, o‘chirish, faolsizlantirish).

## Savollarni yangilash

```bash
python manage.py import_questions                # faqat yangi savollarni qo‘shadi
python manage.py import_questions --replace      # mavzu savollarini o‘chirib, qaytadan yuklaydi
```

Excel fayl nomi mavzu kodi bilan boshlanishi kerak (`1.1 ...xlsx`). Ustunlar:
`Savol | Option A (to‘g‘ri) | Option B | Option C | Option D`.
Mavzu nomlari `quiz/topic_titles.py` da; keyin admin paneldan ham o‘zgartirsa bo‘ladi.

## Serverda (VPS)

Loyiha `/home/maktabgacha_talim_test` papkasida, alohida `quizbot` foydalanuvchisi nomidan ishlaydi.
Serverdagi boshqa loyihalarga tegmaslik uchun sayt o‘z portida ochiladi: `https://189-74-98-102.sslip.io:8443`.

| Nima | Qayerda |
|------|---------|
| Sayt + API (gunicorn, HTTPS :8443) | `systemctl status quizbot-web` |
| Telegram bot | `systemctl status quizbot-bot` |
| Sertifikatni yangilash (har hafta) | `systemctl list-timers quizbot-cert-renew.timer` |
| Sozlamalar | `/home/maktabgacha_talim_test/.env` |
| Baza | `/home/maktabgacha_talim_test/db.sqlite3` |
| Loglar | `journalctl -u quizbot-web -f`, `journalctl -u quizbot-bot -f` |

Yangi versiyani serverga chiqarish:

```bash
cd /home/maktabgacha_talim_test
runuser -u quizbot -- git pull
runuser -u quizbot -- venv/bin/pip install -r requirements.txt
runuser -u quizbot -- venv/bin/python manage.py migrate
runuser -u quizbot -- venv/bin/python manage.py import_questions
runuser -u quizbot -- venv/bin/python manage.py collectstatic --noinput
systemctl restart quizbot-web quizbot-bot
```

Admin uchun login yaratish (serverda bir marta):

```bash
cd /home/maktabgacha_talim_test && runuser -u quizbot -- venv/bin/python manage.py createsuperuser
```
