from django.contrib import admin

from .models import (
    Activity,
    AIInterviewSession,
    CodeAnalysisReport,
    Document,
    InterviewSchedule,
    InterventionRecord,
    MediaUpload,
    Notification,
    PlacementDrive,
    ProjectSubmission,
    RecruiterCandidatePipeline,
    RecruiterJob,
    RecruiterSavedSearch,
    RepoFileSnapshot,
    ScoreCard,
    ScoreSnapshot,
    Skill,
    UniversityBatchUpload,
    VerificationStep,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'level', 'score', 'verified', 'updated_at')
    list_filter = ('verified', 'level')
    search_fields = ('name', 'user__email', 'user__username', 'user__full_name')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'activity_type', 'status', 'created_at')
    list_filter = ('activity_type', 'status')
    search_fields = ('title', 'user__email', 'user__username')


@admin.register(ScoreCard)
class ScoreCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'score_type', 'score', 'change', 'updated_at')
    list_filter = ('score_type',)
    search_fields = ('user__email', 'user__username')


@admin.register(ScoreSnapshot)
class ScoreSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'recorded_on', 'created_at')
    search_fields = ('user__email', 'user__username')


@admin.register(VerificationStep)
class VerificationStepAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'step_type', 'status', 'created_at')
    list_filter = ('step_type', 'status')
    search_fields = ('user__email', 'user__username', 'title')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'doc_type', 'status', 'created_at')
    list_filter = ('doc_type', 'status')
    search_fields = ('title', 'user__email', 'user__username')


@admin.register(AIInterviewSession)
class AIInterviewSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'score', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'user__username')


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'repo_url', 'user__email', 'user__username')


@admin.register(CodeAnalysisReport)
class CodeAnalysisReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'repo_url', 'score', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('repo_url', 'user__email', 'user__username')


@admin.register(RepoFileSnapshot)
class RepoFileSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'repo_url', 'path', 'sha', 'created_at')
    search_fields = ('repo_url', 'path', 'sha', 'user__email', 'user__username')


@admin.register(MediaUpload)
class MediaUploadAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'media_type', 'status', 'created_at')
    list_filter = ('media_type', 'status')
    search_fields = ('title', 'user__email', 'user__username')


@admin.register(RecruiterJob)
class RecruiterJobAdmin(admin.ModelAdmin):
    list_display = ('title', 'recruiter', 'status', 'min_ready_score', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title', 'recruiter__email', 'recruiter__username')


@admin.register(RecruiterCandidatePipeline)
class RecruiterCandidatePipelineAdmin(admin.ModelAdmin):
    list_display = ('recruiter', 'candidate', 'job', 'status', 'match_score', 'follow_up_at', 'updated_at')
    list_filter = ('status',)
    search_fields = (
        'recruiter__email',
        'recruiter__username',
        'candidate__email',
        'candidate__username',
        'job__title',
    )


@admin.register(RecruiterSavedSearch)
class RecruiterSavedSearchAdmin(admin.ModelAdmin):
    list_display = ('name', 'recruiter', 'updated_at')
    search_fields = ('name', 'query', 'recruiter__email', 'recruiter__username')


@admin.register(UniversityBatchUpload)
class UniversityBatchUploadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'university', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('filename', 'university__email', 'university__username')


@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = ('title', 'recruiter', 'candidate', 'job', 'scheduled_at', 'status')
    list_filter = ('status',)
    search_fields = ('title', 'recruiter__email', 'candidate__email', 'job__title')


@admin.register(InterventionRecord)
class InterventionRecordAdmin(admin.ModelAdmin):
    list_display = ('university', 'student', 'status', 'priority', 'updated_at')
    list_filter = ('status', 'priority')
    search_fields = (
        'university__email',
        'university__username',
        'student__email',
        'student__username',
        'student__full_name',
    )


@admin.register(PlacementDrive)
class PlacementDriveAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'role_title', 'university', 'minimum_ready_score', 'status', 'scheduled_on')
    list_filter = ('status',)
    search_fields = ('company_name', 'role_title', 'university__email', 'university__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'read_at', 'created_at')
    list_filter = ('category', 'read_at')
    search_fields = ('title', 'message', 'user__email', 'user__username')
