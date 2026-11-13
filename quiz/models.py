from django.db import models


class TelegramUser(models.Model):
    tg_id = models.BigIntegerField("Telegram ID", unique=True)
    first_name = models.CharField("Ism", max_length=128, blank=True)
    last_name = models.CharField("Familiya", max_length=128, blank=True)
    username = models.CharField("Username", max_length=64, blank=True)
    language_code = models.CharField("Til", max_length=16, blank=True)
    is_blocked = models.BooleanField("Bloklangan", default=False)
    created_at = models.DateTimeField("Qo‘shilgan", auto_now_add=True)
    last_seen = models.DateTimeField("Oxirgi faollik", null=True, blank=True)

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["-last_seen"]

    def __str__(self):
        return self.display_name or str(self.tg_id)

    @property
    def display_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or (f"@{self.username}" if self.username else "")

    # DRF IsAuthenticated uchun
    @property
    def is_authenticated(self):
        return True


class Module(models.Model):
    number = models.PositiveIntegerField("Raqam", unique=True)
    title = models.CharField("Nomi", max_length=255)

    class Meta:
        verbose_name = "Modul"
        verbose_name_plural = "Modullar"
        ordering = ["number"]

    def __str__(self):
        return f"{self.number}-modul. {self.title}"


class Topic(models.Model):
    module = models.ForeignKey(Module, verbose_name="Modul", related_name="topics", on_delete=models.CASCADE)
    code = models.CharField("Kod", max_length=16, unique=True)  # masalan "1.1"
    order = models.PositiveIntegerField("Tartib", default=0)
    title = models.CharField("Nomi", max_length=255)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        ordering = ["order"]

    def __str__(self):
        return f"{self.code}. {self.title}"


class Question(models.Model):
    topic = models.ForeignKey(Topic, verbose_name="Mavzu", related_name="questions", on_delete=models.CASCADE)
    text = models.TextField("Savol")
    correct = models.TextField("To‘g‘ri javob")
    wrong1 = models.TextField("Xato javob 1")
    wrong2 = models.TextField("Xato javob 2")
    wrong3 = models.TextField("Xato javob 3")
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ["topic__order", "id"]

    def __str__(self):
        return self.text[:80]

    @property
    def options(self):
        """0-indeks doim to'g'ri javob; foydalanuvchiga aralashtirilgan tartibda yuboriladi."""
        return [self.correct, self.wrong1, self.wrong2, self.wrong3]


class QuizSession(models.Model):
    STRICT = "strict"   # to'g'ri topmaguncha keyingisiga o'tmaydi
    EXAM = "exam"       # har savolga bitta urinish
    MODES = [(STRICT, "Mashq (to‘g‘ri topguncha)"), (EXAM, "Imtihon (bitta urinish)")]

    user = models.ForeignKey(TelegramUser, verbose_name="Foydalanuvchi", related_name="sessions",
                             on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, verbose_name="Mavzu", related_name="sessions", null=True, blank=True,
                              on_delete=models.SET_NULL, help_text="Bo‘sh bo‘lsa — aralash test")
    is_mixed = models.BooleanField("Aralash", default=False)
    mode = models.CharField("Rejim", max_length=8, choices=MODES, default=STRICT)
    total = models.PositiveIntegerField("Savollar soni", default=0)
    position = models.PositiveIntegerField("Javob berilgan", default=0)
    correct_count = models.PositiveIntegerField("Birinchi urinishda to‘g‘ri", default=0)
    started_at = models.DateTimeField("Boshlangan", auto_now_add=True)
    finished_at = models.DateTimeField("Tugagan", null=True, blank=True)

    class Meta:
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} — {self.title}"

    @property
    def title(self):
        if self.is_mixed or self.topic_id is None:
            return "Aralash test"
        return self.topic.title

    @property
    def is_complete(self):
        return self.total > 0 and self.position >= self.total

    @property
    def percent(self):
        return round(100 * self.correct_count / self.position) if self.position else 0


class SessionQuestion(models.Model):
    session = models.ForeignKey(QuizSession, related_name="items", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, verbose_name="Savol", related_name="+", on_delete=models.CASCADE)
    index = models.PositiveIntegerField("Tartib")
    # Variantlar tartibi: har bir belgi Question.options indeksi ("2031" -> A=options[2], B=options[0], ...)
    order = models.CharField(max_length=4)
    tried = models.CharField("Xato bosilgan o‘rinlar", max_length=4, blank=True)
    answered = models.BooleanField("Javob berilgan", default=False)
    first_try_correct = models.BooleanField("Birinchi urinishda to‘g‘ri", null=True)
    answered_at = models.DateTimeField("Javob vaqti", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Urinishdagi savol"
        verbose_name_plural = "Urinishdagi savollar"
        ordering = ["index"]
        constraints = [models.UniqueConstraint(fields=["session", "index"], name="uniq_session_index")]
