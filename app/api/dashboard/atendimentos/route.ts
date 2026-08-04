import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { getBackendUrl } from '@/lib/backend-url';
import {
  type Stage,
  dispatchStateMeta,
  stageFromDispatchState,
  zeroCountsByStage,
} from '@/lib/attendance/dispatch-states';

export const dynamic = 'force-dynamic';

/**
 * SPEC-043 — Pipeline unificado de atendimentos da corretora (mobile-first).
 *
 * GET → { items: [...], counts: {...} }
 * Junta, SEM custo de LLM (estado real do sistema):
 * - conversas cliente↔atendente (posse, aguardando humano, encerradas);
 * - acionamentos ATIVOS com a seguradora (backend/Redis);
 * - espelhos persistentes de acionamento (histórico);
 * - sessões de observação humana (Espelho — pós-pareamento).
 * Estágio calculado em linguagem humana. Score interno NUNCA é exposto.
 */

// `Stage` vem de `@/lib/attendance/dispatch-states` — a lista canônica. Ela
// morava aqui, escrita à mão, e era uma das sete cópias que deixaram
// `encaminhado` e `resolvido` órfãos no TypeScript inteiro.

interface Item {
  key: string;
  stage: Stage;
  kind: 'conversa' | 'acionamento' | 'observacao';
  titulo: string;
  detalhe: string;
  cliente: string | null;
  telefone: string | null;
  quando: string | null;
  conversa_id: string | null;
  protocolo: string | null;
}

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

const INSURER_LABEL: Record<string, string> = {
  allianz: 'Allianz', porto: 'Porto', hdi: 'HDI', yelum: 'Yelum', tokio: 'Tokio',
  alfa: 'Alfa', azul: 'Azul', bradesco: 'Bradesco', mapfre: 'Mapfre', zurich: 'Zurich',
  suhai: 'Suhai', sompo: 'Sompo', itau: 'Itaú', youse: 'Youse',
};
const SERVICO_LABEL: Record<string, string> = {
  guincho: 'Guincho', bateria: 'Bateria', pneu: 'Pneu', chaveiro: 'Chaveiro',
  eletricista: 'Eletricista', encanador: 'Hidráulica', eletrodomesticos: 'Eletrodomésticos',
  vidros: 'Vidros', sinistro: 'Sinistro', consulta: 'Consulta',
};

const insurerFromRef = (ref?: string | null): string => {
  const key = String(ref || '').split('-')[0];
  return INSURER_LABEL[key] || 'Seguradora';
};

export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const items: Item[] = [];

  // 1) Conversas cliente↔atendente (a porta de entrada de tudo)
  const { data: convs } = await supabase
    .from('conversations')
    .select('id, status, user_phone, user_name, last_message_preview, last_message_at, claimed_by, claimed_by_name, session_id')
    .eq('company_id', ctx.companyId)
    .eq('channel', 'whatsapp')
    .order('last_message_at', { ascending: false, nullsFirst: false })
    .limit(120);

  const convByPhone = new Map<string, { id: string }>();
  for (const c of convs || []) {
    const phone = digits(c.user_phone);
    if (phone && !convByPhone.has(phone)) convByPhone.set(phone, { id: c.id });
  }

  // 2) Acionamentos ATIVOS (backend/Redis — estado vivo do motor)
  type Dispatch = {
    insurer_phone: string; case_id: string | null; state: string | null;
    subservice: string | null; client_phone: string | null;
    captured: Record<string, unknown>; created_at: string | null; playbook_ref?: string | null;
  };
  let dispatches: Dispatch[] = [];
  const key = internalKey();
  if (key) {
    try {
      const res = await fetch(
        `${getBackendUrl()}/api/dispatch/active?company_id=${encodeURIComponent(ctx.companyId)}`,
        { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
      );
      // O backend responde {dispatches: [...]} — SPEC-046 corrige a chave
      // (antes lia .sessions e os acionamentos ativos nunca apareciam na Fila).
      if (res.ok) dispatches = (await res.json())?.dispatches || [];
    } catch {
      /* pipeline segue sem os ativos — fail-soft */
    }
  }

  const dispatchClientPhones = new Set<string>();
  for (const d of dispatches) {
    const clientPhone = digits(d.client_phone);
    if (clientPhone) dispatchClientPhones.add(clientPhone);
    const stage: Stage =
      d.state === 'needs_human' ? 'precisa_de_voce'
        : d.state === 'captured' ? 'protocolo'
          : d.state === 'monitoring' ? 'monitorando'
            : 'acionando';
    const insurer = insurerFromRef(d.playbook_ref);
    const servico = SERVICO_LABEL[d.subservice || ''] || d.subservice || 'Assistência';
    const protocolo = String((d.captured || {}).protocol || '') || null;
    const conv = clientPhone ? convByPhone.get(clientPhone) : undefined;
    items.push({
      key: `disp-${d.insurer_phone}-${d.case_id || ''}`,
      stage,
      kind: 'acionamento',
      titulo: `${servico} · ${insurer}`,
      detalhe:
        stage === 'precisa_de_voce' ? 'O acionamento precisa de uma pessoa — o dossiê já foi entregue à equipe.'
          : stage === 'protocolo' ? `Protocolo garantido${protocolo ? ` (${protocolo})` : ''} — serviço confirmado na seguradora.`
            : stage === 'monitorando' ? 'Serviço confirmado — acompanhando a chegada do prestador.'
              : 'Conversando com a seguradora agora para abrir o serviço.',
      cliente: null,
      telefone: clientPhone || null,
      quando: d.created_at,
      conversa_id: conv?.id || null,
      protocolo,
    });
  }

  // 3) Conversas viram itens (sem duplicar quem já está num acionamento ativo)
  const now = Date.now();
  for (const c of convs || []) {
    const phone = digits(c.user_phone);
    if (phone && dispatchClientPhones.has(phone)) continue;
    const nome = (c.user_name || '').trim() || null;
    const lastAt = c.last_message_at ? new Date(c.last_message_at).getTime() : 0;
    const fresh = now - lastAt < 48 * 3600e3;
    let stage: Stage;
    if (c.status === 'closed') stage = 'concluido';
    else if (c.status === 'HUMAN_REQUESTED') stage = 'precisa_de_voce';
    else if (c.claimed_by) stage = 'com_equipe';
    else if (fresh) stage = 'em_conversa';
    else stage = 'concluido';
    items.push({
      key: `conv-${c.id}`,
      stage,
      kind: 'conversa',
      titulo: nome || phone || 'Cliente',
      detalhe:
        stage === 'precisa_de_voce' ? 'O cliente pediu uma pessoa — assuma a conversa.'
          : stage === 'com_equipe' ? `${c.claimed_by_name || 'Alguém da equipe'} está atendendo.`
            : stage === 'em_conversa' ? (c.last_message_preview || 'Conversa em andamento com o atendente.')
              : (c.last_message_preview || 'Atendimento encerrado.'),
      cliente: nome,
      telefone: phone || null,
      quando: c.last_message_at,
      conversa_id: c.id,
      protocolo: null,
    });
  }

  // 4) Observação humana (Espelho — enche após o pareamento). Sem score.
  try {
    const { data: sess } = await supabase
      .from('attendance_sessions')
      .select('id, counterparty, status, started_at, last_event_at, summary')
      .eq('company_id', ctx.companyId)
      .order('last_event_at', { ascending: false })
      .limit(40);
    for (const s of sess || []) {
      const d = (s.summary as { distilled?: { servico?: string; tipo?: string } } | null)?.distilled;
      const servico = SERVICO_LABEL[d?.servico || ''] || d?.servico || d?.tipo || 'atendimento';
      items.push({
        key: `obs-${s.id}`,
        stage: s.status === 'open' ? 'observacao' : 'concluido',
        kind: 'observacao',
        titulo: `Atendimento da equipe · ${servico}`,
        detalhe: s.status === 'open'
          ? 'Uma atendente da corretora está conversando com o segurado agora (observado pelo sistema).'
          : 'Atendimento humano registrado pelo sistema de observação.',
        cliente: null,
        telefone: digits(s.counterparty) || null,
        quando: s.last_event_at || s.started_at,
        conversa_id: null,
        protocolo: null,
      });
    }
  } catch {
    /* tabela pode estar vazia — segue */
  }

  const counts: Record<Stage, number> = {
    precisa_de_voce: 0, acionando: 0, protocolo: 0, monitorando: 0,
    em_conversa: 0, com_equipe: 0, observacao: 0, concluido: 0,
  };
  for (const i of items) counts[i.stage] += 1;

  return NextResponse.json({ items, counts });
}
