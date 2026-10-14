/**
 * SPEC-132-A · A1 — os tipos do composer novo e os limites que ele avisa ANTES de subir.
 *
 * O contrato com a rota de upload (fatia A2) é `POST /api/upload` → `{ok:true, bucket, path, nome, mime, bytes, url}`
 * ou `{ok:false, motivo}`. O que o pedido do turno leva é só `{bucket, path, nome, mime, bytes}` — nunca a URL:
 * o backend lê o arquivo pelos BYTES, com o prefixo da corretora conferido (D-132A-05).
 */

/** O esforço do turno: o MESMO modelo, com mais ou menos raciocínio (D-132A-04). */
export type Esforco = 'rapido' | 'equilibrado' | 'maximo';

export const ESFORCO_PADRAO: Esforco = 'equilibrado';

/** O anexo como o pedido do turno o leva (`attachments[]` do `POST /api/chat/stream`). */
export interface AnexoDoPedido {
  bucket: string;
  path: string;
  nome: string;
  mime: string;
  bytes: number;
}

/**
 * O anexo como a TELA o conhece depois de subir: o que vai no pedido, mais o que só serve para desenhar a bolha
 * nesta sessão (`url` do proxy autenticado, `previewUrl` local da foto, a duração do áudio gravado).
 */
export interface AnexoEnviado extends AnexoDoPedido {
  url?: string;
  previewUrl?: string;
  duracaoSegundos?: number;
  /** o que o áudio disse, quando o backend devolve a transcrição junto do anexo gravado */
  transcricao?: string;
}

/** As opções que o composer manda junto do texto. */
export interface OpcoesDoEnvio {
  esforco: Esforco;
}

/** Até 10 arquivos por mensagem, 20 MB cada (SPEC-132-A B5). */
export const MAX_ARQUIVOS = 10;
export const MAX_BYTES = 20 * 1024 * 1024;

/** O que o `accept` dos seletores oferece. A rota de upload continua sendo quem decide. */
export const ACEITA_FOTOS = 'image/*,.heic,.heif';
export const ACEITA_ARQUIVOS =
  '.pdf,.docx,.pptx,.xlsx,.xls,.csv,.txt,.md,image/*,.heic,.heif,audio/*,.m4a,.mp3,.ogg,.opus,.wav,.webm';
