import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Briefcase, Building2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { buildApiUrl } from '@/lib/api';

const roleConfigs = {
  recruiter: {
    icon: Briefcase,
    title: 'Recruiter Access Request',
    description: 'Create a recruiter account and submit it for approval.',
    organizationLabel: 'Company Name',
    loginPath: '/recruiter',
  },
  university: {
    icon: Building2,
    title: 'University Access Request',
    description: 'Create a university account and submit it for approval.',
    organizationLabel: 'Institution Name',
    loginPath: '/university',
  },
};

export default function RoleRegister() {
  const navigate = useNavigate();
  const location = useLocation();
  const role = location.pathname.split('/')[1] as keyof typeof roleConfigs;
  const config = roleConfigs[role];

  const [formData, setFormData] = useState({
    full_name: '',
    organization_name: '',
    email: '',
    password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!config) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="glass-card w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>Invalid Role</CardTitle>
            <CardDescription>Use the recruiter or university portal to request access.</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(buildApiUrl('/api/accounts/signup/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: formData.full_name,
          organization_name: formData.organization_name,
          email: formData.email,
          password: formData.password,
          role,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to submit approval request.');
      }

      setSuccess('Request submitted. An admin must approve the account before you can sign in.');
      setFormData({
        full_name: '',
        organization_name: '',
        email: '',
        password: '',
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to submit approval request.');
    } finally {
      setSubmitting(false);
    }
  };

  const Icon = config.icon;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-lg"
      >
        <Card className="glass-card">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4">
              <Icon className="w-8 h-8 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">{config.title}</CardTitle>
            <CardDescription>{config.description}</CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    value={formData.full_name}
                    onChange={(event) => setFormData({ ...formData, full_name: event.target.value })}
                    placeholder="Full name"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="organization_name">{config.organizationLabel}</Label>
                  <Input
                    id="organization_name"
                    value={formData.organization_name}
                    onChange={(event) => setFormData({ ...formData, organization_name: event.target.value })}
                    placeholder={config.organizationLabel}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Work Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(event) => setFormData({ ...formData, email: event.target.value })}
                  placeholder="name@company.com"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(event) => setFormData({ ...formData, password: event.target.value })}
                  placeholder="Create a password"
                  required
                />
              </div>

              <div className="rounded-2xl border border-border/60 bg-card/40 p-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <Sparkles className="w-4 h-4 text-primary" />
                  Approval workflow
                </div>
                <p className="mt-2">
                  New recruiter and university accounts are created in a pending state and unlocked after admin review.
                </p>
              </div>

              {error && <div className="text-sm text-destructive text-center">{error}</div>}
              {success && <div className="text-sm text-primary text-center">{success}</div>}

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Request Access'}
              </Button>
            </form>

            <div className="mt-4 text-center">
              <button
                onClick={() => navigate(config.loginPath)}
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-2 mx-auto"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Login
              </button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
