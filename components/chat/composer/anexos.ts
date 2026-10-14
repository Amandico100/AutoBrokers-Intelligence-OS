/**
 * SPEC-132-A · A1 — o que se decide sobre um arquivo ANTES e DEPOIS de subir. Funções puras (testáveis sem DOM).
 *
 * 🔴 B3 (📊 14/10, `useImageUpload.ts:104`): o composer antigo lia um campo que a rota de upload nunca devolveu, e
 * o anexo sumia sem aviso. Aqui a resposta é lida pelo contrato NOVO e só por ele: `ok:true` com `bucket` + `path`
 * é um anexo; qualquer outra coisa é um erro com a frase da rota (ou uma frase nossa) — nunca um silêncio.
 */
import { toProxyUrl, type StorageBucket } from '@/lib/storage/resolver';

import { MAX_BYTES, type AnexoEnviado } from './tipos';

/** extensão → MIME, para quando o navegador não diz (HEIC no Windows, `.md`, `.xls`, `.opus`…). */
const MIME_POR_EXTENSAO: Record<string, string> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  webp: 'image/webp',
  heic: 'image/heic',
  heif: 'image/heif',
  pdf: 'application/pdf',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  xls: 'application/vnd.ms-excel',
  csv: 'text/csv',
  txt: 'text/plain',
  md: 'text/markdown',
  m4a: 'audio/mp4',
  mp3: 'audio/mpeg',
  ogg: 'audio/ogg',
  opus: 'audio/ogg',
  wav: 'audio/wav',
  webm: 'audio/webm',
};

export function extensaoDe(nome: string): string {
  const i = nome.lastIndexOf('.');
  return i >= 0 ? nome.slice(i + 1).toLowerCase() : '';
}

/** O MIME do arquivo: o do navegador quando ele diz; o da extensão quando ele cala. */
export function mimeDoArquivo(nome: string, mimeDoNavegador: string | undefined | null): string {
  const doNavegador = (mimeDoNavegador || '').trim().toLowerCase();
  if (doNavegador && doNavegador !== 'application/octet-stream') return doNavegador;
  return MIME_POR_EXTENSAO[extensaoDe(nome)] || doNavegador || 'application/octet-stream';
}

export function ehImagem(mime: string): boolean {
  return mime.startsWith('image/');
}

export function ehAudio(mime: string): boolean {
  return mime.startsWith('audio/');
}

/** HEIC/HEIF: a rota aceita e o backend converte, mas fora do Safari o navegador não desenha a miniatura. */
export function navegadorDesenha(mime: string): boolean {
  return ehImagem(mime) && mime !== 'image/heic' && mime !== 'image/heif';
}

/** Foto vai para `chat-media`; documento e áudio para `chat-docs` (contrato A2). */
export function bucketDoArquivo(mime: string): 'chat-media' | 'chat-docs' {
  return ehImagem(mime) ? 'chat-media' : 'chat-docs';
}

/** O que barra o arquivo ANTES de subir. `null` = pode subir. */
export function motivoParaRecusar(nome: string, mime: string, bytes: number): string | null {
  if (bytes > MAX_BYTES) return 'O arquivo passa de 20 MB.';
  if (bytes === 0) return 'O arquivo está vazio.';
  const ext = extensaoDe(nome);
  const conhecido = Boolean(MIME_POR_EXTENSAO[ext]) || ehImagem(mime) || ehAudio(mime);
  if (!conhecido) return ext ? `Formato não aceito: .${ext}` : 'Formato não aceito.';
  return null;
}

export type RespostaDoUpload =
  | { ok: true; anexo: AnexoEnviado }
  | { ok: false; motivo: string };

/**
 * Lê a resposta de `POST /api/upload`. `status` é o HTTP; `corpo` é o JSON (ou `null` se não veio JSON).
 * ⛔ Só o contrato novo: `ok === true` + `bucket` + `path`. Sem isso, NÃO é anexo.
 */
export function lerRespostaDoUpload(status: number, corpo: unknown): RespostaDoUpload {
  const c = (corpo && typeof corpo === 'object' ? corpo : {}) as Record<string, unknown>;
  if (status === 401) return { ok: false, motivo: 'Sua sessão expirou. Entre de novo para anexar.' };
  if (c.ok === true && typeof c.bucket === 'string' && typeof c.path === 'string' && c.path) {
    return {
      ok: true,
      anexo: {
        bucket: c.bucket,
        path: c.path,
        nome: typeof c.nome === 'string' ? c.nome : c.path.split('/').pop() || 'arquivo',
        mime: typeof c.mime === 'string' ? c.mime : 'application/octet-stream',
        bytes: typeof c.bytes === 'number' ? c.bytes : 0,
        url: typeof c.url === 'string' ? c.url : undefined,
      },
    };
  }
  if (typeof c.motivo === 'string' && c.motivo.trim()) return { ok: false, motivo: c.motivo.trim() };
  if (status === 413) return { ok: false, motivo: 'O arquivo passa de 20 MB.' };
  if (status === 415) return { ok: false, motivo: 'Formato não aceito.' };
  return { ok: false, motivo: 'Não consegui enviar este arquivo. Tente de novo.' };
}

/** "2,4 MB" · "380 KB" — o tamanho como o corretor lê. */
export function tamanhoLegivel(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`;
}

const BUCKETS_DO_CHAT = ['chat-media', 'chat-docs', 'voice-messages'];

/**
 * A URL de leitura de um anexo já gravado. O payload guarda `{nome, mime, bytes, path}` (sem a URL, que é efêmera):
 * o bucket vem do próprio anexo, ou do segmento de domínio do caminho canônico
 * (`<company_id>/<dono>/<domínio>/<uuid>.<ext>`), ou do tipo do arquivo.
 */
export function urlDoAnexo(anexo: { bucket?: string; path?: string; mime?: string; url?: string; previewUrl?: string }): string | null {
  if (anexo.previewUrl) return anexo.previewUrl;
  if (anexo.url) return anexo.url;
  if (!anexo.path) return null;
  const segmentos = anexo.path.split('/');
  const bucket =
    (anexo.bucket && BUCKETS_DO_CHAT.includes(anexo.bucket) && anexo.bucket) ||
    segmentos.find((s) => BUCKETS_DO_CHAT.includes(s)) ||
    bucketDoArquivo(anexo.mime || '');
  return toProxyUrl({ bucket: bucket as StorageBucket, path: anexo.path });
}

/** Os anexos de uma mensagem gravada (`messages.payload.attachments`), normalizados. Nunca lança. */
export function anexosDaMensagem(payload: unknown): AnexoEnviado[] {
  const lista = payload && typeof payload === 'object' ? (payload as Record<string, unknown>).attachments : null;
  if (!Array.isArray(lista)) return [];
  const saida: AnexoEnviado[] = [];
  for (const item of lista) {
    if (!item || typeof item !== 'object') continue;
    const a = item as Record<string, unknown>;
    const nome = typeof a.nome === 'string' ? a.nome : '';
    const path = typeof a.path === 'string' ? a.path : '';
    if (!nome && !path) continue;
    saida.push({
      bucket: typeof a.bucket === 'string' ? a.bucket : '',
      path,
      nome: nome || path.split('/').pop() || 'arquivo',
      mime: typeof a.mime === 'string' ? a.mime : 'application/octet-stream',
      bytes: typeof a.bytes === 'number' ? a.bytes : 0,
      url: typeof a.url === 'string' ? a.url : undefined,
      previewUrl: typeof a.previewUrl === 'string' ? a.previewUrl : undefined,
      duracaoSegundos: typeof a.duracaoSegundos === 'number' ? a.duracaoSegundos : undefined,
      transcricao: typeof a.transcricao === 'string' && a.transcricao.trim() ? a.transcricao.trim() : undefined,
    });
  }
  return saida;
}
