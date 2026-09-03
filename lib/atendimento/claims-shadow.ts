/**
 * SPEC-093-B · BLOCO B (lado NEXT) — o gesto da atendente vira evento no Work OS.
 *
 * 🔴 O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR: o gesto humano que não deixa rastro.
 *
 * 📊 Medido em 03/09/2026: `work_events` tinha ZERO eventos com ator humano em
 * 27.985 registros, e `tools_config.human_handoff.enabled` está false/ausente
 * nos 8 agentes. Ou seja: o handoff do robô **não é** a fonte do rastro humano
 * hoje. A fonte REAL é o botão **Assumir** do painel — este arquivo.
 *
 * ⛔ AS TRAVAS QUE ESTE MÓDULO CARREGA (SPEC-093-B §2):
 *   - ZERO texto livre. `payload_redacted` só aceita chaves e valores do
 *     vocabulário (`lib/atendimento/claims-shadow-vocab.json`). O texto da nota
 *     e a fala da atendente NÃO entram — só o booleano `tem_numero`.
 *   - Nada de sombra retroativa: sem `work_runs` com `workflow_key='claims.shadow'`
 *     para a conversa, o gesto NÃO grava evento.
 *   - A sombra nunca impede o gesto: o registrador NUNCA lança.
 *
 * 🔴 POR QUE O VOCABULÁRIO É INJETADO E NÃO IMPORTADO AQUI DENTRO:
 * o repo trava o TypeScript em **5.2.2** (`package.json`), que ainda não entende
 * `import … with { type: 'json' }`; e o Node deste ambiente é **24**, que EXIGE o
 * atributo para importar JSON em ESM (`ERR_IMPORT_ATTRIBUTE_MISSING` — medido).
 * As duas formas existem e nenhuma serve aos dois ao mesmo tempo. Então quem
 * importa o JSON é o **chamador**: o `route.ts` via `@/…json` (`resolveJsonModule`,
 * precedente `lib/admin/provision-tenant.ts:57`) e o teste via `readFileSync` do
 * MESMO arquivo. Um vocabulário, dois leitores — que é o gate ⑤ do BLOCO B.
 */

// ⚠️ `import type` — some na compilação e some também no type-stripping do Node,
// então o teste `.mjs` carrega este arquivo sem arrastar `@/lib/vault/server`
// (que lê env e falaria com o Vault).
import type { getSupabaseAdmin } from '@/lib/vault/server';

export type ClienteDaSombra = ReturnType<typeof getSupabaseAdmin>;

/**
 * A forma do `claims-shadow-vocab.json`. Quem valida o ARQUIVO é o desenhista
 * (`scripts/claims-shadow-vocab.test.mjs`); aqui só se descreve o que se lê.
 */
export interface VocabularioDaSombra {
  eventos: Record<string, { ator: string; payload: string[] }>;
  enums: Record<string, string[]>;
  inteiros: string[];
  atores_do_check: string[];
  limite_de_valor_em_chars: number;
  workflow_key: string;
}

export type ValorDeQualificador = string | number | boolean;
export type PayloadDaSombra = Record<string, ValorDeQualificador>;

export interface GestoDaSombra {
  companyId: string;
  conversationId: string;
  eventType: string;
  payload: PayloadDaSombra;
}

export type ResultadoDaSombra =
  | { gravado: true; workRunId: string }
  | { gravado: false; motivo: string };

/**
 * 🔴 `message_human` SÓ POR TEMPLATE (§2). Nenhuma interpolação, nenhum nome,
 * nenhum número de apólice — a frase é constante e o qualificador mora no payload.
 *
 * ⚠️ E a lista é a dos CINCO gestos que o PAINEL produz, não os onze do
 * vocabulário. Os outros seis são escritos pelo Python, com os templates dele; um
 * `event_type` fora desta lista é recusado aqui **de propósito** — o painel não
 * tem como saber que um documento chegou, e fingir que sabe é dado inventado.
 */
const EVENTOS_DO_PAINEL: Record<string, string> = {
  'claims.humano_assumiu': 'a atendente assumiu o caso',
  'claims.humano_devolveu': 'a atendente devolveu o caso ao atendente IA',
  'claims.humano_respondeu': 'a atendente respondeu pelo painel',
  'claims.nota_registrada': 'a atendente registrou uma anotação interna',
  'claims.encerrado': 'o caso foi encerrado pela atendente',
};

/**
 * ⚠️ O CASADOR QUE IMPEDE TEXTO LIVRE DE ENTRAR POR UMA CHAVE LEGÍTIMA.
 *
 * Um valor que não é enum e não é inteiro ainda pode ser string (`ramo`,
 * `seguradora_slug`). Se a única regra fosse o TAMANHO, `"o cliente bateu o carro"`
 * — 23 chars — passaria. Slug não tem espaço, acento nem pontuação de frase, e é
 * isso que separa um identificador de uma frase.
 */
const FORMA_DE_SLUG = /^[a-z0-9][a-z0-9_.-]*$/;

/** 🔴 O que sai do gesto e vira `payload_redacted`, ou a razão da recusa. */
export function validarGestoDaSombra(
  vocab: VocabularioDaSombra,
  eventType: string,
  payload: PayloadDaSombra,
):
  | { ok: true; ator: string; mensagem: string; payload: PayloadDaSombra }
  | { ok: false; motivo: string } {
  const declarado = vocab?.eventos?.[eventType];
  if (!declarado) return { ok: false, motivo: `event_type fora do vocabulário: ${eventType}` };

  const mensagem = EVENTOS_DO_PAINEL[eventType];
  if (!mensagem) return { ok: false, motivo: `event_type não é um gesto do painel: ${eventType}` };

  // 🔴 O ator vem do VOCABULÁRIO, não de uma constante local — e ainda assim é
  // conferido contra o CHECK real. 📊 `human` não está no CHECK
  // (`ck_work_events_actor`): o Postgres recusa o INSERT e o evento some.
  const ator = declarado.ator;
  if (!Array.isArray(vocab.atores_do_check) || !vocab.atores_do_check.includes(ator)) {
    return { ok: false, motivo: `actor_type fora do CHECK de work_events: ${ator}` };
  }

  const declaradas = Array.isArray(declarado.payload) ? declarado.payload : [];
  const vieram = Object.keys(payload || {});

  const intrusas = vieram.filter((k) => !declaradas.includes(k));
  if (intrusas.length) {
    return { ok: false, motivo: `chave fora do vocabulário: ${intrusas.join(', ')}` };
  }
  const faltando = declaradas.filter((k) => !vieram.includes(k));
  if (faltando.length) {
    return { ok: false, motivo: `qualificador ausente: ${faltando.join(', ')}` };
  }

  const limite = Number(vocab.limite_de_valor_em_chars) || 64;
  for (const chave of declaradas) {
    const valor = payload[chave];
    const enumerado = vocab.enums?.[chave];

    if (enumerado) {
      if (typeof valor !== 'string' || !enumerado.includes(valor)) {
        return { ok: false, motivo: `valor fora do enum '${chave}'` };
      }
      continue;
    }
    if (Array.isArray(vocab.inteiros) && vocab.inteiros.includes(chave)) {
      if (typeof valor !== 'number' || !Number.isInteger(valor)) {
        return { ok: false, motivo: `'${chave}' tem de ser inteiro` };
      }
      continue;
    }
    if (typeof valor === 'boolean') continue;
    if (typeof valor === 'string' && valor.length <= limite && FORMA_DE_SLUG.test(valor)) continue;

    return { ok: false, motivo: `valor não-enumerável em '${chave}' (só booleano ou slug ≤ ${limite})` };
  }

  return { ok: true, ator, mensagem, payload: { ...payload } };
}

/**
 * 🔴 A SOMBRA DESTA CONVERSA, OU NADA.
 *
 * `SELECT id FROM work_runs WHERE company_id=? AND conversation_id=? AND
 * workflow_key='claims.shadow'` — o índice `ix_work_runs_conversa` existe. Sem
 * linha, o gesto não vira evento: nesta SPEC não há sombra retroativa (BLOCO B).
 */
export async function acharSombraDaConversa(
  supabase: ClienteDaSombra,
  vocab: VocabularioDaSombra,
  companyId: string,
  conversationId: string,
): Promise<string | null> {
  const { data, error } = await supabase
    .from('work_runs')
    .select('id')
    // ⚠️ `company_id` PRIMEIRO e SEMPRE (CLAUDE.md §7): o backend usa service
    // role, então RLS não salva de um filtro esquecido no código.
    .eq('company_id', companyId)
    .eq('conversation_id', conversationId)
    .eq('workflow_key', vocab.workflow_key)
    .order('created_at', { ascending: false })
    .limit(1);
  if (error) {
    console.warn('[CLAIMS-SHADOW] sombra nao consultada:', error.message);
    return null;
  }
  const linha = Array.isArray(data) ? (data[0] as { id?: unknown } | undefined) : null;
  return linha && linha.id ? String(linha.id) : null;
}

/**
 * O registrador, já amarrado a UM vocabulário.
 *
 * ⚠️ Devolver a função (em vez de receber o vocabulário a cada chamada) é o que
 * garante um só ponto de fiação por stack: quem esquecer de passar o vocabulário
 * não compila, em vez de gravar com um vocabulário vazio.
 */
export function criarRegistradorDaSombra(vocab: VocabularioDaSombra) {
  /**
   * 🔴 NUNCA LANÇA e nunca desfaz o gesto: a linha do tempo é melhor-esforço, o
   * atendimento não. Mas a falha APARECE no console — um `catch` mudo é uma
   * flag que mente com outro nome (`acionamentos-travados/route.ts:220`).
   */
  return async function registrarEventoDaSombra(
    supabase: ClienteDaSombra,
    gesto: GestoDaSombra,
  ): Promise<ResultadoDaSombra> {
    try {
      const valido = validarGestoDaSombra(vocab, gesto.eventType, gesto.payload || {});
      if (!valido.ok) {
        console.warn('[CLAIMS-SHADOW] evento RECUSADO antes do banco:', valido.motivo);
        return { gravado: false, motivo: valido.motivo };
      }
      if (!gesto.companyId || !gesto.conversationId) {
        return { gravado: false, motivo: 'sem company_id ou conversation_id' };
      }

      const workRunId = await acharSombraDaConversa(
        supabase,
        vocab,
        gesto.companyId,
        gesto.conversationId,
      );
      if (!workRunId) return { gravado: false, motivo: 'conversa sem sombra' };

      const { error } = await supabase.from('work_events').insert({
        company_id: gesto.companyId,
        work_run_id: workRunId,
        event_type: gesto.eventType,
        // 📊 `user` — e não `human`, que o CHECK recusa em silêncio.
        actor_type: valido.ator,
        severity: 'info',
        message_human: valido.mensagem,
        payload_redacted: valido.payload,
      });
      if (error) {
        console.warn('[CLAIMS-SHADOW] evento NAO registrado:', error.message);
        return { gravado: false, motivo: error.message };
      }
      return { gravado: true, workRunId };
    } catch (e) {
      console.warn(
        '[CLAIMS-SHADOW] evento NAO registrado:',
        e instanceof Error ? e.message : String(e),
      );
      return { gravado: false, motivo: 'excecao' };
    }
  };
}

/**
 * `tem_numero` — 🔴 o ÚNICO resíduo de uma anotação que entra no ledger.
 *
 * ⚠️ Seis dígitos ou mais é a forma de um protocolo/sinistro. O booleano diz
 * *"a atendente anotou um número"*; o número em si fica no Espelho, que é onde
 * texto de conversa mora. `payload_redacted` tem esse nome por um motivo.
 */
export function anotacaoTemNumero(texto: unknown): boolean {
  return /\d{6,}/.test(String(texto ?? ''));
}
