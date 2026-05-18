import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Mail, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

type ContactContent = {
  email?: string;
  phone?: string;
  headline?: string;
  subtext?: string;
};

export function CTASection({ content }: { content?: ContactContent }) {
  return (
    <section id="contact-us" className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-transparent to-accent/10" />
      <div className="absolute inset-0 hero-grid opacity-10" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/10 rounded-full blur-3xl" />

      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="glass-card p-8 md:p-12 lg:p-16 text-center max-w-4xl mx-auto perspective-1000 tilt-card relative overflow-hidden"
        >
          <div className="absolute -top-6 right-10 w-24 h-24 rounded-full bg-primary/20 blur-2xl float-3d" />
          <div className="eyebrow-badge mb-6">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>Contact Us</span>
          </div>

          <h2 className="section-title mb-6">
            {content?.headline || ''}
          </h2>

          <p className="section-subtitle mb-8 max-w-2xl mx-auto">
            {content?.subtext || ''}
          </p>

          <div className="flex flex-col gap-4 justify-center items-center">
            <div className="flex items-center gap-3 text-base font-semibold">
              <Mail className="w-5 h-5 text-primary" />
              <span>{content?.email || ''}</span>
            </div>
            <div className="flex items-center gap-3 text-base font-semibold">
              <Phone className="w-5 h-5 text-primary" />
              <span>{content?.phone || ''}</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8">
            <Link to="/student/start">
              <Button variant="hero" size="xl">
                Get Started Free
                <ArrowRight className="w-5 h-5" />
              </Button>
            </Link>
            <Button variant="glass" size="xl">
              Schedule Demo
            </Button>
          </div>

          <p className="text-muted-foreground text-sm mt-6">
            No credit card required - free forever plan available
          </p>
        </motion.div>
      </div>
    </section>
  );
}

