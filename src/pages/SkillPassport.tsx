import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import {
  BadgeCheck,
  Download,
  FileText,
  Share2,
  QrCode,
  Shield,
  Star,
  ExternalLink,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { useEffect, useState } from 'react';
import { buildApiUrl } from '@/lib/api';

interface EvidenceItem {
  source: string;
  title: string;
  detail: string;
  url?: string;
  created_at?: string | null;
}

interface VerifiedSkill {
  name: string;
  level: string;
  evidence: number;
  verified: boolean;
  evidence_items: EvidenceItem[];
}

export default function SkillPassport() {
  const navigate = useNavigate();
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [profile, setProfile] = useState<{
    full_name?: string;
    college?: string;
    course?: string;
    profile_verified?: boolean;
  } | null>(null);
  const [radarData, setRadarData] = useState<{ skill: string; level: number }[]>([]);
  const [barData, setBarData] = useState<{ name: string; score: number }[]>([]);
  const [verifiedSkills, setVerifiedSkills] = useState<VerifiedSkill[]>([]);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }

    fetch(buildApiUrl('/api/accounts/profile/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => setProfile(data?.user || null))
      .catch(() => setProfile(null));

    fetch(buildApiUrl('/api/skills/skill-passport/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        setRadarData(Array.isArray(data?.radar_data) ? data.radar_data : []);
        setBarData(Array.isArray(data?.bar_data) ? data.bar_data : []);
        setVerifiedSkills(Array.isArray(data?.verified_skills) ? data.verified_skills : []);
      })
      .catch(() => {
        setRadarData([]);
        setBarData([]);
        setVerifiedSkills([]);
      });
  }, []);

  const handleDownload = () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    setDownloading(true);
    fetch(buildApiUrl('/api/skills/skill-passport/pdf/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to download');
        }
        return res.blob();
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'skillverify-passport.pdf';
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      })
      .finally(() => setDownloading(false));
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />

      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold mb-2">Verified Skill Passport</h1>
                <p className="text-muted-foreground">
                  Your authenticated digital credential
                </p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline">
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </Button>
                <Button variant="outline" onClick={() => navigate('/dashboard/resume-builder')}>
                  <FileText className="w-4 h-4 mr-2" />
                  Resume Builder
                </Button>
                <Button variant="default" onClick={handleDownload} disabled={downloading}>
                  <Download className="w-4 h-4 mr-2" />
                  {downloading ? 'Preparing...' : 'Download PDF'}
                </Button>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="glass-card p-8 mb-8 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-primary/10 to-transparent rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-accent/10 to-transparent rounded-full blur-3xl" />

            <div className="relative flex items-start justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                  <span className="text-3xl font-bold text-primary-foreground">SV</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">{profile?.full_name || 'Student'}</h2>
                  <p className="text-muted-foreground">
                    {[profile?.course, profile?.college].filter(Boolean).join(' - ') || 'Profile details pending'}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    {profile?.profile_verified ? (
                      <>
                        <BadgeCheck className="w-5 h-5 text-primary" />
                        <span className="text-sm text-primary font-medium">Verified Profile</span>
                      </>
                    ) : (
                      <>
                        <Shield className="w-5 h-5 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground font-medium">
                          Verification pending
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="text-center">
                <div className="w-24 h-24 rounded-xl bg-white/10 border border-border/50 flex items-center justify-center mb-2">
                  <QrCode className="w-16 h-16 text-muted-foreground" />
                </div>
                <span className="text-xs text-muted-foreground">Scan to verify</span>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Overall Score', value: barData[0]?.score ? `${barData[0]?.score}/100` : '--', icon: Star },
                { label: 'Skills Verified', value: verifiedSkills.length ? `${verifiedSkills.length}` : '--', icon: BadgeCheck },
                { label: 'Evidence Items', value: verifiedSkills.length ? `${verifiedSkills.reduce((acc, item) => acc + (item.evidence || 0), 0)}` : '--', icon: Shield },
                { label: 'Authenticity', value: barData.find((item) => item.name.toLowerCase().includes('authentic'))?.score ? `${barData.find((item) => item.name.toLowerCase().includes('authentic'))?.score}%` : '--', icon: Shield },
              ].map((stat, index) => (
                <div key={index} className="text-center p-4 rounded-xl bg-muted/30">
                  <stat.icon className="w-6 h-6 mx-auto mb-2 text-primary" />
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-xs text-muted-foreground">{stat.label}</div>
                </div>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold mb-4">Skill Radar</h3>
                <div className="h-[250px]">
                  {radarData.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      No skills data yet
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="hsl(var(--border))" />
                        <PolarAngleAxis
                          dataKey="skill"
                          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                        />
                        <Radar
                          dataKey="level"
                          stroke="hsl(var(--primary))"
                          fill="hsl(var(--primary))"
                          fillOpacity={0.3}
                          strokeWidth={2}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-4">Core Competencies</h3>
                <div className="h-[250px]">
                  {barData.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      No competency data yet
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData} layout="vertical">
                        <XAxis type="number" domain={[0, 100]} hide />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                          width={100}
                        />
                        <Tooltip
                          contentStyle={{
                            background: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                          }}
                        />
                        <Bar
                          dataKey="score"
                          fill="hsl(var(--accent))"
                          radius={[0, 4, 4, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="glass-card p-6"
          >
            <h3 className="text-lg font-semibold mb-6">Verified Skills & Evidence</h3>
            <div className="space-y-3">
              {verifiedSkills.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No verified skills yet
                </div>
              ) : (
                verifiedSkills.map((skill, index) => (
                  <div key={index} className="border border-border/50 rounded-xl overflow-hidden">
                    <button
                      onClick={() =>
                        setExpandedSkill(expandedSkill === skill.name ? null : skill.name)
                      }
                      className="w-full p-4 flex items-center justify-between hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <BadgeCheck className="w-5 h-5 text-primary" />
                        <div className="text-left">
                          <div className="font-medium">{skill.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {skill.level} - {skill.evidence} evidence items
                          </div>
                        </div>
                      </div>
                      <ChevronDown
                        className={`w-5 h-5 text-muted-foreground transition-transform ${
                          expandedSkill === skill.name ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {expandedSkill === skill.name && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 pb-4 border-t border-border/50"
                      >
                        <div className="pt-4 space-y-3 text-sm text-muted-foreground">
                          {skill.evidence_items.length === 0 ? (
                            <div>No evidence attached yet.</div>
                          ) : (
                            skill.evidence_items.map((item, itemIndex) => {
                              const isExternal = Boolean(item.url?.startsWith('http'));
                              return (
                                <div
                                  key={`${skill.name}-${item.source}-${itemIndex}`}
                                  className="rounded-2xl border border-border/60 bg-card/50 p-4"
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div>
                                      <div className="font-medium text-foreground">{item.title}</div>
                                      <div className="mt-1">{item.detail}</div>
                                      {item.created_at && (
                                        <div className="mt-2 text-xs text-muted-foreground">
                                          {new Date(item.created_at).toLocaleString()}
                                        </div>
                                      )}
                                    </div>
                                    <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                                      {item.source}
                                    </span>
                                  </div>
                                  {item.url && (
                                    <a
                                      href={item.url}
                                      target={isExternal ? '_blank' : undefined}
                                      rel={isExternal ? 'noreferrer' : undefined}
                                      className="mt-3 inline-flex items-center gap-2 text-primary hover:underline"
                                    >
                                      Open source
                                      <ExternalLink className="h-4 w-4" />
                                    </a>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>
                      </motion.div>
                    )}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
