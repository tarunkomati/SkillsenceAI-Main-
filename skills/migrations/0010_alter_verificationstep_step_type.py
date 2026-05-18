from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0009_rename_skills_repor_repo_ur_7c38d7_idx_skills_repo_repo_ur_35b32f_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verificationstep',
            name='step_type',
            field=models.CharField(
                choices=[
                    ('profile_created', 'Profile Created'),
                    ('first_code_upload', 'First Code Upload'),
                    ('skills_extracted', 'Skills Extracted'),
                    ('ai_interview_completed', 'AI Interview Completed'),
                    ('skill_verification', 'Skill Verification'),
                    ('document_verification', 'Document Verification'),
                    ('skill_passport_ready', 'Skill Passport Ready'),
                ],
                max_length=30,
            ),
        ),
    ]
