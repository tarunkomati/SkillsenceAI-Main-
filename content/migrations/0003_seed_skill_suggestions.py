from django.db import migrations


def seed_skill_suggestions(apps, schema_editor):
    ContentBlock = apps.get_model('content', 'ContentBlock')
    ContentBlock.objects.update_or_create(
        key='skill_suggestions',
        defaults={
            'payload': [
                'Python',
                'Java',
                'C',
                'C++',
                'JavaScript',
                'TypeScript',
                'React',
                'Node.js',
                'Django',
                'Flask',
                'SQL',
                'MongoDB',
                'AWS',
                'Docker',
                'Kubernetes',
                'Git',
                'Data Structures',
                'Algorithms',
                'Machine Learning',
                'Deep Learning',
                'UI/UX',
            ]
        },
    )


def unseed_skill_suggestions(apps, schema_editor):
    ContentBlock = apps.get_model('content', 'ContentBlock')
    ContentBlock.objects.filter(key='skill_suggestions').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0002_seed_content'),
    ]

    operations = [
        migrations.RunPython(seed_skill_suggestions, unseed_skill_suggestions),
    ]
