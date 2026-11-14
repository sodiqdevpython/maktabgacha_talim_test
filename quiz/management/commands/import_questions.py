"""Excel fayllardagi savollarni bazaga yuklaydi.

    python manage.py import_questions                 (standart: loyihadagi savollar/ papkasi)
    python manage.py import_questions D:/savollar --replace

Har bir .xlsx — bitta mavzu. Fayl nomi "1.1 ..." kabi kod bilan boshlanadi.
Ustunlar: Savol | Option A (to'g'ri) | Option B | Option C | Option D | Izoh (ixtiyoriy)
Izoh ustuni bo'lsa, u mavjud savollar uchun ham yangilanadi (izoh.py tuzadi).
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from quiz.models import Module, Question, QuestionExplanation, Topic
from quiz.topic_titles import MODULES, TOPICS


def clean(value):
    """Ortiqcha bo'shliqlarni olib tashlaydi, lekin qator uzilishlarini (moslashtirish savollari) saqlaydi."""
    if value is None:
        return ""
    lines = (" ".join(line.split()) for line in str(value).splitlines())
    return "\n".join(line for line in lines if line)


class Command(BaseCommand):
    help = "Excel fayllardagi test savollarini bazaga yuklaydi (har bir fayl — bitta mavzu)."

    def add_arguments(self, parser):
        parser.add_argument("folder", nargs="?", default=str(settings.BASE_DIR / "savollar"))
        parser.add_argument("--replace", action="store_true",
                            help="Mavzuning eski savollarini o'chirib, qaytadan yuklaydi")

    def handle(self, folder, replace, **opts):
        folder = Path(folder)
        if not folder.is_dir():
            raise CommandError(f"Papka topilmadi: {folder}")
        files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~$")]
        if not files:
            raise CommandError(f"{folder} ichida .xlsx fayl yo'q")

        total_new = total_expl = 0
        for f in sorted(files):
            m = re.match(r"\s*(\d+)[.,](\d+)", f.name)
            if not m:
                self.stderr.write(f"! O'tkazib yuborildi (nomida '1.1' kabi kod yo'q): {f.name}")
                continue
            mod_no, sub_no = int(m.group(1)), int(m.group(2))
            code = f"{mod_no}.{sub_no}"

            rows = []
            ws = load_workbook(f, read_only=True).active
            for r in ws.iter_rows(min_row=2, values_only=True):
                cells = [clean(c) for c in (list(r) + [None] * 6)[:6]]
                if all(cells[:4]):  # savol, to'g'ri javob va kamida 2 ta xato variant
                    rows.append(cells)

            with transaction.atomic():
                module, _ = Module.objects.get_or_create(
                    number=mod_no, defaults={"title": MODULES.get(mod_no, f"{mod_no}-modul")})
                topic, _ = Topic.objects.get_or_create(
                    code=code, defaults={"module": module, "order": mod_no * 100 + sub_no,
                                         "title": TOPICS.get(code, f.stem)})
                if replace:
                    topic.questions.all().delete()
                have = set(topic.questions.values_list("text", flat=True))
                new = [Question(topic=topic, text=c[0], correct=c[1], wrong1=c[2], wrong2=c[3], wrong3=c[4])
                       for c in rows if c[0] not in have]
                Question.objects.bulk_create(new)

                # izohlar: yangi va mavjud savollar uchun yaratiladi yoki yangilanadi
                ids = dict(topic.questions.values_list("text", "id"))
                old = {e.question_id: e for e in QuestionExplanation.objects.filter(question__topic=topic)}
                to_create, to_update = [], []
                for c in rows:
                    qid, text = ids.get(c[0]), c[5]
                    if not qid or not text:
                        continue
                    e = old.get(qid)
                    if e is None:
                        to_create.append(QuestionExplanation(question_id=qid, text=text))
                    elif e.text != text:
                        e.text = text
                        to_update.append(e)
                QuestionExplanation.objects.bulk_create(to_create)
                for e in to_update:
                    e.save()
                expl = len(to_create) + len(to_update)
            total_new += len(new)
            total_expl += expl
            self.stdout.write(f"{code:>5}  +{len(new):<4} savol, izoh +{expl:<4} (jami {topic.questions.count()})  {topic.title}")

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {total_new} ta yangi savol, {total_expl} ta izoh yangilandi. Bazada jami "
            f"{Question.objects.count()} ta savol, {QuestionExplanation.objects.count()} ta izoh, "
            f"{Topic.objects.count()} ta mavzu."))
