'use client';

import { AlertCircle, FileAudio, FileSpreadsheet, FileText, ImageIcon, Loader2, X } from 'lucide-react';

import { cn } from '@/lib/utils';

import { ehAudio, ehImagem, extensaoDe, tamanhoLegivel } from './anexos';
import type { EstadoDaFicha } from './useAnexos';

/**
 * SPEC-132-A · A1 — a ficha de um anexo. A MESMA peça no composer (com progresso e ✕) e na bolha do corretor
 * (só leitura). Foto = miniatura; documento = ícone + nome + tamanho; erro = borda e frase em vermelho, com o
 * motivo que a rota devolveu ("O arquivo passa de 20 MB.").
 */
export interface FichaDeAnexoProps {
  nome: string;
  mime: string;
  bytes: number;
  /** a miniatura (foto) — local enquanto sobe, do proxy depois */
  imagemUrl?: string | null;
  /** link para abrir o arquivo (na bolha) */
  href?: string | null;
  estado?: EstadoDaFicha;
  progresso?: number | null;
  motivo?: string;
  onRemover?: () => void;
}

function IconeDoArquivo({ nome, mime, className }: { nome: string; mime: string; className?: string }) {
  const ext = extensaoDe(nome);
  if (ehAudio(mime)) return <FileAudio className={className} aria-hidden="true" />;
  if (ehImagem(mime)) return <ImageIcon className={className} aria-hidden="true" />;
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet className={className} aria-hidden="true" />;
  return <FileText className={className} aria-hidden="true" />;
}

function rotuloDoTipo(nome: string, mime: string): string {
  const ext = extensaoDe(nome);
  if (ehAudio(mime)) return 'Áudio';
  if (ext) return ext.toUpperCase();
  return 'Arquivo';
}

export function FichaDeAnexo({
  nome,
  mime,
  bytes,
  imagemUrl,
  href,
  estado = 'pronto',
  progresso = null,
  motivo,
  onRemover,
}: FichaDeAnexoProps) {
  const comErro = estado === 'erro';
  const subindo = estado === 'subindo';
  const miniatura = ehImagem(mime) && imagemUrl && !comErro;
  const descricao = comErro
    ? `${nome}: ${motivo || 'não foi possível anexar'}`
    : subindo
      ? `${nome}: enviando`
      : nome;

  const botaoTirar = onRemover ? (
    <button
      type="button"
      onClick={onRemover}
      aria-label={`Tirar ${nome}`}
      className={cn(
        // 24 px de desenho, 44 px de toque (o ::before estende a área)
        "absolute -right-1.5 -top-1.5 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border",
        "bg-popover text-foreground shadow-sm transition-colors hover:bg-surface-2",
        "before:absolute before:-inset-2.5 before:content-['']",
      )}
    >
      <X className="h-3.5 w-3.5" aria-hidden="true" />
    </button>
  ) : null;

  const barra =
    subindo && (
      <span className="absolute inset-x-2 bottom-1.5 h-1 overflow-hidden rounded-full bg-foreground/20" aria-hidden="true">
        {progresso == null ? (
          <span className="block h-full w-1/3 animate-pulse rounded-full bg-primary" />
        ) : (
          <span
            className="block h-full rounded-full bg-primary transition-[width] duration-200"
            style={{ width: `${Math.round(Math.max(0.04, progresso) * 100)}%` }}
          />
        )}
      </span>
    );

  if (miniatura) {
    const img = (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={imagemUrl as string} alt={nome} className="h-full w-full object-cover" draggable={false} />
    );
    return (
      <div className="relative shrink-0" title={nome}>
        <div
          className={cn(
            'relative h-16 w-16 overflow-hidden rounded-2xl border border-border bg-surface-2',
            subindo && 'opacity-80',
          )}
        >
          {href ? (
            <a href={href} target="_blank" rel="noopener noreferrer" aria-label={`Abrir ${nome}`} className="block h-full w-full">
              {img}
            </a>
          ) : (
            img
          )}
          {subindo && (
            <span className="absolute inset-0 flex items-center justify-center bg-background/30">
              <Loader2 className="h-5 w-5 animate-spin text-foreground" aria-hidden="true" />
            </span>
          )}
          {barra}
        </div>
        <span className="sr-only" aria-live="polite">{descricao}</span>
        {botaoTirar}
      </div>
    );
  }

  const conteudo = (
    <>
      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
          comErro ? 'bg-danger/10 text-danger' : 'bg-primary/10 text-primary',
        )}
      >
        {comErro ? (
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
        ) : subindo ? (
          <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
        ) : (
          <IconeDoArquivo nome={nome} mime={mime} className="h-5 w-5" />
        )}
      </span>
      <span className="min-w-0 flex-1 text-left">
        <span className="block truncate text-sm font-medium leading-5 text-foreground">{nome}</span>
        {comErro ? (
          <span role="alert" className="block truncate text-xs leading-4 text-danger">
            {motivo || 'Não foi possível anexar.'}
          </span>
        ) : (
          <span className="block truncate text-xs leading-4 text-muted-foreground">
            {[rotuloDoTipo(nome, mime), tamanhoLegivel(bytes)].filter(Boolean).join(' · ')}
          </span>
        )}
      </span>
    </>
  );

  return (
    <div className="relative shrink-0" title={comErro ? motivo : nome}>
      {href && !comErro ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="relative flex h-16 w-56 max-w-[70vw] items-center gap-3 rounded-2xl border border-border bg-surface-2 px-3 transition-colors hover:border-primary/40"
        >
          {conteudo}
        </a>
      ) : (
        <div
          className={cn(
            'relative flex h-16 w-56 max-w-[70vw] items-center gap-3 rounded-2xl border px-3',
            comErro ? 'border-danger/60 bg-danger/5' : 'border-border bg-surface-2',
          )}
        >
          {conteudo}
          {barra}
        </div>
      )}
      {botaoTirar}
    </div>
  );
}

export default FichaDeAnexo;
