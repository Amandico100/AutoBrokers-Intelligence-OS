import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';
import { projetarCasos, type Agora } from '@/lib/atendimento/casos';
import {
  type Stage,
  STAGE_META,
  dispatchStateMeta,
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

/**
 * 🔴 SPEC-097 · R8/U6.2 — TODO EVENTO TEM HORA, FONTE E `fonte_id`.
 *
 * 📊 Medido em 05/09/2026 (§1.7 / E16): **6 dos 9** tipos desta linha do tempo
 * nasciam com `at: null`. A tela mostrava "Cliente identificado" e "Ana assumiu"
 * sem hora nenhuma — e "o que aconteceu, e quando" é a pergunta que a ficha
 * existe para responder.
 *
 * ⛔ Um evento sem hora REAL não entra. Preferimos não mostrar o passo a
 * carimbar nele um horário inventado: o estado ATUAL do acionamento (protocolo
 * garantido, prestador a caminho) vive no bloco AGORA, que é onde ele é
 * verdade — não na linha do tempo, que é uma lista de coisas que aconteceram.
 *
 * `fonte` é a AUTORIDADE de onde o item veio e `fonte_id` a linha dela: sem o
 * id, ninguém consegue voltar à origem para conferir.
 */
interface TimelineEvent {
  at: string;
  label: string;
  detail: string | null;
  done: boolean;
  fonte: 'conversa' | 'corredor' | 'trabalho' | 'espera' | 'aprovacao';
  fonte_id: string;
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

/** Os cinco motivos do CHECK, ditos como uma pessoa diria. */
const MOTIVO_EM_PORTUGUES: Record<string, string> = {
  acionamento_concluido: 'o acionamento foi concluído',
  encaminhado: 'a seguradora encaminhou o atendimento',
  resolvido_pelo_segurado: 'o segurado resolveu por conta',
  fechado_por_humano: 'a equipe encerrou',
  expirou: 'o prazo expirou sem resposta',
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
    .select('id, company_id, session_id, channel, status, user_phone, user_name, claimed_by, claimed_by_name, claimed_at, last_message_at, last_message_preview, created_at, resolvido_em, resolucao_motivo')
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

  // ───────────────────────────────────────────────────────────────────────────
  // 🔴 O AGORA (U6.1) — e ele NÃO é calculado aqui.
  //
  // A ficha tinha a SUA cascata de estágio, escrita à mão, com o mesmo
  // `else 'concluido'` do relógio que a Fila tinha (§1.1). Duas telas, duas
  // cascatas, dois resultados para o mesmo atendimento. R5: uma função só.
  // ───────────────────────────────────────────────────────────────────────────
  const projecao = await projetarCasos(ctx, { conversa_id: id }, { group_by: 'stage' });
  const caso = projecao.items.find((c) => c.conversa_id === id) || projecao.items[0] || null;
  const agora: Agora | null = caso?.agora || null;

  let stage: Stage = caso?.stage || 'em_conversa';
  // O acionamento VIVO no Redis é mais recente que qualquer linha durável — ele
  // refina o estágio enquanto está em voo. ⛔ Mas nunca o ENCERRA: o desfecho é
  // escrito (R1), e um `resolvido` do motor sem `resolvido_em` no banco era
  // exatamente como 584 atendimentos apareciam encerrados sem que ninguém os
  // tivesse encerrado.
  if (dispatch && !caso?.resolvido_em) {
    const doMotor = stageFromDispatchState(dispatch.state);
    if (doMotor !== 'concluido') stage = doMotor;
  }

  let resumo = resumoDestilado;
  if (!resumo) {
    if (dispatch && !caso?.resolvido_em) {
      const fraseDoEstado = dispatch.state === 'captured' && protocolo
        ? '' : ` ${dispatchStateMeta(dispatch.state).detalhe}`;
      resumo = `${servico} acionado na ${insurer}.`
        + (protocolo ? ` Protocolo ${protocolo} garantido.` : '')
        + fraseDoEstado;
    } else {
      resumo = agora?.situacao || STAGE_META[stage]?.desc || 'Atendimento em andamento.';
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // A LINHA DO TEMPO — só o que aconteceu, e só com a hora em que aconteceu.
  // ───────────────────────────────────────────────────────────────────────────
  const timeline: TimelineEvent[] = [];
  const põe = (e: TimelineEvent | null) => { if (e && e.at) timeline.push(e); };

  const firstMsg = msgs.find((m) => m.role === 'user');
  põe({
    at: firstMsg?.created_at || conversation.created_at,
    label: isMirror ? 'Acionamento aberto' : 'O segurado pediu ajuda',
    detail: null,
    done: true,
    fonte: 'conversa',
    fonte_id: String(firstMsg?.id || conversation.id),
  });

  if (conversation.user_name && !isMirror) {
    // 🔴 a hora é a do CADASTRO da conversa — a fonte, não um palpite.
    põe({
      at: conversation.created_at,
      label: 'Segurado identificado',
      detail: conversation.user_name,
      done: true,
      fonte: 'conversa',
      fonte_id: String(conversation.id),
    });
  }

  if (dispatch?.created_at) {
    põe({
      at: dispatch.created_at,
      label: `Acionamos a ${insurer}`,
      detail: servico,
      done: true,
      fonte: 'corredor',
      fonte_id: String(dispatch.case_id || dispatch.insurer_phone),
    });
  }

  // O trabalho, a espera e a aprovação deste atendimento — cada linha tem a
  // hora dela no banco, e é ela que entra aqui.
  try {
    const [{ data: runs }, { data: esperas }] = await Promise.all([
      supabase.from('work_runs')
        .select('id, status, unblock_state, error_message, created_at')
        .eq('company_id', ctx.companyId)            // 🔴 §7
        .eq('conversation_id', id)
        .order('created_at', { ascending: true })
        .limit(50),
      supabase.from('work_waits')
        .select('id, kind, status, created_at, due_at')
        .eq('company_id', ctx.companyId)            // 🔴 §7
        .eq('conversation_id', id)
        .order('created_at', { ascending: true })
        .limit(50),
    ]);
    for (const r of (runs || []) as Record<string, string>[]) {
      if (r.status !== 'failed' && !r.unblock_state) continue;
      põe({
        at: r.created_at,
        label: 'O acionamento parou e precisou de uma pessoa',
        detail: r.error_message || null,
        done: r.unblock_state === 'assumido_por_humano',
        fonte: 'trabalho',
        fonte_id: String(r.id),
      });
    }
    for (const w of (esperas || []) as Record<string, string>[]) {
      põe({
        at: w.created_at,
        label: w.kind === 'esperando_cliente'
          ? 'Passamos a esperar o segurado'
          : w.kind === 'esperando_humano'
            ? 'Passamos a esperar alguém da equipe'
            : 'Passamos a esperar a seguradora',
        detail: w.due_at ? `Prazo combinado: ${new Date(w.due_at).toLocaleString('pt-BR')}.` : null,
        done: w.status !== 'ativo',
        fonte: 'espera',
        fonte_id: String(w.id),
      });
    }
  } catch {
    /* a ficha abre sem estes eventos — fail-soft */
  }

  if (conversation.claimed_by && conversation.claimed_at) {
    põe({
      at: conversation.claimed_at,
      label: `${conversation.claimed_by_name || 'Alguém da equipe'} assumiu o atendimento`,
      detail: null,
      done: true,
      fonte: 'conversa',
      fonte_id: String(conversation.id),
    });
  }

  // 🔴 R1 — o fim é o `resolvido_em` ESCRITO, com o motivo que alguém declarou.
  //    Era `conversation.status === 'closed'` com a hora da última mensagem.
  if (conversation.resolvido_em) {
    põe({
      at: conversation.resolvido_em,
      label: 'Atendimento encerrado',
      detail: MOTIVO_EM_PORTUGUES[String(conversation.resolucao_motivo || '')] || null,
      done: true,
      fonte: 'conversa',
      fonte_id: String(conversation.id),
    });
  }

  timeline.sort((a, b) => String(a.at).localeCompare(String(b.at)));

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
      // 🔴 U6.1 — as SEIS dimensões do AGORA, prontas para a tela. Elas saem da
      //    projeção (R5), então a Ficha e a Fila NUNCA discordam sobre o mesmo
      //    atendimento — que era o que acontecia com duas cascatas.
      agora,
      parado_ha: caso?.parado_ha || null,
      resolvido_em: caso?.resolvido_em || null,
      resolucao_motivo: caso?.resolucao_motivo || null,
      desfecho_em_portugues: caso?.resolucao_motivo
        ? MOTIVO_EM_PORTUGUES[String(caso.resolucao_motivo)] || null
        : null,
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
      pode_assumir: !isMirror && !conversation.resolvido_em,
      // ⛔ E3 — a Ficha ganha o mesmo botão Encerrar de Conversas, e ele
      //    PERGUNTA o motivo. Encerrar só faz sentido uma vez: quem já tem
      //    desfecho escrito não termina de novo.
      pode_encerrar: !isMirror && !conversation.resolvido_em,
      assumido_por: conversation.claimed_by_name || null,
      mensagens_total: msgs.length,
    },
  });
}
