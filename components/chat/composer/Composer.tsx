'use client';

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { ArrowUp, Brain, Globe, Loader2, Mic, Plus, Square, Zap } from 'lucide-react';
import { toast } from 'sonner';

import { cn } from '@/lib/utils';

import { FichaDeAnexo } from './FichaDeAnexo';
import { FolhaDoMais } from './FolhaDoMais';
import { GravadorDeAudio } from './GravadorDeAudio';
import { aparelhoDeToque, deveEnviarNoEnter, teclaQueEscreve } from './teclado';
import { ACEITA_ARQUIVOS, ACEITA_FOTOS, MAX_ARQUIVOS, type AnexoEnviado, type OpcoesDoEnvio } from './tipos';
import { useAnexos } from './useAnexos';
import { rotuloDoEsforco, useEsforco } from './useEsforco';

/**
 * SPEC-132-A · A1 — O COMPOSER. Um só, que não remonta (D-132A-01).
 *
 * 📊 BLOCO 0 (14/10): a caixa antiga tinha textarea de 60–200 px a 14 px (o iPhone dá zoom abaixo de 16 px), uma
 * barra de ícones embaixo, um brilho que seguia o mouse e nenhum foco — o corretor digitava e nada aparecia. Esta é
 * uma linha de 44 px: [+] · o campo (16 px, cresce até 6 linhas) · microfone quando vazio, ENVIAR quando há texto ou
 * anexo, PARAR enquanto responde. Referência: `multimodal-input.tsx` do vercel/ai-chatbot (SPEC §8.1).
 */
export type StatusDoTurnoNoComposer = 'idle' | 'submitting' | 'streaming' | 'stopped' | 'complete' | 'failed';

export interface ComposerProps {
  /** envia o turno. `anexos` já subiram (`{bucket, path, nome, mime, bytes}` + o que a bolha usa) */
  onSendMessage: (texto: string, anexos?: AnexoEnviado[], opcoes?: OpcoesDoEnvio) => unknown;
  onStop?: () => void;
  turnStatus?: StatusDoTurnoNoComposer;
  /**
   * SPEC-095 BLOCO E — o texto com que o campo NASCE (`?pergunta=`). Semeado no inicializador do `useState`, nunca
   * por efeito: um efeito rodaria depois de o corretor já poder ter digitado, e apagaria o que ele escreveu.
   */
  initialText?: string;
  /** muda quando a conversa muda (nova ou outra): o cursor volta para a caixa */
  focoKey?: string;
  podePesquisarNaWeb?: boolean;
  pesquisaNaWeb?: boolean;
  onAlternarPesquisaNaWeb?: () => void;
}

export interface ComposerHandle {
  /** anexa arquivos soltos sobre a conversa (arrastar e soltar da página) */
  adicionarArquivos: (arquivos: File[]) => void;
  focar: () => void;
}

/** 6 linhas de 24 px + o respiro vertical do campo. Depois disso, o campo rola. */
const ALTURA_MAXIMA = 6 * 24 + 20;
const ALTURA_MINIMA = 44;

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  {
    onSendMessage,
    onStop,
    turnStatus = 'idle',
    initialText,
    focoKey,
    podePesquisarNaWeb = false,
    pesquisaNaWeb = false,
    onAlternarPesquisaNaWeb,
  },
  ref,
) {
  const [message, setMessage] = useState(initialText ?? '');
  const [menuAberto, setMenuAberto] = useState(false);
  const [gravando, setGravando] = useState(false);
  /** Enter apertado com arquivo ainda subindo: envia sozinho quando todos terminarem */
  const [envioPendente, setEnvioPendente] = useState(false);
  const [esforco, setEsforco] = useEsforco();

  const campoRef = useRef<HTMLTextAreaElement>(null);
  const maisRef = useRef<HTMLButtonElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fotosRef = useRef<HTMLInputElement>(null);
  const arquivosRef = useRef<HTMLInputElement>(null);
  const textoRef = useRef(message);
  textoRef.current = message;

  const turnoCorrendo = turnStatus === 'submitting' || turnStatus === 'streaming';

  const anexos = useAnexos({
    aoRecusarQuantidade: (cabem) =>
      toast.error(
        cabem === 0
          ? `Dá para mandar até ${MAX_ARQUIVOS} arquivos por mensagem.`
          : `Dá para mandar até ${MAX_ARQUIVOS} arquivos por mensagem — anexei só ${cabem}.`,
      ),
  });

  const focar = useCallback(() => {
    const campo = campoRef.current;
    if (!campo) return;
    try {
      campo.focus({ preventScroll: true });
      const fim = campo.value.length;
      campo.setSelectionRange(fim, fim);
    } catch {
      /* campo fora da tela */
    }
  }, []);

  const ajustarAltura = useCallback(() => {
    const campo = campoRef.current;
    if (!campo) return;
    campo.style.height = 'auto';
    campo.style.height = `${Math.max(ALTURA_MINIMA, Math.min(campo.scrollHeight, ALTURA_MAXIMA))}px`;
    campo.style.overflowY = campo.scrollHeight > ALTURA_MAXIMA ? 'auto' : 'hidden';
  }, []);

  useImperativeHandle(ref, () => ({ adicionarArquivos: (a: File[]) => anexos.adicionar(a), focar }), [anexos.adicionar, focar]);

  // 🔴 B10 — o cursor já está na caixa ao abrir o chat e ao trocar/criar conversa.
  useEffect(() => {
    focar();
  }, [focoKey, focar]);

  // ...e quando a resposta termina, no notebook (no celular isso reabriria o teclado sozinho — §4 "Foco").
  const statusAnteriorRef = useRef(turnStatus);
  useEffect(() => {
    const antes = statusAnteriorRef.current;
    statusAnteriorRef.current = turnStatus;
    const corria = antes === 'submitting' || antes === 'streaming';
    if (corria && !turnoCorrendo && !aparelhoDeToque()) focar();
  }, [turnStatus, turnoCorrendo, focar]);

  // o texto semeado (`?pergunta=`) já nasce com a altura certa
  useEffect(() => {
    ajustarAltura();
  }, [ajustarAltura]);

  // Esc para a resposta. O ouvinte é da JANELA: o foco pode estar em qualquer lugar enquanto ela chega.
  useEffect(() => {
    if (!turnoCorrendo || !onStop) return;
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onStop();
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [turnoCorrendo, onStop]);

  // Começou a digitar fora da caixa (notebook)? A letra vai para a caixa — "digitei e nada apareceu" não acontece.
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (!teclaQueEscreve(e)) return;
      const ativo = document.activeElement as HTMLElement | null;
      if (ativo && ativo !== document.body) {
        const tag = ativo.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || ativo.isContentEditable) return;
        if (ativo.closest('[role="dialog"]')) return;
      }
      focar();
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [focar]);

  const temConteudo = message.trim().length > 0 || anexos.fichas.length > 0;

  const enviarAgora = useCallback(() => {
    const texto = textoRef.current.trim();
    const prontos = anexos.prontos;
    if (!texto && prontos.length === 0) return false;
    void onSendMessage(texto, prontos, { esforco });
    setMessage('');
    textoRef.current = '';
    anexos.limpar();
    setEnvioPendente(false);
    requestAnimationFrame(() => {
      ajustarAltura();
      if (!aparelhoDeToque()) focar();
    });
    return true;
  }, [anexos, onSendMessage, esforco, ajustarAltura, focar]);

  const enviar = useCallback(() => {
    if (turnoCorrendo) return;
    if (anexos.subindo) {
      setEnvioPendente(true); // sai sozinho quando o último arquivo subir
      return;
    }
    // um arquivo com erro nunca some calado: o corretor tira (no ✕) ou anexa de novo, e aí envia
    if (anexos.comErro) {
      toast.error('Um arquivo não subiu. Tire-o (no ✕) ou anexe de novo, e envie.');
      return;
    }
    enviarAgora();
  }, [turnoCorrendo, anexos.subindo, anexos.comErro, enviarAgora]);

  // o envio pendente sai quando a fila esvazia — ou é cancelado se algum arquivo falhou (o corretor decide)
  useEffect(() => {
    if (!envioPendente || anexos.subindo) return;
    if (anexos.comErro) {
      setEnvioPendente(false);
      toast.error('Um arquivo não subiu. Tire-o (no ✕) ou anexe de novo, e envie.');
      return;
    }
    if (!turnoCorrendo) enviarAgora();
  }, [envioPendente, anexos.subindo, anexos.comErro, turnoCorrendo, enviarAgora]);

  const aoTeclar = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      deveEnviarNoEnter({
        key: e.key,
        shiftKey: e.shiftKey,
        isComposing: e.nativeEvent.isComposing,
        toque: aparelhoDeToque(),
      })
    ) {
      e.preventDefault();
      enviar();
    }
  };

  const aoColar = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const arquivos = Array.from(e.clipboardData?.files ?? []);
    if (arquivos.length === 0) return;
    // Copiar células do Excel/Word põe TEXTO e uma IMAGEM na área de transferência: o texto vence (é o que o
    // corretor quis colar). Só um print/arquivo sem texto vira anexo.
    if ((e.clipboardData?.getData('text/plain') ?? '').trim()) return;
    e.preventDefault();
    anexos.adicionar(arquivos);
  };

  const aoEscolher = (e: React.ChangeEvent<HTMLInputElement>) => {
    const arquivos = Array.from(e.target.files ?? []);
    e.target.value = ''; // escolher o MESMO arquivo de novo também dispara
    if (arquivos.length) anexos.adicionar(arquivos);
    focar();
  };

  const fecharMenu = useCallback(() => {
    setMenuAberto(false);
    maisRef.current?.focus({ preventScroll: true });
  }, []);

  const aoConcluirAudio = (arquivo: File, duracaoSegundos: number) => {
    setGravando(false);
    if (duracaoSegundos < 0.6) {
      toast('Áudio curto demais — segure um pouco mais.');
      return;
    }
    anexos.adicionar([arquivo], { duracaoSegundos });
    setEnvioPendente(true); // o áudio vira mensagem assim que subir
  };

  const IconeDoEsforco = esforco === 'rapido' ? Zap : Brain;

  const botaoDaDireita = turnoCorrendo ? (
    <button
      type="button"
      onClick={onStop}
      aria-label="Parar a resposta"
      title="Parar (Esc)"
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-foreground text-background transition-opacity hover:opacity-90"
    >
      <Square className="h-4 w-4" fill="currentColor" aria-hidden="true" />
    </button>
  ) : temConteudo ? (
    <button
      type="button"
      onClick={enviar}
      aria-label={envioPendente ? 'Enviando quando os arquivos subirem' : 'Enviar'}
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity hover:opacity-90"
    >
      {envioPendente ? (
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
      ) : (
        <ArrowUp className="h-5 w-5" strokeWidth={2.25} aria-hidden="true" />
      )}
    </button>
  ) : (
    <button
      type="button"
      onClick={() => {
        setMenuAberto(false);
        setGravando(true);
      }}
      aria-label="Gravar áudio"
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
    >
      <Mic className="h-5 w-5" aria-hidden="true" />
    </button>
  );

  return (
    <div className="relative mx-auto w-full max-w-[760px]" data-composer="">
      <div
        className={cn(
          'relative rounded-[24px] border border-border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.06),0_10px_28px_-18px_rgba(0,0,0,0.45)] transition-colors',
          'focus-within:border-foreground/25',
        )}
      >
        {anexos.fichas.length > 0 && (
          <div className="flex gap-2 overflow-x-auto px-3 pb-1 pt-3" aria-label="Anexos">
            {anexos.fichas.map((f) => (
              <FichaDeAnexo
                key={f.id}
                nome={f.nome}
                mime={f.mime}
                bytes={f.bytes}
                imagemUrl={f.previewUrl}
                estado={f.estado}
                progresso={f.progresso}
                motivo={f.motivo}
                onRemover={() => anexos.remover(f.id)}
              />
            ))}
          </div>
        )}

        {gravando ? (
          <GravadorDeAudio
            onConcluir={aoConcluirAudio}
            onCancelar={() => {
              setGravando(false);
              requestAnimationFrame(focar);
            }}
            onFalhar={(mensagem) => {
              setGravando(false);
              toast.error(mensagem);
            }}
          />
        ) : (
          <div className="flex items-end gap-1 p-1.5">
            <button
              ref={maisRef}
              type="button"
              onClick={() => setMenuAberto((v) => !v)}
              aria-label="Adicionar fotos, arquivos e opções"
              aria-haspopup="dialog"
              aria-expanded={menuAberto}
              className={cn(
                'flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-foreground transition-colors hover:bg-surface-2',
                menuAberto && 'bg-surface-2',
              )}
            >
              <Plus className={cn('h-[22px] w-[22px] transition-transform duration-200', menuAberto && 'rotate-45')} aria-hidden="true" />
            </button>

            {(esforco !== 'equilibrado' || (podePesquisarNaWeb && pesquisaNaWeb)) && (
              <div className="flex h-11 shrink-0 items-center gap-1">
                {esforco !== 'equilibrado' && (
                  <button
                    type="button"
                    onClick={() => setMenuAberto(true)}
                    aria-label={`Esforço: ${rotuloDoEsforco(esforco)}. Trocar`}
                    className="inline-flex h-8 items-center gap-1 rounded-full bg-primary/10 px-2.5 text-[13px] font-medium text-primary transition-colors hover:bg-primary/20"
                  >
                    <IconeDoEsforco className="h-3.5 w-3.5" aria-hidden="true" />
                    {rotuloDoEsforco(esforco)}
                  </button>
                )}
                {podePesquisarNaWeb && pesquisaNaWeb && (
                  <button
                    type="button"
                    onClick={onAlternarPesquisaNaWeb}
                    aria-label="Pesquisa na web ligada. Desligar"
                    className="inline-flex h-8 items-center gap-1 rounded-full bg-primary/10 px-2.5 text-[13px] font-medium text-primary transition-colors hover:bg-primary/20"
                  >
                    <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                    Web
                  </button>
                )}
              </div>
            )}

            <textarea
              ref={campoRef}
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                ajustarAltura();
              }}
              onKeyDown={aoTeclar}
              onPaste={aoColar}
              placeholder="Peça ao AutoBrokers"
              aria-label="Peça ao AutoBrokers"
              rows={1}
              autoFocus
              autoComplete="off"
              spellCheck
              className={cn(
                // 🔴 16 px: abaixo disso o iPhone dá zoom ao tocar no campo (B9)
                'block min-h-11 min-w-0 flex-1 resize-none bg-transparent px-1.5 py-2.5 text-base leading-6 text-foreground',
                'placeholder:text-muted-foreground focus:outline-none',
              )}
              style={{ height: ALTURA_MINIMA, maxHeight: ALTURA_MAXIMA, overflowY: 'hidden' }}
            />

            {botaoDaDireita}
          </div>
        )}
      </div>

      <FolhaDoMais
        aberto={menuAberto}
        onFechar={fecharMenu}
        onCamera={() => cameraRef.current?.click()}
        onFotos={() => fotosRef.current?.click()}
        onArquivos={() => arquivosRef.current?.click()}
        esforco={esforco}
        onEsforco={setEsforco}
        podePesquisarNaWeb={podePesquisarNaWeb}
        pesquisaNaWeb={pesquisaNaWeb}
        onAlternarPesquisaNaWeb={onAlternarPesquisaNaWeb}
      />

      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={aoEscolher} tabIndex={-1} aria-hidden="true" />
      <input ref={fotosRef} type="file" accept={ACEITA_FOTOS} multiple className="hidden" onChange={aoEscolher} tabIndex={-1} aria-hidden="true" />
      <input ref={arquivosRef} type="file" accept={ACEITA_ARQUIVOS} multiple className="hidden" onChange={aoEscolher} tabIndex={-1} aria-hidden="true" />
    </div>
  );
});

export default Composer;
