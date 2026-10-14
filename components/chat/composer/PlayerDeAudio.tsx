'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Play } from 'lucide-react';

/**
 * SPEC-132-A · A1 — a bolha de voz: tocar/pausar, a barra e o tempo, com os tokens do tema (claro e escuro).
 * Substitui, no chat, o player antigo de gradiente roxo. ⚠️ Áudio WebM gravado no Chrome chega sem duração
 * (`Infinity`) até tocar: então usa-se a duração que a gravação mediu, quando a tela a conhece.
 */
function formatar(segundos: number): string {
  if (!Number.isFinite(segundos) || segundos < 0) return '0:00';
  const m = Math.floor(segundos / 60);
  const s = Math.floor(segundos % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function PlayerDeAudio({
  src,
  duracaoConhecida,
  transcricao,
}: {
  src: string;
  duracaoConhecida?: number;
  transcricao?: string;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [tocando, setTocando] = useState(false);
  const [atual, setAtual] = useState(0);
  const [duracao, setDuracao] = useState(duracaoConhecida ?? 0);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    const aoCarregar = () => {
      if (Number.isFinite(a.duration) && a.duration > 0) setDuracao(a.duration);
    };
    const aoTocar = () => {
      setAtual(a.currentTime);
      if (Number.isFinite(a.duration) && a.duration > 0) setDuracao(a.duration);
    };
    const aoAcabar = () => {
      setTocando(false);
      setAtual(0);
    };
    a.addEventListener('loadedmetadata', aoCarregar);
    a.addEventListener('timeupdate', aoTocar);
    a.addEventListener('ended', aoAcabar);
    const aoPausar = () => setTocando(false);
    a.addEventListener('pause', aoPausar);
    return () => {
      a.removeEventListener('loadedmetadata', aoCarregar);
      a.removeEventListener('timeupdate', aoTocar);
      a.removeEventListener('ended', aoAcabar);
      a.removeEventListener('pause', aoPausar);
    };
  }, []);

  const alternar = () => {
    const a = audioRef.current;
    if (!a) return;
    if (tocando) {
      a.pause();
      setTocando(false);
    } else {
      void a.play().then(
        () => setTocando(true),
        () => setTocando(false),
      );
    }
  };

  const progresso = duracao > 0 ? Math.min(100, (atual / duracao) * 100) : 0;

  return (
    <div className="flex w-64 max-w-full flex-col gap-1.5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={alternar}
          aria-label={tocando ? 'Pausar o áudio' : 'Ouvir o áudio'}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity hover:opacity-90"
        >
          {tocando ? (
            <Pause className="h-5 w-5" fill="currentColor" aria-hidden="true" />
          ) : (
            <Play className="ml-0.5 h-5 w-5" fill="currentColor" aria-hidden="true" />
          )}
        </button>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="h-1.5 overflow-hidden rounded-full bg-foreground/20">
            <div className="h-full rounded-full bg-primary transition-[width] duration-150" style={{ width: `${progresso}%` }} />
          </div>
          <div className="flex justify-between font-mono text-[11px] leading-none text-muted-foreground">
            <span>{formatar(atual)}</span>
            <span>{duracao > 0 ? formatar(duracao) : ''}</span>
          </div>
        </div>
        <audio ref={audioRef} src={src} preload="metadata" />
      </div>
      {transcricao && <p className="text-sm leading-relaxed text-foreground-2">{transcricao}</p>}
    </div>
  );
}

export default PlayerDeAudio;
