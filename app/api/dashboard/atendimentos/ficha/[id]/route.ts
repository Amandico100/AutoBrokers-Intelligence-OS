import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import {
  type Stage,
  dispatchStateMeta,
  isDispatchStateEncerrado,
  stageFromDispatchState,
} from '@/lib/attendance/dispatch-states';

export const dynamic = 'force-dynamic';

/**
 * SPEC-046 — Ficha do Atendimento (o dossiê vivo para o corretor).
 *
 * GET /api/dashboard/atendimentos/ficha/[id]  (id = conversation)
 * Agrega SÓ fontes existentes, zero custo novo de LLM:
 * - conversations + messages (cliente, anexos, estado);
 * - dispatch ativo no backend/Redis (estágio, protocolo, slots, dossiê real);
 * - espelho persistente do acionamento (conversa com a seguradora);
 * - attendance_sessions (resumo destilado do Espelho, quando houver);
 * - InfoCap read-only (apólice do titular, quando o CPF já foi identificado).
 * Nota/score interno NUNCA aparece (decisão do founder).
 */

// `Stage` era declarado aqui à mão — e sem `observacao`. Agora vem da lista
// canônica: quem decide o vocabulário de estágio é um arquivo só.

interface TimelineEvent {
  at: string | null;
  label: string;
  detail: string | null;
  done: boolean;
}

interface Anexo {
  id: string;
  tipo: 'imagem' | 'audio' | 'arquivo';
  url: string;
  quando: string | null;
  de: 'cliente' | 'atendente';
}

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

function internalKey(): string | null {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || null;
}

const INSURER_LABEL: Record<string, string> = {
  allianz: 'Allianz', porto: 'Porto Seguro', hdi: 'HDI', yelum: 'Yelum', tokio: 'Tokio Marine',
  alfa: 'Alfa', azul: 'Azul Seguros', bradesco: 'Bradesco Seguros', mapfre: 'Mapfre',
  zurich: 'Zurich', suhai: 'Suhai', sompo: 'Sompo', itau: 'Itaú Seguros', youse: 'Youse',
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

interface Dispatch {
  insurer_phone: string; case_id: string | null; state: string | null;
  subservice: string | null; client_phone: string | null; playbook_ref?: string | null;
  captured: Record<string, unknown>; slots?: Record<string, unknown>;
  reason?: string | null; created_at: string | null;
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const { id } = await params;
  const supabase = getSupabaseAdmin();

  const { data: conversation } = await supabase
    .from('conversations')
    .select('id, company_id, session_id, channel, status, user_phone, user_name, claimed_by, claimed_by_name, last_message_at, created_at')
    .eq('id', id)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (!conversation) return NextResponse.json({ error: 'Atendimento não encontrado' }, { status: 404 });

  const { data: messages } = await supabase
    .from('messages')
    .select('id, role, content, type, image_url, audio_url, sender_user_id, created_at')
    .eq('conversation_id', id)
    .order('created_at', { ascending: true })
    .limit(500);
  const msgs = messages || [];

  const phone = digits(conversation.user_phone);
  const isMirror = String(conversation.session_id || '').startsWith('dispatch:');

  // Acionamento ativo deste cliente (backend/Redis — estado vivo do motor)
  let dispatch: Dispatch | null = null;
  const key = internalKey();
  if (key && phone) {
    try {
      const res = await fetch(
        `${getBackendUrl()}/api/dispatch/active?company_id=${encodeURIComponent(ctx.companyId)}`,
        { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
      );
      if (res.ok) {
        const all: Dispatch[] = (await res.json())?.dispatches || [];
        dispatch = all.find((d) =>
          isMirror ? digits(d.insurer_phone) === phone : digits(d.client_phone) === phone,
        ) || null;
      }
    } catch (e) {
      if (!(e instanceof BackendUrlError)) console.error('[FICHA] dispatch fetch error');
    }
  }

  const slots = (dispatch?.slots || {}) as Record<string, string>;
  const captured = (dispatch?.captured || {}) as Record<string, unknown>;
  const protocolo = String(captured.protocol || '') || null;
  const insurer = dispatch ? insurerFromRef(dispatch.playbook_ref) : null;
  const servico = dispatch
    ? (SERVICO_LABEL[dispatch.subservice || ''] || dispatch.subservice || 'Assistência')
    : null;

  // Espelho persistente da conversa com a seguradora (link "ver acionamento")
  let espelhoConversaId: string | null = null;
  if (dispatch?.case_id && !isMirror) {
    const sessionId = `dispatch:${digits(dispatch.insurer_phone)}:${ctx.companyId}:${dispatch.case_id}`;
    const { data: mirror } = await supabase
      .from('conversations')
      .select('id')
      .eq('company_id', ctx.companyId)
      .eq('session_id', sessionId)
      .maybeSingle();
    espelhoConversaId = mirror?.id || null;
  }

  // Resumo destilado do Espelho de Atendimento (quando existir; já sem PII)
  let resumoDestilado: string | null = null;
  if (phone) {
    try {
      const { data: sess } = await supabase
        .from('attendance_sessions')
        .select('summary, last_event_at')
        .eq('company_id', ctx.companyId)
        .eq('counterparty', phone)
        .order('last_event_at', { ascending: false })
        .limit(1);
      const d = (sess?.[0]?.summary as { distilled?: Record<string, string> } | null)?.distilled;
      if (d) {
        const partes = [d.resumo || d.summary].filter(Boolean);
        if (!partes.length && (d.servico || d.tipo)) {
          partes.push(`Atendimento de ${SERVICO_LABEL[d.servico || ''] || d.servico || d.tipo}${d.desfecho ? ` — ${d.desfecho}` : ''}.`);
        }
        resumoDestilado = partes.join(' ') || null;
      }
    } catch {
      /* tabela pode não existir ainda — segue */
    }
  }

  // Estágio + resumo por regras (mesma linguagem da Fila)
  const now = Date.now();
  const lastAt = conversation.last_message_at ? new Date(conversation.last_message_at).getTime() : 0;
  const fresh = now - lastAt < 48 * 3600e3;
  let stage: Stage;
  if (dispatch) {
    stage = stageFromDispatchState(dispatch.state);
  } else if (conversation.status === 'closed') stage = 'concluido';
  else if (conversation.status === 'HUMAN_REQUESTED') stage = 'precisa_de_voce';
  else if (conversation.claimed_by) stage = 'com_equipe';
  else stage = fresh ? 'em_conversa' : 'concluido';

  let resumo = resumoDestilado;
  if (!resumo) {
    if (dispatch) {
      // A frase do estado vem do mapa canônico. Antes só DOIS estados tinham
      // frase própria aqui (`monitoring` e `needs_human`): um caso `resolvido`
      // produzia "Guincho acionado na Porto." e ponto final — o desfecho, que é
      // o que o corretor abre a ficha para saber, não era dito em lugar nenhum.
      // `captured` com número já foi dito na linha do protocolo; não se repete.
      const fraseDoEstado = dispatch.state === 'captured' && protocolo
        ? '' : ` ${dispatchStateMeta(dispatch.state).detalhe}`;
      resumo = `${servico} acionado na ${insurer}.`
        + (protocolo ? ` Protocolo ${protocolo} garantido.` : '')
        + fraseDoEstado;
    } else if (stage === 'com_equipe') {
      resumo = `${conversation.claimed_by_name || 'Alguém da equipe'} assumiu este atendimento.`;
    } else if (stage === 'precisa_de_voce') {
      resumo = 'O cliente pediu para falar com uma pessoa da corretora.';
    } else if (stage === 'em_conversa') {
      resumo = 'Conversa em andamento com o atendente.';
    } else {
      resumo = 'Atendimento encerrado — a conversa completa está disponível abaixo.';
    }
  }

  // Linha do tempo de EVENTOS (determinística: conversa + estado do motor)
  const firstMsg = msgs.find((m) => m.role === 'user');
  const timeline: TimelineEvent[] = [];
  timeline.push({
    at: firstMsg?.created_at || conversation.created_at,
    label: isMirror ? 'Acionamento aberto' : 'Cliente pediu ajuda',
    detail: null,
    done: true,
  });
  const identificado = Boolean(slots.titular_cpf || slots.titular_nome || conversation.user_name);
  if (identificado && !isMirror) {
    timeline.push({ at: null, label: 'Cliente identificado', detail: conversation.user_name || slots.titular_nome || null, done: true });
  }
  if (dispatch) {
    timeline.push({
      at: dispatch.created_at,
      label: `Acionou a ${insurer}`,
      detail: servico,
      done: true,
    });
    if (protocolo) {
      timeline.push({ at: null, label: `Protocolo ${protocolo} garantido`, detail: 'Serviço confirmado na seguradora.', done: true });
    }
    if (dispatch.state === 'monitoring') {
      timeline.push({ at: null, label: 'Prestador a caminho', detail: 'Acompanhando a chegada até o fim.', done: false });
    }
    if (dispatch.state === 'needs_human') {
      timeline.push({ at: null, label: 'Entregue à equipe', detail: dispatch.reason || 'O dossiê completo foi enviado à corretora.', done: true });
    } else if (isDispatchStateEncerrado(dispatch.state)) {
      // `encaminhado`, `resolvido` e `test_aborted` são TERMINAIS e não tinham
      // evento nenhum: a linha do tempo de um caso encerrado com sucesso parava
      // em "Acionou a Porto" e parecia trabalho travado no meio.
      const desfecho = dispatchStateMeta(dispatch.state);
      timeline.push({ at: null, label: desfecho.label, detail: desfecho.detalhe, done: true });
    }
  }
  if (conversation.claimed_by) {
    timeline.push({ at: null, label: `${conversation.claimed_by_name || 'Equipe'} assumiu`, detail: null, done: true });
  }
  if (conversation.status === 'closed') {
    timeline.push({ at: conversation.last_message_at, label: 'Atendimento concluído', detail: null, done: true });
  }

  // Anexos que o cliente (ou o atendente) enviou
  const anexos: Anexo[] = [];
  for (const m of msgs) {
    const de = m.role === 'user' ? 'cliente' as const : 'atendente' as const;
    if (m.image_url) anexos.push({ id: m.id, tipo: 'imagem', url: m.image_url, quando: m.created_at, de });
    else if (m.audio_url) anexos.push({ id: m.id, tipo: 'audio', url: m.audio_url, quando: m.created_at, de });
    else if (m.type === 'document' && m.content?.startsWith('http')) {
      anexos.push({ id: m.id, tipo: 'arquivo', url: m.content, quando: m.created_at, de });
    }
  }

  // Dossiê REAL de handoff (o mesmo texto entregue à equipe) — sessão viva
  let dossier: string | null = null;
  if (key && dispatch) {
    try {
      const res = await fetch(
        `${getBackendUrl()}/api/dispatch/dossier?company_id=${encodeURIComponent(ctx.companyId)}&insurer_phone=${encodeURIComponent(dispatch.insurer_phone)}`,
        { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
      );
      if (res.ok) dossier = (await res.json())?.dossier || null;
    } catch (e) {
      if (!(e instanceof BackendUrlError)) console.error('[FICHA] dossier fetch error');
    }
  }

  // Apólice na InfoCap (read-only, quando o CPF já foi identificado no caso)
  let apolice: Record<string, unknown> | null = null;
  const cpf = digits(slots.titular_cpf);
  if (key && cpf.length >= 11) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${getBackendUrl()}/attendance/connectors/infocap/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': key },
        body: JSON.stringify({ company_id: ctx.companyId, document: cpf, unmasked: true }),
        signal: controller.signal,
        cache: 'no-store',
      });
      clearTimeout(timer);
      if (res.ok) {
        const j = await res.json();
        const sel = j?.selected || j?.matches?.[0];
        if (j?.ok && sel) {
          apolice = {
            titular: sel.holder_name || conversation.user_name || null,
            documento: sel.document || null,
            numero: sel.policy_number || null,
            seguradora: sel.insurer_key || null,
            produto: sel.product || null,
            vigencia_de: sel.valid_from || null,
            vigencia_ate: sel.valid_to || null,
            ativa: sel.active_now ?? null,
            situacao: sel.policy_status || null,
          };
        }
      }
    } catch {
      /* InfoCap fora do ar não trava a ficha — seção fica ausente */
    }
  }

  return NextResponse.json({
    ficha: {
      conversa_id: conversation.id,
      tipo: isMirror ? 'acionamento' : 'atendimento',
      cliente: {
        nome: conversation.user_name || slots.titular_nome || null,
        telefone: phone || null,
      },
      stage,
      quando: conversation.last_message_at || conversation.created_at,
      resumo,
      resumo_fonte: resumoDestilado ? 'espelho' : 'regras',
      acionamento: dispatch ? {
        seguradora: insurer,
        servico,
        protocolo,
        estado: dispatch.state,
        espelho_conversa_id: espelhoConversaId,
      } : null,
      veiculo: (slots.veiculo_placa || slots.veiculo_descricao) ? {
        placa: slots.veiculo_placa || null,
        descricao: slots.veiculo_descricao || null,
      } : null,
      apolice,
      timeline,
      anexos,
      dossier,
      pode_assumir: !isMirror && conversation.status !== 'closed',
      assumido_por: conversation.claimed_by_name || null,
      mensagens_total: msgs.length,
    },
  });
}
