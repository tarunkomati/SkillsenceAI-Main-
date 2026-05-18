from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0007_alter_verificationstep_step_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="RepoFileSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("repo_url", models.URLField()),
                ("path", models.TextField()),
                ("sha", models.CharField(max_length=64)),
                ("content", models.TextField()),
                ("size", models.IntegerField(default=0)),
                ("lines", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="repo_file_snapshots", to="accounts.user")),
            ],
            options={
                "verbose_name": "Repo File Snapshot",
                "verbose_name_plural": "Repo File Snapshots",
                "ordering": ["-created_at"],
                "unique_together": {("user", "repo_url", "path", "sha")},
            },
        ),
        migrations.AddIndex(
            model_name="repofilesnapshot",
            index=models.Index(fields=["repo_url", "path"], name="skills_repor_repo_ur_7c38d7_idx"),
        ),
        migrations.AddIndex(
            model_name="repofilesnapshot",
            index=models.Index(fields=["sha"], name="skills_repor_sha_0e48c8_idx"),
        ),
    ]
