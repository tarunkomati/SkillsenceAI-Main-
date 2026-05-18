import { motion } from 'framer-motion';
import { Users, Target, Award, TrendingUp } from 'lucide-react';

const iconMap = {
  Users,
  Target,
  Award,
  TrendingUp,
};

type AboutContent = {
  title?: string;
  subtitle?: string;
  items?: { icon: keyof typeof iconMap; title: string; description: string }[];
};

export function AboutSection({ content }: { content?: AboutContent }) {
  const items = content?.items || [];
  return (
    <section id="about" className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 hero-grid opacity-10" />
      <div className="container-custom">
        <div className="max-w-4xl mx-auto text-center mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="section-title mb-6"
          >
            {content?.title || ''}
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="section-subtitle max-w-2xl mx-auto"
          >
            {content?.subtitle || ''}
          </motion.p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {items.map((item, index) => {
            const Icon = iconMap[item.icon] || Users;
            return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="glass-card p-6 text-center group hover:scale-105 transition-transform perspective-1000 tilt-card"
            >
              <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <Icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
              <p className="text-muted-foreground">{item.description}</p>
            </motion.div>
          );
          })}
        </div>
      </div>
    </section>
  );
}
