from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Skill(models.Model):
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='beginner')
    score = models.IntegerField(default=0, help_text='Skill score out of 100')
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']
        verbose_name = _('Skill')
        verbose_name_plural = _('Skills')

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.level})"

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('code_upload', 'Code Upload'),
        ('document_upload', 'Document Upload'),
        ('video_interview', 'Video Interview'),
        ('skill_verification', 'Skill Verification'),
        ('badge_earned', 'Badge Earned'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ScoreCard(models.Model):
    SCORE_TYPES = [
        ('coding_skill_index', 'Coding Skill Index'),
        ('communication_score', 'Communication Score'),
        ('authenticity_score', 'Authenticity Score'),
        ('placement_ready', 'Placement Ready'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scorecards')
    score_type = models.CharField(max_length=30, choices=SCORE_TYPES)
    score = models.IntegerField(default=0, help_text='Score out of 100')
    change = models.IntegerField(default=0, help_text='Change from previous score')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'score_type']
        verbose_name = _('Score Card')
        verbose_name_plural = _('Score Cards')

    def __str__(self):
        return f"{self.user.username} - {self.score_type}: {self.score}"


class ScoreSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='score_snapshots')
    recorded_on = models.DateField()
    scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'recorded_on']
        verbose_name = _('Score Snapshot')
        verbose_name_plural = _('Score Snapshots')
        ordering = ['recorded_on']

    def __str__(self):
        return f"{self.user.username} - {self.recorded_on}"

class VerificationStep(models.Model):
    STEP_TYPES = [
        ('profile_created', 'Profile Created'),
        ('first_code_upload', 'First Code Upload'),
        ('skills_extracted', 'Skills Extracted'),
        ('ai_interview_completed', 'AI Interview Completed'),
        ('skill_verification', 'Skill Verification'),
        ('document_verification', 'Document Verification'),
        ('skill_passport_ready', 'Skill Passport Ready'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('current', 'Current'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_steps')
    step_type = models.CharField(max_length=30, choices=STEP_TYPES)
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'step_type']
        verbose_name = _('Verification Step')
        verbose_name_plural = _('Verification Steps')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('reviewing', 'Reviewing'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class AIInterviewSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_interviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    transcript = models.JSONField(default=list)
    feedback = models.JSONField(default=list)
    metrics = models.JSONField(default=list)
    tips = models.JSONField(default=list)
    questions = models.JSONField(default=list)
    answers = models.JSONField(default=list)
    current_index = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    session_profile = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = _('AI Interview Session')
        verbose_name_plural = _('AI Interview Sessions')

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class ProjectSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing', 'Reviewing'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    title = models.CharField(max_length=200)
    repo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Project Submission')
        verbose_name_plural = _('Project Submissions')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class CodeAnalysisReport(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_analysis_reports')
    repo_url = models.URLField()
    summary = models.TextField(blank=True)
    score = models.IntegerField(default=0)
    metrics = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Code Analysis Report')
        verbose_name_plural = _('Code Analysis Reports')

    def __str__(self):
        return f"{self.user.username} - {self.repo_url}"


class RepoFileSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repo_file_snapshots')
    repo_url = models.URLField()
    path = models.TextField()
    sha = models.CharField(max_length=64)
    content = models.TextField()
    size = models.IntegerField(default=0)
    lines = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Repo File Snapshot')
        verbose_name_plural = _('Repo File Snapshots')
        unique_together = ['user', 'repo_url', 'path', 'sha']
        indexes = [
            models.Index(fields=['repo_url', 'path']),
            models.Index(fields=['sha']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.path}"


class MediaUpload(models.Model):
    MEDIA_TYPES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_uploads')
    title = models.CharField(max_length=200)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    file = models.FileField(upload_to='media/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Media Upload')
        verbose_name_plural = _('Media Uploads')

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class RecruiterJob(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
    ]

    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recruiter_jobs')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    min_ready_score = models.IntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Recruiter Job')
        verbose_name_plural = _('Recruiter Jobs')

    def __str__(self):
        return f"{self.title} ({self.recruiter.email})"


class RecruiterCandidatePipeline(models.Model):
    STATUS_CHOICES = [
        ('sourced', 'Sourced'),
        ('shortlisted', 'Shortlisted'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Offered'),
        ('rejected', 'Rejected'),
    ]

    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_pipeline_entries')
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recruiter_pipeline_entries')
    job = models.ForeignKey(
        RecruiterJob,
        on_delete=models.CASCADE,
        related_name='pipeline_entries',
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sourced')
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    match_score = models.IntegerField(default=0)
    assignee_name = models.CharField(max_length=120, blank=True)
    next_step = models.CharField(max_length=200, blank=True)
    rejection_reason = models.CharField(max_length=200, blank=True)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Recruiter Candidate Pipeline')
        verbose_name_plural = _('Recruiter Candidate Pipelines')
        constraints = [
            models.UniqueConstraint(
                fields=['recruiter', 'candidate', 'job'],
                name='unique_recruiter_candidate_job_pipeline',
            ),
        ]

    def __str__(self):
        candidate_name = self.candidate.full_name or self.candidate.username
        return f"{self.recruiter.email} -> {candidate_name} ({self.status})"


class RecruiterSavedSearch(models.Model):
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=120)
    query = models.CharField(max_length=200, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Recruiter Saved Search')
        verbose_name_plural = _('Recruiter Saved Searches')

    def __str__(self):
        return f"{self.recruiter.email} - {self.name}"


class UniversityBatchUpload(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    university = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_uploads')
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='batch_uploads/', null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('University Batch Upload')
        verbose_name_plural = _('University Batch Uploads')

    def __str__(self):
        return f"{self.university.email} - {self.filename}"


class InterviewSchedule(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_interviews')
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_interviews')
    job = models.ForeignKey(
        RecruiterJob,
        on_delete=models.SET_NULL,
        related_name='interview_schedules',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        verbose_name = _('Interview Schedule')
        verbose_name_plural = _('Interview Schedules')

    def __str__(self):
        return f"{self.title} - {self.candidate.email}"


class InterventionRecord(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('escalated', 'Escalated'),
    ]

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    university = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intervention_records')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_intervention_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    note = models.TextField(blank=True)
    recommended_action = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Intervention Record')
        verbose_name_plural = _('Intervention Records')
        constraints = [
            models.UniqueConstraint(
                fields=['university', 'student'],
                name='unique_university_student_intervention',
            ),
        ]

    def __str__(self):
        student_name = self.student.full_name or self.student.username
        return f"{self.university.email} -> {student_name} ({self.status})"


class PlacementDrive(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('live', 'Live'),
        ('closed', 'Closed'),
    ]

    university = models.ForeignKey(User, on_delete=models.CASCADE, related_name='placement_drives')
    company_name = models.CharField(max_length=200)
    role_title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_branches = models.JSONField(default=list, blank=True)
    target_courses = models.JSONField(default=list, blank=True)
    minimum_ready_score = models.IntegerField(default=65)
    scheduled_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Placement Drive')
        verbose_name_plural = _('Placement Drives')

    def __str__(self):
        return f"{self.company_name} - {self.role_title}"


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('system', 'System'),
        ('student', 'Student'),
        ('recruiter', 'Recruiter'),
        ('university', 'University'),
        ('verification', 'Verification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    link = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        indexes = [
            models.Index(fields=['user', 'read_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
