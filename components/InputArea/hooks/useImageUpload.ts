'use client';

import { useState, useRef, useCallback } from 'react';

interface UseImageUploadProps {
  companyId?: string;
}

interface UseImageUploadReturn {
  pastedImage: { url: string; file: File } | null;
  pastedFile: { name: string; file: File } | null;
  uploadingImage: boolean;
  fileInputRef: React.RefObject<HTMLInputElement>;
  handlePaste: (event: React.ClipboardEvent) => void;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  removePastedImage: () => void;
  removePastedFile: () => void;
  uploadImageToSupabase: (file: File) => Promise<string | null>;
}

// F1 — documentos que o backend sabe extrair (docling).
const DOC_EXTENSIONS = ['.pdf', '.docx', '.pptx', '.xlsx', '.txt', '.csv', '.md'];

export function useImageUpload({ companyId }: UseImageUploadProps): UseImageUploadReturn {
  const [pastedImage, setPastedImage] = useState<{ url: string; file: File } | null>(null);
  const [pastedFile, setPastedFile] = useState<{ name: string; file: File } | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePaste = useCallback((event: React.ClipboardEvent) => {
    const items = event.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        event.preventDefault();
        const file = items[i].getAsFile();
        if (file) {
          const previewUrl = URL.createObjectURL(file);
          setPastedImage({ url: previewUrl, file });
        }
        break;
      }
    }
  }, []);

  const removePastedImage = useCallback(() => {
    if (pastedImage) {
      URL.revokeObjectURL(pastedImage.url);
      setPastedImage(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [pastedImage]);

  const removePastedFile = useCallback(() => {
    setPastedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type.startsWith('image/')) {
        const previewUrl = URL.createObjectURL(file);
        setPastedImage({ url: previewUrl, file });
        setPastedFile(null);
      } else if (DOC_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))) {
        // F1: documento (PDF etc.) — o backend extrai o texto via docling.
        setPastedFile({ name: file.name, file });
        setPastedImage(null);
      }
    }
  }, []);

  const uploadImageToSupabase = useCallback(
    async (file: File): Promise<string | null> => {
      if (!companyId) {
        console.error('[VISION] companyId required for upload');
        return null;
      }

      try {
        setUploadingImage(true);
        const formData = new FormData();
        formData.append('file', file);
        // F1: documentos vão para o chat-docs (o bucket chat-media só aceita imagem)
        formData.append('bucket', file.type.startsWith('image/') ? 'chat-media' : 'chat-docs');
        formData.append('path', `${companyId}/${new Date().toISOString().split('T')[0]}`);

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const error = await response.json();
          console.error('[VISION] Upload error:', error);
          return null;
        }

        const data = await response.json();
        return data.publicUrl;
      } catch (error) {
        console.error('[VISION] Upload failed:', error);
        return null;
      } finally {
        setUploadingImage(false);
      }
    },
    [companyId],
  );

  return {
    pastedImage,
    pastedFile,
    uploadingImage,
    fileInputRef,
    handlePaste,
    handleFileSelect,
    removePastedImage,
    removePastedFile,
    uploadImageToSupabase,
  };
}
