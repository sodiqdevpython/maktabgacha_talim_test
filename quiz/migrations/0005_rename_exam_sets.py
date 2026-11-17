from django.db import migrations

# "Tushgan testlar" to'plamlarining nomlari bosh sahifadagi tugmalarga sig'ishi uchun qisqartiriladi.
# Faqat eski standart nom turgan bo'lsa o'zgartiriladi — admin panelda qo'lda berilgan nomga tegilmaydi.
RENAMES = {
    "0.1": ("2026-yil sentabrda tushgan testlar", "Sentabr oyi testlari"),
    "0.2": ("2026-yil oktabrda tushgan testlar", "Oktabr oyi testlari"),
}


def forwards(apps, schema_editor):
    Topic = apps.get_model("quiz", "Topic")
    for code, (old, new) in RENAMES.items():
        Topic.objects.filter(code=code, title=old).update(title=new)


def backwards(apps, schema_editor):
    Topic = apps.get_model("quiz", "Topic")
    for code, (old, new) in RENAMES.items():
        Topic.objects.filter(code=code, title=new).update(title=old)


class Migration(migrations.Migration):
    dependencies = [("quiz", "0004_alter_question_wrong3")]
    operations = [migrations.RunPython(forwards, backwards)]
