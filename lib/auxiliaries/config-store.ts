// SPEC-064 Bloco F — a corretora configura o Auxiliar depois de instalado.
//
// O defeito, medido em 02/08/2026:
//
//     tenant_auxiliary_revisions ............ ZERO referências em código
//     PATCH para tenant_auxiliaries.config .. NÃO EXISTE
//
// As instalações gravavam `config` no momento da instalação **e nunca mais**.
//
// E o lado da leitura estava pronto e esperando: `auxiliary_context.py`
// (`_read_contract`) prefere `tenant config.contract` sobre
// `template default_config.contract` — uma sobreposição por corretora que
// nada no sistema conseguia escrever.
//
// A REGRA QUE ESTE ARQUIVO IMPLEMENTA
//
//     o template GLOBAL é a origem
//     a config da CORRETORA é uma SOBREPOSIÇÃO
//     mudar o global NÃO apaga a sobreposição da corretora
//     mudar a corretora NUNCA toca no global
//
// É a mesma regra das camadas de conexão, aplicada à configuração:
// o de baixo sobrepõe o de cima, e nenhum dos dois apaga o outro.
import type { SupabaseClient } from '@supabase/supabase-js';

export interface ResultadoDeConfig {
  ok: boolean;
  error?: string;
  revision?: number;
  config?: Record<string, unknown>;
  changed_fields?: string[];
}

/** Campos que a corretora pode ajustar. Fora daqui, é do template. */
const CAMPOS_DA_CORRETORA = new Set([
  'horario',
  'frequencia',
  'canais',
  'destinatarios',
  'teto_itens',
  'ignorar',
  'limites',
  'contract',
  'portais',
  'max_boletos_por_execucao',
  'exige_aprovacao_para_enviar',
]);

/**
 * O que mudou entre duas configurações — por chave de primeiro nível.
 *
 * Serve para `changed_fields`, que é o que torna o histórico legível: uma
 * revisão que diz "mudou" não ajuda ninguém a entender o que aconteceu.
 */
export function camposQueMudaram(
  antes: Record<string, unknown>,
  depois: Record<string, unknown>,
): string[] {
  // `Array.from` em vez de espalhar o Set: o alvo de compilação do projeto não
  // habilita `downlevelIteration`, e iterar Set direto não compila.
  const chaves = Array.from(
    new Set([...Object.keys(antes ?? {}), ...Object.keys(depois ?? {})]),
  );
  const mudou: string[] = [];
  for (const k of chaves) {
    if (JSON.stringify(antes?.[k]) !== JSON.stringify(depois?.[k])) mudou.push(k);
  }
  return mudou.sort();
}

/**
 * Grava a sobreposição da corretora, com histórico.
 *
 * `escopo`: só as chaves de `CAMPOS_DA_CORRETORA` entram. Uma corretora não
 * reescreve o `runtime` do template — isso mudaria o que o Auxiliar É, não
 * como ele se comporta para ela.
 */
export async function gravarConfigDaCorretora(
  supabase: SupabaseClient,
  opts: {
    companyId: string;
    slug: string;
    mudancas: Record<string, unknown>;
    porQuem: string;
    motivo?: string;
  },
): Promise<ResultadoDeConfig> {
  const { companyId, slug, mudancas, porQuem, motivo } = opts;

  const recusados = Object.keys(mudancas).filter((k) => !CAMPOS_DA_CORRETORA.has(k));
  if (recusados.length > 0) {
    return {
      ok: false,
      error: `campos_fora_do_escopo_da_corretora: ${recusados.join(', ')}`,
    };
  }

  // O filtro por company_id é obrigatório aqui e em toda leitura seguinte
  // (CLAUDE.md §7). O backend usa service role: sem o filtro no código, RLS
  // não protege nada.
  const { data: instalacao } = await supabase
    .from('tenant_auxiliaries')
    .select('id, config, permissions, current_revision, release_id')
    .eq('company_id', companyId)
    .eq('slug', slug)
    .maybeSingle();

  if (!instalacao?.id) return { ok: false, error: 'auxiliar_nao_instalado' };

  const antes = (instalacao.config as Record<string, unknown>) ?? {};
  const depois = { ...antes, ...mudancas };
  const mudou = camposQueMudaram(antes, depois);

  if (mudou.length === 0) {
    return { ok: true, revision: instalacao.current_revision ?? 0, config: antes, changed_fields: [] };
  }

  const proxima = Number(instalacao.current_revision ?? 0) + 1;

  // A revisão vem ANTES da escrita, de propósito. Se a atualização falhar,
  // sobra uma revisão órfã — que é um registro a mais. Se fosse ao contrário e
  // a revisão falhasse, sobraria uma mudança sem história, que é pior: ninguém
  // conseguiria responder "quem mudou meu horário?".
  const { error: erroRevisao } = await supabase.from('tenant_auxiliary_revisions').insert({
    company_id: companyId,
    tenant_auxiliary_id: instalacao.id,
    revision: proxima,
    release_id: instalacao.release_id ?? null,
    config: depois,
    permissions: instalacao.permissions ?? {},
    reason: motivo ?? 'ajuste da corretora',
    changed_fields: mudou,
    approved_by: porQuem,
    approved_at: new Date().toISOString(),
  });
  if (erroRevisao) {
    return { ok: false, error: `historico_falhou: ${erroRevisao.message}` };
  }

  const { error: erroUpdate } = await supabase
    .from('tenant_auxiliaries')
    .update({
      config: depois,
      current_revision: proxima,
      updated_at: new Date().toISOString(),
    })
    .eq('id', instalacao.id)
    .eq('company_id', companyId);

  if (erroUpdate) return { ok: false, error: `gravacao_falhou: ${erroUpdate.message}` };

  return { ok: true, revision: proxima, config: depois, changed_fields: mudou };
}

/** O histórico de mudanças desta corretora neste Auxiliar. */
export async function historicoDeConfig(
  supabase: SupabaseClient,
  companyId: string,
  slug: string,
  limite = 20,
) {
  const { data: instalacao } = await supabase
    .from('tenant_auxiliaries')
    .select('id')
    .eq('company_id', companyId)
    .eq('slug', slug)
    .maybeSingle();
  if (!instalacao?.id) return { ok: false as const, error: 'auxiliar_nao_instalado' };

  const { data } = await supabase
    .from('tenant_auxiliary_revisions')
    .select('revision, changed_fields, reason, approved_by, approved_at, created_at')
    .eq('company_id', companyId)
    .eq('tenant_auxiliary_id', instalacao.id)
    .order('revision', { ascending: false })
    .limit(limite);

  return { ok: true as const, revisoes: data ?? [] };
}
