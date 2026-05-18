import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const navItems = [
  { label: 'Home', href: '#hero', type: 'scroll' },
  { label: 'About', href: '#about', type: 'scroll' },
  { label: 'Features', href: '#features', type: 'scroll' },
  { label: 'Get Started', href: '#ecosystem', type: 'scroll' },
  { label: 'Contact Us', href: '#contact-us', type: 'scroll' },
];

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const handleNavClick = (href: string) => {
    setIsOpen(false);
    if (href.startsWith('#')) {
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <header className="fixed top-0 w-full z-50 bg-background/70 backdrop-blur-xl border-b border-border/60">
      <nav className="container-custom">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3">
            <img src="https://i.ibb.co/M51qFRs5/Screenshot-2025-12-18-125743-removebg-preview.png" alt="Skillsence AI Logo" className="w-9 h-9 rounded-full ring-1 ring-border/60 bg-card/80" />
            <span className="text-lg sm:text-xl font-semibold tracking-tight">Skillsence AI</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-2 ml-auto rounded-full border border-border/60 bg-card/70 px-2 py-1 shadow-[0_16px_50px_-40px_hsl(var(--foreground)/0.4)]">
            {navItems.map((item) => {
              if (item.type === 'scroll') {
                return (
                  <Button
                    key={item.label}
                    variant="ghost"
                    onClick={() => handleNavClick(item.href)}
                    className="px-4 text-xs uppercase tracking-[0.2em]"
                  >
                    {item.label}
                  </Button>
                );
              } else {
                return (
                  <Link key={item.label} to={item.href}>
                    <Button variant="ghost" className="px-4 text-xs uppercase tracking-[0.2em]">
                      {item.label}
                    </Button>
                  </Link>
                );
              }
            })}
            <Link to="/ops/login">
              <Button variant="outline" className="px-4 text-xs uppercase tracking-[0.2em]">
                Staff
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden rounded-full border border-border/60 bg-card/70 p-2"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle menu"
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden py-4 border-t border-border/60">
            <div className="flex flex-col space-y-3">
              {navItems.map((item) => {
                if (item.type === 'scroll') {
                  return (
                    <Button
                      key={item.label}
                      variant="ghost"
                      onClick={() => handleNavClick(item.href)}
                      className="w-full justify-start text-xs uppercase tracking-[0.2em]"
                    >
                      {item.label}
                    </Button>
                  );
                } else {
                  return (
                    <Link key={item.label} to={item.href} onClick={() => setIsOpen(false)}>
                      <Button variant="ghost" className="w-full justify-start text-xs uppercase tracking-[0.2em]">
                        {item.label}
                      </Button>
                    </Link>
                  );
                }
              })}
              <Link key="staff" to="/ops/login" onClick={() => setIsOpen(false)}>
                <Button variant="outline" className="w-full justify-start text-xs uppercase tracking-[0.2em]">
                  Staff
                </Button>
              </Link>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export { Navbar };
