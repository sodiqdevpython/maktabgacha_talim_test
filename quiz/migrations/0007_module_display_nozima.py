from django.db import migrations, models

DISPLAYS = [("list", "Ro‘yxat (ma’ruza moduli)"), ("buttons", "Har bir mavzu alohida tugma"),
            ("menu", "Bitta tugma, ichida qismlar")]


def forwards(apps, schema_editor):
    Module = apps.get_model("quiz", "Module")
    Topic = apps.get_model("quiz", "Topic")
    # "Tushgan testlar" to'plamlari avvalgidek alohida tugmalar bo'lib qoladi
    Module.objects.filter(number=0).update(display="buttons")
    # "Oktabr oyi testlari (2-qism)" o'rniga "Nozima" menyusi keladi (20.1-20.3 fayllaridan import qilinadi).
    # Eski to'plam o'chirilmaydi, faqat yashiriladi — foydalanuvchilarning shu testdagi natijalari saqlanadi.
    Topic.objects.filter(code="0.3").update(is_active=False)
    Topic.objects.filter(code="0.2", title="Oktabr oyi testlari (1-qism)").update(title="Oktabr oyi testlari")


def backwards(apps, schema_editor):
    Topic = apps.get_model("quiz", "Topic")
    Topic.objects.filter(code="0.3").update(is_active=True)
    Topic.objects.filter(code="0.2", title="Oktabr oyi testlari").update(title="Oktabr oyi testlari (1-qism)")


class Migration(migrations.Migration):
    dependencies = [("quiz", "0006_october_parts")]
    operations = [
        migrations.AddField(
            model_name="module",
            name="display",
            field=models.CharField(choices=DISPLAYS, default="list", max_length=8,
                                   verbose_name="Bosh sahifada ko‘rinishi"),
        ),
        migrations.RunPython(forwards, backwards),
    ]
