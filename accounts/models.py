from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('university', 'University'),
        ('recruiter', 'Recruiter'),
    ]

    APPROVAL_CHOICES = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
    ]

    email = models.EmailField(
        unique=True,
        help_text=_('Email address (used as username)')
    )

    full_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Full name')
    )

    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_('Gender')
    )

    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_('Phone number')
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        help_text=_('User role in the system')
    )
    organization_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Company or institution name for recruiter/university accounts')
    )
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='approved',
        help_text=_('Approval workflow state for privileged accounts')
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the account was approved')
    )
    approval_notes = models.TextField(
        null=True,
        blank=True,
        help_text=_('Admin notes for approval or rejection')
    )
    profile_verified = models.BooleanField(
        default=False,
        help_text=_('Profile verified after AI interview completion')
    )

    # Student-specific fields
    college = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_('College/University name')
    )
    course = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Course name')
    )
    branch = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_('Branch or specialization')
    )
    year_of_study = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_('Year of study')
    )
    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('CGPA (Cumulative Grade Point Average)')
    )
    student_skills = models.TextField(
        null=True,
        blank=True,
        help_text=_('Comma-separated list of skills')
    )
    github_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('GitHub profile URL')
    )
    leetcode_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('LeetCode profile URL')
    )
    linkedin_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('LinkedIn profile URL')
    )
    linkedin_headline = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_('LinkedIn headline')
    )
    linkedin_about = models.TextField(
        null=True,
        blank=True,
        help_text=_('LinkedIn about summary')
    )
    linkedin_experience_count = models.IntegerField(
        blank=True,
        null=True,
        help_text=_('LinkedIn experience count')
    )
    linkedin_skill_count = models.IntegerField(
        blank=True,
        null=True,
        help_text=_('LinkedIn skills count')
    )
    linkedin_cert_count = models.IntegerField(
        blank=True,
        null=True,
        help_text=_('LinkedIn certifications count')
    )
    codechef_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('CodeChef profile URL')
    )
    hackerrank_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('HackerRank profile URL')
    )
    codeforces_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('Codeforces profile URL')
    )
    gfg_link = models.URLField(
        null=True,
        blank=True,
        help_text=_('GeeksforGeeks profile URL')
    )

    github_stats = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Cached GitHub analysis data')
    )
    leetcode_stats = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Cached LeetCode analysis data')
    )
    linkedin_stats = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Cached LinkedIn analysis data')
    )
    last_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time coding platforms were analyzed')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f"{self.username} ({self.role})"
