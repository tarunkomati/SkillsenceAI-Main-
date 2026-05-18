import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building2, CheckCircle2, Clock3, LogOut, RefreshCcw, ShieldCheck, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { buildApiUrl } from '@/lib/api';

type ApprovalStatus = 'approved' | 'pending' | 'rejected';
type ApprovalRole = 'recruiter' | 'university';

interface ApprovalRequestItem {
  id: number;
  full_name: string | null;
  email: string;
  username: string;
  role: ApprovalRole;
  organization_name: string | null;
  approval_status: ApprovalStatus;
  approval_notes: string | null;
  approved_at: string | null;
  date_joined: string | null;
  last_login: string | null;
}

interface ApprovalSummary {
  pending: number;
  approved: number;
  rejected: number;
  recruiters: number;
  universities: number;
}

const statusBadgeVariant: Record<ApprovalStatus, 'default' | 'secondary' | 'destructive'> = {
  approved: 'default',
  pending: 'secondary',
  rejected: 'destructive',
};

export default function OpsApprovals() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState<ApprovalRequestItem[]>([]);
  const [summary, setSummary] = useState<ApprovalSummary>({
    pending: 0,
    approved: 0,
    rejected: 0,
    recruiters: 0,
    universities: 0,
  });
  const [staffName, setStaffName] = useState('Staff');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | ApprovalStatus>('pending');
  const [roleFilter, setRoleFilter] = useState<'all' | ApprovalRole>('all');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [notesById, setNotesById] = useState<Record<number, string>>({});

  const clearSessionAndRedirect = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userRole');
    localStorage.removeItem('user');
    navigate('/ops/login');
  };

  const fetchRequests = async (token: string, showSpinner = false) => {
    if (showSpinner) {
      setRefreshing(true);
    }

    const params = new URLSearchParams();
    params.set('status', statusFilter);
    params.set('role', roleFilter);
    if (search.trim()) {
      params.set('search', search.trim());
    }

    try {
      const response = await fetch(buildApiUrl(`/api/accounts/staff/approvals/?${params.toString()}`), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.status === 401 || response.status === 403) {
        clearSessionAndRedirect();
        return;
      }

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to load approval requests.');
      }

      const nextRequests = Array.isArray(payload?.requests) ? payload.requests : [];
      setRequests(nextRequests);
      setSummary(payload?.summary || {
        pending: 0,
        approved: 0,
        rejected: 0,
        recruiters: 0,
        universities: 0,
      });
      setNotesById((current) => {
        const next = { ...current };
        nextRequests.forEach((item: ApprovalRequestItem) => {
          next[item.id] = item.approval_notes || '';
        });
        return next;
      });
      setError('');
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unable to load approval requests.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      navigate('/ops/login');
      return;
    }

    fetch(buildApiUrl('/api/accounts/profile/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Authentication required.');
        }
        const payload = await response.json();
        const user = payload?.user;
        if (!user?.is_staff && !user?.is_superuser) {
          throw new Error('Staff access required.');
        }
        setStaffName(user.full_name || user.username || 'Staff');
        localStorage.setItem('user', JSON.stringify(user));
        return fetchRequests(token);
      })
      .catch(() => {
        clearSessionAndRedirect();
      });
  }, [navigate]);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token || loading) {
      return;
    }
    fetchRequests(token);
  }, [roleFilter, search, statusFilter]);

  const handleLogout = async () => {
    const refresh = localStorage.getItem('refreshToken');
    const access = localStorage.getItem('accessToken');

    try {
      if (refresh) {
        await fetch(buildApiUrl('/api/accounts/logout/'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(access ? { Authorization: `Bearer ${access}` } : {}),
          },
          body: JSON.stringify({ refresh }),
        });
      }
    } catch {
      // Ignore logout API errors and clear session locally.
    } finally {
      clearSessionAndRedirect();
    }
  };

  const handleAction = async (requestId: number, action: 'approve' | 'reject' | 'pending') => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      clearSessionAndRedirect();
      return;
    }

    setSavingId(requestId);
    try {
      const response = await fetch(buildApiUrl(`/api/accounts/staff/approvals/${requestId}/`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action,
          approval_notes: notesById[requestId] || '',
        }),
      });

      if (response.status === 401 || response.status === 403) {
        clearSessionAndRedirect();
        return;
      }

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Unable to update approval state.');
      }

      await fetchRequests(token, false);
      setError('');
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to update approval state.');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur-xl">
        <div className="container-custom flex items-center justify-between gap-4 py-4">
          <div>
            <div className="flex items-center gap-2 text-primary">
              <ShieldCheck className="w-5 h-5" />
              <span className="text-sm font-medium uppercase tracking-[0.24em]">Staff Console</span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold">Access Approvals</h1>
            <p className="text-sm text-muted-foreground">Review recruiter and university sign-up requests without leaving the app.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:block text-right">
              <div className="text-sm font-medium">{staffName}</div>
              <div className="text-xs text-muted-foreground">Staff reviewer</div>
            </div>
            <Button variant="outline" onClick={() => {
              const token = localStorage.getItem('accessToken');
              if (token) {
                fetchRequests(token, true);
              }
            }} disabled={refreshing}>
              <RefreshCcw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="ghost" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="container-custom py-8">
        <div className="grid gap-4 md:grid-cols-5 mb-8">
          <div className="rounded-2xl border border-border/60 bg-card/50 p-4">
            <div className="flex items-center gap-2 text-amber-600">
              <Clock3 className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.18em]">Pending</span>
            </div>
            <div className="mt-3 text-3xl font-semibold">{summary.pending}</div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/50 p-4">
            <div className="flex items-center gap-2 text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.18em]">Approved</span>
            </div>
            <div className="mt-3 text-3xl font-semibold">{summary.approved}</div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/50 p-4">
            <div className="flex items-center gap-2 text-rose-600">
              <XCircle className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.18em]">Rejected</span>
            </div>
            <div className="mt-3 text-3xl font-semibold">{summary.rejected}</div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/50 p-4">
            <div className="flex items-center gap-2 text-primary">
              <Building2 className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.18em]">Recruiters</span>
            </div>
            <div className="mt-3 text-3xl font-semibold">{summary.recruiters}</div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/50 p-4">
            <div className="flex items-center gap-2 text-primary">
              <Building2 className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.18em]">Universities</span>
            </div>
            <div className="mt-3 text-3xl font-semibold">{summary.universities}</div>
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-card/40 p-5 mb-6">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setSearch(searchInput.trim());
            }}
            className="grid gap-4 lg:grid-cols-[1.4fr_220px_220px_auto] items-end"
          >
            <div>
              <label className="mb-2 block text-sm font-medium">Search</label>
              <Input
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Name, email, username, organization"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Status</label>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as 'all' | ApprovalStatus)}
                className="input-field w-full"
              >
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="all">All</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Role</label>
              <select
                value={roleFilter}
                onChange={(event) => setRoleFilter(event.target.value as 'all' | ApprovalRole)}
                className="input-field w-full"
              >
                <option value="all">All roles</option>
                <option value="recruiter">Recruiter</option>
                <option value="university">University</option>
              </select>
            </div>
            <Button type="submit">Apply Filters</Button>
          </form>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-3xl border border-border/60 bg-card/40 p-8 text-sm text-muted-foreground">
            Loading approval requests...
          </div>
        ) : requests.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-border/60 bg-card/20 p-8 text-sm text-muted-foreground">
            No accounts matched the current filters.
          </div>
        ) : (
          <div className="space-y-5">
            {requests.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.03 }}
                className="rounded-3xl border border-border/60 bg-card/40 p-6"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-xl font-semibold">{item.full_name || item.username}</h2>
                      <Badge variant={statusBadgeVariant[item.approval_status]}>
                        {item.approval_status}
                      </Badge>
                      <Badge variant="outline">{item.role}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {item.email} {item.organization_name ? `- ${item.organization_name}` : ''}
                    </div>
                    <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
                      <div>Joined: {item.date_joined ? new Date(item.date_joined).toLocaleString() : 'Unknown'}</div>
                      <div>Last login: {item.last_login ? new Date(item.last_login).toLocaleString() : 'Never'}</div>
                      <div>Username: {item.username}</div>
                      <div>Approved at: {item.approved_at ? new Date(item.approved_at).toLocaleString() : 'Not approved yet'}</div>
                    </div>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-3 lg:w-[360px]">
                    <Button
                      onClick={() => handleAction(item.id, 'approve')}
                      disabled={savingId === item.id}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => handleAction(item.id, 'reject')}
                      disabled={savingId === item.id}
                    >
                      Reject
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleAction(item.id, 'pending')}
                      disabled={savingId === item.id}
                    >
                      Reset Pending
                    </Button>
                  </div>
                </div>

                <div className="mt-5">
                  <label className="mb-2 block text-sm font-medium">Approval Notes</label>
                  <Textarea
                    value={notesById[item.id] || ''}
                    onChange={(event) =>
                      setNotesById((current) => ({
                        ...current,
                        [item.id]: event.target.value,
                      }))
                    }
                    placeholder="Why this account was approved, rejected, or sent back to pending"
                    className="min-h-[110px]"
                  />
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
