import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Video, Upload, Music } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { buildApiUrl } from '@/lib/api';

interface MediaItem {
  id: number;
  title: string;
  media_type: string;
  status: string;
  file_url: string;
  created_at: string;
}

export default function DashboardMedia() {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [title, setTitle] = useState('');
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/media/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setItems(Array.isArray(data?.items) ? data.items : []))
      .catch(() => setItems([]));
  }, []);

  const handleUpload = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !file) {
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('media_type', mediaType);
    if (title.trim()) {
      formData.append('title', title.trim());
    }
    try {
      const res = await fetch(buildApiUrl('/api/skills/media/'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setItems((prev) => [data, ...prev]);
        setTitle('');
        setFile(null);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-bold mb-2">Video/Audio</h1>
            <p className="text-muted-foreground">Recorded interviews and evidence</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            <div className="flex flex-col lg:flex-row gap-4 mb-6">
              <Input
                placeholder="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant={mediaType === 'video' ? 'default' : 'outline'}
                  onClick={() => setMediaType('video')}
                >
                  <Video className="w-4 h-4 mr-2" />
                  Video
                </Button>
                <Button
                  type="button"
                  variant={mediaType === 'audio' ? 'default' : 'outline'}
                  onClick={() => setMediaType('audio')}
                >
                  <Music className="w-4 h-4 mr-2" />
                  Audio
                </Button>
              </div>
              <Input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <Button onClick={handleUpload} disabled={uploading || !file}>
                <Upload className="w-4 h-4 mr-2" />
                {uploading ? 'Uploading...' : 'Upload'}
              </Button>
            </div>

            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Video className="w-10 h-10 mb-3 text-primary" />
                No media uploaded yet
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item) => (
                  <div key={item.id} className="p-4 rounded-xl bg-muted/30 flex items-center justify-between">
                    <div>
                      <div className="font-medium">{item.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.media_type} • {item.status}
                      </div>
                    </div>
                    <a
                      href={item.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      View
                    </a>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
