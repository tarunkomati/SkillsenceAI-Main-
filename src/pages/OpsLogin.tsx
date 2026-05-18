import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, LockKeyhole, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { buildApiUrl } from '@/lib/api';

export default function OpsLogin() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const response = await fetch(buildApiUrl('/api/accounts/login/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        setError(payload?.error || 'Login failed.');
        return;
      }

      if (!payload?.user?.is_staff && !payload?.user?.is_superuser) {
        setError('This account does not have approval console access.');
        return;
      }

      localStorage.setItem('accessToken', payload.access);
      localStorage.setItem('refreshToken', payload.refresh);
      localStorage.setItem('userRole', payload.user.role);
      localStorage.setItem('user', JSON.stringify(payload.user));
      navigate('/ops/approvals');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="w-full max-w-md"
      >
        <Card className="glass-card">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-8 h-8 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">Approval Console</CardTitle>
            <CardDescription>Staff-only login for recruiter and university access review.</CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(event) => setFormData((current) => ({ ...current, email: event.target.value }))}
                  placeholder="staff@company.com"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(event) => setFormData((current) => ({ ...current, password: event.target.value }))}
                  placeholder="Enter password"
                  required
                />
              </div>

              <div className="rounded-2xl border border-border/60 bg-card/40 p-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-2 text-foreground font-medium">
                  <LockKeyhole className="w-4 h-4 text-primary" />
                  Restricted access
                </div>
                <p className="mt-2">Only `is_staff` or `is_superuser` accounts can open the approval console.</p>
              </div>

              {error && <div className="text-sm text-center text-destructive">{error}</div>}

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? 'Signing In...' : 'Open Approval Console'}
              </Button>
            </form>

            <div className="mt-4 text-center">
              <button
                onClick={() => navigate('/')}
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-2 mx-auto"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Home
              </button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
