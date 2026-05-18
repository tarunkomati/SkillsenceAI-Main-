from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Create or update initial superuser, recruiter, and university accounts from environment variables."

    def handle(self, *args, **options):
        user_model = get_user_model()
        self._bootstrap_superuser(user_model)
        self._bootstrap_role_user(
            user_model,
            role="recruiter",
            email_env="BOOTSTRAP_RECRUITER_EMAIL",
            username_env="BOOTSTRAP_RECRUITER_USERNAME",
            password_env="BOOTSTRAP_RECRUITER_PASSWORD",
            organization_env="BOOTSTRAP_RECRUITER_ORGANIZATION",
            default_organization="SkillSense Recruiting",
        )
        self._bootstrap_role_user(
            user_model,
            role="university",
            email_env="BOOTSTRAP_UNIVERSITY_EMAIL",
            username_env="BOOTSTRAP_UNIVERSITY_USERNAME",
            password_env="BOOTSTRAP_UNIVERSITY_PASSWORD",
            organization_env="BOOTSTRAP_UNIVERSITY_ORGANIZATION",
            default_organization="SkillSense University",
        )

    def _bootstrap_superuser(self, user_model):
        email = self._env("DJANGO_SUPERUSER_EMAIL")
        username = self._env("DJANGO_SUPERUSER_USERNAME")
        password = self._env("DJANGO_SUPERUSER_PASSWORD")
        if not (email and username and password):
            self.stdout.write("bootstrap_initial_users: superuser env vars not fully set, skipping.")
            return

        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "role": "student",
                "approval_status": "approved",
                "approved_at": timezone.now(),
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.username = username
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.approval_status = "approved"
        user.approved_at = user.approved_at or timezone.now()
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"bootstrap_initial_users: {'created' if created else 'updated'} superuser {email}"
            )
        )

    def _bootstrap_role_user(
        self,
        user_model,
        role,
        email_env,
        username_env,
        password_env,
        organization_env,
        default_organization,
    ):
        email = self._env(email_env)
        username = self._env(username_env)
        password = self._env(password_env)
        organization_name = self._env(organization_env) or default_organization
        if not (email and username and password):
            self.stdout.write(f"bootstrap_initial_users: {role} env vars not fully set, skipping.")
            return

        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "role": role,
                "organization_name": organization_name,
                "approval_status": "approved",
                "approved_at": timezone.now(),
                "is_active": True,
            },
        )
        user.username = username
        user.role = role
        user.organization_name = organization_name
        user.approval_status = "approved"
        user.approved_at = user.approved_at or timezone.now()
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"bootstrap_initial_users: {'created' if created else 'updated'} {role} {email}"
            )
        )

    def _env(self, name):
        from os import environ

        value = environ.get(name, "")
        return value.strip()
