import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GraduationCap, Building2, Briefcase, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { buildApiUrl } from '@/lib/api';

const roleConfigs = {
  student: {
    icon: GraduationCap,
    title: 'Student Login',
    description: 'Access your skill verification dashboard',
    redirectTo: '/dashboard',
  },
  university: {
    icon: Building2,
    title: 'University Login',
    description: 'Manage student verifications and analytics',
    redirectTo: '/university/dashboard',
  },
  recruiter: {
    icon: Briefcase,
    title: 'Recruiter Login',
    description: 'Find and verify top talent',
    redirectTo: '/recruiter/dashboard',
  },
};

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const role = location.pathname.split('/')[1] as keyof typeof roleConfigs;
  const config = roleConfigs[role];

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  if (!config) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>Invalid Role</CardTitle>
            <CardDescription>Please select a valid role to login</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch(buildApiUrl('/api/accounts/login/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store tokens and user data
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem('userRole', data.user.role);
        localStorage.setItem('user', JSON.stringify(data.user));
        if (data?.user?.role !== role) {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('userRole');
          localStorage.removeItem('user');
          setError(`This account is not authorized for the ${role} portal.`);
          return;
        }
        navigate(config.redirectTo);
      } else {
        if (data?.approval_status === 'pending') {
          setError('Your account is pending admin approval. Try again after approval.');
        } else if (data?.approval_status === 'rejected') {
          setError(data.error || 'Your account request was rejected. Contact support or resubmit.');
        } else {
          setError(data.error || 'Login failed');
        }
      }
    } catch (error) {
      setError('Network error. Please try again.');
    }
  };

  const Icon = config.icon;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
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
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-sm text-destructive text-center">{error}</div>
              )}

              <Button type="submit" className="w-full">
                Sign In
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

            {role === 'student' && (
              <div className="mt-4 text-center">
                <button
                  onClick={() => navigate('/student/register')}
                  className="text-sm text-primary hover:text-primary/90"
                >
                  New here? Create a student account
                </button>
              </div>
            )}

            {(role === 'recruiter' || role === 'university') && (
              <div className="mt-4 text-center">
                <button
                  onClick={() => navigate(`/${role}/register`)}
                  className="text-sm text-primary hover:text-primary/90"
                >
                  Need access? Request a {role} account
                </button>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
