import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Circle, Clock } from 'lucide-react';
import { buildApiUrl } from '@/lib/api';

interface VerificationStep {
  id: number;
  title: string;
  description: string;
  status: string;
  completed_at: string | null;
  created_at: string;
}

export function VerificationTimeline() {
  const [steps, setSteps] = useState<VerificationStep[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVerificationSteps = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        const response = await fetch(buildApiUrl('/api/skills/verification-steps/'), {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setSteps(data);
        }
      } catch (error) {
        console.error('Error fetching verification steps:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchVerificationSteps();
  }, []);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Pending';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="glass-card p-6"
      >
        <h3 className="text-lg font-semibold mb-6">Verification Timeline</h3>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary via-accent to-muted" />
          <div className="space-y-6">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="flex items-start gap-4 relative">
                <div className="w-8 h-8 bg-muted rounded-full animate-pulse"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded animate-pulse"></div>
                  <div className="h-3 bg-muted rounded animate-pulse w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-6">Verification Timeline</h3>

      <div className="relative">
        {/* Vertical Line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary via-accent to-muted" />

        <div className="space-y-6">
          {steps.length > 0 ? (
            steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="flex items-start gap-4 relative"
              >
                {/* Icon */}
                <div className="relative z-10 w-8 h-8 rounded-full flex items-center justify-center bg-background">
                  {step.status === 'completed' ? (
                    <CheckCircle2 className="w-6 h-6 text-primary" />
                  ) : step.status === 'in_progress' ? (
                    <Clock className="w-6 h-6 text-accent animate-pulse" />
                  ) : (
                    <Circle className="w-6 h-6 text-muted-foreground" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 pb-2">
                  <div
                    className={`font-medium text-sm ${
                      step.status === 'pending' ? 'text-muted-foreground' : ''
                    }`}
                  >
                    {step.title}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {step.status === 'completed' && step.completed_at
                      ? formatDate(step.completed_at)
                      : step.status === 'in_progress'
                      ? 'In Progress'
                      : 'Pending'}
                  </div>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No verification steps available
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
