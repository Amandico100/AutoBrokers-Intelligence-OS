'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  bucketDoArquivo,
  ehImagem,
  lerRespostaDoUpload,
  mimeDoArquivo,
  motivoParaRecusar,
  navegadorDesenha,
} from './anexos';
import { MAX_ARQUIVOS, type AnexoEnviado } from './tipos';

/**
 * SPEC-132-A · A1 — a fila de anexos do composer.
 *
 * Cada arquivo sobe ASSIM QUE é escolhido (não no clique de Enviar), em paralelo, com progresso real
 * (XMLHttpRequest — o `fetch` não informa progresso de envio). O modelo é o `multimodal-input` do vercel/ai-chatbot
 * (SPEC §8.1): fichas + fila de upload. O limite (10 arquivos, 20 MB) é avisado ANTES de subir.
 */
export type EstadoDaFicha = 'subindo' | 'pronto' | 'erro';

export interface Ficha {
  id: string;
  nome: string;
  mime: string;
  bytes: number;
  estado: EstadoDaFicha;
  /** 0–1 quando o navegador informa; `null` = indeterminado. */
  progresso: number | null;
  motivo?: string;
  previewUrl?: string;
  duracaoSegundos?: number;
  anexo?: AnexoEnviado;
}

export interface OpcoesDoArquivo {
  duracaoSegundos?: number;
}

function novoId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `f-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

/** O arquivo com o MIME que a rota entende (o navegador às vezes não diz: HEIC, `.md`, `.xls`). */
function comMimeCerto(arquivo: File): File {
  const mime = mimeDoArquivo(arquivo.name, arquivo.type);
  if (mime === arquivo.type) return arquivo;
  try {
    return new File([arquivo], arquivo.name, { type: mime, lastModified: arquivo.lastModified });
  } catch {
    return arquivo;
  }
}

export function useAnexos(opcoes: { aoRecusarQuantidade?: (cabem: number) => void } = {}) {
  const [fichas, setFichas] = useState<Ficha[]>([]);
  const fichasRef = useRef<Ficha[]>([]);
  const envios = useRef(new Map<string, XMLHttpRequest>());
  const aoRecusarRef = useRef(opcoes.aoRecusarQuantidade);
  aoRecusarRef.current = opcoes.aoRecusarQuantidade;

  const atualizar = useCallback((id: string, parcial: Partial<Ficha>) => {
    setFichas((atual) => {
      const nova = atual.map((f) => (f.id === id ? { ...f, ...parcial } : f));
      fichasRef.current = nova;
      return nova;
    });
  }, []);

  const subir = useCallback(
    (id: string, arquivo: File, mime: string, extra: Partial<AnexoEnviado>) => {
      const xhr = new XMLHttpRequest();
      envios.current.set(id, xhr);
      const corpo = new FormData();
      corpo.append('file', arquivo, arquivo.name);
      corpo.append('bucket', bucketDoArquivo(mime));

      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable && ev.total > 0) atualizar(id, { progresso: Math.min(1, ev.loaded / ev.total) });
      };
      xhr.onload = () => {
        envios.current.delete(id);
        let json: unknown = null;
        try {
          json = JSON.parse(xhr.responseText);
        } catch {
          json = null;
        }
        const r = lerRespostaDoUpload(xhr.status, json);
        if (r.ok) {
          atualizar(id, { estado: 'pronto', progresso: 1, anexo: { ...r.anexo, ...extra } });
        } else {
          atualizar(id, { estado: 'erro', progresso: null, motivo: r.motivo });
        }
      };
      xhr.onerror = () => {
        envios.current.delete(id);
        atualizar(id, { estado: 'erro', progresso: null, motivo: 'Sem conexão. Tire o arquivo e anexe de novo.' });
      };
      xhr.open('POST', '/api/upload');
      xhr.send(corpo);
    },
    [atualizar],
  );

  /** Anexa arquivos. Os que passam do limite de 10 nem entram (avisa); os grandes ou estranhos entram já com erro. */
  const adicionar = useCallback(
    (arquivos: File[], extra: OpcoesDoArquivo = {}): string[] => {
      const cabem = Math.max(0, MAX_ARQUIVOS - fichasRef.current.length);
      if (arquivos.length > cabem) aoRecusarRef.current?.(cabem);
      const aceitos = arquivos.slice(0, cabem);
      const novas: Ficha[] = [];
      const paraSubir: { ficha: Ficha; arquivo: File }[] = [];
      for (const original of aceitos) {
        const arquivo = comMimeCerto(original);
        const mime = arquivo.type || mimeDoArquivo(arquivo.name, '');
        const motivo = motivoParaRecusar(arquivo.name, mime, arquivo.size);
        let previewUrl: string | undefined;
        if (!motivo && ehImagem(mime) && navegadorDesenha(mime)) {
          try {
            previewUrl = URL.createObjectURL(arquivo);
          } catch {
            previewUrl = undefined;
          }
        }
        const ficha: Ficha = {
          id: novoId(),
          nome: arquivo.name,
          mime,
          bytes: arquivo.size,
          estado: motivo ? 'erro' : 'subindo',
          progresso: motivo ? null : 0,
          motivo: motivo ?? undefined,
          previewUrl,
          duracaoSegundos: extra.duracaoSegundos,
        };
        novas.push(ficha);
        if (!motivo) paraSubir.push({ ficha, arquivo });
      }
      if (novas.length === 0) return [];
      fichasRef.current = [...fichasRef.current, ...novas];
      setFichas(fichasRef.current);
      for (const { ficha, arquivo } of paraSubir) {
        subir(ficha.id, arquivo, ficha.mime, { previewUrl: ficha.previewUrl, duracaoSegundos: ficha.duracaoSegundos });
      }
      return novas.map((f) => f.id);
    },
    [subir],
  );

  const remover = useCallback((id: string) => {
    const xhr = envios.current.get(id);
    if (xhr) {
      xhr.abort();
      envios.current.delete(id);
    }
    const alvo = fichasRef.current.find((f) => f.id === id);
    if (alvo?.previewUrl) {
      try {
        URL.revokeObjectURL(alvo.previewUrl);
      } catch {
        /* nada */
      }
    }
    fichasRef.current = fichasRef.current.filter((f) => f.id !== id);
    setFichas(fichasRef.current);
  }, []);

  /**
   * Esvazia a fila depois do envio. As miniaturas NÃO são revogadas: a bolha da mensagem enviada continua usando
   * a `previewUrl` até a página fechar.
   */
  const limpar = useCallback(() => {
    fichasRef.current = [];
    setFichas([]);
  }, []);

  useEffect(() => {
    const emCurso = envios.current;
    return () => {
      emCurso.forEach((xhr) => xhr.abort());
      emCurso.clear();
    };
  }, []);

  const subindo = fichas.some((f) => f.estado === 'subindo');
  const comErro = fichas.some((f) => f.estado === 'erro');
  const prontos = fichas.filter((f) => f.estado === 'pronto' && f.anexo).map((f) => f.anexo as AnexoEnviado);

  return { fichas, fichasRef, adicionar, remover, limpar, subindo, comErro, prontos };
}
