import random
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Question, QuestionExplanation, QuizSession, SessionQuestion, TelegramUser, Topic
from .serializers import AnswerSerializer, StartSessionSerializer

STATIC_DIR = Path(__file__).resolve().parent / "static" / "quiz"


@xframe_options_exempt  # Telegram Web (brauzer) ilovani iframe ichida ochadi
def index(request):
    version = max(int(p.stat().st_mtime) for p in STATIC_DIR.iterdir())
    return render(request, "quiz/index.html", {"v": version})


# ------------------------------------------------------------------ yordamchilar


def first_unanswered(s):
    return s.items.filter(answered=False).order_by("index").values_list("index", flat=True).first()


def session_payload(s):
    """position — javob berilgan savollar soni; current — javob berilmagan birinchi savol."""
    return {"id": s.id, "mode": s.mode, "total": s.total, "position": s.position,
            "title": s.title, "topic": None if s.is_mixed else s.topic_id, "mixed": s.is_mixed,
            "done": s.is_complete, "closed": s.finished_at is not None,
            "current": None if s.is_complete else first_unanswered(s)}


def explanation_of(q):
    try:
        return q.explanation.text
    except QuestionExplanation.DoesNotExist:
        return ""


def question_payload(s, index=None):
    """Bitta savol holati (index berilmasa — javob berilmagan birinchi savol).

    To'g'ri javob o'rni va izoh brauzerga FAQAT savolga javob berib bo'lingandan keyin yuboriladi.
    """
    if index is None:
        index = first_unanswered(s)
        if index is None:
            return None
    item = (s.items.select_related("question__topic", "question__explanation")
            .filter(index=index).first())
    if item is None:
        return None
    q = item.question
    opts = q.options
    data = {
        "index": item.index,
        "text": q.text,
        "options": [opts[int(c)] for c in item.order],
        "tried": [int(c) for c in item.tried],
        "topic": f"{q.topic.code}. {q.topic.title}" if s.is_mixed else "",
        "answered": item.answered,
    }
    if item.answered:
        data["correct_position"] = item.order.index("0")
        data["explanation"] = explanation_of(q)
    return data


def pick_mixed(n):
    """Barcha mavzulardan imkon qadar teng taqsimlab n ta savol tanlaydi."""
    by_topic = defaultdict(list)
    rows = Question.objects.filter(is_active=True, topic__is_active=True).values_list("id", "topic_id")
    for qid, tid in rows:
        by_topic[tid].append(qid)
    for ids in by_topic.values():
        random.shuffle(ids)
    topics, chosen = list(by_topic), []
    while len(chosen) < n and topics:
        random.shuffle(topics)
        for t in list(topics):
            if len(chosen) >= n:
                break
            chosen.append(by_topic[t].pop())
            if not by_topic[t]:
                topics.remove(t)
    random.shuffle(chosen)
    return chosen


def random_order():
    order = list("0123")
    random.shuffle(order)
    return "".join(order)


# ------------------------------------------------------------------ API


@api_view(["GET"])
def home(request):
    user = request.user
    topics = (Topic.objects.filter(is_active=True).select_related("module")
              .annotate(n=Count("questions", filter=Q(questions__is_active=True)))
              .filter(n__gt=0).order_by("module__number", "order"))

    best = {}
    done = QuizSession.objects.filter(user=user, is_mixed=False, topic__isnull=False, total__gt=0,
                                      position=F("total")).values_list("topic_id", "correct_count", "total")
    for tid, correct, total in done:
        best[tid] = max(best.get(tid, 0), round(100 * correct / total))

    modules, total = [], 0
    for t in topics:
        if not modules or modules[-1]["number"] != t.module.number:
            modules.append({"number": t.module.number, "title": t.module.title, "topics": []})
        modules[-1]["topics"].append({"id": t.id, "code": t.code, "title": t.title, "count": t.n,
                                      "best": best.get(t.id)})
        total += t.n

    active = (QuizSession.objects.filter(user=user, finished_at__isnull=True, position__gt=0)
              .select_related("topic").order_by("-started_at").first())
    return Response({
        "user": {"name": user.first_name or str(user)},
        "modules": modules,
        "total": total,
        "resume": session_payload(active) if active else None,
    })


@api_view(["POST"])
def start_session(request):
    ser = StartSessionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    topic = ser.validated_data.get("topic")
    mode = ser.validated_data["mode"]
    count = ser.validated_data.get("count")

    if topic:
        ids = list(topic.questions.filter(is_active=True).values_list("id", flat=True))
        random.shuffle(ids)
        if count:
            ids = ids[:count]
    else:
        ids = pick_mixed(count or 30)
    if not ids:
        return Response({"detail": "Savollar topilmadi."}, status=400)

    with transaction.atomic():
        # Bir vaqtda faqat bitta tugallanmagan test bo'ladi
        old = QuizSession.objects.filter(user=request.user, finished_at__isnull=True)
        old.filter(position=0).delete()
        old.update(finished_at=timezone.now())
        s = QuizSession.objects.create(user=request.user, topic=topic, is_mixed=topic is None,
                                       mode=mode, total=len(ids))
        SessionQuestion.objects.bulk_create(
            SessionQuestion(session=s, question_id=qid, index=i, order=random_order())
            for i, qid in enumerate(ids))
    return Response({"session": session_payload(s), "question": question_payload(s)}, status=201)


@api_view(["GET"])
def session_detail(request, pk):
    s = get_object_or_404(QuizSession.objects.select_related("topic"), pk=pk, user=request.user)
    return Response({"session": session_payload(s), "question": question_payload(s)})


@api_view(["GET"])
def question(request, pk, index):
    """Istalgan savolni ko'rish — oldingi/keyingi savolga o'tish uchun."""
    s = get_object_or_404(QuizSession.objects.select_related("topic"), pk=pk, user=request.user)
    data = question_payload(s, index)
    if data is None:
        return Response({"detail": "Savol topilmadi."}, status=404)
    return Response({"session": session_payload(s), "question": data})


@api_view(["POST"])
def answer(request, pk):
    ser = AnswerSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    index, position = ser.validated_data["index"], ser.validated_data["position"]

    with transaction.atomic():
        s = get_object_or_404(QuizSession.objects.select_for_update().select_related("topic"),
                              pk=pk, user=request.user)
        item = s.items.select_related("question").filter(index=index).first()
        if item is None:
            return Response({"detail": "Savol topilmadi."}, status=404)
        if item.answered or s.finished_at:
            # Bu savolga allaqachon javob berilgan yoki test yopilgan — joriy holatni qaytaramiz
            return Response({"stale": True, "session": session_payload(s),
                             "question": question_payload(s, index)})

        is_correct = item.order[position] == "0"
        resolved = False

        if s.mode == QuizSession.STRICT:  # mashq: to'g'ri topilmaguncha savol ochiq qoladi
            if is_correct:
                item.first_try_correct = item.tried == ""
                resolved = True
            elif str(position) not in item.tried:
                item.tried += str(position)
        else:  # imtihon: bitta urinish
            item.first_try_correct = is_correct
            resolved = True
            if not is_correct:
                item.tried = str(position)

        if resolved:
            item.answered = True
            item.answered_at = timezone.now()
            s.position += 1
            if item.first_try_correct:
                s.correct_count += 1
            if s.is_complete:
                s.finished_at = timezone.now()
            s.save(update_fields=["position", "correct_count", "finished_at"])
        item.save(update_fields=["tried", "answered", "first_try_correct", "answered_at"])

    return Response({
        "correct": is_correct,
        "resolved": resolved,
        "session": session_payload(s),
        # yangilangan holat: javob berilgan bo'lsa to'g'ri javob o'rni va izoh bilan
        "question": question_payload(s, index),
    })


@api_view(["GET"])
def result(request, pk):
    s = get_object_or_404(QuizSession.objects.select_related("topic"), pk=pk, user=request.user)
    missed = (s.items.filter(answered=True, first_try_correct=False)
              .select_related("question__explanation"))
    return Response({
        "session": session_payload(s),
        "answered": s.position,
        "correct": s.correct_count,
        "wrong": s.position - s.correct_count,
        "percent": s.percent,
        "mistakes": [{"text": i.question.text, "correct": i.question.correct,
                      "explanation": explanation_of(i.question)} for i in missed],
    })


# ------------------------------------------------------------------ natijalar va reyting

PERIODS = ("day", "week", "month", "all")
TOP_N = 50


def period_start(period):
    """Davr boshi (Toshkent vaqti bilan): bugun 00:00, shu hafta dushanbasi, shu oyning 1-kuni."""
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        return day
    if period == "week":
        return day - timedelta(days=day.weekday())
    if period == "month":
        return day.replace(day=1)
    return None


def answered_items(start=None):
    qs = SessionQuestion.objects.filter(answered=True)
    return qs.filter(answered_at__gte=start) if start else qs


@api_view(["GET"])
def leaderboard(request):
    """Foydalanuvchilar reytingi: tanlangan davrda nechta savolga javob bergani bo'yicha."""
    period = request.query_params.get("period", "week")
    if period not in PERIODS:
        period = "week"
    rows = list(answered_items(period_start(period))
                .filter(session__user__is_blocked=False)
                .values("session__user")
                .annotate(answered=Count("id"), correct=Count("id", filter=Q(first_try_correct=True)))
                .order_by("-answered", "-correct", "session__user"))
    names = {u.id: u.display_name for u in
             TelegramUser.objects.filter(id__in=[r["session__user"] for r in rows])}

    def entry(rank, r):
        uid = r["session__user"]
        return {"rank": rank, "name": names.get(uid) or "Foydalanuvchi", "answered": r["answered"],
                "correct": r["correct"], "percent": round(100 * r["correct"] / r["answered"]),
                "me": uid == request.user.id}

    ranked = [entry(i, r) for i, r in enumerate(rows, 1)]
    return Response({
        "period": period,
        "users": len(ranked),
        "top": ranked[:TOP_N],
        "me": next((e for e in ranked if e["me"]), None),
    })


@api_view(["GET"])
def my_stats(request):
    """Foydalanuvchining o'z natijalari: umumiy ko'rsatkichlar va oxirgi testlar."""
    user = request.user
    mine = SessionQuestion.objects.filter(session__user=user, answered=True)
    correct = Count("id", filter=Q(first_try_correct=True))

    def summary(start):
        a = (mine.filter(answered_at__gte=start) if start else mine).aggregate(answered=Count("id"), correct=correct)
        a["percent"] = round(100 * a["correct"] / a["answered"]) if a["answered"] else 0
        return a

    sessions = QuizSession.objects.filter(user=user, position__gt=0)
    recent = sessions.select_related("topic").order_by("-started_at")[:20]
    return Response({
        "name": user.display_name,
        "today": summary(period_start("day")),
        "week": summary(period_start("week")),
        "month": summary(period_start("month")),
        "all": summary(None),
        "tests": sessions.count(),
        "recent": [{
            "id": s.id, "title": s.title, "mode": s.mode, "answered": s.position, "total": s.total,
            "correct": s.correct_count, "percent": s.percent, "done": s.is_complete,
            "active": s.finished_at is None,
            "date": timezone.localtime(s.finished_at or s.started_at).isoformat(),
        } for s in recent],
    })
