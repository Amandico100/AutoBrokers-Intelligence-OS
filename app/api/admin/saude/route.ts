// Saúde do sistema, em português — a tela que responde "o deploy entrou?".
//
// 06/08/2026: o Founder precisou confirmar se um conserto tinha subido e não
// tinha como. A resposta existia no `/health` do backend, mas exigia montar uma
// URL à mão e ler JSON cru. Informação que só o autor consegue ler não é
// observabilidade — é anotação particular.
//
// Read-only e sem segredo: devolve apenas os SINAIS (booleanos) e o estado da
// infraestrutura. Nenhum token, nenhuma URL interna, nenhum valor de variável.
import { NextRequest, NextResponse } from 'next/server';

import { requireMasterAdmin } from '@/lib/admin/admin-auth';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) {
    return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  }

  let backend: string;
  try {
    backend = getBackendUrl();
  } catch (e) {
    if (e instanceof BackendUrlError) {
      return NextResponse.json({ ok: false, error: 'backend_url_nao_configurada' }, { status: 503 });
    }
    throw e;
  }

  try {
    const res = await fetch(`${backend}/health`, { cache: 'no-store' });
    const json = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const codigo = (json?.codigo ?? {}) as Record<string, unknown>;

    return NextResponse.json({
      ok: res.ok,
      status: json?.status ?? null,
      // Infra: cada peça diz de si mesma. Mantido como veio — o backend já
      // devolve só presença/estado, nunca credencial.
      infra: {
        database_sync: json?.database_sync ?? null,
        database_async: json?.database_async ?? null,
        redis: json?.redis ?? null,
        qdrant: json?.qdrant ?? null,
        storage: json?.storage ?? null,
      },
      // Os SINAIS são o que responde "qual código está no ar". Cada chave é uma
      // peça que nasceu num commit datado: se a peça existe, o commit subiu.
      // Vale mais que `git_commit`, que depende de o builder lembrar de passar
      // a variável — e 📊 em 06/08/2026 ele não passava ("nao-injetado").
      sinais: codigo,
      consultado_em: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({ ok: false, error: 'backend_inalcancavel' }, { status: 502 });
  }
}
