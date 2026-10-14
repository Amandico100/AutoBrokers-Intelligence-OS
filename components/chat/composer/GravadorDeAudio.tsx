'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, X } from 'lucide-react';

/**
 * SPEC-132-A · A1 — gravar áudio no chat. Toque no microfone → grava (ondas + cronômetro + ✕ cancelar + ✓ enviar).
 * O áudio vira um ANEXO (`audio/*`) do mesmo `POST /api/chat/stream` (D-132A-06: o chat sai do `/api/n8n`).
 *
 * O formato é o que o navegador grava bem: WebM/Opus no Chrome, Edge e Firefox; MP4/AAC no Safari (iPhone).
 * O microfone é solto (`track.stop()`) ao terminar, ao cancelar e ao sair da tela — a luz do microfone apaga.
 */
const FORMATOS: { mime: string; ext: string; tipo: string }[] = [
  { mime: 'audio/webm;codecs=opus', ext: 'webm', tipo: 'audio/webm' },
  { mime: 'audio/webm', ext: 'webm', tipo: 'audio/webm' },
  { mime: 'audio/mp4;codecs=mp4a.40.2', ext: 'm4a', tipo: 'audio/mp4' },
  { mime: 'audio/mp4', ext: 'm4a', tipo: 'audio/mp4' },
  { mime: 'audio/ogg;codecs=opus', ext: 'ogg', tipo: 'audio/ogg' },
];

/** Dez minutos: cabe com folga nos 20 MB (Opus ≈ 32 kbit/s) e corta o áudio esquecido ligado. */
const MAXIMO_SEGUNDOS = 600;
const BARRAS = 32;

export function escolherFormato(suporta: (mime: string) => boolean): { mime: string; ext: string; tipo: string } | null {
  for (const f of FORMATOS) {
    try {
      if (suporta(f.mime)) return f;
    } catch {
      /* segue */
    }
  }
  return null;
}

function relogio(segundos: number): string {
  const m = Math.floor(segundos / 60);
  const s = Math.floor(segundos % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export interface GravadorDeAudioProps {
  /** o áudio pronto, como arquivo, e quanto durou */
  onConcluir: (arquivo: File, duracaoSegundos: number) => void;
  onCancelar: () => void;
  /** o microfone não abriu (permissão negada, sem microfone, navegador sem suporte) */
  onFalhar: (mensagem: string) => void;
}

export function GravadorDeAudio({ onConcluir, onCancelar, onFalhar }: GravadorDeAudioProps) {
  const [segundos, setSegundos] = useState(0);
  const [niveis, setNiveis] = useState<number[]>(() => Array(BARRAS).fill(0.08));
  const [pronto, setPronto] = useState(false);

  const gravadorRef = useRef<MediaRecorder | null>(null);
  const fluxoRef = useRef<MediaStream | null>(null);
  const contextoRef = useRef<AudioContext | null>(null);
  const pedacosRef = useRef<Blob[]>([]);
  const quadroRef = useRef<number | null>(null);
  const inicioRef = useRef(0);
  const destinoRef = useRef<'enviar' | 'cancelar' | null>(null);
  const formatoRef = useRef<{ ext: string; tipo: string }>({ ext: 'webm', tipo: 'audio/webm' });
  const callbacks = useRef({ onConcluir, onCancelar, onFalhar });
  callbacks.current = { onConcluir, onCancelar, onFalhar };

  const soltarMicrofone = useCallback(() => {
    if (quadroRef.current != null) cancelAnimationFrame(quadroRef.current);
    quadroRef.current = null;
    fluxoRef.current?.getTracks().forEach((t) => t.stop());
    fluxoRef.current = null;
    const ctx = contextoRef.current;
    contextoRef.current = null;
    if (ctx && ctx.state !== 'closed') void ctx.close().catch(() => undefined);
  }, []);

  const terminar = useCallback((destino: 'enviar' | 'cancelar') => {
    if (destinoRef.current) return;
    destinoRef.current = destino;
    const g = gravadorRef.current;
    if (g && g.state !== 'inactive') {
      g.stop(); // o `onstop` decide o que fazer com os pedaços
    } else {
      soltarMicrofone();
      if (destino === 'cancelar') callbacks.current.onCancelar();
    }
  }, [soltarMicrofone]);

  useEffect(() => {
    let vivo = true;
    destinoRef.current = null;
    inicioRef.current = 0;
    (async () => {
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        callbacks.current.onFalhar('Este navegador não grava áudio. Tente pelo Chrome ou pelo Safari atualizado.');
        return;
      }
      let fluxo: MediaStream;
      try {
        fluxo = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      } catch {
        callbacks.current.onFalhar('Não consegui usar o microfone. Libere o acesso nas permissões do navegador.');
        return;
      }
      if (!vivo) {
        fluxo.getTracks().forEach((t) => t.stop());
        return;
      }
      fluxoRef.current = fluxo;

      const formato = escolherFormato((m) => MediaRecorder.isTypeSupported(m));
      let gravador: MediaRecorder;
      try {
        gravador = formato ? new MediaRecorder(fluxo, { mimeType: formato.mime, audioBitsPerSecond: 48000 }) : new MediaRecorder(fluxo);
      } catch {
        gravador = new MediaRecorder(fluxo);
      }
      const tipoReal = (gravador.mimeType || formato?.tipo || 'audio/webm').split(';')[0];
      formatoRef.current = { tipo: tipoReal, ext: tipoReal === 'audio/mp4' ? 'm4a' : tipoReal === 'audio/ogg' ? 'ogg' : 'webm' };
      gravadorRef.current = gravador;
      pedacosRef.current = [];
      gravador.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) pedacosRef.current.push(ev.data);
      };
      gravador.onstop = () => {
        const duracao = Math.max(0, (performance.now() - inicioRef.current) / 1000);
        const destino = destinoRef.current;
        soltarMicrofone();
        if (destino !== 'enviar' || pedacosRef.current.length === 0) {
          callbacks.current.onCancelar();
          return;
        }
        const { tipo, ext } = formatoRef.current;
        const blob = new Blob(pedacosRef.current, { type: tipo });
        const quando = new Date();
        const nome = `audio-${quando.getFullYear()}${String(quando.getMonth() + 1).padStart(2, '0')}${String(quando.getDate()).padStart(2, '0')}-${String(quando.getHours()).padStart(2, '0')}${String(quando.getMinutes()).padStart(2, '0')}${String(quando.getSeconds()).padStart(2, '0')}.${ext}`;
        callbacks.current.onConcluir(new File([blob], nome, { type: tipo }), duracao);
      };

      // as ondas: o nível do microfone, amostrado a cada quadro e empurrado ~12 vezes por segundo
      try {
        const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (Ctx) {
          const ctx = new Ctx();
          contextoRef.current = ctx;
          const analisador = ctx.createAnalyser();
          analisador.fftSize = 512;
          ctx.createMediaStreamSource(fluxo).connect(analisador);
          const dados = new Uint8Array(analisador.fftSize);
          let ultimoEmpurrao = 0;
          const quadro = (agora: number) => {
            analisador.getByteTimeDomainData(dados);
            let soma = 0;
            for (let i = 0; i < dados.length; i++) {
              const v = (dados[i] - 128) / 128;
              soma += v * v;
            }
            const nivel = Math.min(1, Math.sqrt(soma / dados.length) * 3.2);
            if (agora - ultimoEmpurrao > 80) {
              ultimoEmpurrao = agora;
              setNiveis((n) => [...n.slice(1), Math.max(0.08, nivel)]);
              const s = (performance.now() - inicioRef.current) / 1000;
              setSegundos(Math.floor(s));
              if (s >= MAXIMO_SEGUNDOS) terminar('enviar');
            }
            quadroRef.current = requestAnimationFrame(quadro);
          };
          quadroRef.current = requestAnimationFrame(quadro);
        }
      } catch {
        /* sem ondas: o cronômetro continua pelo intervalo abaixo */
      }

      gravador.start(250);
      inicioRef.current = performance.now();
      setPronto(true);
    })();

    // o cronômetro também anda sem o AudioContext (Safari antigo)
    const relogioDoGravador = window.setInterval(() => {
      if (!inicioRef.current) return;
      const s = (performance.now() - inicioRef.current) / 1000;
      setSegundos(Math.floor(s));
      if (s >= MAXIMO_SEGUNDOS) terminar('enviar');
    }, 500);

    return () => {
      vivo = false;
      window.clearInterval(relogioDoGravador);
      const g = gravadorRef.current;
      if (g && g.state !== 'inactive') {
        destinoRef.current = 'cancelar';
        try {
          g.stop();
        } catch {
          /* nada */
        }
      }
      soltarMicrofone();
    };
  }, [soltarMicrofone, terminar]);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') terminar('cancelar');
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [terminar]);

  return (
    <div className="flex min-h-11 items-center gap-2 p-1.5" role="group" aria-label="Gravando áudio">
      <button
        type="button"
        onClick={() => terminar('cancelar')}
        aria-label="Cancelar a gravação"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
      >
        <X className="h-5 w-5" aria-hidden="true" />
      </button>

      <span className="flex shrink-0 items-center gap-2 pl-1">
        <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-danger opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-danger" />
        </span>
        <span className="font-mono text-sm tabular-nums text-foreground" aria-live="off">
          {relogio(segundos)}
        </span>
      </span>

      <span className="flex h-8 min-w-0 flex-1 items-center justify-center gap-[3px] overflow-hidden px-1" aria-hidden="true">
        {niveis.map((n, i) => (
          <span
            key={i}
            className="w-[3px] shrink-0 rounded-full bg-foreground/60 transition-[height] duration-100"
            style={{ height: `${Math.round(6 + n * 24)}px` }}
          />
        ))}
      </span>

      <button
        type="button"
        onClick={() => terminar('enviar')}
        disabled={!pronto}
        aria-label="Enviar o áudio"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        <Check className="h-5 w-5" aria-hidden="true" />
      </button>
    </div>
  );
}

export default GravadorDeAudio;
