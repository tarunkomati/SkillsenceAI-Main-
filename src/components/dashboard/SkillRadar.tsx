import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import { buildApiUrl } from '@/lib/api';

export function SkillRadar() {
  const [skillData, setSkillData] = useState<{ skill: string; level: number; fullMark: number }[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/dashboard/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        const skills = Array.isArray(data?.skills) ? data.skills : [];
        setSkillData(
          skills.map((skill: { name: string; score?: number }) => ({
            skill: skill.name,
            level: skill.score ?? 50,
            fullMark: 100,
          }))
        );
      })
      .catch(() => setSkillData([]));
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-4">Skill Radar</h3>
      <div className="h-[300px]">
        {skillData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            No skills data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={skillData}>
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis
                dataKey="skill"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 100]}
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
              />
              <Radar
                name="Skills"
                dataKey="level"
                stroke="hsl(var(--primary))"
                fill="hsl(var(--primary))"
                fillOpacity={0.3}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  );
}
