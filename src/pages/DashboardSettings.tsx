import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Download, Save, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { buildApiUrl } from '@/lib/api';

type ResumeDocument = {
  filename?: string;
  download_path?: string;
  uploaded_at?: string | null;
};

type ProfileValue = string | number | boolean | ResumeDocument | null | undefined;

type UserProfile = {
  id?: number;
  username?: string;
  email?: string;
  role?: string;
  full_name?: string | null;
  gender?: string | null;
  phone_number?: string | null;
  college?: string | null;
  course?: string | null;
  branch?: string | null;
  year_of_study?: string | null;
  cgpa?: string | number | null;
  student_skills?: string | null;
  github_link?: string | null;
  leetcode_link?: string | null;
  linkedin_link?: string | null;
  codechef_link?: string | null;
  hackerrank_link?: string | null;
  codeforces_link?: string | null;
  gfg_link?: string | null;
  linkedin_headline?: string | null;
  linkedin_about?: string | null;
  linkedin_experience_count?: number | string | null;
  linkedin_skill_count?: number | string | null;
  linkedin_cert_count?: number | string | null;
  resume_document?: ResumeDocument | null;
  [key: string]: ProfileValue;
};

type ProfileResponse = {
  user?: UserProfile | null;
};

export default function DashboardSettings() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [downloadingResume, setDownloadingResume] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/accounts/profile/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data: ProfileResponse) => setProfile(data?.user || null))
      .catch(() => setProfile(null));
  }, []);

  const handleSave = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !profile) {
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(buildApiUrl('/api/accounts/profile/update/'), {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data?.user || profile);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadResume = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !profile?.resume_document) {
      return;
    }
    setDownloadingResume(true);
    try {
      const res = await fetch(buildApiUrl('/api/skills/resume/'), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        throw new Error('Unable to download resume.');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = profile.resume_document.filename || 'resume';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloadingResume(false);
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
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-bold mb-2">Settings</h1>
            <p className="text-muted-foreground">Profile and preferences</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            {profile ? (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="Full name"
                    value={profile.full_name || ''}
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  />
                  <Input
                    placeholder="Gender"
                    value={profile.gender || ''}
                    onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                  />
                  <Input
                    placeholder="Phone number"
                    value={profile.phone_number || ''}
                    onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                  />
                  <Input
                    placeholder="College"
                    value={profile.college || ''}
                    onChange={(e) => setProfile({ ...profile, college: e.target.value })}
                  />
                  <Input
                    placeholder="Course"
                    value={profile.course || ''}
                    onChange={(e) => setProfile({ ...profile, course: e.target.value })}
                  />
                  <Input
                    placeholder="Branch"
                    value={profile.branch || ''}
                    onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                  />
                  <Input
                    placeholder="Year of study"
                    value={profile.year_of_study || ''}
                    onChange={(e) => setProfile({ ...profile, year_of_study: e.target.value })}
                  />
                  <Input
                    placeholder="CGPA"
                    value={profile.cgpa || ''}
                    onChange={(e) => setProfile({ ...profile, cgpa: e.target.value })}
                  />
                  <Textarea
                    placeholder="Skills (comma-separated)"
                    value={profile.student_skills || ''}
                    onChange={(e) => setProfile({ ...profile, student_skills: e.target.value })}
                    rows={2}
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="GitHub URL"
                    value={profile.github_link || ''}
                    onChange={(e) => setProfile({ ...profile, github_link: e.target.value })}
                  />
                  <Input
                    placeholder="LeetCode URL"
                    value={profile.leetcode_link || ''}
                    onChange={(e) => setProfile({ ...profile, leetcode_link: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn URL"
                    value={profile.linkedin_link || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_link: e.target.value })}
                  />
                  <Input
                    placeholder="CodeChef URL"
                    value={profile.codechef_link || ''}
                    onChange={(e) => setProfile({ ...profile, codechef_link: e.target.value })}
                  />
                  <Input
                    placeholder="HackerRank URL"
                    value={profile.hackerrank_link || ''}
                    onChange={(e) => setProfile({ ...profile, hackerrank_link: e.target.value })}
                  />
                  <Input
                    placeholder="Codeforces URL"
                    value={profile.codeforces_link || ''}
                    onChange={(e) => setProfile({ ...profile, codeforces_link: e.target.value })}
                  />
                  <Input
                    placeholder="GeeksforGeeks URL"
                    value={profile.gfg_link || ''}
                    onChange={(e) => setProfile({ ...profile, gfg_link: e.target.value })}
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="LinkedIn headline"
                    value={profile.linkedin_headline || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_headline: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn experience count"
                    value={profile.linkedin_experience_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_experience_count: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn skills count"
                    value={profile.linkedin_skill_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_skill_count: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn certifications count"
                    value={profile.linkedin_cert_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_cert_count: e.target.value })}
                  />
                  <Textarea
                    placeholder="LinkedIn about summary"
                    value={profile.linkedin_about || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_about: e.target.value })}
                    rows={3}
                    className="md:col-span-2"
                  />
                </div>

                <div className="rounded-2xl border border-border/60 bg-card/40 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="font-medium">Resume on file</div>
                      {profile.resume_document ? (
                        <div className="text-sm text-muted-foreground">
                          {profile.resume_document.filename}
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground">
                          No original resume is stored for this account yet.
                        </div>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleDownloadResume}
                      disabled={downloadingResume || !profile.resume_document}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      {downloadingResume ? 'Downloading...' : 'Download Resume'}
                    </Button>
                  </div>
                </div>

                <Button onClick={handleSave} disabled={saving}>
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Settings className="w-10 h-10 mb-3 text-primary" />
                No settings available yet
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
