import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { buildApiUrl } from '@/lib/api';

interface ProgressResponse {
  series: Array<Record<string, number | string>>;
  streak: number;
  milestones: Record<string, number>;
}

export default function DashboardProgress() {
  const [data, setData] = useState<ProgressResponse | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/progress/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((payload) => setData(payload))
      .catch(() => setData(null));
  }, []);

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
            <h1 className="text-2xl font-bold mb-2">Progress</h1>
            <p className="text-muted-foreground">Track verification progress</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            {!data || !Array.isArray(data.series) ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <TrendingUp className="w-10 h-10 mb-3 text-primary" />
                No progress updates yet
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid md:grid-cols-3 gap-4">
                  {Object.entries(data.milestones || {}).map(([key, value]) => (
                    <div key={key} className="p-4 rounded-xl bg-muted/30">
                      <div className="text-xs text-muted-foreground">{key}</div>
                      <div className="text-2xl font-semibold">{value}</div>
                    </div>
                  ))}
                  <div className="p-4 rounded-xl bg-muted/30">
                    <div className="text-xs text-muted-foreground">streak</div>
                    <div className="text-2xl font-semibold">{data.streak || 0} days</div>
                  </div>
                </div>
                <div className="h-64">
                  {data.series.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      No trend data yet
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={data.series}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
                        <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                        <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
                        <Tooltip />
                        <Line type="monotone" dataKey="coding_skill_index" stroke="#2563eb" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="communication_score" stroke="#10b981" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="authenticity_score" stroke="#f59e0b" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="placement_ready" stroke="#0ea5e9" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
