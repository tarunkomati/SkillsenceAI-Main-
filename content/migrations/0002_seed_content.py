from django.db import migrations


def seed_content(apps, schema_editor):
    ContentBlock = apps.get_model('content', 'ContentBlock')

    defaults = {
        'hero': {
            'badge_text': 'AI-Powered Skill Verification',
            'title': 'Discover Real Skills.',
            'highlight': 'Verify True Talent.',
            'subtitle': 'Multimodal AI extracts, verifies, and authenticates real student skills from code, documents, videos, and interviews.',
            'stats': [
                {'value': '50K+', 'label': 'Students Verified'},
                {'value': '99.2%', 'label': 'Accuracy Rate'},
                {'value': '500+', 'label': 'Partner Companies'},
            ],
        },
        'features': [
            {
                'icon': 'Layers',
                'title': 'Multimodal Skill Extraction',
                'description': 'AI analyzes code, documents, videos, and interviews to build a complete skill profile.',
                'gradient': 'from-primary to-primary/50',
            },
            {
                'icon': 'ShieldCheck',
                'title': 'Fraud Detection',
                'description': 'Advanced algorithms detect copied code, plagiarized content, and inauthentic claims.',
                'gradient': 'from-accent to-accent/50',
            },
            {
                'icon': 'Mic',
                'title': 'AI Interview Simulator',
                'description': 'Practice with AI interviewers that evaluate communication, confidence, and technical depth.',
                'gradient': 'from-primary to-accent',
            },
            {
                'icon': 'FileCheck',
                'title': 'Verified Skill Passport',
                'description': 'Digital credentials with QR verification and evidence-backed skill attestations.',
                'gradient': 'from-accent to-primary',
            },
            {
                'icon': 'Target',
                'title': 'Placement Readiness Score',
                'description': 'AI calculates your job-readiness based on verified skills and industry requirements.',
                'gradient': 'from-primary to-primary/50',
            },
            {
                'icon': 'Sparkles',
                'title': 'AI Mentor Twin',
                'description': 'Personalized improvement roadmap based on your skill gaps and career goals.',
                'gradient': 'from-accent to-accent/50',
            },
        ],
        'data_types': [
            {'icon': 'Code', 'label': 'Code Analysis', 'color': 'text-primary'},
            {'icon': 'FileText', 'label': 'Document Parsing', 'color': 'text-accent'},
            {'icon': 'Video', 'label': 'Video Analysis', 'color': 'text-primary'},
            {'icon': 'TrendingUp', 'label': 'Performance Tracking', 'color': 'text-accent'},
        ],
        'user_types': [
            {
                'icon': 'GraduationCap',
                'title': 'For Students',
                'description': 'Secure registration & login with Email. Upload projects and proof for AI verification.',
                'features': [
                    'Upload Projects & Evidence',
                    'Code & GitHub Verification',
                    'AI Authenticity Checks',
                    'Skill Scores & Reports',
                    'Verified Badges',
                    'Shareable Passport',
                ],
                'cta': 'Student Login',
                'href': '/student/start',
                'gradient': 'from-primary to-primary/60',
            },
            {
                'icon': 'Building2',
                'title': 'For Universities',
                'description': 'Institution account registration for student identity verification and bulk assessments.',
                'features': [
                    'Student Identity Verification',
                    'Bulk Upload & Verification',
                    'AI Evaluation Reports',
                    'Approve/Reject Authenticity',
                    'Student Records & Analytics',
                    'Trust & Verification Statistics',
                ],
                'cta': 'University Login',
                'href': '/university',
                'gradient': 'from-primary to-accent',
            },
            {
                'icon': 'Briefcase',
                'title': 'For Recruiters',
                'description': 'Search verified candidates and access authentic skill evidence instantly.',
                'features': [
                    'Search by Verification ID/Link',
                    'View Verified Projects & Skills',
                    'Authenticity & Trust Scores',
                    'Candidate Shortlisting',
                    'Skill-Based Filtering',
                    'Verification Insights',
                ],
                'cta': 'Recruiter Login',
                'href': '/recruiter',
                'gradient': 'from-accent to-accent/60',
            },
        ],
        'testimonials': [
            {
                'name': 'Priya Sharma',
                'role': 'Computer Science Student',
                'company': 'IIT Delhi',
                'image': 'https://i.pravatar.cc/100?img=1',
                'content': 'SkillVerify helped me showcase my actual coding abilities. I got 3 interview calls within a week of sharing my verified passport!',
                'rating': 5,
            },
            {
                'name': 'Rajesh Kumar',
                'role': 'Senior Recruiter',
                'company': 'Google India',
                'image': 'https://i.pravatar.cc/100?img=3',
                'content': 'We reduced our screening time by 60%. The verified skill badges give us confidence in candidate capabilities before interviews.',
                'rating': 5,
            },
            {
                'name': 'Dr. Ananya Patel',
                'role': 'Placement Director',
                'company': 'NIT Trichy',
                'image': 'https://i.pravatar.cc/100?img=5',
                'content': 'The batch analytics helped us identify skill gaps early. Our placement rate improved by 25% this year.',
                'rating': 5,
            },
        ],
        'how_it_works': [
            {
                'icon': 'Upload',
                'title': 'Upload Your Work',
                'description': 'Submit code, documents, project videos, or take AI interviews.',
                'color': 'primary',
            },
            {
                'icon': 'Brain',
                'title': 'Multimodal AI Analysis',
                'description': 'AI analyzes patterns, detects authenticity, and extracts real skills.',
                'color': 'accent',
            },
            {
                'icon': 'BadgeCheck',
                'title': 'Verified Skill Passport',
                'description': 'Receive a tamper-proof digital credential with evidence-backed skills.',
                'color': 'primary',
            },
        ],
        'about': {
            'title': 'Revolutionizing Skill Verification with AI Technology',
            'subtitle': "We're bridging the gap between education and employment by providing verifiable proof of skills that employers can trust.",
            'items': [
                {
                    'icon': 'Users',
                    'title': 'For Students',
                    'description': 'Showcase your real skills with AI-verified credentials that stand out to employers.',
                },
                {
                    'icon': 'Target',
                    'title': 'For Employers',
                    'description': 'Find truly skilled candidates with confidence using our advanced verification system.',
                },
                {
                    'icon': 'Award',
                    'title': 'For Universities',
                    'description': 'Partner with us to provide your students with industry-recognized skill verification.',
                },
                {
                    'icon': 'TrendingUp',
                    'title': 'For Recruiters',
                    'description': 'Streamline your hiring process with reliable, AI-powered skill assessments.',
                },
            ],
        },
        'contact': {
            'email': 'skillssenceai@gmail.com',
            'phone': '+91 6300063289',
            'headline': 'Get in Touch with Skillsence AI',
            'subtext': 'Have questions or need assistance? We are here to help you on your journey to verified skills.',
        },
    }

    for key, payload in defaults.items():
        ContentBlock.objects.update_or_create(
            key=key,
            defaults={'payload': payload},
        )


def unseed_content(apps, schema_editor):
    ContentBlock = apps.get_model('content', 'ContentBlock')
    ContentBlock.objects.filter(key__in=[
        'hero',
        'features',
        'data_types',
        'user_types',
        'testimonials',
        'how_it_works',
        'about',
        'contact',
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_content, unseed_content),
    ]
