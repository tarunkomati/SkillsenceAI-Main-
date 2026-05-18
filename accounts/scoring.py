from datetime import timedelta
from urllib.parse import urlparse
import json
import os
import time
import urllib.request
import urllib.error

from django.utils import timezone
from skills.models import ScoreCard, Skill, ScoreSnapshot


def _split_skills(skills_text):
    if not skills_text:
        return []
    return [item.strip() for item in skills_text.split(",") if item.strip()]


def _cgpa_bonus(cgpa_value):
    if cgpa_value is None:
        return 0
    try:
        cgpa = float(cgpa_value)
    except (TypeError, ValueError):
        return 0
    if cgpa >= 9:
        return 10
    if cgpa >= 8:
        return 7
    if cgpa >= 7:
        return 4
    return 2


def _extract_username(url, fallback_segments=1):
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return None
        parts = [segment for segment in path.split("/") if segment]
        if not parts:
            return None
        return parts[-fallback_segments]
    except Exception:
        return None


def _http_json(method, url, payload=None, headers=None, timeout=8):
    if headers is None:
        headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_github_stats(username):
    if not username:
        return None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "skillsence-ai",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    user_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"

    profile = _http_json("GET", user_url, headers=headers)
    repos = _http_json("GET", repos_url, headers=headers)

    repo_count = len(repos)
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    total_forks = sum(repo.get("forks_count", 0) for repo in repos)
    languages = sorted({repo.get("language") for repo in repos if repo.get("language")})

    forked_count = sum(1 for repo in repos if repo.get("fork"))
    original_count = max(0, repo_count - forked_count)
    fork_ratio = round(forked_count / repo_count, 3) if repo_count else 0

    language_counts = {}
    for repo in repos:
        language = repo.get("language")
        if not language:
            continue
        language_counts[language] = language_counts.get(language, 0) + 1
    top_languages = sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[:6]

    recent_cutoff = timezone.now() - timedelta(days=180)
    recent_repos = 0
    for repo in repos:
        pushed_at = repo.get("pushed_at")
        if not pushed_at:
            continue
        try:
            pushed_time = timezone.datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if pushed_time >= recent_cutoff:
            recent_repos += 1

    return {
        "profile": {
            "public_repos": profile.get("public_repos", repo_count),
            "followers": profile.get("followers", 0),
            "following": profile.get("following", 0),
        },
        "repos": {
            "count": repo_count,
            "stars": total_stars,
            "forks": total_forks,
            "recent_repos": recent_repos,
            "languages": languages,
            "forked": forked_count,
            "original": original_count,
            "fork_ratio": fork_ratio,
            "top_languages": top_languages,
        },
        "originality": {
            "fork_ratio": fork_ratio,
            "note": "Higher original repos increase authenticity.",
        },
        "fetched_at": timezone.now().isoformat(),
    }


def _fetch_leetcode_stats(username):
    if not username:
        return None
    query = """
    query userStats($username: String!) {
      matchedUser(username: $username) {
        username
        submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
            submissions
          }
        }
        submitStats {
          acSubmissionNum {
            difficulty
            count
            submissions
          }
        }
        profile {
          ranking
          reputation
          starRating
        }
      }
    }
    """
    payload = {"query": query, "variables": {"username": username}}
    headers = {
        "Accept": "application/json",
        "User-Agent": "skillsence-ai",
    }
    data = _http_json("POST", "https://leetcode.com/graphql", payload=payload, headers=headers)
    matched = (data or {}).get("data", {}).get("matchedUser")
    if not matched:
        return {"error": "User not found"}
    stats_global = matched.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
    stats_local = matched.get("submitStats", {}).get("acSubmissionNum", [])
    totals_global = {item.get("difficulty"): item.get("count", 0) for item in stats_global}
    totals_local = {item.get("difficulty"): item.get("count", 0) for item in stats_local}
    totals = {}
    for difficulty in ["All", "Easy", "Medium", "Hard"]:
        totals[difficulty] = max(totals_global.get(difficulty, 0), totals_local.get(difficulty, 0))
    if not totals.get("All"):
        totals["All"] = totals.get("Easy", 0) + totals.get("Medium", 0) + totals.get("Hard", 0)
    return {
        "username": matched.get("username"),
        "solved": {
            "all": totals.get("All", 0),
            "easy": totals.get("Easy", 0),
            "medium": totals.get("Medium", 0),
            "hard": totals.get("Hard", 0),
        },
        "raw": {
            "submitStatsGlobal": totals_global,
            "submitStats": totals_local,
        },
        "profile": matched.get("profile", {}),
        "fetched_at": timezone.now().isoformat(),
    }


def _language_match_bonus(skills, languages):
    if not skills or not languages:
        return 0
    skill_map = {
        "react": {"JavaScript", "TypeScript"},
        "node": {"JavaScript", "TypeScript"},
        "python": {"Python"},
        "django": {"Python"},
        "flask": {"Python"},
        "java": {"Java"},
        "spring": {"Java"},
        "c++": {"C++"},
        "c": {"C"},
        "javascript": {"JavaScript"},
        "typescript": {"TypeScript"},
        "sql": {"SQL"},
        "aws": {"Python", "JavaScript", "TypeScript"},
    }
    language_set = set(languages)
    matched = 0
    for skill in skills:
        key = skill.lower().strip()
        for mapped_skill, mapped_languages in skill_map.items():
            if mapped_skill in key and language_set.intersection(mapped_languages):
                matched += 1
                break
    return min(10, matched * 2)


def _level_from_score(score):
    if score >= 85:
        return "expert"
    if score >= 70:
        return "advanced"
    if score >= 55:
        return "intermediate"
    return "beginner"


def _linkedin_profile_score(user):
    score = 0
    if user.linkedin_link:
        score += 10
    headline = (user.linkedin_headline or "").strip()
    about = (user.linkedin_about or "").strip()
    experience_count = user.linkedin_experience_count or 0
    skill_count = user.linkedin_skill_count or 0
    cert_count = user.linkedin_cert_count or 0

    if len(headline) >= 12:
        score += 6
    if len(about) >= 60:
        score += 10
    if experience_count >= 1:
        score += 8
    if experience_count >= 3:
        score += 4
    if skill_count >= 5:
        score += 8
    if skill_count >= 15:
        score += 4
    if cert_count >= 1:
        score += 6
    if cert_count >= 3:
        score += 4
    return min(50, score)


def _language_skill_names(languages):
    mapping = {
        "JavaScript": "JavaScript",
        "TypeScript": "TypeScript",
        "Python": "Python",
        "Java": "Java",
        "C++": "C++",
        "C": "C",
        "Go": "Go",
        "Ruby": "Ruby",
        "PHP": "PHP",
        "C#": "C#",
        "HTML": "HTML",
        "CSS": "CSS",
    }
    return {mapping[lang] for lang in languages if lang in mapping}


def sync_skills(user, coding_skill_index):
    skills = _split_skills(user.student_skills)
    github_languages = (user.github_stats or {}).get("repos", {}).get("languages", []) or []
    language_skills = _language_skill_names(github_languages)

    combined = []
    seen = set()
    for skill in skills + sorted(language_skills):
        normalized = skill.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        combined.append(normalized)

    for skill_name in combined:
        score = 40 + round(coding_skill_index * 0.3)
        if skill_name in language_skills:
            score += 20
        score = min(100, score)
        level = _level_from_score(score)
        verified = skill_name in language_skills

        Skill.objects.update_or_create(
            user=user,
            name=skill_name,
            defaults={
                "score": score,
                "level": level,
                "verified": verified,
            },
        )


def analyze_platforms(user, force=False):
    if user.role != "student":
        return {}
    if not force and user.last_analyzed_at:
        if timezone.now() - user.last_analyzed_at < timedelta(hours=12):
            return {
                "github": user.github_stats,
                "leetcode": user.leetcode_stats,
                "linkedin": user.linkedin_stats,
            }

    github_username = _extract_username(user.github_link)
    leetcode_username = _extract_username(user.leetcode_link)

    github_stats = None
    leetcode_stats = None
    linkedin_stats = {
        "linked": bool(user.linkedin_link),
        "headline_len": len((user.linkedin_headline or "").strip()),
        "about_len": len((user.linkedin_about or "").strip()),
        "experience_count": user.linkedin_experience_count or 0,
        "skill_count": user.linkedin_skill_count or 0,
        "cert_count": user.linkedin_cert_count or 0,
    }

    try:
        if github_username:
            github_stats = _fetch_github_stats(github_username)
    except Exception as exc:
        github_stats = {"error": str(exc)}

    time.sleep(0.4)

    try:
        if leetcode_username:
            leetcode_stats = _fetch_leetcode_stats(leetcode_username)
    except Exception as exc:
        leetcode_stats = {"error": str(exc)}

    user.github_stats = github_stats
    user.leetcode_stats = leetcode_stats
    user.linkedin_stats = linkedin_stats
    user.last_analyzed_at = timezone.now()
    user.save(update_fields=["github_stats", "leetcode_stats", "linkedin_stats", "last_analyzed_at"])

    return {
        "github": github_stats,
        "leetcode": leetcode_stats,
        "linkedin": linkedin_stats,
    }


def _compute_scores_and_breakdown(user):
    skills = _split_skills(user.student_skills)
    skills_count = len(skills)

    links = [
        user.github_link,
        user.leetcode_link,
        user.linkedin_link,
        user.codechef_link,
        user.hackerrank_link,
        user.codeforces_link,
        user.gfg_link,
    ]
    platform_count = len([link for link in links if link])

    github_stats = user.github_stats or {}
    leetcode_stats = user.leetcode_stats or {}
    github_repo_count = github_stats.get("repos", {}).get("count", 0) or 0
    github_stars = github_stats.get("repos", {}).get("stars", 0) or 0
    github_languages = github_stats.get("repos", {}).get("languages", []) or []
    recent_repos = github_stats.get("repos", {}).get("recent_repos", 0) or 0
    fork_ratio = github_stats.get("repos", {}).get("fork_ratio", 0) or 0
    forked_repos = github_stats.get("repos", {}).get("forked", 0) or 0
    original_repos = github_stats.get("repos", {}).get("original", 0) or 0

    leetcode_solved = leetcode_stats.get("solved", {}).get("all", 0) or 0
    leetcode_medium = leetcode_stats.get("solved", {}).get("medium", 0) or 0
    leetcode_hard = leetcode_stats.get("solved", {}).get("hard", 0) or 0

    leetcode_profile = leetcode_stats.get("profile", {}) if isinstance(leetcode_stats, dict) else {}
    leetcode_rank = leetcode_profile.get("ranking") or 0
    leetcode_star = leetcode_profile.get("starRating") or 0
    linkedin_profile_score = _linkedin_profile_score(user)

    coding_points = {
        "leetcode_solved_points": min(32, leetcode_solved / 4.5),
        "leetcode_medium_points": min(11, leetcode_medium * 0.55),
        "leetcode_hard_points": min(9, leetcode_hard * 1.1),
        "github_repos": min(18, github_repo_count * 1.7),
        "github_recent": min(11, recent_repos * 1.7),
        "github_stars": min(7, github_stars / 4.5),
        "language_match": _language_match_bonus(skills, github_languages),
        "leetcode_star": min(5, leetcode_star * 1.3),
    }
    coding_parts = {
        **coding_points,
        "leetcode_solved_raw": leetcode_solved,
        "leetcode_easy_raw": leetcode_stats.get("solved", {}).get("easy", 0) or 0,
        "leetcode_medium_raw": leetcode_medium,
        "leetcode_hard_raw": leetcode_hard,
    }
    coding_skill_index = sum(coding_points.values())

    communication_parts = {
        "linkedin_profile": min(40, linkedin_profile_score),
        "phone_presence": 10 if user.phone_number else 0,
        "skills_breadth": min(20, skills_count * 2),
        "college_presence": 10 if user.college else 0,
    }
    communication_score = sum(communication_parts.values())

    authenticity_points = {
        "github_repos": min(22, github_repo_count * 1.7),
        "github_stars": min(18, github_stars / 3.5),
        "github_recent": min(13, recent_repos * 1.7),
        "leetcode_solved": min(18, leetcode_solved / 5.5),
        "github_leetcode_combo": 5 if user.github_link and user.leetcode_link else 0,
        "linkedin_profile": min(9, round(linkedin_profile_score / 5.5)),
        "platform_count": min(10, platform_count * 2),
        "github_originality": round(max(0, 1 - fork_ratio) * 8, 2),
    }
    authenticity_parts = {
        **authenticity_points,
        "github_forked_raw": forked_repos,
        "github_original_raw": original_repos,
    }
    authenticity_score = sum(authenticity_points.values())

    placement_components = {
        "coding_weighted": coding_skill_index * 0.55,
        "communication_weighted": communication_score * 0.2,
        "authenticity_weighted": authenticity_score * 0.25,
        "cgpa_bonus": _cgpa_bonus(user.cgpa),
    }
    placement_ready = sum(placement_components.values())

    scale = 0.92
    scores = {
        "coding_skill_index": min(100, round(coding_skill_index * scale)),
        "communication_score": min(100, round(communication_score * scale)),
        "authenticity_score": min(100, round(authenticity_score * scale)),
        "placement_ready": min(100, round(placement_ready * scale)),
    }
    breakdown = {
        "coding_skill_index": coding_parts,
        "communication_score": communication_parts,
        "authenticity_score": authenticity_parts,
        "placement_ready": placement_components,
    }
    return scores, breakdown


def calculate_student_scores(user):
    scores, _breakdown = _compute_scores_and_breakdown(user)
    return scores


def score_breakdown(user):
    _scores, breakdown = _compute_scores_and_breakdown(user)
    return breakdown


def upsert_scorecards(user):
    analyze_platforms(user, force=False)
    scores = calculate_student_scores(user)
    if user.role == "student":
        sync_skills(user, scores.get("coding_skill_index", 0))
        today = timezone.localdate()
        ScoreSnapshot.objects.update_or_create(
            user=user,
            recorded_on=today,
            defaults={"scores": scores},
        )
    for score_type, score in scores.items():
        previous = ScoreCard.objects.filter(user=user, score_type=score_type).first()
        change = score - previous.score if previous else 0
        ScoreCard.objects.update_or_create(
            user=user,
            score_type=score_type,
            defaults={"score": score, "change": change},
        )
    return scores
