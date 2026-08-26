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
//
// 📊 Auditoria de 04/08/2026: o `import` da lista canônica já existia aqui, mas
// as cadeias de ternários abaixo continuavam intactas — `stageFromDispatchState`,
// `dispatchStateMeta` e `zeroCountsByStage` estavam importados e NÃO usados. Um
// caso `resolvido` ainda caía em 'acionando'. Importar não é ligar.

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
    const stage: Stage = stageFromDispatchState(d.state);
    const meta = dispatchStateMeta(d.state);
    const insurer = insurerFromRef(d.playbook_ref);
    const servico = SERVICO_LABEL[d.subservice || ''] || d.subservice || 'Assistência';
    const protocolo = String((d.captured || {}).protocol || '') || null;
    const conv = clientPhone ? convByPhone.get(clientPhone) : undefined;
    items.push({
      key: `disp-${d.insurer_phone}-${d.case_id || ''}`,
      stage,
      kind: 'acionamento',
      titulo: `${servico} · ${insurer}`,
      // A frase vem do mapa canônico. O NÚMERO do protocolo saiu dela de
      // propósito: ele é dado do caso, não do estado, e já é exibido no seu
      // próprio chip pela Fila e pelo Histórico (campo `protocolo` abaixo).
      detalhe: meta.detalhe,
      cliente: null,
      telefone: clientPhone || null,
      quando: d.created_at,
      conversa_id: conv?.id || null,
      protocolo,
    });
  }

  // 2b) 🔴 SPEC-085 BLOCO E.1 — O TRAVAMENTO QUE JÁ PASSOU DAS 6h.
  //
  // ⚠️ ISTO **SOMA** À FONTE ACIMA. NÃO A SUBSTITUI, e a diferença é o bloco
  // inteiro: o Redis tem TODO acionamento em voo (`ura`, `human_phase`,
  // `monitoring`); a linha durável só nasce em `needs_human`. Trocar uma pela
  // outra tiraria da tela todo acionamento vivo — e esvaziaria o dedup
  // `dispatchClientPhones` logo acima, fazendo as conversas suprimidas
  // voltarem DUPLICADAS.
  //
  // 📊 O que a linha durável acrescenta é exatamente o que o Redis perde: o
  // TTL de `dispatch:active:*` é de 6 horas (`dispatch_router.py:66`), e um
  // travamento mais velho que isso sumia da Fila, do Vigia e de tudo.
  //
  // 🔴 E ela lê `output_redacted`, o gêmeo mascarado — nunca o payload.
  try {
    const { data: travados } = await supabase
      .from('work_runs')
      .select('id, current_step_key, error_code, error_message, created_at, input_payload')
      .eq('company_id', ctx.companyId)
      .eq('runtime_kind', 'acionamento')
      // 🔴 `assumido_por_humano` CONTINUA NA FILA — e a igualdade exata que
      // estava aqui apagava o caso no instante em que a atendente clicava.
      //
      // 📊 26/08/2026: o BLOCO C da SPEC-093 passou a gravar
      // `assumido_por_humano` quando alguém destrava pelo WhatsApp. Com
      // `.eq('travado')`, bastava a atendente mandar "só um minuto" para o
      // caso sumir da única Fila que existe — assim que o Redis expirasse
      // (TTL de 6h). E não voltava nunca: `_fechar_travamento`
      // (`dispatch_router.py:1126`) filtra `['travado','retomado_pelo_robo']`
      // de propósito, para não pisar neste estado. Terminal e invisível.
      //
      // ⚠️ É a MESMA classe de defeito que `e527705` consertou em 25/08 —
      // "o desfecho parava de apagar da Fila quem ainda espera gente" — 
      // reintroduzida por outra porta, um dia depois.
      //
      // 🔴 E o motivo de produto é o desenho do Founder: a atendente
      // DESTRAVA, ela não assume. O caso continua sendo do robô, continua
      // em voo, e continua precisando de olho.
      .in('unblock_state', ['travado', 'assumido_por_humano'])
      .order('created_at', { ascending: false })
      .limit(30);
    for (const run of (travados || []) as any[]) {
      const caseId = String(run.input_payload?.case_id || '');
      // Dedup contra a fonte quente: um travamento cuja sessão AINDA está no
      // Redis já apareceu acima, com o estágio dele. Aqui só entram os que o
      // cache perdeu.
      if (dispatches.some((d) => String(d.case_id || '') === caseId)) continue;
      const insurer = insurerFromRef(run.input_payload?.playbook_ref);
      const sub = String(run.input_payload?.subservice || '');
      items.push({
        key: `travado-${run.id}`,
        stage: 'precisa_de_voce' as Stage,
        kind: 'acionamento',
        titulo: `${SERVICO_LABEL[sub] || sub || 'Assistência'} · ${insurer}`,
        detalhe: String(run.error_message || 'O acionamento parou e precisa de uma pessoa.'),
        cliente: null,
        // ⚠️ Sem telefone: ele viria do payload cru, e esta lista não precisa
        // dele para a pessoa agir. O que ela precisa está no dossiê.
        telefone: null,
        quando: run.created_at,
        conversa_id: null,
        protocolo: null,
      });
    }
  } catch {
    /* a Fila segue com a fonte quente — fail-soft, como o bloco acima */
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

  // Zerar contador por contador à mão era a oitava lista: um estágio novo
  // nasceria sem chave aqui e o `counts[i.stage] += 1` somaria sobre `undefined`.
  const counts = zeroCountsByStage();
  for (const i of items) counts[i.stage] += 1;

  // ===========================================================================
  // 🔴 SPEC-086 BLOCO D — A PERGUNTA DA SEXTA-FEIRA
  // ===========================================================================
  //
  // > *"Dos atendimentos desta semana, quantos terminaram, quantos ainda
  // > esperam alguém, e quantos morreram esperando?"*
  //
  // ⚠️ **Sem tela nova** — a Fila já existe e já lê `unblock_state`. Ela ganha
  // três contadores, e eles são TRÊS de propósito:
  //
  // 🔴 `morreram_esperando` sai de FORA de `terminaram`. Tecnicamente `expirou`
  // também é um fim; contá-lo junto faria a sexta-feira dizer *"12 terminaram"*
  // num dia em que sete morreram esperando — e é justamente essa diferença que
  // a SPEC-086 inteira existe para criar.
  //
  // ⛔ **Falha sozinho.** Se estas duas consultas caírem, a Fila continua
  // funcionando sem os contadores — uma tela que não abre é pior que uma tela
  // sem número.
  const semana = new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString();
  let semanaResumo: Record<string, unknown> = {
    terminaram: 0, ainda_esperam: 0, morreram_esperando: 0,
    por_motivo: {}, por_kind: {}, indisponivel: true,
  };
  try {
    const [{ data: resolvidas }, { data: esperas }] = await Promise.all([
      supabase
        .from('conversations')
        .select('resolucao_motivo')
        .eq('company_id', ctx.companyId)          // 🔴 §7
        .gte('resolvido_em', semana)
        .limit(2000),
      supabase
        .from('work_waits')
        .select('kind, status')
        .eq('company_id', ctx.companyId)          // 🔴 §7
        .eq('status', 'ativo')
        .limit(2000),
    ]);

    // ⚠️ Os motivos vivem no CHECK do banco; esta lista é a MESMA, e o guarda
    //    `test_o_atendimento_termina_e_o_produto_sabe` compara as duas.
    const SUCESSO = new Set([
      'acionamento_concluido', 'encaminhado',
      'resolvido_pelo_segurado', 'fechado_por_humano',
    ]);
    const porMotivo: Record<string, number> = {};
    let terminaram = 0;
    let morreram = 0;
    for (const c of resolvidas || []) {
      const m = String((c as { resolucao_motivo?: string }).resolucao_motivo || '');
      if (!m) continue;
      porMotivo[m] = (porMotivo[m] || 0) + 1;
      if (m === 'expirou') morreram += 1;
      else if (SUCESSO.has(m)) terminaram += 1;
    }
    const porKind: Record<string, number> = {};
    for (const w of esperas || []) {
      const k = String((w as { kind?: string }).kind || '?');
      porKind[k] = (porKind[k] || 0) + 1;
    }
    semanaResumo = {
      terminaram,
      ainda_esperam: (esperas || []).length,
      morreram_esperando: morreram,
      por_motivo: porMotivo,
      por_kind: porKind,
      indisponivel: false,
    };
  } catch {
    // ⛔ `indisponivel: true` é o zero DECLARADO. Sumir com os campos faria a
    //    tela mostrar "0 terminaram" num dia em que ninguém conseguiu olhar.
    console.error('[ATENDIMENTOS] contadores da semana indisponíveis');
  }

  return NextResponse.json({ items, counts, semana: semanaResumo });
}
