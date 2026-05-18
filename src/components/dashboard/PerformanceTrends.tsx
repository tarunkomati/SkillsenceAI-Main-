import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { buildApiUrl } from '@/lib/api';

interface TrendPoint {
  date: string;
  coding_skill_index: number;
  communication_score: number;
  authenticity_score: number;
  placement_ready: number;
}

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

export function PerformanceTrends() {
  const [series, setSeries] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setLoading(false);
      return;
    }

    fetch(buildApiUrl('/api/skills/performance/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data?.series)) {
          setSeries(data.series);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="glass-card p-6"
      >
        <div className="h-5 w-40 bg-muted rounded mb-4 animate-pulse" />
        <div className="h-52 bg-muted/40 rounded-xl animate-pulse" />
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Performance Trends</h3>
          <p className="text-xs text-muted-foreground">Last 90 days</p>
        </div>
        <span className="text-xs text-muted-foreground">AI analytics</span>
      </div>

      {series.length === 0 ? (
        <div className="text-center text-muted-foreground py-12">
          No history yet. Recalculate scores to start tracking.
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ left: 0, right: 16, top: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
              <XAxis dataKey="date" tickFormatter={formatDate} stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip labelFormatter={formatDate} />
              <Legend />
              <Line type="monotone" dataKey="coding_skill_index" name="Coding" stroke="#2563eb" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="communication_score" name="Communication" stroke="#10b981" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="authenticity_score" name="Authenticity" stroke="#f59e0b" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="placement_ready" name="Placement" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
}
