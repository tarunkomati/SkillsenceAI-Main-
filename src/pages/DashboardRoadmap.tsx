import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { BookOpen, CheckCircle2, Clock } from 'lucide-react';
import { buildApiUrl } from '@/lib/api';

interface RoadmapItem {
  title: string;
  description: string;
  status: string;
}

export default function DashboardRoadmap() {
  const [items, setItems] = useState<RoadmapItem[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/roadmap/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setItems(Array.isArray(data?.items) ? data.items : []))
      .catch(() => setItems([]));
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
            <h1 className="text-2xl font-bold mb-2">Roadmap</h1>
            <p className="text-muted-foreground">Personalized learning path</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <BookOpen className="w-10 h-10 mb-3 text-primary" />
                No roadmap items yet
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item, index) => (
                  <div key={`${item.title}-${index}`} className="p-4 rounded-xl bg-muted/30 flex items-start gap-3">
                    <div className="mt-1">
                      {item.status === 'completed' ? (
                        <CheckCircle2 className="w-5 h-5 text-primary" />
                      ) : (
                        <Clock className="w-5 h-5 text-accent" />
                      )}
                    </div>
                    <div>
                      <div className="font-medium">{item.title}</div>
                      <div className="text-sm text-muted-foreground">{item.description}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {item.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
