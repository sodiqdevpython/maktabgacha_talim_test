from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from .models import Module, Question, QuizSession, SessionQuestion, TelegramUser, Topic


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class SessionInline(ReadOnlyInline):
    model = QuizSession
    fields = ("title_col", "mode", "progress", "percent_col", "started_at", "finished_at")
    readonly_fields = fields
    ordering = ("-started_at",)
    verbose_name_plural = "Test urinishlari"

    @admin.display(description="Test")
    def title_col(self, obj):
        return obj.title

    @admin.display(description="Javob berilgan")
    def progress(self, obj):
        return f"{obj.position} / {obj.total}"

    @admin.display(description="Natija")
    def percent_col(self, obj):
        return f"{obj.percent}%" if obj.position else "—"


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "username_link", "tg_id", "tests", "answered", "accuracy",
                    "last_seen", "created_at", "is_blocked")
    list_filter = ("is_blocked", "created_at", "last_seen")
    search_fields = ("first_name", "last_name", "username", "tg_id")
    readonly_fields = ("tg_id", "first_name", "last_name", "username", "language_code",
                       "created_at", "last_seen")
    fields = readonly_fields + ("is_blocked",)
    inlines = [SessionInline]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _tests=Count("sessions", distinct=True),
            _answered=Count("sessions__items", filter=Q(sessions__items__answered=True)),
            _correct=Count("sessions__items", filter=Q(sessions__items__first_try_correct=True)),
        )

    @admin.display(description="Ism", ordering="first_name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "—"

    @admin.display(description="Username", ordering="username")
    def username_link(self, obj):
        if not obj.username:
            return "—"
        return format_html('<a href="https://t.me/{0}" target="_blank" rel="noopener">@{0}</a>', obj.username)

    @admin.display(description="Testlar", ordering="_tests")
    def tests(self, obj):
        return obj._tests

    @admin.display(description="Javoblar", ordering="_answered")
    def answered(self, obj):
        return obj._answered

    @admin.display(description="To‘g‘ri (1-urinishda)")
    def accuracy(self, obj):
        return f"{round(100 * obj._correct / obj._answered)}%" if obj._answered else "—"


class SessionQuestionInline(ReadOnlyInline):
    model = SessionQuestion
    fields = ("index", "question", "answered", "first_try_correct", "wrong_tries")
    readonly_fields = fields
    show_change_link = False
    verbose_name_plural = "Savollar"

    @admin.display(description="Xato urinishlar")
    def wrong_tries(self, obj):
        return len(obj.tried)


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "title_col", "mode", "progress", "percent_col", "started_at", "finished_at")
    list_filter = ("mode", "is_mixed", "topic__module", "started_at")
    search_fields = ("user__first_name", "user__last_name", "user__username", "user__tg_id")
    list_select_related = ("user", "topic")
    readonly_fields = ("user", "topic", "is_mixed", "mode", "total", "position", "correct_count",
                       "started_at", "finished_at")
    inlines = [SessionQuestionInline]
    date_hierarchy = "started_at"

    def has_add_permission(self, request):
        return False

    @admin.display(description="Test")
    def title_col(self, obj):
        return obj.title

    @admin.display(description="Javob berilgan")
    def progress(self, obj):
        return f"{obj.position} / {obj.total}"

    @admin.display(description="Natija", ordering="correct_count")
    def percent_col(self, obj):
        return f"{obj.percent}%" if obj.position else "—"


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    fields = ("code", "order", "title", "is_active")
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "topic_count")
    list_display_links = ("number", "title")
    inlines = [TopicInline]

    @admin.display(description="Mavzular")
    def topic_count(self, obj):
        return obj.topics.count()


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "module", "question_count", "is_active")
    list_display_links = ("code", "title")
    list_filter = ("module", "is_active")
    list_editable = ("is_active",)
    search_fields = ("code", "title")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_q=Count("questions"))

    @admin.display(description="Savollar", ordering="_q")
    def question_count(self, obj):
        return obj._q


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_text", "topic", "is_active")
    list_filter = ("is_active", "topic__module", "topic")
    search_fields = ("text", "correct", "wrong1", "wrong2", "wrong3")
    list_select_related = ("topic",)
    list_per_page = 50

    @admin.display(description="Savol")
    def short_text(self, obj):
        return obj.text[:110]
