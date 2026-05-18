import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Login from "./pages/Login";
import RoleRegister from "./pages/RoleRegister";
import StudentStart from "./pages/StudentStart";
import StudentRegister from "./pages/StudentRegister";
import Dashboard from "./pages/Dashboard";
import DashboardCodeAnalysis from "./pages/DashboardCodeAnalysis";
import DashboardMedia from "./pages/DashboardMedia";
import DashboardProgress from "./pages/DashboardProgress";
import DashboardRoadmap from "./pages/DashboardRoadmap";
import DashboardResumeBuilder from "./pages/DashboardResumeBuilder";
import DashboardSettings from "./pages/DashboardSettings";
import SkillPassport from "./pages/SkillPassport";
import AIInterview from "./pages/AIInterview";
import RecruiterDashboard from "./pages/RecruiterDashboard";
import UniversityDashboard from "./pages/UniversityDashboard";
import OpsLogin from "./pages/OpsLogin";
import OpsApprovals from "./pages/OpsApprovals";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/student/start" element={<StudentStart />} />
          <Route path="/student" element={<Login />} />
          <Route path="/student/register" element={<StudentRegister />} />
          <Route path="/university" element={<Login />} />
          <Route path="/university/register" element={<RoleRegister />} />
          <Route path="/recruiter" element={<Login />} />
          <Route path="/recruiter/register" element={<RoleRegister />} />
          <Route path="/ops/login" element={<OpsLogin />} />
          <Route path="/ops/approvals" element={<OpsApprovals />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/code" element={<DashboardCodeAnalysis />} />
          <Route path="/dashboard/media" element={<DashboardMedia />} />
          <Route path="/dashboard/passport" element={<SkillPassport />} />
          <Route path="/dashboard/interview" element={<AIInterview />} />
          <Route path="/dashboard/progress" element={<DashboardProgress />} />
          <Route path="/dashboard/roadmap" element={<DashboardRoadmap />} />
          <Route path="/dashboard/resume-builder" element={<DashboardResumeBuilder />} />
          <Route path="/dashboard/settings" element={<DashboardSettings />} />
          <Route path="/recruiter/dashboard" element={<RecruiterDashboard />} />
          <Route path="/university/dashboard" element={<UniversityDashboard />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
