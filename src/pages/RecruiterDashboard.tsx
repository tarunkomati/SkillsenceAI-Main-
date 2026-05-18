import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import {
  BadgeCheck,
  BookmarkPlus,
  Briefcase,
  ClipboardList,
  Download,
  Eye,
  Filter,
  GraduationCap,
  Mail,
  MapPin,
  Search,
  ShieldCheck,
  Star,
  Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { buildApiUrl } from '@/lib/api';
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts';

interface CandidateSkill {
  name: string;
  score: number;
  level: string;
  verified: boolean;
}

interface CandidateScores {
  placement_ready: number;
  coding_skill_index: number;
  communication_score: number;
  authenticity_score: number;
}

interface CandidateLinks {
  github: string;
  leetcode: string;
  linkedin: string;
  codechef: string;
  hackerrank: string;
  codeforces: string;
  gfg: string;
}

interface CandidateResume {
  filename: string;
  uploaded_at: string | null;
  download_path: string;
}

interface Candidate {
  id: number;
  verification_id: string;
  name: string;
  email: string;
  college: string;
  course: string;
  branch: string;
  year_of_study: string;
  cgpa: number | null;
  location: string;
  headline: string;
  summary: string;
  profile_verified: boolean;
  status_label: string;
  focus_area: string;
  recommended_action: string;
  needs_attention: boolean;
  score: number;
  scores: CandidateScores;
  skills: CandidateSkill[];
  verified_skills: number;
  highlights: string[];
  resume_document: CandidateResume | null;
  links: CandidateLinks;
  last_analyzed_at: string | null;
  match_score?: number;
  match_reasons?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  semantic_score?: number;
  matched_keywords?: string[];
  missing_keywords?: string[];
  pipeline?: CandidatePipeline | null;
}

interface CandidatePipeline {
  status: 'sourced' | 'shortlisted' | 'interviewing' | 'offered' | 'rejected';
  notes: string;
  tags: string[];
  match_score: number;
  assignee_name: string;
  next_step: string;
  rejection_reason: string;
  follow_up_at: string | null;
  last_contacted_at: string | null;
  updated_at?: string | null;
}

interface RecruiterJob {
  id: number;
  title: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  min_ready_score: number;
  status: 'open' | 'paused' | 'closed';
  top_matches: number;
  created_at: string | null;
  updated_at: string | null;
}

interface SavedSearch {
  id: number;
  name: string;
  query: string;
  filters: {
    search?: string;
    skill?: string;
    min_score?: number;
    verified_only?: boolean;
    job_id?: number | null;
  };
  updated_at: string | null;
}

interface InterviewSchedule {
  id: number;
  title: string;
  candidate_id: number;
  candidate_name: string;
  recruiter_id: number;
  recruiter_name: string;
  job_id: number | null;
  job_title: string;
  scheduled_at: string | null;
  duration_minutes: number;
  meeting_link: string;
  notes: string;
  status: 'scheduled' | 'completed' | 'cancelled';
}

interface RecruiterSummary {
  candidates: number;
  average_ready: number;
  verified_profiles: number;
  shortlist_ready: number;
  active_jobs: number;
  shortlisted: number;
}

interface RecruiterResponse {
  summary: RecruiterSummary;
  filters: {
    skills: string[];
  };
  selected_job_id: number | null;
  jobs: RecruiterJob[];
  saved_searches: SavedSearch[];
  pipeline_summary: Record<string, number>;
  interview_schedules: InterviewSchedule[];
  candidates: Candidate[];
}

const scoreLabels: Array<{ key: keyof CandidateScores; label: string }> = [
  { key: 'placement_ready', label: 'Placement Ready' },
  { key: 'coding_skill_index', label: 'Coding Skill' },
  { key: 'communication_score', label: 'Communication' },
  { key: 'authenticity_score', label: 'Authenticity' },
];

export default function RecruiterDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<RecruiterResponse | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [profileExpanded, setProfileExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [skillFilter, setSkillFilter] = useState('all');
  const [minScore, setMinScore] = useState('0');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [downloadingResumeId, setDownloadingResumeId] = useState<number | null>(null);
  const [creatingJob, setCreatingJob] = useState(false);
  const [savingPipeline, setSavingPipeline] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);
  const [savedSearchName, setSavedSearchName] = useState('');
  const [jobForm, setJobForm] = useState({
    title: '',
    description: '',
    required_skills: '',
    preferred_skills: '',
    min_ready_score: '65',
  });
  const [pipelineForm, setPipelineForm] = useState({
    status: 'sourced' as CandidatePipeline['status'],
    notes: '',
    tags: '',
    assignee_name: '',
    next_step: '',
    rejection_reason: '',
    follow_up_at: '',
  });
  const [scheduling, setScheduling] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    title: '',
    scheduled_at: '',
    duration_minutes: '30',
    meeting_link: '',
    notes: '',
  });
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const role = localStorage.getItem('userRole');
    if (!token || role !== 'recruiter') {
      navigate('/recruiter');
      return;
    }

    const query = selectedJobId ? `?job_id=${selectedJobId}` : '';
    setLoading(true);
    fetch(buildApiUrl(`/api/skills/recruiter-dashboard/${query}`), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          navigate('/recruiter');
          return null;
        }
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          throw new Error(payload?.error || 'Unable to load recruiter dashboard.');
        }
        return res.json();
      })
      .then((payload: RecruiterResponse | null) => {
        if (!payload) {
          return;
        }
        setData(payload);
        if (payload.selected_job_id !== selectedJobId) {
          setSelectedJobId(payload.selected_job_id);
        }
        setSelectedCandidate(payload.candidates[0] || null);
        setError('');
      })
      .catch((fetchError: unknown) => {
        setData(null);
        setSelectedCandidate(null);
        setError(fetchError instanceof Error ? fetchError.message : 'Unable to load recruiter dashboard.');
      })
      .finally(() => setLoading(false));
  }, [navigate, refreshKey, selectedJobId]);

  useEffect(() => {
    if (!copyMessage) {
      return;
    }
    const timeoutId = window.setTimeout(() => setCopyMessage(''), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [copyMessage]);

  useEffect(() => {
    if (!selectedCandidate) {
      setPipelineForm({
        status: 'sourced',
        notes: '',
        tags: '',
        assignee_name: '',
        next_step: '',
        rejection_reason: '',
        follow_up_at: '',
      });
      setScheduleForm({
        title: '',
        scheduled_at: '',
        duration_minutes: '30',
        meeting_link: '',
        notes: '',
      });
      return;
    }
    setPipelineForm({
      status: selectedCandidate.pipeline?.status || 'sourced',
      notes: selectedCandidate.pipeline?.notes || '',
      tags: (selectedCandidate.pipeline?.tags || []).join(', '),
      assignee_name: selectedCandidate.pipeline?.assignee_name || '',
      next_step: selectedCandidate.pipeline?.next_step || '',
      rejection_reason: selectedCandidate.pipeline?.rejection_reason || '',
      follow_up_at: selectedCandidate.pipeline?.follow_up_at
        ? selectedCandidate.pipeline.follow_up_at.slice(0, 16)
        : '',
    });
    setScheduleForm((current) => ({
      ...current,
      title: current.title || `${selectedCandidate.name} interview`,
    }));
  }, [selectedCandidate]);

  const filteredCandidates = useMemo(() => {
    const minScoreValue = Number(minScore) || 0;
    return (data?.candidates || []).filter((candidate) => {
      const haystack = [
        candidate.name,
        candidate.email,
        candidate.college,
        candidate.course,
        candidate.branch,
        candidate.verification_id,
        ...candidate.skills.map((skill) => skill.name),
      ]
        .join(' ')
        .toLowerCase();

      const matchesSearch = !search.trim() || haystack.includes(search.trim().toLowerCase());
      const matchesSkill =
        skillFilter === 'all' ||
        candidate.skills.some((skill) => skill.name.toLowerCase() === skillFilter.toLowerCase());
      const matchesScore = candidate.score >= minScoreValue;
      const matchesVerification = !verifiedOnly || candidate.profile_verified;

      return matchesSearch && matchesSkill && matchesScore && matchesVerification;
    });
  }, [data, minScore, search, skillFilter, verifiedOnly]);

  const compareCandidates = useMemo(
    () => filteredCandidates.filter((candidate) => compareIds.includes(candidate.id)).slice(0, 3),
    [compareIds, filteredCandidates],
  );

  useEffect(() => {
    if (!filteredCandidates.length) {
      setSelectedCandidate(null);
      return;
    }
    if (!selectedCandidate || !filteredCandidates.some((candidate) => candidate.id === selectedCandidate.id)) {
      setSelectedCandidate(filteredCandidates[0]);
      setProfileExpanded(false);
    }
  }, [filteredCandidates, selectedCandidate]);

  const handleCompareToggle = (candidateId: number) => {
    setCompareIds((currentIds) => {
      if (currentIds.includes(candidateId)) {
        return currentIds.filter((id) => id !== candidateId);
      }
      if (currentIds.length >= 3) {
        return [...currentIds.slice(1), candidateId];
      }
      return [...currentIds, candidateId];
    });
  };

  const handleDownloadReport = async (candidate: Candidate) => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    setDownloadingId(candidate.id);
    try {
      const response = await fetch(
        buildApiUrl(`/api/skills/recruiter-dashboard/report/${candidate.id}/`),
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (!response.ok) {
        throw new Error('Unable to export candidate report.');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${candidate.name.replace(/\s+/g, '-').toLowerCase()}-candidate-summary.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : 'Unable to export candidate report.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDownloadResume = async (candidate: Candidate) => {
    const token = localStorage.getItem('accessToken');
    if (!token || !candidate.resume_document) {
      return;
    }
    setDownloadingResumeId(candidate.id);
    try {
      const response = await fetch(
        buildApiUrl(candidate.resume_document.download_path),
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (!response.ok) {
        throw new Error('Unable to download candidate resume.');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = candidate.resume_document.filename || `${candidate.name}-resume`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : 'Unable to download candidate resume.');
    } finally {
      setDownloadingResumeId(null);
    }
  };

  const handleContactCandidate = (candidate: Candidate) => {
    window.location.href = `mailto:${candidate.email}?subject=SkillSense%20opportunity`;
  };

  const handleCopyVerificationId = async (candidate: Candidate) => {
    try {
      await navigator.clipboard.writeText(candidate.verification_id);
      setCopyMessage(`Copied ${candidate.verification_id}`);
    } catch {
      setCopyMessage(candidate.verification_id);
    }
  };

  const handleCreateJob = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !jobForm.title.trim()) {
      setError('Job title is required.');
      return;
    }
    setCreatingJob(true);
    try {
      const response = await fetch(buildApiUrl('/api/skills/recruiter-dashboard/jobs/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(jobForm),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to save recruiter brief.');
      }
      const createdJob: RecruiterJob | undefined = payload?.job;
      if (createdJob) {
        setSelectedJobId(createdJob.id);
      }
      setJobForm({
        title: '',
        description: '',
        required_skills: '',
        preferred_skills: '',
        min_ready_score: '65',
      });
      setError('');
    } catch (jobError) {
      setError(jobError instanceof Error ? jobError.message : 'Unable to save recruiter brief.');
    } finally {
      setCreatingJob(false);
    }
  };

  const handleSavePipeline = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !selectedCandidate) {
      return;
    }
    setSavingPipeline(true);
    try {
      const response = await fetch(
        buildApiUrl(`/api/skills/recruiter-dashboard/pipeline/${selectedCandidate.id}/`),
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            job_id: selectedJobId,
            status: pipelineForm.status,
            notes: pipelineForm.notes,
            tags: pipelineForm.tags,
            assignee_name: pipelineForm.assignee_name,
            next_step: pipelineForm.next_step,
            rejection_reason: pipelineForm.rejection_reason,
            follow_up_at: pipelineForm.follow_up_at || null,
          }),
        },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to update pipeline.');
      }
      setSelectedCandidate((current) =>
        current
          ? {
              ...current,
              pipeline: payload?.pipeline || current.pipeline,
              match_score: payload?.match?.score ?? current.match_score,
              match_reasons: payload?.match?.reasons ?? current.match_reasons,
            }
          : current,
      );
      setData((current) =>
        current
          ? {
              ...current,
              candidates: current.candidates.map((candidate) =>
                candidate.id === selectedCandidate.id
                  ? {
                      ...candidate,
                      pipeline: payload?.pipeline || candidate.pipeline,
                      match_score: payload?.match?.score ?? candidate.match_score,
                      match_reasons: payload?.match?.reasons ?? candidate.match_reasons,
                    }
                  : candidate,
              ),
            }
          : current,
      );
      setError('');
      setRefreshKey((current) => current + 1);
    } catch (pipelineError) {
      setError(pipelineError instanceof Error ? pipelineError.message : 'Unable to update pipeline.');
    } finally {
      setSavingPipeline(false);
    }
  };

  const handleCreateSchedule = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !selectedCandidate || !scheduleForm.scheduled_at) {
      setError('Interview time is required.');
      return;
    }
    setScheduling(true);
    try {
      const response = await fetch(buildApiUrl('/api/skills/interview-schedules/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          candidate_id: selectedCandidate.id,
          job_id: selectedJobId,
          title: scheduleForm.title,
          scheduled_at: new Date(scheduleForm.scheduled_at).toISOString(),
          duration_minutes: Number(scheduleForm.duration_minutes) || 30,
          meeting_link: scheduleForm.meeting_link,
          notes: scheduleForm.notes,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to schedule interview.');
      }
      setData((current) =>
        current
          ? {
              ...current,
              interview_schedules: [payload.schedule, ...(current.interview_schedules || [])].slice(0, 12),
            }
          : current,
      );
      setScheduleForm({
        title: `${selectedCandidate.name} interview`,
        scheduled_at: '',
        duration_minutes: '30',
        meeting_link: '',
        notes: '',
      });
      setError('');
    } catch (scheduleError) {
      setError(scheduleError instanceof Error ? scheduleError.message : 'Unable to schedule interview.');
    } finally {
      setScheduling(false);
    }
  };

  const handleSaveSearch = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !savedSearchName.trim()) {
      setError('Add a name before saving this search.');
      return;
    }
    setSavingSearch(true);
    try {
      const response = await fetch(buildApiUrl('/api/skills/recruiter-dashboard/saved-searches/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: savedSearchName.trim(),
          query: search,
          filters: {
            search,
            skill: skillFilter !== 'all' ? skillFilter : '',
            min_score: Number(minScore) || 0,
            verified_only: verifiedOnly,
            job_id: selectedJobId,
          },
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to save search.');
      }
      setData((current) =>
        current
          ? {
              ...current,
              saved_searches: [payload.saved_search, ...(current.saved_searches || [])].slice(0, 8),
            }
          : current,
      );
      setSavedSearchName('');
      setError('');
    } catch (saveSearchError) {
      setError(saveSearchError instanceof Error ? saveSearchError.message : 'Unable to save search.');
    } finally {
      setSavingSearch(false);
    }
  };

  const applySavedSearch = (savedSearch: SavedSearch) => {
    setSearch(savedSearch.filters.search || savedSearch.query || '');
    setSkillFilter(savedSearch.filters.skill || 'all');
    setMinScore(String(savedSearch.filters.min_score ?? 0));
    setVerifiedOnly(Boolean(savedSearch.filters.verified_only));
    setSelectedJobId(savedSearch.filters.job_id ?? null);
  };

  const scoreSummaryCards = [
    { label: 'Total Candidates', value: data?.summary.candidates ?? 0, icon: Briefcase },
    { label: 'Active Jobs', value: data?.summary.active_jobs ?? 0, icon: ClipboardList },
    { label: 'Average Ready Score', value: `${data?.summary.average_ready ?? 0}%`, icon: Star },
    { label: 'Verified Profiles', value: data?.summary.verified_profiles ?? 0, icon: ShieldCheck },
    { label: 'Shortlisted', value: data?.summary.shortlisted ?? 0, icon: BadgeCheck },
  ];

  const radarData = (selectedCandidate?.skills || []).map((skill) => ({
    skill: skill.name,
    level: skill.score || 0,
  }));

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="container-custom">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h1 className="text-3xl font-bold mb-2">
              Recruiter <span className="gradient-text">Talent Desk</span>
            </h1>
            <p className="text-muted-foreground">
              Search verified students, compare profiles, and export candidate summaries.
            </p>
          </motion.div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            {scoreSummaryCards.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.08 }}
                className="glass-card p-5"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <stat.icon className="w-5 h-5 text-primary" />
                  </div>
                </div>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.9fr)] mb-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.08 }}
              className="glass-card p-6"
            >
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <h2 className="text-lg font-semibold">JD Matching Workspace</h2>
                  <p className="text-sm text-muted-foreground">
                    Add a job brief, extract the core skills, and rank candidates against it.
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-card/40 px-4 py-3 text-right">
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Active brief
                  </div>
                  <div className="mt-1 font-semibold">
                    {data?.jobs.find((job) => job.id === selectedJobId)?.title || 'No brief selected'}
                  </div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <input
                  type="text"
                  value={jobForm.title}
                  onChange={(event) => setJobForm((current) => ({ ...current, title: event.target.value }))}
                  placeholder="Role title"
                  className="input-field"
                />
                <input
                  type="number"
                  value={jobForm.min_ready_score}
                  onChange={(event) => setJobForm((current) => ({ ...current, min_ready_score: event.target.value }))}
                  placeholder="Minimum ready score"
                  className="input-field"
                />
                <Textarea
                  value={jobForm.description}
                  onChange={(event) => setJobForm((current) => ({ ...current, description: event.target.value }))}
                  placeholder="Paste the job description or role brief"
                  className="md:col-span-2 min-h-[120px]"
                />
                <input
                  type="text"
                  value={jobForm.required_skills}
                  onChange={(event) => setJobForm((current) => ({ ...current, required_skills: event.target.value }))}
                  placeholder="Required skills (comma-separated)"
                  className="input-field"
                />
                <input
                  type="text"
                  value={jobForm.preferred_skills}
                  onChange={(event) => setJobForm((current) => ({ ...current, preferred_skills: event.target.value }))}
                  placeholder="Preferred skills (comma-separated)"
                  className="input-field"
                />
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button onClick={handleCreateJob} disabled={creatingJob}>
                  <Target className="w-4 h-4 mr-2" />
                  {creatingJob ? 'Saving Brief...' : 'Create Job Brief'}
                </Button>
                <select
                  value={selectedJobId ?? ''}
                  onChange={(event) => setSelectedJobId(event.target.value ? Number(event.target.value) : null)}
                  className="input-field min-w-[250px]"
                >
                  <option value="">All candidates (no brief)</option>
                  {(data?.jobs || []).map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.title} • {job.top_matches} top matches
                    </option>
                  ))}
                </select>
              </div>

              {(data?.jobs || []).length > 0 && (
                <div className="mt-5 flex flex-wrap gap-2">
                  {(data?.jobs || []).map((job) => (
                    <button
                      key={job.id}
                      type="button"
                      onClick={() => setSelectedJobId(job.id)}
                      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        selectedJobId === job.id
                          ? 'border-primary/50 bg-primary/10 text-primary'
                          : 'border-border/60 bg-card/40 text-muted-foreground'
                      }`}
                    >
                      {job.title}
                    </button>
                  ))}
                </div>
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.12 }}
              className="glass-card p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <ClipboardList className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-semibold">Pipeline Control</h2>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Sourced', value: data?.pipeline_summary.sourced ?? 0 },
                  { label: 'Shortlisted', value: data?.pipeline_summary.shortlisted ?? 0 },
                  { label: 'Interviewing', value: data?.pipeline_summary.interviewing ?? 0 },
                  { label: 'Offered', value: data?.pipeline_summary.offered ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="rounded-2xl border border-border/60 bg-card/40 p-4">
                    <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{item.label}</div>
                    <div className="mt-2 text-2xl font-semibold">{item.value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-5">
                <div className="text-sm font-medium">Saved searches</div>
                <div className="mt-3 flex gap-3">
                  <input
                    type="text"
                    value={savedSearchName}
                    onChange={(event) => setSavedSearchName(event.target.value)}
                    placeholder="Name this search"
                    className="input-field flex-1"
                  />
                  <Button variant="outline" onClick={handleSaveSearch} disabled={savingSearch}>
                    <BookmarkPlus className="w-4 h-4 mr-2" />
                    {savingSearch ? 'Saving...' : 'Save'}
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(data?.saved_searches || []).length === 0 ? (
                    <span className="text-sm text-muted-foreground">No saved searches yet.</span>
                  ) : (
                    (data?.saved_searches || []).map((savedSearch) => (
                      <button
                        key={savedSearch.id}
                        type="button"
                        onClick={() => applySavedSearch(savedSearch)}
                        className="rounded-full border border-border/60 bg-card/40 px-3 py-1 text-xs font-medium text-muted-foreground hover:border-primary/40 hover:text-primary"
                      >
                        {savedSearch.name}
                      </button>
                    ))
                  )}
                </div>
              </div>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6 mb-8"
          >
            <div className="flex flex-col xl:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by name, skill, email, college, or verification ID"
                  className="input-field pl-12 w-full"
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <select
                  value={skillFilter}
                  onChange={(event) => setSkillFilter(event.target.value)}
                  className="input-field min-w-[180px]"
                >
                  <option value="all">All skills</option>
                  {(data?.filters.skills || []).map((skill) => (
                    <option key={skill} value={skill}>
                      {skill}
                    </option>
                  ))}
                </select>
                <select
                  value={minScore}
                  onChange={(event) => setMinScore(event.target.value)}
                  className="input-field min-w-[160px]"
                >
                  <option value="0">Any score</option>
                  <option value="50">50+ ready score</option>
                  <option value="65">65+ ready score</option>
                  <option value="75">75+ ready score</option>
                  <option value="85">85+ ready score</option>
                </select>
                <Button
                  variant={verifiedOnly ? 'default' : 'outline'}
                  onClick={() => setVerifiedOnly((current) => !current)}
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Verified Only
                </Button>
                <Button
                  variant={compareMode ? 'default' : 'outline'}
                  onClick={() => {
                    setCompareMode((current) => !current);
                    setCompareIds([]);
                  }}
                >
                  Compare Mode
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSearch('');
                    setSkillFilter('all');
                    setMinScore('0');
                    setVerifiedOnly(false);
                  }}
                >
                  Reset
                </Button>
              </div>
            </div>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mt-4 text-sm text-muted-foreground">
              <span>
                Showing {filteredCandidates.length} of {data?.candidates.length || 0} candidates
              </span>
              <span>
                {compareMode
                  ? `Select up to 3 candidates to compare (${compareIds.length}/3 chosen)`
                  : 'Turn on compare mode to shortlist side by side.'}
              </span>
            </div>
          </motion.div>

          {compareMode && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="glass-card p-6 mb-8"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold">Candidate Comparison</h2>
                  <p className="text-sm text-muted-foreground">
                    Compare readiness, strengths, and focus areas before you shortlist.
                  </p>
                </div>
              </div>
              {compareCandidates.length < 2 ? (
                <div className="text-sm text-muted-foreground">
                  Pick at least two candidates from the list to populate the comparison view.
                </div>
              ) : (
                <div className="grid lg:grid-cols-3 gap-4">
                  {compareCandidates.map((candidate) => (
                    <div key={candidate.id} className="rounded-2xl border border-border/60 bg-card/50 p-5">
                      <div className="flex items-start justify-between gap-3 mb-4">
                        <div>
                          <div className="font-semibold">{candidate.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {candidate.course} | {candidate.college || 'College pending'}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold gradient-text">{candidate.score}</div>
                          <div className="text-xs text-muted-foreground">Ready score</div>
                        </div>
                      </div>
                      <div className="space-y-3">
                        {scoreLabels.map((scoreItem) => (
                          <div key={scoreItem.key}>
                            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                              <span>{scoreItem.label}</span>
                              <span className="text-foreground font-medium">
                                {candidate.scores[scoreItem.key]}
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-muted/60 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                                style={{ width: `${candidate.scores[scoreItem.key]}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 text-sm text-muted-foreground">
                        <div className="font-medium text-foreground mb-1">Focus area</div>
                        <div>{candidate.focus_area}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-4">
              {loading ? (
                <div className="glass-card p-6 text-center text-muted-foreground">
                  Loading verified candidates...
                </div>
              ) : error ? (
                <div className="glass-card p-6 text-center text-destructive">{error}</div>
              ) : filteredCandidates.length === 0 ? (
                <div className="glass-card p-6 text-center text-muted-foreground">
                  No candidates match the current filters.
                </div>
              ) : (
                filteredCandidates.map((candidate, index) => (
                  <motion.div
                    key={candidate.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.05 }}
                    onClick={() => {
                      setSelectedCandidate(candidate);
                      setProfileExpanded(false);
                    }}
                    className={`glass-card p-6 cursor-pointer card-hover ${
                      selectedCandidate?.id === candidate.id ? 'border-primary/50 glow-primary' : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      {compareMode && (
                        <input
                          type="checkbox"
                          checked={compareIds.includes(candidate.id)}
                          onChange={() => handleCompareToggle(candidate.id)}
                          onClick={(event) => event.stopPropagation()}
                          className="mt-2 h-5 w-5 rounded border-border bg-background"
                        />
                      )}
                      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                        <span className="text-lg font-semibold text-primary">
                          {candidate.name.slice(0, 1)}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="font-semibold text-lg">{candidate.name}</h3>
                              {candidate.profile_verified && (
                                <BadgeCheck className="w-5 h-5 text-primary" />
                              )}
                              <span className="px-2 py-0.5 rounded-full bg-muted/60 text-xs text-muted-foreground">
                                {candidate.status_label}
                              </span>
                              {candidate.pipeline?.status && (
                                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-xs text-primary">
                                  {candidate.pipeline.status.replace('_', ' ')}
                                </span>
                              )}
                            </div>
                            <p className="text-muted-foreground text-sm">
                              {candidate.course} | {candidate.verification_id}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold gradient-text">{candidate.score}</div>
                            <div className="text-xs text-muted-foreground">
                              {selectedJobId ? `${candidate.match_score ?? candidate.score}% match` : 'Overall readiness'}
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-4 mt-3 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {candidate.branch || 'Branch pending'}
                          </span>
                          <span className="flex items-center gap-1">
                            <GraduationCap className="w-4 h-4" />
                            {candidate.college || 'College pending'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-4 h-4" />
                            Focus: {candidate.focus_area}
                          </span>
                        </div>

                        <div className="grid md:grid-cols-4 gap-2 mt-4">
                          {scoreLabels.map((scoreItem) => (
                            <div key={scoreItem.key} className="rounded-xl bg-muted/30 p-3">
                              <div className="text-xs text-muted-foreground">{scoreItem.label}</div>
                              <div className="text-lg font-semibold">
                                {candidate.scores[scoreItem.key]}
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="flex flex-wrap gap-2 mt-4">
                          {candidate.skills.length === 0 ? (
                            <span className="text-xs text-muted-foreground">No skill evidence yet</span>
                          ) : (
                            candidate.skills.map((skill) => (
                              <span
                                key={skill.name}
                                className={`px-3 py-1 rounded-full text-xs font-medium ${
                                  skill.verified
                                    ? 'bg-primary/10 text-primary'
                                    : 'bg-muted/60 text-muted-foreground'
                                }`}
                              >
                                {skill.name}
                              </span>
                            ))
                          )}
                        </div>

                        {selectedJobId && candidate.match_reasons?.length ? (
                          <div className="mt-4 rounded-2xl border border-border/60 bg-card/40 p-3 text-sm text-muted-foreground">
                            {candidate.match_reasons[0]}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>

            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                className="glass-card p-6 sticky top-24"
              >
                {selectedCandidate ? (
                  <>
                    <div className="text-center mb-6">
                      <div className="w-20 h-20 rounded-2xl mx-auto mb-4 bg-primary/10 flex items-center justify-center">
                        <span className="text-xl font-semibold text-primary">
                          {selectedCandidate.name.slice(0, 1)}
                        </span>
                      </div>
                      <h3 className="text-xl font-semibold">{selectedCandidate.name}</h3>
                      <p className="text-muted-foreground">
                        {selectedCandidate.course} | {selectedCandidate.college || 'College pending'}
                      </p>
                      <button
                        type="button"
                        onClick={() => handleCopyVerificationId(selectedCandidate)}
                        className="mt-2 text-xs text-primary hover:underline"
                      >
                        {copyMessage || selectedCandidate.verification_id}
                      </button>
                    </div>

                    <div className="h-[220px] mb-6">
                      {radarData.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-muted-foreground">
                          No skill evidence yet
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart data={radarData}>
                            <PolarGrid stroke="hsl(var(--border))" />
                            <PolarAngleAxis
                              dataKey="skill"
                              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                            />
                            <Radar
                              dataKey="level"
                              stroke="hsl(var(--primary))"
                              fill="hsl(var(--primary))"
                              fillOpacity={0.25}
                            />
                          </RadarChart>
                        </ResponsiveContainer>
                      )}
                    </div>

                    <div className="space-y-3 mb-5">
                      {scoreLabels.map((scoreItem) => (
                        <div key={scoreItem.key}>
                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                            <span>{scoreItem.label}</span>
                            <span className="text-foreground font-medium">
                              {selectedCandidate.scores[scoreItem.key]}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-muted/60 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                              style={{ width: `${selectedCandidate.scores[scoreItem.key]}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-5">
                      <div className="rounded-xl bg-muted/30 p-3">
                        <div className="text-xs text-muted-foreground">Branch</div>
                        <div className="font-medium">{selectedCandidate.branch || 'Pending'}</div>
                      </div>
                      <div className="rounded-xl bg-muted/30 p-3">
                        <div className="text-xs text-muted-foreground">Year</div>
                        <div className="font-medium">{selectedCandidate.year_of_study || 'Pending'}</div>
                      </div>
                      <div className="rounded-xl bg-muted/30 p-3">
                        <div className="text-xs text-muted-foreground">CGPA</div>
                        <div className="font-medium">
                          {selectedCandidate.cgpa !== null ? selectedCandidate.cgpa : 'Pending'}
                        </div>
                      </div>
                      <div className="rounded-xl bg-muted/30 p-3">
                        <div className="text-xs text-muted-foreground">Verified Skills</div>
                        <div className="font-medium">{selectedCandidate.verified_skills}</div>
                      </div>
                    </div>

                    <div className="mb-5 rounded-2xl border border-border/60 bg-card/40 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            Match Score
                          </div>
                          <div className="mt-1 text-2xl font-semibold">
                            {selectedCandidate.match_score ?? selectedCandidate.score}
                          </div>
                        </div>
                        <div className="text-right text-sm text-muted-foreground">
                          <div>{data?.jobs.find((job) => job.id === selectedJobId)?.title || 'No job brief selected'}</div>
                          <div className="mt-1">{selectedCandidate.pipeline?.status?.replace('_', ' ') || 'Pipeline not started'}</div>
                        </div>
                      </div>
                      <div className="mt-4 space-y-2">
                        {(selectedCandidate.match_reasons || []).length === 0 ? (
                          <div className="text-sm text-muted-foreground">
                            Add a job brief to generate candidate-specific match reasoning.
                          </div>
                        ) : (
                          (selectedCandidate.match_reasons || []).map((reason, index) => (
                            <div key={`${selectedCandidate.id}-reason-${index}`} className="rounded-xl bg-background/70 p-3 text-sm text-muted-foreground">
                              {reason}
                            </div>
                          ))
                        )}
                        {!!selectedCandidate.matched_keywords?.length && (
                          <div className="flex flex-wrap gap-2 pt-1">
                            {selectedCandidate.matched_keywords?.map((keyword) => (
                              <span key={keyword} className="rounded-full bg-primary/10 px-2.5 py-1 text-xs text-primary">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        )}
                        <div className="text-xs text-muted-foreground">
                          Semantic overlap score: {selectedCandidate.semantic_score ?? 0}/100
                        </div>
                      </div>
                    </div>

                    <div className="mb-5 rounded-2xl border border-border/60 bg-card/40 p-4">
                      <div className="flex items-center gap-2">
                        <ClipboardList className="h-4 w-4 text-primary" />
                        <div className="font-medium">Pipeline Update</div>
                      </div>
                      <div className="mt-4 space-y-3">
                        <select
                          value={pipelineForm.status}
                          onChange={(event) =>
                            setPipelineForm((current) => ({
                              ...current,
                              status: event.target.value as CandidatePipeline['status'],
                            }))
                          }
                          className="input-field w-full"
                        >
                          <option value="sourced">Sourced</option>
                          <option value="shortlisted">Shortlisted</option>
                          <option value="interviewing">Interviewing</option>
                          <option value="offered">Offered</option>
                          <option value="rejected">Rejected</option>
                        </select>
                        <input
                          type="text"
                          value={pipelineForm.assignee_name}
                          onChange={(event) =>
                            setPipelineForm((current) => ({ ...current, assignee_name: event.target.value }))
                          }
                          placeholder="Owner / assignee"
                          className="input-field w-full"
                        />
                        <input
                          type="text"
                          value={pipelineForm.tags}
                          onChange={(event) =>
                            setPipelineForm((current) => ({ ...current, tags: event.target.value }))
                          }
                          placeholder="Tags (comma-separated)"
                          className="input-field w-full"
                        />
                        <input
                          type="text"
                          value={pipelineForm.next_step}
                          onChange={(event) =>
                            setPipelineForm((current) => ({ ...current, next_step: event.target.value }))
                          }
                          placeholder="Next step"
                          className="input-field w-full"
                        />
                        {pipelineForm.status === 'rejected' && (
                          <input
                            type="text"
                            value={pipelineForm.rejection_reason}
                            onChange={(event) =>
                              setPipelineForm((current) => ({ ...current, rejection_reason: event.target.value }))
                            }
                            placeholder="Rejection reason"
                            className="input-field w-full"
                          />
                        )}
                        <input
                          type="datetime-local"
                          value={pipelineForm.follow_up_at}
                          onChange={(event) =>
                            setPipelineForm((current) => ({ ...current, follow_up_at: event.target.value }))
                          }
                          className="input-field w-full"
                        />
                        <Textarea
                          value={pipelineForm.notes}
                          onChange={(event) =>
                            setPipelineForm((current) => ({ ...current, notes: event.target.value }))
                          }
                          placeholder="Why this candidate fits, concerns, and next step notes"
                          className="min-h-[110px]"
                        />
                        <Button variant="outline" className="w-full" onClick={handleSavePipeline} disabled={savingPipeline}>
                          {savingPipeline ? 'Saving Pipeline...' : 'Save Pipeline Update'}
                        </Button>
                      </div>
                    </div>

                    <div className="mb-5 rounded-2xl border border-border/60 bg-card/40 p-4">
                      <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-primary" />
                        <div className="font-medium">Schedule Interview</div>
                      </div>
                      <div className="mt-4 space-y-3">
                        <input
                          type="text"
                          value={scheduleForm.title}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, title: event.target.value }))
                          }
                          placeholder="Interview title"
                          className="input-field w-full"
                        />
                        <input
                          type="datetime-local"
                          value={scheduleForm.scheduled_at}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, scheduled_at: event.target.value }))
                          }
                          className="input-field w-full"
                        />
                        <input
                          type="number"
                          min="15"
                          value={scheduleForm.duration_minutes}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, duration_minutes: event.target.value }))
                          }
                          placeholder="Duration (minutes)"
                          className="input-field w-full"
                        />
                        <input
                          type="url"
                          value={scheduleForm.meeting_link}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, meeting_link: event.target.value }))
                          }
                          placeholder="Meeting link"
                          className="input-field w-full"
                        />
                        <Textarea
                          value={scheduleForm.notes}
                          onChange={(event) =>
                            setScheduleForm((current) => ({ ...current, notes: event.target.value }))
                          }
                          placeholder="Interview agenda or note"
                          className="min-h-[90px]"
                        />
                        <Button variant="outline" className="w-full" onClick={handleCreateSchedule} disabled={scheduling}>
                          {scheduling ? 'Scheduling...' : 'Schedule Interview'}
                        </Button>
                        <div className="space-y-2">
                          {(data?.interview_schedules || [])
                            .filter((item) => item.candidate_id === selectedCandidate.id)
                            .slice(0, 3)
                            .map((item) => (
                              <div key={item.id} className="rounded-xl bg-background/70 p-3 text-sm">
                                <div className="font-medium">{item.title}</div>
                                <div className="mt-1 text-muted-foreground">
                                  {item.scheduled_at ? new Date(item.scheduled_at).toLocaleString() : 'TBD'} • {item.duration_minutes} min
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    </div>

                    {profileExpanded && (
                      <div className="space-y-4 mb-5 rounded-2xl border border-border/60 bg-card/40 p-4">
                        <div>
                          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                            Focus Area
                          </div>
                          <div className="font-medium">{selectedCandidate.focus_area}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                            Recommended Action
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {selectedCandidate.recommended_action}
                          </div>
                        </div>
                        {selectedCandidate.headline && (
                          <div>
                            <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                              Headline
                            </div>
                            <div className="text-sm">{selectedCandidate.headline}</div>
                          </div>
                        )}
                        {selectedCandidate.summary && (
                          <div>
                            <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                              Profile Summary
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {selectedCandidate.summary}
                            </div>
                          </div>
                        )}
                        {selectedCandidate.resume_document && (
                          <div>
                            <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                              Resume On File
                            </div>
                            <div className="text-sm">{selectedCandidate.resume_document.filename}</div>
                          </div>
                        )}
                        <div>
                          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                            Public Links
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(selectedCandidate.links)
                              .filter(([, url]) => Boolean(url))
                              .map(([label, url]) => (
                                <a
                                  key={label}
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium hover:underline"
                                >
                                  {label}
                                </a>
                              ))}
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="space-y-3">
                      <Button
                        className="w-full"
                        onClick={() => setProfileExpanded((current) => !current)}
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        {profileExpanded ? 'Hide Full Profile' : 'View Full Profile'}
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => handleContactCandidate(selectedCandidate)}
                      >
                        <Mail className="w-4 h-4 mr-2" />
                        Contact Candidate
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => handleDownloadResume(selectedCandidate)}
                        disabled={!selectedCandidate.resume_document || downloadingResumeId === selectedCandidate.id}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        {!selectedCandidate.resume_document
                          ? 'Resume Unavailable'
                          : downloadingResumeId === selectedCandidate.id
                            ? 'Downloading Resume...'
                            : 'Download Resume'}
                      </Button>
                      <Button
                        variant="ghost"
                        className="w-full"
                        onClick={() => handleDownloadReport(selectedCandidate)}
                        disabled={downloadingId === selectedCandidate.id}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        {downloadingId === selectedCandidate.id ? 'Exporting...' : 'Download Summary'}
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="text-center text-muted-foreground py-6">
                    Select a candidate to inspect the profile.
                  </div>
                )}
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
