import { motion } from 'framer-motion';
import { GraduationCap, Briefcase, Building2, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

const iconMap = {
  GraduationCap,
  Building2,
  Briefcase,
};

type UserType = {
  icon: keyof typeof iconMap;
  title: string;
  description: string;
  features: string[];
  cta: string;
  href: string;
  gradient: string;
};

export function UserTypes({ userTypes }: { userTypes: UserType[] }) {
  return (
    <section id="ecosystem" className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-card/60 via-transparent to-card/60" />
      <div className="absolute inset-0 noise-bg" />

      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="eyebrow-badge">Who It Is For</span>
          <h2 className="section-title mt-6 mb-6">
            Built for the <span className="gradient-text">Entire Ecosystem</span>
          </h2>
          <p className="section-subtitle max-w-2xl mx-auto">
            Whether you are a student, recruiter, or university, we have the tools you need.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {userTypes.map((type, index) => {
            const Icon = iconMap[type.icon] || GraduationCap;
            return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
              className="group perspective-1000"
            >
              <div className="glass-card p-8 h-full flex flex-col card-hover relative overflow-hidden tilt-card">
                {/* Top Gradient Line */}
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${type.gradient}`} />

                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${type.gradient} flex items-center justify-center mb-6`}>
                  <Icon className="w-7 h-7 text-primary-foreground" />
                </div>

                <h3 className="text-2xl font-semibold mb-3">{type.title}</h3>
                <p className="text-muted-foreground mb-6">{type.description}</p>

                <ul className="space-y-3 mb-8 flex-grow">
                  {type.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-3 text-sm">
                      <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${type.gradient}`} />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link to={type.href}>
                  <Button variant="outline" className="w-full group-hover:border-primary/50">
                    {type.cta}
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
              </div>
            </motion.div>
          );
          })}
        </div>
      </div>
    </section>
  );
}

