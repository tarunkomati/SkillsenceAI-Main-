import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Mic,
  BadgeCheck,
  Settings,
  ChevronLeft,
  Sparkles,
  Code,
  FileText,
  TrendingUp,
  BookOpen,
  Video,
} from 'lucide-react';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  { icon: Code, label: 'Code Analysis', href: '/dashboard/code' },
  { icon: Video, label: 'Media', href: '/dashboard/media' },
  { icon: Mic, label: 'AI Interview', href: '/dashboard/interview' },
  { icon: BadgeCheck, label: 'Skill Passport', href: '/dashboard/passport' },
  { icon: FileText, label: 'Resume Builder', href: '/dashboard/resume-builder' },
  { icon: TrendingUp, label: 'Progress', href: '/dashboard/progress' },
  { icon: BookOpen, label: 'Roadmap', href: '/dashboard/roadmap' },
  { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
];

export function DashboardSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 80 : 260 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="fixed left-0 top-0 h-screen bg-sidebar border-r border-sidebar-border z-40"
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-sidebar-border">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-lg font-semibold gradient-text"
              >
                SkillVerify
              </motion.span>
            )}
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-3">
          <ul className="space-y-1">
            {menuItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <li key={item.href}>
                  <Link
                    to={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                      isActive
                        ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                        : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
                    }`}
                  >
                    <item.icon
                      className={`w-5 h-5 flex-shrink-0 ${
                        isActive ? 'text-primary' : 'group-hover:text-primary'
                      }`}
                    />
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-sm font-medium"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Collapse Button */}
        <div className="p-4 border-t border-sidebar-border">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-sidebar-accent/50 hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
          >
            <ChevronLeft
              className={`w-5 h-5 transition-transform ${collapsed ? 'rotate-180' : ''}`}
            />
            {!collapsed && <span className="text-sm">Collapse</span>}
          </button>
        </div>
      </div>
    </motion.aside>
  );
}
