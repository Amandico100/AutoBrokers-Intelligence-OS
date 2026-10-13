// SPEC-064 Bloco C.3 — a página de cada Auxiliar. SPEC-131-B — a CASCA de todo aplicativo: cabeçalho + abas por
// `?aba=` (Início · Configurar · o trabalho feito · Dúvidas).
//
// Server component: resolve a sessão e a corretora no servidor. O `companyId` NUNCA vem do client — é o mesmo
// princípio de todo o dashboard.
//
// A rota é dinâmica por slug, e é a ÚNICA. A auditoria encontrou duas páginas escritas à mão ao lado da rota
// dinâmica da galeria — `follow-up-whatsapp/` e `resumo-atendimentos/` — que é exatamente como a bagunça se
// reproduz: cada Auxiliar novo acha que é exceção. Aqui não há exceção. As abas são QUERY (`?aba=`), nunca subrota:
// uma pasta nova ao lado de `[slug]` com outro nome de parâmetro derruba a tabela de rotas (CLAUDE.md §9.1).

import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/auxiliaries/server';
import { getBackendUrl } from '@/lib/backend-url';
import {
  atividadeRecente,
  auxiliarPorSlug,
  podeLigar,
  type FontesDoComoComecar,
  type PassoDaProntidao,
} from '@/lib/auxiliaries/catalog';
import AuxiliarDetalheClient from './AuxiliarDetalheClient';

export const dynamic = 'force-dynamic';

/** Os aplicativos cujo "Como começar" lê a prontidão do multicálculo (conexões da corretora e da pessoa). */
const LEEM_A_PRONTIDAO = new Set(['renovacao', 'cotacao', 'quem-cobra-menos']);

function cabecalhosDoBackend(): Record<string, string> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  return { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key };
}

async function lerDoBackend(caminho: string): Promise<any | null> {
  try {
    const res = await fetch(`${getBackendUrl()}${caminho}`, {
      headers: cabecalhosDoBackend(),
      cache: 'no-store',
      signal: AbortSignal.timeout(6000),
    });
    if (!res.ok) return null;
    return await res.json().catch(() => null);
  } catch {
    return null;
  }
}

/**
 * O que o "Como começar" precisa e só o servidor lê: os passos da prontidão (a régua ÚNICA do backend —
 * `servicos_da_corretora.prontidao`) e se o Agger DA PESSOA da sessão está conectado (`aggers-da-equipe`).
 * Falhou a leitura → `null`, e o passo aparece como "não deu para conferir agora" (nunca como pronto).
 */
async function fontesDoComoComecar(companyId: string, userId: string): Promise<FontesDoComoComecar> {
  const cid = encodeURIComponent(companyId);
  const [prontidao, equipe] = await Promise.all([
    lerDoBackend(`/api/servicos-da-corretora/prontidao?company_id=${cid}`),
    lerDoBackend(`/api/portal/aggers-da-equipe?company_id=${cid}`),
  ]);
  const passos: PassoDaProntidao[] | null = Array.isArray(prontidao?.passos) ? prontidao.passos : null;
  let meuAgger: boolean | null = null;
  if (Array.isArray(equipe?.pessoas)) {
    const eu = equipe.pessoas.find((p: any) => String(p?.user_id) === userId);
    meuAgger = eu ? Boolean(eu?.agger?.conectado) : false;
  }
  return { prontidao: passos, meuAgger };
}

export default async function AuxiliarPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const sessao = await resolveSessionCompany();
  if (!sessao) redirect('/login');

  const supabase = getSupabaseAdmin();
  const item = await auxiliarPorSlug(supabase, sessao.companyId, slug);
  if (!item) notFound();

  const [atividade, fontes] = await Promise.all([
    atividadeRecente(supabase, sessao.companyId, item),
    LEEM_A_PRONTIDAO.has(item.slug)
      ? fontesDoComoComecar(sessao.companyId, sessao.userId)
      : Promise.resolve<FontesDoComoComecar>({ prontidao: null, meuAgger: null }),
  ]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl px-4 pb-16 pt-6 sm:px-6 sm:pt-8">
        <Link
          href="/dashboard/auxiliares"
          className="mb-4 inline-flex min-h-[44px] items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
          Aplicativos
        </Link>

        <AuxiliarDetalheClient
          item={item}
          podeLigar={podeLigar(item)}
          atividade={atividade}
          fontes={fontes}
        />
      </div>
    </div>
  );
}
