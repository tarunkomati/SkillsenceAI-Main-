import { motion } from 'framer-motion';
import { Upload, Brain, BadgeCheck, ArrowRight } from 'lucide-react';

const iconMap = {
  Upload,
  Brain,
  BadgeCheck,
};

type Step = {
  icon: keyof typeof iconMap;
  title: string;
  description: string;
  color: 'primary' | 'accent';
};

export function HowItWorks({ steps }: { steps: Step[] }) {
  return (
    <section className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-card/50 to-transparent" />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="eyebrow-badge">How It Works</span>
          <h2 className="section-title mt-6 mb-6">
            Three Steps to <span className="gradient-text">Verified Skills</span>
          </h2>
          <p className="section-subtitle max-w-2xl mx-auto">
            Our streamlined process transforms raw evidence into verified credentials in minutes.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connection Line */}
          <div className="hidden md:block absolute top-24 left-1/4 right-1/4 h-0.5 bg-gradient-to-r from-primary via-accent to-primary opacity-30" />

          {steps.map((step, index) => {
            const Icon = iconMap[step.icon] || Upload;
            return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
              className="relative perspective-1000"
            >
              <div className="glass-card p-8 text-center card-hover h-full tilt-card">
                {/* Step Number */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-sm font-bold text-primary-foreground">
                  {index + 1}
                </div>

                {/* Icon */}
                <div
                  className={`w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center ${
                    step.color === 'primary' ? 'bg-primary/10' : 'bg-accent/10'
                  }`}
                >
                  <Icon className={`w-8 h-8 ${step.color === 'primary' ? 'text-primary' : 'text-accent'}`} />
                </div>

                <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-muted-foreground text-sm">{step.description}</p>
              </div>

              {/* Arrow (between cards) */}
              {index < steps.length - 1 && (
                <div className="hidden md:flex absolute top-24 -right-4 z-10">
                  <ArrowRight className="w-8 h-8 text-primary/30" />
                </div>
              )}
            </motion.div>
          );
          })}
        </div>
      </div>
    </section>
  );
}
