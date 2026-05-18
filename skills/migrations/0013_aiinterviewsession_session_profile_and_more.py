from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0012_recruitercandidatepipeline_assignee_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiinterviewsession",
            name="session_profile",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="aiinterviewsession",
            name="summary",
            field=models.JSONField(default=dict),
        ),
    ]
