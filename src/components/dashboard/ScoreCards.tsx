import { motion } from 'framer-motion';
import { Code, MessageSquare, Shield, Target } from 'lucide-react';

type ScoreKey = 'coding_skill_index' | 'communication_score' | 'authenticity_score' | 'placement_ready';

const scoreConfig: Record<ScoreKey, { icon: typeof Code; label: string; color: 'primary' | 'accent' }> = {
  coding_skill_index: {
    icon: Code,
    label: 'Coding Skill Index',
    color: 'primary',
  },
  communication_score: {
    icon: MessageSquare,
    label: 'Communication Score',
    color: 'accent',
  },
  authenticity_score: {
    icon: Shield,
    label: 'Authenticity Score',
    color: 'primary',
  },
  placement_ready: {
    icon: Target,
    label: 'Placement Ready',
    color: 'accent',
  },
};

export function ScoreCards({ scores }: { scores?: Record<string, number> }) {
  const resolvedScores = (scores || {}) as Record<ScoreKey, number>;

  const items = (Object.keys(scoreConfig) as ScoreKey[]).map((key) => ({
    key,
    score: resolvedScores[key] ?? 0,
    change: '+0',
    ...scoreConfig[key],
  }));

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((item, index) => (
        <motion.div
          key={item.key}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
          className="glass-card p-5 card-hover"
        >
          <div className="flex items-start justify-between mb-4">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                item.color === 'primary' ? 'bg-primary/10' : 'bg-accent/10'
              }`}
            >
              <item.icon
                className={`w-5 h-5 ${
                  item.color === 'primary' ? 'text-primary' : 'text-accent'
                }`}
              />
            </div>
            <span className="text-xs text-green-400 font-medium bg-green-400/10 px-2 py-0.5 rounded-full">
              {item.change}
            </span>
          </div>
          <div className="text-3xl font-bold mb-1">
            {scores ? item.score : '--'}
          </div>
          <div className="text-sm text-muted-foreground">{item.label}</div>
          
          {/* Progress Bar */}
          <div className="mt-3 h-1.5 bg-muted rounded-full overflow-hidden">
            {scores && (
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${item.score}%` }}
                transition={{ duration: 1, delay: index * 0.1 + 0.3 }}
                className={`h-full rounded-full ${
                  item.color === 'primary'
                    ? 'bg-gradient-to-r from-primary to-primary/60'
                    : 'bg-gradient-to-r from-accent to-accent/60'
                }`}
              />
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
