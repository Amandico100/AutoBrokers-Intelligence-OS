'use client';

import { useState } from 'react';
import { AnimatedAIChat } from '../ui/animated-ai-chat';
import { ImagePreview } from './ImagePreview';
import { AudioPreview } from './AudioPreview';
import { StatusIndicator } from './StatusIndicator';
import { useImageUpload } from './hooks/useImageUpload';
import { useAudioRecorder } from './hooks/useAudioRecorder';

interface InputAreaProps {
  onSendMessage?: (message: string, imageUrl?: string, fileUrl?: string, fileName?: string) => void;
  onSendVoice?: (audioBase64: string, audioBlob: Blob) => void;
  disabled?: boolean;
  allowWebSearch?: boolean;
  onToggleWebSearch?: () => void;
  showWebSearch?: boolean;
  companyId?: string;
  agents?: { id: string; name: string }[];
  selectedAgentId?: string;
  onAgentChange?: (agentId: string) => void;
  showAgentSelector?: boolean;
}

export default function InputArea({
  onSendMessage,
  onSendVoice,
  disabled,
  allowWebSearch = false,
  onToggleWebSearch,
  showWebSearch = true,
  companyId,
  agents = [],
  selectedAgentId = '',
  onAgentChange,
  showAgentSelector = true,
}: InputAreaProps) {
  const [message, setMessage] = useState('');

  const {
    pastedImage,
    pastedFile,
    uploadingImage,
    fileInputRef,
    handlePaste,
    handleFileSelect,
    removePastedImage,
    removePastedFile,
    uploadImageToSupabase,
  } = useImageUpload({ companyId });

  const {
    pendingAudio,
    isPlaying,
    audioRef,
    isRecording,
    isProcessing,
    toggleRecording,
    handleCancelAudio,
    handleSendAudio,
    toggleAudioPreview,
    setIsPlaying,
  } = useAudioRecorder();

  const handleSend = async () => {
    let imageUrl: string | undefined = undefined;
    let fileUrl: string | undefined = undefined;
    let fileName: string | undefined = undefined;

    if (pastedImage) {
      imageUrl = (await uploadImageToSupabase(pastedImage.file)) || undefined;
      removePastedImage();
    }
    if (pastedFile) {
      // F1: mesmo upload (bucket chat-media); o backend extrai o texto.
      fileUrl = (await uploadImageToSupabase(pastedFile.file)) || undefined;
      fileName = pastedFile.name;
      removePastedFile();
    }

    if ((message.trim() || imageUrl || fileUrl) && onSendMessage) {
      onSendMessage(message.trim() || (fileUrl ? `📄 ${fileName}` : '[Imagem]'), imageUrl, fileUrl, fileName);
      setMessage('');
    }
  };

  const placeholder = isRecording
    ? 'Gravando...'
    : isProcessing
      ? 'Processando...'
      : 'Digite sua mensagem...';

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-6">
      {pastedImage && (
        <ImagePreview
          imageUrl={pastedImage.url}
          uploading={uploadingImage}
          onRemove={removePastedImage}
        />
      )}

      {pastedFile && (
        <div className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <span className="truncate text-sm text-foreground">📄 {pastedFile.name}</span>
          <button
            onClick={removePastedFile}
            className="shrink-0 text-xs text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Remover documento"
          >
            Remover
          </button>
        </div>
      )}

      {pendingAudio ? (
        <AudioPreview
          audioUrl={pendingAudio.url}
          isPlaying={isPlaying}
          audioRef={audioRef}
          onCancel={handleCancelAudio}
          onSend={() => onSendVoice && handleSendAudio(onSendVoice)}
          onTogglePlay={toggleAudioPreview}
          onEnded={() => setIsPlaying(false)}
        />
      ) : (
        <AnimatedAIChat
          value={message}
          onChange={setMessage}
          onSend={handleSend}
          onVoiceRecord={toggleRecording}
          onPaste={handlePaste}
          isRecording={isRecording}
          isTyping={disabled || uploadingImage}
          placeholder={placeholder}
          disabled={disabled || isProcessing || uploadingImage}
          showWebSearch={showWebSearch}
          allowWebSearch={allowWebSearch}
          onToggleWebSearch={onToggleWebSearch}
          onFileSelect={() => fileInputRef.current?.click()}
          agents={agents}
          selectedAgentId={selectedAgentId}
          onAgentChange={onAgentChange}
          showAgentSelector={showAgentSelector}
        />
      )}

      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept="image/*,.pdf,.docx,.pptx,.xlsx,.txt,.csv,.md"
        onChange={handleFileSelect}
      />

      <StatusIndicator
        isRecording={isRecording}
        isProcessing={isProcessing}
        uploadingImage={uploadingImage}
      />
    </div>
  );
}
