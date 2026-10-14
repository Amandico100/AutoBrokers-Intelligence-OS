// SPEC-054 Bloco A — upload server-side autorizado.
//
// Mudanças em relação ao comportamento anterior:
//   1. a empresa do caminho é DERIVADA DA SESSÃO, nunca aceita do client;
//   2. a resposta devolve `storagePath` (referência durável) e `url` do proxy
//      autenticado — `publicUrl` deixa de ser a identidade do objeto;
//   3. o MIME é validado contra o conteúdo real (magic bytes), não apenas
//      contra o header enviado pelo browser.
//
// SPEC-132-A · A2 — o upload do CHAT novo.
//   📊 B3 (14/10/2026): `useImageUpload.ts:104` lia `data.publicUrl`, que esta rota
//   nunca devolveu — o anexo sumia sem aviso. O contrato agora é explícito:
//     sucesso → { ok: true, bucket, path, nome, mime, bytes, url } (+ os campos
//               antigos `success/storagePath/filePath/fileName/mimeType/size`,
//               que avatars e voice-messages ainda leem)
//     erro    → { ok: false, motivo } em português (413 · 415 · 400 · 401 · 500);
//               `error` repete o motivo para quem ainda lê o campo antigo.
//   📊 B5: + HEIC/HEIF (o iPhone), .xls, áudio por arquivo (m4a/mp3/ogg/opus/wav/
//   webm/aac) e 20 MB nos buckets do chat. `avatars`/`voice-messages` mantêm 5 MB.
//   🔴 O PREFIXO: o `path` devolvido é SEMPRE `<company_id>/<user_id|system>/<domínio>/
//   <uuid>.<ext>` (`buildCanonicalPath`, `lib/storage/resolver.ts`), com a corretora
//   da SESSÃO. O BFF do turno (`app/api/chat/stream/route.ts`) e o backend
//   (`chat_anexos.py`) recusam qualquer path que não comece com `<company_id>/`.
import { NextRequest, NextResponse } from 'next/server';
import { randomUUID } from 'crypto';

import { getAdminContext, requireCompanyMember } from '@/lib/admin/admin-auth';
import { buildCanonicalPath, toProxyUrl, type StorageBucket } from '@/lib/storage/resolver';
import { uploadObject } from '@/lib/storage/signed';

export const dynamic = 'force-dynamic';

const MB = 1024 * 1024;

/** O teto por bucket. Os do chat sobem para 20 MB (SPEC-132-A B5); os outros ficam como eram. */
const LIMITE_POR_BUCKET: Record<string, number> = {
  'chat-media': 20 * MB,
  'chat-docs': 20 * MB,
  avatars: 5 * MB,
  'voice-messages': 5 * MB,
};

const ALLOWED_BUCKETS: StorageBucket[] = ['chat-media', 'chat-docs', 'avatars', 'voice-messages'];

const MIME_DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const MIME_PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
const MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const MIME_XLS = 'application/vnd.ms-excel';

const IMAGENS_DO_CHAT = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', 'image/heif'];
const DOCUMENTOS_DO_CHAT = [
  'application/pdf', MIME_DOCX, MIME_PPTX, MIME_XLSX, MIME_XLS,
  'text/plain', 'text/csv', 'text/markdown',
];
const AUDIOS_DO_CHAT = ['audio/webm', 'audio/ogg', 'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/mp4', 'audio/aac'];

/**
 * O que cada bucket aceita (o MIME CANÔNICO, depois de `resolverMime`).
 * Os dois buckets do chat aceitam o MESMO conjunto: a tela escolhe o bucket pela
 * natureza do arquivo, e uma escolha "errada" não pode virar um erro para o corretor.
 */
const ALLOWED_MIME_TYPES: Record<string, string[]> = {
  'chat-media': [...IMAGENS_DO_CHAT, ...DOCUMENTOS_DO_CHAT, ...AUDIOS_DO_CHAT],
  'chat-docs': [...IMAGENS_DO_CHAT, ...DOCUMENTOS_DO_CHAT, ...AUDIOS_DO_CHAT],
  avatars: ['image/jpeg', 'image/png', 'image/webp'],
  'voice-messages': ['audio/webm', 'audio/ogg', 'audio/mp3', 'audio/mpeg', 'audio/wav'],
};

/**
 * Extensão → o MIME canônico + os nomes que os navegadores e sistemas usam para ele.
 * 📊 O que chega de verdade: o Windows manda `.csv` como `application/vnd.ms-excel`;
 * o Safari manda HEIC como `image/heic` e alguns Androids como `application/octet-stream`;
 * o MediaRecorder manda `audio/webm;codecs=opus`. Sem esta tabela, cada um vira "formato
 * não aceito" — e foi exatamente o "dá erro" do Founder.
 */
const FORMATOS: Record<string, { mime: string; aliases: string[] }> = {
  jpg: { mime: 'image/jpeg', aliases: ['image/jpg', 'image/pjpeg'] },
  jpeg: { mime: 'image/jpeg', aliases: ['image/jpg', 'image/pjpeg'] },
  png: { mime: 'image/png', aliases: [] },
  gif: { mime: 'image/gif', aliases: [] },
  webp: { mime: 'image/webp', aliases: [] },
  heic: { mime: 'image/heic', aliases: ['image/heif', 'image/heic-sequence', 'image/heif-sequence'] },
  heif: { mime: 'image/heif', aliases: ['image/heic', 'image/heif-sequence', 'image/heic-sequence'] },
  pdf: { mime: 'application/pdf', aliases: ['application/x-pdf'] },
  docx: { mime: MIME_DOCX, aliases: ['application/zip'] },
  pptx: { mime: MIME_PPTX, aliases: ['application/zip'] },
  xlsx: { mime: MIME_XLSX, aliases: ['application/zip'] },
  xls: { mime: MIME_XLS, aliases: ['application/excel', 'application/x-excel', 'application/x-msexcel'] },
  csv: {
    mime: 'text/csv',
    aliases: ['application/vnd.ms-excel', 'text/comma-separated-values', 'application/csv', 'text/x-csv', 'text/plain'],
  },
  txt: { mime: 'text/plain', aliases: [] },
  md: { mime: 'text/markdown', aliases: ['text/x-markdown', 'text/plain'] },
  markdown: { mime: 'text/markdown', aliases: ['text/x-markdown', 'text/plain'] },
  m4a: { mime: 'audio/mp4', aliases: ['audio/x-m4a', 'audio/m4a', 'audio/mp4a-latm', 'video/mp4'] },
  mp3: { mime: 'audio/mpeg', aliases: ['audio/mp3', 'audio/mpeg3', 'audio/x-mpeg-3', 'audio/x-mp3'] },
  ogg: { mime: 'audio/ogg', aliases: ['application/ogg', 'audio/opus', 'audio/x-ogg'] },
  oga: { mime: 'audio/ogg', aliases: ['application/ogg', 'audio/opus'] },
  opus: { mime: 'audio/ogg', aliases: ['audio/opus', 'application/ogg'] },
  wav: { mime: 'audio/wav', aliases: ['audio/x-wav', 'audio/wave', 'audio/vnd.wave'] },
  webm: { mime: 'audio/webm', aliases: ['video/webm'] },
  aac: { mime: 'audio/aac', aliases: ['audio/x-aac', 'audio/aacp'] },
};

/** O navegador não soube dizer o tipo: quem decide é a extensão. */
const MIME_GENERICO = new Set(['', 'application/octet-stream', 'binary/octet-stream']);

/** `audio/webm;codecs=opus` → `audio/webm`; minúsculas; sem espaços. */
function normalizarMime(tipo: string | null | undefined): string {
  return String(tipo || '').split(';')[0].trim().toLowerCase();
}

function extensaoDe(nome: string): string {
  const partes = String(nome || '').toLowerCase().split('.');
  return partes.length > 1 ? (partes.pop() || '').replace(/[^a-z0-9]/g, '') : '';
}

/**
 * O MIME CANÔNICO do arquivo, ou null quando não é um formato que conhecemos.
 *   1. a extensão é conhecida e o tipo declarado bate com ela (ou é genérico) → o canônico da extensão;
 *   2. senão, o tipo declarado — como era antes desta SPEC (o blob de voz sem extensão, por exemplo).
 */
function resolverMime(nome: string, declarado: string): string | null {
  const formato = FORMATOS[extensaoDe(nome)];
  if (formato && (declarado === formato.mime || formato.aliases.includes(declarado) || MIME_GENERICO.has(declarado))) {
    return formato.mime;
  }
  return declarado || null;
}

/** O nome que o corretor vê de volta: sem pasta, sem caractere de controle, com teto. */
function nomeLimpo(nome: string): string {
  // eslint-disable-next-line no-control-regex
  const base = String(nome || '').split(/[\\/]/).pop()!.replace(/[\u0000-\u001f\u007f]/g, '').trim();
  return (base || 'arquivo').slice(0, 200);
}

function rotuloDoFormato(nome: string, mime: string): string {
  const ext = extensaoDe(nome);
  if (ext) return `.${ext}`;
  return mime || 'sem extensão';
}

/**
 * Verificação de conteúdo real por magic bytes.
 * Bloqueia HTML ativo e executáveis mascarados por extensão/`Content-Type`.
 * Retorna null quando o conteúdo é aceitável.
 */
function rejectByMagicBytes(bytes: Uint8Array, declaredMime: string): string | null {
  const head = Array.from(bytes.slice(0, 16));
  const startsWith = (sig: number[], at = 0) => sig.every((b, i) => head[at + i] === b);
  const ascii = (at: number, len: number) => String.fromCharCode(...head.slice(at, at + len));

  // executáveis: MZ (PE), ELF, Mach-O
  if (startsWith([0x4d, 0x5a])) return 'executavel_nao_permitido';
  if (startsWith([0x7f, 0x45, 0x4c, 0x46])) return 'executavel_nao_permitido';
  if (startsWith([0xcf, 0xfa, 0xed, 0xfe]) || startsWith([0xfe, 0xed, 0xfa, 0xcf])) {
    return 'executavel_nao_permitido';
  }

  // HTML ativo mascarado
  const asciiHead = new TextDecoder('utf-8', { fatal: false })
    .decode(bytes.slice(0, 512))
    .trimStart()
    .toLowerCase();
  if (asciiHead.startsWith('<!doctype html') || asciiHead.startsWith('<html') || asciiHead.startsWith('<script')) {
    return 'html_ativo_nao_permitido';
  }

  // coerência mínima para os formatos que mais circulam
  if (declaredMime === 'application/pdf' && !startsWith([0x25, 0x50, 0x44, 0x46])) {
    return 'conteudo_nao_confere_com_pdf';
  }
  if (declaredMime === 'image/png' && !startsWith([0x89, 0x50, 0x4e, 0x47])) {
    return 'conteudo_nao_confere_com_png';
  }
  if (declaredMime === 'image/jpeg' && !startsWith([0xff, 0xd8, 0xff])) {
    return 'conteudo_nao_confere_com_jpeg';
  }
  // SPEC-132-A — os formatos novos têm assinatura universal; os outros (mp3, aac, texto) só passam pelo filtro acima.
  if (declaredMime === 'image/gif' && ascii(0, 4) !== 'GIF8') return 'conteudo_nao_confere_com_gif';
  if (declaredMime === 'image/webp' && !(ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WEBP')) {
    return 'conteudo_nao_confere_com_webp';
  }
  if ((declaredMime === 'image/heic' || declaredMime === 'image/heif') && ascii(4, 4) !== 'ftyp') {
    return 'conteudo_nao_confere_com_heic';
  }
  if ([MIME_DOCX, MIME_PPTX, MIME_XLSX].includes(declaredMime) && !startsWith([0x50, 0x4b, 0x03, 0x04])) {
    return 'conteudo_nao_confere_com_office';
  }
  if (declaredMime === MIME_XLS && !startsWith([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1])) {
    return 'conteudo_nao_confere_com_xls';
  }
  if (declaredMime === 'audio/ogg' && ascii(0, 4) !== 'OggS') return 'conteudo_nao_confere_com_ogg';
  if (declaredMime === 'audio/webm' && !startsWith([0x1a, 0x45, 0xdf, 0xa3])) return 'conteudo_nao_confere_com_webm';
  if (declaredMime === 'audio/wav' && !(ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WAVE')) {
    return 'conteudo_nao_confere_com_wav';
  }
  if (declaredMime === 'audio/mp4' && ascii(4, 4) !== 'ftyp') return 'conteudo_nao_confere_com_m4a';

  return null;
}

/** O código técnico do magic bytes vira a frase que o corretor lê. */
function motivoDoConteudo(codigo: string, nome: string): string {
  if (codigo === 'executavel_nao_permitido') return 'Este arquivo é um programa, e programas não podem ser enviados.';
  if (codigo === 'html_ativo_nao_permitido') return 'Este arquivo é uma página da web, e páginas não podem ser enviadas.';
  return `O conteúdo de "${nome}" não confere com o tipo dele. Ele pode estar corrompido — tente salvar de novo e reenviar.`;
}

function falha(motivo: string, status: number) {
  return NextResponse.json({ ok: false, motivo, error: motivo }, { status });
}

/** Empresa e usuário SEMPRE derivados do servidor. */
async function resolveOwner(): Promise<{ companyId: string; ownerId: string | null } | null> {
  const tenant = await requireCompanyMember({ write: false });
  if (tenant.ok) return { companyId: tenant.ctx.companyId, ownerId: tenant.ctx.userId };

  const admin = await getAdminContext();
  if (admin?.companyId) return { companyId: admin.companyId, ownerId: admin.adminId };

  return null;
}

export async function POST(request: NextRequest) {
  try {
    const owner = await resolveOwner();
    if (!owner) {
      return falha('Sua sessão expirou. Entre de novo para enviar o arquivo.', 401);
    }

    let formData: FormData;
    try {
      formData = await request.formData();
    } catch {
      return falha('Não consegui receber o arquivo. Tente enviar de novo.', 400);
    }
    const file = formData.get('file') as File | null;
    const bucket = ((formData.get('bucket') as string) || 'chat-docs') as StorageBucket;

    if (!file || typeof (file as any).arrayBuffer !== 'function') {
      return falha('Nenhum arquivo chegou. Escolha o arquivo e tente de novo.', 400);
    }

    if (!ALLOWED_BUCKETS.includes(bucket)) {
      return falha('Este destino de arquivo não existe.', 400);
    }

    const nome = nomeLimpo(file.name);
    const limite = LIMITE_POR_BUCKET[bucket] ?? 5 * MB;
    if (file.size > limite) {
      return falha(`O arquivo passa de ${Math.round(limite / MB)} MB.`, 413);
    }
    if (file.size === 0) {
      return falha(`O arquivo "${nome}" está vazio.`, 400);
    }

    const mime = resolverMime(nome, normalizarMime(file.type));
    const allowedTypes = ALLOWED_MIME_TYPES[bucket] || [];
    if (!mime || !allowedTypes.includes(mime)) {
      return falha(`Formato não aceito: ${rotuloDoFormato(nome, normalizarMime(file.type))}`, 415);
    }

    const buffer = new Uint8Array(await file.arrayBuffer());

    const magicError = rejectByMagicBytes(buffer, mime);
    if (magicError) {
      return falha(motivoDoConteudo(magicError, nome), 415);
    }

    // O caminho é construído no servidor. Nada vindo do client entra aqui.
    // 🔴 `<company_id da sessão>/<user_id|system>/<bucket>/<uuid>.<ext>` — o prefixo que o BFF e o backend conferem.
    const objectPath = buildCanonicalPath({
      companyId: owner.companyId,
      ownerId: owner.ownerId,
      domain: bucket,
      fileName: nome,
      uuid: randomUUID(),
    });

    const result = await uploadObject({
      ref: { bucket, path: objectPath },
      body: buffer,
      contentType: mime,
    });

    if ('error' in result) {
      // ⛔ nunca o nome do arquivo no log — só o motivo técnico do Storage.
      console.error('[UPLOAD API] falha no upload:', result.error);
      const erro = String(result.error || '').toLowerCase();
      if (/too large|maximum allowed size|exceed/.test(erro)) {
        return falha('O arquivo passa do limite que o armazenamento aceita hoje.', 413);
      }
      if (/mime|content type|not supported|invalid_mime/.test(erro)) {
        return falha('O armazenamento ainda não aceita este formato.', 415);
      }
      return falha('Não consegui guardar o arquivo agora. Tente de novo em instantes.', 500);
    }

    const proxyUrl = toProxyUrl({ bucket, path: result.path });

    return NextResponse.json(
      {
        ok: true,
        bucket,
        path: result.path,
        nome,
        mime,
        bytes: file.size,
        // URL de leitura autorizada (efêmera do ponto de vista de autorização) — para a TELA, nunca para um modelo
        url: proxyUrl,
        // ── os campos de antes (avatars e voice-messages ainda os leem) ──
        success: true,
        // referência DURÁVEL — é isto que deve ser persistido
        storagePath: `${bucket}/${result.path}`,
        filePath: result.path,
        fileName: nome,
        mimeType: mime,
        size: file.size,
      },
      { status: 201 },
    );
  } catch (error) {
    console.error('[UPLOAD API] erro inesperado:', (error as any)?.name || 'erro');
    return falha('Não consegui guardar o arquivo agora. Tente de novo em instantes.', 500);
  }
}
