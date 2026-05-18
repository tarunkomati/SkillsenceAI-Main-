import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Code, FileText, Video, CheckCircle2, Clock } from 'lucide-react';
import { buildApiUrl } from '@/lib/api';

interface Activity {
  id: number;
  activity_type: string;
  title: string;
  description: string;
  status: string;
  created_at: string;
}

const activityIcons = {
  github_analysis: Code,
  resume_verification: FileText,
  video_interview: Video,
  skill_badge: CheckCircle2,
};

export function RecentActivity() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        const response = await fetch(buildApiUrl('/api/skills/activities/'), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setActivities(data);
        }
      } catch (error) {
        console.error('Error fetching activities:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchActivities();
  }, []);

  const formatTimeAgo = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} days ago`;
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="glass-card p-6"
      >
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="flex items-start gap-4 p-3 rounded-xl">
              <div className="w-10 h-10 bg-muted rounded-xl animate-pulse"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-muted rounded animate-pulse"></div>
                <div className="h-3 bg-muted rounded animate-pulse"></div>
                <div className="h-3 bg-muted rounded animate-pulse w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
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
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {activities.length > 0 ? (
          activities.map((activity, index) => {
            const Icon = activityIcons[activity.activity_type as keyof typeof activityIcons] || Code;

            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="flex items-start gap-4 p-3 rounded-xl hover:bg-muted/30 transition-colors"
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    activity.status === 'completed' ? 'bg-primary/10' : 'bg-accent/10'
                  }`}
                >
                  <Icon
                    className={`w-5 h-5 ${
                      activity.status === 'completed' ? 'text-primary' : 'text-accent'
                    }`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">{activity.title}</span>
                    {activity.status === 'pending' && (
                      <span className="flex items-center gap-1 text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                        <Clock className="w-3 h-3" />
                        Processing
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground truncate">{activity.description}</p>
                  <span className="text-xs text-muted-foreground">{formatTimeAgo(activity.created_at)}</span>
                </div>
              </motion.div>
            );
          })
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No recent activities
          </div>
        )}
      </div>
    </motion.div>
  );
}
