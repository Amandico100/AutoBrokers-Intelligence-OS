// SPEC-054 Bloco A — emissão de signed URL com service role.
// Separado de `resolver.ts` porque exige segredo e I/O; o resolver
// permanece puro e testável offline.
import { createClient } from '@supabase/supabase-js';

import { SIGNED_URL_TTL_SECONDS, type StorageRef } from './resolver';

function serviceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

/**
 * Emite uma signed URL curta para o objeto.
 * A URL NUNCA deve ser persistida no banco — a referência durável é o path.
 */
export async function createSignedUrl(
  ref: StorageRef,
  ttlSeconds: number = SIGNED_URL_TTL_SECONDS,
): Promise<string | null> {
  const { data, error } = await serviceClient()
    .storage.from(ref.bucket)
    .createSignedUrl(ref.path, ttlSeconds);

  if (error || !data?.signedUrl) return null;
  return data.signedUrl;
}

/** Baixa os bytes do objeto para streaming pelo proxy autenticado. */
export async function downloadObject(
  ref: StorageRef,
): Promise<{ body: ArrayBuffer; contentType: string } | null> {
  const { data, error } = await serviceClient().storage.from(ref.bucket).download(ref.path);
  if (error || !data) return null;
  return {
    body: await data.arrayBuffer(),
    contentType: data.type || 'application/octet-stream',
  };
}

/** Upload server-side autorizado. Retorna o path efetivo gravado. */
export async function uploadObject(args: {
  ref: StorageRef;
  body: Uint8Array;
  contentType: string;
}): Promise<{ path: string } | { error: string }> {
  const { data, error } = await serviceClient()
    .storage.from(args.ref.bucket)
    .upload(args.ref.path, args.body, { contentType: args.contentType, upsert: false });

  if (error || !data?.path) return { error: error?.message || 'upload_failed' };
  return { path: data.path };
}
