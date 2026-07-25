// SPEC-054 Bloco A — upload server-side autorizado.
//
// Mudanças em relação ao comportamento anterior:
//   1. a empresa do caminho é DERIVADA DA SESSÃO, nunca aceita do client;
//   2. a resposta devolve `storagePath` (referência durável) e `url` do proxy
//      autenticado — `publicUrl` deixa de ser a identidade do objeto;
//   3. o MIME é validado contra o conteúdo real (magic bytes), não apenas
//      contra o header enviado pelo browser.
import { NextRequest, NextResponse } from 'next/server';
import { randomUUID } from 'crypto';

import { getAdminContext, requireCompanyMember } from '@/lib/admin/admin-auth';
import { buildCanonicalPath, toProxyUrl, type StorageBucket } from '@/lib/storage/resolver';
import { uploadObject } from '@/lib/storage/signed';

export const dynamic = 'force-dynamic';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

const ALLOWED_BUCKETS: StorageBucket[] = ['chat-media', 'chat-docs', 'avatars', 'voice-messages'];

const ALLOWED_MIME_TYPES: Record<string, string[]> = {
  'chat-media': [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain', 'text/csv', 'text/markdown',
  ],
  'chat-docs': [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain', 'text/csv', 'text/markdown',
    'audio/webm', 'audio/ogg', 'audio/mp3', 'audio/mpeg', 'audio/wav',
  ],
  avatars: ['image/jpeg', 'image/png', 'image/webp'],
  'voice-messages': ['audio/webm', 'audio/ogg', 'audio/mp3', 'audio/mpeg', 'audio/wav'],
};

/** Domínio lógico dentro do path canônico, por bucket. */
const BUCKET_DOMAIN: Record<string, string> = {
  'chat-media': 'chat-media',
  'chat-docs': 'chat-docs',
  'voice-messages': 'voice-messages',
  avatars: 'avatars',
};

/**
 * Verificação de conteúdo real por magic bytes.
 * Bloqueia HTML ativo e executáveis mascarados por extensão/`Content-Type`.
 * Retorna null quando o conteúdo é aceitável.
 */
function rejectByMagicBytes(bytes: Uint8Array, declaredMime: string): string | null {
  const head = Array.from(bytes.slice(0, 16));
  const startsWith = (sig: number[]) => sig.every((b, i) => head[i] === b);

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

  return null;
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
      return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
    }

    const formData = await request.formData();
    const file = formData.get('file') as File | null;
    const bucket = ((formData.get('bucket') as string) || 'chat-docs') as StorageBucket;

    if (!file) {
      return NextResponse.json({ error: 'Arquivo não fornecido' }, { status: 400 });
    }

    if (file.size > MAX_FILE_SIZE) {
      const maxMB = MAX_FILE_SIZE / 1024 / 1024;
      return NextResponse.json(
        { error: `Arquivo muito grande. Máximo permitido: ${maxMB}MB` },
        { status: 413 },
      );
    }

    if (!ALLOWED_BUCKETS.includes(bucket)) {
      return NextResponse.json({ error: 'Bucket não permitido' }, { status: 400 });
    }

    const allowedTypes = ALLOWED_MIME_TYPES[bucket] || [];
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: `Tipo de arquivo não permitido. Aceitos: ${allowedTypes.join(', ')}` },
        { status: 415 },
      );
    }

    const buffer = new Uint8Array(await file.arrayBuffer());

    const magicError = rejectByMagicBytes(buffer, file.type);
    if (magicError) {
      return NextResponse.json({ error: magicError }, { status: 415 });
    }

    // O caminho é construído no servidor. Nada vindo do client entra aqui.
    const objectPath = buildCanonicalPath({
      companyId: owner.companyId,
      ownerId: owner.ownerId,
      domain: BUCKET_DOMAIN[bucket] || bucket,
      fileName: file.name,
      uuid: randomUUID(),
    });

    const result = await uploadObject({
      ref: { bucket, path: objectPath },
      body: buffer,
      contentType: file.type,
    });

    if ('error' in result) {
      console.error('[UPLOAD API] falha no upload:', result.error);
      return NextResponse.json({ error: 'Erro ao fazer upload do arquivo' }, { status: 500 });
    }

    const proxyUrl = toProxyUrl({ bucket, path: result.path });

    return NextResponse.json(
      {
        success: true,
        // referência DURÁVEL — é isto que deve ser persistido
        storagePath: `${bucket}/${result.path}`,
        filePath: result.path,
        bucket,
        // URL de leitura autorizada (efêmera do ponto de vista de autorização)
        url: proxyUrl,
        fileName: file.name,
        mimeType: file.type,
        size: file.size,
      },
      { status: 201 },
    );
  } catch (error) {
    console.error('[UPLOAD API] erro inesperado:', error);
    return NextResponse.json({ error: 'Erro interno ao fazer upload' }, { status: 500 });
  }
}
