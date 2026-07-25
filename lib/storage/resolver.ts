// SPEC-054 Bloco A — Resolver central de Storage.
//
// Antes desta SPEC os buckets eram públicos e a aplicação guardava a URL
// pública absoluta como identificador durável. Isso expunha documentos de
// corretora por URL e tornava impossível fechar o bucket sem quebrar o
// histórico.
//
// Regra canônica a partir daqui:
//   - a referência DURÁVEL é o PATH (`<company_id>/<...>`), nunca a URL;
//   - a URL de leitura é efêmera e emitida por rota server-side autorizada;
//   - a URL pública legada continua sendo ACEITA na leitura (compat), mas
//     nunca é gravada de novo.
//
// Este módulo é puro e não faz I/O — para ser testável offline. A emissão de
// signed URL vive em `signed.ts` porque exige service role.

/** Buckets governados por esta SPEC. */
export const STORAGE_BUCKETS = [
  'chat-media',
  'chat-docs',
  'voice-messages',
  'avatars',
  'portal-evidence',
] as const;

export type StorageBucket = (typeof STORAGE_BUCKETS)[number];

/** Buckets que o proxy autenticado pode servir ao usuário final. */
export const PROXY_READABLE_BUCKETS: StorageBucket[] = [
  'chat-media',
  'chat-docs',
  'voice-messages',
  'avatars',
];

export interface StorageRef {
  bucket: StorageBucket;
  /** Caminho dentro do bucket, sem barra inicial. */
  path: string;
}

const PUBLIC_URL_MARKER = '/storage/v1/object/public/';
const SIGNED_URL_MARKER = '/storage/v1/object/sign/';

function isKnownBucket(value: string): value is StorageBucket {
  return (STORAGE_BUCKETS as readonly string[]).includes(value);
}

/**
 * Normaliza um caminho de objeto.
 * Rejeita traversal, barras duplicadas, segmentos vazios e caminho absoluto.
 * Retorna null quando o caminho é inaceitável — o chamador deve tratar como 400.
 */
export function normalizeObjectPath(raw: string): string | null {
  if (!raw) return null;

  // remove querystring e fragmento (URLs legadas gravadas com '?' no fim)
  let value = raw.split('#')[0].split('?')[0];

  // decodifica uma vez; se ainda houver %2e/%2f escondendo traversal, cai fora
  try {
    value = decodeURIComponent(value);
  } catch {
    return null;
  }

  value = value.replace(/^\/+/, '');
  if (!value) return null;

  // caractere de controle ou NUL
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(value)) return null;
  const segments = value.split('/');
  for (const segment of segments) {
    if (segment === '' || segment === '.' || segment === '..') return null;
    if (segment === '~') return null;
  }

  // caminho absoluto do Windows ou esquema embutido
  if (/^[a-zA-Z]:/.test(value) || value.includes('://')) return null;

  return segments.join('/');
}

/**
 * Aceita as três formas que existem hoje no banco e no código:
 *   1. URL pública legada  .../storage/v1/object/public/<bucket>/<path>
 *   2. URL assinada        .../storage/v1/object/sign/<bucket>/<path>?token=...
 *   3. Referência canônica <bucket>/<path>
 *
 * Retorna null se não for reconhecível.
 */
export function parseStorageRef(value: string | null | undefined): StorageRef | null {
  if (!value) return null;
  const input = String(value).trim();
  if (!input) return null;

  for (const marker of [PUBLIC_URL_MARKER, SIGNED_URL_MARKER]) {
    const at = input.indexOf(marker);
    if (at !== -1) {
      const rest = input.slice(at + marker.length);
      const slash = rest.indexOf('/');
      if (slash <= 0) return null;
      const bucket = rest.slice(0, slash);
      const path = normalizeObjectPath(rest.slice(slash + 1));
      if (!path || !isKnownBucket(bucket)) return null;
      return { bucket, path };
    }
  }

  // qualquer outra URL absoluta não é referência de storage nossa
  if (/^https?:\/\//i.test(input)) return null;

  const normalized = normalizeObjectPath(input);
  if (!normalized) return null;
  const slash = normalized.indexOf('/');
  if (slash <= 0) return null;
  const bucket = normalized.slice(0, slash);
  const path = normalized.slice(slash + 1);
  if (!isKnownBucket(bucket) || !path) return null;
  return { bucket, path };
}

/** Forma canônica gravável no banco: `<bucket>/<path>`. */
export function toStorageRef(bucket: StorageBucket, path: string): string {
  return `${bucket}/${path}`;
}

/** URL do proxy autenticado que a UI deve consumir. */
export function toProxyUrl(ref: StorageRef): string {
  const encoded = ref.path
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  return `/api/storage/${ref.bucket}/${encoded}`;
}

/**
 * Converte qualquer valor legado ou canônico na URL que a UI deve usar.
 * Devolve o valor original quando não reconhece — assim uma URL externa
 * legítima (avatar de terceiro, por exemplo) continua funcionando.
 */
export function resolveMediaUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const ref = parseStorageRef(value);
  return ref ? toProxyUrl(ref) : value;
}

/**
 * O primeiro segmento do path é o tenant dono do objeto.
 * `null` quando o objeto é legado/sem escopo (ex.: `teste-fable/t.pdf`).
 */
export function ownerCompanyOf(ref: StorageRef): string | null {
  const first = ref.path.split('/')[0];
  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(first);
  return isUuid ? first : null;
}

/**
 * Autorização de leitura. `isPlatformMaster` enxerga tudo (suporte);
 * qualquer outro principal só acessa objeto do próprio tenant.
 * Objeto sem escopo de tenant é acessível somente pelo master.
 */
export function canAccessObject(args: {
  ref: StorageRef;
  companyId: string | null;
  isPlatformMaster: boolean;
}): boolean {
  const { ref, companyId, isPlatformMaster } = args;
  if (isPlatformMaster) return true;
  const owner = ownerCompanyOf(ref);
  if (!owner) return false;
  if (!companyId) return false;
  return owner === companyId;
}

/** Caminho canônico para NOVOS objetos: `<company>/<owner>/<domain>/<uuid>.<ext>`. */
export function buildCanonicalPath(args: {
  companyId: string;
  ownerId: string | null;
  domain: string;
  fileName: string;
  uuid: string;
}): string {
  const ext = (args.fileName.split('.').pop() || 'bin').toLowerCase().replace(/[^a-z0-9]/g, '');
  const owner = args.ownerId || 'system';
  return `${args.companyId}/${owner}/${args.domain}/${args.uuid}.${ext || 'bin'}`;
}

/** TTL padrão das signed URLs (segundos). Curto por decisão da SPEC-054 §7.3.4. */
export const SIGNED_URL_TTL_SECONDS = 300;
