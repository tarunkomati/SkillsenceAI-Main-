import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import {
  AlertTriangle,
  Download,
  Filter,
  ShieldCheck,
  Target,
  TrendingUp,
  UploadCloud,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { buildApiUrl } from '@/lib/api';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface StudentScores {
  placement_ready: number;
  coding_skill_index: number;
  communication_score: number;
  authenticity_score: number;
}

interface StudentSummary {
  id: number;
  verification_id: string;
  name: string;
  college: string;
  course: string;
  branch: string;
  year_of_study: string;
  profile_verified: boolean;
  score: number;
  focus_area: string;
  recommended_action: string;
  scores: StudentScores;
}

interface Summary {
  students: number;
  average_ready: number;
  average_coding: number;
  average_authenticity: number;
  verified_profiles: number;
  need_attention: number;
  tracked_interventions: number;
}

interface DistributionItem {
  name: string;
  count: number;
}

interface TrendPoint {
  date: string;
  placement_ready: number;
  coding_skill_index: number;
  communication_score: number;
  authenticity_score: number;
}

interface InterventionItem {
  id: number;
  name: string;
  verification_id: string;
  college: string;
  branch: string;
  score: number;
  focus_area: string;
  severity: 'high' | 'medium' | 'low';
  reason: string;
  action: string;
  status: 'planned' | 'in_progress' | 'completed' | 'escalated';
  priority: 'high' | 'medium' | 'low';
  note: string;
  recommended_action: string;
}

interface BatchUpload {
  id: number;
  filename: string;
  status: 'completed' | 'failed';
  summary: {
    created?: number;
    updated?: number;
    skipped?: number;
  };
  created_at: string | null;
}

interface PlacementDrive {
  id: number;
  company_name: string;
  role_title: string;
  description: string;
  target_branches: string[];
  target_courses: string[];
  minimum_ready_score: number;
  scheduled_on: string | null;
  status: 'planning' | 'live' | 'closed';
  eligible_count: number;
  top_candidates: Array<{
    id: number;
    name: string;
    score: number;
    branch: string;
    verification_id: string;
  }>;
  updated_at: string | null;
}

interface UniversityResponse {
  summary: Summary;
  filters: {
    branches: string[];
    courses: string[];
    years: string[];
  };
  readiness_breakdown: DistributionItem[];
  skill_distribution: DistributionItem[];
  placement_trend: TrendPoint[];
  interventions: InterventionItem[];
  top_students: StudentSummary[];
  students: StudentSummary[];
  batch_uploads: BatchUpload[];
  placement_drives: PlacementDrive[];
}

const readinessColors = ['hsl(var(--primary))', 'hsl(var(--accent))', '#f59e0b'];

export default function UniversityDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<UniversityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [courseFilter, setCourseFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [uploadingBatch, setUploadingBatch] = useState(false);
  const [uploadSummary, setUploadSummary] = useState<BatchUpload['summary'] | null>(null);
  const [savingDrive, setSavingDrive] = useState(false);
  const [savingInterventionId, setSavingInterventionId] = useState<number | null>(null);
  const [interventionDrafts, setInterventionDrafts] = useState<
    Record<number, Pick<InterventionItem, 'status' | 'priority' | 'note' | 'recommended_action'>>
  >({});
  const [driveForm, setDriveForm] = useState({
    company_name: '',
    role_title: '',
    description: '',
    target_branches: '',
    target_courses: '',
    minimum_ready_score: '70',
    scheduled_on: '',
    status: 'planning',
  });

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    const role = localStorage.getItem('userRole');
    if (!token || role !== 'university') {
      navigate('/university');
      return;
    }

    const params = new URLSearchParams();
    if (branchFilter) {
      params.set('branch', branchFilter);
    }
    if (courseFilter) {
      params.set('course', courseFilter);
    }
    if (yearFilter) {
      params.set('year_of_study', yearFilter);
    }

    const query = params.toString();
    const path = query
      ? `/api/skills/university-dashboard/?${query}`
      : '/api/skills/university-dashboard/';

    setLoading(true);
    fetch(buildApiUrl(path), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          navigate('/university');
          return null;
        }
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          throw new Error(payload?.error || 'Unable to load university dashboard.');
        }
        return res.json();
      })
      .then((payload: UniversityResponse | null) => {
        if (!payload) {
          return;
        }
        setData(payload);
        setError('');
      })
      .catch((fetchError: unknown) => {
        setData(null);
        setError(fetchError instanceof Error ? fetchError.message : 'Unable to load university dashboard.');
      })
      .finally(() => setLoading(false));
  }, [branchFilter, courseFilter, navigate, refreshKey, yearFilter]);

  useEffect(() => {
    const nextDrafts: Record<
      number,
      Pick<InterventionItem, 'status' | 'priority' | 'note' | 'recommended_action'>
    > = {};
    (data?.interventions || []).forEach((item) => {
      nextDrafts[item.id] = {
        status: item.status,
        priority: item.priority,
        note: item.note,
        recommended_action: item.recommended_action || item.action,
      };
    });
    setInterventionDrafts(nextDrafts);
  }, [data?.interventions]);

  const summaryCards = [
    { label: 'Total Students', value: data?.summary.students ?? 0, icon: Users },
    { label: 'Average Ready', value: `${data?.summary.average_ready ?? 0}%`, icon: TrendingUp },
    { label: 'Verified Profiles', value: data?.summary.verified_profiles ?? 0, icon: ShieldCheck },
    { label: 'Tracked Support', value: data?.summary.tracked_interventions ?? 0, icon: Target },
    { label: 'Need Attention', value: data?.summary.need_attention ?? 0, icon: AlertTriangle },
  ];

  const cohortCsv = useMemo(() => {
    const students = data?.students || [];
    const rows = [
      ['Verification ID', 'Name', 'College', 'Course', 'Branch', 'Year', 'Ready Score', 'Coding', 'Communication', 'Authenticity', 'Verified'],
      ...students.map((student) => [
        student.verification_id,
        student.name,
        student.college,
        student.course,
        student.branch,
        student.year_of_study,
        String(student.scores.placement_ready),
        String(student.scores.coding_skill_index),
        String(student.scores.communication_score),
        String(student.scores.authenticity_score),
        student.profile_verified ? 'Yes' : 'No',
      ]),
    ];
    return rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
  }, [data]);

  const handleExportCsv = () => {
    if (!data?.students.length) {
      return;
    }
    const blob = new Blob([cohortCsv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'skillsense-university-cohort.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleBatchUpload = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !batchFile) {
      setError('Choose a CSV file before uploading.');
      return;
    }
    setUploadingBatch(true);
    setError('');
    try {
      const payload = new FormData();
      payload.append('file', batchFile);
      const response = await fetch(buildApiUrl('/api/skills/university-dashboard/batch-upload/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: payload,
      });
      const dataPayload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(dataPayload?.error || 'Unable to upload student batch.');
      }
      setUploadSummary(dataPayload?.summary || null);
      setBatchFile(null);
      setRefreshKey((current) => current + 1);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Unable to upload student batch.');
    } finally {
      setUploadingBatch(false);
    }
  };

  const handleInterventionSave = async (studentId: number) => {
    const token = localStorage.getItem('accessToken');
    const draft = interventionDrafts[studentId];
    if (!token || !draft) {
      return;
    }
    setSavingInterventionId(studentId);
    try {
      const response = await fetch(
        buildApiUrl(`/api/skills/university-dashboard/interventions/${studentId}/`),
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(draft),
        },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to update intervention.');
      }
      setData((current) =>
        current
          ? {
              ...current,
              interventions: current.interventions.map((item) =>
                item.id === studentId
                  ? {
                      ...item,
                      ...draft,
                    }
                  : item,
              ),
            }
          : current,
      );
      setError('');
    } catch (interventionError) {
      setError(interventionError instanceof Error ? interventionError.message : 'Unable to update intervention.');
    } finally {
      setSavingInterventionId(studentId);
    }
  };

  const handleCreateDrive = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !driveForm.company_name.trim() || !driveForm.role_title.trim()) {
      setError('Company name and role title are required.');
      return;
    }
    setSavingDrive(true);
    try {
      const response = await fetch(buildApiUrl('/api/skills/university-dashboard/drives/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(driveForm),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to create placement drive.');
      }
      setData((current) =>
        current
          ? {
              ...current,
              placement_drives: [payload.drive, ...(current.placement_drives || [])].slice(0, 8),
            }
          : current,
      );
      setDriveForm({
        company_name: '',
        role_title: '',
        description: '',
        target_branches: '',
        target_courses: '',
        minimum_ready_score: '70',
        scheduled_on: '',
        status: 'planning',
      });
      setError('');
    } catch (driveError) {
      setError(driveError instanceof Error ? driveError.message : 'Unable to create placement drive.');
    } finally {
      setSavingDrive(false);
    }
  };

  const severityStyles: Record<InterventionItem['severity'], string> = {
    high: 'border-l-red-500',
    medium: 'border-l-amber-500',
    low: 'border-l-emerald-500',
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="container-custom">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col md:flex-row md:items-center justify-between mb-8"
          >
            <div>
              <h1 className="text-3xl font-bold mb-2">
                University <span className="gradient-text">Analytics Hub</span>
              </h1>
              <p className="text-muted-foreground">
                Monitor cohort readiness, filter the batch, and export the current view.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 mt-4 md:mt-0">
              <select
                value={branchFilter}
                onChange={(event) => setBranchFilter(event.target.value)}
                className="input-field min-w-[170px]"
              >
                <option value="">All branches</option>
                {(data?.filters.branches || []).map((branch) => (
                  <option key={branch} value={branch}>
                    {branch}
                  </option>
                ))}
              </select>
              <select
                value={courseFilter}
                onChange={(event) => setCourseFilter(event.target.value)}
                className="input-field min-w-[170px]"
              >
                <option value="">All courses</option>
                {(data?.filters.courses || []).map((course) => (
                  <option key={course} value={course}>
                    {course}
                  </option>
                ))}
              </select>
              <select
                value={yearFilter}
                onChange={(event) => setYearFilter(event.target.value)}
                className="input-field min-w-[150px]"
              >
                <option value="">All years</option>
                {(data?.filters.years || []).map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
              <Button
                variant="outline"
                onClick={() => {
                  setBranchFilter('');
                  setCourseFilter('');
                  setYearFilter('');
                }}
              >
                <Filter className="w-4 h-4 mr-2" />
                Reset Filters
              </Button>
              <Button onClick={handleExportCsv} disabled={!data?.students.length}>
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
            </div>
          </motion.div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            {summaryCards.map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, delay: index * 0.08 }}
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

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] mb-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.08 }}
              className="glass-card p-6"
            >
              <div className="flex items-start justify-between gap-4 mb-5">
                <div>
                  <h2 className="text-lg font-semibold">Batch Import</h2>
                  <p className="text-sm text-muted-foreground">
                    Upload a CSV with cohort details, skills, and optional score columns to seed analytics.
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-card/40 px-4 py-3 text-right text-sm">
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Suggested columns</div>
                  <div className="mt-1 text-muted-foreground">
                    `email, full_name, college, course, branch, year_of_study, skills`
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
                <div className="rounded-2xl border border-border/60 bg-card/40 p-5">
                  <label className="block text-sm font-medium mb-3">Student batch CSV</label>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(event) => setBatchFile(event.target.files?.[0] || null)}
                    className="input-field w-full"
                  />
                  <p className="mt-3 text-xs text-muted-foreground">
                    Add score columns like `placement_ready`, `coding_skill_index`, `communication_score`, and `authenticity_score` if you have them.
                  </p>
                </div>
                <div className="flex items-center">
                  <Button onClick={handleBatchUpload} disabled={uploadingBatch || !batchFile}>
                    <UploadCloud className="w-4 h-4 mr-2" />
                    {uploadingBatch ? 'Uploading...' : 'Upload Batch'}
                  </Button>
                </div>
              </div>

              {uploadSummary && (
                <div className="mt-4 rounded-2xl border border-primary/20 bg-primary/5 p-4 text-sm">
                  Created {uploadSummary.created ?? 0}, updated {uploadSummary.updated ?? 0}, skipped {uploadSummary.skipped ?? 0}.
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
                <UploadCloud className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-semibold">Recent Uploads</h2>
              </div>
              <div className="space-y-3">
                {(data?.batch_uploads || []).length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                    No cohort uploads yet.
                  </div>
                ) : (
                  (data?.batch_uploads || []).map((batch) => (
                    <div key={batch.id} className="rounded-2xl border border-border/60 bg-card/40 p-4">
                      <div className="font-medium">{batch.filename}</div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        Created {batch.summary.created ?? 0} • Updated {batch.summary.updated ?? 0} • Skipped {batch.summary.skipped ?? 0}
                      </div>
                      <div className="mt-2 text-xs text-muted-foreground">
                        {batch.created_at ? new Date(batch.created_at).toLocaleString() : 'Recently'}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </div>

          {loading ? (
            <div className="glass-card p-8 text-center text-muted-foreground">
              Loading university analytics...
            </div>
          ) : error ? (
            <div className="glass-card p-8 text-center text-destructive">{error}</div>
          ) : (
            <>
              <div className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] mb-8">
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="glass-card p-6"
                >
                  <div className="flex items-start justify-between gap-4 mb-5">
                    <div>
                      <h2 className="text-lg font-semibold">Placement Drive Planner</h2>
                      <p className="text-sm text-muted-foreground">
                        Create live drives and track eligible students by branch, course, and readiness threshold.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-card/40 px-4 py-3 text-sm text-muted-foreground">
                      Uses the current verified and readiness data to compute eligibility.
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <input
                      type="text"
                      value={driveForm.company_name}
                      onChange={(event) => setDriveForm((current) => ({ ...current, company_name: event.target.value }))}
                      placeholder="Company name"
                      className="input-field"
                    />
                    <input
                      type="text"
                      value={driveForm.role_title}
                      onChange={(event) => setDriveForm((current) => ({ ...current, role_title: event.target.value }))}
                      placeholder="Role title"
                      className="input-field"
                    />
                    <input
                      type="text"
                      value={driveForm.target_branches}
                      onChange={(event) => setDriveForm((current) => ({ ...current, target_branches: event.target.value }))}
                      placeholder="Target branches (comma-separated)"
                      className="input-field"
                    />
                    <input
                      type="text"
                      value={driveForm.target_courses}
                      onChange={(event) => setDriveForm((current) => ({ ...current, target_courses: event.target.value }))}
                      placeholder="Target courses (comma-separated)"
                      className="input-field"
                    />
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={driveForm.minimum_ready_score}
                      onChange={(event) => setDriveForm((current) => ({ ...current, minimum_ready_score: event.target.value }))}
                      placeholder="Minimum ready score"
                      className="input-field"
                    />
                    <input
                      type="date"
                      value={driveForm.scheduled_on}
                      onChange={(event) => setDriveForm((current) => ({ ...current, scheduled_on: event.target.value }))}
                      className="input-field"
                    />
                    <select
                      value={driveForm.status}
                      onChange={(event) => setDriveForm((current) => ({ ...current, status: event.target.value }))}
                      className="input-field md:col-span-2"
                    >
                      <option value="planning">Planning</option>
                      <option value="live">Live</option>
                      <option value="closed">Closed</option>
                    </select>
                    <Textarea
                      value={driveForm.description}
                      onChange={(event) => setDriveForm((current) => ({ ...current, description: event.target.value }))}
                      placeholder="Role summary, process notes, or company expectations"
                      className="md:col-span-2 min-h-[110px]"
                    />
                  </div>

                  <div className="mt-4">
                    <Button onClick={handleCreateDrive} disabled={savingDrive}>
                      {savingDrive ? 'Saving Drive...' : 'Create Placement Drive'}
                    </Button>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.08 }}
                  className="glass-card p-6"
                >
                  <h2 className="text-lg font-semibold mb-4">Active Drives</h2>
                  <div className="space-y-3">
                    {(data?.placement_drives || []).length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        No placement drives created yet.
                      </div>
                    ) : (
                      (data?.placement_drives || []).map((drive) => (
                        <div key={drive.id} className="rounded-2xl border border-border/60 bg-card/40 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="font-medium">{drive.company_name}</div>
                              <div className="text-sm text-muted-foreground">{drive.role_title}</div>
                            </div>
                            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs text-primary">
                              {drive.status}
                            </span>
                          </div>
                          <div className="mt-3 text-sm text-muted-foreground">
                            Eligible students: {drive.eligible_count} • Threshold: {drive.minimum_ready_score}
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {drive.target_branches.map((branch) => (
                              <span key={`${drive.id}-${branch}`} className="rounded-full bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground">
                                {branch}
                              </span>
                            ))}
                          </div>
                          <div className="mt-3 space-y-2">
                            {drive.top_candidates.slice(0, 3).map((candidate) => (
                              <div key={`${drive.id}-${candidate.id}`} className="rounded-xl bg-background/70 p-3 text-sm">
                                <div className="font-medium">{candidate.name}</div>
                                <div className="text-muted-foreground">
                                  {candidate.verification_id} • {candidate.branch || 'Branch pending'} • {candidate.score}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>

              <div className="grid lg:grid-cols-3 gap-8 mb-8">
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="lg:col-span-2 glass-card p-6"
                >
                  <h2 className="text-lg font-semibold mb-4">Top Skill Distribution</h2>
                  <div className="h-[320px]">
                    {!data?.skill_distribution.length ? (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        No skill distribution data yet
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.skill_distribution}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                          />
                          <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{
                              background: 'hsl(var(--card))',
                              border: '1px solid hsl(var(--border))',
                              borderRadius: '8px',
                            }}
                          />
                          <Bar dataKey="count" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.08 }}
                  className="glass-card p-6"
                >
                  <h2 className="text-lg font-semibold mb-4">Readiness Split</h2>
                  <div className="h-[220px]">
                    {!data?.readiness_breakdown.length ? (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        No readiness data yet
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={data.readiness_breakdown}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={90}
                            dataKey="count"
                          >
                            {data.readiness_breakdown.map((item, index) => (
                              <Cell key={item.name} fill={readinessColors[index % readinessColors.length]} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: 'hsl(var(--card))',
                              border: '1px solid hsl(var(--border))',
                              borderRadius: '8px',
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                  <div className="space-y-2 mt-4">
                    {(data?.readiness_breakdown || []).map((item, index) => (
                      <div key={item.name} className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ background: readinessColors[index % readinessColors.length] }}
                          />
                          <span>{item.name}</span>
                        </div>
                        <span className="font-medium">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>

              <div className="grid lg:grid-cols-2 gap-8 mb-8">
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.12 }}
                  className="glass-card p-6"
                >
                  <h2 className="text-lg font-semibold mb-4">Placement Trend</h2>
                  <div className="h-[320px]">
                    {!data?.placement_trend.length ? (
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        No placement trend data yet
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data.placement_trend}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis
                            dataKey="date"
                            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                          />
                          <YAxis domain={[0, 100]} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{
                              background: 'hsl(var(--card))',
                              border: '1px solid hsl(var(--border))',
                              borderRadius: '8px',
                            }}
                          />
                          <Legend />
                          <Line type="monotone" dataKey="placement_ready" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="coding_skill_index" stroke="#10b981" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="authenticity_score" stroke="#f59e0b" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.18 }}
                  className="glass-card p-6"
                >
                  <h2 className="text-lg font-semibold mb-4">Intervention Suggestions</h2>
                  <div className="space-y-3">
                    {!data?.interventions.length ? (
                      <div className="text-center text-muted-foreground py-12">
                        No intervention suggestions for the current filter set.
                      </div>
                    ) : (
                      data.interventions.map((item) => (
                        <div
                          key={item.id}
                          className={`rounded-2xl border border-border/60 bg-card/40 p-4 border-l-4 ${severityStyles[item.severity]}`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="font-medium">{item.name}</div>
                              <div className="text-sm text-muted-foreground">
                                {item.verification_id} | {item.branch || 'Branch pending'}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-xl font-semibold">{item.score}</div>
                              <div className="text-xs text-muted-foreground">Ready score</div>
                            </div>
                          </div>
                          <div className="text-sm text-muted-foreground mt-3">{item.reason}</div>
                          <div className="text-sm mt-2">
                            <span className="font-medium">Action:</span> {item.action}
                          </div>
                          <div className="mt-4 grid gap-3">
                            <div className="grid gap-3 md:grid-cols-2">
                              <select
                                value={item.id in interventionDrafts ? interventionDrafts[item.id].status : item.status}
                                onChange={(event) =>
                                  setInterventionDrafts((current) => ({
                                    ...current,
                                    [item.id]: {
                                      ...(current[item.id] || {
                                        status: item.status,
                                        priority: item.priority,
                                        note: item.note,
                                        recommended_action: item.recommended_action || item.action,
                                      }),
                                      status: event.target.value as InterventionItem['status'],
                                    },
                                  }))
                                }
                                className="input-field"
                              >
                                <option value="planned">Planned</option>
                                <option value="in_progress">In Progress</option>
                                <option value="completed">Completed</option>
                                <option value="escalated">Escalated</option>
                              </select>
                              <select
                                value={item.id in interventionDrafts ? interventionDrafts[item.id].priority : item.priority}
                                onChange={(event) =>
                                  setInterventionDrafts((current) => ({
                                    ...current,
                                    [item.id]: {
                                      ...(current[item.id] || {
                                        status: item.status,
                                        priority: item.priority,
                                        note: item.note,
                                        recommended_action: item.recommended_action || item.action,
                                      }),
                                      priority: event.target.value as InterventionItem['priority'],
                                    },
                                  }))
                                }
                                className="input-field"
                              >
                                <option value="high">High Priority</option>
                                <option value="medium">Medium Priority</option>
                                <option value="low">Low Priority</option>
                              </select>
                            </div>
                            <Textarea
                              value={item.id in interventionDrafts ? interventionDrafts[item.id].recommended_action : (item.recommended_action || item.action)}
                              onChange={(event) =>
                                setInterventionDrafts((current) => ({
                                  ...current,
                                  [item.id]: {
                                    ...(current[item.id] || {
                                      status: item.status,
                                      priority: item.priority,
                                      note: item.note,
                                      recommended_action: item.recommended_action || item.action,
                                    }),
                                    recommended_action: event.target.value,
                                  },
                                }))
                              }
                              placeholder="Recommended support action"
                              className="min-h-[88px]"
                            />
                            <Textarea
                              value={item.id in interventionDrafts ? interventionDrafts[item.id].note : item.note}
                              onChange={(event) =>
                                setInterventionDrafts((current) => ({
                                  ...current,
                                  [item.id]: {
                                    ...(current[item.id] || {
                                      status: item.status,
                                      priority: item.priority,
                                      note: item.note,
                                      recommended_action: item.recommended_action || item.action,
                                    }),
                                    note: event.target.value,
                                  },
                                }))
                              }
                              placeholder="Advisor note, owner, or next checkpoint"
                              className="min-h-[88px]"
                            />
                            <Button
                              variant="outline"
                              onClick={() => handleInterventionSave(item.id)}
                              disabled={savingInterventionId === item.id}
                            >
                              {savingInterventionId === item.id ? 'Saving...' : 'Save Intervention'}
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>

              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.22 }}
                className="glass-card p-6"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5">
                  <div>
                    <h2 className="text-lg font-semibold">Filtered Cohort</h2>
                    <p className="text-sm text-muted-foreground">
                      Students currently included in this analytics view.
                    </p>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {data?.students.length || 0} student{data?.students.length === 1 ? '' : 's'}
                  </div>
                </div>

                {!data?.students.length ? (
                  <div className="text-center text-muted-foreground py-10">
                    No students match the current filters.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-sm">
                      <thead>
                        <tr className="border-b border-border/60 text-left text-muted-foreground">
                          <th className="py-3 pr-4 font-medium">Student</th>
                          <th className="py-3 pr-4 font-medium">Program</th>
                          <th className="py-3 pr-4 font-medium">Ready</th>
                          <th className="py-3 pr-4 font-medium">Coding</th>
                          <th className="py-3 pr-4 font-medium">Comm.</th>
                          <th className="py-3 pr-4 font-medium">Authenticity</th>
                          <th className="py-3 pr-0 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.students.map((student) => (
                          <tr key={student.id} className="border-b border-border/40">
                            <td className="py-4 pr-4">
                              <div className="font-medium">{student.name}</div>
                              <div className="text-xs text-muted-foreground">
                                {student.verification_id} | {student.college || 'College pending'}
                              </div>
                            </td>
                            <td className="py-4 pr-4 text-muted-foreground">
                              {student.course || 'Course pending'}
                              <div className="text-xs">
                                {[student.branch, student.year_of_study].filter(Boolean).join(' | ') || 'Details pending'}
                              </div>
                            </td>
                            <td className="py-4 pr-4 font-semibold">{student.scores.placement_ready}</td>
                            <td className="py-4 pr-4">{student.scores.coding_skill_index}</td>
                            <td className="py-4 pr-4">{student.scores.communication_score}</td>
                            <td className="py-4 pr-4">{student.scores.authenticity_score}</td>
                            <td className="py-4 pr-0">
                              <span
                                className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  student.profile_verified
                                    ? 'bg-primary/10 text-primary'
                                    : 'bg-muted/60 text-muted-foreground'
                                }`}
                              >
                                {student.profile_verified ? 'Verified' : 'Pending'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </motion.div>
            </>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
