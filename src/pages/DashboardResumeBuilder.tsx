import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Button } from '@/components/ui/button';
import { buildApiUrl } from '@/lib/api';
import { Download, FileText, Link2, Sparkles } from 'lucide-react';

interface ResumeEducation {
  college: string;
  course: string;
  branch: string;
  year_of_study: string;
  cgpa: number | null;
}

interface ResumeSkill {
  name: string;
  level: string;
  score: number;
  verified: boolean;
}

interface ResumeProject {
  title: string;
  description: string;
  link?: string;
}

interface ResumeLink {
  label: string;
  url: string;
}

interface ResumePreview {
  full_name: string;
  headline: string;
  summary: string;
  generated_at?: string;
  education: ResumeEducation;
  skills: ResumeSkill[];
  achievements: string[];
  projects: ResumeProject[];
  links: ResumeLink[];
}

export default function DashboardResumeBuilder() {
  const navigate = useNavigate();
  const [preview, setPreview] = useState<ResumePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      navigate('/student');
      return;
    }

    fetch(buildApiUrl('/api/skills/resume-builder/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          throw new Error(payload?.error || 'Unable to load resume builder.');
        }
        return res.json();
      })
      .then((payload: ResumePreview) => {
        setPreview(payload);
        setError('');
      })
      .catch((fetchError: unknown) => {
        setPreview(null);
        setError(fetchError instanceof Error ? fetchError.message : 'Unable to load resume builder.');
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleDownload = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    setDownloading(true);
    try {
      const response = await fetch(buildApiUrl('/api/skills/resume-builder/pdf/'), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Unable to generate resume PDF.');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'skillsense-resume.pdf';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : 'Unable to generate resume PDF.');
    } finally {
      setDownloading(false);
    }
  };

  const educationLine = [
    preview?.education.course,
    preview?.education.branch,
    preview?.education.year_of_study,
  ]
    .filter(Boolean)
    .join(' | ');

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />

      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
          >
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                <Sparkles className="h-3.5 w-3.5" />
                Resume Builder
              </div>
              <h1 className="mt-4 text-3xl font-bold">Generated Resume</h1>
              <p className="text-muted-foreground">
                Turn your verified profile, scores, and evidence into a recruiter-ready resume.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => navigate('/dashboard/settings')}>
                Edit Profile Inputs
              </Button>
              <Button onClick={handleDownload} disabled={downloading || loading || !preview}>
                <Download className="mr-2 h-4 w-4" />
                {downloading ? 'Generating...' : 'Download PDF'}
              </Button>
            </div>
          </motion.div>

          {loading ? (
            <div className="glass-card p-8 text-center text-muted-foreground">
              Building your resume preview...
            </div>
          ) : error ? (
            <div className="glass-card p-8 text-center text-destructive">{error}</div>
          ) : preview ? (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55 }}
              className="space-y-6"
            >
              <div className="glass-card p-8">
                <div className="flex flex-col gap-4 border-b border-border/60 pb-6 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h2 className="text-3xl font-semibold">{preview.full_name}</h2>
                    <p className="mt-2 text-lg text-primary">{preview.headline}</p>
                    <div className="mt-3 text-sm text-muted-foreground">
                      {[preview.education.college, educationLine].filter(Boolean).join(' • ')}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-border/60 bg-card/50 p-4 text-sm text-muted-foreground">
                    <div className="font-medium text-foreground">Latest generation</div>
                    <div className="mt-1">
                      {preview.generated_at ? new Date(preview.generated_at).toLocaleString() : 'Just now'}
                    </div>
                  </div>
                </div>

                <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
                  <div className="space-y-6">
                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="flex items-center gap-2 text-lg font-semibold">
                        <FileText className="h-5 w-5 text-primary" />
                        Professional Summary
                      </h3>
                      <p className="mt-4 text-sm leading-7 text-muted-foreground">{preview.summary}</p>
                    </section>

                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="text-lg font-semibold">Projects & Evidence</h3>
                      <div className="mt-4 space-y-4">
                        {preview.projects.length === 0 ? (
                          <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                            No project evidence available yet. Run code analysis or upload project artifacts.
                          </div>
                        ) : (
                          preview.projects.map((project, index) => (
                            <div key={`${project.title}-${index}`} className="rounded-2xl border border-border/60 bg-background/70 p-4">
                              <div className="font-medium">{project.title}</div>
                              <div className="mt-2 text-sm text-muted-foreground">{project.description}</div>
                              {project.link && (
                                <a
                                  href={project.link}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="mt-3 inline-flex items-center gap-2 text-sm text-primary hover:underline"
                                >
                                  <Link2 className="h-4 w-4" />
                                  Open project
                                </a>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </section>

                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="text-lg font-semibold">Achievement Highlights</h3>
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        {preview.achievements.length === 0 ? (
                          <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                            Score highlights appear after platform analysis and interviews.
                          </div>
                        ) : (
                          preview.achievements.map((achievement, index) => (
                            <div key={`${achievement}-${index}`} className="rounded-2xl border border-border/60 bg-background/70 p-4 text-sm">
                              {achievement}
                            </div>
                          ))
                        )}
                      </div>
                    </section>
                  </div>

                  <div className="space-y-6">
                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="text-lg font-semibold">Education</h3>
                      <div className="mt-4 space-y-2 text-sm">
                        <div className="font-medium">{preview.education.college || 'College pending'}</div>
                        <div className="text-muted-foreground">{educationLine || 'Program details pending'}</div>
                        <div className="text-muted-foreground">
                          {preview.education.cgpa !== null ? `CGPA: ${preview.education.cgpa}` : 'CGPA pending'}
                        </div>
                      </div>
                    </section>

                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="text-lg font-semibold">Skills</h3>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {preview.skills.length === 0 ? (
                          <span className="text-sm text-muted-foreground">No verified skills yet</span>
                        ) : (
                          preview.skills.map((skill) => (
                            <span
                              key={skill.name}
                              className={`rounded-full px-3 py-1 text-xs font-medium ${
                                skill.verified
                                  ? 'bg-primary/10 text-primary'
                                  : 'bg-muted/60 text-muted-foreground'
                              }`}
                            >
                              {skill.name} • {skill.level}
                            </span>
                          ))
                        )}
                      </div>
                    </section>

                    <section className="rounded-3xl border border-border/60 bg-card/40 p-6">
                      <h3 className="text-lg font-semibold">Public Links</h3>
                      <div className="mt-4 space-y-3">
                        {preview.links.length === 0 ? (
                          <div className="text-sm text-muted-foreground">No public links connected yet.</div>
                        ) : (
                          preview.links.map((link) => (
                            <a
                              key={link.label}
                              href={link.url}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center justify-between rounded-2xl border border-border/60 bg-background/70 px-4 py-3 text-sm hover:border-primary/40"
                            >
                              <span className="font-medium">{link.label}</span>
                              <span className="truncate pl-3 text-muted-foreground">{link.url}</span>
                            </a>
                          ))
                        )}
                      </div>
                    </section>
                  </div>
                </div>
              </div>
            </motion.div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
