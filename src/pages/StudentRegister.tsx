import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, ArrowLeft, BadgeCheck, Sparkles, UserPlus, UploadCloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { buildApiUrl } from '@/lib/api';

export default function StudentRegister() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      if (!resumeFile) {
        setError('Please upload your resume.');
        setIsSubmitting(false);
        return;
      }

      const payload = new FormData();
      payload.append('full_name', formData.full_name);
      payload.append('email', formData.email);
      payload.append('password', formData.password);
      payload.append('resume', resumeFile);
      payload.append('role', 'student');

      const response = await fetch(buildApiUrl('/api/accounts/signup/'), {
        method: 'POST',
        body: payload,
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem('userRole', data.user.role);
        localStorage.setItem('user', JSON.stringify(data.user));
        navigate('/dashboard');
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-accent/10" />
        <div className="absolute -top-32 -right-24 w-[420px] h-[420px] rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-32 -left-24 w-[420px] h-[420px] rounded-full bg-accent/20 blur-3xl" />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 max-w-6xl mx-auto px-4 py-12"
        >
          <div className="grid lg:grid-cols-[320px_1fr] gap-8">
            <div className="space-y-6">
              <div className="glass-card p-6">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mb-4">
                  <GraduationCap className="w-7 h-7 text-primary-foreground" />
                </div>
                <h1 className="text-3xl font-bold mb-2">Student Registration</h1>
                <p className="text-sm text-muted-foreground">
                  Upload your resume and we will auto-build your profile.
                </p>
                <div className="mt-6 space-y-3 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary" />
                    Real platform analysis
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-accent" />
                    Evidence-backed scores
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary/50" />
                    Skill passport generation
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <BadgeCheck className="w-4 h-4 text-accent" />
                  Verification Note
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  We extract skills, education, and platform links from your resume.
                </p>
              </div>

              <button
                onClick={() => navigate('/student')}
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Login
              </button>
            </div>

            <Card className="glass-card">
              <CardHeader className="border-b border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl">Profile Build</CardTitle>
                    <CardDescription>Complete each block for accurate scoring</CardDescription>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Sparkles className="w-4 h-4 text-primary" />
                    2026-ready
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <UserPlus className="w-4 h-4 text-primary" />
                      <h3 className="text-sm font-semibold">Personal Details</h3>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="full_name">Full Name</Label>
                        <Input
                          id="full_name"
                          value={formData.full_name}
                          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                          placeholder="Enter your full name"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                          id="email"
                          type="email"
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="Email address"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input
                          id="password"
                          type="password"
                          value={formData.password}
                          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                          placeholder="Create a password"
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <UploadCloud className="w-4 h-4 text-accent" />
                      <h3 className="text-sm font-semibold">Resume Upload</h3>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="resume">Resume (PDF/DOCX/TXT)</Label>
                      <Input
                        id="resume"
                        type="file"
                        accept=".pdf,.docx,.txt"
                        onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                        required
                      />
                      <p className="text-xs text-muted-foreground">
                        We will auto-fill your education, skills, and platform links.
                      </p>
                    </div>
                  </div>

                  {error && <div className="text-sm text-destructive text-center">{error}</div>}

                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating Account...' : 'Create Account'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
