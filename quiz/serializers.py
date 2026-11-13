from rest_framework import serializers

from .models import QuizSession, Topic


class StartSessionSerializer(serializers.Serializer):
    """topic berilmasa — barcha mavzulardan aralash test."""
    topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.filter(is_active=True),
                                               required=False, allow_null=True)
    mode = serializers.ChoiceField(choices=[QuizSession.STRICT, QuizSession.EXAM])
    count = serializers.IntegerField(min_value=1, max_value=5000, required=False, allow_null=True)


class AnswerSerializer(serializers.Serializer):
    index = serializers.IntegerField(min_value=0)      # nechanchi savolga javob berilyapti
    position = serializers.IntegerField(min_value=0, max_value=3)  # ekrandagi variant o'rni (A=0 ... D=3)
