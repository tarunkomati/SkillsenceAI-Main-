from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0005_projectsubmission_mediaupload_codeanalysisreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiinterviewsession",
            name="questions",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="aiinterviewsession",
            name="answers",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="aiinterviewsession",
            name="current_index",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="aiinterviewsession",
            name="score",
            field=models.IntegerField(default=0),
        ),
    ]
