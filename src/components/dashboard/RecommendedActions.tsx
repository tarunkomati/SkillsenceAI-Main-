import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Mic, Upload, Target, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { buildApiUrl } from '@/lib/api';

interface Recommendation {
  id: number;
  title: string;
  description: string;
  action_type: string;
  priority: string;
  href: string;
  created_at: string;
}

const actionIcons = {
  ai_interview: Mic,
  upload_projects: Upload,
  complete_assessment: Target,
  review_roadmap: BookOpen,
};

const priorityColors = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-500',
  low: 'border-l-green-500',
};

export function RecommendedActions() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        if (!token) {
          setError('Login required to load recommendations.');
          setRecommendations([]);
          return;
        }
        const response = await fetch(buildApiUrl('/api/skills/recommendations/'), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setRecommendations(data);
        } else {
          setError(`Failed to load recommendations (${response.status}).`);
        }
      } catch (error) {
        console.error('Error fetching recommendations:', error);
        setError('Failed to load recommendations. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="glass-card p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recommended Actions</h3>
          <span className="text-xs text-muted-foreground">AI Suggestions</span>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="p-4 rounded-xl bg-muted/30 border-l-4 border-l-muted animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-muted rounded-xl"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded"></div>
                  <div className="h-3 bg-muted rounded w-3/4"></div>
                </div>
                <div className="w-5 h-5 bg-muted rounded"></div>
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
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Recommended Actions</h3>
        <span className="text-xs text-muted-foreground">AI Suggestions</span>
      </div>

      <div className="space-y-3">
        {error ? (
          <div className="text-center text-muted-foreground py-8">
            {error}
          </div>
        ) : recommendations.length > 0 ? (
          recommendations.map((item, index) => {
            const Icon = actionIcons[item.action_type as keyof typeof actionIcons] || Target;

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
              >
                <Link
                  to={item.href}
                  className={`block p-4 rounded-xl bg-muted/30 hover:bg-muted/50 border-l-4 ${
                    priorityColors[item.priority as keyof typeof priorityColors] || priorityColors.medium
                  } transition-all group`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{item.title}</div>
                      <p className="text-sm text-muted-foreground truncate">
                        {item.description}
                      </p>
                    </div>
                    <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              </motion.div>
            );
          })
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No recommendations available
          </div>
        )}
      </div>

      <Button variant="ghost" className="w-full mt-4">
        View All Recommendations
      </Button>
    </motion.div>
  );
}
