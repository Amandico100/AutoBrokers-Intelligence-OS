// TA2-A/B — config do agente (AutoBrokers/Even) para a corretora logada.
// company_id + papel resolvidos SERVER-SIDE (sessão → users_v2). PATCH exige admin
// da própria corretora. Nunca confia em body/query. Resposta sanitizada.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { decidirPatchDeAgente } from '@/lib/admin/admin-auth-policy';
import { getTenantAgentConfig, patchTenantAgentConfig, roleForKey, setTenantAgentActive } from '@/lib/admin/tenant-agent-store';
import { ativarTodosOsCorredores } from '@/lib/admin/tenant-corridor-store';
import { previaDaSaudacao } from '@/lib/admin/saudacao-religamento';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getTenantAgentConfig(auth.supabase, auth.ctx.companyId, role);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ agentKey: string }> }) {
  const { agentKey } = await params;
  const role = roleForKey(agentKey);
  if (!role) return NextResponse.json({ ok: false, error: 'agente_invalido' }, { status: 400 });
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  // 🔴 SPEC-093 BLOCO A — o portão é por CAMPO, e por isso a autorização
  // acontece DEPOIS de ler o corpo.
  //
  // `write: false` aqui resolve sessão, corretora e papel **sem** aplicar o
  // portão de escrita. Quem decide é o par (o que o corpo pede) × (o que o
  // papel pode) logo abaixo — e nenhum caminho fica sem portão.
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));

  // 🔴 SPEC-093 BLOCO A — a decisão mora em `decidirPatchDeAgente`, que é PURA
  // e é o que o gate testa. Aqui só se traduz o veredito em HTTP.
  let alternado: Awaited<ReturnType<typeof setTenantAgentActive>> | null = null;
  let alternadoCorredores: unknown = null;
  let alternadoSaudacao: unknown = null;
  const decisao = decidirPatchDeAgente({
    role: auth.ctx.role,
    isOwner: auth.ctx.isOwner,
    agentRole: role,
    camposDoCorpo: Object.keys(body ?? {}),
  });
  if (!decisao.permitido) {
    return NextResponse.json({ ok: false, error: decisao.motivo }, { status: 403 });
  }

  // SPEC-045: botão LIGAR/DESLIGAR (só attendance). Mutação isolada — não
  // mistura com variáveis/overrides.
  if (decisao.tambemAlterna) {
    // 🔴 BOOLEANO DE VERDADE, NÃO `Boolean(...)`.
    //
    // ⚠️ O painel achou: `Boolean("false") === true`. Um `PATCH
    // {"is_active":"false"}` — que é o que um formulário manda — LIGARIA o
    // agente de atendimento, e o robô voltaria a falar com segurados quando o
    // pedido dizia para calar. O guarda `typeof === 'boolean'` existia antes
    // desta SPEC e foi desfeito por ela.
    if (typeof body.is_active !== 'boolean') {
      return NextResponse.json(
        { ok: false, error: 'is_active_precisa_ser_booleano' }, { status: 400 });
    }
    const toggled = await setTenantAgentActive(
      auth.supabase, auth.ctx.companyId, role, body.is_active);
    if (!toggled.ok) return NextResponse.json(toggled, { status: 400 });

    // 🔴 SPEC-093 BLOCO G — LIGAR O ATENDIMENTO LIGA OS CORREDORES JUNTO.
    //
    // > **Decisão do Founder, 25/08:** *"na hora que a corretora ligar o
    // > atendimento, tudo pode estar ligado automaticamente. Ela pode desligar
    // > no dashboard."*
    //
    // ⚠️ Só no RELIGAMENTO (`religou`), nunca num clique que não mudou nada:
    // apertar `ligar` num agente já ligado não é evento. E `ativarTodosOsCorredores`
    // **respeita quem ela pausou à mão** — ver `corridor-bulk-decision.ts`.
    //
    // 🔴 Best-effort, e é deliberado: falhar em ligar corredor **não pode**
    // desfazer o toggle que já aconteceu. Mas sai no log, porque um "ligou tudo"
    // que ligou nada é a família de silêncio que esta SPEC existe para matar.
    //
    // 🔴 E SÓ QUEM PODE ESCREVER CONFIGURAÇÃO LIGA OS CORREDORES.
    //
    // ⚠️ **Este bloco desfazia o BLOCO A.** `ativarTodosOsCorredores` escreve
    // `corridor_templates` e `tenant_corridors` — e a rota dedicada a essa
    // escrita (`POST /api/dashboard/corridors/[templateId]`) exige
    // `requireCompanyMember({ write: true })`. Sem esta condição, o papel
    // `attendant`, criado justamente para **não** abrir a configuração,
    // instalaria 14 corredores em nome da corretora, com o id dele em
    // `installed_by`.
    //
    // 🔴 Nenhuma autoridade é inventada aqui: quem liga os corredores é quem já
    // podia ligá-los à mão. O clique da atendente liga o atendimento — e só.
    let corredores: Awaited<ReturnType<typeof ativarTodosOsCorredores>> | null = null;
    if ((toggled as { religou?: boolean }).religou && decisao.escreveConfiguracao) {
      try {
        corredores = await ativarTodosOsCorredores(
          auth.supabase, auth.ctx.companyId, auth.ctx.userId ?? '');
        if (!corredores.ok) {
          console.error('[AGENTS] corredores NAO ativados:', corredores.error);
        } else if (corredores.sem_ancora > 0) {
          // ⚠️ `ok: true` com âncoras faltando é o "ligou tudo que ligou nada".
          console.error(
            `[AGENTS] religamento ligou ${corredores.ativados} corredor(es), mas `
            + `${corredores.sem_ancora} ficaram sem âncora`);
        }
      } catch (e) {
        console.error('[AGENTS] corredores NAO ativados:', e);
      }
    }
    // 🔴 SPEC-093 BLOCO D.5 — A PRÉVIA VOLTA NO RELIGAMENTO. ⛔ NADA É ENVIADO.
    //
    // 📊 O painel achou que o BLOCO D inteiro não tinha gatilho: o serviço, a
    // migration e as duas rotas existiam, e **nenhum caminho do produto os
    // alcançava**. Um recurso pronto que ninguém chama é um recurso que não
    // existe.
    //
    // ⛔ E ela é PRÉVIA, não envio: 📊 o robô teve 4 conversas de WhatsApp em
    // toda a história do produto, e a decisão do Founder é que o primeiro
    // religamento de cada corretora **espera confirmação explícita**. Esta
    // resposta é o que a tela mostra para pedir essa confirmação.
    //
    // Best-effort pelo mesmo motivo dos corredores: falhar em montar a prévia
    // não desfaz um toggle que já aconteceu.
    let saudacao: unknown = null;
    if ((toggled as { religou?: boolean }).religou) {
      try {
        saudacao = await previaDaSaudacao(auth.ctx.companyId);
      } catch (e) {
        console.error('[AGENTS] prévia da saudação indisponível:', e);
      }
    }
    if (decisao.acao === 'toggle') {
      return NextResponse.json({ ...toggled, corredores, saudacao }, { status: 200 });
    }
    alternadoCorredores = corredores;
    alternadoSaudacao = saudacao;
    // Corpo misto: o toggle já aconteceu; a configuração segue abaixo.
    alternado = toggled;
  }

  const input = {
    variables: body.variables && typeof body.variables === 'object' ? body.variables : undefined,
    overrides: body.overrides && typeof body.overrides === 'object' ? body.overrides : undefined,
  };
  const out = await patchTenantAgentConfig(auth.supabase, auth.ctx.companyId, role, input);
  // 🔴 O CORPO MISTO DEVOLVE AS DUAS METADES.
  //
  // ⚠️ O painel achou o toggle sendo engolido em silêncio com 200 OK. Agora ele
  // acontece — e a resposta **diz que aconteceu**, senão quem clicou continua
  // sem saber.
  //
  // ⚠️ E ISSO VALE TAMBÉM QUANDO A CONFIGURAÇÃO FALHA. O juiz pegou a janela
  // que o próprio conserto abriu: no corpo misto, um erro em
  // `patchTenantAgentConfig` devolvia 400 com o toggle **já aplicado** — quem
  // clicou lê erro e o agente mudou de estado assim mesmo. É o inverso do
  // silêncio que este conserto matou, e a resposta é a mesma: **dizer o que
  // aconteceu**. Repetir o PATCH é seguro: `setTenantAgentActive` grava valor
  // absoluto, não incremento.
  const corpo = alternado
    ? { ...out, alternado, corredores: alternadoCorredores, saudacao: alternadoSaudacao }
    : out;
  return NextResponse.json(corpo, { status: out.ok ? 200 : 400 });
}
