/**
 * Os acionamentos travados, e os dois botões que os destravam — SPEC-085 BLOCO E.
 *
 * GET  → { travados: [...] }
 * POST → { action: 'assumir' | 'arquivar', run_id, motivo? }
 *
 * ## Por que esta rota existe
 *
 * 📊 Antes dela, `backend/app/api/dispatch_monitor.py` tinha **52 linhas e só
 * GET**; `app/admin/acionamentos/page.tsx` era leitura pura; e
 * `admin_spec034.py` não tinha POST de sessão.
 *
 * > **O único destravamento humano do produto era o do PORTAL.
 * > O acionamento não tinha nenhum.**
 *
 * 📊 E o resultado media-se em zero: `work_events` com `run.resumed` /
 * `run.paused` / `approval.*` / `step.retried` → **0**, em 26.803 eventos.
 * `work_runs.paused_at IS NOT NULL` → 0. `human_review_tasks` → 0 linhas.
 * **Ninguém nunca destravou nada — e não é que a retomada falhou: ela não
 * tinha como ser registrada.**
 *
 * ## 🔴 ELA LÊ O GÊMEO MASCARADO, NUNCA O PAYLOAD
 *
 * `work_steps.output_summary` é o **payload de restauração** da sessão:
 * `_ultimo_retrato` → `sessao_restaurada` → `render_reply` → a URA. Ele guarda
 * CPF, telefone e endereço em claro, porque a URA precisa deles.
 *
 * `work_steps.output_redacted` é o gêmeo que a FASE 1 criou **para esta tela**:
 * mesma informação de triagem — corredor, serviço, motivo completo, quais slots
 * faltaram — com a PII mascarada. Quem escrever leitura nova aqui usa o gêmeo.
 *
 * ## A referência é o portal, que já fez isto
 *
 * `POST /api/dashboard/portal-jobs` com `retry|archive`, e a regra espelhada em
 * `lib/portal/hitl.ts` ↔ `backend/portal_worker/guardrails.py`. Mesma forma de
 * autenticação, mesmo escopo por corretora, mesma exigência de mesma origem.
 */
import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { assertSameOrigin } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';

const RUN_SELECT =
  'id, company_id, status, unblock_state, current_step_key, error_code, ' +
  'error_message, owner_user_id, input_payload, created_at, updated_at';

/** Os estados que a §F0.1 declarou, e o CHECK do banco garante. */
const TRAVADO = 'travado';
const ASSUMIDO = 'assumido_por_humano';
const ABANDONADO = 'abandonado';

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const limit = Math.min(Math.max(Number(req.nextUrl.searchParams.get('limit') || 20), 1), 50);
  // Por padrão só o que está esperando gente. `?estado=all` mostra o histórico
  // de quem já foi assumido ou arquivado — é o que responde "e depois?".
  const estado = req.nextUrl.searchParams.get('estado') || TRAVADO;

  let q = supabase
    .from('work_runs')
    .select(RUN_SELECT)
    // 🔴 O filtro por corretora é do REPOSITORY, não da RLS. O backend usa
    // service role, e `CLAUDE.md` §7 é literal: "RLS sem policy não protege
    // nada contra erro de filtro no código".
    .eq('company_id', ctx.companyId)
    .eq('runtime_kind', 'acionamento')
    .not('unblock_state', 'is', null)
    .order('created_at', { ascending: false })
    .limit(limit);
  if (estado !== 'all') q = q.eq('unblock_state', estado);

  const { data, error } = await q;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const runs = (data || []) as any[];
  if (!runs.length) return NextResponse.json({ travados: [] });

  // 🔴 O GÊMEO, e só ele. Pedir `output_summary` aqui traria CPF e telefone
  // em claro para uma tela — e a coluna ao lado existe exatamente para isso
  // não precisar acontecer.
  const { data: etapas } = await supabase
    .from('work_steps')
    .select('work_run_id, step_key, output_redacted, finished_at')
    .in('work_run_id', runs.map((r) => r.id))
    .eq('company_id', ctx.companyId)
    .order('finished_at', { ascending: false });

  const retrato: Record<string, any> = {};
  for (const etapa of (etapas || []) as any[]) {
    const id = String(etapa.work_run_id);
    if (!retrato[id]) retrato[id] = etapa.output_redacted || {};
  }

  return NextResponse.json({
    travados: runs.map((run) => {
      const r = retrato[String(run.id)] || {};
      return {
        run_id: run.id,
        estado: run.unblock_state,
        fase: run.current_step_key,
        // O motivo COMPLETO — `missing_slots:titular_cpf,local_seguro` —, que é
        // o que diz à pessoa o que falta, e não só que faltou algo.
        motivo: String(run.error_code || '').replace(/^needs_human:/, ''),
        recado: run.error_message,
        corredor: r.playbook_ref ?? run.input_payload?.playbook_ref ?? null,
        servico: r.subservice ?? run.input_payload?.subservice ?? null,
        faltaram: r.missing_slots ?? [],
        // `ausente` | `recusado` | `envio_falhou` — três instruções diferentes
        // para a corretora, e por isso três valores (BLOCO B.3).
        suporte: r.suporte_indisponivel ?? null,
        assumido_por: run.owner_user_id,
        travado_em: run.created_at,
        mexido_em: run.updated_at,
      };
    }),
  });
}

export async function POST(req: NextRequest) {
  const sameOrigin = assertSameOrigin(req);
  if (sameOrigin) return NextResponse.json({ error: sameOrigin.error }, { status: sameOrigin.status });

  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const action = String(body?.action || '');
  const runId = String(body?.run_id || '');
  const motivo = String(body?.motivo || '').trim();

  // 🔴 DOIS BOTÕES, E NÃO MAIS QUE DOIS (§E.2). Cada botão a mais é uma decisão
  // que alguém precisa tomar com o segurado esperando.
  if (!['assumir', 'arquivar'].includes(action) || !runId) {
    return NextResponse.json(
      { error: 'action=assumir|arquivar e run_id sao obrigatorios' },
      { status: 400 },
    );
  }
  // ⚠️ Arquivar é dizer "ninguém vai continuar isto". Sem motivo escrito, o
  // caso some e ninguém sabe por quê — que é o defeito que a SPEC ataca, com
  // outro nome.
  if (action === 'arquivar' && motivo.length < 3) {
    return NextResponse.json(
      { error: 'arquivar exige um motivo escrito' },
      { status: 400 },
    );
  }

  const supabase = getSupabaseAdmin();
  const agora = new Date().toISOString();

  if (action === 'assumir') {
    // 🔴 ATÔMICO. O `.eq('unblock_state', TRAVADO)` é o que impede duas
    // atendentes de assumirem o mesmo caso — mesma escolha do `claim` de
    // conversa, que devolve 409 quando outro humano chegou primeiro.
    const { data, error } = await supabase
      .from('work_runs')
      .update({ unblock_state: ASSUMIDO, owner_user_id: ctx.userId ?? null, updated_at: agora })
      .eq('id', runId)
      .eq('company_id', ctx.companyId)
      .eq('unblock_state', TRAVADO)
      .select('id')
      .maybeSingle();
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
    if (!data) {
      return NextResponse.json(
        { error: 'Este acionamento ja foi assumido ou arquivado por outra pessoa.' },
        { status: 409 },
      );
    }
    await registrarEvento(supabase, ctx.companyId, runId, 'run.resumed',
      'Uma pessoa da corretora assumiu este acionamento travado.');
    return NextResponse.json({ ok: true, estado: ASSUMIDO });
  }

  const { data, error } = await supabase
    .from('work_runs')
    .update({
      unblock_state: ABANDONADO,
      owner_user_id: ctx.userId ?? null,
      status: 'cancelled',
      finished_at: agora,
      updated_at: agora,
      result_summary: `Arquivado por uma pessoa da corretora. Motivo: ${motivo}`.slice(0, 400),
    })
    .eq('id', runId)
    .eq('company_id', ctx.companyId)
    .in('unblock_state', [TRAVADO, ASSUMIDO])
    .select('id')
    .maybeSingle();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  if (!data) {
    return NextResponse.json(
      { error: 'Este acionamento ja foi arquivado, ou nao esta travado.' },
      { status: 409 },
    );
  }
  await registrarEvento(supabase, ctx.companyId, runId, 'run.cancelled',
    `Arquivado pela corretora. Motivo: ${motivo}`);
  return NextResponse.json({ ok: true, estado: ABANDONADO });
}

/**
 * 🔴 O destravamento vira LINHA DO TEMPO, não só uma coluna.
 *
 * 📊 `work_events` tinha **zero** eventos de retomada em 26.803 registros. A
 * coluna diz o estado de agora; a linha do tempo diz o que aconteceu — e é ela
 * que responde "quem assumiu, e quando?" seis meses depois.
 *
 * Best-effort: falhar aqui não pode desfazer o destravamento que já aconteceu.
 *
 * ⚠️ 🔴 MAS A FALHA APARECE. A primeira versão desta função escrevia `run_id`,
 * `message` e omitia `actor_type`/`payload_redacted` — três erros de nome
 * contra o schema real (`work_run_id`, `message_human`, e os dois `NOT NULL`).
 * Dentro de um `catch {}` mudo, isso seria **um registro que nunca acontece e
 * ninguém descobre** — a mesma família do `dossier_sent = True` incondicional.
 * Um `catch` que não conta nada é uma flag que mente com outro nome.
 */
async function registrarEvento(
  supabase: ReturnType<typeof getSupabaseAdmin>,
  companyId: string,
  runId: string,
  tipo: string,
  mensagem: string,
) {
  try {
    const { error } = await supabase.from('work_events').insert({
      work_run_id: runId,
      company_id: companyId,
      event_type: tipo,
      actor_type: 'human',
      severity: 'info',
      message_human: mensagem,
      payload_redacted: {},
    });
    if (error) {
      console.error('[acionamentos-travados] evento NAO registrado:', error.message);
    }
  } catch (e) {
    console.error('[acionamentos-travados] evento NAO registrado:', e);
  }
}
