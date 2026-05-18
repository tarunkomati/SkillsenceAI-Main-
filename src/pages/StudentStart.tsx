import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, LogIn, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function StudentStart() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        <Card className="glass-card">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4">
              <GraduationCap className="w-8 h-8 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">Welcome, Student</CardTitle>
            <CardDescription>Choose how you want to get started</CardDescription>
          </CardHeader>
          <CardContent className="grid md:grid-cols-2 gap-4">
            <Button
              variant="hero"
              size="xl"
              className="w-full"
              onClick={() => navigate('/student')}
            >
              <LogIn className="w-5 h-5" />
              Sign In
            </Button>
            <Button
              variant="glass"
              size="xl"
              className="w-full"
              onClick={() => navigate('/student/register')}
            >
              <UserPlus className="w-5 h-5" />
              Register
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
