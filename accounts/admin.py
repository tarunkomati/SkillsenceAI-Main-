from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('id',)
    list_display = (
        'email',
        'username',
        'role',
        'approval_status',
        'organization_name',
        'full_name',
        'profile_verified',
        'is_staff',
    )
    list_filter = ('role', 'approval_status', 'profile_verified', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'username', 'full_name', 'organization_name', 'college', 'course', 'branch')
    actions = ('approve_accounts', 'mark_pending', 'reject_accounts')

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Profile',
            {
                'fields': (
                    'role',
                    'organization_name',
                    'approval_status',
                    'approved_at',
                    'approval_notes',
                    'full_name',
                    'profile_verified',
                    'gender',
                    'phone_number',
                    'college',
                    'course',
                    'branch',
                    'year_of_study',
                    'cgpa',
                    'student_skills',
                )
            },
        ),
        (
            'Links',
            {
                'fields': (
                    'github_link',
                    'leetcode_link',
                    'linkedin_link',
                    'codechef_link',
                    'hackerrank_link',
                    'codeforces_link',
                    'gfg_link',
                )
            },
        ),
        (
            'LinkedIn Snapshot',
            {
                'fields': (
                    'linkedin_headline',
                    'linkedin_about',
                    'linkedin_experience_count',
                    'linkedin_skill_count',
                    'linkedin_cert_count',
                )
            },
        ),
        (
            'Cached Analysis',
            {
                'fields': (
                    'github_stats',
                    'leetcode_stats',
                    'linkedin_stats',
                    'last_analyzed_at',
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            'Role',
            {
                'fields': ('email', 'role', 'organization_name', 'approval_status', 'full_name'),
            },
        ),
    )

    @admin.action(description='Approve selected accounts')
    def approve_accounts(self, request, queryset):
        queryset.update(approval_status='approved', approved_at=timezone.now())

    @admin.action(description='Mark selected accounts pending')
    def mark_pending(self, request, queryset):
        queryset.update(approval_status='pending', approved_at=None)

    @admin.action(description='Reject selected accounts')
    def reject_accounts(self, request, queryset):
        queryset.update(approval_status='rejected', approved_at=None)
