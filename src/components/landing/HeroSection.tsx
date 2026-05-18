import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight, Play, Sparkles, Shield, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';

type HeroContent = {
  badge_text?: string;
  title?: string;
  highlight?: string;
  subtitle?: string;
  stats?: { value: string; label: string }[];
};

export function HeroSection({ content }: { content?: HeroContent }) {
  const stats = content?.stats || [];
  return (
    <section id="hero" className="relative min-h-screen flex items-center overflow-hidden pt-24 pb-16">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-hero-gradient" />
      <div className="absolute inset-0 bg-mesh-glow opacity-70" />
      <div className="absolute inset-0 hero-grid opacity-20" />
      <div className="absolute inset-0 noise-bg" />
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-primary/15 rounded-full blur-3xl animate-blob" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-accent/15 rounded-full blur-3xl animate-blob animation-delay-2000" />
      <div className="absolute top-1/2 right-20 w-[520px] h-[520px] opacity-30">
        <div className="absolute inset-0 border border-primary/20 rounded-full animate-spin-slow" />
        <div className="absolute inset-8 border border-accent/20 rounded-full animate-spin-slow" style={{ animationDirection: 'reverse' }} />
        <div className="absolute inset-16 border border-primary/10 rounded-full animate-spin-slow" />
      </div>

      <div className="container-custom relative z-10">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-12 items-center">
          <div className="max-w-2xl">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="eyebrow-badge mb-8"
            >
              <Sparkles className="w-4 h-4 text-primary" />
              <span>{content?.badge_text || ''}</span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-semibold leading-tight mb-6"
            >
              {content?.title || ''}
              <br />
              <span className="gradient-text text-glow">{content?.highlight || ''}</span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-lg sm:text-xl text-muted-foreground max-w-xl mb-10"
            >
              {content?.subtitle || ''}
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex flex-col sm:flex-row gap-4 mb-12"
            >
              <Link to="/student/start">
                <Button variant="hero" size="xl" className="w-full sm:w-auto">
                  Get Started Free
                  <ArrowRight className="w-5 h-5" />
                </Button>
              </Link>
              <Button variant="glass" size="xl" className="w-full sm:w-auto">
                <Play className="w-5 h-5" />
                Watch Demo
              </Button>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="grid grid-cols-1 sm:grid-cols-3 gap-4"
            >
              {stats.map((stat, index) => (
                <div key={index} className="glass-card p-4 text-left">
                  <div className="text-2xl font-semibold gradient-text">{stat.value}</div>
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="glass-card p-8 relative overflow-hidden perspective-1000 tilt-card"
          >
            <div className="absolute -top-10 -left-6 w-24 h-24 rounded-full bg-primary/20 blur-2xl float-3d" />
            <div className="absolute -bottom-8 right-6 w-20 h-20 rounded-full bg-accent/20 blur-2xl float-3d" />
            <div className="absolute top-0 right-0 w-40 h-40 bg-accent/20 blur-3xl" />
            <div className="flex items-center justify-between mb-8">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Live Skill Passport</p>
                <h3 className="text-2xl font-semibold mt-2">Verification Pulse</h3>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-border/60 bg-card/80 px-3 py-1 text-xs font-semibold">
                <Shield className="w-4 h-4 text-primary" />
                Trusted
              </div>
            </div>

            <div className="space-y-5">
              {[
                { label: 'Authenticity', value: 88, icon: Shield },
                { label: 'Coding Signal', value: 82, icon: Brain },
                { label: 'Communication', value: 76, icon: Sparkles },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="space-y-2">
                    <div className="flex items-center justify-between text-sm font-semibold">
                      <span className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-primary" />
                        {item.label}
                      </span>
                      <span className="text-muted-foreground">{item.value}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted/60 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary to-accent"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-8 flex items-center justify-between rounded-2xl border border-border/60 bg-card/70 px-4 py-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Placement Ready</p>
                <p className="text-lg font-semibold">Score: 84</p>
              </div>
              <div className="flex items-center gap-2 text-primary font-semibold">
                <Sparkles className="w-4 h-4" />
                Ranked
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
