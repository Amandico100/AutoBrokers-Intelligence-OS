'use client';

import { useState, useRef } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Camera, Loader2, User } from 'lucide-react';
import { toast } from 'sonner';

/**
 * SPEC-132-A (A4) — a URL do avatar a partir da resposta ATUAL de `POST /api/upload`.
 * 📊 A rota nunca devolveu `publicUrl` (o mesmo defeito do anexo do chat, B3): o avatar subia e a tela recebia
 * `undefined`. A rota devolve `{ok, bucket, path, url}` — `url` é o proxy autenticado (`/api/storage/...`), que só
 * abre com sessão da MESMA corretora. O bucket `avatars` é PÚBLICO e o avatar aparece fora da sessão (o agente no
 * widget, por exemplo): por isso se monta a URL pública do Storage pelo `path`, como era antes da SPEC-054.
 * Sem a URL do Supabase no ambiente, fica o `url` do proxy.
 */
export function urlDoAvatarEnviado(resposta: unknown, supabaseUrl: string | undefined): string | null {
  const r = (resposta && typeof resposta === 'object' ? resposta : {}) as Record<string, unknown>;
  const path = typeof r.path === 'string' && r.path ? r.path : typeof r.filePath === 'string' ? r.filePath : '';
  const base = String(supabaseUrl || '').replace(/\/+$/, '');
  if (path && base) {
    const codificado = path.split('/').map((s) => encodeURIComponent(s)).join('/');
    return `${base}/storage/v1/object/public/avatars/${codificado}`;
  }
  return typeof r.url === 'string' && r.url ? r.url : null;
}

interface AvatarUploadProps {
  currentImageUrl?: string;
  onUpload: (url: string) => void;
  uploadPath: string; // e.g., "users", "agents", "admins"
  entityId: string; // e.g., user_id, agent_id
  size?: string; // Tailwind size classes, default "h-20 w-20"
  fallback?: string; // Fallback text for avatar
}

export function AvatarUpload({
  currentImageUrl,
  onUpload,
  uploadPath,
  entityId,
  size = 'h-20 w-20',
  fallback,
}: AvatarUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato inválido. Use: JPG, PNG, WEBP ou GIF');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Imagem muito grande. Máximo 5MB.');
      return;
    }

    // Show preview immediately
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    setIsUploading(true);

    try {
      // Upload via API
      const formData = new FormData();
      formData.append('file', file);
      formData.append('bucket', 'avatars');
      formData.append('path', `${uploadPath}`);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.motivo || errorData.error || 'Erro ao fazer upload');
      }

      const data = await response.json();
      const url = urlDoAvatarEnviado(data, process.env.NEXT_PUBLIC_SUPABASE_URL);
      if (!url) throw new Error('A foto subiu, mas não consegui o endereço dela. Tente de novo.');

      // Call the onUpload callback with the new URL
      onUpload(url);
      toast.success('Foto atualizada com sucesso!');
    } catch (error: any) {
      console.error('Avatar upload error:', error);
      toast.error(error.message || 'Erro ao fazer upload da imagem.');
      setPreviewUrl(null);
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const displayUrl = previewUrl || currentImageUrl;
  const initials = fallback?.slice(0, 2).toUpperCase() || 'U';

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={handleClick}
        disabled={isUploading}
        className="relative group focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background rounded-full"
      >
        <Avatar
          className={`${size} border-2 border-border group-hover:border-primary transition-colors`}
        >
          <AvatarImage src={displayUrl} alt="Avatar" className="object-cover" />
          <AvatarFallback className="bg-surface-2 text-muted-foreground text-lg">
            {fallback ? initials : <User className="h-8 w-8" />}
          </AvatarFallback>
        </Avatar>

        {/* Overlay on hover */}
        <div
          className={`absolute inset-0 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity ${isUploading ? 'opacity-100' : ''}`}
        >
          {isUploading ? (
            <Loader2 className="h-6 w-6 text-white animate-spin" />
          ) : (
            <Camera className="h-6 w-6 text-white" />
          )}
        </div>
      </button>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Small edit badge */}
      <div className="absolute -bottom-1 -right-1 bg-primary rounded-full p-1.5 border-2 border-background">
        <Camera className="h-3 w-3 text-primary-foreground" />
      </div>
    </div>
  );
}
