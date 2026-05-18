import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Code,
  Eye,
  FileCode2,
  GitBranch,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { buildApiUrl } from '@/lib/api';

interface FileReview {
  path: string;
  role: string;
  score: number;
  risk_level: 'low' | 'medium' | 'high';
  lines: number;
  strengths: string[];
  risks: string[];
  summary: string;
  ai_generated?: string;
  ai_confidence?: number;
  ai_rationale?: string;
  issues?: Record<string, number>;
}

interface AIReview {
  summary: string;
  strengths: string[];
  concerns: string[];
  next_steps: string[];
}

interface CommitActivity {
  sample_size: number;
  unique_authors?: number;
  message_quality?: string;
  last_commit_at?: string | null;
  recent_messages?: string[];
  categories?: Record<string, number>;
}

interface TreeOverview {
  total_files?: number;
  source_files?: number;
  test_files?: number;
  documentation_files?: number;
  configuration_files?: number;
  ci_files?: number;
  has_readme?: boolean;
  has_license?: boolean;
  has_ci?: boolean;
  has_docker?: boolean;
}

interface AnalysisMetrics {
  engineering_score: number;
  maintainability_score: number;
  security_score: number;
  testing_score: number;
  documentation_score: number;
  architecture_score: number;
  originality_score: number;
  ai_generated?: string;
  ai_confidence?: number;
  languages?: string[];
  files_analyzed?: number;
  lines_analyzed?: number;
  tree_overview?: TreeOverview;
  commit_activity?: CommitActivity;
  architecture?: string[];
  strengths?: string[];
  risks?: string[];
  recommendations?: string[];
  file_reviews?: FileReview[];
  ai_review?: AIReview | null;
  stars?: number;
  forks?: number;
  open_issues?: number;
  default_branch?: string | null;
  pushed_at?: string | null;
}

interface AnalysisItem {
  id: number;
  repo_name?: string;
  repo_url: string;
  description: string;
  score: number;
  metrics: AnalysisMetrics;
  status: string;
  created_at: string;
}

interface FilePreviewPayload {
  path: string;
  sha: string;
  size: number;
  lines: number;
  preview: string;
  truncated: boolean;
  review?: FileReview | null;
}

const scoreCards: Array<{
  key: keyof AnalysisMetrics;
  label: string;
  icon: typeof Sparkles;
}> = [
  { key: 'engineering_score', label: 'Engineering', icon: Sparkles },
  { key: 'security_score', label: 'Security', icon: ShieldCheck },
  { key: 'testing_score', label: 'Testing', icon: CheckCircle2 },
  { key: 'documentation_score', label: 'Docs', icon: FileCode2 },
];

const formatLabel = (value: string) =>
  value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const riskBadgeVariant = (risk: string) => {
  if (risk === 'high') {
    return 'destructive' as const;
  }
  if (risk === 'medium') {
    return 'secondary' as const;
  }
  return 'outline' as const;
};

export default function DashboardCodeAnalysis() {
  const [items, setItems] = useState<AnalysisItem[]>([]);
  const [repoUrl, setRepoUrl] = useState('');
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('');
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState('');
  const [filePreview, setFilePreview] = useState<FilePreviewPayload | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const loadFilePreview = async (reportId: number, path: string) => {
    const token = localStorage.getItem('accessToken');
    if (!token || !reportId || !path) {
      setFilePreview(null);
      return;
    }
    setLoadingPreview(true);
    try {
      const response = await fetch(
        buildApiUrl(`/api/skills/code-analysis/${reportId}/file/?path=${encodeURIComponent(path)}`),
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.error) {
        setFilePreview(null);
        return;
      }
      setFilePreview(data);
    } catch {
      setFilePreview(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/code-analysis/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        const nextItems = Array.isArray(data?.items) ? data.items : [];
        setItems(nextItems);
        if (nextItems[0]?.id) {
          setSelectedReportId((current) => current ?? nextItems[0].id);
        }
      })
      .catch(() => {
        setItems([]);
      });
  }, []);

  const selectedReport = useMemo(
    () => items.find((item) => item.id === selectedReportId) ?? items[0] ?? null,
    [items, selectedReportId],
  );

  useEffect(() => {
    if (!selectedReport?.id) {
      setFilePreview(null);
      setSelectedFilePath('');
      return;
    }
    const firstPath = selectedReport.metrics?.file_reviews?.[0]?.path ?? '';
    setSelectedFilePath(firstPath);
  }, [selectedReport?.id]);

  useEffect(() => {
    if (!selectedReport?.id || !selectedFilePath) {
      setFilePreview(null);
      return;
    }
    loadFilePreview(selectedReport.id, selectedFilePath);
  }, [selectedReport?.id, selectedFilePath]);

  const handleAnalyze = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !repoUrl.trim()) {
      setMessage('Enter a valid GitHub repository URL.');
      return;
    }
    setMessage('');
    setRunning(true);
    try {
      const res = await fetch(buildApiUrl('/api/skills/code-analysis/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMessage(data?.error || 'Unable to run analysis right now.');
        return;
      }
      setItems((current) => {
        const withoutCurrent = current.filter((item) => item.id !== data.id);
        return [data, ...withoutCurrent];
      });
      setSelectedReportId(data.id);
      setSelectedFilePath(data?.metrics?.file_reviews?.[0]?.path || '');
      setRepoUrl('');
      setMessage('Repository analysis completed.');
    } catch {
      setMessage('Network error. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-bold mb-2">Git Work Analysis</h1>
            <p className="text-muted-foreground">
              Deep repository review with commit signals, file-level risks, structure checks, and optional AI coaching.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.05 }}
            className="glass-card p-6 mb-6"
          >
            <div className="flex flex-col lg:flex-row gap-4">
              <Input
                placeholder="https://github.com/owner/repository"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
              />
              <Button onClick={handleAnalyze} disabled={running || !repoUrl.trim()}>
                {running ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <GitBranch className="w-4 h-4 mr-2" />}
                {running ? 'Analyzing Repository...' : 'Run Deep Review'}
              </Button>
            </div>
            {message ? (
              <div className="mt-4 rounded-xl border border-border/50 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                {message}
              </div>
            ) : null}
          </motion.div>

          {items.length === 0 ? (
            <div className="glass-card p-12 text-center text-muted-foreground">
              <Code className="w-12 h-12 mx-auto mb-4 text-primary" />
              <div className="text-lg font-medium text-foreground mb-2">No repository reviews yet</div>
              <div>Run a deep GitHub review to inspect code quality, file risks, commit habits, and AI-backed recommendations.</div>
            </div>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
              <div className="space-y-4">
                <Card className="glass-card border-border/60">
                  <CardHeader>
                    <CardTitle className="text-lg">Previous Reviews</CardTitle>
                    <CardDescription>Select a report to inspect the repo in detail.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {items.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setSelectedReportId(item.id)}
                        className={`w-full rounded-2xl border p-4 text-left transition ${
                          selectedReport?.id === item.id
                            ? 'border-primary/50 bg-primary/5'
                            : 'border-border/50 bg-background/40 hover:border-primary/30'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-medium">{item.repo_name || item.repo_url}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {new Date(item.created_at).toLocaleString()}
                            </div>
                          </div>
                          <div className="text-lg font-semibold">{item.score}</div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {(item.metrics.languages || []).slice(0, 3).map((language) => (
                            <Badge key={language} variant="outline">
                              {language}
                            </Badge>
                          ))}
                        </div>
                      </button>
                    ))}
                  </CardContent>
                </Card>
              </div>

              {selectedReport ? (
                <div className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-4">
                    {scoreCards.map(({ key, label, icon: Icon }) => (
                      <Card key={key} className="glass-card border-border/60">
                        <CardContent className="p-5">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm text-muted-foreground">{label}</div>
                              <div className="text-2xl font-semibold mt-1">{selectedReport.metrics[key] ?? 0}</div>
                            </div>
                            <Icon className="w-5 h-5 text-primary" />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  <Card className="glass-card border-border/60">
                    <CardHeader>
                      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                        <div>
                          <CardTitle>{selectedReport.repo_name || selectedReport.repo_url}</CardTitle>
                          <CardDescription className="mt-2">{selectedReport.description}</CardDescription>
                        </div>
                        <a
                          href={selectedReport.repo_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-primary hover:underline"
                        >
                          Open repository
                        </a>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-5">
                      <div className="flex flex-wrap gap-2">
                        {(selectedReport.metrics.architecture || []).map((tag) => (
                          <Badge key={tag}>{tag}</Badge>
                        ))}
                        {(selectedReport.metrics.languages || []).map((language) => (
                          <Badge key={language} variant="outline">
                            {language}
                          </Badge>
                        ))}
                      </div>

                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 text-sm">
                        <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                          <div className="text-muted-foreground">Files reviewed</div>
                          <div className="font-semibold text-lg mt-1">{selectedReport.metrics.files_analyzed ?? 0}</div>
                        </div>
                        <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                          <div className="text-muted-foreground">Lines inspected</div>
                          <div className="font-semibold text-lg mt-1">{selectedReport.metrics.lines_analyzed ?? 0}</div>
                        </div>
                        <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                          <div className="text-muted-foreground">Originality</div>
                          <div className="font-semibold text-lg mt-1">{selectedReport.metrics.originality_score ?? 0}</div>
                        </div>
                        <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                          <div className="text-muted-foreground">AI likelihood</div>
                          <div className="font-semibold text-lg mt-1">
                            {formatLabel(selectedReport.metrics.ai_generated || 'unknown')} ({selectedReport.metrics.ai_confidence ?? 0})
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="grid gap-4 xl:grid-cols-3">
                    <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <CheckCircle2 className="w-4 h-4 text-primary" />
                        <div className="font-medium">Strengths</div>
                      </div>
                      <div className="space-y-2 text-sm text-muted-foreground">
                        {(selectedReport.metrics.strengths || []).map((item) => (
                          <div key={item}>{item}</div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                        <div className="font-medium">Risks</div>
                      </div>
                      <div className="space-y-2 text-sm text-muted-foreground">
                        {(selectedReport.metrics.risks || []).map((item) => (
                          <div key={item}>{item}</div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="w-4 h-4 text-primary" />
                        <div className="font-medium">Next Improvements</div>
                      </div>
                      <div className="space-y-2 text-sm text-muted-foreground">
                        {(selectedReport.metrics.recommendations || []).map((item) => (
                          <div key={item}>{item}</div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
                    <Card className="glass-card border-border/60">
                      <CardHeader>
                        <CardTitle className="text-lg">File-by-File Review</CardTitle>
                        <CardDescription>Inspect the files that most influence code quality, maintainability, and risk.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {(selectedReport.metrics.file_reviews || []).map((file) => (
                          <button
                            key={file.path}
                            type="button"
                            onClick={() => setSelectedFilePath(file.path)}
                            className={`w-full rounded-2xl border p-4 text-left transition ${
                              selectedFilePath === file.path
                                ? 'border-primary/50 bg-primary/5'
                                : 'border-border/50 bg-background/40 hover:border-primary/30'
                            }`}
                          >
                            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                              <div className="min-w-0">
                                <div className="font-medium break-all">{file.path}</div>
                                <div className="text-sm text-muted-foreground mt-1">{file.summary}</div>
                              </div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant={riskBadgeVariant(file.risk_level)}>{formatLabel(file.risk_level)} risk</Badge>
                                <Badge variant="outline">{formatLabel(file.role)}</Badge>
                                <Badge variant="outline">{file.lines} lines</Badge>
                                <div className="text-lg font-semibold">{file.score}</div>
                              </div>
                            </div>
                            <div className="grid gap-3 md:grid-cols-2 mt-4 text-sm">
                              <div>
                                <div className="font-medium mb-2">Strengths</div>
                                <div className="space-y-1 text-muted-foreground">
                                  {(file.strengths || []).map((item) => (
                                    <div key={item}>{item}</div>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <div className="font-medium mb-2">Risks</div>
                                <div className="space-y-1 text-muted-foreground">
                                  {(file.risks || []).map((item) => (
                                    <div key={item}>{item}</div>
                                  ))}
                                </div>
                              </div>
                            </div>
                            {file.ai_generated ? (
                              <div className="mt-3 text-xs text-muted-foreground">
                                AI likelihood: {formatLabel(file.ai_generated)} ({file.ai_confidence ?? 0})
                              </div>
                            ) : null}
                          </button>
                        ))}
                      </CardContent>
                    </Card>

                    <div className="space-y-6">
                      <Card className="glass-card border-border/60">
                        <CardHeader>
                          <CardTitle className="text-lg">Commit Activity</CardTitle>
                          <CardDescription>Sampled recent commit signals from GitHub.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4 text-sm">
                          <div className="grid gap-3 sm:grid-cols-2">
                            <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                              <div className="text-muted-foreground">Commits reviewed</div>
                              <div className="font-semibold text-lg mt-1">{selectedReport.metrics.commit_activity?.sample_size ?? 0}</div>
                            </div>
                            <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                              <div className="text-muted-foreground">Message quality</div>
                              <div className="font-semibold text-lg mt-1">
                                {formatLabel(selectedReport.metrics.commit_activity?.message_quality || 'unknown')}
                              </div>
                            </div>
                          </div>
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                            <div className="flex items-center gap-2 mb-3">
                              <Clock3 className="w-4 h-4 text-primary" />
                              <div className="font-medium">Recent messages</div>
                            </div>
                            <div className="space-y-2 text-muted-foreground">
                              {(selectedReport.metrics.commit_activity?.recent_messages || []).map((item) => (
                                <div key={item}>{item}</div>
                              ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="glass-card border-border/60">
                        <CardHeader>
                          <CardTitle className="text-lg">File Preview</CardTitle>
                          <CardDescription>Open the selected reviewed file to inspect the captured snapshot.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          {loadingPreview ? (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Loading file preview...
                            </div>
                          ) : filePreview ? (
                            <div className="space-y-4">
                              <div className="flex items-center justify-between gap-3 flex-wrap">
                                <div>
                                  <div className="font-medium break-all">{filePreview.path}</div>
                                  <div className="text-sm text-muted-foreground">{filePreview.lines} lines / {filePreview.size} bytes</div>
                                </div>
                                <Button variant="outline" size="sm" onClick={() => loadFilePreview(selectedReport.id, filePreview.path)}>
                                  <Eye className="w-4 h-4 mr-2" />
                                  Refresh preview
                                </Button>
                              </div>
                              {filePreview.review?.ai_rationale ? (
                                <div className="rounded-xl border border-border/50 bg-background/40 p-3 text-sm text-muted-foreground">
                                  {filePreview.review.ai_rationale}
                                </div>
                              ) : null}
                              <pre className="max-h-[420px] overflow-auto rounded-2xl border border-border/50 bg-slate-950 p-4 text-xs text-slate-100 whitespace-pre-wrap break-words">
                                {filePreview.preview}
                              </pre>
                              {filePreview.truncated ? (
                                <div className="text-xs text-muted-foreground">
                                  Preview truncated. The snapshot stores more content than is shown here.
                                </div>
                              ) : null}
                            </div>
                          ) : (
                            <div className="text-sm text-muted-foreground">Select a reviewed file to inspect its captured content.</div>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  </div>

                  <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                    <Card className="glass-card border-border/60">
                      <CardHeader>
                        <CardTitle className="text-lg">Repository Footprint</CardTitle>
                        <CardDescription>Signals derived from the repository tree and hosting metadata.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                            <div className="text-muted-foreground">Total files</div>
                            <div className="font-semibold text-lg mt-1">{selectedReport.metrics.tree_overview?.total_files ?? 0}</div>
                          </div>
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                            <div className="text-muted-foreground">Test files</div>
                            <div className="font-semibold text-lg mt-1">{selectedReport.metrics.tree_overview?.test_files ?? 0}</div>
                          </div>
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                            <div className="text-muted-foreground">Stars / forks</div>
                            <div className="font-semibold text-lg mt-1">
                              {selectedReport.metrics.stars ?? 0} / {selectedReport.metrics.forks ?? 0}
                            </div>
                          </div>
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                            <div className="text-muted-foreground">Open issues</div>
                            <div className="font-semibold text-lg mt-1">{selectedReport.metrics.open_issues ?? 0}</div>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {selectedReport.metrics.tree_overview?.has_readme ? <Badge variant="outline">README</Badge> : null}
                          {selectedReport.metrics.tree_overview?.has_ci ? <Badge variant="outline">CI</Badge> : null}
                          {selectedReport.metrics.tree_overview?.has_docker ? <Badge variant="outline">Docker</Badge> : null}
                          {selectedReport.metrics.tree_overview?.has_license ? <Badge variant="outline">License</Badge> : null}
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="glass-card border-border/60">
                      <CardHeader>
                        <CardTitle className="text-lg">AI Review</CardTitle>
                        <CardDescription>Senior-review style coaching generated from the repository signals.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4 text-sm">
                        {selectedReport.metrics.ai_review ? (
                          <>
                            <div className="rounded-2xl border border-border/50 bg-background/40 p-4 text-muted-foreground">
                              <div className="flex items-center gap-2 mb-2 font-medium text-foreground">
                                <BrainCircuit className="w-4 h-4 text-primary" />
                                Summary
                              </div>
                              {selectedReport.metrics.ai_review.summary}
                            </div>
                            <div className="grid gap-4 md:grid-cols-3">
                              <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                                <div className="font-medium mb-2">Strengths</div>
                                <div className="space-y-2 text-muted-foreground">
                                  {selectedReport.metrics.ai_review.strengths.map((item) => (
                                    <div key={item}>{item}</div>
                                  ))}
                                </div>
                              </div>
                              <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                                <div className="font-medium mb-2">Concerns</div>
                                <div className="space-y-2 text-muted-foreground">
                                  {selectedReport.metrics.ai_review.concerns.map((item) => (
                                    <div key={item}>{item}</div>
                                  ))}
                                </div>
                              </div>
                              <div className="rounded-2xl border border-border/50 bg-background/40 p-4">
                                <div className="font-medium mb-2">Next steps</div>
                                <div className="space-y-2 text-muted-foreground">
                                  {selectedReport.metrics.ai_review.next_steps.map((item) => (
                                    <div key={item}>{item}</div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="rounded-2xl border border-border/50 bg-background/40 p-4 text-muted-foreground">
                            <div className="flex items-center gap-2 mb-2 text-foreground font-medium">
                              <ShieldAlert className="w-4 h-4 text-amber-500" />
                              AI coaching not available
                            </div>
                            Set <code>OPENAI_API_KEY</code> on the backend to attach repo-specific AI coaching to each review. The heuristic engineering review still works without it.
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
