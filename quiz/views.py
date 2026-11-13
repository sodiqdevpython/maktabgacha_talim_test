import random
from collections import defaultdict
from pathlib import Path

from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Question, QuizSession, SessionQuestion, Topic
from .serializers import AnswerSerializer, StartSessionSerializer

STATIC_DIR = Path(__file__).resolve().parent / "static" / "quiz"


@xframe_options_exempt  # Telegram Web (brauzer) ilovani iframe ichida ochadi
def index(request):
    version = max(int(p.stat().st_mtime) for p in STATIC_DIR.iterdir())
    return render(request, "quiz/index.html", {"v": version})


# ------------------------------------------------------------------ yordamchilar


def session_payload(s):
    return {"id": s.id, "mode": s.mode, "total": s.total, "position": s.position,
            "title": s.title, "topic": None if s.is_mixed else s.topic_id, "mixed": s.is_mixed,
            "done": s.is_complete}


def question_payload(s):
    """Joriy savol. To'g'ri javob qaysi ekani brauzerga HECH QACHON yuborilmaydi."""
    if s.is_complete:
        return None
    item = s.items.select_related("question__topic").get(index=s.position)
    q = item.question
    opts = q.options
    return {
        "index": item.index,
        "text": q.text,
        "options": [opts[int(c)] for c in item.order],
        "tried": [int(c) for c in item.tried],
        "topic": f"{q.topic.code}. {q.topic.title}" if s.is_mixed else "",
    }


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


@api_view(["POST"])
def answer(request, pk):
    ser = AnswerSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    index, position = ser.validated_data["index"], ser.validated_data["position"]

    with transaction.atomic():
        s = get_object_or_404(QuizSession.objects.select_for_update().select_related("topic"),
                              pk=pk, user=request.user)
        if s.is_complete or s.finished_at or index != s.position:
            # Eskirgan so'rov (masalan ikki marta bosilgan) — joriy holatni qaytaramiz
            return Response({"stale": True, "session": session_payload(s), "question": question_payload(s)})

        item = s.items.select_related("question").get(index=index)
        is_correct = item.order[position] == "0"
        correct_position = None
        advance = False

        if s.mode == QuizSession.STRICT:
            if is_correct:
                item.first_try_correct = item.tried == ""
                advance = True
            elif str(position) not in item.tried:
                item.tried += str(position)
        else:  # imtihon: bitta urinish
            item.first_try_correct = is_correct
            advance = True
            if not is_correct:
                item.tried = str(position)
                correct_position = item.order.index("0")

        if advance:
            item.answered = True
            s.position += 1
            if item.first_try_correct:
                s.correct_count += 1
            if s.is_complete:
                s.finished_at = timezone.now()
            s.save(update_fields=["position", "correct_count", "finished_at"])
        item.save(update_fields=["tried", "answered", "first_try_correct"])

    return Response({
        "correct": is_correct,
        "correct_position": correct_position,
        "advanced": advance,
        "session": session_payload(s),
        "question": question_payload(s) if advance else None,
    })


@api_view(["GET"])
def result(request, pk):
    s = get_object_or_404(QuizSession.objects.select_related("topic"), pk=pk, user=request.user)
    missed = (s.items.filter(answered=True, first_try_correct=False).select_related("question"))
    return Response({
        "session": session_payload(s),
        "answered": s.position,
        "correct": s.correct_count,
        "wrong": s.position - s.correct_count,
        "percent": s.percent,
        "mistakes": [{"text": i.question.text, "correct": i.question.correct} for i in missed],
    })
