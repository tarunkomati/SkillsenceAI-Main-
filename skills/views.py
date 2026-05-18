from datetime import timedelta
import csv
import io
import math
import json
import os
import base64
import re
import textwrap
import urllib.request
import urllib.error
from urllib.parse import urlparse
import random
from django.db import transaction
from django.db.models import Avg, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.http import FileResponse, HttpResponse

from .models import (
    Skill,
    Activity,
    ScoreCard,
    VerificationStep,
    ScoreSnapshot,
    Document,
    InterviewSchedule,
    AIInterviewSession,
    CodeAnalysisReport,
    MediaUpload,
    Notification,
    PlacementDrive,
    ProjectSubmission,
    RecruiterCandidatePipeline,
    RecruiterJob,
    RecruiterSavedSearch,
    RepoFileSnapshot,
    InterventionRecord,
    UniversityBatchUpload,
)
from .serializers import (
    SkillSerializer,
    ActivitySerializer,
    ScoreCardSerializer,
    VerificationStepSerializer,
)
from accounts.models import User
from accounts.scoring import calculate_student_scores, score_breakdown, upsert_scorecards
from content.models import ContentBlock

def _bool(value):
    return bool(value and str(value).strip())


def _require_role(user, role):
    return user and getattr(user, "role", None) == role


def _score_mean(values):
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clamp_number(value, minimum=0, maximum=100):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(minimum)
    return max(minimum, min(maximum, numeric))


def _normalize_string_list(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        items = raw_value
    elif isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    items = loaded
                else:
                    items = [text]
            except json.JSONDecodeError:
                items = text.replace("\n", ",").replace(";", ",").split(",")
        else:
            items = text.replace("\n", ",").replace(";", ",").split(",")
    else:
        items = [raw_value]

    cleaned = []
    seen = set()
    for item in items:
        normalized = str(item or "").strip()
        if not normalized:
            continue
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        cleaned.append(normalized)
    return cleaned


def _tokenize_match_text(text):
    if not text:
        return set()
    tokens = re.findall(r"[a-z0-9+#.]{2,}", str(text).lower())
    stopwords = {
        "and", "the", "for", "with", "from", "that", "this", "have", "will", "your",
        "role", "team", "work", "years", "year", "using", "build", "built", "into",
        "about", "need", "plus", "more", "must", "able", "good", "strong", "skills",
        "experience", "candidate", "student", "project", "projects", "company",
    }
    return {token for token in tokens if token not in stopwords}


def _candidate_match_corpus(student, candidate_payload=None):
    payload = candidate_payload or _student_summary_payload(student)
    parts = [
        student.student_skills or "",
        student.linkedin_headline or "",
        student.linkedin_about or "",
        " ".join(skill.get("name", "") for skill in payload.get("skills", [])),
        " ".join(payload.get("highlights", [])),
    ]
    latest_report = student.code_analysis_reports.filter(status='completed').first()
    if latest_report:
        parts.extend([latest_report.summary or "", latest_report.repo_url or ""])
    latest_submission = student.submissions.first()
    if latest_submission:
        parts.extend([latest_submission.title or "", latest_submission.description or "", latest_submission.repo_url or ""])
    latest_interview = student.ai_interviews.filter(status='completed').first()
    if latest_interview:
        answers = latest_interview.answers or []
        parts.extend(answer.get("answer", "") for answer in answers[:5] if isinstance(answer, dict))
    return " ".join(filter(None, parts))


def _job_tokens(job):
    return _tokenize_match_text(
        " ".join(
            [
                job.title or "",
                job.description or "",
                " ".join(_normalize_string_list(job.required_skills)),
                " ".join(_normalize_string_list(job.preferred_skills)),
            ]
        )
    )


def _semantic_overlap(job, student, candidate_payload=None):
    candidate_tokens = _tokenize_match_text(_candidate_match_corpus(student, candidate_payload))
    job_tokens = _job_tokens(job)
    if not job_tokens:
        return {
            "score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
        }
    matched = sorted(job_tokens & candidate_tokens)
    missing = sorted(job_tokens - candidate_tokens)
    score = round((len(matched) / max(1, len(job_tokens))) * 100)
    return {
        "score": score,
        "matched_keywords": matched[:8],
        "missing_keywords": missing[:8],
    }


def _create_notification(user, title, message, category="system", link="", metadata=None):
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
        link=link,
        metadata=metadata or {},
    )


def _notification_payload(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "category": notification.category,
        "link": notification.link,
        "metadata": notification.metadata or {},
        "read": bool(notification.read_at),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def _bootstrap_notifications_for_user(user):
    if Notification.objects.filter(user=user).exists():
        return

    if _require_role(user, "student"):
        _create_notification(
            user,
            "Complete your passport",
            "Add more verified evidence to strengthen your skill passport.",
            category="student",
            link="/dashboard/passport",
        )
        if not user.profile_verified:
            _create_notification(
                user,
                "Interview pending",
                "Finish the AI interview to unlock a verified profile.",
                category="verification",
                link="/dashboard/interview",
            )
        if not _latest_resume_document(user):
            _create_notification(
                user,
                "Resume builder ready",
                "Generate an ATS-friendly resume from your verified profile.",
                category="student",
                link="/dashboard/resume-builder",
            )
    elif _require_role(user, "recruiter"):
        _create_notification(
            user,
            "Create your first job brief",
            "Add a job description to rank candidates by match score.",
            category="recruiter",
            link="/recruiter/dashboard",
        )
    elif _require_role(user, "university"):
        _create_notification(
            user,
            "Import your batch",
            "Upload a cohort CSV to populate students and intervention tracking.",
            category="university",
            link="/university/dashboard",
        )


def _candidate_pipeline_payload(entry):
    if not entry:
        return None
    return {
        "status": entry.status,
        "notes": entry.notes,
        "tags": entry.tags or [],
        "match_score": int(entry.match_score or 0),
        "assignee_name": entry.assignee_name,
        "next_step": entry.next_step,
        "rejection_reason": entry.rejection_reason,
        "follow_up_at": entry.follow_up_at.isoformat() if entry.follow_up_at else None,
        "last_contacted_at": entry.last_contacted_at.isoformat() if entry.last_contacted_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _pipeline_summary_for_entries(entries):
    summary = {
        "sourced": 0,
        "shortlisted": 0,
        "interviewing": 0,
        "offered": 0,
        "rejected": 0,
    }
    for entry in entries:
        if entry.status in summary:
            summary[entry.status] += 1
    return summary


def _job_match_payload(candidate_payload, job, student=None):
    if not job:
        return {
            "score": candidate_payload.get("score", 0),
            "reasons": [],
            "matched_skills": [],
            "missing_skills": [],
            "semantic_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
        }

    candidate_skills = {
        (skill.get("name") or "").strip().lower(): skill
        for skill in candidate_payload.get("skills", [])
        if skill.get("name")
    }
    required = _normalize_string_list(job.required_skills)
    preferred = _normalize_string_list(job.preferred_skills)
    matched_required = [skill for skill in required if skill.lower() in candidate_skills]
    matched_preferred = [skill for skill in preferred if skill.lower() in candidate_skills]
    missing_required = [skill for skill in required if skill.lower() not in candidate_skills]

    required_ratio = len(matched_required) / max(1, len(required)) if required else min(
        1,
        (candidate_payload.get("scores", {}).get("coding_skill_index", 0) or 0) / 100,
    )
    preferred_ratio = len(matched_preferred) / max(1, len(preferred)) if preferred else 0.5
    ready_ratio = min(1, (candidate_payload.get("score", 0) or 0) / 100)
    min_ready_bonus = 1 if (candidate_payload.get("score", 0) or 0) >= int(job.min_ready_score or 0) else 0
    authenticity_ratio = min(
        1,
        (candidate_payload.get("scores", {}).get("authenticity_score", 0) or 0) / 100,
    )
    verified_bonus = 1 if candidate_payload.get("profile_verified") else 0
    semantic = _semantic_overlap(job, student, candidate_payload) if student else {"score": 0, "matched_keywords": [], "missing_keywords": []}
    semantic_ratio = min(1, (semantic.get("score", 0) or 0) / 100)

    match_score = round(
        min(
            100,
            (
                required_ratio * 35
                + preferred_ratio * 10
                + ready_ratio * 15
                + min_ready_bonus * 15
                + authenticity_ratio * 5
                + verified_bonus * 5
                + semantic_ratio * 15
            ),
        )
    )

    reasons = []
    if matched_required:
        reasons.append(f"Matched required skills: {', '.join(matched_required[:3])}.")
    if (candidate_payload.get("score", 0) or 0) >= int(job.min_ready_score or 0):
        reasons.append(f"Placement readiness clears the {job.min_ready_score} threshold.")
    if candidate_payload.get("profile_verified"):
        reasons.append("Profile is verification-complete.")
    if missing_required:
        reasons.append(f"Still missing: {', '.join(missing_required[:3])}.")
    if semantic.get("matched_keywords"):
        reasons.append(f"Semantic overlap detected in: {', '.join(semantic['matched_keywords'][:3])}.")

    return {
        "score": match_score,
        "reasons": reasons[:3],
        "matched_skills": matched_required,
        "missing_skills": missing_required,
        "semantic_score": semantic.get("score", 0),
        "matched_keywords": semantic.get("matched_keywords", []),
        "missing_keywords": semantic.get("missing_keywords", []),
    }


def _job_payload(job):
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "required_skills": _normalize_string_list(job.required_skills),
        "preferred_skills": _normalize_string_list(job.preferred_skills),
        "min_ready_score": int(job.min_ready_score or 0),
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _interview_schedule_payload(schedule):
    return {
        "id": schedule.id,
        "title": schedule.title,
        "candidate_id": schedule.candidate_id,
        "candidate_name": schedule.candidate.full_name or schedule.candidate.username,
        "recruiter_id": schedule.recruiter_id,
        "recruiter_name": schedule.recruiter.full_name or schedule.recruiter.username,
        "job_id": schedule.job_id,
        "job_title": schedule.job.title if schedule.job else "",
        "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else None,
        "duration_minutes": schedule.duration_minutes,
        "meeting_link": schedule.meeting_link,
        "notes": schedule.notes,
        "status": schedule.status,
    }


def _saved_search_payload(saved_search):
    return {
        "id": saved_search.id,
        "name": saved_search.name,
        "query": saved_search.query,
        "filters": saved_search.filters or {},
        "updated_at": saved_search.updated_at.isoformat() if saved_search.updated_at else None,
    }


def _batch_upload_payload(batch_upload):
    return {
        "id": batch_upload.id,
        "filename": batch_upload.filename,
        "status": batch_upload.status,
        "summary": batch_upload.summary or {},
        "created_at": batch_upload.created_at.isoformat() if batch_upload.created_at else None,
    }


def _intervention_record_payload(record):
    if not record:
        return None
    return {
        "status": record.status,
        "priority": record.priority,
        "note": record.note,
        "recommended_action": record.recommended_action,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _placement_drive_payload(drive, students=None):
    eligible_students = []
    if students is not None:
        for item in students:
            branch_match = not drive.target_branches or item.get("branch") in drive.target_branches
            course_match = not drive.target_courses or item.get("course") in drive.target_courses
            score_match = item.get("score", 0) >= int(drive.minimum_ready_score or 0)
            if branch_match and course_match and score_match:
                eligible_students.append(item)
    return {
        "id": drive.id,
        "company_name": drive.company_name,
        "role_title": drive.role_title,
        "description": drive.description,
        "target_branches": _normalize_string_list(drive.target_branches),
        "target_courses": _normalize_string_list(drive.target_courses),
        "minimum_ready_score": int(drive.minimum_ready_score or 0),
        "scheduled_on": drive.scheduled_on.isoformat() if drive.scheduled_on else None,
        "status": drive.status,
        "eligible_count": len(eligible_students),
        "top_candidates": [
            {
                "id": item["id"],
                "name": item["name"],
                "score": item["score"],
                "branch": item["branch"],
                "verification_id": item["verification_id"],
            }
            for item in sorted(eligible_students, key=lambda entry: (-entry["score"], entry["name"].lower()))[:5]
        ],
        "updated_at": drive.updated_at.isoformat() if drive.updated_at else None,
    }


def _repo_cache_enabled():
    return os.environ.get("AI_REPO_CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


def _repo_cache_max_chars():
    try:
        return int(os.environ.get("AI_REPO_CACHE_CHARS", "20000"))
    except (TypeError, ValueError):
        return 20000


def _store_repo_file_snapshot(user, repo_url, path, sha, content, size, lines):
    if not user or not _repo_cache_enabled():
        return
    max_chars = _repo_cache_max_chars()
    stored_content = content if max_chars <= 0 else (content or "")[:max_chars]
    RepoFileSnapshot.objects.update_or_create(
        user=user,
        repo_url=repo_url,
        path=path,
        sha=sha,
        defaults={
            "content": stored_content,
            "size": size or 0,
            "lines": lines or 0,
        },
    )


def _build_verification_steps(user):
    steps = []
    now = timezone.now()

    personal_complete = all([
        _bool(user.full_name),
        _bool(user.gender),
        _bool(user.phone_number),
        _bool(user.email),
    ])
    academic_complete = all([
        _bool(user.college),
        _bool(user.course),
        _bool(user.branch),
        _bool(user.year_of_study),
    ])
    skills_complete = _bool(user.student_skills)
    github_complete = _bool(user.github_link)
    leetcode_complete = _bool(user.leetcode_link)
    linkedin_profile_complete = _bool(user.linkedin_link) and any([
        _bool(user.linkedin_headline),
        _bool(user.linkedin_about),
        user.linkedin_experience_count,
        user.linkedin_skill_count,
        user.linkedin_cert_count,
    ])
    analysis_ready = user.last_analyzed_at is not None

    steps.append({
        "id": 1,
        "title": "Account created",
        "description": "Your SkillVerify account is active.",
        "status": "completed",
        "completed_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 2,
        "title": "Personal details",
        "description": "Name, gender, phone, and email.",
        "status": "completed" if personal_complete else "in_progress",
        "completed_at": user.date_joined.isoformat() if personal_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 3,
        "title": "Academic profile",
        "description": "College, course, branch, and year.",
        "status": "completed" if academic_complete else "pending",
        "completed_at": user.date_joined.isoformat() if academic_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 4,
        "title": "Skill list",
        "description": "Add the skills you want verified.",
        "status": "completed" if skills_complete else "pending",
        "completed_at": user.date_joined.isoformat() if skills_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 5,
        "title": "Connect GitHub",
        "description": "Link your GitHub to verify project activity.",
        "status": "completed" if github_complete else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if github_complete and user.last_analyzed_at else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 6,
        "title": "Connect LeetCode",
        "description": "Link LeetCode to verify problem solving.",
        "status": "completed" if leetcode_complete else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if leetcode_complete and user.last_analyzed_at else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 7,
        "title": "LinkedIn snapshot",
        "description": "Add headline, about, and experience counts.",
        "status": "completed" if linkedin_profile_complete else "pending",
        "completed_at": user.date_joined.isoformat() if linkedin_profile_complete else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    steps.append({
        "id": 8,
        "title": "Score analysis",
        "description": "Run AI scoring after linking platforms.",
        "status": "completed" if analysis_ready else "pending",
        "completed_at": user.last_analyzed_at.isoformat() if analysis_ready else None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    ai_interview_complete = AIInterviewSession.objects.filter(user=user, status='completed').exists()
    steps.append({
        "id": 9,
        "title": "AI Interview",
        "description": "Complete AI-generated interview questions.",
        "status": "completed" if ai_interview_complete else "pending",
        "completed_at": None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    skill_verification_complete = user.profile_verified or user.skills.filter(verified=True).exists()
    steps.append({
        "id": 10,
        "title": "Skill Verification",
        "description": "Verify skills based on interview performance.",
        "status": "completed" if skill_verification_complete else "pending",
        "completed_at": None,
        "created_at": user.date_joined.isoformat() if user.date_joined else now.isoformat(),
    })
    return steps


def _maybe_mark_profile_verified(user, session):
    total_questions = len(session.questions or [])
    answered = len(session.answers or [])
    if total_questions and answered >= total_questions and not user.profile_verified:
        user.profile_verified = True
        user.save(update_fields=["profile_verified"])
        _create_notification(
            user,
            "Profile verified",
            "Your AI interview is complete and your profile is now verified.",
            category="verification",
            link="/dashboard/passport",
        )


def _build_recommendations(user):
    items = []
    scores = calculate_student_scores(user) if user.role == "student" else {}
    breakdown = score_breakdown(user) if user.role == "student" else {}

    coding_score = scores.get("coding_skill_index", 0)
    communication_score = scores.get("communication_score", 0)
    authenticity_score = scores.get("authenticity_score", 0)
    placement_ready = scores.get("placement_ready", 0)
    placement_parts = breakdown.get("placement_ready", {})

    if placement_ready and placement_ready < 75:
        if placement_parts.get("coding_weighted", 0) < 35:
            items.append({
                "id": 1,
                "title": "Boost coding score for placements",
                "description": "Solve 10 medium LeetCode problems and push 2 GitHub updates.",
                "action_type": "complete_assessment",
                "priority": "high",
            "href": "/dashboard/code",
                "created_at": "",
            })
        if placement_parts.get("communication_weighted", 0) < 12:
            items.append({
                "id": 2,
                "title": "Improve communication readiness",
                "description": "Complete an AI interview session and update LinkedIn summary.",
                "action_type": "review_roadmap",
                "priority": "medium",
                "href": "/dashboard/interview",
                "created_at": "",
            })
        if placement_parts.get("cgpa_bonus", 0) < 4:
            items.append({
                "id": 4,
                "title": "Add CGPA for placement confidence",
                "description": "Update your CGPA to strengthen academic credibility.",
                "action_type": "review_roadmap",
                "priority": "low",
                "href": "/dashboard/settings",
                "created_at": "",
            })

    if coding_score and coding_score < 70:
        weak = breakdown.get("coding_skill_index", {})
        if weak.get("leetcode_solved_points", 0) < 20:
            items.append({
                "id": 5,
                "title": "Raise LeetCode consistency",
                "description": "Target 5-10 more medium problems to boost coding score.",
                "action_type": "complete_assessment",
                "priority": "high",
            "href": "/dashboard/code",
                "created_at": "",
            })
    if communication_score and communication_score < 60:
        items.append({
            "id": 7,
            "title": "Strengthen your profile story",
            "description": "Add a strong LinkedIn headline and summary.",
            "action_type": "review_roadmap",
            "priority": "medium",
            "href": "/dashboard/settings",
            "created_at": "",
        })
    if authenticity_score and authenticity_score < 60:
        items.append({
            "id": 8,
            "title": "Diversify verified platforms",
            "description": "Connect one more coding platform to raise authenticity.",
            "action_type": "review_roadmap",
            "priority": "medium",
            "href": "/dashboard/settings",
            "created_at": "",
        })
    if not items:
        items.append({
            "id": 9,
            "title": "Placement readiness stable",
            "description": "Keep weekly submissions and interviews to stay placement-ready.",
            "action_type": "review_roadmap",
            "priority": "low",
            "href": "/dashboard/progress",
            "created_at": "",
        })
    return items


def _extract_github_username(url):
    if not url:
        return None
    try:
        parts = url.strip('/').split('/')
        return parts[-1] if parts else None
    except Exception:
        return None


def _extract_github_repo_owner_and_name(repo_url):
    if not repo_url:
        return None, None
    try:
        parsed = urlparse(repo_url)
    except Exception:
        return None, None
    if parsed.netloc and "github.com" not in parsed.netloc.lower():
        return None, None
    path = parsed.path.strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None, None
    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _http_json(method, url, payload=None, headers=None, timeout=10):
    if headers is None:
        headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "skillsence-ai",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_repo_languages(languages_url, headers):
    if not languages_url:
        return []
    try:
        data = _http_json("GET", languages_url, headers=headers)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    sorted_langs = sorted(data.items(), key=lambda item: item[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:5]]


def _fetch_repo_commits(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=20"
    try:
        data = _http_json("GET", url, headers=headers)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return data


def _fetch_repo_readme(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    readme_headers = dict(headers)
    readme_headers["Accept"] = "application/vnd.github.raw+json"
    try:
        req = urllib.request.Request(url, headers=readme_headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")
            return content[:4000]
    except Exception:
        return ""


def _ai_signal_from_text(text):
    lowered = text.lower()
    keywords = ["chatgpt", "copilot", "generated by", "ai generated", "openai", "llm"]
    if any(keyword in lowered for keyword in keywords):
        return 40
    return 0


def _safe_json_loads(text):
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    stripped = text.strip()
    if "```" in stripped:
        parts = stripped.split("```")
        for idx in range(1, len(parts), 2):
            candidate = parts[idx].strip()
            if "\n" in candidate:
                candidate = candidate.split("\n", 1)[1].strip()
            try:
                return json.loads(candidate)
            except Exception:
                continue
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = stripped.find(start_char)
        end = stripped.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None


def _ai_signal_from_commits(commits):
    score = 0
    for commit in commits:
        message = ((commit.get("commit") or {}).get("message") or "").lower()
        score = max(score, _ai_signal_from_text(message))
    return score


def _analyze_repo(owner, repo):
    headers = _github_headers()
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_data = _http_json("GET", repo_url, headers=headers)
    if not isinstance(repo_data, dict):
        return None

    languages = _fetch_repo_languages(repo_data.get("languages_url"), headers)
    commits = _fetch_repo_commits(owner, repo, headers)
    readme_text = _fetch_repo_readme(owner, repo, headers)

    ai_score = max(_ai_signal_from_commits(commits), _ai_signal_from_text(readme_text))
    ai_generated = "likely" if ai_score >= 40 else "possible" if ai_score >= 20 else "no_signal"

    copied_or_forked = bool(repo_data.get("fork") or repo_data.get("is_template"))
    originality_score = 70
    if copied_or_forked:
        originality_score = 35
    if repo_data.get("stargazers_count", 0) > 10:
        originality_score += 5
    if repo_data.get("pushed_at"):
        originality_score += 5
    originality_score = min(100, originality_score)

    return {
        "repo_name": repo_data.get("name"),
        "repo_url": repo_data.get("html_url"),
        "description": repo_data.get("description") or "",
        "status": "completed",
        "score": originality_score,
        "metrics": {
            "languages": languages,
            "forked": bool(repo_data.get("fork")),
            "template": bool(repo_data.get("is_template")),
            "ai_generated": ai_generated,
            "ai_confidence": ai_score,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
        },
        "created_at": timezone.now().isoformat(),
    }

def _llm_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "skillsence-ai",
    }


def _llm_chat_completion(payload, timeout=20):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions")
    try:
        data = _http_json("POST", url, payload=payload, headers=_llm_headers(api_key), timeout=timeout)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        return {"error": {"status": exc.code, "body": body}}
    except Exception:
        return None
    return data


def _llm_message_content(data):
    try:
        return (((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
    except Exception:
        return ""


def _openai_chat_json(system_content, user_content, max_tokens=700):
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    data = _llm_chat_completion(payload, timeout=20)
    content = _llm_message_content(data)
    parsed = _safe_json_loads(content)
    if parsed is not None:
        return parsed

    fallback_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"{system_content}\n"
                    "Return raw JSON only. Do not use markdown, code fences, or extra narration."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{user_content}\n"
                    "Return valid JSON only."
                ),
            },
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    data = _llm_chat_completion(fallback_payload, timeout=20)
    try:
        content = _llm_message_content(data)
        return _safe_json_loads(content)
    except Exception:
        return None


def _is_text_path(path):
    binary_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
        ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac",
        ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".woff", ".woff2",
        ".ttf", ".otf", ".eot", ".exe", ".dll",
    }
    ext = os.path.splitext(path.lower())[1]
    return ext not in binary_exts


def _chunk_text(text, max_chars):
    if max_chars <= 0:
        max_chars = 6000
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        chunks.append(text[start:start + max_chars])
        start += max_chars
    return chunks


def _fetch_repo_tree(owner, repo, headers, default_branch):
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    return _http_json("GET", tree_url, headers=headers)


def _fetch_blob_text(owner, repo, sha, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}"
    data = _http_json("GET", url, headers=headers)
    if not isinstance(data, dict):
        return None
    if data.get("encoding") != "base64":
        return None
    try:
        decoded = base64.b64decode(data.get("content", ""))
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _repo_analysis_max_files():
    value = _safe_int(os.environ.get("AI_REPO_MAX_FILES"), default=14)
    return max(4, min(24, value))


def _repo_preview_chars():
    value = _safe_int(os.environ.get("AI_REPO_PREVIEW_CHARS"), default=4000)
    return max(500, min(12000, value))


def _should_skip_repo_path(path):
    lowered = (path or "").lower()
    if not lowered:
        return True
    blocked_segments = (
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".next",
        ".nuxt",
        ".venv",
        "venv",
        "__pycache__",
        "vendor",
        "staticfiles",
    )
    if any(f"/{segment}/" in f"/{lowered}/" for segment in blocked_segments):
        return True
    blocked_files = (
        "package-lock.json",
        "bun.lockb",
        "yarn.lock",
        "pnpm-lock.yaml",
        ".DS_Store".lower(),
    )
    if any(lowered.endswith(name) for name in blocked_files):
        return True
    blocked_suffixes = (".min.js", ".min.css", ".map")
    return lowered.endswith(blocked_suffixes)


def _repo_file_role(path):
    lowered = (path or "").lower()
    name = os.path.basename(lowered)
    if lowered.startswith(".github/workflows/"):
        return "ci"
    if name in {"readme", "readme.md", "readme.rst", "license", "license.md", "contributing.md"}:
        return "documentation"
    if name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "requirements.txt", "package.json", "tsconfig.json", "pyproject.toml"}:
        return "configuration"
    if any(part in lowered for part in ("/test/", "/tests/", "__tests__")) or name.startswith("test_") or name.endswith((".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx", "_test.py")):
        return "test"
    if name.endswith((".md", ".rst")):
        return "documentation"
    if name.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".env.example")):
        return "configuration"
    if lowered.startswith("scripts/") or "/scripts/" in lowered:
        return "tooling"
    return "source"


def _select_repo_files_for_review(files):
    role_rank = {
        "source": 0,
        "test": 1,
        "configuration": 2,
        "ci": 3,
        "tooling": 4,
        "documentation": 5,
    }
    selected = []
    for item in files:
        path = item.get("path") or ""
        if not path or _should_skip_repo_path(path) or not _is_text_path(path):
            continue
        size = _safe_int(item.get("size"), default=0)
        if size > 250000:
            continue
        role = _repo_file_role(path)
        selected.append({
            "path": path,
            "sha": item.get("sha"),
            "size": size,
            "role": role,
        })
    selected.sort(
        key=lambda item: (
            role_rank.get(item["role"], 99),
            -min(item["size"], 50000),
            item["path"].count("/"),
            item["path"],
        )
    )
    return selected[:_repo_analysis_max_files()]


def _repo_tree_overview(files):
    paths = [item.get("path") or "" for item in files]
    role_counts = {
        "source_files": 0,
        "test_files": 0,
        "documentation_files": 0,
        "configuration_files": 0,
        "ci_files": 0,
    }
    for path in paths:
        role = _repo_file_role(path)
        if role == "source":
            role_counts["source_files"] += 1
        elif role == "test":
            role_counts["test_files"] += 1
        elif role == "documentation":
            role_counts["documentation_files"] += 1
        elif role == "configuration":
            role_counts["configuration_files"] += 1
        elif role == "ci":
            role_counts["ci_files"] += 1
    role_counts["total_files"] = len(paths)
    role_counts["has_readme"] = any(os.path.basename(path.lower()).startswith("readme") for path in paths)
    role_counts["has_license"] = any(os.path.basename(path.lower()).startswith("license") for path in paths)
    role_counts["has_ci"] = any(path.lower().startswith(".github/workflows/") for path in paths)
    role_counts["has_docker"] = any(os.path.basename(path.lower()) in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"} for path in paths)
    return role_counts


def _infer_repo_architecture(files, readme_text, languages):
    paths = {item.get("path") or "" for item in files}
    lowered_paths = {path.lower() for path in paths}
    languages_lower = {str(language).lower() for language in languages}
    tags = []
    if "manage.py" in lowered_paths or any(path.endswith("/settings.py") for path in lowered_paths):
        tags.append("Django backend")
    if "package.json" in lowered_paths and any(path.endswith((".tsx", ".jsx")) for path in lowered_paths):
        tags.append("React frontend")
    if any(path.endswith((".ts", ".tsx")) for path in lowered_paths) or "typescript" in languages_lower:
        tags.append("TypeScript")
    if any(path.endswith((".py", ".pyi")) for path in lowered_paths) or "python" in languages_lower:
        tags.append("Python")
    if any(path.startswith(".github/workflows/") for path in lowered_paths):
        tags.append("GitHub Actions CI")
    if any(path.endswith((".spec.ts", ".test.ts", ".test.tsx", "_test.py")) or "/tests/" in path for path in lowered_paths):
        tags.append("Automated tests")
    if any(os.path.basename(path) in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"} for path in lowered_paths):
        tags.append("Containerized")
    if any(path.endswith("tailwind.config.ts") or path.endswith("tailwind.config.js") for path in lowered_paths):
        tags.append("Tailwind UI")
    readme_lower = (readme_text or "").lower()
    if "rest api" in readme_lower or "api" in readme_lower:
        tags.append("API service")
    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped[:8]


def _commit_category(message):
    lowered = (message or "").strip().lower()
    if not lowered:
        return "unknown"
    prefixes = {
        "feat": "feature",
        "fix": "fix",
        "docs": "docs",
        "refactor": "refactor",
        "test": "test",
        "chore": "chore",
    }
    for prefix, label in prefixes.items():
        if lowered.startswith(prefix):
            return label
    if "fix" in lowered:
        return "fix"
    if "test" in lowered:
        return "test"
    if "doc" in lowered or "readme" in lowered:
        return "docs"
    return "general"


def _commit_activity_payload(commits):
    categories = {
        "feature": 0,
        "fix": 0,
        "docs": 0,
        "refactor": 0,
        "test": 0,
        "chore": 0,
        "general": 0,
        "unknown": 0,
    }
    unique_authors = set()
    commit_messages = []
    meaningful_messages = 0
    for commit in commits:
        message = ((commit.get("commit") or {}).get("message") or "").strip()
        commit_messages.append(message)
        categories[_commit_category(message)] += 1
        if len(message.split()) >= 3 and message.lower() not in {"update", "changes", "fix", "wip"}:
            meaningful_messages += 1
        author = (commit.get("author") or {}).get("login") or ((commit.get("commit") or {}).get("author") or {}).get("name")
        if author:
            unique_authors.add(author)
    sample_size = len(commit_messages)
    quality_ratio = meaningful_messages / sample_size if sample_size else 0
    if quality_ratio >= 0.7:
        message_quality = "strong"
    elif quality_ratio >= 0.4:
        message_quality = "mixed"
    else:
        message_quality = "weak"
    last_commit_at = None
    if commits:
        last_commit_at = (((commits[0].get("commit") or {}).get("committer") or {}).get("date"))
    return {
        "sample_size": sample_size,
        "unique_authors": len(unique_authors),
        "message_quality": message_quality,
        "last_commit_at": last_commit_at,
        "categories": categories,
        "recent_messages": [message for message in commit_messages[:5] if message],
    }


def _count_secret_hits(content):
    patterns = [
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
        r"secret[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
        r"password\s*[:=]\s*['\"][^'\"]+['\"]",
        r"token\s*[:=]\s*['\"][^'\"]+['\"]",
    ]
    return sum(len(re.findall(pattern, content, flags=re.IGNORECASE)) for pattern in patterns)


def _file_review_summary(role, line_count, strength_count, risk_count):
    descriptor = {
        "source": "Application source",
        "test": "Test coverage",
        "configuration": "Configuration",
        "ci": "CI automation",
        "tooling": "Tooling",
        "documentation": "Documentation",
    }.get(role, "Repository file")
    return (
        f"{descriptor} file with {line_count} lines, "
        f"{strength_count} positive signal{'s' if strength_count != 1 else ''}, "
        f"and {risk_count} review risk{'s' if risk_count != 1 else ''}."
    )


def _heuristic_file_review(path, content):
    role = _repo_file_role(path)
    lines = content.splitlines()
    line_count = len(lines)
    non_empty = [line for line in lines if line.strip()]
    comment_lines = sum(
        1
        for line in non_empty
        if line.strip().startswith(("#", "//", "/*", "*", "<!--"))
    )
    comment_ratio = (comment_lines / len(non_empty)) if non_empty else 0
    function_count = len(re.findall(r"^\s*(async\s+def|def|function|const\s+\w+\s*=\s*\(|export\s+function|public\s+\w+\s*\()", content, flags=re.MULTILINE))
    class_count = len(re.findall(r"^\s*class\s+\w+", content, flags=re.MULTILINE))
    test_asserts = len(re.findall(r"\b(assert|expect\(|self\.assert|pytest)\b", content))
    todo_count = len(re.findall(r"\b(TODO|FIXME|HACK)\b", content, flags=re.IGNORECASE))
    long_lines = sum(1 for line in lines if len(line) > 120)
    secret_hits = _count_secret_hits(content)
    debug_hits = len(re.findall(r"\b(console\.log|print\(|debugger\b)\b", content))
    bare_excepts = len(re.findall(r"^\s*except\s*:\s*$", content, flags=re.MULTILINE))
    eval_hits = len(re.findall(r"\b(eval|exec)\s*\(", content))
    shell_true_hits = len(re.findall(r"shell\s*=\s*True", content))
    typed_file = path.lower().endswith((".ts", ".tsx", ".pyi"))
    documentation_signal = '"""' in content or "/*" in content or comment_ratio >= 0.08

    strengths = []
    if typed_file:
        strengths.append("Uses typed source code.")
    if documentation_signal:
        strengths.append("Includes developer-facing documentation or comments.")
    if test_asserts:
        strengths.append("Contains executable assertions or test expectations.")
    if function_count and line_count <= 260:
        strengths.append("Implementation is reasonably segmented into functions.")
    if class_count:
        strengths.append("Encapsulates logic into class-based structure.")

    risks = []
    if secret_hits:
        risks.append("Possible hard-coded secret or credential pattern detected.")
    if bare_excepts:
        risks.append("Bare exception handler can hide runtime failures.")
    if eval_hits or shell_true_hits:
        risks.append("Dynamic execution patterns need security review.")
    if debug_hits >= 2:
        risks.append("Debug statements are still committed.")
    if todo_count >= 2:
        risks.append("Outstanding TODO/FIXME markers suggest unfinished work.")
    if long_lines >= 12:
        risks.append("Several long lines reduce readability and reviewability.")
    if line_count > 500:
        risks.append("Large file likely needs decomposition.")

    score = 74
    score += 6 if typed_file else 0
    score += 6 if documentation_signal else 0
    score += 5 if test_asserts else 0
    score += 4 if function_count and line_count <= 260 else 0
    score -= min(secret_hits * 22, 35)
    score -= min(bare_excepts * 10, 20)
    score -= min((eval_hits + shell_true_hits) * 12, 24)
    score -= min(debug_hits * 3, 12)
    score -= min(todo_count * 2, 10)
    score -= min(max(long_lines - 3, 0), 12)
    if line_count > 350:
        score -= 8
    if line_count > 700:
        score -= 10
    score = max(0, min(100, score))

    if secret_hits or score < 45:
        risk_level = "high"
    elif score < 70 or risks:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "path": path,
        "role": role,
        "score": score,
        "risk_level": risk_level,
        "lines": line_count,
        "functions": function_count,
        "classes": class_count,
        "comment_ratio": round(comment_ratio, 2),
        "issues": {
            "todo_count": todo_count,
            "long_lines": long_lines,
            "secret_hits": secret_hits,
            "debug_hits": debug_hits,
            "bare_excepts": bare_excepts,
            "dynamic_exec_hits": eval_hits + shell_true_hits,
        },
        "strengths": strengths[:4],
        "risks": risks[:4],
        "summary": _file_review_summary(role, line_count, len(strengths), len(risks)),
    }


def _normalize_ai_string_list(value, limit=4):
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        normalized = str(item or "").strip()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _openai_repo_review(context):
    result = _openai_chat_json(
        (
            "You are a senior software engineering reviewer. Review repository evidence and "
            "return ONLY JSON with keys: summary (string), strengths (array), concerns (array), "
            "next_steps (array). Keep every point grounded in the provided signals."
        ),
        json.dumps(context, ensure_ascii=False),
        max_tokens=500,
    )
    if not isinstance(result, dict):
        return None
    summary = str(result.get("summary") or "").strip()
    return {
        "summary": summary[:400],
        "strengths": _normalize_ai_string_list(result.get("strengths")),
        "concerns": _normalize_ai_string_list(result.get("concerns")),
        "next_steps": _normalize_ai_string_list(result.get("next_steps")),
    }


def _build_repo_recommendations(tree_overview, commit_activity, file_reviews):
    recommendations = []
    if not tree_overview.get("test_files"):
        recommendations.append("Add automated tests around the main source paths before the next feature cycle.")
    if not tree_overview.get("documentation_files"):
        recommendations.append("Add a README section that explains setup, architecture, and deployment.")
    high_risk_files = [item for item in file_reviews if item.get("risk_level") == "high"]
    if high_risk_files:
        recommendations.append("Resolve the high-risk file findings first, especially secrets, dynamic execution, and oversized files.")
    if commit_activity.get("message_quality") == "weak":
        recommendations.append("Use clearer commit messages so reviewers can trace feature, fix, and refactor intent.")
    if len(recommendations) < 3:
        recommendations.append("Break large source files into smaller modules with tighter responsibilities.")
    return recommendations[:4]


def _build_repo_strengths(tree_overview, architecture_tags, file_reviews):
    strengths = []
    if tree_overview.get("has_readme"):
        strengths.append("Repository has baseline onboarding documentation.")
    if tree_overview.get("test_files"):
        strengths.append("Repository includes automated test files.")
    if architecture_tags:
        strengths.append(f"Project structure clearly signals {', '.join(architecture_tags[:3])}.")
    strong_files = [item for item in file_reviews if item.get("score", 0) >= 80]
    if strong_files:
        strengths.append(f"{len(strong_files)} reviewed files scored in the strong maintainability range.")
    return strengths[:4]


def _build_repo_risks(tree_overview, commit_activity, file_reviews):
    risks = []
    if not tree_overview.get("has_ci"):
        risks.append("No CI workflow was detected, so regression checks may depend on manual runs.")
    if commit_activity.get("sample_size", 0) <= 2:
        risks.append("Very little recent commit history was available for activity analysis.")
    medium_or_high = [item for item in file_reviews if item.get("risk_level") in {"medium", "high"}]
    if medium_or_high:
        risks.append(f"{len(medium_or_high)} reviewed files still carry medium or high review risk.")
    return risks[:4]


def _analyze_repository_work(owner, repo, user=None):
    headers = _github_headers()
    repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        repo_data = _http_json("GET", repo_api_url, headers=headers)
    except Exception:
        return {"error": "Unable to fetch repository data."}
    if not isinstance(repo_data, dict):
        return {"error": "Unable to fetch repository data."}

    default_branch = repo_data.get("default_branch") or "main"
    try:
        tree = _fetch_repo_tree(owner, repo, headers, default_branch)
    except Exception:
        return {"error": "Unable to fetch repository tree."}
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        return {"error": "Unable to fetch repository tree."}

    files = [node for node in tree.get("tree", []) if node.get("type") == "blob"]
    selected_files = _select_repo_files_for_review(files)
    if not selected_files:
        return {"error": "No analyzable text files found for this repository."}

    languages = _fetch_repo_languages(repo_data.get("languages_url"), headers)
    commits = _fetch_repo_commits(owner, repo, headers)
    readme_text = _fetch_repo_readme(owner, repo, headers)
    tree_overview = _repo_tree_overview(files)
    architecture_tags = _infer_repo_architecture(files, readme_text, languages)
    commit_activity = _commit_activity_payload(commits)

    total_lines = 0
    file_reviews = []
    total_score = 0
    total_files = 0
    top_ai_candidates = []
    repo_html_url = repo_data.get("html_url") or f"https://github.com/{owner}/{repo}"

    for item in selected_files:
        path = item.get("path")
        sha = item.get("sha")
        if not path or not sha:
            continue
        content = _fetch_blob_text(owner, repo, sha, headers)
        if content is None:
            continue
        lines = content.count("\n") + 1 if content else 0
        total_lines += lines
        _store_repo_file_snapshot(
            user=user,
            repo_url=repo_html_url,
            path=path,
            sha=sha,
            content=content,
            size=item.get("size", 0),
            lines=lines,
        )
        review = _heuristic_file_review(path, content)
        review["size"] = item.get("size", 0)
        file_reviews.append(review)
        total_score += review["score"]
        total_files += 1
        if review["role"] == "source":
            top_ai_candidates.append((review["risk_level"], -review["score"], -review["lines"], path, content))

    if not file_reviews:
        return {"error": "Unable to load repository source files for analysis."}

    top_ai_candidates.sort(key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item[0], 9), item[1], item[2], item[3]))
    if os.environ.get("OPENAI_API_KEY"):
        for risk_level, _neg_score, _neg_lines, path, content in top_ai_candidates[:3]:
            ai_result = _openai_score_code_chunk(path, content[:6000], 0, 1)
            if not ai_result:
                continue
            for review in file_reviews:
                if review["path"] == path:
                    review["ai_confidence"] = ai_result["score"]
                    review["ai_generated"] = ai_result["label"]
                    review["ai_rationale"] = ai_result["rationale"]
                    if risk_level == "high" and ai_result["score"] >= 65:
                        review["risks"] = [*review["risks"], "AI review also flagged strong generated-code likelihood."][:4]
                    break

    maintainability_score = int(round(total_score / max(total_files, 1)))
    testing_score = min(100, tree_overview["test_files"] * 18 + (20 if tree_overview["test_files"] else 0))
    documentation_score = min(100, tree_overview["documentation_files"] * 18 + (25 if tree_overview["has_readme"] else 0))
    security_penalty = sum(item["issues"].get("secret_hits", 0) * 25 for item in file_reviews)
    security_penalty += sum(item["issues"].get("dynamic_exec_hits", 0) * 10 for item in file_reviews)
    security_penalty += sum(item["issues"].get("bare_excepts", 0) * 6 for item in file_reviews)
    security_penalty += sum(item["issues"].get("debug_hits", 0) * 2 for item in file_reviews)
    security_score = max(20, 100 - security_penalty)
    architecture_score = min(100, 40 + len(architecture_tags) * 10 + (15 if tree_overview["has_ci"] else 0) + (15 if tree_overview["has_docker"] else 0))
    originality_score = 82
    if repo_data.get("fork") or repo_data.get("is_template"):
        originality_score -= 30
    if repo_data.get("stargazers_count", 0) > 5:
        originality_score += 4
    if commit_activity["sample_size"] >= 8:
        originality_score += 4
    originality_score = max(25, min(100, originality_score))
    commit_score = 45
    commit_score += min(commit_activity["sample_size"] * 3, 25)
    commit_score += 10 if commit_activity["message_quality"] == "strong" else 4 if commit_activity["message_quality"] == "mixed" else 0
    commit_score += min(commit_activity["unique_authors"] * 4, 12)
    commit_score = min(100, commit_score)
    engineering_score = int(round(
        maintainability_score * 0.34
        + security_score * 0.18
        + testing_score * 0.14
        + documentation_score * 0.12
        + architecture_score * 0.10
        + commit_score * 0.12
    ))

    repo_ai_confidence = max(
        [review.get("ai_confidence", 0) for review in file_reviews if isinstance(review.get("ai_confidence"), int)] or [0]
    )
    if repo_ai_confidence >= 70:
        ai_generated = "likely"
    elif repo_ai_confidence >= 40:
        ai_generated = "possible"
    else:
        ai_generated = "unlikely"

    strengths = _build_repo_strengths(tree_overview, architecture_tags, file_reviews)
    risks = _build_repo_risks(tree_overview, commit_activity, file_reviews)
    recommendations = _build_repo_recommendations(tree_overview, commit_activity, file_reviews)

    ai_review = None
    if os.environ.get("OPENAI_API_KEY"):
        ai_review = _openai_repo_review({
            "repo_name": repo_data.get("name"),
            "description": repo_data.get("description") or "",
            "languages": languages,
            "architecture": architecture_tags,
            "tree_overview": tree_overview,
            "commit_activity": commit_activity,
            "top_file_reviews": [
                {
                    "path": item["path"],
                    "score": item["score"],
                    "risk_level": item["risk_level"],
                    "strengths": item["strengths"],
                    "risks": item["risks"],
                }
                for item in file_reviews[:6]
            ],
            "strengths": strengths,
            "risks": risks,
            "recommendations": recommendations,
        })

    summary = (
        (ai_review or {}).get("summary")
        or f"{repo_data.get('name') or repo} scored {engineering_score}/100. "
           f"Strongest signals: {', '.join(strengths[:2]) or 'basic project structure'}. "
           f"Main risks: {', '.join(risks[:2]) or 'follow-up engineering review recommended'}."
    )

    file_reviews = sorted(
        file_reviews,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item["risk_level"], 9),
            item["score"],
            -item["lines"],
            item["path"],
        )
    )[:12]

    return {
        "repo_name": repo_data.get("name") or repo,
        "repo_url": repo_html_url,
        "description": repo_data.get("description") or "",
        "summary": summary[:500],
        "engineering_score": engineering_score,
        "maintainability_score": maintainability_score,
        "security_score": security_score,
        "testing_score": testing_score,
        "documentation_score": documentation_score,
        "architecture_score": architecture_score,
        "originality_score": originality_score,
        "ai_generated": ai_generated,
        "ai_confidence": repo_ai_confidence,
        "languages": languages,
        "files_analyzed": len(file_reviews),
        "lines_analyzed": total_lines,
        "tree_overview": tree_overview,
        "commit_activity": commit_activity,
        "architecture": architecture_tags,
        "strengths": strengths,
        "risks": risks,
        "recommendations": recommendations,
        "file_reviews": file_reviews,
        "ai_review": ai_review,
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "open_issues": repo_data.get("open_issues_count", 0),
        "default_branch": default_branch,
        "pushed_at": repo_data.get("pushed_at"),
    }


def _openai_score_code_chunk(path, chunk, chunk_index, total_chunks):
    system = (
        "You are a code forensic analyst. Determine likelihood that the provided code "
        "was AI-generated. Return ONLY JSON with keys: score (0-100), label "
        "(likely|possible|unlikely), rationale (short string)."
    )
    user = (
        f"File: {path}\n"
        f"Chunk {chunk_index + 1} of {total_chunks}\n"
        "Analyze the code below:\n\n"
        f"{chunk}"
    )
    result = _openai_chat_json(system, user, max_tokens=220)
    if not isinstance(result, dict):
        return None
    score = result.get("score")
    label = (result.get("label") or "").strip().lower()
    if not isinstance(score, (int, float)):
        return None
    if label not in {"likely", "possible", "unlikely"}:
        return None
    return {
        "score": max(0, min(100, int(score))),
        "label": label,
        "rationale": (result.get("rationale") or "").strip()[:200],
    }


def _analyze_repo_ai_generated(owner, repo, user=None):
    if not os.environ.get("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not configured."}
    headers = _github_headers()
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        repo_data = _http_json("GET", repo_url, headers=headers)
    except Exception:
        return {"error": "Unable to fetch repository data."}
    if not isinstance(repo_data, dict):
        return {"error": "Unable to fetch repository data."}

    default_branch = repo_data.get("default_branch") or "main"
    try:
        tree = _fetch_repo_tree(owner, repo, headers, default_branch)
    except Exception:
        return {"error": "Unable to fetch repository tree."}
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        return {"error": "Unable to fetch repository tree."}

    files = []
    for node in tree.get("tree", []):
        if node.get("type") != "blob":
            continue
        path = node.get("path") or ""
        if not path or not _is_text_path(path):
            continue
        files.append({
            "path": path,
            "sha": node.get("sha"),
            "size": node.get("size", 0),
        })

    if not files:
        return {"error": "No text files found for analysis."}

    chunk_chars = int(os.environ.get("AI_REPO_CHUNK_CHARS", "6000") or 6000)
    file_scores = []
    total_weight = 0
    weighted_score = 0
    total_lines = 0

    repo_html_url = repo_data.get("html_url")

    for item in files:
        sha = item.get("sha")
        path = item.get("path")
        if not sha or not path:
            return {"error": "Invalid file metadata."}
        content = _fetch_blob_text(owner, repo, sha, headers)
        if content is None:
            return {"error": f"Failed to load {path}."}
        lines = content.count("\n") + 1 if content else 0
        _store_repo_file_snapshot(
            user=user,
            repo_url=repo_html_url or repo_url,
            path=path,
            sha=sha,
            content=content,
            size=item.get("size", 0),
            lines=lines,
        )
        total_lines += lines
        chunks = _chunk_text(content, chunk_chars)
        if not chunks:
            continue

        chunk_scores = []
        for idx, chunk in enumerate(chunks):
            result = _openai_score_code_chunk(path, chunk, idx, len(chunks))
            if not result:
                return {"error": f"AI analysis failed for {path}."}
            chunk_scores.append((result["score"], len(chunk), result["label"]))

        weighted = sum(score * weight for score, weight, _ in chunk_scores)
        total = sum(weight for _, weight, _ in chunk_scores) or 1
        file_score = int(round(weighted / total))
        file_label = "likely" if file_score >= 70 else "possible" if file_score >= 40 else "unlikely"
        file_scores.append({
            "path": path,
            "score": file_score,
            "label": file_label,
            "lines": lines,
        })
        total_weight += total
        weighted_score += file_score * total

    if total_weight == 0:
        return {"error": "No analyzable files."}

    repo_score = int(round(weighted_score / total_weight))
    repo_label = "likely" if repo_score >= 70 else "possible" if repo_score >= 40 else "unlikely"
    top_files = sorted(file_scores, key=lambda f: f["score"], reverse=True)[:5]

    languages = _fetch_repo_languages(repo_data.get("languages_url"), headers)
    return {
        "repo_name": repo_data.get("name"),
        "repo_url": repo_data.get("html_url"),
        "ai_generated": repo_label,
        "ai_confidence": repo_score,
        "languages": languages,
        "files_analyzed": len(file_scores),
        "lines_analyzed": total_lines,
        "top_ai_files": top_files,
    }

def _question_bank():
    return [
        {"id": 1, "question": "Explain the difference between REST and GraphQL.", "difficulty": "easy", "tags": ["api", "backend"]},
        {"id": 2, "question": "What is a primary key and why is it important?", "difficulty": "easy", "tags": ["sql", "database"]},
        {"id": 3, "question": "How does React manage state updates?", "difficulty": "easy", "tags": ["react", "frontend", "javascript"]},
        {"id": 4, "question": "What is the purpose of indexes in databases?", "difficulty": "medium", "tags": ["sql", "database"]},
        {"id": 5, "question": "Describe how JWT authentication works.", "difficulty": "medium", "tags": ["auth", "backend"]},
        {"id": 6, "question": "What are Python generators and when would you use them?", "difficulty": "medium", "tags": ["python"]},
        {"id": 7, "question": "How do you prevent SQL injection?", "difficulty": "easy", "tags": ["security", "backend"]},
        {"id": 8, "question": "Explain the virtual DOM and its benefits.", "difficulty": "medium", "tags": ["react", "frontend"]},
        {"id": 9, "question": "How would you optimize a slow Django view?", "difficulty": "hard", "tags": ["django", "backend"]},
        {"id": 10, "question": "Describe the time complexity of binary search.", "difficulty": "easy", "tags": ["algorithms"]},
        {"id": 11, "question": "What is the CAP theorem and why does it matter?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 12, "question": "How does caching improve performance? Give an example.", "difficulty": "medium", "tags": ["system", "backend"]},
        {"id": 13, "question": "Explain the difference between PUT and PATCH.", "difficulty": "easy", "tags": ["api", "backend"]},
        {"id": 14, "question": "What are database transactions and ACID properties?", "difficulty": "medium", "tags": ["sql", "database"]},
        {"id": 15, "question": "How would you design a rate limiter for an API?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 16, "question": "Describe the lifecycle methods or hooks in React.", "difficulty": "medium", "tags": ["react", "frontend"]},
        {"id": 17, "question": "What is the difference between synchronous and asynchronous programming?", "difficulty": "easy", "tags": ["general"]},
        {"id": 18, "question": "Explain dependency injection and its benefits.", "difficulty": "medium", "tags": ["backend", "general"]},
        {"id": 19, "question": "How do you handle pagination in an API?", "difficulty": "medium", "tags": ["api", "backend"]},
        {"id": 20, "question": "What are webhooks and when would you use them?", "difficulty": "easy", "tags": ["api"]},
        {"id": 21, "question": "Explain the difference between threads and processes.", "difficulty": "medium", "tags": ["system"]},
        {"id": 22, "question": "How would you structure a scalable file upload system?", "difficulty": "hard", "tags": ["system", "backend"]},
        {"id": 23, "question": "What is CORS and how do you configure it safely?", "difficulty": "easy", "tags": ["security", "frontend", "backend"]},
        {"id": 24, "question": "Describe how you would model a many-to-many relationship.", "difficulty": "easy", "tags": ["database"]},
        {"id": 25, "question": "Explain eventual consistency with an example.", "difficulty": "hard", "tags": ["system"]},
        {"id": 26, "question": "What is memoization and when is it useful?", "difficulty": "medium", "tags": ["algorithms"]},
        {"id": 27, "question": "How do you secure secrets in production?", "difficulty": "medium", "tags": ["security"]},
        {"id": 28, "question": "Explain the difference between SSR and CSR.", "difficulty": "medium", "tags": ["frontend"]},
        {"id": 29, "question": "How would you debug a memory leak in a Node.js app?", "difficulty": "hard", "tags": ["javascript", "backend"]},
        {"id": 30, "question": "Describe how you would design a search feature.", "difficulty": "medium", "tags": ["system", "backend"]},
    ]


def _select_questions_for_user(user, total=10):
    bank = _question_bank()
    skill_names = {skill.name.strip().lower() for skill in user.skills.all() if skill.name}

    def matches(question):
        tags = set(question.get("tags") or [])
        if not tags:
            return True
        return bool(tags & skill_names)

    filtered = [q for q in bank if matches(q)]
    if not filtered:
        filtered = bank

    by_diff = {
        "easy": [q for q in filtered if q["difficulty"] == "easy"],
        "medium": [q for q in filtered if q["difficulty"] == "medium"],
        "hard": [q for q in filtered if q["difficulty"] == "hard"],
    }
    targets = {"easy": 3, "medium": 4, "hard": 3}

    chosen = []
    for level, count in targets.items():
        pool = by_diff.get(level, [])
        if pool:
            chosen.extend(random.sample(pool, min(count, len(pool))))

    if len(chosen) < total:
        remaining = [q for q in filtered if q not in chosen]
        random.shuffle(remaining)
        chosen.extend(remaining[: max(0, total - len(chosen))])

    while len(chosen) < total:
        chosen.append(random.choice(bank))

    random.shuffle(chosen)
    return chosen[:total]


def _intro_questions(user):
    name_hint = user.full_name or "your full name"
    return [
        {
            "id": "intro-1",
            "question": "Welcome! Please tell me your full name and the role you are targeting.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
        {
            "id": "intro-2",
            "question": "Give a brief introduction about yourself, including your current education or experience.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
        {
            "id": "intro-3",
            "question": "Walk me through one project you are proud of and your specific contributions.",
            "difficulty": "easy",
            "tags": ["intro"],
        },
    ]

def _generate_ai_questions(user, total=10):
    if not os.environ.get("OPENAI_API_KEY"):
        return None

    skills = [skill.name for skill in user.skills.all() if skill.name]
    parsed = _openai_chat_json(
        "You are an interview question generator. Return valid JSON only.",
        (
            f"Generate {total} technical interview questions tailored to this user skill list: "
            f"{', '.join(skills) if skills else 'general software engineering'}. "
            f"Return ONLY a JSON object with a key named questions. "
            f"questions must be an array of {total} objects with keys: question, difficulty, tags. "
            "difficulty must be one of: easy, medium, hard. Keep questions short."
        ),
        max_tokens=700,
    )
    if not isinstance(parsed, dict):
        return None

    question_items = parsed.get("questions")
    if not isinstance(question_items, list):
        return None

    cleaned = []
    for item in question_items:
        if not isinstance(item, dict):
            continue
        question = (item.get("question") or "").strip()
        difficulty = (item.get("difficulty") or "").strip().lower()
        tags = item.get("tags") or []
        if not question or difficulty not in {"easy", "medium", "hard"}:
            continue
        cleaned.append({
            "id": len(cleaned) + 1,
            "question": question,
            "difficulty": difficulty,
            "tags": tags if isinstance(tags, list) else [],
        })

    if len(cleaned) < total:
        return None
    return cleaned[:total]


def _select_or_generate_questions(user, total=10):
    intro = _intro_questions(user)
    technical_total = max(0, total - len(intro))
    questions = _generate_ai_questions(user, total=technical_total)
    if questions:
        return intro + questions
    return intro + _select_questions_for_user(user, total=technical_total)


def _score_answer(text, difficulty):
    base = {"easy": 5, "medium": 8, "hard": 12}
    weight = base.get(difficulty, 6)
    word_count = len(text.split())
    length_factor = min(word_count / 40, 1.0)
    keywords = ["api", "db", "database", "cache", "optimize", "complexity", "latency", "index", "security", "auth"]
    keyword_hits = sum(1 for kw in keywords if kw in text.lower())
    keyword_factor = min(keyword_hits / 4, 1.0)
    quality = 0.5 * length_factor + 0.5 * keyword_factor
    score = int(round(weight * (0.4 + 0.6 * quality)))
    return min(weight, max(1, score))


def _max_score(questions):
    base = {"easy": 5, "medium": 8, "hard": 12}
    return sum(base.get(q.get("difficulty"), 6) for q in questions)


def _build_interview_metrics(answers, questions, score):
    answered = len(answers)
    total = max(1, len(questions))
    word_counts = [a.get("word_count", 0) for a in answers] or [0]
    avg_words = sum(word_counts) / len(word_counts)
    clarity = min(100, int(30 + avg_words * 2))
    depth = min(100, int(20 + avg_words * 2.2))
    progress = int(round((answered / total) * 100))
    max_score = max(1, _max_score(questions))
    score_pct = int(round((score / max_score) * 100))
    return [
        {"label": "Interview Score", "value": score_pct, "color": "primary"},
        {"label": "Progress", "value": progress, "color": "accent"},
        {"label": "Clarity", "value": clarity, "color": "primary"},
        {"label": "Depth", "value": depth, "color": "accent"},
    ]


def _build_interview_feedback(answer):
    text = (answer.get("answer") or "").strip()
    word_count = answer.get("word_count", 0)
    filler = sum(text.lower().count(word) for word in ["um", "uh", "like", "basically", "actually"])
    clarity_score = max(0, min(100, int(30 + word_count * 2 - filler * 5)))
    sentiment_score = 0
    for word in ["confident", "achieved", "improved", "delivered", "led", "built", "optimized", "reduced"]:
        if word in text.lower():
            sentiment_score += 1
    sentiment_label = "positive" if sentiment_score >= 2 else "neutral"
    feedback = []
    if word_count < 20:
        feedback.append({"type": "improvement", "text": "Expand with specifics and measurable outcomes."})
    else:
        feedback.append({"type": "strength", "text": "Clear structure with solid context."})
    if clarity_score < 55:
        feedback.append({"type": "improvement", "text": "Slow down and reduce filler words for clarity."})
    else:
        feedback.append({"type": "strength", "text": "Clarity and pacing are strong."})
    if sentiment_label == "positive":
        feedback.append({"type": "strength", "text": "Confident, action-oriented tone."})
    else:
        feedback.append({"type": "improvement", "text": "Add stronger action verbs to increase impact."})
    return feedback


def _build_interview_summary(answers):
    if not answers:
        return {"strengths": ["Willing to engage in the interview."], "improvements": ["Provide more detail."]}
    avg_words = sum(a.get("word_count", 0) for a in answers) / max(1, len(answers))
    strengths = []
    improvements = []
    if avg_words >= 35:
        strengths.append("Strong detail and context in responses.")
    else:
        improvements.append("Add more depth with examples and metrics.")
    if any("project" in (a.get("answer") or "").lower() for a in answers):
        strengths.append("Good use of project-based explanations.")
    else:
        improvements.append("Reference a concrete project to back up your claims.")
    if not strengths:
        strengths.append("Consistent participation across questions.")
    if not improvements:
        improvements.append("Keep answers concise and structured.")
    return {"strengths": strengths, "improvements": improvements}


def _generate_followup_question(answer, current_question):
    prompt = (
        "Generate one short follow-up interview question based on this candidate answer. "
        "Return JSON with keys: question, difficulty. difficulty must be easy or medium."
    )
    user = f"Question: {current_question}\nAnswer: {answer}\n"
    result = _openai_chat_json(prompt, user, max_tokens=120)
    if isinstance(result, dict):
        question = (result.get("question") or "").strip()
        difficulty = (result.get("difficulty") or "easy").strip().lower()
        if question and difficulty in {"easy", "medium"}:
            return {"id": f"followup-{random.randint(1000, 9999)}", "question": question, "difficulty": difficulty, "tags": ["followup"]}
    if len(answer.split()) < 25:
        return {
            "id": f"followup-{random.randint(1000, 9999)}",
            "question": "Can you add more detail and a concrete example to support that?",
            "difficulty": "easy",
            "tags": ["followup"],
        }
    return None


def _build_interview_tips(answers):
    if not answers:
        return ["Keep answers structured: context, action, result.", "Mention measurable impact when possible."]
    last = answers[-1].get("difficulty")
    if last == "hard":
        return ["Break complex problems into smaller parts.", "Highlight trade-offs and constraints."]
    if last == "medium":
        return ["Explain your approach before details.", "Mention edge cases you considered."]
    return ["Use simple, concise explanations.", "Offer a quick example to reinforce the idea."]


def _interview_state_payload(session):
    questions = session.questions or []
    total = len(questions)
    index = session.current_index
    current = None
    if 0 <= index < total:
        current = questions[index]
    max_score = max(1, _max_score(questions))
    score_pct = int(round((session.score / max_score) * 100)) if questions else 0
    return {
        "total_questions": total,
        "current_index": index,
        "current_question": current.get("question") if current else None,
        "current_difficulty": current.get("difficulty") if current else None,
        "score": score_pct,
    }


def _candidate_skill_names(user, limit=8):
    names = []
    seen = set()
    for skill in list(user.skills.all()):
        normalized = (skill.name or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(normalized)
    if names:
        return names[:limit]

    fallback = []
    for item in (user.student_skills or "").split(","):
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        fallback.append(normalized)
    return fallback[:limit]


def _infer_interview_track(target_role, focus_areas, candidate_skills):
    tokens = " ".join([target_role or "", " ".join(focus_areas or []), " ".join(candidate_skills or [])]).lower()
    if any(term in tokens for term in ["frontend", "react", "ui", "web", "javascript", "typescript"]):
        return "frontend"
    if any(term in tokens for term in ["backend", "api", "django", "flask", "node", "microservice", "spring"]):
        return "backend"
    if any(term in tokens for term in ["full stack", "fullstack", "mern", "mean"]):
        return "fullstack"
    if any(term in tokens for term in ["data", "analytics", "machine learning", "ml"]):
        return "data"
    if any(term in tokens for term in ["devops", "cloud", "docker", "kubernetes", "sre", "platform"]):
        return "devops"
    if any(term in tokens for term in ["mobile", "android", "ios", "flutter", "react native"]):
        return "mobile"
    return "general"


def _advanced_interview_defaults(user):
    skills = _candidate_skill_names(user)
    skill_tokens = " ".join(skills).lower()
    if any(token in skill_tokens for token in ["react", "frontend", "javascript", "typescript"]):
        target_role = "Frontend Engineer"
    elif any(token in skill_tokens for token in ["django", "python", "backend", "api", "sql"]):
        target_role = "Backend Engineer"
    elif any(token in skill_tokens for token in ["data", "machine learning", "analytics"]):
        target_role = "Data Engineer"
    else:
        target_role = "Software Engineer"

    focus_areas = _normalize_string_list(skills[:3] or ["problem solving", "communication", "system design"])[:4]
    year = (user.year_of_study or "").lower()
    seniority = "intern" if any(term in year for term in ["1st", "2nd"]) else "new_grad"
    return {
        "target_role": target_role,
        "seniority": seniority,
        "company_style": "product",
        "interview_mode": "mixed",
        "focus_areas": focus_areas,
        "candidate_skills": skills,
        "question_count": 9,
        "answer_time_sec": 120,
        "max_followups": 3,
        "track": _infer_interview_track(target_role, focus_areas, skills),
    }


def _normalize_advanced_interview_profile(user, raw_profile=None):
    defaults = _advanced_interview_defaults(user)
    raw = raw_profile or {}
    if isinstance(raw, dict) and isinstance(raw.get("config"), dict):
        raw = raw.get("config") or {}

    target_role = (raw.get("target_role") or defaults["target_role"]).strip()[:120]
    seniority = (raw.get("seniority") or defaults["seniority"]).strip().lower()
    if seniority not in {"intern", "new_grad", "junior", "mid", "senior"}:
        seniority = defaults["seniority"]
    company_style = (raw.get("company_style") or defaults["company_style"]).strip().lower()
    if company_style not in {"product", "startup", "enterprise", "consulting"}:
        company_style = defaults["company_style"]
    interview_mode = (raw.get("interview_mode") or defaults["interview_mode"]).strip().lower()
    if interview_mode not in {"mixed", "technical", "behavioral", "system_design"}:
        interview_mode = defaults["interview_mode"]

    focus_areas = _normalize_string_list(raw.get("focus_areas") or defaults["focus_areas"])[:4]
    candidate_skills = _normalize_string_list(raw.get("candidate_skills") or defaults["candidate_skills"])[:8]
    question_count = int(_clamp_number(raw.get("question_count", defaults["question_count"]), 8, 12))
    answer_time_sec = int(_clamp_number(raw.get("answer_time_sec", defaults["answer_time_sec"]), 90, 180))
    max_followups = int(_clamp_number(raw.get("max_followups", defaults["max_followups"]), 1, 4))

    return {
        "target_role": target_role,
        "seniority": seniority,
        "company_style": company_style,
        "interview_mode": interview_mode,
        "focus_areas": focus_areas,
        "candidate_skills": candidate_skills,
        "question_count": question_count,
        "answer_time_sec": answer_time_sec,
        "max_followups": max_followups,
        "track": _infer_interview_track(target_role, focus_areas, candidate_skills),
        "headline": f"{seniority.replace('_', ' ').title()} {target_role}",
        "context": {
            "college": user.college or "",
            "course": user.course or "",
            "branch": user.branch or "",
            "year_of_study": user.year_of_study or "",
            "linkedin_headline": user.linkedin_headline or "",
        },
    }


def _advanced_question_bank():
    return [
        {
            "id": "api-design",
            "question": "Design a production-ready API for collaborative task workflows. How would you model resources, permissions, retries, and failures?",
            "difficulty": "hard",
            "mode": "technical",
            "competency": "system_design",
            "role_tracks": ["backend", "fullstack", "general"],
            "tags": ["api", "backend", "auth", "permissions", "idempotency"],
            "expected_signals": ["resource modeling", "authorization", "idempotency", "observability"],
            "evaluation_focus": "Architecture depth, failure handling, and tradeoffs.",
            "panelist": "Platform Architect",
        },
        {
            "id": "react-perf",
            "question": "A React screen re-renders too often. How do you isolate the cause and fix it without introducing accidental complexity?",
            "difficulty": "medium",
            "mode": "technical",
            "competency": "problem_solving",
            "role_tracks": ["frontend", "fullstack", "general"],
            "tags": ["react", "frontend", "performance", "profiling"],
            "expected_signals": ["profiling", "state boundaries", "memoization", "measurement"],
            "evaluation_focus": "Debugging sequence and performance judgment.",
            "panelist": "Frontend Lead",
        },
        {
            "id": "db-hotspot",
            "question": "A high-traffic endpoint slows down under load. How do you determine whether the bottleneck is query shape, indexes, cache strategy, or application code?",
            "difficulty": "hard",
            "mode": "technical",
            "competency": "problem_solving",
            "role_tracks": ["backend", "fullstack", "data", "general"],
            "tags": ["database", "performance", "cache", "profiling", "django"],
            "expected_signals": ["measurement", "indexes", "query analysis", "caching"],
            "evaluation_focus": "Prioritization and evidence-based diagnosis.",
            "panelist": "Performance Reviewer",
        },
        {
            "id": "auth-boundary",
            "question": "How would you secure an authentication flow that spans browser, API, and a third-party identity provider?",
            "difficulty": "medium",
            "mode": "technical",
            "competency": "technical_depth",
            "role_tracks": ["backend", "frontend", "fullstack", "general"],
            "tags": ["security", "auth", "tokens", "session", "oauth"],
            "expected_signals": ["token lifecycle", "refresh strategy", "attack surface", "storage"],
            "evaluation_focus": "Security boundary awareness.",
            "panelist": "Security Engineer",
        },
        {
            "id": "project-ownership",
            "question": "Tell me about a project where the outcome clearly depended on your decisions. What was ambiguous at the start, and what did you personally drive?",
            "difficulty": "medium",
            "mode": "behavioral",
            "competency": "ownership",
            "role_tracks": ["general", "backend", "frontend", "fullstack", "data", "devops", "mobile"],
            "tags": ["ownership", "leadership", "delivery", "project"],
            "expected_signals": ["ambiguity", "decision-making", "ownership", "outcomes"],
            "evaluation_focus": "Ownership and decision quality.",
            "panelist": "Hiring Manager",
        },
        {
            "id": "quality-tradeoff",
            "question": "Describe a time you had to choose between shipping quickly and improving technical quality. What tradeoff did you make, and why?",
            "difficulty": "medium",
            "mode": "behavioral",
            "competency": "tradeoffs",
            "role_tracks": ["general", "backend", "frontend", "fullstack", "data", "devops", "mobile"],
            "tags": ["tradeoff", "quality", "delivery", "stakeholders"],
            "expected_signals": ["tradeoffs", "stakeholder alignment", "follow-through"],
            "evaluation_focus": "Judgment under constraint.",
            "panelist": "Bar Raiser",
        },
        {
            "id": "multi-tenant",
            "question": "Design a multi-tenant platform for student portfolios where each university needs isolated data, custom reporting, and reliable exports.",
            "difficulty": "hard",
            "mode": "system_design",
            "competency": "system_design",
            "role_tracks": ["backend", "fullstack", "devops", "general"],
            "tags": ["system", "multi-tenant", "data-isolation", "reporting", "scalability"],
            "expected_signals": ["tenancy model", "authorization", "batch jobs", "storage", "observability"],
            "evaluation_focus": "Boundary design and operational rigor.",
            "panelist": "Systems Architect",
        },
        {
            "id": "realtime-stream",
            "question": "How would you build a realtime interview assistant that streams transcript updates, survives unstable networks, and preserves session state?",
            "difficulty": "hard",
            "mode": "system_design",
            "competency": "system_design",
            "role_tracks": ["frontend", "backend", "fullstack", "devops", "general"],
            "tags": ["realtime", "websocket", "state", "resilience", "latency"],
            "expected_signals": ["transport choice", "reconnect strategy", "state recovery", "latency"],
            "evaluation_focus": "Realtime systems and resilience.",
            "panelist": "Realtime Systems Lead",
        },
        {
            "id": "feedback-loop",
            "question": "Tell me about a time you received tough technical feedback. What changed in your work after that?",
            "difficulty": "easy",
            "mode": "behavioral",
            "competency": "communication",
            "role_tracks": ["general", "backend", "frontend", "fullstack", "data", "devops", "mobile"],
            "tags": ["feedback", "growth", "communication", "self-awareness"],
            "expected_signals": ["reflection", "adaptation", "specific improvement"],
            "evaluation_focus": "Coachability and reflection.",
            "panelist": "Hiring Manager",
        },
        {
            "id": "observability-gap",
            "question": "If users report intermittent failures but dashboards look normal, what observability gaps do you investigate first?",
            "difficulty": "medium",
            "mode": "system_design",
            "competency": "problem_solving",
            "role_tracks": ["backend", "devops", "fullstack", "general"],
            "tags": ["observability", "incident", "tracing", "metrics", "logs"],
            "expected_signals": ["traces", "correlation", "sampling", "alerts"],
            "evaluation_focus": "Production debugging maturity.",
            "panelist": "Production Engineer",
        },
    ]


def _advanced_intro_questions(user, profile):
    role_label = profile.get("target_role") or "software role"
    focus_text = ", ".join(profile.get("focus_areas") or []) or "core engineering"
    return [
        {
            "id": "intro-role",
            "question": f"Give me a concise introduction: who you are, the {role_label} role you want, and what makes you credible for it.",
            "difficulty": "easy",
            "mode": "behavioral",
            "competency": "communication",
            "role_tracks": ["general"],
            "tags": ["intro", "communication", "positioning"],
            "expected_signals": ["clarity", "role alignment", "summary"],
            "evaluation_focus": "Executive summary and role alignment.",
            "panelist": "Hiring Manager",
        },
        {
            "id": "intro-project",
            "question": f"Choose one project that best represents your work in {focus_text}. Explain the problem, your ownership, and the measurable result.",
            "difficulty": "medium",
            "mode": "behavioral",
            "competency": "ownership",
            "role_tracks": ["general"],
            "tags": ["project", "ownership", "metrics"],
            "expected_signals": ["problem framing", "ownership", "impact"],
            "evaluation_focus": "Ownership and evidence quality.",
            "panelist": "Technical Lead",
        },
    ]


def _advanced_difficulty_targets(profile, total):
    seniority = profile.get("seniority")
    if seniority == "intern":
        return {"easy": 3, "medium": 3, "hard": max(0, total - 6)}
    if seniority == "new_grad":
        return {"easy": 2, "medium": 4, "hard": max(0, total - 6)}
    if seniority == "junior":
        return {"easy": 1, "medium": 4, "hard": max(0, total - 5)}
    if seniority == "mid":
        return {"easy": 1, "medium": 3, "hard": max(0, total - 4)}
    return {"easy": 0, "medium": 3, "hard": max(0, total - 3)}


def _advanced_question_fit_score(question, profile):
    score = 0
    track = profile.get("track") or "general"
    role_tracks = question.get("role_tracks") or []
    if track in role_tracks:
        score += 30
    if "general" in role_tracks:
        score += 10

    interview_mode = profile.get("interview_mode") or "mixed"
    mode = question.get("mode") or "technical"
    if interview_mode == "mixed":
        score += 14
    elif mode == interview_mode:
        score += 24
    elif interview_mode == "technical" and mode == "system_design":
        score += 12
    elif interview_mode == "system_design" and mode == "technical":
        score += 8

    focus_tokens = _tokenize_match_text(" ".join(profile.get("focus_areas") or []))
    skill_tokens = _tokenize_match_text(" ".join(profile.get("candidate_skills") or []))
    question_tokens = set(question.get("tags") or [])
    score += len(focus_tokens & question_tokens) * 6
    score += len(skill_tokens & question_tokens) * 5

    targets = _advanced_difficulty_targets(profile, 8)
    if targets.get(question.get("difficulty"), 0) > 0:
        score += 8
    if question.get("competency") in {"ownership", "communication"} and interview_mode == "behavioral":
        score += 10
    if question.get("competency") == "system_design" and interview_mode in {"mixed", "system_design"}:
        score += 8
    return score


def _normalize_generated_advanced_question(item, fallback_id, profile):
    if not isinstance(item, dict):
        return None
    question = (item.get("question") or "").strip()
    difficulty = (item.get("difficulty") or "").strip().lower()
    if difficulty not in {"easy", "medium", "hard"} or not question:
        return None
    mode = (item.get("mode") or profile.get("interview_mode") or "technical").strip().lower()
    if mode not in {"technical", "behavioral", "system_design"}:
        mode = "technical"
    competency = (item.get("competency") or "problem_solving").strip().lower()
    if competency not in {"communication", "technical_depth", "problem_solving", "ownership", "tradeoffs", "system_design"}:
        competency = "problem_solving"
    return {
        "id": f"ai-{fallback_id}",
        "question": question,
        "difficulty": difficulty,
        "mode": mode,
        "competency": competency,
        "role_tracks": [profile.get("track") or "general"],
        "tags": _normalize_string_list(item.get("tags"))[:6],
        "expected_signals": _normalize_string_list(item.get("expected_signals"))[:5],
        "evaluation_focus": (item.get("evaluation_focus") or "Depth, ownership, and clarity.").strip(),
        "panelist": (item.get("panelist") or "Domain Interviewer").strip()[:60],
    }


def _generate_advanced_ai_questions(user, profile, total=3, existing_questions=None):
    if not os.environ.get("OPENAI_API_KEY") or total <= 0:
        return []

    skills = profile.get("candidate_skills") or _candidate_skill_names(user)
    focus_areas = profile.get("focus_areas") or []
    asked = [item.get("question") for item in (existing_questions or []) if item.get("question")]
    parsed = _openai_chat_json(
        "You are a senior interview panel designing high-signal engineering interviews. Return valid JSON only.",
        (
            f"Generate {total} advanced interview questions for a candidate targeting {profile.get('target_role')} at the "
            f"{profile.get('seniority')} level. Company style is {profile.get('company_style')}. "
            f"Interview mode is {profile.get('interview_mode')}. Focus areas: {', '.join(focus_areas) or 'general engineering'}. "
            f"Candidate skills: {', '.join(skills) or 'general software engineering'}. "
            f"Avoid duplicating these existing questions: {' | '.join(asked[:5]) or 'none'}. "
            "Return a JSON object with key questions. questions must be an array of objects with keys: "
            "question, difficulty, mode, competency, tags, expected_signals, evaluation_focus, panelist."
        ),
        max_tokens=1000,
    )
    if not isinstance(parsed, dict):
        return []

    cleaned = []
    for item in parsed.get("questions") or []:
        normalized = _normalize_generated_advanced_question(item, len(cleaned) + 1, profile)
        if normalized:
            cleaned.append(normalized)
    return cleaned[:total]


def _select_advanced_questions(user, profile):
    total = profile.get("question_count") or 9
    intro = _advanced_intro_questions(user, profile)
    core_total = max(0, total - len(intro))
    ranked = sorted(
        _advanced_question_bank(),
        key=lambda item: (_advanced_question_fit_score(item, profile), random.random()),
        reverse=True,
    )
    targets = _advanced_difficulty_targets(profile, core_total)
    chosen = []
    used_ids = set()
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
    competency_counts = {}

    for question in ranked:
        if len(chosen) >= core_total:
            break
        difficulty = question.get("difficulty") or "medium"
        competency = question.get("competency") or "problem_solving"
        if question["id"] in used_ids:
            continue
        if difficulty_counts[difficulty] >= targets.get(difficulty, core_total):
            continue
        if competency_counts.get(competency, 0) >= 2:
            continue
        chosen.append(dict(question))
        used_ids.add(question["id"])
        difficulty_counts[difficulty] += 1
        competency_counts[competency] = competency_counts.get(competency, 0) + 1

    for question in ranked:
        if len(chosen) >= core_total:
            break
        if question["id"] in used_ids:
            continue
        chosen.append(dict(question))
        used_ids.add(question["id"])

    generated = _generate_advanced_ai_questions(user, profile, total=min(3, core_total), existing_questions=chosen)
    if generated:
        replace_count = min(len(generated), len(chosen))
        chosen = generated + chosen[: max(0, len(chosen) - replace_count)]
    return intro + chosen[:core_total]


def _advanced_question_weight(question):
    difficulty = question if isinstance(question, str) else (question or {}).get("difficulty")
    is_followup = False if isinstance(question, str) else bool((question or {}).get("is_followup"))
    base = {"easy": 8, "medium": 12, "hard": 16}
    weight = base.get(difficulty, 10)
    if is_followup:
        weight = max(5, int(round(weight * 0.65)))
    return weight


def _advanced_max_score(questions):
    return sum(_advanced_question_weight(question) for question in (questions or []))


def _phrase_hit_count(text, phrases):
    lowered = (text or "").lower()
    return sum(1 for phrase in phrases if phrase in lowered)


def _evaluate_advanced_answer(answer_text, question, profile):
    text = (answer_text or "").strip()
    lowered = text.lower()
    question = question or {}
    keyword_hits = len(set(question.get("tags") or []) & _tokenize_match_text(text))
    keyword_hits += _phrase_hit_count(lowered, question.get("expected_signals") or [])
    filler_count = _phrase_hit_count(lowered, [" um ", " uh ", " basically", " actually", " you know", " kind of "])
    hedge_count = _phrase_hit_count(lowered, ["maybe", "probably", "i think", "sort of", "kind of", "not sure"])
    action_hits = _phrase_hit_count(lowered, ["built", "implemented", "designed", "led", "delivered", "optimized", "owned", "migrated", "debugged"])
    tradeoff_hits = _phrase_hit_count(lowered, ["tradeoff", "trade-off", "versus", "instead", "because", "constraint", "pros", "cons"])
    testing_hits = _phrase_hit_count(lowered, ["test", "tests", "unit", "integration", "regression", "rollback", "monitoring"])
    structure_hits = _phrase_hit_count(lowered, ["first", "then", "finally", "result", "impact", "because", "so that"])
    ownership_hits = _phrase_hit_count(lowered, ["i led", "i built", "i designed", "i owned", "my role", "i decided", "i drove"])
    project_hits = _phrase_hit_count(lowered, ["project", "service", "feature", "system", "platform", "module"])
    metric_hits = len(re.findall(r"\b\d+(?:\.\d+)?(?:%|x|ms|s|sec|seconds|minutes|users|requests|queries|errors|days|weeks)?\b", text))
    edge_case_hits = _phrase_hit_count(lowered, ["edge case", "failure", "fallback", "retry", "rollback", "timeout", "race condition"])
    sentence_count = max(1, len([segment for segment in re.split(r"[.!?]+", text) if segment.strip()]))
    word_count = len(text.split())

    communication = _clamp_number(34 + word_count * 0.55 + sentence_count * 2.5 - filler_count * 7 - hedge_count * 4)
    technical_depth = _clamp_number(22 + keyword_hits * 10 + testing_hits * 6 + edge_case_hits * 5 + metric_hits * 4)
    problem_solving = _clamp_number(28 + structure_hits * 11 + edge_case_hits * 7 + tradeoff_hits * 6 + testing_hits * 4)
    ownership = _clamp_number(26 + ownership_hits * 12 + action_hits * 6 + metric_hits * 5)
    evidence = _clamp_number(18 + metric_hits * 16 + project_hits * 7 + keyword_hits * 4)
    tradeoffs = _clamp_number(16 + tradeoff_hits * 18 + edge_case_hits * 5 + testing_hits * 4)
    confidence = _clamp_number(34 + action_hits * 6 - hedge_count * 8 - filler_count * 5)

    competency = question.get("competency") or "problem_solving"
    if competency == "communication":
        weighted_score = communication * 0.32 + ownership * 0.18 + evidence * 0.16 + confidence * 0.14 + problem_solving * 0.10 + tradeoffs * 0.10
    elif competency in {"system_design", "tradeoffs"}:
        weighted_score = technical_depth * 0.24 + problem_solving * 0.22 + tradeoffs * 0.22 + communication * 0.12 + evidence * 0.10 + ownership * 0.10
    else:
        weighted_score = technical_depth * 0.24 + problem_solving * 0.20 + communication * 0.16 + evidence * 0.14 + ownership * 0.12 + tradeoffs * 0.09 + confidence * 0.05

    rubric = {
        "communication": int(round(communication)),
        "technical_depth": int(round(technical_depth)),
        "problem_solving": int(round(problem_solving)),
        "ownership": int(round(ownership)),
        "evidence": int(round(evidence)),
        "tradeoffs": int(round(tradeoffs)),
        "confidence": int(round(confidence)),
    }

    strengths = []
    improvements = []
    red_flags = []
    if rubric["communication"] >= 72:
        strengths.append("Answer had a clear structure and was easy to follow.")
    elif rubric["communication"] < 55:
        improvements.append("Structure the response more clearly using context, action, and result.")
    if rubric["technical_depth"] >= 70:
        strengths.append("Technical reasoning went beyond surface-level description.")
    elif rubric["technical_depth"] < 52 and competency != "communication":
        improvements.append("Go deeper into implementation details and engineering choices.")
    if rubric["evidence"] >= 65:
        strengths.append("Used concrete examples or measurable outcomes to support claims.")
    elif rubric["evidence"] < 45:
        improvements.append("Use metrics, scale, or a concrete example to make the answer credible.")
    if rubric["tradeoffs"] >= 65 and competency in {"system_design", "tradeoffs", "problem_solving"}:
        strengths.append("Called out tradeoffs and constraints instead of presenting a single-path answer.")
    elif competency in {"system_design", "tradeoffs"} and rubric["tradeoffs"] < 50:
        improvements.append("Discuss alternatives, tradeoffs, and why your chosen path is appropriate.")
    if rubric["ownership"] >= 68:
        strengths.append("Ownership was clearly attributed to your actions and decisions.")
    elif rubric["ownership"] < 48:
        improvements.append("Be explicit about what you personally owned instead of team-only language.")

    if word_count < 18:
        red_flags.append("Answer was too short for a high-signal assessment.")
    if hedge_count >= 3:
        red_flags.append("Answer carried too much uncertainty for an interview setting.")
    if competency in {"system_design", "tradeoffs"} and rubric["tradeoffs"] < 45:
        red_flags.append("Critical tradeoffs were not discussed.")
    if competency != "communication" and rubric["technical_depth"] < 42:
        red_flags.append("Technical depth stayed below the expected bar.")
    if rubric["evidence"] < 35:
        red_flags.append("Claims were not backed by outcomes, scale, or specifics.")

    weakest_dimension = min(rubric.items(), key=lambda item: item[1])[0]
    strongest_dimension = max(rubric.items(), key=lambda item: item[1])[0]
    quality_score = int(round(_clamp_number(weighted_score)))
    points = int(round(_advanced_question_weight(question) * (quality_score / 100.0)))
    return {
        "word_count": word_count,
        "quality_score": quality_score,
        "points": points,
        "rubric": rubric,
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "red_flags": red_flags[:3],
        "signals": {
            "filler_count": filler_count,
            "hedge_count": hedge_count,
            "metric_hits": metric_hits,
            "tradeoff_hits": tradeoff_hits,
            "testing_hits": testing_hits,
            "keyword_hits": keyword_hits,
        },
        "weakest_dimension": weakest_dimension,
        "strongest_dimension": strongest_dimension,
        "followup_reason": "Probe the weakest dimension to validate depth." if red_flags or quality_score < 68 else "Escalate with a deeper question because the answer showed strong signal.",
        "followup_style": "gap_probe" if red_flags or quality_score < 68 else "bar_raise",
        "coach_summary": f"Strongest signal: {strongest_dimension.replace('_', ' ')}. Weakest signal: {weakest_dimension.replace('_', ' ')}.",
    }


def _advanced_feedback_payload(answer_analysis):
    if not answer_analysis:
        return []
    items = [{"type": "strength", "text": text} for text in answer_analysis.get("strengths", [])[:2]]
    items.extend({"type": "improvement", "text": text} for text in answer_analysis.get("improvements", [])[:2])
    if not items:
        items.append({"type": "improvement", "text": "Expand the next answer with more specifics and clearer ownership."})
    return items[:4]


def _advanced_summary_payload(answers, questions=None, profile=None, score=0):
    if not answers:
        return {
            "strengths": ["Session has started but there is not enough signal yet."],
            "improvements": ["Answer a few questions to generate a meaningful hiring summary."],
            "red_flags": [],
            "next_steps": ["Use STAR structure and concrete project evidence."],
            "readiness_score": 0,
            "recommendation": "Signal not ready",
            "competency_scores": {},
            "highlights": [],
        }

    rubric_totals = {
        "communication": 0,
        "technical_depth": 0,
        "problem_solving": 0,
        "ownership": 0,
        "evidence": 0,
        "tradeoffs": 0,
        "confidence": 0,
    }
    red_flags = []
    highlights = []
    improvements = []
    for answer in answers:
        analysis = answer.get("analysis") or {}
        rubric = analysis.get("rubric") or {}
        for key in rubric_totals:
            rubric_totals[key] += int(rubric.get(key, 0) or 0)
        red_flags.extend(analysis.get("red_flags", []))
        highlights.extend(analysis.get("strengths", []))
        improvements.extend(analysis.get("improvements", []))

    total_answers = max(1, len(answers))
    competency_scores = {key: int(round(value / total_answers)) for key, value in rubric_totals.items()}
    score_pct = int(round((score / max(1, _advanced_max_score(questions or []))) * 100)) if questions else 0
    readiness_score = int(round((score_pct * 0.55) + (_score_mean(list(competency_scores.values())) * 0.45)))
    readiness_score = int(_clamp_number(readiness_score))
    ordered_scores = sorted(competency_scores.items(), key=lambda item: item[1], reverse=True)
    top_dimensions = [item[0] for item in ordered_scores[:2]]
    bottom_dimensions = [item[0] for item in ordered_scores[-2:]]

    strengths = []
    if "communication" in top_dimensions:
        strengths.append("Communicates ideas with clear structure and good pacing.")
    if "technical_depth" in top_dimensions:
        strengths.append("Shows enough implementation depth to support technical claims.")
    if "ownership" in top_dimensions:
        strengths.append("Makes personal contribution and decision-making explicit.")
    if "evidence" in top_dimensions:
        strengths.append("Backs claims with examples, metrics, or production context.")
    if not strengths:
        strengths.append("Stayed engaged and produced usable signal across the session.")

    summary_improvements = []
    for dimension in bottom_dimensions:
        if dimension == "communication":
            summary_improvements.append("Tighten answer structure and reduce ambiguity under pressure.")
        elif dimension == "technical_depth":
            summary_improvements.append("Go deeper into implementation details, architecture, and failure modes.")
        elif dimension == "problem_solving":
            summary_improvements.append("Show the debugging or reasoning sequence more explicitly.")
        elif dimension == "ownership":
            summary_improvements.append("Separate your contribution from the team's contribution more clearly.")
        elif dimension == "evidence":
            summary_improvements.append("Use measurable results, scale, and concrete examples more consistently.")
        elif dimension == "tradeoffs":
            summary_improvements.append("Discuss alternatives, constraints, and why one path was chosen.")
        elif dimension == "confidence":
            summary_improvements.append("State decisions more directly and reduce hedging language.")

    unique_red_flags = []
    seen_flags = set()
    for item in red_flags:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen_flags:
            continue
        seen_flags.add(key)
        unique_red_flags.append(normalized)

    if readiness_score >= 84 and len(unique_red_flags) <= 1:
        recommendation = "Strong shortlist"
    elif readiness_score >= 70:
        recommendation = "Proceed with targeted follow-up round"
    elif readiness_score >= 58:
        recommendation = "Needs coaching before recruiter-facing rounds"
    else:
        recommendation = "Not ready for external interview loop yet"

    next_steps = []
    if "technical_depth" in bottom_dimensions:
        next_steps.append("Prepare deeper implementation explanations for one project in your portfolio.")
    if "tradeoffs" in bottom_dimensions:
        next_steps.append("Practice answering with alternatives considered, constraints, and final decision.")
    if "evidence" in bottom_dimensions:
        next_steps.append("Attach metrics, scale, latency, users, or quality outcomes to your examples.")
    if "communication" in bottom_dimensions:
        next_steps.append("Use a tighter context-action-result structure for each answer.")
    if not next_steps:
        next_steps.append("Maintain depth and consistency across harder follow-up rounds.")

    return {
        "strengths": strengths[:3],
        "improvements": summary_improvements[:3],
        "red_flags": unique_red_flags[:3],
        "next_steps": next_steps[:3],
        "readiness_score": readiness_score,
        "recommendation": recommendation,
        "competency_scores": competency_scores,
        "answered_questions": len(answers),
        "target_role": (profile or {}).get("target_role") if isinstance(profile, dict) else None,
        "interview_mode": (profile or {}).get("interview_mode") if isinstance(profile, dict) else None,
        "followup_questions": sum(1 for question in (questions or []) if question.get("is_followup")),
        "highlights": highlights[:3],
    }


def _advanced_metrics_payload(answers, questions, score, summary):
    total = max(1, len(questions or []))
    answered = len(answers or [])
    progress = int(round((answered / total) * 100))
    score_pct = int(round((score / max(1, _advanced_max_score(questions or []))) * 100))
    competency_scores = summary.get("competency_scores") or {}
    return [
        {"label": "Interview Score", "value": score_pct, "color": "primary"},
        {"label": "Progress", "value": progress, "color": "accent"},
        {"label": "Technical Depth", "value": int(competency_scores.get("technical_depth", 0) or 0), "color": "primary"},
        {"label": "Communication", "value": int(competency_scores.get("communication", 0) or 0), "color": "accent"},
        {"label": "Ownership", "value": int(competency_scores.get("ownership", 0) or 0), "color": "primary"},
        {"label": "Hiring Readiness", "value": int(summary.get("readiness_score", 0) or 0), "color": "accent"},
    ]


def _advanced_tips_payload(answers, summary):
    if not answers:
        return [
            "Answer in context-action-result order.",
            "Tie every important claim to a concrete example or metric.",
            "Explain one tradeoff whenever the question involves architecture or scale.",
        ]

    latest_analysis = (answers[-1] or {}).get("analysis") or {}
    weakest = latest_analysis.get("weakest_dimension")
    tip_map = {
        "communication": "Lead with the headline first, then fill in supporting detail.",
        "technical_depth": "Name the exact mechanism, technology choice, or failure boundary involved.",
        "problem_solving": "Explain the sequence: hypothesis, test, observation, decision.",
        "ownership": "State your personal decision and the part you directly owned.",
        "evidence": "Use metrics, traffic, latency, defect counts, or business outcomes.",
        "tradeoffs": "Name the rejected alternatives and the reason they lost.",
        "confidence": "Use direct language and avoid softening your decision unnecessarily.",
    }
    tips = [tip_map[weakest]] if weakest in tip_map else []
    for item in summary.get("next_steps", [])[:2]:
        if item not in tips:
            tips.append(item)
    return [item for item in tips if item][:3]


def _generate_advanced_followup(answer_text, current_question, profile, answer_analysis, current_questions=None):
    question = current_question or {}
    current_questions = current_questions or []
    if question.get("is_followup") or int(question.get("followup_depth", 0) or 0) >= 1:
        return None
    followup_count = sum(1 for item in current_questions if item.get("is_followup"))
    if followup_count >= int((profile or {}).get("max_followups", 2) or 2):
        return None

    weakest = (answer_analysis or {}).get("weakest_dimension") or "technical_depth"
    style = (answer_analysis or {}).get("followup_style") or "gap_probe"
    fallback_gap = {
        "communication": "Re-answer that in a tighter structure: context, your action, and the result.",
        "technical_depth": "Go one level deeper into the implementation details. What exactly happened under the hood?",
        "problem_solving": "Walk me through the decision sequence step by step, including what you ruled out.",
        "ownership": "What was specifically yours to own, and what critical decision did you personally make?",
        "evidence": "What measurable result or production signal proved the approach actually worked?",
        "tradeoffs": "What alternatives did you evaluate, and why did you reject them?",
        "confidence": "State your decision more directly. What would you defend if challenged on this approach?",
    }
    fallback_raise = {
        "technical_depth": "Assume the load doubles tomorrow. What part of your design breaks first and how do you redesign it?",
        "problem_solving": "What is the hardest failure mode in that approach, and how would you prove your mitigation works?",
        "tradeoffs": "Under tight latency and reliability constraints, which tradeoff becomes unacceptable and why?",
        "evidence": "What metric would you monitor in the first 24 hours to prove the system is healthy?",
    }

    if os.environ.get("OPENAI_API_KEY"):
        result = _openai_chat_json(
            "Generate one short follow-up interview question. Return JSON only with keys question and difficulty.",
            (
                f"Candidate target role: {(profile or {}).get('target_role')}. "
                f"Interview mode: {(profile or {}).get('interview_mode')}. "
                f"Current question: {question.get('question')}. "
                f"Candidate answer: {answer_text}. "
                f"Weakest dimension: {weakest}. "
                f"Follow-up style: {style}. "
                f"Reason: {(answer_analysis or {}).get('followup_reason')}."
            ),
            max_tokens=180,
        )
        if isinstance(result, dict):
            followup_question = (result.get("question") or "").strip()
            followup_difficulty = (result.get("difficulty") or "medium").strip().lower()
            if followup_question and followup_difficulty in {"easy", "medium", "hard"}:
                return {
                    "id": f"followup-{random.randint(1000, 9999)}",
                    "question": followup_question,
                    "difficulty": followup_difficulty,
                    "mode": question.get("mode") or "technical",
                    "competency": weakest if weakest in {"communication", "technical_depth", "problem_solving", "ownership", "tradeoffs", "system_design"} else "problem_solving",
                    "role_tracks": [profile.get("track") or "general"],
                    "tags": ["followup", weakest],
                    "expected_signals": [weakest.replace("_", " ")],
                    "evaluation_focus": (answer_analysis or {}).get("followup_reason") or "Follow-up depth check.",
                    "panelist": question.get("panelist") or "Follow-up Reviewer",
                    "is_followup": True,
                    "followup_depth": int(question.get("followup_depth", 0) or 0) + 1,
                    "parent_id": question.get("id"),
                }

    fallback_question = fallback_raise.get(weakest) if style == "bar_raise" else fallback_gap.get(weakest)
    if not fallback_question:
        return None
    return {
        "id": f"followup-{random.randint(1000, 9999)}",
        "question": fallback_question,
        "difficulty": "hard" if style == "bar_raise" else "medium",
        "mode": question.get("mode") or "technical",
        "competency": weakest if weakest in {"communication", "technical_depth", "problem_solving", "ownership", "tradeoffs", "system_design"} else "problem_solving",
        "role_tracks": [profile.get("track") or "general"],
        "tags": ["followup", weakest],
        "expected_signals": [weakest.replace("_", " ")],
        "evaluation_focus": (answer_analysis or {}).get("followup_reason") or "Follow-up depth check.",
        "panelist": question.get("panelist") or "Follow-up Reviewer",
        "is_followup": True,
        "followup_depth": int(question.get("followup_depth", 0) or 0) + 1,
        "parent_id": question.get("id"),
    }


def _advanced_state_payload(session):
    questions = session.questions or []
    total = len(questions)
    index = session.current_index
    current = questions[index] if 0 <= index < total else None
    session_profile = session.session_profile or {}
    score_pct = int(round((session.score / max(1, _advanced_max_score(questions))) * 100)) if questions else 0
    return {
        "total_questions": total,
        "current_index": index,
        "current_question": current.get("question") if current else None,
        "current_difficulty": current.get("difficulty") if current else None,
        "current_competency": current.get("competency") if current else None,
        "current_panelist": current.get("panelist") if current else None,
        "current_focus": current.get("evaluation_focus") if current else None,
        "score": score_pct,
        "answer_time_sec": int(session_profile.get("answer_time_sec", 120) or 120),
    }


def _advanced_history_payload(user, limit=6):
    sessions = user.ai_interviews.all()[:limit]
    payload = []
    for session in sessions:
        answers = session.answers or []
        profile = session.session_profile or _advanced_interview_defaults(user)
        summary = session.summary or _advanced_summary_payload(answers, session.questions or [], profile, score=session.score or 0)
        payload.append({
            "id": session.id,
            "status": session.status,
            "score": _advanced_state_payload(session)["score"],
            "answered": len(answers),
            "questions": len(session.questions or []),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "strengths": summary.get("strengths", [])[:2],
            "improvements": summary.get("improvements", [])[:2],
            "target_role": profile.get("target_role"),
            "interview_mode": profile.get("interview_mode"),
            "readiness_score": summary.get("readiness_score", 0),
            "recommendation": summary.get("recommendation"),
        })
    return payload


def _advanced_session_payload(user, session=None):
    setup_defaults = _advanced_interview_defaults(user)
    if not session:
        idle_session = AIInterviewSession(user=user, session_profile=setup_defaults, summary={})
        return {
            "status": "idle",
            "transcript": [],
            "feedback": [],
            "metrics": [],
            "tips": [],
            "history": _advanced_history_payload(user),
            "session_profile": setup_defaults,
            "summary": {},
            "latest_analysis": {},
            "setup_defaults": setup_defaults,
            **_advanced_state_payload(idle_session),
        }

    summary = session.summary or _advanced_summary_payload(session.answers or [], session.questions or [], session.session_profile or setup_defaults, score=session.score or 0)
    latest_answer = (session.answers or [])[-1] if session.answers else {}
    return {
        "status": session.status,
        "transcript": session.transcript,
        "feedback": session.feedback,
        "metrics": session.metrics,
        "tips": session.tips,
        "history": _advanced_history_payload(user),
        "session_profile": session.session_profile or setup_defaults,
        "summary": summary,
        "latest_analysis": latest_answer.get("analysis") or {},
        "setup_defaults": setup_defaults,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        **_advanced_state_payload(session),
    }

def _flag_ai_generated_repos(owner, user=None):
    headers = _github_headers()
    repos_url = f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated"
    try:
        repos = _http_json("GET", repos_url, headers=headers)
    except Exception:
        return []

    flagged = []
    if isinstance(repos, list):
        for repo in repos:
            repo_name = repo.get("name")
            if not repo_name:
                continue
            analysis = _analyze_repo_ai_generated(owner, repo_name, user=user)
            if not analysis:
                continue
            if analysis.get("error"):
                flagged.append({
                    "repo_name": repo_name,
                    "repo_url": repo.get("html_url"),
                    "status": "failed",
                    "error": analysis.get("error"),
                })
                continue
            if analysis.get("ai_generated") in {"likely", "possible"}:
                flagged.append({
                    "repo_name": analysis.get("repo_name"),
                    "repo_url": analysis.get("repo_url"),
                    "ai_generated": analysis.get("ai_generated"),
                    "ai_confidence": analysis.get("ai_confidence", 0),
                    "languages": analysis.get("languages", []),
                    "files_analyzed": analysis.get("files_analyzed", 0),
                    "lines_analyzed": analysis.get("lines_analyzed", 0),
                    "top_ai_files": analysis.get("top_ai_files", []),
                })
    return flagged


def _student_score_map(student):
    score_map = {
        card.score_type: card.score
        for card in student.scorecards.all()
    }
    if score_map:
        return score_map
    if student.role != "student":
        return {}
    try:
        return calculate_student_scores(student)
    except Exception:
        return {}


def _student_skill_payload(student):
    skill_objects = sorted(
        list(student.skills.all()),
        key=lambda skill: (-(skill.score or 0), skill.name.lower()),
    )
    skills = [
        {
            "name": skill.name,
            "score": skill.score or 0,
            "level": skill.level,
            "verified": skill.verified,
        }
        for skill in skill_objects
    ]
    if skills:
        return skills

    fallback = []
    seen = set()
    for item in (student.student_skills or "").split(","):
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        fallback.append({
            "name": normalized,
            "score": 50,
            "level": "beginner",
            "verified": False,
        })
    return fallback


def _student_focus_area(scores):
    focus_scores = {
        "Coding": scores.get("coding_skill_index", 0) or 0,
        "Communication": scores.get("communication_score", 0) or 0,
        "Authenticity": scores.get("authenticity_score", 0) or 0,
    }
    focus_area, _value = min(focus_scores.items(), key=lambda item: item[1])
    actions = {
        "Coding": "Schedule a coding round and review GitHub depth.",
        "Communication": "Assess storytelling, clarity, and mock interview confidence.",
        "Authenticity": "Review platform evidence and ask for project walkthroughs.",
    }
    return focus_area, actions[focus_area]


def _student_status_label(placement_ready, profile_verified):
    if placement_ready >= 80 and profile_verified:
        return "Interview ready"
    if placement_ready >= 70:
        return "Shortlist next"
    if placement_ready >= 55:
        return "Needs one more review"
    return "Needs coaching"


def _latest_resume_document(student):
    prefetched_documents = getattr(student, "_prefetched_objects_cache", {}).get("documents")
    if prefetched_documents is not None:
        for document in prefetched_documents:
            if document.doc_type == "resume" and document.file:
                return document
        return None
    return student.documents.filter(doc_type="resume").first()


def _resume_document_payload(document, download_path):
    if not document or not document.file:
        return None
    return {
        "filename": document.title or os.path.basename(document.file.name or "resume"),
        "uploaded_at": document.created_at.isoformat() if document.created_at else None,
        "download_path": download_path,
    }


def _resume_file_response(document):
    if not document or not document.file:
        return Response({'error': 'Resume not found'}, status=404)
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.title or os.path.basename(document.file.name or "resume"),
    )


def _build_skill_evidence_items(user, skill):
    items = []
    skill_name = (skill.name or "").strip()
    skill_name_lower = skill_name.lower()
    resume_document = _latest_resume_document(user)
    student_skills_text = (user.student_skills or "").lower()

    if resume_document:
        items.append({
            "source": "resume",
            "title": "Resume evidence",
            "detail": f"Referenced in uploaded resume: {resume_document.title}",
            "url": "/api/skills/resume/",
            "created_at": resume_document.created_at.isoformat() if resume_document.created_at else None,
        })

    if skill_name_lower and skill_name_lower in student_skills_text:
        items.append({
            "source": "profile",
            "title": "Declared by student",
            "detail": "Listed in the student skill profile.",
            "url": "/dashboard/settings",
            "created_at": None,
        })

    latest_report = user.code_analysis_reports.filter(status="completed").first()
    if latest_report:
        items.append({
            "source": "repository",
            "title": "Repository analysis",
            "detail": latest_report.repo_url,
            "url": latest_report.repo_url,
            "created_at": latest_report.created_at.isoformat() if latest_report.created_at else None,
        })

    latest_submission = user.submissions.exclude(repo_url="").first()
    if latest_submission:
        items.append({
            "source": "project",
            "title": latest_submission.title or "Project submission",
            "detail": latest_submission.repo_url or (latest_submission.description or "Project evidence"),
            "url": latest_submission.repo_url,
            "created_at": latest_submission.created_at.isoformat() if latest_submission.created_at else None,
        })

    interview_session = user.ai_interviews.filter(status="completed").first()
    if interview_session:
        items.append({
            "source": "interview",
            "title": "Interview verification",
            "detail": f"Completed AI interview with score {_interview_state_payload(interview_session)['score']}/100.",
            "url": "/dashboard/interview",
            "created_at": interview_session.completed_at.isoformat() if interview_session.completed_at else None,
        })

    media_upload = user.media_uploads.exclude(status="processing").first()
    if media_upload:
        items.append({
            "source": media_upload.media_type,
            "title": media_upload.title,
            "detail": f"{media_upload.media_type.title()} upload available as supporting evidence.",
            "url": "/dashboard/media",
            "created_at": media_upload.created_at.isoformat() if media_upload.created_at else None,
        })

    public_links = [
        ("GitHub", user.github_link),
        ("LeetCode", user.leetcode_link),
        ("LinkedIn", user.linkedin_link),
        ("CodeChef", user.codechef_link),
        ("HackerRank", user.hackerrank_link),
    ]
    for label, url in public_links:
        if not url:
            continue
        items.append({
            "source": label.lower(),
            "title": f"{label} profile connected",
            "detail": url,
            "url": url,
            "created_at": None,
        })
        if len(items) >= 6:
            break

    deduped = []
    seen = set()
    for item in items:
        key = (item["source"], item["title"], item["detail"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6]


def _resume_preview_payload(user):
    skills = list(user.skills.order_by('-verified', '-score', 'name')[:10])
    scorecards = list(user.scorecards.all())
    latest_interview = user.ai_interviews.filter(status='completed').first()
    latest_report = user.code_analysis_reports.filter(status='completed').first()
    links = [
        {"label": "GitHub", "url": user.github_link},
        {"label": "LeetCode", "url": user.leetcode_link},
        {"label": "LinkedIn", "url": user.linkedin_link},
        {"label": "CodeChef", "url": user.codechef_link},
        {"label": "HackerRank", "url": user.hackerrank_link},
        {"label": "Codeforces", "url": user.codeforces_link},
        {"label": "GeeksforGeeks", "url": user.gfg_link},
    ]

    top_skill_names = [skill.name for skill in skills[:4] if skill.name]
    summary = (
        user.linkedin_about
        or user.linkedin_headline
        or (
            f"{user.full_name or user.username} is a {user.course or 'student'} focused on "
            f"{', '.join(top_skill_names) or 'applied software projects'} with a placement readiness "
            f"score of {next((card.score for card in scorecards if card.score_type == 'placement_ready'), 0)}/100."
        )
    )

    achievements = []
    for card in scorecards:
        label = card.score_type.replace('_', ' ').title()
        achievements.append(f"{label}: {card.score}/100")
    if latest_interview:
        achievements.append(
            f"AI interview score: {_interview_state_payload(latest_interview)['score']}/100"
        )
    if latest_report:
        achievements.append(f"Repository analyzed: {latest_report.repo_url}")

    return {
        "full_name": user.full_name or user.username,
        "headline": user.linkedin_headline or "Verified student profile",
        "summary": summary,
        "education": {
            "college": user.college or "",
            "course": user.course or "",
            "branch": user.branch or "",
            "year_of_study": user.year_of_study or "",
            "cgpa": float(user.cgpa) if user.cgpa is not None else None,
        },
        "skills": [
            {
                "name": skill.name,
                "level": skill.level,
                "score": skill.score,
                "verified": skill.verified,
            }
            for skill in skills
        ],
        "achievements": achievements[:6],
        "projects": [
            {
                "title": report.repo_url if report.repo_url else "Repository analysis",
                "description": report.summary or "AI-analyzed code repository.",
                "link": report.repo_url,
            }
            for report in user.code_analysis_reports.filter(status='completed')[:3]
        ] + [
            {
                "title": submission.title,
                "description": submission.description or "Project submission",
                "link": submission.repo_url,
            }
            for submission in user.submissions.exclude(repo_url='')[:2]
        ],
        "links": [item for item in links if item["url"]],
    }


def _interview_history_payload(user, limit=6):
    return _advanced_history_payload(user, limit=limit)


def _student_summary_payload(student):
    scores = _student_score_map(student)
    skills = _student_skill_payload(student)
    resume_document = _latest_resume_document(student)
    placement_ready = int(scores.get("placement_ready", 0) or 0)
    focus_area, recommended_action = _student_focus_area(scores)
    top_skills = skills[:8]
    profile_verified = bool(student.profile_verified)

    return {
        "id": student.id,
        "verification_id": f"SKV-{student.id:05d}",
        "name": student.full_name or student.username,
        "email": student.email,
        "college": student.college or "",
        "course": student.course or "Student",
        "branch": student.branch or "",
        "year_of_study": student.year_of_study or "",
        "cgpa": float(student.cgpa) if student.cgpa is not None else None,
        "location": student.branch or "",
        "headline": student.linkedin_headline or "",
        "summary": student.linkedin_about or "",
        "profile_verified": profile_verified,
        "status_label": _student_status_label(placement_ready, profile_verified),
        "focus_area": focus_area,
        "recommended_action": recommended_action,
        "needs_attention": placement_ready < 60 or not profile_verified,
        "score": placement_ready,
        "scores": {
            "placement_ready": placement_ready,
            "coding_skill_index": int(scores.get("coding_skill_index", 0) or 0),
            "communication_score": int(scores.get("communication_score", 0) or 0),
            "authenticity_score": int(scores.get("authenticity_score", 0) or 0),
        },
        "skills": top_skills,
        "verified_skills": sum(1 for skill in top_skills if skill["verified"]),
        "highlights": [skill["name"] for skill in top_skills[:3]],
        "resume_document": _resume_document_payload(
            resume_document,
            f"/api/skills/recruiter-dashboard/resume/{student.id}/",
        ),
        "links": {
            "github": student.github_link or "",
            "leetcode": student.leetcode_link or "",
            "linkedin": student.linkedin_link or "",
            "codechef": student.codechef_link or "",
            "hackerrank": student.hackerrank_link or "",
            "codeforces": student.codeforces_link or "",
            "gfg": student.gfg_link or "",
        },
        "last_analyzed_at": student.last_analyzed_at.isoformat() if student.last_analyzed_at else None,
    }


def _skill_distribution_for_students(student_payloads, limit=8):
    counts = {}
    for payload in student_payloads:
        for skill in payload.get("skills", [])[:6]:
            name = skill.get("name")
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1
    items = sorted(
        [{"name": name, "count": count} for name, count in counts.items()],
        key=lambda item: (-item["count"], item["name"].lower()),
    )
    return items[:limit]


def _trend_for_students(student_ids, student_payloads):
    if not student_ids:
        return []

    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(
        user_id__in=student_ids,
        recorded_on__gte=cutoff,
    ).order_by("recorded_on")

    buckets = {}
    for snapshot in snapshots:
        bucket = buckets.setdefault(snapshot.recorded_on, {
            "count": 0,
            "placement_ready": 0,
            "coding_skill_index": 0,
            "communication_score": 0,
            "authenticity_score": 0,
        })
        bucket["count"] += 1
        scores = snapshot.scores or {}
        for field in ["placement_ready", "coding_skill_index", "communication_score", "authenticity_score"]:
            bucket[field] += scores.get(field, 0) or 0

    if not buckets:
        if not student_payloads:
            return []
        return [{
            "date": timezone.localdate().isoformat(),
            "placement_ready": _score_mean([item["scores"]["placement_ready"] for item in student_payloads]),
            "coding_skill_index": _score_mean([item["scores"]["coding_skill_index"] for item in student_payloads]),
            "communication_score": _score_mean([item["scores"]["communication_score"] for item in student_payloads]),
            "authenticity_score": _score_mean([item["scores"]["authenticity_score"] for item in student_payloads]),
        }]

    series = []
    for recorded_on in sorted(buckets):
        bucket = buckets[recorded_on]
        count = bucket["count"] or 1
        series.append({
            "date": recorded_on.isoformat(),
            "placement_ready": round(bucket["placement_ready"] / count, 1),
            "coding_skill_index": round(bucket["coding_skill_index"] / count, 1),
            "communication_score": round(bucket["communication_score"] / count, 1),
            "authenticity_score": round(bucket["authenticity_score"] / count, 1),
        })
    return series


def _interventions_for_students(student_payloads, limit=6):
    interventions = []
    for payload in student_payloads:
        reasons = []
        scores = payload["scores"]
        if payload["score"] < 60:
            reasons.append("Placement readiness is below 60.")
        if scores["coding_skill_index"] < 55:
            reasons.append("Coding evidence is still weak.")
        if scores["communication_score"] < 55:
            reasons.append("Communication needs more structure.")
        if not payload["profile_verified"]:
            reasons.append("Verification interview is incomplete.")
        if not reasons:
            continue
        severity = "high" if payload["score"] < 50 else "medium" if payload["score"] < 65 else "low"
        interventions.append({
            "id": payload["id"],
            "name": payload["name"],
            "verification_id": payload["verification_id"],
            "college": payload["college"],
            "branch": payload["branch"],
            "score": payload["score"],
            "focus_area": payload["focus_area"],
            "severity": severity,
            "reason": " ".join(reasons[:2]),
            "action": payload["recommended_action"],
        })
    interventions.sort(key=lambda item: (item["score"], item["name"].lower()))
    return interventions[:limit]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    user = request.user
    skills = SkillSerializer(user.skills.all(), many=True).data
    activities = ActivitySerializer(user.activities.all()[:10], many=True).data
    scorecards = ScoreCardSerializer(user.scorecards.all(), many=True).data
    steps = VerificationStepSerializer(user.verification_steps.all(), many=True).data
    return Response({
        'skills': skills,
        'activities': activities,
        'scorecards': scorecards,
        'verification_steps': steps,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activities_view(request):
    activities = ActivitySerializer(request.user.activities.all()[:20], many=True).data
    return Response(activities)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_steps_view(request):
    steps = list(request.user.verification_steps.all())
    if steps:
        return Response(VerificationStepSerializer(steps, many=True).data)
    return Response(_build_verification_steps(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations_view(request):
    return Response(_build_recommendations(request.user))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_generated_repos_view(request):
    owner = _extract_github_username(request.user.github_link)
    if not owner:
        return Response({'items': [], 'analyzed_at': None})
    items = _flag_ai_generated_repos(owner, user=request.user)
    analyzed_at = timezone.now()
    request.user.last_analyzed_at = analyzed_at
    request.user.save(update_fields=["last_analyzed_at"])
    return Response({'items': items, 'analyzed_at': analyzed_at.isoformat()})


@api_view(['GET'])
@permission_classes([AllowAny])
def skill_suggestions_view(request):
    skills = Skill.objects.values_list('name', flat=True).distinct().order_by('name')[:50]
    if skills:
        return Response(list(skills))
    block = ContentBlock.objects.filter(key='skill_suggestions').first()
    if block and isinstance(block.payload, list):
        return Response(block.payload)
    return Response([])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_passport_view(request):
    skills = request.user.skills.all()
    radar_data = [
        {'skill': skill.name, 'level': skill.score or 50, 'fullMark': 100}
        for skill in skills
    ]
    verified = []
    for skill in skills.filter(verified=True):
        evidence_items = _build_skill_evidence_items(request.user, skill)
        verified.append(
            {
                'name': skill.name,
                'level': skill.level,
                'evidence': len(evidence_items),
                'verified': skill.verified,
                'evidence_items': evidence_items,
            }
        )
    scorecards = ScoreCard.objects.filter(user=request.user)
    bar_data = [
        {'name': score.score_type.replace('_', ' ').title(), 'score': score.score}
        for score in scorecards
    ]
    return Response({
        'radar_data': radar_data,
        'bar_data': bar_data,
        'verified_skills': verified,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_passport_pdf_view(request):
    user = request.user
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return Response(
            {'error': 'PDF export requires the reportlab package.'},
            status=500,
        )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        matplotlib_available = True
    except Exception:
        matplotlib_available = False

    skills = user.skills.all()
    scorecards = ScoreCard.objects.filter(user=user)
    scores = {card.score_type: card.score for card in scorecards}

    cutoff = timezone.localdate() - timedelta(days=90)
    series = list(user.score_snapshots.filter(recorded_on__gte=cutoff).order_by("recorded_on"))

    def render_chart(fig):
        chart_buffer = io.BytesIO()
        fig.savefig(chart_buffer, format="png", dpi=120, bbox_inches="tight")
        if matplotlib_available:
            plt.close(fig)
        chart_buffer.seek(0)
        return chart_buffer

    def chart_scores():
        if not matplotlib_available:
            return None
        labels = ["Coding", "Communication", "Authenticity", "Placement"]
        values = [
            scores.get("coding_skill_index", 0),
            scores.get("communication_score", 0),
            scores.get("authenticity_score", 0),
            scores.get("placement_ready", 0),
        ]
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.bar(labels, values, color=["#2563eb", "#10b981", "#f59e0b", "#0ea5e9"])
        ax.set_ylim(0, 100)
        ax.set_title("Core Scores")
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        for idx, value in enumerate(values):
            ax.text(idx, value + 2, str(value), ha="center", fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        return render_chart(fig)

    def chart_trend():
        if not matplotlib_available:
            return None
        if not series:
            return None
        dates = [snap.recorded_on for snap in series]
        fig, ax = plt.subplots(figsize=(6, 2.2))
        ax.plot(dates, [snap.scores.get("placement_ready", 0) for snap in series], label="Placement", color="#0ea5e9")
        ax.plot(dates, [snap.scores.get("coding_skill_index", 0) for snap in series], label="Coding", color="#2563eb")
        ax.set_ylim(0, 100)
        ax.set_title("90 Day Trend")
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=7, loc="upper left")
        ax.spines[["top", "right"]].set_visible(False)
        return render_chart(fig)

    def chart_radar():
        if not matplotlib_available:
            return None
        top = sorted(skills, key=lambda s: s.score or 0, reverse=True)[:6]
        if not top:
            return None
        labels = [skill.name for skill in top]
        values = [skill.score or 0 for skill in top]
        angles = [n / len(labels) * 2 * math.pi for n in range(len(labels))]
        values = values + [values[0]]
        angles = angles + [angles[0]]
        fig = plt.figure(figsize=(4, 3))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles, values, color="#2563eb", linewidth=2)
        ax.fill(angles, values, color="#2563eb", alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 100)
        ax.set_title("Skill Radar", y=1.08)
        return render_chart(fig)

    def chart_verified():
        if not matplotlib_available:
            return None
        total = skills.count()
        verified = skills.filter(verified=True).count()
        if total == 0:
            return None
        fig, ax = plt.subplots(figsize=(3.5, 2.4))
        ax.pie([verified, max(0, total - verified)], labels=["Verified", "Unverified"], autopct="%1.0f%%", textprops={"fontsize": 7})
        ax.set_title("Verification Mix")
        return render_chart(fig)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.75 * inch
    y = height - x_margin

    pdf.setTitle("SkillVerify Skill Passport")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, "SkillVerify Skill Passport")
    y -= 0.3 * inch

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x_margin, y, f"Name: {user.full_name or user.username}")
    y -= 0.18 * inch
    pdf.drawString(x_margin, y, f"Email: {user.email}")
    y -= 0.18 * inch
    profile_line = " - ".join([value for value in [user.course, user.college] if value])
    pdf.drawString(x_margin, y, f"Profile: {profile_line or '-'}")
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Core Scores")
    y -= 0.2 * inch

    bar_chart = chart_scores()
    if bar_chart:
        pdf.drawImage(ImageReader(bar_chart), x_margin, y - 2.2 * inch, width=6.5 * inch, height=2.2 * inch)
        y -= 2.5 * inch
    else:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x_margin, y, "Charts unavailable (matplotlib not installed).")
        y -= 0.3 * inch

    y -= 0.2 * inch
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x_margin, y, "Verified Skills")
    y -= 0.2 * inch
    pdf.setFont("Helvetica", 10)
    if not skills:
        pdf.drawString(x_margin, y, "No skills verified yet.")
        y -= 0.18 * inch
    else:
        for skill in skills:
            pdf.drawString(x_margin, y, f"{skill.name} - {skill.level} ({skill.score}/100)")
            y -= 0.18 * inch
            if y < 1.2 * inch:
                pdf.showPage()
                y = height - x_margin
                pdf.setFont("Helvetica", 10)

    y -= 0.2 * inch
    radar = chart_radar()
    if radar:
        pdf.drawImage(ImageReader(radar), x_margin, y - 3 * inch, width=4 * inch, height=3 * inch)
    verified_chart = chart_verified()
    if verified_chart:
        pdf.drawImage(ImageReader(verified_chart), x_margin + 4.2 * inch, y - 2.4 * inch, width=2.3 * inch, height=2.3 * inch)

    y -= 3.2 * inch
    trend = chart_trend()
    if trend:
        if y < 2.6 * inch:
            pdf.showPage()
            y = height - x_margin
        pdf.drawImage(ImageReader(trend), x_margin, y - 2.2 * inch, width=6.5 * inch, height=2.2 * inch)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="skillverify-passport.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_interview_view(request):
    session = AIInterviewSession.objects.filter(user=request.user).first()
    return Response(_advanced_session_payload(request.user, session))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_interview_action_view(request):
    action = request.data.get('action')
    if action == 'start':
        profile = _normalize_advanced_interview_profile(request.user, request.data)
        questions = _select_advanced_questions(request.user, profile)
        if not questions:
            return Response({'error': 'AI question generation failed'}, status=502)
        first = questions[0] if questions else None
        summary = _advanced_summary_payload([], questions, profile, score=0)
        metrics = _advanced_metrics_payload([], questions, 0, summary)
        tips = _advanced_tips_payload([], summary)
        AIInterviewSession.objects.filter(user=request.user, status='active').update(
            status='completed',
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        session = AIInterviewSession.objects.create(
            user=request.user,
            transcript=[{
                'speaker': 'AI',
                'text': first.get('question') if first else 'Tell me about a recent project you built.',
                'difficulty': first.get('difficulty') if first else 'easy',
                'panelist': first.get('panelist') if first else 'Hiring Manager',
                'competency': first.get('competency') if first else 'communication',
                'question_index': 0,
            }],
            questions=questions,
            answers=[],
            current_index=0,
            score=0,
            metrics=metrics,
            tips=tips,
            session_profile=profile,
            summary=summary,
        )
        return Response(_advanced_session_payload(request.user, session))

    session = AIInterviewSession.objects.filter(user=request.user, status='active').first()
    if not session:
        return Response({'error': 'No active session'}, status=400)

    if action == 'respond':
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'Message required'}, status=400)
        questions = session.questions or []
        if not questions:
            return Response({'error': 'No questions available'}, status=400)

        index = session.current_index
        if index >= len(questions):
            return Response({'error': 'Interview already completed'}, status=400)

        current = questions[index]
        profile = session.session_profile or _advanced_interview_defaults(request.user)
        analysis = _evaluate_advanced_answer(message, current, profile)

        answers = list(session.answers or [])
        answers.append({
            "question": current.get("question"),
            "difficulty": current.get("difficulty"),
            "competency": current.get("competency"),
            "panelist": current.get("panelist"),
            "answer": message,
            "word_count": analysis.get("word_count", 0),
            "points": analysis.get("points", 0),
            "analysis": analysis,
        })

        transcript = list(session.transcript or [])
        transcript.append({
            'speaker': 'You',
            'text': message,
            'difficulty': current.get("difficulty"),
            'panelist': current.get("panelist"),
            'competency': current.get("competency"),
            'question_index': index,
        })

        session.score = (session.score or 0) + int(analysis.get("points", 0) or 0)

        followup = _generate_advanced_followup(message, current, profile, analysis, current_questions=questions)
        if followup:
            questions.insert(index + 1, followup)

        if index + 1 < len(questions):
            next_q = questions[index + 1]
            transcript.append({
                'speaker': 'AI',
                'text': next_q.get('question'),
                'difficulty': next_q.get('difficulty'),
                'panelist': next_q.get('panelist'),
                'competency': next_q.get('competency'),
                'question_index': index + 1,
            })
            session.current_index = index + 1
        else:
            summary = _advanced_summary_payload(answers, questions, profile, score=session.score)
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.current_index = len(questions)
            transcript.append({
                'speaker': 'AI',
                'text': (
                    "Interview completed. "
                    f"Recommendation: {summary.get('recommendation')}. "
                    f"Top strengths: {', '.join(summary.get('strengths', [])[:2])}. "
                    f"Next steps: {', '.join(summary.get('next_steps', [])[:2])}."
                ),
                'difficulty': 'summary',
                'panelist': 'AI Review Board',
                'competency': 'summary',
                'question_index': index,
            })

        summary = _advanced_summary_payload(answers, questions, profile, score=session.score)
        session.answers = answers
        session.questions = questions
        session.transcript = transcript
        session.metrics = _advanced_metrics_payload(answers, questions, session.score, summary)
        session.feedback = _advanced_feedback_payload(analysis)
        session.tips = _advanced_tips_payload(answers, summary)
        session.summary = summary
        session.save(update_fields=[
            'answers',
            'transcript',
            'questions',
            'metrics',
            'feedback',
            'tips',
            'score',
            'summary',
            'current_index',
            'status',
            'completed_at',
            'updated_at',
        ])
        if session.status == 'completed':
            _maybe_mark_profile_verified(request.user, session)
            _create_notification(
                request.user,
                "Interview session completed",
                "Your mock interview history and latest score are now available.",
                category="verification" if request.user.profile_verified else "student",
                link="/dashboard/interview",
                metadata={
                    "session_id": session.id,
                    "score": _advanced_state_payload(session)["score"],
                    "readiness": summary.get("readiness_score", 0),
                },
            )

        return Response(_advanced_session_payload(request.user, session))

    if action == 'finish':
        profile = session.session_profile or _advanced_interview_defaults(request.user)
        summary = _advanced_summary_payload(session.answers or [], session.questions or [], profile, score=session.score or 0)
        transcript = list(session.transcript or [])
        if not transcript or transcript[-1].get('difficulty') != 'summary':
            transcript.append({
                'speaker': 'AI',
                'text': (
                    f"Session closed. Recommendation: {summary.get('recommendation')}. "
                    f"Primary next step: {(summary.get('next_steps') or ['Review the weakest interview dimension.'])[0]}"
                ),
                'difficulty': 'summary',
                'panelist': 'AI Review Board',
                'competency': 'summary',
                'question_index': session.current_index,
            })
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.summary = summary
        session.metrics = _advanced_metrics_payload(session.answers or [], session.questions or [], session.score or 0, summary)
        session.tips = _advanced_tips_payload(session.answers or [], summary)
        session.transcript = transcript
        session.current_index = len(session.questions or [])
        session.save(update_fields=['status', 'completed_at', 'summary', 'metrics', 'tips', 'transcript', 'current_index', 'updated_at'])
        _maybe_mark_profile_verified(request.user, session)
        _create_notification(
            request.user,
            "Interview session ended",
            "Review coach notes and use the history panel to compare attempts.",
            category="student",
            link="/dashboard/interview",
            metadata={
                "session_id": session.id,
                "score": _advanced_state_payload(session)["score"],
                "readiness": summary.get("readiness_score", 0),
            },
        )
        return Response(_advanced_session_payload(request.user, session))

    return Response({'error': 'Invalid action'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_dashboard_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)
    _bootstrap_notifications_for_user(request.user)
    requested_job_id = _safe_int(request.query_params.get('job_id'), default=0)
    jobs = list(RecruiterJob.objects.filter(recruiter=request.user))
    selected_job = next((job for job in jobs if job.id == requested_job_id), None)
    if not selected_job and jobs:
        selected_job = next((job for job in jobs if job.status == 'open'), jobs[0])

    students = User.objects.filter(role='student').prefetch_related(
        'scorecards',
        'skills',
        'documents',
        'submissions',
        'ai_interviews',
        'code_analysis_reports',
    )
    pipeline_entries = list(
        RecruiterCandidatePipeline.objects.filter(recruiter=request.user).select_related('candidate', 'job')
    )
    pipeline_map = {
        (entry.candidate_id, entry.job_id): entry
        for entry in pipeline_entries
    }
    generic_pipeline_map = {
        entry.candidate_id: entry
        for entry in pipeline_entries
        if entry.job_id is None
    }

    candidates = []
    for student in students:
        payload = _student_summary_payload(student)
        match = _job_match_payload(payload, selected_job, student)
        pipeline_entry = (
            pipeline_map.get((student.id, selected_job.id if selected_job else None))
            if selected_job
            else generic_pipeline_map.get(student.id)
        )
        payload['match_score'] = (
            int(pipeline_entry.match_score or 0)
            if pipeline_entry and pipeline_entry.match_score
            else match['score']
        )
        payload['match_reasons'] = match['reasons']
        payload['matched_skills'] = match['matched_skills']
        payload['missing_skills'] = match['missing_skills']
        payload['semantic_score'] = match['semantic_score']
        payload['matched_keywords'] = match['matched_keywords']
        payload['missing_keywords'] = match['missing_keywords']
        payload['pipeline'] = _candidate_pipeline_payload(pipeline_entry)
        candidates.append(payload)

    sort_key = "match_score" if selected_job else "score"
    candidates = sorted(
        candidates,
        key=lambda item: (-item[sort_key], -item["score"], item["name"].lower()),
    )
    summary = {
        "candidates": len(candidates),
        "average_ready": _score_mean([item["score"] for item in candidates]),
        "verified_profiles": sum(1 for item in candidates if item["profile_verified"]),
        "shortlist_ready": sum(1 for item in candidates if item["score"] >= 75),
        "active_jobs": sum(1 for job in jobs if job.status == 'open'),
        "shortlisted": sum(1 for entry in pipeline_entries if entry.status == 'shortlisted'),
    }
    available_skills = sorted({
        skill["name"]
        for candidate in candidates
        for skill in candidate.get("skills", [])
        if skill.get("name")
    })
    job_payloads = []
    for job in jobs[:10]:
        top_matches = 0
        for candidate in candidates:
            if _job_match_payload(candidate, job, None)["score"] >= max(int(job.min_ready_score or 0), 60):
                top_matches += 1
        item = _job_payload(job)
        item["top_matches"] = top_matches
        job_payloads.append(item)

    schedules = InterviewSchedule.objects.filter(recruiter=request.user).select_related('candidate', 'job')[:12]

    return Response({
        'summary': summary,
        'filters': {
            'skills': available_skills[:20],
        },
        'selected_job_id': selected_job.id if selected_job else None,
        'jobs': job_payloads,
        'saved_searches': [
            _saved_search_payload(search)
            for search in RecruiterSavedSearch.objects.filter(recruiter=request.user)[:8]
        ],
        'pipeline_summary': _pipeline_summary_for_entries(pipeline_entries),
        'interview_schedules': [_interview_schedule_payload(schedule) for schedule in schedules],
        'candidates': candidates,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recruiter_jobs_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        title = (request.data.get('title') or '').strip()
        if not title:
            return Response({'error': 'Job title is required'}, status=400)
        job = RecruiterJob.objects.create(
            recruiter=request.user,
            title=title,
            description=(request.data.get('description') or '').strip(),
            required_skills=_normalize_string_list(request.data.get('required_skills')),
            preferred_skills=_normalize_string_list(request.data.get('preferred_skills')),
            min_ready_score=_safe_int(request.data.get('min_ready_score'), default=60),
            status=(request.data.get('status') or 'open').strip() or 'open',
        )
        _create_notification(
            request.user,
            "Job brief saved",
            f"{job.title} is ready for candidate matching.",
            category="recruiter",
            link="/recruiter/dashboard",
            metadata={"job_id": job.id},
        )
        return Response({'job': _job_payload(job)}, status=201)

    return Response({
        'jobs': [_job_payload(job) for job in RecruiterJob.objects.filter(recruiter=request.user)],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recruiter_pipeline_view(request, candidate_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    candidate = User.objects.filter(role='student', id=candidate_id).prefetch_related(
        'scorecards',
        'skills',
        'documents',
    ).first()
    if not candidate:
        return Response({'error': 'Candidate not found'}, status=404)

    job = None
    job_id = _safe_int(request.data.get('job_id'), default=0)
    if job_id:
        job = RecruiterJob.objects.filter(recruiter=request.user, id=job_id).first()
        if not job:
            return Response({'error': 'Job not found'}, status=404)

    status_value = (request.data.get('status') or 'sourced').strip() or 'sourced'
    tags = _normalize_string_list(request.data.get('tags'))
    notes = (request.data.get('notes') or '').strip()
    assignee_name = (request.data.get('assignee_name') or '').strip()
    next_step = (request.data.get('next_step') or '').strip()
    rejection_reason = (request.data.get('rejection_reason') or '').strip()
    follow_up_raw = (request.data.get('follow_up_at') or '').strip()
    follow_up_at = None
    if follow_up_raw:
        try:
            follow_up_at = timezone.datetime.fromisoformat(follow_up_raw.replace("Z", "+00:00"))
            if timezone.is_naive(follow_up_at):
                follow_up_at = timezone.make_aware(follow_up_at, timezone.get_current_timezone())
        except (TypeError, ValueError):
            follow_up_at = None
    candidate_payload = _student_summary_payload(candidate)
    match = _job_match_payload(candidate_payload, job, candidate)
    pipeline_entry, _ = RecruiterCandidatePipeline.objects.update_or_create(
        recruiter=request.user,
        candidate=candidate,
        job=job,
        defaults={
            'status': status_value,
            'notes': notes,
            'tags': tags,
            'match_score': match['score'],
            'assignee_name': assignee_name,
            'next_step': next_step,
            'rejection_reason': rejection_reason,
            'follow_up_at': follow_up_at,
            'last_contacted_at': timezone.now() if request.data.get('contacted') else None,
        },
    )

    if status_value in {'shortlisted', 'interviewing', 'offered'}:
        _create_notification(
            candidate,
            "Recruiter activity",
            f"Your profile moved to {status_value.replace('_', ' ')} for {job.title if job else 'a recruiter review'}.",
            category="student",
            link="/dashboard",
            metadata={"job_id": job.id if job else None, "status": status_value},
        )

    return Response({
        'pipeline': _candidate_pipeline_payload(pipeline_entry),
        'match': match,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def interview_schedules_view(request):
    if request.method == 'POST':
        if not _require_role(request.user, 'recruiter'):
            return Response({'error': 'Unauthorized'}, status=403)
        candidate_id = _safe_int(request.data.get('candidate_id'), default=0)
        candidate = User.objects.filter(role='student', id=candidate_id).first()
        if not candidate:
            return Response({'error': 'Candidate not found'}, status=404)
        scheduled_at_raw = (request.data.get('scheduled_at') or '').strip()
        if not scheduled_at_raw:
            return Response({'error': 'Interview date and time are required'}, status=400)
        try:
            scheduled_at = timezone.datetime.fromisoformat(scheduled_at_raw.replace("Z", "+00:00"))
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
        except (TypeError, ValueError):
            return Response({'error': 'Invalid interview date format'}, status=400)

        job = None
        job_id = _safe_int(request.data.get('job_id'), default=0)
        if job_id:
            job = RecruiterJob.objects.filter(recruiter=request.user, id=job_id).first()
            if not job:
                return Response({'error': 'Job not found'}, status=404)

        schedule = InterviewSchedule.objects.create(
            recruiter=request.user,
            candidate=candidate,
            job=job,
            title=(request.data.get('title') or '').strip() or f"{job.title if job else 'Interview'} discussion",
            scheduled_at=scheduled_at,
            duration_minutes=max(15, _safe_int(request.data.get('duration_minutes'), default=30)),
            meeting_link=(request.data.get('meeting_link') or '').strip(),
            notes=(request.data.get('notes') or '').strip(),
        )
        _create_notification(
            candidate,
            "Interview scheduled",
            f"{request.user.full_name or request.user.username} scheduled an interview on {timezone.localtime(schedule.scheduled_at).strftime('%b %d, %Y %I:%M %p')}.",
            category="student",
            link="/dashboard",
            metadata={"schedule_id": schedule.id, "job_id": schedule.job_id},
        )
        return Response({'schedule': _interview_schedule_payload(schedule)}, status=201)

    if _require_role(request.user, 'recruiter'):
        schedules = InterviewSchedule.objects.filter(recruiter=request.user).select_related('candidate', 'job')[:20]
    elif _require_role(request.user, 'student'):
        schedules = InterviewSchedule.objects.filter(candidate=request.user).select_related('recruiter', 'job')[:20]
    else:
        return Response({'schedules': []})

    return Response({'schedules': [_interview_schedule_payload(schedule) for schedule in schedules]})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recruiter_saved_searches_view(request):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'error': 'Search name is required'}, status=400)
        filters = request.data.get('filters') if isinstance(request.data.get('filters'), dict) else {}
        saved_search = RecruiterSavedSearch.objects.create(
            recruiter=request.user,
            name=name,
            query=(request.data.get('query') or '').strip(),
            filters=filters,
        )
        return Response({'saved_search': _saved_search_payload(saved_search)}, status=201)

    return Response({
        'saved_searches': [
            _saved_search_payload(search)
            for search in RecruiterSavedSearch.objects.filter(recruiter=request.user)
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_candidate_report_view(request, student_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    student = User.objects.filter(role='student', id=student_id).prefetch_related('scorecards', 'skills', 'documents').first()
    if not student:
        return Response({'error': 'Candidate not found'}, status=404)

    candidate = _student_summary_payload(student)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError:
        return Response({'error': 'PDF export requires the reportlab package.'}, status=500)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 0.75 * inch
    y = height - x_margin

    def draw_line(label, value, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_margin, y, f"{label}:")
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        pdf.drawString(x_margin + 1.45 * inch, y, value or "-")
        y -= 0.2 * inch

    def draw_wrapped(label, value):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_margin, y, f"{label}:")
        y -= 0.16 * inch
        pdf.setFont("Helvetica", 10)
        for line in textwrap.wrap(value or "-", width=88):
            pdf.drawString(x_margin + 0.2 * inch, y, line)
            y -= 0.16 * inch

    pdf.setTitle(f"{candidate['name']} - Candidate Summary")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(x_margin, y, "Recruiter Candidate Summary")
    y -= 0.3 * inch

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x_margin, y, candidate["name"])
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - x_margin, y, candidate["verification_id"])
    y -= 0.26 * inch

    draw_line("Email", candidate["email"])
    draw_line("College", candidate["college"] or "-")
    draw_line("Course", candidate["course"] or "-")
    draw_line("Branch", candidate["branch"] or "-")
    draw_line("Year", candidate["year_of_study"] or "-")
    draw_line("Placement Ready", f"{candidate['scores']['placement_ready']}/100", bold=True)
    draw_line("Coding Skill Index", f"{candidate['scores']['coding_skill_index']}/100")
    draw_line("Communication Score", f"{candidate['scores']['communication_score']}/100")
    draw_line("Authenticity Score", f"{candidate['scores']['authenticity_score']}/100")
    draw_line("Status", candidate["status_label"])
    draw_line("Focus Area", candidate["focus_area"])
    draw_line(
        "Resume",
        candidate["resume_document"]["filename"] if candidate["resume_document"] else "Not uploaded",
    )

    y -= 0.08 * inch
    draw_wrapped("Recommended Action", candidate["recommended_action"])
    draw_wrapped("Top Skills", ", ".join(skill["name"] for skill in candidate["skills"]) or "No skills available")

    links = [url for url in candidate["links"].values() if url]
    draw_wrapped("Portfolio Links", ", ".join(links) if links else "No public links connected")

    if candidate["summary"]:
        draw_wrapped("LinkedIn Summary", candidate["summary"])

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    filename = f"{candidate['name'].replace(' ', '_').lower()}-candidate-summary.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recruiter_candidate_resume_view(request, student_id):
    if not _require_role(request.user, 'recruiter'):
        return Response({'error': 'Unauthorized'}, status=403)

    resume_document = Document.objects.filter(
        user_id=student_id,
        user__role='student',
        doc_type='resume',
    ).first()
    return _resume_file_response(resume_document)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_document_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)
    return _resume_file_response(_latest_resume_document(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_builder_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)
    preview = _resume_preview_payload(request.user)
    preview["generated_at"] = timezone.now().isoformat()
    return Response(preview)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resume_builder_pdf_view(request):
    if not _require_role(request.user, 'student'):
        return Response({'error': 'Unauthorized'}, status=403)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError:
        return Response({'error': 'PDF export requires the reportlab package.'}, status=500)

    preview = _resume_preview_payload(request.user)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    y = height - margin

    def draw_heading(text):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin, y, text)
        y -= 0.22 * inch

    def draw_body(lines, indent=0.0):
        nonlocal y
        pdf.setFont("Helvetica", 10)
        for line in lines:
            for wrapped in textwrap.wrap(line or "-", width=92):
                pdf.drawString(margin + indent, y, wrapped)
                y -= 0.16 * inch
                if y < margin:
                    pdf.showPage()
                    y = height - margin
                    pdf.setFont("Helvetica", 10)

    pdf.setTitle(f"{preview['full_name']} - Resume")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, y, preview["full_name"])
    y -= 0.22 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, y, preview["headline"])
    y -= 0.3 * inch

    draw_heading("Professional Summary")
    draw_body([preview["summary"]])
    y -= 0.08 * inch

    education = preview["education"]
    draw_heading("Education")
    education_lines = [
        " | ".join(
            [
                value
                for value in [
                    education.get("college"),
                    education.get("course"),
                    education.get("branch"),
                    education.get("year_of_study"),
                ]
                if value
            ]
        ) or "Education details pending",
    ]
    if education.get("cgpa") is not None:
        education_lines.append(f"CGPA: {education['cgpa']}")
    draw_body(education_lines)
    y -= 0.08 * inch

    draw_heading("Skills")
    draw_body([
        ", ".join(
            f"{item['name']} ({item['level']}, {item['score']}/100)"
            for item in preview["skills"]
        ) or "No verified skills yet"
    ])
    y -= 0.08 * inch

    draw_heading("Projects")
    project_lines = []
    for project in preview["projects"][:5]:
        project_lines.append(f"{project['title']}: {project['description']}")
    draw_body(project_lines or ["No project evidence available yet"])
    y -= 0.08 * inch

    draw_heading("Highlights")
    draw_body(preview["achievements"] or ["No score highlights available yet"])
    y -= 0.08 * inch

    draw_heading("Links")
    draw_body([f"{item['label']}: {item['url']}" for item in preview["links"]] or ["No public links connected"])

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    _create_notification(
        request.user,
        "Resume generated",
        "Your ATS-ready resume export is ready for download.",
        category="student",
        link="/dashboard/resume-builder",
    )

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="skillsense-resume.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    _bootstrap_notifications_for_user(request.user)
    notifications = Notification.objects.filter(user=request.user)[:12]
    return Response({
        "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
        "notifications": [_notification_payload(notification) for notification in notifications],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read_view(request, notification_id):
    queryset = Notification.objects.filter(user=request.user)
    if notification_id == 0:
        queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"message": "All notifications marked as read"})

    notification = queryset.filter(id=notification_id).first()
    if not notification:
        return Response({'error': 'Notification not found'}, status=404)
    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
    return Response({"notification": _notification_payload(notification)})


def _batch_row_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _coerce_csv_bool(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _ingest_batch_row(university, row):
    email = _batch_row_value(row, "email", "Email")
    if not email:
        return "skipped", None

    full_name = _batch_row_value(row, "full_name", "name", "Name")
    username = email.split("@")[0] or (full_name.replace(" ", "").lower() if full_name else email)
    defaults = {
        "username": username[:150],
        "role": "student",
    }
    student, created = User.objects.get_or_create(email=email, defaults=defaults)
    if created:
        student.set_unusable_password()

    student.username = student.username or username[:150]
    student.role = "student"
    student.full_name = full_name or student.full_name
    student.college = _batch_row_value(row, "college", "College") or student.college
    student.course = _batch_row_value(row, "course", "Course") or student.course
    student.branch = _batch_row_value(row, "branch", "Branch") or student.branch
    student.year_of_study = _batch_row_value(row, "year_of_study", "year", "Year") or student.year_of_study
    cgpa_value = _batch_row_value(row, "cgpa", "CGPA")
    if cgpa_value:
        try:
            student.cgpa = float(cgpa_value)
        except (TypeError, ValueError):
            pass
    student.student_skills = _batch_row_value(row, "student_skills", "skills", "Skills") or student.student_skills
    verified_value = _batch_row_value(row, "profile_verified", "verified")
    if verified_value:
        student.profile_verified = _coerce_csv_bool(verified_value)
    student.save()

    score_map = {
        "placement_ready": _safe_int(_batch_row_value(row, "placement_ready", "ready_score")),
        "coding_skill_index": _safe_int(_batch_row_value(row, "coding_skill_index", "coding_score")),
        "communication_score": _safe_int(_batch_row_value(row, "communication_score", "communication")),
        "authenticity_score": _safe_int(_batch_row_value(row, "authenticity_score", "authenticity")),
    }
    if any(score_map.values()):
        for score_type, score in score_map.items():
            ScoreCard.objects.update_or_create(
                user=student,
                score_type=score_type,
                defaults={"score": score, "change": 0},
            )
        ScoreSnapshot.objects.update_or_create(
            user=student,
            recorded_on=timezone.localdate(),
            defaults={"scores": score_map},
        )

    imported_skills = _normalize_string_list(_batch_row_value(row, "student_skills", "skills", "Skills"))
    verified_skills = {
        item.lower()
        for item in _normalize_string_list(_batch_row_value(row, "verified_skills", "Verified Skills"))
    }
    coding_score = score_map["coding_skill_index"]
    inferred_level = (
        "advanced" if coding_score >= 75 else "intermediate" if coding_score >= 55 else "beginner"
    )
    inferred_score = coding_score or max(score_map["placement_ready"], 50)
    for skill_name in imported_skills[:15]:
        Skill.objects.update_or_create(
            user=student,
            name=skill_name,
            defaults={
                "level": inferred_level,
                "score": inferred_score,
                "verified": student.profile_verified or skill_name.lower() in verified_skills,
            },
        )

    _create_notification(
        student,
        "University profile synced",
        f"{university.full_name or university.username} updated your cohort profile data.",
        category="student",
        link="/dashboard",
        metadata={"source": "batch_upload"},
    )
    return ("created" if created else "updated"), student


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def university_dashboard_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)
    _bootstrap_notifications_for_user(request.user)
    branch = (request.query_params.get('branch') or '').strip()
    course = (request.query_params.get('course') or '').strip()
    year_of_study = (request.query_params.get('year_of_study') or '').strip()

    students = User.objects.filter(role='student')
    if branch:
        students = students.filter(branch=branch)
    if course:
        students = students.filter(course=course)
    if year_of_study:
        students = students.filter(year_of_study=year_of_study)

    students = students.prefetch_related('scorecards', 'skills', 'documents')
    student_payloads = sorted(
        [_student_summary_payload(student) for student in students],
        key=lambda item: (-item["score"], item["name"].lower()),
    )
    totals = len(student_payloads)
    placement_scores = [student["scores"]["placement_ready"] for student in student_payloads]
    coding_scores = [student["scores"]["coding_skill_index"] for student in student_payloads]
    authenticity_scores = [student["scores"]["authenticity_score"] for student in student_payloads]
    verified_profiles = sum(1 for student in student_payloads if student["profile_verified"])
    need_attention = sum(1 for student in student_payloads if student["needs_attention"])
    student_ids = [student["id"] for student in student_payloads]
    all_students = User.objects.filter(role='student')
    intervention_map = {
        record.student_id: record
        for record in InterventionRecord.objects.filter(
            university=request.user,
            student_id__in=student_ids,
        )
    }
    interventions = []
    for item in _interventions_for_students(student_payloads):
        record = intervention_map.get(item["id"])
        item["status"] = record.status if record else "planned"
        item["priority"] = record.priority if record else item["severity"]
        item["note"] = record.note if record else ""
        item["recommended_action"] = record.recommended_action if record and record.recommended_action else item["action"]
        item["record"] = _intervention_record_payload(record)
        interventions.append(item)
    drives = [
        _placement_drive_payload(drive, student_payloads)
        for drive in PlacementDrive.objects.filter(university=request.user)[:8]
    ]
    return Response({
        'summary': {
            'students': totals,
            'average_ready': _score_mean(placement_scores),
            'average_coding': _score_mean(coding_scores),
            'average_authenticity': _score_mean(authenticity_scores),
            'verified_profiles': verified_profiles,
            'need_attention': need_attention,
            'tracked_interventions': sum(
                1 for record in intervention_map.values() if record.status != 'completed'
            ),
        },
        'filters': {
            'branches': sorted(filter(None, all_students.values_list('branch', flat=True).distinct())),
            'courses': sorted(filter(None, all_students.values_list('course', flat=True).distinct())),
            'years': sorted(filter(None, all_students.values_list('year_of_study', flat=True).distinct())),
        },
        'readiness_breakdown': [
            {'name': 'Ready', 'count': sum(1 for item in student_payloads if item['score'] >= 75)},
            {'name': 'Almost Ready', 'count': sum(1 for item in student_payloads if 60 <= item['score'] < 75)},
            {'name': 'Needs Support', 'count': sum(1 for item in student_payloads if item['score'] < 60)},
        ],
        'skill_distribution': _skill_distribution_for_students(student_payloads),
        'placement_trend': _trend_for_students(student_ids, student_payloads),
        'interventions': interventions,
        'top_students': student_payloads[:5],
        'students': student_payloads,
        'batch_uploads': [
            _batch_upload_payload(batch_upload)
            for batch_upload in UniversityBatchUpload.objects.filter(university=request.user)[:5]
        ],
        'placement_drives': drives,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def university_batch_upload_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    upload = request.FILES.get('file')
    if not upload:
        return Response({'error': 'CSV file is required'}, status=400)

    try:
        content = upload.read().decode('utf-8-sig')
    except Exception:
        return Response({'error': 'Unable to read CSV file'}, status=400)

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return Response({'error': 'CSV file must contain a header row'}, status=400)

    summary = {"created": 0, "updated": 0, "skipped": 0}
    with transaction.atomic():
        for row in reader:
            result, _student = _ingest_batch_row(request.user, row)
            if result in summary:
                summary[result] += 1
            else:
                summary["skipped"] += 1

        try:
            upload.seek(0)
        except Exception:
            pass
        batch_upload = UniversityBatchUpload.objects.create(
            university=request.user,
            filename=upload.name or "cohort.csv",
            file=upload,
            summary=summary,
            status='completed',
        )

    _create_notification(
        request.user,
        "Batch upload completed",
        f"Created {summary['created']} and updated {summary['updated']} student records.",
        category="university",
        link="/university/dashboard",
        metadata={"batch_upload_id": batch_upload.id, **summary},
    )
    return Response(
        {
            "batch_upload": _batch_upload_payload(batch_upload),
            "summary": summary,
        },
        status=201,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def university_intervention_view(request, student_id):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    student = User.objects.filter(role='student', id=student_id).first()
    if not student:
        return Response({'error': 'Student not found'}, status=404)

    status_value = (request.data.get('status') or 'planned').strip() or 'planned'
    priority = (request.data.get('priority') or 'medium').strip() or 'medium'
    note = (request.data.get('note') or '').strip()
    recommended_action = (request.data.get('recommended_action') or '').strip()

    record, _ = InterventionRecord.objects.update_or_create(
        university=request.user,
        student=student,
        defaults={
            'status': status_value,
            'priority': priority,
            'note': note,
            'recommended_action': recommended_action,
        },
    )
    _create_notification(
        student,
        "University support plan updated",
        f"Intervention status changed to {status_value.replace('_', ' ')}.",
        category="student",
        link="/dashboard/progress",
        metadata={"priority": priority},
    )
    return Response({'intervention': _intervention_record_payload(record)})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def university_placement_drives_view(request):
    if not _require_role(request.user, 'university'):
        return Response({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        company_name = (request.data.get('company_name') or '').strip()
        role_title = (request.data.get('role_title') or '').strip()
        if not company_name or not role_title:
            return Response({'error': 'Company name and role title are required'}, status=400)
        scheduled_on = None
        scheduled_on_raw = (request.data.get('scheduled_on') or '').strip()
        if scheduled_on_raw:
            try:
                scheduled_on = timezone.datetime.fromisoformat(scheduled_on_raw).date()
            except (TypeError, ValueError):
                scheduled_on = None
        drive = PlacementDrive.objects.create(
            university=request.user,
            company_name=company_name,
            role_title=role_title,
            description=(request.data.get('description') or '').strip(),
            target_branches=_normalize_string_list(request.data.get('target_branches')),
            target_courses=_normalize_string_list(request.data.get('target_courses')),
            minimum_ready_score=_safe_int(request.data.get('minimum_ready_score'), default=65),
            scheduled_on=scheduled_on,
            status=(request.data.get('status') or 'planning').strip() or 'planning',
        )
        students = [
            _student_summary_payload(student)
            for student in User.objects.filter(role='student').prefetch_related('scorecards', 'skills', 'documents')
        ]
        return Response({'drive': _placement_drive_payload(drive, students)}, status=201)

    students = [
        _student_summary_payload(student)
        for student in User.objects.filter(role='student').prefetch_related('scorecards', 'skills', 'documents')
    ]
    drives = [
        _placement_drive_payload(drive, students)
        for drive in PlacementDrive.objects.filter(university=request.user)
    ]
    return Response({'placement_drives': drives})




@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def code_analysis_view(request):
    if request.method == 'POST':
        repo_url = (request.data.get('repo_url') or '').strip()
        if not repo_url:
            return Response({'error': 'Repository URL is required'}, status=400)
        owner, repo_name = _extract_github_repo_owner_and_name(repo_url)
        if not owner:
            owner = _extract_github_username(request.user.github_link)
        if not owner or not repo_name:
            return Response({'error': 'Valid GitHub repository URL is required'}, status=400)
        try:
            analysis = _analyze_repository_work(owner, repo_name, user=request.user)
        except Exception:
            analysis = {"error": "Unable to analyze repository right now."}
        if not isinstance(analysis, dict) or analysis.get("error"):
            return Response({'error': (analysis or {}).get("error") or 'Unable to analyze repository'}, status=400)

        report, _ = CodeAnalysisReport.objects.update_or_create(
            user=request.user,
            repo_url=analysis['repo_url'],
            defaults={
                'summary': analysis.get('summary') or 'Repository engineering analysis.',
                'score': analysis.get("engineering_score", 0),
                'metrics': {
                    "engineering_score": analysis.get("engineering_score", 0),
                    "maintainability_score": analysis.get("maintainability_score", 0),
                    "security_score": analysis.get("security_score", 0),
                    "testing_score": analysis.get("testing_score", 0),
                    "documentation_score": analysis.get("documentation_score", 0),
                    "architecture_score": analysis.get("architecture_score", 0),
                    "originality_score": analysis.get("originality_score", 0),
                    "ai_generated": analysis.get("ai_generated"),
                    "ai_confidence": analysis.get("ai_confidence", 0),
                    "languages": analysis.get("languages", []),
                    "files_analyzed": analysis.get("files_analyzed", 0),
                    "lines_analyzed": analysis.get("lines_analyzed", 0),
                    "tree_overview": analysis.get("tree_overview", {}),
                    "commit_activity": analysis.get("commit_activity", {}),
                    "architecture": analysis.get("architecture", []),
                    "strengths": analysis.get("strengths", []),
                    "risks": analysis.get("risks", []),
                    "recommendations": analysis.get("recommendations", []),
                    "file_reviews": analysis.get("file_reviews", []),
                    "ai_review": analysis.get("ai_review"),
                    "stars": analysis.get("stars", 0),
                    "forks": analysis.get("forks", 0),
                    "open_issues": analysis.get("open_issues", 0),
                    "default_branch": analysis.get("default_branch"),
                    "pushed_at": analysis.get("pushed_at"),
                },
                'status': 'completed',
            },
        )
        return Response({
            "id": report.id,
            "repo_name": analysis.get("repo_name"),
            "repo_url": analysis.get("repo_url"),
            "description": report.summary,
            "score": report.score,
            "metrics": report.metrics,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
        })

    items = []
    for report in CodeAnalysisReport.objects.filter(user=request.user):
        repo_name = report.repo_url.rstrip('/').split('/')[-1]
        items.append({
            'id': report.id,
            'repo_name': repo_name,
            'repo_url': report.repo_url,
            'description': report.summary,
            'score': report.score,
            'metrics': report.metrics,
            'status': report.status,
            'created_at': report.created_at.isoformat(),
        })
    return Response({'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def code_analysis_file_view(request, report_id):
    report = CodeAnalysisReport.objects.filter(user=request.user, id=report_id).first()
    if not report:
        return Response({'error': 'Analysis report not found'}, status=404)
    path = (request.query_params.get('path') or '').strip()
    if not path:
        return Response({'error': 'File path is required'}, status=400)
    snapshot = RepoFileSnapshot.objects.filter(
        user=request.user,
        repo_url=report.repo_url,
        path=path,
    ).order_by('-created_at').first()
    if not snapshot:
        return Response({'error': 'File preview not found'}, status=404)
    file_reviews = report.metrics.get("file_reviews", []) if isinstance(report.metrics, dict) else []
    review = next((item for item in file_reviews if item.get("path") == path), None)
    preview_chars = _repo_preview_chars()
    preview = snapshot.content[:preview_chars]
    return Response({
        'path': snapshot.path,
        'sha': snapshot.sha,
        'size': snapshot.size,
        'lines': snapshot.lines,
        'preview': preview,
        'truncated': len(snapshot.content or "") > preview_chars,
        'review': review,
    })




@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def media_view(request):
    if request.method == 'POST':
        upload = request.FILES.get('file')
        title = (request.data.get('title') or '').strip()
        media_type = (request.data.get('media_type') or '').strip()
        if not upload or not media_type:
            return Response({'error': 'File and media_type are required'}, status=400)
        if media_type not in ['video', 'audio']:
            return Response({'error': 'media_type must be video or audio'}, status=400)
        if not title:
            title = upload.name
        media = MediaUpload.objects.create(
            user=request.user,
            title=title,
            media_type=media_type,
            file=upload,
            status='ready',
        )
        return Response({
            'id': media.id,
            'title': media.title,
            'media_type': media.media_type,
            'status': media.status,
            'file_url': media.file.url,
            'created_at': media.created_at.isoformat(),
        })
    items = [
        {
            'id': item.id,
            'title': item.title,
            'media_type': item.media_type,
            'status': item.status,
            'file_url': item.file.url,
            'created_at': item.created_at.isoformat(),
        }
        for item in MediaUpload.objects.filter(user=request.user)
    ]
    return Response({'items': items})




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def progress_view(request):
    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(user=request.user, recorded_on__gte=cutoff).order_by('recorded_on')
    series = [
        {
            'date': snap.recorded_on.isoformat(),
            **(snap.scores or {}),
        }
        for snap in snapshots
    ]
    streak = 0
    if snapshots.exists():
        dates = {snap.recorded_on for snap in snapshots}
        day = timezone.localdate()
        while day in dates:
            streak += 1
            day = day - timedelta(days=1)
    milestones = {
        'skills': request.user.skills.count(),
    }
    return Response({
        'series': series,
        'streak': streak,
        'milestones': milestones,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def roadmap_view(request):
    scores = calculate_student_scores(request.user) if request.user.role == 'student' else {}
    items = []
    if scores.get('coding_skill_index', 0) < 70:
        items.append({
            'title': 'Algorithm mastery sprint',
            'description': 'Solve 15 medium problems over 3 weeks.',
            'status': 'in_progress',
        })
    if scores.get('communication_score', 0) < 70:
        items.append({
            'title': 'Profile narrative upgrade',
            'description': 'Refine LinkedIn summary and add 2 experience bullets.',
            'status': 'pending',
        })
    if not items:
        items.append({
            'title': 'Maintain momentum',
            'description': 'Keep shipping weekly updates to sustain your scores.',
            'status': 'completed',
        })
    return Response({'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def settings_view(request):
    return Response({'settings': {}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_view(request):
    user = request.user
    if user.role != "student":
        return Response({"series": []})

    cutoff = timezone.localdate() - timedelta(days=90)
    snapshots = ScoreSnapshot.objects.filter(user=user, recorded_on__gte=cutoff).order_by("recorded_on")

    if not snapshots.exists():
        scores = upsert_scorecards(user)
        today = timezone.localdate()
        ScoreSnapshot.objects.update_or_create(
            user=user,
            recorded_on=today,
            defaults={"scores": scores},
        )
        snapshots = ScoreSnapshot.objects.filter(user=user, recorded_on__gte=cutoff).order_by("recorded_on")

    series = []
    for snapshot in snapshots:
        scores = snapshot.scores or {}
        series.append({
            "date": snapshot.recorded_on.isoformat(),
            "coding_skill_index": scores.get("coding_skill_index", 0),
            "communication_score": scores.get("communication_score", 0),
            "authenticity_score": scores.get("authenticity_score", 0),
            "placement_ready": scores.get("placement_ready", 0),
        })

    return Response({"series": series})
