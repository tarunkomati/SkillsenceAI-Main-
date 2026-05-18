from rest_framework import serializers
from .models import Skill, Activity, ScoreCard, VerificationStep

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'level', 'score', 'verified', 'created_at', 'updated_at']

class ActivitySerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'activity_type', 'title', 'description', 'status', 'created_at', 'completed_at', 'time_ago']

    def get_time_ago(self, obj):
        from django.utils.timesince import timesince
        if obj.completed_at:
            return timesince(obj.completed_at)
        return timesince(obj.created_at)

class ScoreCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreCard
        fields = ['id', 'score_type', 'score', 'change', 'updated_at']

class VerificationStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationStep
        fields = ['id', 'step_type', 'title', 'status', 'completed_at', 'created_at']
