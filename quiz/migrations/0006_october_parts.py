from django.db import migrations

# Oktabr testlarining ikkinchi to'plami qo'shilgani uchun birinchisi "1-qism" deb nomlanadi.
# Faqat eski standart nom turgan bo'lsa o'zgartiriladi — admin panelda qo'lda berilgan nomga tegilmaydi.
OLD, NEW = "Oktabr oyi testlari", "Oktabr oyi testlari (1-qism)"


def forwards(apps, schema_editor):
    apps.get_model("quiz", "Topic").objects.filter(code="0.2", title=OLD).update(title=NEW)


def backwards(apps, schema_editor):
    apps.get_model("quiz", "Topic").objects.filter(code="0.2", title=NEW).update(title=OLD)


class Migration(migrations.Migration):
    dependencies = [("quiz", "0005_rename_exam_sets")]
    operations = [migrations.RunPython(forwards, backwards)]
