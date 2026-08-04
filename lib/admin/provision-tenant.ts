// SPEC-063 Bloco P — a corretora nasce COMPLETA, e nenhum agente nasce mudo.
//
// Server-only. Idempotente. Reusa a tabela `agents` (Smith), o Capability
// Registry, `memory_settings` e `briefing_profiles` que já existem. NÃO cria
// motor paralelo: não há segundo provisionador, segundo registry, segunda
// memória (CLAUDE.md §5).
//
// O QUE ESTAVA ERRADO
// -------------------
// 📊 Medido em 02/08/2026 no banco de produção
// (`docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md`, Parte C.6):
//
//     corretora    agentes  prompt vazio  memória  entitlements  briefing
//     Amandus         2          0           0          0            2
//     AutoFleet       2         *1*          0          0            2
//     Resulta         2          0           0          0            2
//
// Nada era uniforme exceto agentes e perfis de briefing. E a AutoFleet tinha
// um agente CORE **ATIVO com prompt de ZERO caracteres**, saído do mesmo
// blueprint `autobrokers-core-v1` que rendeu 650 caracteres na Resulta.
//
// Três falhas estruturais, e este arquivo responde às três:
//
//   a) `ensureAgentByRole` devolvia `{action:'exists'}` e NUNCA atualizava —
//      melhoria no blueprint global jamais chegava em corretora existente.
//      → agora `exists` passa pela cura: o que está VAZIO é preenchido.
//
//   b) o mecanismo que faria isso (`agent_release_rollouts`) tem 1 linha, e ela
//      está `rolled_back`. → a herança vive aqui, no mesmo caminho que cria.
//
//   c) o provisionamento podia produzir agente mudo e nada percebia.
//      → o prompt é validado ANTES do insert e RELIDO DO BANCO depois dele.
//        Prompt vazio deixa de ser um estado possível: é erro, e o agente
//        criado mudo nasce DESLIGADO em vez de ativo e sem instrução.
//
// A REGRA DURA DA HERANÇA (não é negociável)
// ------------------------------------------
//     preenche o que está VAZIO
//     versiona ANTES de tocar no que está PREENCHIDO
//     nunca sobrescreve sem registro
//
// 📊 A Amandus tem um prompt de 7.914 caracteres editado à mão. Perder isso é
// inaceitável — por isso o versionamento é uma ESCRITA SEPARADA, confirmada por
// releitura, e o prompt novo só é gravado depois dela. Se o versionamento
// falhar, o texto antigo continua no lugar (fail-closed).
import type { SupabaseClient } from '@supabase/supabase-js';
import { createHash } from 'node:crypto';
import {
  AUTOBROKERS_CORE_BLUEPRINT, EVEN_ATTENDANCE_BLUEPRINT,
  computeAgentConfigUpdate, renderTemplate, resolveEffectiveConfig,
  type AgentRole, type CanonicalBlueprint,
} from '@/lib/admin/agent-blueprints-canonical';
import { extractSavedTenantInput } from '@/lib/admin/release-rollout';
import { CAPABILITY_CATALOG } from '@/lib/capabilities/registry';
import { getCompanyKind } from '@/lib/admin/company-kind-store';
import { isPlatformCompany } from '@/lib/admin/company-kind';

// ---------------------------------------------------------------------------
// 1. O PORTÃO: prompt vazio é IMPOSSÍVEL
// ---------------------------------------------------------------------------

/** Prompt final composto (personalização + guardrails). O real hoje passa de 1.200. */
export const PROMPT_MINIMO_CHARS = 400;
/** Só a parte personalizada. O real hoje passa de 600. */
export const PERSONALIZACAO_MINIMA_CHARS = 120;

const PLACEHOLDER_PENDENTE = /\{\{\s*[a-z0-9_]+\s*\}\}/i;

/**
 * Por que DUAS medidas e não só "prompt não vazio".
 *
 * `composeSystemPromptWithGuardrails('')` devolve um texto de ~560 caracteres
 * cheio de cabeçalhos e regras — e nenhuma instrução sobre o que o agente é ou
 * faz. Um agente com essa casca passa em qualquer checagem de "não vazio" e
 * continua mudo na prática. A personalização é medida separadamente por isso.
 *
 * Devolve a lista de problemas. Vazia = pode gravar.
 */
export function problemasDoPrompt(promptFinal: string, personalizado: string): string[] {
  const problemas: string[] = [];
  const final = String(promptFinal ?? '').trim();
  const pessoal = String(personalizado ?? '').trim();

  if (!final) problemas.push('prompt_vazio');
  else if (final.length < PROMPT_MINIMO_CHARS) problemas.push(`prompt_curto_demais:${final.length}`);

  if (!pessoal) problemas.push('personalizacao_vazia');
  else if (pessoal.length < PERSONALIZACAO_MINIMA_CHARS) problemas.push(`personalizacao_curta:${pessoal.length}`);

  // `{{company_name}}` sobrando significa que a variável não chegou: o agente
  // se apresentaria com as chaves literais na frente do corretor.
  if (final && PLACEHOLDER_PENDENTE.test(final)) problemas.push('placeholder_nao_resolvido');

  return problemas;
}

/** A parte personalizada do prompt (sem o bloco de guardrails). */
function personalizacaoDe(bp: CanonicalBlueprint, variaveis: Record<string, string>): string {
  return renderTemplate(bp.system_prompt_template, variaveis);
}

/**
 * O MESMO portão, aplicado ao resultado de `computeAgentConfigUpdate` /
 * `resetAgentConfigUpdate`.
 *
 * P-36 — este arquivo tinha o portão e o usava; três outros caminhos escreviam
 * `agents.agent_system_prompt` sem passar por ele (`tenant-agent-store`,
 * `release-rollout-store`, `blueprint-studio-store`). Ter o portão em um
 * caminho e não nos outros é o mesmo que não ter portão: 📊 a AutoFleet ficou
 * com um agente CORE **ativo e de prompt zero** (auditoria de 02/08/2026,
 * `docs/canon/reports/SPEC-063-BLOCO-0-AUDITORIA.md`, Parte C.6) saindo do
 * mesmo blueprint que rendeu 650 caracteres na Resulta.
 *
 * Existe para que ninguém precise reconstruir o par (prompt final,
 * personalização) na mão — foi reconstruí-lo errado, ou não reconstruí-lo,
 * que abriu os três furos.
 */
export function problemasDoUpdate(
  bp: CanonicalBlueprint,
  upd: { columns: Record<string, unknown>; effective: { variables_used: Record<string, string> } },
): string[] {
  return problemasDoPrompt(
    String(upd.columns.agent_system_prompt ?? ''),
    personalizacaoDe(bp, upd.effective.variables_used),
  );
}

/**
 * O portão para prompt de AUTORIA (Blueprint Studio).
 *
 * Aqui `{{placeholder}}` NÃO é defeito — é o ponto: o Source Agent guarda o
 * template, e quem resolve as variáveis é a materialização por corretora. E
 * nada soma a casca de guardrails por cima, então a medida dupla de
 * `problemasDoPrompt` (que existe justamente porque a casca vazia já tem ~560
 * caracteres) não se aplica. O que sobra, e é o que mata, é o VAZIO.
 *
 * E aqui o vazio custa mais caro que numa corretora: um Source Agent mudo vira
 * release, e a release desce para TODAS as corretoras que a receberem.
 */
export function problemasDoPromptDeAutoria(prompt: string, minimoChars: number): string[] {
  const texto = String(prompt ?? '').trim();
  if (!texto) return ['prompt_de_autoria_vazio'];
  if (texto.length < minimoChars) return [`prompt_de_autoria_curto:${texto.length}`];
  return [];
}

/**
 * Relê do BANCO o que ficou gravado e DESLIGA o agente se ele ficou mudo.
 *
 * Era a verificação que não existia em 02/08/2026: o agente era escrito e o
 * resultado nunca era conferido. Trigger, default de coluna, RPC que ignora um
 * campo ou coluna truncada aparecem aqui — não na primeira conversa do
 * segurado. "Gravei" tem de ser afirmação sobre um fato lido de volta, não
 * sobre uma requisição enviada.
 *
 * Silêncio é melhor que um agente ativo sem uma linha de instrução e sem
 * nenhuma trava — por isso a consequência é desligar, não só reportar.
 */
export async function conferirPromptGravado(
  supabase: SupabaseClient, companyId: string, agentId: string, origem: string,
): Promise<{ ok: boolean; chars: number; reason?: string }> {
  const { data } = await supabase.from('agents')
    .select('agent_system_prompt').eq('id', agentId).eq('company_id', companyId).maybeSingle();
  const gravado = String((data as { agent_system_prompt?: string | null } | null)?.agent_system_prompt ?? '');
  if (gravado.trim()) return { ok: true, chars: gravado.length };

  await supabase.from('agents')
    .update({ is_active: false, agent_enabled: false, updated_at: new Date().toISOString() })
    .eq('id', agentId).eq('company_id', companyId);
  return { ok: false, chars: 0, reason: `prompt_vazio_apos_escrita:${origem}:agente_desligado` };
}

// ---------------------------------------------------------------------------
// 2. Materialização do agente a partir do blueprint
// ---------------------------------------------------------------------------

export interface AgenteMaterializado {
  payload: Record<string, unknown>;
  prompt: string;
  problemas: string[];
}

/** Monta o insert do agente E diz se o prompt resultante é utilizável. */
export function materializarAgente(
  companyId: string, companyName: string, bp: CanonicalBlueprint, slug: string,
): AgenteMaterializado {
  const eff = resolveEffectiveConfig({ blueprint: bp, company_name: companyName });
  const problemas = problemasDoPrompt(eff.system_prompt, personalizacaoDe(bp, eff.variables_used));
  return {
    prompt: eff.system_prompt,
    problemas,
    payload: {
      company_id: companyId,
      name: bp.brand_locked_name ?? bp.default_display_name, // canônico; apresentação vem do prompt/runtime
      slug,
      is_active: bp.default_active,
      agent_enabled: true,
      llm_provider: eff.llm_provider,
      llm_model: eff.llm_model,
      agent_system_prompt: eff.system_prompt,
      is_subagent: bp.is_subagent,
      allow_direct_chat: bp.allow_direct_chat,
      agent_role: bp.role,
      agent_audience: bp.audience,
      blueprint_version: bp.blueprint_key,
      allow_vision: bp.role === 'attendance',
      security_settings: { enabled: false },
    },
  };
}

// ---------------------------------------------------------------------------
// 3. Versionamento — nada preenchido é tocado sem registro
// ---------------------------------------------------------------------------

export const HERANCA_NS = 'blueprint_heranca';
/** Teto do histórico. A PRIMEIRA versão nunca é descartada — é a que mais custa. */
export const MAX_VERSOES = 10;

export interface VersaoDoPrompt {
  gravado_em: string;
  motivo: string;
  blueprint_key: string;
  chars: number;
  sha256_12: string;
  agent_system_prompt: string;
  /** O nome exibido também é trabalho da corretora — some junto se ninguém guardar. */
  name?: string | null;
}

export function hashCurto(texto: string): string {
  return createHash('sha256').update(String(texto ?? '')).digest('hex').slice(0, 12);
}

/**
 * Devolve um `context_package` novo com o prompt anterior arquivado. PURO:
 * não escreve nada — quem escreve é `reaplicarBlueprintGlobal`, e só grava o
 * prompt novo DEPOIS de confirmar que este registro entrou no banco.
 */
export function registrarVersaoDoPrompt(
  contextPackage: unknown,
  entrada: { prompt: string; motivo: string; blueprint_key: string; agora?: string; name?: string | null },
): Record<string, unknown> {
  const cp: Record<string, unknown> = (contextPackage && typeof contextPackage === 'object' && !Array.isArray(contextPackage))
    ? { ...(contextPackage as Record<string, unknown>) } : {};
  const anterior = cp[HERANCA_NS] as { versoes?: unknown } | undefined;
  const versoes: VersaoDoPrompt[] = Array.isArray(anterior?.versoes) ? [...(anterior!.versoes as VersaoDoPrompt[])] : [];

  const texto = String(entrada.prompt ?? '');
  versoes.push({
    gravado_em: entrada.agora ?? new Date().toISOString(),
    motivo: entrada.motivo,
    blueprint_key: entrada.blueprint_key,
    chars: texto.length,
    sha256_12: hashCurto(texto),
    agent_system_prompt: texto,
    name: entrada.name ?? null,
  });

  // Corta pelo MEIO: o índice 0 é o texto original da corretora (na Amandus,
  // 7.914 caracteres escritos à mão). Ele fica, custe o que custar.
  if (versoes.length > MAX_VERSOES) versoes.splice(1, versoes.length - MAX_VERSOES);

  cp[HERANCA_NS] = {
    blueprint_key: entrada.blueprint_key,
    ultima_aplicacao: entrada.agora ?? new Date().toISOString(),
    ultimo_motivo: entrada.motivo,
    versoes,
  };
  return cp;
}

/** Marca a aplicação da herança sem arquivar nada (usado quando o campo estava VAZIO). */
export function marcarHerancaAplicada(
  contextPackage: unknown,
  entrada: { motivo: string; blueprint_key: string; agora?: string },
): Record<string, unknown> {
  const cp: Record<string, unknown> = (contextPackage && typeof contextPackage === 'object' && !Array.isArray(contextPackage))
    ? { ...(contextPackage as Record<string, unknown>) } : {};
  const anterior = cp[HERANCA_NS] as { versoes?: unknown } | undefined;
  cp[HERANCA_NS] = {
    blueprint_key: entrada.blueprint_key,
    ultima_aplicacao: entrada.agora ?? new Date().toISOString(),
    ultimo_motivo: entrada.motivo,
    versoes: Array.isArray(anterior?.versoes) ? anterior!.versoes : [],
  };
  return cp;
}

// ---------------------------------------------------------------------------
// 4. Contratos de saída
// ---------------------------------------------------------------------------

export type AcaoAgente = 'exists' | 'created' | 'healed' | 'error';
export interface ResultadoAgente { id: string | null; action: AcaoAgente; reason?: string }

export type AcaoPeca = 'criado' | 'existente' | 'parcial' | 'ignorado' | 'erro';
export interface ResultadoPeca {
  peca: string;
  acao: AcaoPeca;
  quantidade?: number;
  criados?: number;
  motivo?: string;
}

export interface ProvisionResult {
  ok: boolean;
  company_id: string;
  error?: string; // lido por app/api/admin/companies/route.ts
  core: ResultadoAgente;
  attendance: ResultadoAgente;
  pecas: ResultadoPeca[];
  completa: boolean;
  faltando: string[];
}

const AGENTE_SELECT = 'id, name, agent_system_prompt, context_package, is_active';

/**
 * A mesma regra do prompt vale para o NOME exibido. `computeAgentConfigUpdate`
 * devolve `name` para os blueprints sem marca travada (o de atendimento): se a
 * corretora renomeou o atendente direto na coluna, reaplicar o global o
 * chamaria de "Even" de novo — perda silenciosa de trabalho de alguém.
 *
 * Preenchido só é tocado com autorização, e aí vai versionado junto.
 */
export function semRenomear(
  columns: Record<string, unknown>, nomeAtual: string | null | undefined,
): Record<string, unknown> {
  if (!String(nomeAtual ?? '').trim()) return columns; // sem nome: pode nomear
  const { name: _preservado, ...resto } = columns;
  return resto;
}

// ---------------------------------------------------------------------------
// 5. O agente: cria, verifica o que gravou, e cura o que está vazio
// ---------------------------------------------------------------------------

async function curarAgenteExistente(
  supabase: SupabaseClient, companyId: string, bp: CanonicalBlueprint, companyName: string,
  existente: { id: string; name: string | null; agent_system_prompt: string | null; context_package: unknown },
): Promise<ResultadoAgente> {
  const atual = String(existente.agent_system_prompt ?? '');
  // Preenchido: NÃO se toca aqui. Reaplicar sobre texto existente só por
  // `reaplicarBlueprintGlobal`, que versiona antes.
  if (atual.trim()) return { id: existente.id, action: 'exists' };

  const salvo = extractSavedTenantInput(existente.context_package);
  const upd = computeAgentConfigUpdate(bp, companyName, existente.context_package, salvo);
  const novo = String(upd.columns.agent_system_prompt ?? '');
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) return { id: existente.id, action: 'error', reason: `blueprint_invalido:${problemas.join(',')}` };

  const cp = marcarHerancaAplicada(upd.context_package, {
    motivo: 'preenchimento_de_prompt_vazio', blueprint_key: bp.blueprint_key,
  });
  const { error } = await supabase.from('agents')
    .update({ ...semRenomear(upd.columns, existente.name), context_package: cp, updated_at: new Date().toISOString() })
    .eq('id', existente.id).eq('company_id', companyId);
  if (error) return { id: existente.id, action: 'error', reason: 'cura_falhou' };
  return { id: existente.id, action: 'healed', reason: `prompt_preenchido:${novo.length}` };
}

async function ensureAgentByRole(
  supabase: SupabaseClient, companyId: string, companyName: string, bp: CanonicalBlueprint, slug: string,
): Promise<ResultadoAgente> {
  try {
    // FAIL-CLOSED, antes de qualquer escrita: se o blueprint resolve para um
    // prompt inutilizável, o provisionamento PARA. Não existe "cria e vê depois".
    const material = materializarAgente(companyId, companyName, bp, slug);
    if (material.problemas.length) {
      return { id: null, action: 'error', reason: `prompt_invalido:${material.problemas.join(',')}` };
    }

    const { data: existing, error: lookupErr } = await supabase
      .from('agents').select(AGENTE_SELECT).eq('company_id', companyId).eq('agent_role', bp.role).limit(1).maybeSingle();
    if (lookupErr) return { id: null, action: 'error', reason: lookupErr.code ?? 'lookup_failed' };
    if (existing?.id) {
      return curarAgenteExistente(supabase, companyId, bp, companyName, existing as any);
    }

    // slug único por sufixo se já houver colisão de slug.
    let useSlug = slug;
    const { data: slugHit } = await supabase.from('agents').select('id').eq('company_id', companyId).eq('slug', slug).maybeSingle();
    if (slugHit?.id) useSlug = `${slug}-${Date.now().toString(36).slice(-4)}`;

    const payload = { ...material.payload, slug: useSlug };
    const { data, error } = await supabase.from('agents').insert(payload).select('id, agent_system_prompt').single();
    if (error || !data) return { id: null, action: 'error', reason: error?.message ?? 'insert_failed' };

    // VERIFICAÇÃO PÓS-CRIAÇÃO — o que faltava em 02/08/2026.
    // Lê de volta o que o BANCO guardou (não o que mandamos). Trigger, default
    // ou coluna truncada aparecem aqui, e não na primeira conversa do segurado.
    const gravado = String((data as { agent_system_prompt?: string | null }).agent_system_prompt ?? '');
    if (!gravado.trim()) {
      // Agente mudo NÃO fica ativo. Silêncio é melhor que um agente ativo sem
      // uma linha de instrução e sem nenhuma trava.
      await supabase.from('agents')
        .update({ is_active: false, agent_enabled: false, updated_at: new Date().toISOString() })
        .eq('id', data.id).eq('company_id', companyId);
      return { id: data.id, action: 'error', reason: 'prompt_vazio_apos_insert:agente_desligado' };
    }
    return { id: data.id, action: 'created' };
  } catch (e: any) {
    return { id: null, action: 'error', reason: String(e?.message ?? 'exception').slice(0, 60) };
  }
}

// ---------------------------------------------------------------------------
// 6. As peças que faltavam para a corretora nascer completa
// ---------------------------------------------------------------------------

/**
 * Config de memória por agente. 📊 0 linhas nas três corretoras — o agente
 * rodava com o default implícito do código, e a tela de memória criava a linha
 * só quando alguém abria a tela.
 *
 * NÃO inventa política: grava apenas `agent_id` + `company_id` e deixa os
 * DEFAULTS da coluna decidirem o resto. Escolher aqui um valor diferente do que
 * a tela grava criaria uma terceira verdade sobre memória.
 */
async function garantirConfigDeMemoria(
  supabase: SupabaseClient, companyId: string, agentIds: string[],
): Promise<ResultadoPeca> {
  if (!agentIds.length) return { peca: 'memoria', acao: 'ignorado', motivo: 'sem_agente' };
  try {
    // O filtro de tenant já foi aplicado na origem: estes ids saíram de
    // `agents` filtrado por company_id. Aqui a busca é por agent_id porque a
    // tela legada grava a linha SEM company_id — filtrar por empresa acharia
    // "nada" e o insert bateria na unique(agent_id).
    const { data: existentes, error } = await supabase
      .from('memory_settings').select('id, agent_id, company_id').in('agent_id', agentIds);
    if (error) return { peca: 'memoria', acao: 'ignorado', motivo: 'tabela_indisponivel' };

    const porAgente = new Map<string, { id: string; company_id: string | null }>();
    for (const linha of (existentes ?? []) as any[]) porAgente.set(String(linha.agent_id), { id: linha.id, company_id: linha.company_id ?? null });

    let criados = 0;
    for (const agentId of agentIds) {
      const atual = porAgente.get(agentId);
      if (!atual) {
        const { error: insErr } = await supabase.from('memory_settings').insert({ agent_id: agentId, company_id: companyId });
        if (insErr) return { peca: 'memoria', acao: 'erro', criados, motivo: 'insert_falhou' };
        criados += 1;
        continue;
      }
      // Linha órfã da tela legada: adota o tenant, sem tocar na configuração.
      if (!atual.company_id) {
        await supabase.from('memory_settings').update({ company_id: companyId }).eq('id', atual.id);
      }
    }
    return { peca: 'memoria', acao: criados ? 'criado' : 'existente', quantidade: agentIds.length, criados };
  } catch {
    return { peca: 'memoria', acao: 'ignorado', motivo: 'excecao' };
  }
}

/**
 * Entitlements de capability. 📊 0 linhas nas três corretoras.
 *
 * MATERIALIZAR NÃO LIGA NADA QUE JÁ NÃO ESTIVESSE LIGADO. Tanto o resolver do
 * runtime (`backend/app/agents/capability_resolver.py`, `ent_disabled`) quanto
 * o cockpit (`app/api/admin/companies/[companyId]/capabilities/route.ts`)
 * tratam ausência de linha como PERMITIDO. O gate real continua sendo a
 * conexão (`requires_connection`) e a aprovação (`requires_approval`).
 *
 * O que muda: passa a existir a linha que alguém pode DESLIGAR, e o estado da
 * corretora deixa de ser implícito.
 */
async function garantirEntitlements(supabase: SupabaseClient, companyId: string): Promise<ResultadoPeca> {
  try {
    const { data: existentes, error } = await supabase
      .from('tenant_capability_entitlements').select('capability_key').eq('company_id', companyId);
    if (error) return { peca: 'entitlements', acao: 'ignorado', motivo: 'tabela_indisponivel' };

    const jaTem = new Set((existentes ?? []).map((e: any) => String(e.capability_key)));
    const faltantes = CAPABILITY_CATALOG.filter((c) => !jaTem.has(c.key));
    if (!faltantes.length) {
      return { peca: 'entitlements', acao: 'existente', quantidade: jaTem.size, criados: 0 };
    }
    const linhas = faltantes.map((c) => ({ company_id: companyId, capability_key: c.key, enabled: true }));
    const { error: insErr } = await supabase.from('tenant_capability_entitlements')
      .upsert(linhas, { onConflict: 'company_id,capability_key', ignoreDuplicates: true });
    if (insErr) return { peca: 'entitlements', acao: 'erro', motivo: 'insert_falhou' };
    return { peca: 'entitlements', acao: 'criado', quantidade: CAPABILITY_CATALOG.length, criados: faltantes.length };
  } catch {
    return { peca: 'entitlements', acao: 'ignorado', motivo: 'excecao' };
  }
}

/**
 * Perfis de briefing (diário + executivo). Já existem nas três corretoras
 * porque `briefing_service.perfil()` cria sob demanda — mas só depois que
 * alguém pede um briefing. Nascer com eles é o que torna as corretoras iguais.
 *
 * Os campos espelham `backend/app/services/intelligence/briefing_service.py`
 * (`padrao`). O resto vem do DEFAULT da coluna.
 */
const PERFIS_DE_BRIEFING: Array<{ cadence: string; name: string; schedule_spec: Record<string, unknown> }> = [
  { cadence: 'daily', name: 'Briefing diário', schedule_spec: { time: '08:00' } },
  { cadence: 'weekly', name: 'Briefing executivo', schedule_spec: { time: '08:00', weekday: 0 } },
];

async function garantirPerfisDeBriefing(supabase: SupabaseClient, companyId: string): Promise<ResultadoPeca> {
  try {
    const { data: existentes, error } = await supabase
      .from('briefing_profiles').select('id, cadence, user_id, is_active')
      .eq('company_id', companyId).is('user_id', null).eq('is_active', true);
    if (error) return { peca: 'briefing', acao: 'ignorado', motivo: 'tabela_indisponivel' };

    const jaTem = new Set((existentes ?? []).map((p: any) => String(p.cadence)));
    let criados = 0;
    for (const perfil of PERFIS_DE_BRIEFING) {
      if (jaTem.has(perfil.cadence)) continue;
      const { error: insErr } = await supabase.from('briefing_profiles').insert({
        company_id: companyId, user_id: null, scope: 'company',
        name: perfil.name, cadence: perfil.cadence,
        schedule_spec: perfil.schedule_spec, channels: ['dashboard'],
      });
      // Índice único parcial pode recusar corrida — isso é sucesso, não falha.
      if (insErr && !String(insErr.code ?? '').startsWith('23')) {
        return { peca: 'briefing', acao: 'erro', criados, motivo: 'insert_falhou' };
      }
      if (!insErr) criados += 1;
    }
    return { peca: 'briefing', acao: criados ? 'criado' : 'existente', quantidade: PERFIS_DE_BRIEFING.length, criados };
  } catch {
    return { peca: 'briefing', acao: 'ignorado', motivo: 'excecao' };
  }
}

/**
 * O catálogo global é GLOBAL: `auxiliary_templates` não tem `company_id`, então
 * a corretora nova enxerga a mesma prateleira que as antigas — sem cópia por
 * tenant (seria motor paralelo). O que se confere aqui é que a prateleira NÃO
 * ESTÁ VAZIA: catálogo com zero itens é uma corretora nascendo sem o que ligar.
 *
 * Nada é instalado: instalar é decisão do corretor (nada nasce ligado).
 */
async function conferirCatalogoGlobal(supabase: SupabaseClient): Promise<ResultadoPeca> {
  try {
    const { count, error } = await supabase.from('auxiliary_templates')
      .select('id', { count: 'exact', head: true }).eq('is_active', true);
    if (error) return { peca: 'catalogo_global', acao: 'ignorado', motivo: 'tabela_indisponivel' };
    const total = count ?? 0;
    if (total <= 0) return { peca: 'catalogo_global', acao: 'ignorado', quantidade: 0, motivo: 'catalogo_global_vazio' };
    return { peca: 'catalogo_global', acao: 'existente', quantidade: total };
  } catch {
    return { peca: 'catalogo_global', acao: 'ignorado', motivo: 'excecao' };
  }
}

// ---------------------------------------------------------------------------
// 7. Provisionamento
// ---------------------------------------------------------------------------

function falha(companyId: string, motivo: string): ProvisionResult {
  return {
    ok: false, company_id: companyId, error: motivo,
    core: { id: null, action: 'error', reason: motivo },
    attendance: { id: null, action: 'error', reason: motivo },
    pecas: [], completa: false, faltando: [motivo],
  };
}

/**
 * Garante que a corretora tenha TUDO com que ela deveria nascer. Idempotente:
 * rodar de novo não duplica nada e cura o que estiver vazio.
 */
export async function provisionTenant(supabase: SupabaseClient, companyId: string): Promise<ProvisionResult> {
  // SPEC-013 — empresas-plataforma (Studio/Knowledge) NÃO recebem provisionamento
  // comercial. Seus Source Agents são autorados no Blueprint Center, não aqui.
  const kind = await getCompanyKind(supabase, companyId);
  if (isPlatformCompany(kind)) {
    return {
      ok: true, company_id: companyId,
      core: { id: null, action: 'exists', reason: 'platform_company_skipped' },
      attendance: { id: null, action: 'exists', reason: 'platform_company_skipped' },
      pecas: [], completa: true, faltando: [],
    };
  }

  // Empresa inexistente ou sem nome deixou de ser tratada com o antigo fallback
  // `'Corretora'`: ele produzia um agente que se apresentava como "AutoBrokers
  // da Corretora" e ninguém percebia. É erro, e para aqui.
  const { data: company } = await supabase.from('companies').select('id, company_name').eq('id', companyId).maybeSingle();
  if (!company?.id) return falha(companyId, 'empresa_inexistente');
  const companyName = String((company as any).company_name ?? '').trim();
  if (!companyName) return falha(companyId, 'empresa_sem_nome');

  const core = await ensureAgentByRole(supabase, companyId, companyName, AUTOBROKERS_CORE_BLUEPRINT, 'autobrokers');
  const attendance = await ensureAgentByRole(supabase, companyId, companyName, EVEN_ATTENDANCE_BLUEPRINT, 'even-atendimento');

  const agentIds = [core.id, attendance.id].filter((id): id is string => typeof id === 'string' && id.length > 0);
  const pecas: ResultadoPeca[] = [
    await garantirConfigDeMemoria(supabase, companyId, agentIds),
    await garantirEntitlements(supabase, companyId),
    await garantirPerfisDeBriefing(supabase, companyId),
    await conferirCatalogoGlobal(supabase),
  ];

  const faltando: string[] = [];
  if (core.action === 'error') faltando.push(`core:${core.reason ?? 'erro'}`);
  if (attendance.action === 'error') faltando.push(`attendance:${attendance.reason ?? 'erro'}`);
  for (const p of pecas) {
    if (p.acao === 'erro' || p.acao === 'ignorado') faltando.push(`${p.peca}:${p.motivo ?? p.acao}`);
  }

  const agentesOk = core.action !== 'error' && attendance.action !== 'error';
  const pecaComErro = pecas.some((p) => p.acao === 'erro');
  const ok = agentesOk && !pecaComErro;

  return {
    ok, company_id: companyId, core, attendance, pecas,
    completa: faltando.length === 0,
    ...(ok ? {} : { error: faltando[0] ?? 'provision_failed' }),
    faltando,
  };
}

// ---------------------------------------------------------------------------
// 8. Herança: o global chega em quem já existe
// ---------------------------------------------------------------------------

export type AcaoHeranca = 'preenchido' | 'igual' | 'preservado' | 'atualizado' | 'ausente' | 'erro';

export interface HerancaAgente {
  role: AgentRole;
  agent_id: string | null;
  acao: AcaoHeranca;
  chars_antes?: number;
  chars_depois?: number;
  versao_gravada?: string; // sha256 curto do texto ARQUIVADO
  detalhe?: string;
}

export interface HerancaResultado {
  ok: boolean;
  company_id: string;
  sobrescrever: boolean;
  motivo: string;
  agentes: HerancaAgente[];
}

const BLUEPRINTS_POR_PAPEL: Array<{ role: AgentRole; bp: CanonicalBlueprint }> = [
  { role: 'core', bp: AUTOBROKERS_CORE_BLUEPRINT },
  { role: 'attendance', bp: EVEN_ATTENDANCE_BLUEPRINT },
];

/**
 * Reaplica o blueprint global numa corretora que JÁ EXISTE.
 *
 *     vazio        → preenche
 *     idêntico     → não faz nada
 *     divergente   → PRESERVA, a menos que `sobrescrever: true`
 *     sobrescrever → versiona primeiro, confere que versionou, e só então grava
 *
 * O versionamento é uma escrita separada de propósito. Se ele falhar, o texto
 * antigo continua no banco: perder 7.914 caracteres escritos à mão para ganhar
 * um template não é um negócio que valha a pena em nenhuma corretora.
 */
export async function reaplicarBlueprintGlobal(
  supabase: SupabaseClient,
  companyId: string,
  opcoes: { sobrescrever?: boolean; motivo?: string } = {},
): Promise<HerancaResultado> {
  const sobrescrever = opcoes.sobrescrever === true;
  const motivo = String(opcoes.motivo ?? 'reaplicacao_blueprint_global').slice(0, 120);
  const base: HerancaResultado = { ok: true, company_id: companyId, sobrescrever, motivo, agentes: [] };

  const kind = await getCompanyKind(supabase, companyId);
  if (isPlatformCompany(kind)) return { ...base, ok: true };

  const { data: company } = await supabase.from('companies').select('id, company_name').eq('id', companyId).maybeSingle();
  const companyName = String((company as any)?.company_name ?? '').trim();
  if (!company?.id || !companyName) {
    return { ...base, ok: false, agentes: [{ role: 'core', agent_id: null, acao: 'erro', detalhe: 'empresa_inexistente_ou_sem_nome' }] };
  }

  const agentes: HerancaAgente[] = [];
  for (const { role, bp } of BLUEPRINTS_POR_PAPEL) {
    agentes.push(await reaplicarNoAgente(supabase, companyId, companyName, role, bp, sobrescrever, motivo));
  }
  return { ...base, ok: !agentes.some((a) => a.acao === 'erro'), agentes };
}

async function reaplicarNoAgente(
  supabase: SupabaseClient, companyId: string, companyName: string,
  role: AgentRole, bp: CanonicalBlueprint, sobrescrever: boolean, motivo: string,
): Promise<HerancaAgente> {
  const { data: agent, error } = await supabase.from('agents').select(AGENTE_SELECT)
    .eq('company_id', companyId).eq('agent_role', role).limit(1).maybeSingle();
  if (error) return { role, agent_id: null, acao: 'erro', detalhe: 'lookup_falhou' };
  if (!agent?.id) return { role, agent_id: null, acao: 'ausente', detalhe: 'provisione_antes' };

  const atual = String((agent as any).agent_system_prompt ?? '');
  const salvo = extractSavedTenantInput((agent as any).context_package);
  const upd = computeAgentConfigUpdate(bp, companyName, (agent as any).context_package, salvo);
  const novo = String(upd.columns.agent_system_prompt ?? '');

  // Fail-closed também aqui: um blueprint quebrado não apaga o que existe.
  const problemas = problemasDoUpdate(bp, upd);
  if (problemas.length) {
    return { role, agent_id: agent.id, acao: 'erro', chars_antes: atual.length, detalhe: `blueprint_invalido:${problemas.join(',')}` };
  }

  const agora = new Date().toISOString();

  // 1) VAZIO — preenche. Não há o que versionar.
  if (!atual.trim()) {
    const cp = marcarHerancaAplicada(upd.context_package, { motivo: `${motivo}:preenchimento_de_vazio`, blueprint_key: bp.blueprint_key, agora });
    const { error: upErr } = await supabase.from('agents')
      .update({ ...semRenomear(upd.columns, (agent as any).name), context_package: cp, updated_at: agora })
      .eq('id', agent.id).eq('company_id', companyId);
    if (upErr) return { role, agent_id: agent.id, acao: 'erro', detalhe: 'update_falhou' };
    return { role, agent_id: agent.id, acao: 'preenchido', chars_antes: 0, chars_depois: novo.length };
  }

  // 2) IDÊNTICO — nada a fazer (evita versão inútil a cada execução).
  if (atual === novo) {
    return { role, agent_id: agent.id, acao: 'igual', chars_antes: atual.length, chars_depois: novo.length };
  }

  // 3) DIVERGENTE e sem autorização — PRESERVA. É o caso da Amandus.
  if (!sobrescrever) {
    return {
      role, agent_id: agent.id, acao: 'preservado',
      chars_antes: atual.length, chars_depois: novo.length,
      detalhe: 'texto_local_diferente_do_global:sobrescrever=false',
    };
  }

  // 4) DIVERGENTE e autorizado — VERSIONA PRIMEIRO, em escrita separada.
  const cpVersionado = registrarVersaoDoPrompt((agent as any).context_package, {
    prompt: atual, motivo: `${motivo}:antes_de_sobrescrever`, blueprint_key: bp.blueprint_key, agora,
    name: (agent as any).name ?? null, // o nome exibido vai junto — some se ninguém guardar
  });
  const { error: verErr } = await supabase.from('agents')
    .update({ context_package: cpVersionado, updated_at: agora })
    .eq('id', agent.id).eq('company_id', companyId);
  if (verErr) {
    return { role, agent_id: agent.id, acao: 'erro', chars_antes: atual.length, detalhe: 'versionamento_falhou:prompt_preservado' };
  }

  // Confere no BANCO que a versão entrou. Sem esta releitura, "versionei" seria
  // uma afirmação sobre uma requisição, não sobre um fato gravado.
  const esperado = hashCurto(atual);
  const { data: conferencia } = await supabase.from('agents').select('context_package').eq('id', agent.id).eq('company_id', companyId).maybeSingle();
  const versoes = (((conferencia as any)?.context_package ?? {})[HERANCA_NS]?.versoes ?? []) as VersaoDoPrompt[];
  if (!Array.isArray(versoes) || !versoes.some((v) => v?.sha256_12 === esperado)) {
    return { role, agent_id: agent.id, acao: 'erro', chars_antes: atual.length, detalhe: 'versao_nao_confirmada:prompt_preservado' };
  }

  // 5) Só agora o texto novo entra — sobre um histórico que já está no banco.
  const cpFinal = { ...cpVersionado, ...upd.context_package, [HERANCA_NS]: (cpVersionado as any)[HERANCA_NS] };
  const { error: upErr } = await supabase.from('agents')
    .update({ ...upd.columns, context_package: cpFinal, updated_at: agora })
    .eq('id', agent.id).eq('company_id', companyId);
  if (upErr) return { role, agent_id: agent.id, acao: 'erro', chars_antes: atual.length, detalhe: 'update_falhou:versao_ja_gravada' };

  return {
    role, agent_id: agent.id, acao: 'atualizado',
    chars_antes: atual.length, chars_depois: novo.length, versao_gravada: esperado,
  };
}
