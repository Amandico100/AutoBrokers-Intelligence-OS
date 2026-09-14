// TA2-A — store da configuração de agente por tenant (Core/Even). Server-only.
// Reusa a tabela `agents` (Smith). NÃO cria estrutura paralela. A config editável
// é mesclada em context_package + colunas reais (name/avatar/temperature) + o
// agent_system_prompt é RE-RENDERIZADO (o runtime passa a usar a config).
//
// P-36 — este era o caminho MAIS quente dos três que gravavam
// `agent_system_prompt` sem o portão de prompt vazio: é o que roda quando
// alguém salva a tela de Personalização. Ele reescreve o prompt inteiro a cada
// save, e nada conferia o que saiu nem o que o banco guardou.
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  getBlueprintByRole, computeAgentConfigUpdate, resetAgentConfigUpdate, sanitizeAgentConfigForDashboard,
  validateTenantAgentInput, TENANT_AGENT_CONFIG_NS,
  type AgentRole, type TenantAgentConfigInput,
} from '@/lib/admin/agent-blueprints-canonical';
import { getTeam } from '@/lib/admin/tenant-overview-store';
import { problemasDoUpdate, conferirPromptGravado } from '@/lib/admin/provision-tenant';
import { decidirTransicaoDoToggle } from '@/lib/admin/toggle-transicao';

// 🔴 SPEC-EXTRA-001.2 §10.5 — O NOME DA ASSISTENTE NÃO PODE SER O DE ALGUÉM DA
// EQUIPE, e quem recusa é o SERVIDOR.
//
// ⛔ Validação só no cliente não é validação: a rota é chamada por PATCH e um
// `curl` passaria por cima da tela. A comparação é NORMALIZADA (sem acento,
// sem caixa, sem espaço duplo), pelo nome completo E pelo primeiro nome —
// "Amanda" bate com "Amanda Silva", e no grupo e no dossiê ninguém saberia
// quem falou.
//
// 🔴 §7: a lista de membros vem SEMPRE da mesma corretora (`getTeam` filtra por
// `company_id`). Um membro da corretora B jamais bloqueia o nome da A.
//
// 📊 14/09/2026: **0** colisões hoje (10 membros ativos em 3 corretoras) — a
// trava nasce guardando o futuro. ⚠️ E legado colidente só AVISA: quebrar o
// save de quem já está em produção não é conserto.
/** Os diacríticos que o `NFKD` separa da letra. Escrito por CÓDIGO, nunca com
 *  o caractere combinante solto no fonte — ele é invisível num diff. */
const DIACRITICOS = new RegExp('[\\u0300-\\u036f]', 'g');

export function nomeNormalizado(nome: string | null | undefined): string {
  return String(nome ?? '')
    .normalize('NFKD').replace(DIACRITICOS, '')
    .toLowerCase().trim().replace(/\s+/g, ' ');
}

export function colisaoComAEquipe(
  nomeDoAgente: string | null | undefined,
  membros: Array<{ name?: string | null }>,
): string | null {
  const alvo = nomeNormalizado(nomeDoAgente);
  if (!alvo) return null;
  const primeiroAlvo = alvo.split(' ')[0];
  for (const m of membros ?? []) {
    const norm = nomeNormalizado(m?.name);
    if (!norm) continue;
    if (norm === alvo || norm.split(' ')[0] === primeiroAlvo) return String(m.name);
  }
  return null;
}

/** 💭 A frase que a tela mostra. Ela diz o CUSTO, não só a regra. */
export function fraseDeNomeColidente(membro: string): string {
  return `Esse nome já é de alguém da sua equipe (${membro}). Escolha outro para a `
    + 'assistente — senão, no grupo e nos dossiês, ninguém vai saber quem falou.';
}

export type AgentKey = 'autobrokers' | 'even';
export function roleForKey(key: string): AgentRole | null {
  if (key === 'autobrokers') return 'core';
  if (key === 'even') return 'attendance';
  return null;
}

const AGENT_SELECT = 'id, name, slug, is_active, avatar_url, llm_temperature, llm_model, agent_role, agent_audience, blueprint_version, context_package';

async function companyName(supabase: SupabaseClient, companyId: string): Promise<string> {
  const { data } = await supabase.from('companies').select('company_name').eq('id', companyId).maybeSingle();
  return data?.company_name ?? 'Corretora';
}

export async function getTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select(AGENT_SELECT).eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent) {
    return { ok: true as const, provisioned: false, blueprint_key: bp.blueprint_key, config: sanitizeAgentConfigForDashboard(bp, name, null), agent: null };
  }
  return {
    ok: true as const, provisioned: true, blueprint_key: bp.blueprint_key,
    agent: { id: agent.id, name: agent.name, is_active: agent.is_active, avatar_url: agent.avatar_url ?? null, llm_temperature: agent.llm_temperature ?? null, blueprint_version: agent.blueprint_version ?? null, audience: agent.agent_audience ?? null },
    config: sanitizeAgentConfigForDashboard(bp, name, agent.context_package),
  };
}

export async function patchTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole, input: TenantAgentConfigInput) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  // TA2-B — valida/sanitiza server-side ANTES de materializar (rejeita perigoso).
  const v = validateTenantAgentInput(bp, input);
  if (!v.ok) return { ok: false as const, error: 'validation_failed', errors: v.errors };

  // 🔴 §10.5 — A RECUSA DO NOME COLIDENTE, NO SERVIDOR, ANTES DA ESCRITA.
  //
  // ⚠️ Só quando o nome MUDA: o legado colidente (se existir) avisa e deixa a
  // corretora salvar as outras coisas.
  const nomePedido = String((v.clean.variables ?? {}).attendant_name ?? '').trim();
  const nomeAtual = String(
    ((agent.context_package as any)?.[TENANT_AGENT_CONFIG_NS]?.variables ?? {}).attendant_name ?? '',
  ).trim();
  let avisoDeNome: string | null = null;
  if (nomePedido) {
    const { members } = await getTeam(supabase, companyId);
    const colide = colisaoComAEquipe(nomePedido, members ?? []);
    if (colide) {
      if (nomeNormalizado(nomePedido) !== nomeNormalizado(nomeAtual)) {
        return {
          ok: false as const, error: 'nome_colide_com_a_equipe',
          membro: colide, message: fraseDeNomeColidente(colide),
        };
      }
      avisoDeNome = fraseDeNomeColidente(colide);   // legado: avisa, não bloqueia
    }
  }

  const upd = computeAgentConfigUpdate(bp, name, agent.context_package, v.clean);

  // O PORTÃO, antes da escrita. Uma personalização que se resolve para nada
  // (variável faltando, template quebrado) produziria a casca de guardrails —
  // ~560 caracteres sem uma instrução sobre o que o agente é. Recusar o save é
  // melhor que emudecer um agente que já falava.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { ok: false as const, error: 'prompt_invalido', errors: problemas };

  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };

  const conferido = await conferirPromptGravado(supabase, companyId, agent.id, 'patch_tenant_agent_config');
  if (!conferido.ok) return { ok: false as const, error: conferido.reason ?? 'prompt_vazio_apos_escrita' };

  return {
    ok: true as const, rejected: upd.rejected,
    aviso_nome: avisoDeNome,
    config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package),
  };
}

/**
 * SPEC-045 — botão LIGAR/DESLIGAR do Agente de Atendimento (agents.is_active).
 * SÓ o papel attendance é alternável (o Core/AutoBrokers fica sempre ativo).
 * DESLIGADO = modo observação: o número segue pareado, a equipe humana atende
 * e o sistema captura (Espelho). O OBSERVADOR NUNCA DESLIGA — o botão governa
 * apenas se o agente RESPONDE. O gate correspondente vive no webhook (backend).
 */
// SPEC-093 BLOCO D.1 - a decisao mora em arquivo SEM import, para o gate
// poder roda-la em `node` puro. Ver `toggle-transicao.ts`.
export async function setTenantAgentActive(
  supabase: SupabaseClient, companyId: string, role: AgentRole, isActive: boolean,
) {
  if (role !== 'attendance') return { ok: false as const, error: 'toggle_only_attendance' };
  const { data: agent } = await supabase.from('agents')
    .select('id, is_active, desligado_em')
    .eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const transicao = decidirTransicaoDoToggle(agent.is_active, isActive);
  const desligadoEmAntes: string | null = (agent as { desligado_em?: string | null }).desligado_em ?? null;

  // 🔴 SPEC-093 BLOCO D.1 — DESDE QUANDO ESTÁVAMOS FORA.
  //
  // 📊 `updated_at` **não serve**: este mesmo arquivo o reescreve em
  // `patchTenantAgentConfig`, em `resetTenantAgentConfig` e na linha abaixo. Um
  // ajuste de prompt no meio do desligamento apagaria a resposta — e a idade é
  // o que decide entre saudar a pessoa e mandar o caso para a fila humana
  // (≤12h · 12–24h · >24h nunca).
  //
  // ⚠️ Escrita **só na transição**. Religar LIMPA. E um clique que não muda
  // nada não toca na coluna: reescrever `desligado_em` a cada `desligar`
  // apertado duas vezes rejuvenesceria o desligamento, e conversas que já
  // passaram de 24h voltariam a parecer recentes.
  const campos: Record<string, unknown> = {
    is_active: isActive, updated_at: new Date().toISOString(),
  };
  if (transicao.desligou) campos.desligado_em = new Date().toISOString();
  if (transicao.religou) campos.desligado_em = null;

  const { error } = await supabase.from('agents')
    .update(campos)
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return {
    ok: true as const, is_active: isActive,
    religou: transicao.religou,
    // 🔴 09/09/2026 — quem grava o HISTÓRICO precisa saber se o clique foi
    // evento. `religou` sozinho não serve: um DESLIGAMENTO também é uma linha
    // que a corretora vai querer ler, e `religou:false` não distingue
    // "desligou agora" de "apertou num agente que já estava desligado".
    mudou: transicao.muda,
    // O valor de ANTES de limpar — é ele que diz há quanto tempo o atendimento
    // esteve fora, e quem decide a saudação precisa dele.
    desligado_em: transicao.religou ? desligadoEmAntes : (campos.desligado_em as string | null),
  };
}

export async function resetTenantAgentConfig(supabase: SupabaseClient, companyId: string, role: AgentRole) {
  const bp = getBlueprintByRole(role);
  if (!bp) return { ok: false as const, error: 'unknown_role' };
  const name = await companyName(supabase, companyId);
  const { data: agent } = await supabase.from('agents').select('id, context_package').eq('company_id', companyId).eq('agent_role', role).maybeSingle();
  if (!agent?.id) return { ok: false as const, error: 'agent_not_provisioned' };

  const upd = resetAgentConfigUpdate(bp, name, agent.context_package);

  // Voltar ao padrão também reescreve o prompt inteiro. Se o blueprint global
  // estiver quebrado, "resetar" seria o botão que apaga a voz do agente.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { ok: false as const, error: 'prompt_invalido', errors: problemas };

  const { error } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: upd.context_package, updated_at: new Date().toISOString() })
    .eq('id', agent.id).eq('company_id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };

  const conferido = await conferirPromptGravado(supabase, companyId, agent.id, 'reset_tenant_agent_config');
  if (!conferido.ok) return { ok: false as const, error: conferido.reason ?? 'prompt_vazio_apos_escrita' };

  return { ok: true as const, config: sanitizeAgentConfigForDashboard(bp, name, upd.context_package) };
}
