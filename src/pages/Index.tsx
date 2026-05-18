import { useEffect, useState } from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { HeroSection } from '@/components/landing/HeroSection';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { UserTypes } from '@/components/landing/UserTypes';
import { Testimonials } from '@/components/landing/Testimonials';
import { AboutSection } from '@/components/landing/AboutSection';
import { CTASection } from '@/components/landing/CTASection';
import { buildApiUrl } from '@/lib/api';

type LandingContent = {
  hero?: NonNullable<Parameters<typeof HeroSection>[0]['content']>;
  features?: Parameters<typeof FeaturesSection>[0]['features'];
  data_types?: Parameters<typeof FeaturesSection>[0]['dataTypes'];
  user_types?: Parameters<typeof UserTypes>[0]['userTypes'];
  testimonials?: Parameters<typeof Testimonials>[0]['testimonials'];
  about?: NonNullable<Parameters<typeof AboutSection>[0]['content']>;
  contact?: NonNullable<Parameters<typeof CTASection>[0]['content']>;
};

const Index = () => {
  const [content, setContent] = useState<LandingContent>({});

  useEffect(() => {
    fetch(buildApiUrl('/api/content/landing/'))
      .then((res) => res.json())
      .then((data: LandingContent) => setContent(data || {}))
      .catch(() => setContent({}));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection content={content.hero} />
        <FeaturesSection
          features={content.features || []}
          dataTypes={content.data_types || []}
        />
        <UserTypes userTypes={content.user_types || []} />
        <Testimonials testimonials={content.testimonials || []} />
        <AboutSection content={content.about} />
        <CTASection content={content.contact} />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
