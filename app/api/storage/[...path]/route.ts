// SPEC-054 Bloco A — proxy autenticado de leitura de Storage.
//
// Substitui o acesso por URL pública. Toda leitura passa por aqui e é
// autorizada server-side contra a sessão (iron-session) e o banco.
//
// GET /api/storage/<bucket>/<path...>
//   200 -> bytes do objeto (padrão)
//   302 -> signed URL curta, quando ?mode=redirect
//   401 -> sem sessão
//   403 -> objeto de outro tenant
//   400 -> bucket inválido ou path com traversal
//   404 -> objeto inexistente
import { NextRequest, NextResponse } from 'next/server';

import { getAdminContext, requireCompanyMember } from '@/lib/admin/admin-auth';
import {
  PROXY_READABLE_BUCKETS,
  canAccessObject,
  normalizeObjectPath,
  type StorageBucket,
  type StorageRef,
} from '@/lib/storage/resolver';
import { createSignedUrl, downloadObject } from '@/lib/storage/signed';

export const dynamic = 'force-dynamic';

interface Principal {
  companyId: string | null;
  isPlatformMaster: boolean;
}

/**
 * Resolve o principal aceitando as DUAS superfícies existentes:
 * dashboard da corretora (smith_user_session) e Portal Admin
 * (smith_admin_session). Ambos validados no banco, nunca só pelo cookie.
 */
async function resolvePrincipal(): Promise<Principal | null> {
  const tenant = await requireCompanyMember({ write: false });
  if (tenant.ok) {
    return { companyId: tenant.ctx.companyId, isPlatformMaster: false };
  }

  const admin = await getAdminContext();
  if (admin) {
    return { companyId: admin.companyId, isPlatformMaster: admin.isMaster };
  }

  return null;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  try {
    const { path: segments } = await context.params;

    if (!segments || segments.length < 2) {
      return NextResponse.json({ error: 'invalid_path' }, { status: 400 });
    }

    const bucket = segments[0] as StorageBucket;
    if (!PROXY_READABLE_BUCKETS.includes(bucket)) {
      return NextResponse.json({ error: 'bucket_not_allowed' }, { status: 400 });
    }

    const objectPath = normalizeObjectPath(segments.slice(1).join('/'));
    if (!objectPath) {
      return NextResponse.json({ error: 'invalid_path' }, { status: 400 });
    }

    const principal = await resolvePrincipal();
    if (!principal) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
    }

    const ref: StorageRef = { bucket, path: objectPath };

    if (!canAccessObject({ ref, ...principal })) {
      // 403 explícito: o objeto existe conceitualmente, mas é de outro tenant.
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    if (request.nextUrl.searchParams.get('mode') === 'redirect') {
      const signed = await createSignedUrl(ref);
      if (!signed) return NextResponse.json({ error: 'not_found' }, { status: 404 });
      return NextResponse.redirect(signed, { status: 302 });
    }

    const object = await downloadObject(ref);
    if (!object) {
      return NextResponse.json({ error: 'not_found' }, { status: 404 });
    }

    return new NextResponse(object.body, {
      status: 200,
      headers: {
        'Content-Type': object.contentType,
        // conteúdo de corretora nunca é cacheado por proxy compartilhado
        'Cache-Control': 'private, max-age=60, must-revalidate',
        'X-Content-Type-Options': 'nosniff',
        'Content-Disposition': 'inline',
      },
    });
  } catch (error) {
    console.error('[STORAGE PROXY] erro inesperado:', error);
    return NextResponse.json({ error: 'internal_error' }, { status: 500 });
  }
}
