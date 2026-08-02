// SPEC-064 Bloco B/E — Entregas: tudo que o AutoBrokers fez pela corretora,
// numa linha do tempo só.
//
// O menu tinha TRÊS itens para a mesma pergunta — "o que já aconteceu aqui?":
//
//     Atividades   agent_activities        o que os agentes fizeram
//     Histórico    conversations           o que você conversou com o chat
//     Pesquisas    research_*              o que você mandou conferir
//
// E ainda faltavam dois que não tinham tela nenhuma: os **artifacts** (o
// entregável de primeira classe, que o corretor abre e manda ao cliente) e as
// **execuções de auxiliar**. O produto produzia e não mostrava.
//
// Três itens de menu para a mesma pergunta é como um menu vira lista. Aqui é
// um lugar só, com filtro por tipo — o mesmo princípio de "o menu não cresce".
//
// Nada aqui é motor novo: são cinco leituras das tabelas que já existem,
// normalizadas numa forma comum. Não há tabela de "entrega".
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

/** Os tipos que o corretor reconhece — não as tabelas que os produzem. */
export type TipoDeEntrega = 'documento' | 'conversa' | 'trabalho' | 'pesquisa';

interface Entrega {
  id: string;
  tipo: TipoDeEntrega;
  titulo: string;
  detalhe: string | null;
  quando: string;
  /** Para onde o corretor vai quando clicar. Null = não há para onde ir ainda. */
  href: string | null;
  /** Rótulo curto de origem: "Cobrança Feita", "Checklist das 6h"… */
  origem: string | null;
}

const LIMITE_POR_FONTE = 120;

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  const [artefatos, briefings, execucoes, conversas, atividades, auxiliares] = await Promise.all([
    supabase.from('artifacts')
      .select('id, title, subtitle, kind, status, created_at')
      .eq('company_id', empresa).is('archived_at', null)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('briefing_publications')
      .select('id, headline, summary_text, briefing_type, published_at, created_at, delivery_status')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('auxiliary_runs')
      .select('id, tenant_auxiliary_id, status, run_type, error_message, started_at, finished_at, created_at')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('conversations')
      .select('id, session_id, title, channel, last_message_preview, updated_at, created_at')
      .eq('company_id', empresa)
      .order('updated_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    supabase.from('agent_activities')
      .select('id, category, title, detail, created_at')
      .eq('company_id', empresa)
      .order('created_at', { ascending: false }).limit(LIMITE_POR_FONTE),

    // Para dar NOME ao auxiliar que rodou. Sem isto a linha diria
    // "execução 4f2a-…", que não significa nada para o corretor.
    supabase.from('tenant_auxiliaries')
      .select('id, name, slug')
      .eq('company_id', empresa),
  ]);

  const nomeAux = new Map<string, { nome: string; slug: string }>();
  for (const a of auxiliares.data ?? []) {
    nomeAux.set(a.id, { nome: a.name ?? a.slug, slug: a.slug });
  }

  const itens: Entrega[] = [];

  for (const a of artefatos.data ?? []) {
    itens.push({
      id: `artifact:${a.id}`,
      tipo: 'documento',
      titulo: a.title || 'Documento sem título',
      detalhe: a.subtitle ?? null,
      quando: a.created_at,
      href: null, // o visualizador de artifact é da SPEC-057; ainda não há rota de tenant
      origem: a.kind ?? null,
    });
  }

  for (const b of briefings.data ?? []) {
    itens.push({
      id: `briefing:${b.id}`,
      tipo: 'documento',
      titulo: b.headline || 'Checklist do dia',
      // A honestidade que o Bloco E vai consertar: enquanto `delivery_status`
      // for 'pending', o briefing foi PUBLICADO e não ENTREGUE. Dizer o
      // contrário aqui esconderia o defeito em vez de mostrá-lo.
      detalhe: b.delivery_status === 'pending'
        ? 'Publicado — a entrega no canal ainda não aconteceu'
        : (b.summary_text ?? null),
      quando: b.published_at || b.created_at,
      href: '/dashboard/auxiliares/checklist-6h',
      origem: 'Checklist das 6h',
    });
  }

  for (const e of execucoes.data ?? []) {
    const aux = e.tenant_auxiliary_id ? nomeAux.get(e.tenant_auxiliary_id) : null;
    itens.push({
      id: `run:${e.id}`,
      tipo: 'trabalho',
      titulo: aux ? `${aux.nome} rodou` : 'Auxiliar rodou',
      detalhe: e.status === 'failed'
        ? (e.error_message || 'Falhou')
        : (e.run_type === 'manual' ? 'Execução manual' : null),
      quando: e.finished_at || e.started_at || e.created_at,
      href: aux ? `/dashboard/auxiliares/${aux.slug}` : null,
      origem: aux?.nome ?? null,
    });
  }

  for (const c of conversas.data ?? []) {
    itens.push({
      id: `conversa:${c.id}`,
      tipo: 'conversa',
      titulo: c.title || 'Conversa com o AutoBrokers',
      detalhe: c.last_message_preview ?? null,
      quando: c.updated_at || c.created_at,
      href: c.channel === 'web' || !c.channel
        ? `/dashboard/chat?session=${c.session_id ?? ''}`
        : '/dashboard/atendimentos/conversas',
      origem: c.channel === 'web' || !c.channel ? 'Chat' : 'Atendimento',
    });
  }

  for (const a of atividades.data ?? []) {
    itens.push({
      id: `atividade:${a.id}`,
      tipo: 'trabalho',
      titulo: a.title || 'Atividade',
      detalhe: a.detail ?? null,
      quando: a.created_at,
      href: null,
      origem: a.category ?? null,
    });
  }

  itens.sort((x, y) => (y.quando || '').localeCompare(x.quando || ''));

  return NextResponse.json({
    ok: true,
    itens: itens.slice(0, 400),
    // Contagem por tipo, para os filtros mostrarem números reais.
    contagem: itens.reduce<Record<string, number>>((acc, i) => {
      acc[i.tipo] = (acc[i.tipo] ?? 0) + 1;
      return acc;
    }, {}),
  });
}
