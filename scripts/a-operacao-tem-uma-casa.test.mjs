// SPEC-097 — A OPERAÇÃO TEM UMA CASA. O guarda do lado da TELA e do BFF,
// escrito ANTES do código (protocolo AAA v11.2 §4: quem faz a prova não faz a
// resposta — o DESENHISTA escreve o teste, os builders o deixam verde).
//
// 🔴 ESTE ARQUIVO NASCE VERMELHO, E É PARA NASCER. Em `7f3f3eb` (a cópia limpa
// `../AutoBrokers-FIX-gate0`) ele imprime os itens do GATE ZERO (§4 BLOCO 0.1)
// que são do lado da tela/BFF:
//
//    (i)   o `else` do silêncio ainda vira `concluido`      → [2]
//    (ii)  o claim escreve `status: 'HUMAN_REQUESTED'`      → [4]
//    (iii) `attendance_sessions` sem `conversation_id`      → [5]
//    (v)   `.limit(120)` na Fila                            → [7]
//    (vi)  a busca de Casos é `filter()` no cliente         → [7]
//    (vii) tipos de timeline com `at: null`                 → [10]
//    (viii) duas funções de leitura (Fila ≠ Casos)          → [1]
//    (ix)  `semana.terminaram` contradiz `items`            → [3]
//
// Os itens (iv) — a IA não pausa por `claimed_by` — e o resto de (iii) são do
// guarda irmão, `backend/tests/test_o_atendimento_sabe_como_terminou.py`.
//
// Um guarda que nasce verde não mediu nada (CLAUDE.md §9.3): tudo que já está
// verde em HEAD é suspeito e está anotado no relatório.
//
// ─────────────────────────────────────────────────────────────────────────────
// O QUE ELE GUARDA — a medição de 05/09/2026 (SPEC-097 §1)
// ─────────────────────────────────────────────────────────────────────────────
//
//   📊 atendimentos/route.ts:217-221  cascata `closed → HUMAN_REQUESTED →
//                              claimed_by → fresh(<48h) → else 'concluido'`.
//                              Rodada sobre o acervo: 584 de 668 conversas
//                              (87,4%) "encerradas" — e `resolvido_em` NULL em
//                              728/728. Ninguém encerrou nada (§1.1) — R1
//   📊 atendimentos/route.ts:83  `.limit(120)` sobre 448 conversas da AutoFleet:
//                              73% invisível; a busca de Casos é `filter()` no
//                              cliente sobre os 120 → falso zero (§1.5) — R5
//   📊 conversas/[id]/route.ts:120  o único escritor de `claimed_by` grava
//                              `status: 'HUMAN_REQUESTED'` junto, e a cascata
//                              testa o status ANTES do dono: `com_equipe` é
//                              inalcançável (§1.2) — R2
//   📊 attendance_sessions      12.755 linhas, 5,8 episódios por contato, SEM
//                              `conversation_id`: o caso é o EPISÓDIO, e ele
//                              não tem elo com a conversa (§1.4) — R3
//   📊 ficha/[id]/route.ts      6 de 9 tipos da timeline com `at: null` (§1.7,
//                              E16) — R8
//
// Nenhum desses defeitos trava nada. Todos respondem 200. É o CLAUDE.md §9.5 na
// casa da operação: a Fila RESPONDE, e responde errado — em silêncio.
//
// ─────────────────────────────────────────────────────────────────────────────
// COMO ELE FUNCIONA — sem rede, sem banco, sem servidor
// ─────────────────────────────────────────────────────────────────────────────
//
// Mesma forma de `o-chat-responde-e-continua.test.mjs` (SPEC-096): o produto é
// transpilado com o TypeScript do projeto, carregado com um `require` falso e
// EXECUTADO sobre dublês. O dublê de Supabase APLICA os filtros e REGISTRA cada
// consulta (`from/select/eq/in/lt/gt/or/order/limit/range/textSearch/ilike`), o
// `fetch` global é dublado, e `resolveSessionCompany` devolve a sessão que o
// teste escolhe. Nenhum servidor sobe.
//
// 🔴 CADA ASSERÇÃO EXECUTA O PRODUTO (a lição da 096, §9.4 do CLAUDE.md).
// Regex sobre a fonte aparece em DOIS lugares, e só para medir a FORMA de uma
// DECLARAÇÃO (a lista canônica de estágios; o rótulo de navegação) — nunca para
// substituir o motor.
//
// O arquivo NOVO da SPEC (`lib/atendimento/casos.ts`) ainda não existe: o guarda
// captura a AUSÊNCIA, mostra a CAUSA CRUA e REPROVA com mensagem — nunca estoura
// (protocolo §0.3), e nunca diz "ainda não existe" quando a causa foi outra.
//
// ─────────────────────────────────────────────────────────────────────────────
// O CONTRATO QUE ESTE GUARDA FIXA — é o que os builders têm de escrever
// ─────────────────────────────────────────────────────────────────────────────
//
//   lib/atendimento/casos.ts
//     export async function projetarCasos(
//       ctx: { companyId: string; userId?: string },
//       filtro: Record<string, unknown> = {},
//       opcoes: { group_by?: 'stage'; cursor?: string|null; busca?: string;
//                 limite?: number } = {},
//     ): Promise<{
//       items: Caso[];
//       counts?: Record<Stage, number>;   // só com group_by:'stage' (o Quadro)
//       semana: { terminaram: number; ainda_esperam: number;
//                 morreram_esperando: number; por_motivo: …; por_kind: …;
//                 indisponivel: boolean };
//       indisponivel: Record<string, boolean>;   // POR FONTE (R5)
//       cursor: string | null;
//       has_more: boolean;
//     }>
//
//     Caso = {
//       key, stage, kind: 'episodio'|'conversa',
//       conversa_id, session_id, telefone, cliente, protocolo,
//       ultimo_evento_em,                 // R1/E5: UM relógio
//       parado_desde, parado_ha,          // só quando stage === 'parado'
//       resolvido_em, resolucao_motivo,   // R1: concluido ⇔ resolvido_em
//       dono: { id, nome } | null,        // R2
//       esperando: { kind, desde, due_at, vencida } | null,   // R4
//       sem_conversa_vinculada?: boolean, // R3/E7 (42,2% das sessões)
//       agora: {                          // R6/R7 — as 6 dimensões
//         situacao, dono, esperando, ha_quanto_tempo, atencao, proxima_acao
//       },
//     }
//
//   `group_by:'stage'` é a FILA/Quadro: uma linha por CONVERSA ativa (E11).
//   Sem `group_by` é CASOS: uma linha por EPISÓDIO (`attendance_sessions`), com
//   cursor `(ultimo_evento_em, id)` e busca NO BANCO.
//
// ─────────────────────────────────────────────────────────────────────────────
// 🔴 MUTAÇÕES — e agora elas RODAM: `node scripts/a-operacao-tem-uma-casa.test.mjs --mutar [ID]`
// ─────────────────────────────────────────────────────────────────────────────
//
// ⚠️ ESTA LISTA ERA PROSA. `provaDasMutacoes` conferia três coisas — id único,
// caminho existente e `length === 14` — e mais nada. Foi assim que CINCO
// mutações declaradas nasceram VERDES sem ninguém notar (lente de verdade,
// A-8): U3, U4, U7, M13 e M16 não deixavam nada vermelho, e as três primeiras
// são exatamente as regras que a §1 da SPEC mede como o defeito a consertar.
// Um guarda cujo painel de mutação não roda é um carimbo (CLAUDE.md §9.3).
//
// Cada entrada agora é EXECUTÁVEL:
//
//   ancora      a string EXATA que existe no código do PRODUTO. ⛔ NUNCA em
//               comentário: um comentário mutado não muda comportamento nenhum,
//               e a mutação ficaria verde por construção.
//   substituto  o defeito de volta, escrito por extenso.
//   vermelho    os NOMES de asserção que TÊM de ficar vermelhos. Se a mutação
//               passar, o runner sai `rc=1` e diz qual regra não guarda nada.
//
// ⛔ A mutação é por CÓPIA e o restauro mora num `finally`: o arquivo volta
// byte a byte, e o runner CONFERE isso (hash antes/depois + `git status`
// idêntico). Rode com a árvore parada — enquanto alguém edita `app/` ou `lib/`,
// o restauro apagaria a edição daquele segundo.
//
export const MUTACOES = [
  { id: 'U1', arquivo: 'lib/atendimento/casos.ts',
    o_que: "reintroduzir o ramo `else stage = 'concluido'` do silêncio (48h)",
    reprova: '[2] (640 conversas velhas voltam a ser "encerradas" sem `resolvido_em`)',
    ancora: "  else if (fresca) stage = 'em_conversa';\n  else stage = 'parado';",
    substituto: "  else if (fresca) stage = 'em_conversa';\n  else stage = 'concluido';",
    vermelho: ['[2] as 640 em silêncio viram'] },

  { id: 'U2', arquivo: 'app/api/dashboard/conversas/[id]/route.ts',
    o_que: "o claim volta a gravar `status: 'HUMAN_REQUESTED'` junto de `claimed_by`",
    reprova: '[4] (o dono e o status voltam a ser a mesma coisa — ACHADO-1b)',
    ancora: '      .update({\n'
      + '        claimed_by: ctx.userId,\n'
      + '        claimed_by_name: myName,\n'
      + '        claimed_at: new Date().toISOString(),\n'
      + '      })',
    substituto: '      .update({\n'
      + '        claimed_by: ctx.userId,\n'
      + '        claimed_by_name: myName,\n'
      + '        claimed_at: new Date().toISOString(),\n'
      + "        status: 'HUMAN_REQUESTED',\n"
      + '      })',
    vermelho: ['[4] o claim grava `claimed_by/claimed_by_name/claimed_at` e NÃO `status`'] },

  // 🔴 A-3 — esta mutação ficava VERDE porque o MUNDO não tinha o defeito: nenhuma
  //    conversa da fixture tinha `claimed_by` E `status:'HUMAN_REQUESTED'` ao mesmo
  //    tempo, que é a combinação que o claim de `7f3f3eb` produzia (§1.2). Agora
  //    `cv-alfa-0066` existe, e o leitor não tem mais onde se esconder.
  { id: 'U3', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'a cascata volta a testar `status` ANTES de `claimed_by`',
    reprova: '[4] (a coluna "com a equipe" volta a ser inalcançável)',
    ancora: '  let stage: Stage;\n'
      + "  if (resolvido_em) stage = 'concluido';\n"
      + "  else if (dono) stage = 'com_equipe';\n"
      + "  else if (pediuPessoa) stage = 'precisa_de_voce';",
    substituto: '  let stage: Stage;\n'
      + "  if (resolvido_em) stage = 'concluido';\n"
      + "  else if (String(conversa?.status || '') === 'HUMAN_REQUESTED') stage = 'precisa_de_voce';\n"
      + "  else if (dono) stage = 'com_equipe';",
    vermelho: ['[4] a conversa que PEDIU UMA PESSOA e JÁ TEM DONO sai'] },

  { id: 'U3B', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'o `pediuPessoa` volta a ignorar o dono (o status decide sozinho)',
    reprova: '[4] (a próxima ação manda ASSUMIR uma conversa que já tem dono — R2/R7)',
    ancora: "  const pediuPessoa = !dono && String(conversa?.status || '') === 'HUMAN_REQUESTED';",
    substituto: "  const pediuPessoa = String(conversa?.status || '') === 'HUMAN_REQUESTED';",
    vermelho: ['[4] a conversa que JÁ TEM DONO não recebe "assuma a conversa"'] },

  // 🔴 A-4 — verde até aqui porque `[7]` só observava a projeção de CASOS, e o
  //    `.limit(120)` medido em §1.5 é o da FILA. O ramo não observado era o do
  //    defeito.
  { id: 'U4', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'voltar `.limit(120)` fixo na leitura de conversas da FILA',
    reprova: '[7] (73% do acervo da AutoFleet some de novo)',
    ancora: '      return q\n'
      + "        .order('last_message_at', { ascending: false })\n"
      + "        .order('id', { ascending: false })\n"
      + '        .range(de, ate);',
    substituto: '      return q\n'
      + "        .order('last_message_at', { ascending: false })\n"
      + "        .order('id', { ascending: false })\n"
      + '        .limit(120);',
    vermelho: ['[7] a FILA lê TODAS as conversas em lotes de 1.000'] },

  { id: 'U5', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'ignorar `opcoes.busca` na consulta (a busca volta a ser do cliente)',
    reprova: '[7] (um protocolo de 60 dias devolve "nada encontrado")',
    ancora: '  const busca = termoSeguro(opcoes.busca);',
    substituto: "  const busca = '';",
    vermelho: ['[7] sem `.limit(120)`; cursor'] },

  // ⚠️ A-6 — `indisponivel.esperas` tem DOIS escritores (a projeção e a semana).
  //    Mutar um só ficava verde. A mutação certa é a que faz o MAPA INTEIRO
  //    parar de aceitar escrita: é o `indisponivel: false` fixo do §1.3, e ele
  //    não se reproduz mexendo em uma linha só.
  { id: 'U6', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'fixar `indisponivel: false` em vez de marcar a fonte que falhou',
    reprova: '[8] (zero silencioso: a tela mostra 0 num dia em que ninguém olhou)',
    ancora: '  const indisponivel: Record<Fonte, boolean> = {\n'
      + '    conversas: false,\n'
      + '    sessoes: false,\n'
      + '    esperas: false,\n'
      + '    trabalhos: false,\n'
      + '    aprovacoes: false,\n'
      + '  };',
    substituto: '  const indisponivel: Record<Fonte, boolean> = new Proxy(\n'
      + '    { conversas: false, sessoes: false, esperas: false, trabalhos: false, aprovacoes: false },\n'
      + '    { set: () => true },\n'
      + '  ) as Record<Fonte, boolean>;',
    vermelho: ['[8] derrubando `work_waits` no dublê'] },

  { id: 'U7', arquivo: 'app/api/dashboard/atendimentos/ficha/[id]/route.ts',
    o_que: 'um tipo de evento da timeline volta a nascer com `at: null`',
    reprova: '[10] (a timeline volta a ter evento sem hora — R8)',
    ancora: '      at: conversation.claimed_at,',
    substituto: '      at: null,',
    vermelho: ['[10] no mundo em que TODA fonte tem hora'] },

  // 🔴 A-1 — a mutação que provou que `[10]` era inatingível: o produto
  //    DESCARTAVA o evento sem hora antes de o guarda olhar, e por isso zerar um
  //    `at` não deixava nada vermelho. Aqui o descarte volta, e o guarda vê.
  { id: 'U7B', arquivo: 'app/api/dashboard/atendimentos/ficha/[id]/route.ts',
    o_que: 'o `põe()` volta a DESCARTAR em silêncio o evento sem hora',
    reprova: '[10] (o passo que aconteceu evapora da ficha, e a saída fica impecável)',
    ancora: '  const põe = (e: TimelineEvent | null) => {\n'
      + '    if (!e) return;\n'
      + '    timeline.push(e.at ? e : { ...e, at: null, sem_hora: true });\n'
      + '  };',
    substituto: '  const põe = (e: TimelineEvent | null) => {\n'
      + '    if (e && e.at) timeline.push(e);\n'
      + '  };',
    vermelho: ['[10] a Ficha NÃO esconde o evento sem hora'] },

  { id: 'U8', arquivo: 'app/api/dashboard/atendimentos/route.ts',
    o_que: 'a rota volta a montar a lista com consulta própria em vez de chamar `projetarCasos`',
    reprova: '[1] (duas funções de leitura: Fila e Casos divergem — G4 regride)',
    ancora: '  const projecao = await projetarCasos(ctx, estagio ? { estagio } : {}, '
      + "{ group_by: 'stage' });",
    substituto: "  const { getSupabaseAdmin: __sb } = require('@/lib/vault/server');\n"
      + '  await __sb()\n'
      + "    .from('conversations')\n"
      + "    .select('id, status, user_phone, last_message_at')\n"
      + "    .eq('company_id', ctx.companyId)\n"
      + "    .eq('channel', 'whatsapp')\n"
      + '    .limit(120);\n'
      + '  const projecao = await projetarCasos(ctx, estagio ? { estagio } : {}, '
      + "{ group_by: 'stage' });",
    vermelho: ['[1] a rota da Fila não tem consulta própria'] },

  { id: 'U11', arquivo: 'lib/atendimento/casos.ts',
    o_que: "remover o `.eq('company_id', …)` de UMA das fontes da projeção",
    reprova: '[11] (vazamento entre corretoras — CLAUDE.md §7)',
    ancora: "      .eq('company_id', companyId) // 🔴 R9/§7\n"
      + "      .eq('status', 'ativo')\n"
      + '      .limit(TETO_DE_CONTEXTO),',
    substituto: "      .eq('status', 'ativo')\n"
      + '      .limit(TETO_DE_CONTEXTO),',
    vermelho: ['[11] a sessão de Beta só vê Beta'] },

  { id: 'U12', arquivo: 'app/api/dashboard/atendimentos/ficha/[id]/route.ts',
    o_que: 'acrescentar `work_events` como fonte da timeline',
    reprova: '[10] (telemetria de motor vira evento do atendimento — §18/R8)',
    ancora: "  const firstMsg = msgs.find((m) => m.role === 'user');",
    substituto: '  const { data: __telemetria } = await supabase\n'
      + "    .from('work_events')\n"
      + "    .select('id, event_type, created_at')\n"
      + "    .eq('company_id', ctx.companyId)\n"
      + '    .limit(50);\n'
      + '  for (const ev of (__telemetria || []) as Record<string, string>[]) {\n'
      + '    põe({\n'
      + '      at: ev.created_at,\n'
      + "      label: String(ev.event_type || 'run.leased'),\n"
      + '      detail: null,\n'
      + '      done: true,\n'
      + "      fonte: 'work_events' as never,\n"
      + '      fonte_id: String(ev.id),\n'
      + '    });\n'
      + '  }\n'
      + "  const firstMsg = msgs.find((m) => m.role === 'user');",
    vermelho: ['[10] a ficha NÃO consulta `work_events`'] },

  // 🔴 A-5 — `[13]` guardava uma LISTA FECHADA de palavras técnicas, não a regra
  //    R11. `precisa_de_voce` e `com_equipe` são snake_case SEM ponto e fora da
  //    lista: passavam verdes direto para o card do corretor.
  { id: 'M13', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'o texto do card vira a chave crua do estágio (`detalhe = stage`)',
    reprova: "[13] (o corretor vê 'precisa_de_voce' em vez de \"pediu uma pessoa\" — R11)",
    ancora: '    detalhe: situacao,',
    substituto: '    detalhe: stage,',
    vermelho: ['[13] `detalhe`/`titulo`'] },

  { id: 'M14', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'trocar `vence_em` por `due_at` na consulta a `work_waits` (a coluna NÃO existe no banco)',
    reprova: '[14] (42703 — column work_waits.due_at does not exist; schema_vivo.json)',
    ancora: '      .select(\n'
      + "        'id, company_id, conversation_id, work_run_id, kind, scope, status, vence_em, created_at',\n"
      + '      )',
    substituto: '      .select(\n'
      + "        'id, company_id, conversation_id, work_run_id, kind, scope, status, due_at, created_at',\n"
      + '      )',
    vermelho: ['[14] `projetarCasos`/rotas de atendimento só pedem colunas'] },

  { id: 'M15', arquivo: 'app/api/dashboard/conversas/[id]/route.ts',
    o_que: 'tirar o 409 do `claim` numa conversa com `resolvido_em`',
    reprova: '[15] (o autor do atendimento encerrado é sobrescrito por quem clicou depois)',
    // ⚠️ o `claim` e o `release` têm o MESMO bloco de 409, palavra por palavra.
    //    A âncora desce até a linha de código que só existe no `claim` (o
    //    UPDATE atômico) — senão ela casaria nos dois e a mutação seria outra.
    ancora: '    if (conversation.resolvido_em) {\n'
      + '      return NextResponse.json(\n'
      + "        { error: 'Este atendimento já terminou. Para voltar a ele, é preciso reabri-lo.' },\n"
      + '        { status: 409 },\n'
      + '      );\n'
      + '    }\n'
      + '\n'
      + '    // Atômico: só assume se ninguém (ou eu mesmo) for o dono.\n'
      + '    const { data: updated, error } = await supabase',
    substituto: '    if (false && conversation.resolvido_em) {\n'
      + '      return NextResponse.json(\n'
      + "        { error: 'Este atendimento já terminou. Para voltar a ele, é preciso reabri-lo.' },\n"
      + '        { status: 409 },\n'
      + '      );\n'
      + '    }\n'
      + '\n'
      + '    // Atômico: só assume se ninguém (ou eu mesmo) for o dono.\n'
      + '    const { data: updated, error } = await supabase',
    vermelho: ['[15] assumir um atendimento ENCERRADO devolve 409'] },

  // 🔴 A-7 — `[15b]` media a ESCRITA do desfecho. A LEITURA ficava livre: o
  //    episódio herdava o `resolvido_em` da conversa e os 5,8 episódios daquele
  //    telefone apareciam encerrados de uma vez.
  { id: 'M16', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'o episódio volta a herdar `resolvido_em` DA CONVERSA em Casos',
    reprova: '[15] (encerrar UM atendimento marca os 5,8 episódios daquele telefone)',
    ancora: '  const resolvido_em = daSessao\n'
      + '    ? sessao?.resolvido_em || null\n'
      + '    : conversa?.resolvido_em || sessao?.resolvido_em || null;',
    substituto: '  const resolvido_em = conversa?.resolvido_em || sessao?.resolvido_em || null;',
    vermelho: ['[15] em CASOS, só o episódio com `resolvido_em` PRÓPRIO'] },

  // U9 (`mirror_conversation_id` obrigatório → [B1]) e U10 (backfill sem o 1:1
  // → [B4]) são do guarda irmão em python, e estão declaradas lá.
];
//
// ─────────────────────────────────────────────────────────────────────────────
// ⛔ SEGURANÇA
// ─────────────────────────────────────────────────────────────────────────────
//   · Sem rede, sem banco, sem escrita: os dublês são memória pura.
//   · NENHUM nome de pessoa, CPF, telefone real, apólice, placa, senha ou token
//     nas fixtures. As corretoras são sentinelas óbvias ("Corretora Alfa",
//     "Corretora Beta") e os telefones começam em +55 11 90000-0001.
//   · Duas corretoras SEMPRE: Alfa é a do teste, Beta existe para provar que
//     nada dela atravessa (CLAUDE.md §7 — o backend usa service role).
//
// Rodar:  npm run test:casa
//         node scripts/a-operacao-tem-uma-casa.test.mjs

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

// ─────────────────────────────────────────────────────────────────────────────
// As fixtures — duas corretoras, 700 conversas, 4.000 episódios (§4 BLOCO G)
// ─────────────────────────────────────────────────────────────────────────────
const CO_ALFA = 'co-alfa-0000-4000-8000-000000000001';
const CO_BETA = 'co-beta-0000-4000-8000-000000000002';
const U_ALFA = 'u-alfa-0000-4000-8000-000000000001';
const U_BETA = 'u-beta-0000-4000-8000-000000000002';

const AGORA = Date.now();
const H = 3600e3;
const D = 24 * H;
const iso = (ms) => new Date(ms).toISOString();

/** 📊 §1.1 — 700 conversas de Alfa: 60 vivas (<48h), 640 em silêncio. */
const N_CONVERSAS_ALFA = 700;
const N_FRESCAS = 60;
const N_VELHAS = N_CONVERSAS_ALFA - N_FRESCAS;   // 640
const N_RESOLVIDAS = 3;
const N_ASSUMIDAS = 2;
/**
 * 🔴 A-3 — A CONVERSA DO DEFEITO HISTÓRICO, e ela faltava.
 *
 * 📊 §1.2: o único escritor de `claimed_by` gravava `status:'HUMAN_REQUESTED'`
 * JUNTO, e a cascata testava o status antes do dono — "com a equipe" era
 * inalcançável. A fixture tinha `assumida` (dono, status `open`) e `pediuPessoa`
 * (status `HUMAN_REQUESTED`, sem dono) em índices DISJUNTOS: o mundo defeituoso
 * — as duas coisas na MESMA linha — não existia. Sem ele, o leitor podia voltar
 * a testar o status primeiro e a suíte ficava verde (mutação U3).
 */
const I_ASSUMIDA_E_PEDIU = N_FRESCAS + N_RESOLVIDAS + N_ASSUMIDAS + 1;
const CONVERSA_DO_DEFEITO = `cv-alfa-${String(I_ASSUMIDA_E_PEDIU).padStart(4, '0')}`;
/** 📊 §1.4 — 4.000 episódios (5,8 por telefone), 90% com elo, 10% órfãos. */
const N_SESSOES_ALFA = 4000;
const PROTOCOLO_ANTIGO = 'PROT-8821-ABRIL';   // o protocolo de 60 dias do §0
/** a conversa ASSUMIDA (indice 63) — e a que a Ficha abre em [10]. */
const CONVERSA_DA_FICHA = `cv-alfa-${String(N_FRESCAS + N_RESOLVIDAS).padStart(4, '0')}`;

function telefone(i) {
  // +55 11 90000-0001 … — sentinelas óbvias, nunca número de pessoa.
  return `5511900000${String(i % 10000).padStart(4, '0')}`;
}

function mundoAlfa() {
  const conversations = [];
  for (let i = 0; i < N_CONVERSAS_ALFA; i++) {
    const fresca = i < N_FRESCAS;
    const resolvida = i >= N_FRESCAS && i < N_FRESCAS + N_RESOLVIDAS;
    const assumida = i >= N_FRESCAS + N_RESOLVIDAS && i < N_FRESCAS + N_RESOLVIDAS + N_ASSUMIDAS;
    const pediuPessoa = i === N_FRESCAS + N_RESOLVIDAS + N_ASSUMIDAS;   // exatamente 1
    // 🔴 A-3 — dono E `HUMAN_REQUESTED` na MESMA linha (o que o claim de
    //    `7f3f3eb` gravava). Ela TEM de sair em 'com_equipe': o dono vence.
    const assumidaEPediu = i === I_ASSUMIDA_E_PEDIU;
    conversations.push({
      id: `cv-alfa-${String(i).padStart(4, '0')}`,
      company_id: CO_ALFA,
      channel: 'whatsapp',
      // 📊 §1.1: `closed` NÃO existe no acervo (0/728). O status nunca foi o desfecho.
      status: pediuPessoa || assumidaEPediu ? 'HUMAN_REQUESTED' : 'open',
      user_phone: telefone(i),
      user_name: `Segurado Alfa ${i}`,
      last_message_preview: 'mensagem de exemplo',
      last_message_at: iso(AGORA - (fresca ? (i + 1) * H : (3 + i) * D)),
      created_at: iso(AGORA - (30 + i) * D),
      session_id: `ss-alfa-${i}`,
      claimed_by: assumida || assumidaEPediu ? U_ALFA : null,
      claimed_by_name: assumida || assumidaEPediu ? 'Ana da Equipe' : null,
      claimed_at: assumida || assumidaEPediu ? iso(AGORA - 6 * H) : null,
      // 🔴 R1 — o ÚNICO desfecho. 3 conversas, todas dentro da semana.
      resolvido_em: resolvida ? iso(AGORA - 2 * D) : null,
      resolucao_motivo: resolvida ? 'acionamento_concluido' : null,
      unblock_state: null,
    });
  }

  // 📊 §1.4 — 4.000 episódios sobre ~690 telefones (5,8 por contato).
  const attendance_sessions = [];
  for (let i = 0; i < N_SESSOES_ALFA; i++) {
    const daConversa = i % 10 !== 9;    // 90% com elo; 10% órfãos (E7)
    const alvo = i % N_CONVERSAS_ALFA;
    attendance_sessions.push({
      id: `as-alfa-${String(i).padStart(4, '0')}`,
      company_id: CO_ALFA,
      // 🔴 R3/U3.1 — a coluna NOVA. Em `7f3f3eb` ela não existe no banco; aqui
      //    a fixture já a traz, porque é ela que o read model precisa ler.
      conversation_id: daConversa ? `cv-alfa-${String(alvo).padStart(4, '0')}` : null,
      counterparty: telefone(alvo),
      observer_number: '5511900009999',
      // 📊 E9 — `status` fechado por 6h de silêncio (attendance_distiller) NÃO é
      //    desfecho. A projeção o ignora para ENCERRADO.
      status: i % 3 === 0 ? 'open' : 'closed',
      started_at: iso(AGORA - (2 + (i % 60)) * D),
      last_event_at: iso(AGORA - (1 + (i % 60)) * D),
      resolvido_em: null,
      resolucao_motivo: null,
      summary: { distilled: { servico: 'guincho', tipo: 'assistencia', protocolo: i === 7 ? PROTOCOLO_ANTIGO : null } },
      protocolo: i === 7 ? PROTOCOLO_ANTIGO : null,
      ramo: 'auto',
      servico: 'guincho',
    });
  }

  // 📊 §1.3 — `work_waits`: 5 ativos (3 seguradora, 2 cliente), 1 vencido.
  const work_waits = [
    { id: 'ww-1', company_id: CO_ALFA, conversation_id: 'cv-alfa-0000', attendance_session_id: 'as-alfa-0000', kind: 'esperando_seguradora', status: 'ativo', scope: 'acionamento', vence_em: iso(AGORA + 6 * H), due_at: iso(AGORA + 6 * H), created_at: iso(AGORA - 2 * D) },
    { id: 'ww-2', company_id: CO_ALFA, conversation_id: 'cv-alfa-0001', attendance_session_id: 'as-alfa-0001', kind: 'esperando_seguradora', status: 'ativo', scope: 'acionamento', vence_em: iso(AGORA + 12 * H), due_at: iso(AGORA + 12 * H), created_at: iso(AGORA - 1 * D) },
    // 🔴 o VENCIDO — `due_at` no passado (R6: `espera_vencida`)
    { id: 'ww-3', company_id: CO_ALFA, conversation_id: 'cv-alfa-0002', attendance_session_id: 'as-alfa-0002', kind: 'esperando_seguradora', status: 'ativo', scope: 'acionamento', vence_em: iso(AGORA - 5 * H), due_at: iso(AGORA - 5 * H), created_at: iso(AGORA - 3 * D) },
    { id: 'ww-4', company_id: CO_ALFA, conversation_id: 'cv-alfa-0003', attendance_session_id: 'as-alfa-0003', kind: 'esperando_cliente', status: 'ativo', scope: 'default', vence_em: iso(AGORA + 2 * D), due_at: iso(AGORA + 2 * D), created_at: iso(AGORA - 1 * D) },
    { id: 'ww-5', company_id: CO_ALFA, conversation_id: 'cv-alfa-0004', attendance_session_id: 'as-alfa-0004', kind: 'esperando_cliente', status: 'ativo', scope: 'default', vence_em: null, due_at: null, created_at: iso(AGORA - 1 * D) },
    // e um SATISFEITO, que não pode aparecer como espera ativa
    { id: 'ww-6', company_id: CO_ALFA, conversation_id: 'cv-alfa-0005', attendance_session_id: 'as-alfa-0005', kind: 'esperando_cliente', status: 'satisfeito', scope: 'default', vence_em: iso(AGORA - 9 * D), due_at: iso(AGORA - 9 * D), created_at: iso(AGORA - 10 * D) },
    // 🔴 SPEC-097.1 U1.3/E6 — A CONVERSA COM **DUAS** ESPERAS ATIVAS.
    //
    // ⚠️ Sem este par, a regra da escolha (menor `vence_em`; empate →
    // `pos_acionamento`) nunca era EXERCITADA: o dublê tinha no máximo uma
    // espera por conversa, e a projeção passava por sorte. `cv-alfa-0000` já
    // tinha a do TRAVAMENTO (`ww-1`, vence em 6h); esta é a do PÓS, e vence
    // ANTES — então é ela que a tela tem de mostrar.
    { id: 'ww-7', company_id: CO_ALFA, conversation_id: 'cv-alfa-0000', attendance_session_id: 'as-alfa-0000', kind: 'esperando_seguradora', status: 'ativo', scope: 'pos_acionamento', vence_em: iso(AGORA + 2 * H), due_at: iso(AGORA + 2 * H), created_at: iso(AGORA - 1 * D) },
  ];

  // 📊 §1.6 — 2 `work_runs` failed COM conversa (R6: `trabalho_falhou`).
  const work_runs = [
    { id: 'wr-1', company_id: CO_ALFA, conversation_id: 'cv-alfa-0010', status: 'failed', runtime_kind: 'acionamento', unblock_state: 'travado', current_step_key: 'ura.menu', error_code: 'ura_timeout', error_message: 'O acionamento parou e precisa de uma pessoa.', created_at: iso(AGORA - 2 * D), input_payload: { case_id: 'case-1', playbook_ref: 'porto-auto', subservice: 'guincho' } },
    { id: 'wr-2', company_id: CO_ALFA, conversation_id: 'cv-alfa-0011', status: 'failed', runtime_kind: 'acionamento', unblock_state: 'assumido_por_humano', current_step_key: 'ura.protocolo', error_code: 'ura_timeout', error_message: 'O acionamento parou e precisa de uma pessoa.', created_at: iso(AGORA - 3 * D), input_payload: { case_id: 'case-2', playbook_ref: 'hdi-auto', subservice: 'pneu' } },
  ];

  // 📊 §1.6/E17 — `approval_requests` NÃO tem conversa. A ponte é run→conversa.
  const approval_requests = [
    { id: 'ap-1', company_id: CO_ALFA, work_run_id: 'wr-1', status: 'pending', created_at: iso(AGORA - 1 * D), title: 'Confirmar acionamento' },
  ];

  // 🔴 duas conversas com histórico: a viva (cv-alfa-0000) e a ASSUMIDA
  //    (CONVERSA_DA_FICHA) — é a assumida que faz a Ficha emitir os tipos de
  //    evento que hoje nascem com `at: null` ("Cliente identificado",
  //    "<Fulana> assumiu", "Atendimento concluído").
  const messages = [];
  for (const alvo of ['cv-alfa-0000', CONVERSA_DA_FICHA]) {
    for (let i = 0; i < 40; i++) {
      messages.push({
        id: `msg-${alvo}-${String(i).padStart(3, '0')}`,
        conversation_id: alvo,
        company_id: CO_ALFA,
        role: i % 2 === 0 ? 'user' : 'assistant',
        type: 'text',
        content: `mensagem ${i}`,
        image_url: null, audio_url: null, sender_user_id: null,
        created_at: iso(AGORA - (40 - i) * H),
      });
    }
  }

  return { conversations, attendance_sessions, work_waits, work_runs, approval_requests, messages };
}

function mundoBeta() {
  const conversations = [];
  const attendance_sessions = [];
  for (let i = 0; i < 50; i++) {
    conversations.push({
      id: `cv-beta-${String(i).padStart(4, '0')}`,
      company_id: CO_BETA, channel: 'whatsapp', status: 'open',
      user_phone: `5511911110${String(i).padStart(3, '0')}`,
      user_name: `SEGURADO BETA ${i} — nao pode aparecer`,
      last_message_preview: 'BETA', last_message_at: iso(AGORA - (i + 1) * H),
      created_at: iso(AGORA - 40 * D), session_id: `ss-beta-${i}`,
      claimed_by: null, claimed_by_name: null, claimed_at: null,
      resolvido_em: null, resolucao_motivo: null, unblock_state: null,
    });
    attendance_sessions.push({
      id: `as-beta-${String(i).padStart(4, '0')}`,
      company_id: CO_BETA, conversation_id: `cv-beta-${String(i).padStart(4, '0')}`,
      counterparty: `5511911110${String(i).padStart(3, '0')}`,
      observer_number: '5511911119999', status: 'open',
      started_at: iso(AGORA - 5 * D), last_event_at: iso(AGORA - 1 * D),
      resolvido_em: null, resolucao_motivo: null,
      summary: { distilled: { servico: 'BETA' } }, protocolo: null,
      ramo: 'auto', servico: 'guincho',
    });
  }
  const work_waits = [{ id: 'ww-beta-1', company_id: CO_BETA, conversation_id: 'cv-beta-0000', attendance_session_id: 'as-beta-0000', kind: 'esperando_cliente', status: 'ativo', scope: 'default', vence_em: iso(AGORA + D), due_at: iso(AGORA + D), created_at: iso(AGORA - D) }];
  const work_runs = [{ id: 'wr-beta-1', company_id: CO_BETA, conversation_id: 'cv-beta-0000', status: 'failed', runtime_kind: 'acionamento', unblock_state: 'travado', current_step_key: 'x', error_code: 'x', error_message: 'BETA', created_at: iso(AGORA - D), input_payload: { case_id: 'case-beta' } }];
  const approval_requests = [{ id: 'ap-beta-1', company_id: CO_BETA, work_run_id: 'wr-beta-1', status: 'pending', created_at: iso(AGORA - D), title: 'BETA' }];
  const messages = [{ id: 'msg-beta-0', conversation_id: 'cv-beta-0000', company_id: CO_BETA, role: 'user', type: 'text', content: 'BETA', image_url: null, audio_url: null, sender_user_id: null, created_at: iso(AGORA - D) }];
  return { conversations, attendance_sessions, work_waits, work_runs, approval_requests, messages };
}

function fixtures() {
  const a = mundoAlfa();
  const b = mundoBeta();
  const junta = (k) => [...a[k], ...b[k]];
  return {
    companies: [
      { id: CO_ALFA, name: 'Corretora Alfa' },
      { id: CO_BETA, name: 'Corretora Beta' },
    ],
    users_v2: [
      { id: U_ALFA, company_id: CO_ALFA, name: 'Ana da Equipe', email: 'ana@alfa.local' },
      { id: U_BETA, company_id: CO_BETA, name: 'Beto de Beta', email: 'beto@beta.local' },
    ],
    conversations: junta('conversations'),
    attendance_sessions: junta('attendance_sessions'),
    work_waits: junta('work_waits'),
    work_runs: junta('work_runs'),
    approval_requests: junta('approval_requests'),
    messages: junta('messages'),
    // ⛔ existe de propósito, VAZIA: nenhuma projeção pode lê-la (R8/§18).
    work_events: [],
  };
}

/**
 * 🔴 A-1 — O MUNDO EM QUE UMA FONTE NÃO TEM HORA.
 *
 * A fixture grande tem relógio em tudo, e por isso `[10]` nunca conseguia
 * distinguir "a timeline tem hora" de "a timeline ESCONDE o que não tem hora":
 * zerar o `at` de uma fonte deixava a suíte VERDE, porque o evento simplesmente
 * sumia da Ficha (`if (e && e.at) timeline.push(e)`).
 *
 * Aqui a conversa não tem `created_at` NEM mensagem — o "o segurado pediu
 * ajuda" e o "segurado identificado" nascem sem hora POR FALTA DE FONTE, não
 * por mutação. E ela TEM `claimed_at`: assim a linha do tempo mistura os dois
 * casos, e dá para exigir que o que tem hora venha ANTES.
 *
 * 📊 É um mundo real: `conversations.created_at` é anulável e o acervo tem
 * conversas sem uma única mensagem persistida.
 */
const CONVERSA_SEM_HORA = 'cv-sh-0001';
function mundoSemHora() {
  return {
    companies: [{ id: CO_ALFA, name: 'Corretora Alfa' }],
    users_v2: [{ id: U_ALFA, company_id: CO_ALFA, name: 'Ana da Equipe', email: 'ana@alfa.local' }],
    conversations: [
      {
        id: CONVERSA_SEM_HORA,
        company_id: CO_ALFA,
        channel: 'whatsapp',
        status: 'open',
        user_phone: telefone(77),
        user_name: 'Segurado Sem Relogio',
        last_message_preview: 'x',
        last_message_at: iso(AGORA - 2 * H),
        // ⛔ SEM `created_at`: a abertura e a identificação não têm de onde tirar hora.
        created_at: null,
        session_id: 'ss-sh-1',
        claimed_by: U_ALFA,
        claimed_by_name: 'Ana da Equipe',
        claimed_at: iso(AGORA - 1 * H),   // 🔴 ESTE tem hora — e tem de vir ANTES
        resolvido_em: null,
        resolucao_motivo: null,
        unblock_state: null,
      },
    ],
    attendance_sessions: [],
    work_waits: [],
    work_runs: [],
    approval_requests: [],
    messages: [],
    work_events: [],
  };
}

/**
 * 🔴 A-7 — O MUNDO DO DERRAMAMENTO DO DESFECHO (a LEITURA, não a escrita).
 *
 * `[15b]` provava que "Encerrar" grava no episódio corrente. Ninguém media a
 * PROJEÇÃO: devolver `conversa?.resolvido_em || sessao?.resolvido_em` em Casos
 * marcava os 5,8 episódios médios daquele telefone como encerrados de uma vez
 * (📊 §1.4) — e a suíte ficava verde.
 *
 * Duas sessões da MESMA conversa, e a conversa TEM desfecho. Só a sessão com
 * `resolvido_em` PRÓPRIO pode sair 'concluido'.
 */
function mundoDoDerramamento() {
  const base = {
    company_id: CO_ALFA,
    counterparty: telefone(88),
    observer_number: '5511900009999',
    summary: { distilled: { servico: 'guincho' } },
    ramo: 'auto',
    servico: 'guincho',
  };
  return {
    companies: [{ id: CO_ALFA, name: 'Corretora Alfa' }],
    users_v2: [],
    conversations: [
      {
        id: 'cv-d-0001', company_id: CO_ALFA, channel: 'whatsapp', status: 'open',
        user_phone: telefone(88), user_name: 'Segurado Derramamento',
        last_message_preview: 'x', last_message_at: iso(AGORA - 3 * H),
        created_at: iso(AGORA - 20 * D), session_id: 'ss-d-1',
        claimed_by: null, claimed_by_name: null, claimed_at: null,
        // 🔴 a CONVERSA terminou — e é SÓ ela e o episódio corrente que terminaram.
        resolvido_em: iso(AGORA - 2 * H), resolucao_motivo: 'acionamento_concluido',
        unblock_state: null,
      },
    ],
    attendance_sessions: [
      { ...base, id: 'as-d-fechado', conversation_id: 'cv-d-0001', status: 'closed',
        started_at: iso(AGORA - 4 * H), last_event_at: iso(AGORA - 2 * H),
        resolvido_em: iso(AGORA - 2 * H), resolucao_motivo: 'acionamento_concluido' },
      // ⛔ o episódio ANTIGO do mesmo telefone: sem desfecho PRÓPRIO
      { ...base, id: 'as-d-aberto', conversation_id: 'cv-d-0001', status: 'closed',
        started_at: iso(AGORA - 4 * D), last_event_at: iso(AGORA - 3 * D),
        resolvido_em: null, resolucao_motivo: null },
    ],
    work_waits: [],
    work_runs: [],
    approval_requests: [],
    messages: [],
    work_events: [],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso (o molde de 095/096).
// ─────────────────────────────────────────────────────────────────────────────
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }

// ─────────────────────────────────────────────────────────────────────────────
// 🔴 [14] SCHEMA VIVO — a lente do DADO. O dublê ATÉ AQUI aceitava qualquer
// coluna em `.select(...)`, e por isso ficou VERDE quando `casos.ts` pedia
// `work_waits.due_at`, `work_waits.attendance_session_id`,
// `attendance_sessions.protocolo` e `approval_requests.title` — NENHUMA
// existe no banco (📊 `backend/tests/fixtures/schema_vivo.json`, medido em
// information_schema.columns). O PostgREST real devolve 42703 para isto; o
// dublê agora faz o mesmo, e [14] acusa a consulta que pediu a coluna errada.
//
// ⚠️ `attendance_sessions` na fixture é ANTERIOR à migration desta SPEC: as
// 3 colunas que ELA acrescenta (`conversation_id`, `resolvido_em`,
// `resolucao_motivo`) são aceitas aqui porque a migration existe e as
// declara — lidas do PRÓPRIO arquivo `.sql`, nunca digitadas de novo.
// ─────────────────────────────────────────────────────────────────────────────
const CAMINHO_SCHEMA_VIVO = 'backend/tests/fixtures/schema_vivo.json';
const CAMINHO_MIGRATION_097 = 'backend/supabase/migrations/20260905_01_spec097_episodio_tem_conversa.sql';

const SCHEMA_VIVO = JSON.parse(fonte(CAMINHO_SCHEMA_VIVO));

/** As colunas que uma migration `ADD COLUMN IF NOT EXISTS` declara para `tabela`. */
function colunasDaMigration(caminhoRel, tabelaAlvo) {
  if (!existe(caminhoRel)) return [];
  const sql = fonte(caminhoRel);
  const re = new RegExp(`ALTER\\s+TABLE\\s+public\\.${tabelaAlvo}\\s+ADD\\s+COLUMN\\s+IF\\s+NOT\\s+EXISTS\\s+(\\w+)`, 'gi');
  const nomes = [];
  let m;
  while ((m = re.exec(sql))) nomes.push(m[1]);
  return nomes;
}

// O schema EFETIVO = o medido (schema_vivo.json) + o que ESTA SPEC acrescenta
// e já tem migration escrita — nunca um "achismo" de coluna que a SPEC ainda
// vai criar.
const SCHEMA_EFETIVO = JSON.parse(JSON.stringify(SCHEMA_VIVO.tabelas || {}));
for (const nomeDaColuna of colunasDaMigration(CAMINHO_MIGRATION_097, 'attendance_sessions')) {
  if (!SCHEMA_EFETIVO.attendance_sessions) SCHEMA_EFETIVO.attendance_sessions = {};
  SCHEMA_EFETIVO.attendance_sessions[nomeDaColuna] = 'timestamp with time zone';
}

/** `tabela` fora do schema_vivo (não é uma das 8 medidas) não trava — está fora do escopo desta fixture. */
function colunaExiste(tabela, coluna) {
  const t = SCHEMA_EFETIVO[tabela];
  if (!t) return true;
  return Object.prototype.hasOwnProperty.call(t, coluna);
}

/**
 * Parser do `select(...)` do PostgREST: vírgulas de topo (fora de parênteses),
 * alias `x:coluna` (fica com o que vem DEPOIS do `:`), relação `tabela(colunas)`
 * (fica só com o nome antes do `(` — a coluna interna não é desta tabela) e
 * `->`/`->>` (fica só com a parte ANTES do operador — o resto é chave de JSON).
 */
function colunasDoSelect(str) {
  const partes = [];
  let profundidade = 0;
  let atual = '';
  for (const ch of String(str || '')) {
    if (ch === '(') profundidade += 1;
    if (ch === ')') profundidade -= 1;
    if (ch === ',' && profundidade === 0) { partes.push(atual); atual = ''; }
    else atual += ch;
  }
  if (atual.trim()) partes.push(atual);

  const colunas = [];
  for (let p of partes) {
    p = p.trim();
    if (!p || p === '*') continue;
    const parenIdx = p.indexOf('(');
    if (parenIdx !== -1) p = p.slice(0, parenIdx).trim();       // relação: não valida colunas internas
    if (!p) continue;
    if (p.includes(':')) p = p.split(':').pop().trim();          // alias
    if (p.includes('->')) p = p.split('->')[0].trim();           // ->/->> : só a coluna
    p = p.replace(/::\w+$/, '').trim();                          // cast ::tipo
    p = p.replace(/^!(inner|left)\s*/i, '').trim();
    if (p) colunas.push(p);
  }
  return colunas;
}

function carregarTS(caminhoRelativo, resolverImport, opcoes = {}) {
  const saida = ts.transpileModule(fonte(caminhoRelativo), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      jsx: opcoes.jsx ?? ts.JsxEmit.None,
    },
    fileName: caminhoRelativo,
  }).outputText;
  const js = opcoes.jsx ? `const React = require('react');\n${saida}` : saida;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

// ─────────────────────────────────────────────────────────────────────────────
// Dublê de Supabase — o encadeamento do cliente real, com os filtros APLICADOS
// e TODA consulta REGISTRADA (from/select/eq/in/lt/gt/or/order/limit/range/
// textSearch/ilike). É o registro que prova onde a busca e a paginação moram.
// ─────────────────────────────────────────────────────────────────────────────
function valorDe(linha, coluna) {
  if (!/->/.test(String(coluna))) return linha[coluna];
  let v = linha;
  for (const p of String(coluna).split(/->>|->/).map((s) => s.replace(/^'|'$/g, ''))) {
    if (v == null) return undefined;
    v = v[p];
  }
  return v;
}

/**
 * @param linhasPorTabela  o mundo
 * @param registro         array que recebe uma entrada por consulta
 * @param falhar           Set de tabelas cuja consulta DEVE falhar (R5/[8])
 */
function dubleSupabase(linhasPorTabela, registro, falhar = new Set()) {
  function tabela(nome) {
    const consulta = {
      tabela: nome, op: 'select', colunas: '', opcoes: {},
      predicados: [], ordens: [], limite: null, range: null, payload: null,
      or: [], ilike: [], textSearch: [],
    };
    registro.push(consulta);
    const cadeia = {};
    cadeia.select = (colunas, opcoes) => {
      consulta.op = consulta.payload ? consulta.op : 'select';
      consulta.colunas = String(colunas ?? '');
      consulta.opcoes = opcoes ?? {};
      // 🔴 [14] — a validação do PostgREST real: coluna que não existe é 42703,
      // não uma linha inventada pelo dublê.
      consulta.colunasPedidas = colunasDoSelect(consulta.colunas);
      consulta.colunasInvalidas = consulta.colunasPedidas.filter((c) => !colunaExiste(nome, c));
      return cadeia;
    };
    cadeia.insert = (payload) => { consulta.op = 'insert'; consulta.payload = payload; return cadeia; };
    cadeia.update = (payload) => { consulta.op = 'update'; consulta.payload = payload; return cadeia; };
    cadeia.upsert = (payload) => { consulta.op = 'upsert'; consulta.payload = payload; return cadeia; };
    cadeia.delete = () => { consulta.op = 'delete'; return cadeia; };
    for (const op of ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'in', 'is', 'not']) {
      cadeia[op] = (coluna, valor, extra) => { consulta.predicados.push({ op, coluna, valor, extra }); return cadeia; };
    }
    // 🔴 O cursor `(ultimo_evento_em, id)` vive num `.or(...)` — e ele é
    //    REGISTRADO, não aplicado: o que este guarda afirma é que a paginação
    //    foi PEDIDA AO BANCO, não que o dublê saiba emular o PostgREST.
    cadeia.or = (expr) => { consulta.or.push(String(expr)); consulta.predicados.push({ op: 'or', coluna: '(or)', valor: String(expr) }); return cadeia; };
    cadeia.ilike = (coluna, padrao) => { consulta.ilike.push({ coluna, padrao }); consulta.predicados.push({ op: 'ilike', coluna, valor: padrao }); return cadeia; };
    cadeia.like = cadeia.ilike;
    cadeia.textSearch = (coluna, termo, opcoes) => { consulta.textSearch.push({ coluna, termo, opcoes }); consulta.predicados.push({ op: 'textSearch', coluna, valor: termo }); return cadeia; };
    cadeia.order = (coluna, opcoes) => { consulta.ordens.push({ coluna, ascendente: opcoes?.ascending !== false }); return cadeia; };
    cadeia.limit = (n) => { consulta.limite = n; return cadeia; };
    cadeia.range = (a, b) => { consulta.range = [a, b]; return cadeia; };

    const casa = (l, p) => {
      if (p.op === 'or' || p.op === 'textSearch') return true;      // registrado, não aplicado
      const v = valorDe(l, p.coluna);
      switch (p.op) {
        case 'eq': return String(v) === String(p.valor);
        case 'neq': return String(v) !== String(p.valor);
        case 'gt': return v != null && String(v) > String(p.valor);
        case 'gte': return v != null && String(v) >= String(p.valor);
        case 'lt': return v != null && String(v) < String(p.valor);
        case 'lte': return v != null && String(v) <= String(p.valor);
        case 'in': return (p.valor ?? []).map(String).includes(String(v));
        case 'is': return p.valor === null || p.valor === 'null' ? v == null : v === p.valor;
        case 'not': return p.extra === null || p.extra === 'null' ? v != null : String(v) !== String(p.extra);
        case 'ilike': {
          const re = new RegExp('^' + String(p.valor).replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*') + '$', 'i');
          return v != null && re.test(String(v));
        }
        default: return true;
      }
    };
    const resolver = () => {
      // 🔴 [14] — igual ao PostgREST: coluna inexistente falha ANTES de
      // qualquer outra coisa, com 42703 (a lente do DADO, não a do dublê).
      if (consulta.op === 'select' && (consulta.colunasInvalidas || []).length) {
        const erro = new Error(`column ${nome}.${consulta.colunasInvalidas[0]} does not exist`);
        erro.__schemaCode = '42703';
        throw erro;
      }
      if (falhar.has(nome)) {
        const erro = new Error(`FONTE_INDISPONIVEL: a consulta a "${nome}" falhou (dublê)`);
        erro.__fonte = nome;
        throw erro;
      }
      if (consulta.op !== 'select') {
        const regs = Array.isArray(consulta.payload) ? consulta.payload : [consulta.payload];
        const saida = [];
        for (const r of regs) {
          const alvos = (linhasPorTabela[nome] ?? []).filter((l) => consulta.predicados.every((p) => casa(l, p)));
          if (consulta.op === 'update' && alvos.length) {
            for (const l of alvos) Object.assign(l, r);
            saida.push(...alvos.map((l) => ({ ...l })));
          } else if (consulta.op === 'update') {
            /* nenhuma linha casou — é o caminho da idempotência */
          } else {
            const linha = { id: `${nome.slice(0, 3)}-${(linhasPorTabela[nome] || []).length + 1}`, ...r };
            (linhasPorTabela[nome] = linhasPorTabela[nome] || []).push(linha);
            saida.push(linha);
          }
        }
        return saida;
      }
      let linhas = (linhasPorTabela[nome] ?? []).filter((l) => consulta.predicados.every((p) => casa(l, p)));
      for (const { coluna, ascendente } of [...consulta.ordens].reverse()) {
        linhas = [...linhas].sort((a, b) => {
          const r = String(a[coluna] ?? '').localeCompare(String(b[coluna] ?? ''));
          return ascendente ? r : -r;
        });
      }
      if (consulta.limite != null) linhas = linhas.slice(0, consulta.limite);
      if (consulta.range) linhas = linhas.slice(consulta.range[0], consulta.range[1] + 1);
      return linhas;
    };
    const corpo = () => {
      try {
        const linhas = resolver();
        const o = consulta.opcoes || {};
        return o.head
          ? { data: null, count: linhas.length, error: null }
          : { data: linhas, count: o.count ? linhas.length : null, error: null };
      } catch (e) {
        const codigo = e.__schemaCode || 'FONTE_INDISPONIVEL';
        return { data: null, count: null, error: { message: String(e.message), code: codigo } };
      }
    };
    cadeia.maybeSingle = () => { const c = corpo(); return Promise.resolve({ data: (c.data || [])[0] ?? null, error: c.error }); };
    cadeia.single = () => { const c = corpo(); const l = c.data || []; return Promise.resolve({ data: l[0] ?? null, error: c.error || (l.length ? null : { message: 'no rows' }) }); };
    cadeia.then = (ok, err) => Promise.resolve(corpo()).then(ok, err);
    cadeia.catch = (f) => Promise.resolve(corpo()).catch(f);
    return cadeia;
  }
  return { from: tabela };
}

// ─────────────────────────────────────────────────────────────────────────────
// O placar — três verbos (o molde de 095/096/protocolo §5)
// ─────────────────────────────────────────────────────────────────────────────
const falhas = [];
function checar(problemas, nome) {
  if (problemas.length === 0) { console.log(`  OK  ${nome}`); }
  else { falhas.push(nome); console.log(`  X   ${nome}`); for (const p of problemas) console.log(`        ${p}`); }
}
function controle(problemas, nome) {
  if (problemas.length > 0) { console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`); }
  else { falhas.push(`CONTROLE ${nome}`); console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Executar o produto — a projeção e as rotas, sobre os dublês
// ─────────────────────────────────────────────────────────────────────────────
class NextResponseFalsa {
  static json(body, init) {
    return { __json: true, body, status: init?.status ?? 200 };
  }
}
const NEXT_SERVER = { NextResponse: NextResponseFalsa, NextRequest: class {} };

async function silenciando(fn) {
  const orig = { log: console.log, error: console.error, warn: console.warn, info: console.info };
  console.log = console.error = console.warn = console.info = () => {};
  try { return await fn(); }
  finally { Object.assign(console, orig); }
}

const CAMINHO_PROJECAO = 'lib/atendimento/casos.ts';
const CAMINHO_FILA = 'app/api/dashboard/atendimentos/route.ts';
const CAMINHO_FICHA = 'app/api/dashboard/atendimentos/ficha/[id]/route.ts';
const CAMINHO_CLAIM = 'app/api/dashboard/conversas/[id]/route.ts';
const CAMINHO_CASOS_CLIENTE = 'app/dashboard/atendimentos/casos/HistoricoClient.tsx';
const CAMINHO_FILA_CLIENTE = 'app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx';
const CAMINHO_MODULOS = 'lib/mock/tenant-modules.ts';
const CAMINHO_ESTAGIOS = 'lib/attendance/dispatch-states.ts';

/** O resolvedor de imports comum às rotas e à projeção. */
function resolvedor({ supabase, sessao }) {
  return (id) => {
    if (id === 'next/server') return NEXT_SERVER;
    if (id === '@/lib/vault/server' || id === '@/lib/auxiliaries/server') {
      return { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => supabase };
    }
    if (id === '@/lib/backend-url') {
      return { getBackendUrl: () => 'http://backend.local', BackendUrlError: class extends Error {} };
    }
    if (id === '@/lib/attendance/dispatch-states') return carregarTS(CAMINHO_ESTAGIOS, () => undefined);
    if (id === '@/lib/atendimento/casos') {
      if (!existe(CAMINHO_PROJECAO)) throw new Error(`MODULO_AUSENTE: ${CAMINHO_PROJECAO}`);
      return carregarTS(CAMINHO_PROJECAO, resolvedor({ supabase, sessao }));
    }
    // 🔴 os módulos REAIS: o claim passa por eles, e trocá-los por vazio faria
    //    [4] medir um caminho que não é o do produto.
    if (id === '@/lib/atendimento/a-nota-da-atendente') return carregarTS('lib/atendimento/a-nota-da-atendente.ts', () => ({}));
    if (id === '@/lib/atendimento/claims-shadow') return carregarTS('lib/atendimento/claims-shadow.ts', () => ({}));
    if (id === '@/lib/atendimento/claims-shadow-vocab.json') return { default: JSON.parse(fonte('lib/atendimento/claims-shadow-vocab.json')) };
    if (id.startsWith('@/lib/') || id.startsWith('@/components/') || id.startsWith('@/hooks/')) return {};
    return {};
  };
}

/** Roda `projetarCasos`. Nunca estoura: devolve `{ erro }` com a CAUSA CRUA. */
async function observarProjecao({ companyId = CO_ALFA, filtro = {}, opcoes = {}, falhar = new Set(), linhas } = {}) {
  const mundo = linhas || fixtures();
  const registro = [];
  const supabase = dubleSupabase(mundo, registro, falhar);
  const sessao = { companyId, userId: companyId === CO_ALFA ? U_ALFA : U_BETA };
  if (!existe(CAMINHO_PROJECAO)) {
    return { erro: `MODULO_AUSENTE: ${CAMINHO_PROJECAO} não existe (R5/U5.1 — a ÚNICA função de leitura ainda não foi escrita)`, registro, mundo };
  }
  try {
    const mod = carregarTS(CAMINHO_PROJECAO, resolvedor({ supabase, sessao }));
    const projetar = mod.projetarCasos || mod.default;
    if (typeof projetar !== 'function') {
      return { erro: `SEM_EXPORT: ${CAMINHO_PROJECAO} existe mas não exporta \`projetarCasos\``, registro, mundo };
    }
    const saida = await silenciando(() => projetar(sessao, filtro, opcoes));
    return { saida, registro, mundo };
  } catch (e) {
    return { erro: `${e.name}: ${e.message}`, registro, mundo };
  }
}

/** Roda uma rota GET do BFF. Nunca estoura: devolve `{ erro }` com a causa crua. */
async function observarRota(caminho, { companyId = CO_ALFA, params = null, url = 'http://t.local/x', falhar = new Set(), linhas } = {}) {
  const mundo = linhas || fixtures();
  const registro = [];
  const supabase = dubleSupabase(mundo, registro, falhar);
  const sessao = { companyId, userId: companyId === CO_ALFA ? U_ALFA : U_BETA };
  if (!existe(caminho)) return { erro: `ARQUIVO_AUSENTE: ${caminho}`, registro, mundo };
  const fetchOriginal = globalThis.fetch;
  const chamadasFetch = [];
  globalThis.fetch = async (u, opts = {}) => {
    chamadasFetch.push({ url: String(u), headers: opts.headers || {} });
    // 📊 sem acionamento ativo: o Redis não é fonte desta SPEC.
    return { ok: true, status: 200, json: async () => ({ dispatches: [] }), text: async () => '{}' };
  };
  try {
    const mod = carregarTS(caminho, resolvedor({ supabase, sessao }));
    if (typeof mod.GET !== 'function') return { erro: `SEM_GET: ${caminho} não exporta GET`, registro, mundo };
    const pedido = { url, nextUrl: new URL(url), headers: new Map(), json: async () => ({}) };
    const ctx = params ? { params: Promise.resolve(params) } : undefined;
    const resposta = await silenciando(() => mod.GET(pedido, ctx));
    return { corpo: resposta?.body, status: resposta?.status ?? 200, registro, mundo, chamadasFetch };
  } catch (e) {
    return { erro: `${e.name}: ${e.message}`, registro, mundo, chamadasFetch };
  } finally {
    globalThis.fetch = fetchOriginal;
  }
}

/** Roda o POST de `conversas/[id]` (o claim). Devolve o payload do UPDATE. */
async function observarClaim({ companyId = CO_ALFA, acao = 'claim', corpoExtra = {}, id = 'cv-alfa-0000', linhas = null } = {}) {
  const mundo = linhas || fixtures();
  const registro = [];
  const supabase = dubleSupabase(mundo, registro);
  const sessao = { companyId, userId: U_ALFA };
  if (!existe(CAMINHO_CLAIM)) return { erro: `ARQUIVO_AUSENTE: ${CAMINHO_CLAIM}`, registro, mundo };
  const fetchOriginal = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({}), text: async () => '' });
  try {
    const mod = carregarTS(CAMINHO_CLAIM, resolvedor({ supabase, sessao }));
    if (typeof mod.POST !== 'function') return { erro: `SEM_POST: ${CAMINHO_CLAIM}`, registro, mundo };
    const pedido = { url: 'http://t.local/c', json: async () => ({ action: acao, ...corpoExtra }) };
    const resposta = await silenciando(() => mod.POST(pedido, { params: Promise.resolve({ id }) }));
    const updates = registro.filter((c) => c.tabela === 'conversations' && c.op === 'update');
    const updatesDeSessao = registro.filter((c) => c.tabela === 'attendance_sessions' && c.op === 'update');
    return { corpo: resposta?.body, status: resposta?.status ?? 200, registro, updates, updatesDeSessao, mundo };
  } catch (e) {
    return { erro: `${e.name}: ${e.message}`, registro, mundo };
  } finally {
    globalThis.fetch = fetchOriginal;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Os analisadores — cada um recebe uma OBSERVAÇÃO (o que o produto produziu) e
// devolve a lista de problemas. É o que permite ao PAR ser sintético: a mesma
// régua, sobre uma observação com o defeito de propósito.
// ─────────────────────────────────────────────────────────────────────────────

const itensDe = (o) => (o?.saida?.items ?? o?.corpo?.items ?? []);
const assinatura = (registro) => (registro || [])
  .filter((c) => c.op === 'select')
  .map((c) => `${c.tabela}:${[...new Set(c.predicados.map((p) => `${p.op}(${p.coluna})`))].sort().join('+')}`);

// [1] R5/U5 — Fila e Casos chamam a MESMA função.
function analisarUmaFuncao({ rota, projecao }) {
  const p = [];
  if (rota?.erro) { p.push(`a rota da Fila não executou: ${rota.erro}`); }
  if (projecao?.erro) { p.push(`projetarCasos não executou: ${projecao.erro}`); }
  if (p.length) return p;
  const aRota = assinatura(rota.registro);
  const aFuncao = assinatura(projecao.registro);
  if (aRota.length === 0) p.push('a rota da Fila não consultou NADA — não pode estar lendo o read model');
  const soDaRota = aRota.filter((x) => !aFuncao.includes(x));
  if (soDaRota.length) {
    p.push('a rota da Fila tem consulta PRÓPRIA, que `projetarCasos` não faz — são DUAS funções de leitura (G4 regride):');
    for (const x of [...new Set(soDaRota)]) p.push(`    · ${x}`);
  }
  return p;
}

// [1b] o Quadro é `group_by:'stage'` da MESMA função.
function analisarQuadro({ quadro }) {
  const p = [];
  if (quadro?.erro) return [`projetarCasos({group_by:'stage'}) não executou: ${quadro.erro}`];
  const counts = quadro.saida?.counts;
  if (!counts || typeof counts !== 'object') {
    p.push("`group_by:'stage'` não devolveu `counts` — o Quadro não é uma lente da mesma função (R5)");
    return p;
  }
  const soma = Object.values(counts).reduce((a, b) => a + (Number(b) || 0), 0);
  if (soma !== itensDe(quadro).length) {
    p.push(`os \`counts\` (${soma}) não somam os \`items\` (${itensDe(quadro).length}) — o Quadro conta outra coisa que a Lista`);
  }
  return p;
}

// [2] R1 — silêncio vira `parado`, NUNCA `concluido`.
function analisarParado({ observacao, mundo }) {
  const p = [];
  if (observacao?.erro) return [`a projeção da Fila não executou: ${observacao.erro}`];
  const items = itensDe(observacao);
  if (!items.length) return ['a projeção da Fila devolveu ZERO itens — nada foi medido'];
  const porId = new Map((mundo?.conversations || []).map((c) => [c.id, c]));
  const concluidosSemDesfecho = items.filter((i) => i.stage === 'concluido'
    && !(i.resolvido_em || porId.get(i.conversa_id)?.resolvido_em));
  if (concluidosSemDesfecho.length) {
    p.push(`${concluidosSemDesfecho.length} item(ns) com stage 'concluido' e SEM \`resolvido_em\` — o desfecho voltou a ser deduzido do relógio (R1). Ex.: ${concluidosSemDesfecho.slice(0, 3).map((i) => i.key).join(', ')}`);
  }
  const parados = items.filter((i) => i.stage === 'parado');
  if (!parados.length) {
    p.push("nenhum item com stage 'parado' — o estado que a SPEC cria não existe na saída (R1)");
  }
  const semHa = parados.filter((i) => !i.parado_ha && !i.parado_desde);
  if (semHa.length) p.push(`${semHa.length} item(ns) 'parado' sem \`parado_ha\`/\`parado_desde\` — "há quanto tempo" é a razão de o estado existir`);
  const comDesfecho = items.filter((i) => (i.resolvido_em || porId.get(i.conversa_id)?.resolvido_em) && i.stage !== 'concluido');
  if (comDesfecho.length) p.push(`${comDesfecho.length} item(ns) COM \`resolvido_em\` e stage ≠ 'concluido' — 'concluido' ⇔ \`resolvido_em\` é bicondicional (R1)`);
  return p;
}

// [3] R1 — o mesmo payload não se contradiz.
function analisarContradicao({ observacao, mundo }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const p = [];
  const saida = observacao.saida ?? observacao.corpo ?? {};
  const semana = saida.semana;
  if (!semana || typeof semana !== 'object') return ['o payload não traz `semana` — os contadores da 086 saíram da projeção (U5.3)'];
  const items = itensDe(observacao);
  const concluidos = items.filter((i) => i.stage === 'concluido').length;
  const terminaram = Number(semana.terminaram || 0);
  if (concluidos > 0 && terminaram === 0) {
    p.push(`CONTRADIÇÃO no MESMO payload: ${concluidos} item(ns) 'concluido' e \`semana.terminaram: 0\` (§1.1 — foi exatamente este defeito)`);
  }
  if (terminaram !== concluidos) {
    p.push(`\`semana.terminaram\` (${terminaram}) ≠ itens 'concluido' (${concluidos}) — os dois têm de sair do MESMO campo \`resolvido_em\``);
  }
  return p;
}

// [4] R2 — o claim grava dono, não status; e a cascata testa dono antes de status.
function analisarClaim({ claim }) {
  if (claim?.erro) return [`o claim não executou: ${claim.erro}`];
  const p = [];
  const updates = claim.updates || [];
  if (!updates.length) return ['o claim não fez UPDATE nenhum em `conversations` — nada foi medido'];
  const carga = Object.assign({}, ...updates.map((u) => u.payload || {}));
  if (!('claimed_by' in carga)) p.push('o claim não grava `claimed_by`');
  if (!('claimed_by_name' in carga)) p.push('o claim não grava `claimed_by_name`');
  if (!('claimed_at' in carga)) p.push('o claim não grava `claimed_at`');
  if ('status' in carga) {
    p.push(`o claim grava \`status: ${JSON.stringify(carga.status)}\` junto do dono — dono e status voltaram a ser a mesma dimensão (R2, ACHADO-1b §1.2)`);
  }
  return p;
}

function analisarDonoAntesDeStatus({ observacao }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const items = itensDe(observacao);
  const p = [];
  const assumidos = items.filter((i) => i.dono && i.dono.id);
  if (!assumidos.length) return ["nenhum item com `dono` preenchido — a conversa assumida sumiu da projeção (R2)"];
  const fora = assumidos.filter((i) => i.stage !== 'com_equipe');
  if (fora.length) {
    p.push(`${fora.length} conversa(s) COM dono e stage ≠ 'com_equipe' (${[...new Set(fora.map((i) => i.stage))].join(', ')}) — a cascata testou status ANTES do dono: "com a equipe" é inalcançável (R2/U2.2)`);
  }
  const pediram = items.filter((i) => i.stage === 'precisa_de_voce');
  const pediuComDono = pediram.filter((i) => i.dono && i.dono.id);
  if (pediuComDono.length) p.push(`${pediuComDono.length} item(ns) em 'precisa_de_voce' JÁ com dono — "pediu uma pessoa" é HUMAN_REQUESTED ∧ SEM dono (U2.2)`);
  return p;
}

/**
 * 🔴 [4] A-3 — O DONO VENCE O STATUS, na linha em que os DOIS existem.
 *
 * `analisarDonoAntesDeStatus` media "toda conversa com dono está em
 * `com_equipe`" — verdade, e insuficiente: nenhuma conversa da fixture tinha
 * `claimed_by` E `status:'HUMAN_REQUESTED'` ao mesmo tempo, que é EXATAMENTE o
 * que o claim de `7f3f3eb` gravava (§1.2). A cascata podia voltar a testar o
 * status primeiro e nada ficava vermelho.
 */
function analisarDonoVenceStatus({ observacao }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const items = itensDe(observacao);
  const alvo = items.find((i) => i.conversa_id === CONVERSA_DO_DEFEITO);
  if (!alvo) {
    return [`a conversa do defeito histórico (${CONVERSA_DO_DEFEITO}: dono E \`HUMAN_REQUESTED\`) não voltou da projeção — o mundo defeituoso sumiu e a régua não mede nada`];
  }
  const p = [];
  if (!alvo.dono || !alvo.dono.id) {
    p.push(`${CONVERSA_DO_DEFEITO} tem \`claimed_by\` no dublê e voltou SEM \`dono\` — a projeção perdeu a dimensão`);
  }
  if (alvo.stage !== 'com_equipe') {
    p.push(`${CONVERSA_DO_DEFEITO} tem dono E \`status:'HUMAN_REQUESTED'\` e saiu como '${alvo.stage}' — a cascata testou o STATUS antes do DONO, e "com a equipe" volta a ser inalcançável (§1.2/R2)`);
  }
  return p;
}

/**
 * 🔴 [4] R2/R7 — QUEM JÁ TEM DONO NÃO RECEBE "ASSUMA A CONVERSA".
 *
 * O estágio pode estar certo e a PRÓXIMA AÇÃO errada: basta o `pediuPessoa`
 * deixar de olhar o dono. Ninguém trava; o card só manda a atendente assumir um
 * atendimento que já é dela. É o §9.5 — o passo responde, e responde errado.
 */
function analisarNaoMandeAssumirComDono({ observacao }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const items = itensDe(observacao);
  const p = [];
  const comDono = items.filter((i) => i.dono && i.dono.id);
  if (!comDono.length) return ['nenhum item com dono — nada foi medido'];
  const mandando = comDono.filter((i) => {
    const pa = i.agora?.proxima_acao || i.proxima_acao;
    return pa && (pa.regra === 'pessoa' || /assum[ai]\b/i.test(String(pa.texto || '')));
  });
  if (mandando.length) {
    p.push(`${mandando.length} conversa(s) COM dono receberam "assuma a conversa" como próxima ação (${mandando.slice(0, 3).map((i) => i.key).join(', ')}) — o card manda a atendente assumir o que já é dela (R2/R7)`);
  }
  // ⛔ o PAR: sem isto a régua ficaria verde num mundo em que NINGUÉM recebe a
  //    regra `pessoa` — verde por ausência não é verde por acerto.
  const semDonoEPediu = items.filter((i) => !i.dono && (i.agora?.proxima_acao?.regra === 'pessoa'));
  if (!semDonoEPediu.length) {
    p.push('nenhuma conversa SEM dono recebeu a próxima ação `pessoa` — a régua não teria como distinguir nada (R7 precedência)');
  }
  return p;
}

// [5] R3 — o read model de CASOS é por EPISÓDIO.
function analisarEpisodio({ casos, mundo }) {
  if (casos?.erro) return [`a projeção de Casos não executou: ${casos.erro}`];
  const p = [];
  const items = itensDe(casos);
  if (!items.length) return ['a projeção de Casos devolveu ZERO itens'];
  const comSessao = items.filter((i) => i.session_id).length;
  if (comSessao === 0) {
    p.push('nenhum caso traz `session_id`: a lista continua ancorada na CONVERSA, não no EPISÓDIO (R3/§1.4 — 5,8 episódios por contato viram 1 balde)');
  }
  const conversasDoMundo = (mundo?.conversations || []).filter((c) => c.company_id === CO_ALFA).length;
  const sessoesDoMundo = (mundo?.attendance_sessions || []).filter((s) => s.company_id === CO_ALFA).length;
  if (items.length && comSessao === 0 && items.length <= conversasDoMundo) {
    p.push(`📊 ${items.length} itens para ${sessoesDoMundo} episódios e ${conversasDoMundo} conversas — a granularidade é a da conversa`);
  }
  const orfaos = items.filter((i) => i.session_id && !i.conversa_id);
  if (sessoesDoMundo && comSessao && !orfaos.length) {
    p.push('nenhum caso "sem conversa vinculada": os episódios órfãos (📊 E7: 42,2%) sumiram da lista em vez de continuarem CASOS (R3)');
  }
  const orfaosSemRotulo = orfaos.filter((i) => i.sem_conversa_vinculada !== true);
  if (orfaosSemRotulo.length) p.push(`${orfaosSemRotulo.length} episódio(s) sem conversa e sem o rótulo \`sem_conversa_vinculada\` — a tela não sabe dizer por que falta contexto`);
  return p;
}

// [6] R4 — a espera só existe se `work_waits` tiver linha ativa.
function analisarEspera({ observacao }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const p = [];
  const items = itensDe(observacao);
  const esperando = items.filter((i) => i.esperando);
  if (!esperando.length) {
    p.push('nenhum item com `esperando` — os 5 `work_waits` ativos do dublê não chegaram à projeção (R4)');
    return p;
  }
  const KINDS = new Set(['esperando_cliente', 'esperando_seguradora', 'esperando_humano']);
  const kindsRuins = esperando.filter((i) => !KINDS.has(String(i.esperando.kind)));
  if (kindsRuins.length) {
    p.push(`kind fora do CHECK do banco: ${[...new Set(kindsRuins.map((i) => i.esperando.kind))].join(', ')} — 📊 "documento" NEM É kind válido (§1.3)`);
  }
  const vencidas = esperando.filter((i) => i.esperando.vencida === true || i.esperando.estado === 'espera_vencida');
  if (!vencidas.length) p.push('a espera com `due_at` no passado não foi marcada como vencida (`espera_vencida` — R6)');
  const semDesde = esperando.filter((i) => !i.esperando.desde);
  if (semDesde.length) p.push(`${semDesde.length} espera(s) sem \`desde\` — "esperando a seguradora · Xd Yh" precisa da hora em que a espera nasceu`);
  // ⛔ a espera NUNCA é deduzida do texto da conversa
  const semLinha = esperando.filter((i) => !i.esperando.fonte_id && !i.esperando.wait_id);
  if (semLinha.length) p.push(`${semLinha.length} espera(s) sem id da linha de \`work_waits\` — espera sem linha é espera DEDUZIDA (R4)`);
  return p;
}

// [7] R5 — paginação por cursor e busca NO BANCO.
function analisarPaginacao({ pagina1, pagina2, busca }) {
  const p = [];
  for (const [nome, o] of [['página 1', pagina1], ['página 2', pagina2], ['busca', busca]]) {
    if (o?.erro) p.push(`a projeção de ${nome} não executou: ${o.erro}`);
  }
  if (p.length) return p;

  const consultas = (o) => (o.registro || []).filter((c) => c.op === 'select');
  const fixo120 = consultas(pagina1).filter((c) => c.limite === 120);
  if (fixo120.length) {
    p.push(`${fixo120.length} consulta(s) com \`.limit(120)\` fixo (${fixo120.map((c) => c.tabela).join(', ')}) — 📊 §1.5: 120 de 448 conversas, 73% invisível`);
  }
  // a Fila lê TODAS em lotes (E11): o lote é grande, nunca 120
  const lotesPequenos = consultas(pagina1).filter((c) => c.tabela === 'conversations' && c.limite != null && c.limite < 1000 && c.range == null);
  if (lotesPequenos.length) p.push(`a leitura de \`conversations\` tem teto ${lotesPequenos.map((c) => c.limite).join('/')} < 1000 — E11 manda ler TODAS em lotes de 1.000`);

  // o cursor `(ultimo_evento_em, id)` foi PEDIDO AO BANCO
  const comCursor = consultas(pagina2).filter((c) => c.or.some((e) => /ultimo_evento_em|last_event_at/.test(e))
    || c.predicados.some((x) => x.op === 'lt' && /ultimo_evento_em|last_event_at/.test(String(x.coluna))));
  if (!comCursor.length) {
    p.push('a página 2 não pediu cursor ao banco: nenhum `.lt(ultimo_evento_em, …)` nem `.or(...)` com as duas chaves — a paginação é do cliente (R5)');
  }
  const duasChaves = consultas(pagina2).filter((c) => c.ordens.length >= 2
    && c.ordens.some((o) => /ultimo_evento_em|last_event_at/.test(String(o.coluna)))
    && c.ordens.some((o) => String(o.coluna) === 'id'));
  if (!duasChaves.length) {
    p.push('nenhuma consulta ordena pelas DUAS chaves do cursor (`ultimo_evento_em` e `id`) — sem desempate, um caso some ou repete ao acaso');
  }
  const comLimite = consultas(pagina2).filter((c) => c.limite != null || c.range != null);
  if (!comLimite.length) p.push('a página 2 não pediu `limit`/`range` — cursor sem tamanho de página não pagina nada');

  // a BUSCA vai ao banco
  const noBanco = consultas(busca).filter((c) => c.ilike.length || c.textSearch.length
    || c.or.some((e) => /ilike|fts|plfts|wfts/.test(e)));
  if (!noBanco.length) {
    p.push(`a busca por "${PROTOCOLO_ANTIGO}" não chegou ao banco: nenhum \`ilike\`/\`textSearch\` registrado — 📊 §1.5: \`filter()\` no cliente sobre 120 linhas devolve "nada" para um protocolo de 60 dias`);
  }
  const achou = itensDe(busca);
  if (noBanco.length && achou.length === 0) {
    p.push(`a busca foi ao banco e devolveu ZERO para "${PROTOCOLO_ANTIGO}", que EXISTE no dublê — o predicado não casa o protocolo`);
  }
  return p;
}

/**
 * 🔴 [7] A-4 — E A FILA TAMBÉM É MEDIDA.
 *
 * `analisarPaginacao` observa `projetarCasos({opcoes:{}})` — a projeção de
 * CASOS. O `.limit(120)` de §1.5 (📊 120 de 448 conversas da AutoFleet, 73%
 * invisível) é o da FILA, e o ramo da Fila é justamente o que ninguém observava:
 * pôr `.limit(120)` nele deixava a suíte VERDE (mutação U4).
 *
 * E11: a Fila lê TODAS as conversas ativas em LOTES de 1.000 — `.range(de, de+999)`,
 * nunca um `.limit()` pequeno, e nunca um teto que a tela não tem como saber.
 */
function analisarLeituraDaFila({ fila }) {
  if (fila?.erro) return [`a projeção da Fila não executou: ${fila.erro}`];
  const p = [];
  const consultas = (fila.registro || []).filter((c) => c.op === 'select' && c.tabela === 'conversations');
  if (!consultas.length) return ['a Fila não consultou `conversations` — nada foi medido'];

  const fixo120 = consultas.filter((c) => c.limite === 120);
  if (fixo120.length) {
    p.push(`${fixo120.length} consulta(s) de \`conversations\` da FILA com \`.limit(120)\` fixo — 📊 §1.5: 120 de 448 conversas, 73% invisível (e é o ramo que [7] não observava)`);
  }
  const teto = consultas.filter((c) => c.limite != null && c.limite < 1000);
  if (teto.length) {
    p.push(`a FILA lê \`conversations\` com teto ${[...new Set(teto.map((c) => c.limite))].join('/')} < 1.000 — E11 manda ler TODAS em lotes de 1.000`);
  }
  const emLotes = consultas.filter((c) => Array.isArray(c.range) && c.range[1] - c.range[0] + 1 >= 1000);
  if (!emLotes.length) {
    p.push('nenhuma consulta de `conversations` da FILA pediu uma FAIXA de 1.000 (`.range(de, de + 999)`) — sem lote não existe "todas": existe a primeira página e um teto silencioso');
  }
  const itens = itensDe(fila);
  if (itens.length <= 120) {
    p.push(`a Fila devolveu ${itens.length} itens sobre ${N_CONVERSAS_ALFA} conversas de Alfa — o teto de §1.5 voltou por algum caminho`);
  }
  return p;
}

// [7b] a busca do cliente de Casos morreu (FORMA da declaração — §9.4).
function analisarBuscaNoCliente({ codigo }) {
  if (codigo == null) return [`${CAMINHO_CASOS_CLIENTE} não existe`];
  const p = [];
  // o filtro cliente-side de HOJE: `.filter((i) => !q ...` sobre os itens vindos da rota
  if (/\.filter\(\s*\(\s*i\s*\)\s*=>\s*!\s*q\b/.test(codigo)) {
    p.push('o cliente de Casos ainda filtra a busca em memória (`.filter((i) => !q …`) — 📊 §1.5: busca no cliente sobre o teto = falso zero (R5/U5.2)');
  }
  if (!/busca|q=|search/.test(codigo)) {
    p.push('o cliente de Casos não manda o termo de busca ao servidor (nenhum `busca`/`q=` na chamada) — a busca continua sendo dele');
  }
  return p;
}

// [8] R5 — `indisponivel` POR FONTE, nunca zero silencioso.
function analisarIndisponivel({ comFalha, semFalha }) {
  const p = [];
  if (comFalha?.erro) return [`a projeção com fonte derrubada não executou: ${comFalha.erro}`];
  if (semFalha?.erro) return [`a projeção sem falha não executou: ${semFalha.erro}`];
  const ind = comFalha.saida?.indisponivel ?? comFalha.corpo?.indisponivel;
  if (ind == null) return ['o payload não traz `indisponivel` — R5 exige a declaração por fonte'];
  if (typeof ind !== 'object') {
    p.push(`\`indisponivel\` é ${typeof ind} e não um mapa por FONTE — R5: "indisponivel: true QUANDO UMA FONTE falha"`);
    if (ind !== true) p.push('e ele está `false` com uma fonte derrubada: é o zero silencioso (§1.3 — `ainda_esperam: 0` com `indisponivel: false` todo dia)');
    return p;
  }
  const marcadas = Object.entries(ind).filter(([, v]) => v === true).map(([k]) => k);
  if (!marcadas.length) {
    p.push('a consulta a `work_waits` falhou no dublê e NENHUMA fonte foi marcada indisponível — zero silencioso (§1.3)');
  } else if (!marcadas.some((k) => /wait|espera/i.test(k))) {
    p.push(`a fonte derrubada foi \`work_waits\`, mas as marcadas são [${marcadas.join(', ')}] — a marca não aponta a fonte certa`);
  }
  const indOk = semFalha.saida?.indisponivel ?? semFalha.corpo?.indisponivel;
  if (indOk && typeof indOk === 'object' && Object.values(indOk).some((v) => v === true)) {
    p.push('sem falha nenhuma, alguma fonte está marcada indisponível — a marca não distingue nada');
  }
  return p;
}

// [9] R6/R7 — o AGORA, as razões observáveis e a precedência.
const RAZOES_OBSERVAVEIS = new Set(['pediu_pessoa', 'trabalho_falhou', 'parado', 'espera_vencida']);
const DIMENSOES_DO_AGORA = ['situacao', 'dono', 'esperando', 'ha_quanto_tempo', 'atencao', 'proxima_acao'];
const PRECEDENCIA = ['pessoa', 'aprovacao', 'passo_do_trabalho', 'espera_com_prazo', 'sem_proxima_acao_declarada'];

function analisarAgora({ observacao }) {
  if (observacao?.erro) return [`a projeção não executou: ${observacao.erro}`];
  const p = [];
  const items = itensDe(observacao);
  if (!items.length) return ['a projeção devolveu ZERO itens'];
  const semAgora = items.filter((i) => !i.agora || typeof i.agora !== 'object');
  if (semAgora.length === items.length) return ['nenhum item traz o bloco `agora` — U6.1 (situação · dono · de quem espera · há quanto tempo · atenção · próxima ação)'];
  if (semAgora.length) p.push(`${semAgora.length} item(ns) sem o bloco \`agora\``);
  const comAgora = items.filter((i) => i.agora && typeof i.agora === 'object');
  const faltando = new Set();
  for (const i of comAgora) for (const d of DIMENSOES_DO_AGORA) if (!(d in i.agora)) faltando.add(d);
  if (faltando.size) p.push(`o \`agora\` não tem as 6 dimensões — falta: ${[...faltando].join(', ')} (U6.1)`);

  // R6 — só as razões observáveis
  const inventadas = new Set();
  for (const i of comAgora) for (const r of (i.agora.atencao || i.atencao || [])) {
    const chave = typeof r === 'string' ? r : r?.razao;
    if (chave && !RAZOES_OBSERVAVEIS.has(String(chave))) inventadas.add(String(chave));
  }
  if (inventadas.size) {
    p.push(`razão de atenção SEM FONTE: ${[...inventadas].join(', ')} — R6 admite só ${[...RAZOES_OBSERVAVEIS].join(', ')} (E17 tirou \`aprovacao_pendente\`; \`sla_at_risk\` nunca teve escritor)`);
  }
  const comAtencao = comAgora.filter((i) => (i.agora.atencao || []).length > 0);
  if (!comAtencao.length) p.push('nenhum item com razão de atenção — o dublê tem HUMAN_REQUESTED, run failed, 640 paradas e 1 espera vencida (R6)');

  // R7 — próxima ação com FONTE e pela precedência
  const semFonte = comAgora.filter((i) => i.agora.proxima_acao
    && !(i.agora.proxima_acao.fonte || i.agora.proxima_acao.fonte_id || i.agora.proxima_acao.origem));
  if (semFonte.length) p.push(`${semFonte.length} "próxima ação" sem \`fonte\` — R7 proíbe ficção: ou vem de uma autoridade, ou é "sem próxima ação declarada"`);
  const semNada = comAgora.filter((i) => !i.agora.proxima_acao);
  if (semNada.length) p.push(`${semNada.length} item(ns) com \`proxima_acao\` ausente — a ausência tem NOME ("sem próxima ação declarada"), não é \`null\` mudo (R7)`);
  const regras = new Set(comAgora.map((i) => i.agora.proxima_acao?.regra).filter(Boolean));
  const foraDaPrecedencia = [...regras].filter((r) => !PRECEDENCIA.includes(String(r)));
  if (regras.size && foraDaPrecedencia.length) p.push(`regra de precedência desconhecida: ${foraDaPrecedencia.join(', ')} — R7 fixa ${PRECEDENCIA.join(' → ')}`);
  return p;
}

// ─────────────────────────────────────────────────────────────────────────────
// [10] R8 — A TIMELINE. 🔴 E A RÉGUA MUDOU, porque a antiga era inatingível.
// ─────────────────────────────────────────────────────────────────────────────
//
// A régua anterior era "nenhum item com `at: null`", medida DEPOIS do `põe()`
// da Ficha — que descartava em silêncio todo evento sem hora. Zerar o `at` de
// TRÊS fontes diferentes deixava a suíte VERDE (lente de verdade, A-1): o
// evento sumia, e "a timeline tem hora" e "a timeline esconde o que não tem
// hora" eram a mesma cor. É o carimbo do CLAUDE.md §9.3, e o §9.5 inteiro: a
// rota responde 200 e responde ERRADO, em silêncio.
//
// A régua agora tem três perguntas, e cada uma pega o que as outras não pegam:
//
//   (a) o nº de eventos da timeline == o nº de FATOS das fontes  → nada sumiu
//   (b) todo evento tem `fonte` e `fonte_id`                     → dá para voltar
//   (c) os que têm hora vêm ANTES dos que não têm                → e o sem hora
//                                                                  se DECLARA
//
const FONTES_DA_TIMELINE = new Set(['conversa', 'corredor', 'trabalho', 'espera', 'aprovacao', 'aprovação', 'peca', 'peça']);

/**
 * 🔴 (a) — OS FATOS QUE O MUNDO PRODUZ para esta conversa, contados AQUI, no
 * guarda, a partir das linhas do dublê. É a contagem que a Ficha tem de
 * devolver. Contar a partir da SAÍDA dela seria perguntar ao réu.
 */
function fatosDaTimeline(mundo, conversaId) {
  const c = (mundo?.conversations || []).find((x) => String(x.id) === String(conversaId));
  if (!c) return [];
  const espelho = String(c.session_id || '').startsWith('dispatch:');
  const fatos = ['abertura (1ª mensagem ou criação da conversa)'];
  if (c.user_name && !espelho) fatos.push('segurado identificado');
  for (const r of mundo.work_runs || []) {
    if (String(r.conversation_id) !== String(conversaId)) continue;
    if (r.status !== 'failed' && !r.unblock_state) continue;   // o mesmo recorte da rota
    fatos.push(`trabalho parado ${r.id}`);
  }
  for (const w of mundo.work_waits || []) {
    if (String(w.conversation_id) === String(conversaId)) fatos.push(`espera ${w.id}`);
  }
  if (c.claimed_by && c.claimed_at) fatos.push('alguém da equipe assumiu');
  if (c.resolvido_em) fatos.push('atendimento encerrado');
  return fatos;
}

function analisarTimeline({ ficha, mundo, conversaId }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const p = [];
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? ficha.corpo?.linha_do_tempo ?? [];
  if (!Array.isArray(timeline) || !timeline.length) return ['a ficha não devolveu timeline — nada foi medido'];

  // (a) NADA É DESCARTADO
  const fatos = fatosDaTimeline(mundo ?? ficha.mundo, conversaId);
  if (fatos.length && timeline.length !== fatos.length) {
    const faltam = fatos.length - timeline.length;
    p.push(
      `a Ficha devolveu ${timeline.length} evento(s) para ${fatos.length} fato(s) das fontes `
      + `(${fatos.join(' · ')}) — ${faltam > 0 ? `${faltam} sumiram` : `${-faltam} apareceram do nada`}, `
      + 'e nenhuma linha diz por quê (R8/A-1: descartar em silêncio é pior que mostrar sem hora)',
    );
  }

  // (c) os que têm hora vêm ANTES dos que não têm, e o sem hora se DECLARA
  const primeiroSemHora = timeline.findIndex((e) => e.at == null);
  if (primeiroSemHora !== -1) {
    const comHoraDepois = timeline.slice(primeiroSemHora + 1).filter((e) => e.at != null);
    if (comHoraDepois.length) {
      p.push(`${comHoraDepois.length} evento(s) COM hora vêm DEPOIS de um evento sem hora — o sem hora vai para o FIM, senão a página faz parecer que ele veio primeiro (R8)`);
    }
  }
  const semHoraMudo = timeline.filter((e) => e.at == null && e.sem_hora !== true);
  if (semHoraMudo.length) {
    p.push(`${semHoraMudo.length} evento(s) com \`at: null\` e SEM \`sem_hora: true\` — a tela não tem como escrever "sem hora registrada", e um travessão parece defeito de carga`);
  }

  // (b) a AUTORIDADE de cada item
  const semFonte = timeline.filter((e) => !e.fonte && !e.source_authority);
  if (semFonte.length) p.push(`${semFonte.length} evento(s) sem \`fonte\` — R8 exige a autoridade de onde o item veio`);
  const semId = timeline.filter((e) => !e.fonte_id && !e.source_id);
  if (semId.length) p.push(`${semId.length} evento(s) sem \`fonte_id\` — sem o id, ninguém volta à autoridade`);
  const fontesRuins = [...new Set(timeline.map((e) => String(e.fonte || e.source_authority || '')).filter(Boolean))]
    .filter((f) => !FONTES_DA_TIMELINE.has(f));
  if (fontesRuins.length) p.push(`fonte fora da lista: ${fontesRuins.join(', ')} — R8 fixa ${[...FONTES_DA_TIMELINE].slice(0, 6).join(', ')}`);
  return p;
}

/**
 * 🔴 [10] R8 — no mundo em que TODA fonte tem hora no banco, nenhum evento pode
 * chegar sem hora. É a régua ORIGINAL do E16 (📊 6 de 9 tipos com `at: null`),
 * agora dita num mundo onde a hora EXISTE: se um evento vier sem ela, foi o
 * código que a perdeu, não a fonte que não tinha.
 */
function analisarTodosComHora({ ficha }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? [];
  if (!Array.isArray(timeline) || !timeline.length) return ['a ficha não devolveu timeline — nada foi medido'];
  const semAt = timeline.filter((e) => e.at == null);
  return semAt.length
    ? [`${semAt.length} de ${timeline.length} eventos com \`at: null\` — e neste mundo TODAS as fontes têm hora no banco: ${semAt.slice(0, 4).map((e) => JSON.stringify(e.label)).join(', ')} (📊 E16, R8)`]
    : [];
}

/**
 * 🔴 [10] A-1 — E O QUE NÃO TEM HORA NÃO SOME.
 *
 * O outro lado da mesma moeda, e o que faltava: no mundo em que a fonte NÃO tem
 * hora, o evento continua na linha do tempo, marcado, no fim. A régua de cima
 * (`analisarTodosComHora`) e esta TÊM de poder discordar — senão as duas
 * medem a mesma coisa e a Ficha pode voltar a apagar a prova.
 */
function analisarNaoEscondeSemHora({ ficha, mundo, conversaId }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const p = [];
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? [];
  if (!Array.isArray(timeline)) return ['a ficha não devolveu timeline'];
  const fatos = fatosDaTimeline(mundo, conversaId);
  if (timeline.length !== fatos.length) {
    p.push(
      `a conversa sem \`created_at\` e sem mensagem produz ${fatos.length} fato(s) `
      + `(${fatos.join(' · ')}) e a Ficha devolveu ${timeline.length} — o evento SEM HORA foi `
      + 'DESCARTADO em silêncio (`if (e && e.at) timeline.push(e)`), e a saída ficou impecável mentindo por omissão (A-1)',
    );
  }
  const semHora = timeline.filter((e) => e.at == null);
  if (!semHora.length) {
    p.push('nenhum evento chegou com `at: null` num mundo em que a fonte não tem hora nenhuma — ele não "ganhou hora", ele SUMIU (R8 pede hora, não sumiço)');
    return p;
  }
  const mudos = semHora.filter((e) => e.sem_hora !== true);
  if (mudos.length) p.push(`${mudos.length} evento(s) sem hora chegaram MUDOS (sem \`sem_hora: true\`) — a tela precisa da marca para escrever "sem hora registrada"`);
  const ultimo = timeline[timeline.length - 1];
  if (ultimo && ultimo.at != null) p.push('o evento sem hora não ficou no FIM da linha do tempo');
  const comHora = timeline.filter((e) => e.at != null);
  if (!comHora.length) p.push('nenhum evento COM hora neste mundo — a régua da ordem (c) não teria como falhar, e um guarda que não pode falhar não guarda nada');
  else if (timeline.indexOf(comHora[0]) > timeline.indexOf(semHora[0])) {
    p.push('o evento COM hora ficou depois do sem hora');
  }
  return p;
}

// [10b] `work_events` NUNCA é fonte da timeline (execução: o dublê registra a leitura).
function analisarSemWorkEvents({ ficha }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const p = [];
  const leu = (ficha.registro || []).filter((c) => c.tabela === 'work_events');
  if (leu.length) p.push(`a ficha CONSULTOU \`work_events\` ${leu.length}× — 📊 §1.7: 100% telemetria de motor (\`run.leased\`, \`step.started\`), o que a §18 proíbe exibir`);
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? [];
  const daTelemetria = timeline.filter((e) => /work_event|run\.leased|step\.started/.test(String(e.fonte || '') + String(e.label || '')));
  if (daTelemetria.length) p.push(`${daTelemetria.length} evento(s) da timeline vieram de telemetria de motor`);
  return p;
}

// [11] R9 — dois tenants.
function analisarTenant({ beta, mundo, cruzada }) {
  if (beta?.erro) return [`a projeção de Beta não executou: ${beta.erro}`];
  const p = [];
  const items = itensDe(beta);
  if (!items.length) return ['a projeção de Beta devolveu ZERO itens — o guarda não mediu vazamento nenhum'];
  const idsAlfa = new Set([
    ...(mundo?.conversations || []).filter((c) => c.company_id === CO_ALFA).map((c) => c.id),
    ...(mundo?.attendance_sessions || []).filter((s) => s.company_id === CO_ALFA).map((s) => s.id),
  ]);
  const vazados = items.filter((i) => idsAlfa.has(i.conversa_id) || idsAlfa.has(i.session_id));
  if (vazados.length) p.push(`🔴 P0 — ${vazados.length} item(ns) de ALFA na sessão de BETA: ${vazados.slice(0, 3).map((i) => i.key).join(', ')}`);
  const textoBeta = JSON.stringify(items);
  if (/Segurado Alfa|cv-alfa|as-alfa/.test(textoBeta)) p.push('🔴 P0 — a saída de Beta cita objetos de Alfa pelo id/nome');

  // 🔴 TODA consulta registrada tem `company_id` — RLS sozinha não conta (§7)
  const consultas = (beta.registro || []).filter((c) => c.op === 'select');
  const semFiltro = consultas.filter((c) => !c.predicados.some((x) => x.coluna === 'company_id'));
  if (semFiltro.length) {
    p.push(`${semFiltro.length} consulta(s) SEM \`.eq('company_id', …)\`: ${[...new Set(semFiltro.map((c) => c.tabela))].join(', ')} — o backend usa service role, e a RLS não protege contra erro de filtro no código (CLAUDE.md §7)`);
  }
  if (cruzada && cruzada.status !== 404) {
    p.push(`a ficha de uma conversa de ALFA pedida pela sessão de BETA devolveu ${cruzada.status}, não 404 (R9: UUID não é autorização)`);
  }
  return p;
}

// [12] R10 — "Histórico" deixou de ser rótulo de navegação (FORMA da declaração).
function analisarCutover({ modulos, filaCliente }) {
  const p = [];
  if (modulos == null) p.push(`${CAMINHO_MODULOS} não existe`);
  else if (/title:\s*'Histórico'/.test(modulos)) {
    p.push(`\`${CAMINHO_MODULOS}\` ainda declara \`title: 'Histórico'\` para /dashboard/atendimentos/casos — R10/BLOCO K: a rota já é "casos"`);
  }
  if (filaCliente == null) p.push(`${CAMINHO_FILA_CLIENTE} não existe`);
  else {
    const semComentario = filaCliente.replace(/\/\*[\s\S]*?\*\//g, ' ').split('\n').map((l) => l.split('//')[0]).join('\n');
    if (/>\s*Histórico\s*</.test(semComentario)) {
      p.push(`\`${CAMINHO_FILA_CLIENTE}\` ainda tem o link rotulado "Histórico" — R10`);
    }
  }
  return p;
}

// [12b] a lista canônica de estágios conhece `parado` (FORMA da declaração).
function analisarEstagioParado({ estagios }) {
  if (estagios == null) return [`${CAMINHO_ESTAGIOS} não existe`];
  const semComentario = estagios.replace(/\/\*[\s\S]*?\*\//g, ' ').split('\n').map((l) => l.split('//')[0]).join('\n');
  const bloco = (semComentario.split('ATTENDANCE_STAGES = [')[1] || '').split(']')[0];
  if (!/'parado'/.test(bloco)) {
    return ["a lista canônica `ATTENDANCE_STAGES` não conhece 'parado' — o estado que a SPEC-097 cria (R1) nasceria fora do vocabulário, como `encaminhado` nasceu em 04/08"];
  }
  return [];
}

// [13] R11 — LINGUAGEM HUMANA: nenhum texto do corretor expõe chave/vocabulário
// de máquina. As chaves do JSON são contrato de código — o alvo aqui é só o
// TEXTO que a tela mostra (§9.4: regex sobre o texto REAL, produzido pelo
// motor real, nunca sobre a declaração).
const RE_CHAVE_METRICA = /\b[a-z_]+\.[a-z_]+@\d+\b/;
const RE_IDENTIFICADOR_PONTO = /\b[a-z]+_[a-z_]+\.[a-z_]+\b/;
const RE_VOCAB_TECNICO = /\b(tool|node|lease|redis|qdrant|run_id|work_run|unblock_state|HUMAN_REQUESTED|claimed_by|resolvido_em|session_id|conversation_id|uuid|null|undefined|NaN)\b/;

// ─────────────────────────────────────────────────────────────────────────────
// 🔴 A-5 — [13] GUARDAVA A LISTA, NÃO A REGRA. Agora guarda a REGRA.
// ─────────────────────────────────────────────────────────────────────────────
//
// `RE_IDENTIFICADOR_PONTO` exige um PONTO e `RE_VOCAB_TECNICO` é uma LISTA
// FECHADA. `detalhe: stage` entregava `precisa_de_voce`, `com_equipe`,
// `em_conversa` ao corretor e passava VERDE: snake_case sem ponto e fora da
// lista (mutação M13 — a mutação que este guarda dizia existir PARA ele).
//
// A regra R11 não é "não diga estas 15 palavras". É: **nenhum texto que o
// corretor lê é linguagem de máquina**. Três formas, e cada uma pega o que as
// outras não pegam:
//
//   1. QUALQUER token snake_case (`precisa_de_voce`, `auto_socorro`, `due_at`)
//   2. `@\d` — o sufixo de versão/janela das chaves de métrica (`producao@30`)
//   3. IDENTIDADE com um valor de vocabulário do sistema: `ATTENDANCE_STAGES`,
//      `resolucao_motivo`, razões de atenção, regras de precedência, kinds de
//      espera. Pega o que NÃO tem sublinhado — `concluido`, `parado`,
//      `esperando`, `expirou` — e que nenhuma regex de forma acusaria.
const RE_SNAKE_CASE = /\b[a-z]+_[a-z_]+\b/;
const RE_ARROBA_NUMERO = /@\d/;

/** O vocabulário de MÁQUINA do atendimento. Um texto IDÊNTICO a um destes é a
 *  chave crua vazando para a tela — foi assim que `estagio`/`stage` virou card. */
const VOCABULARIO_DE_MAQUINA = new Set([
  // `ATTENDANCE_STAGES` vem do arquivo canônico, EXECUTADO, nunca redigitado
  ...(() => {
    try { return carregarTS(CAMINHO_ESTAGIOS, () => undefined).ATTENDANCE_STAGES || []; }
    catch { return []; }
  })(),
  // os motivos do CHECK de `resolucao_motivo`
  'acionamento_concluido', 'encaminhado', 'resolvido_pelo_segurado', 'fechado_por_humano', 'expirou',
  // as razões de atenção e as regras da precedência
  ...RAZOES_OBSERVAVEIS, ...PRECEDENCIA,
  // os kinds de `work_waits`
  'esperando_cliente', 'esperando_seguradora', 'esperando_humano',
].map((s) => String(s).toLowerCase()));

/**
 * Só os TEXTOS que a tela mostra ao corretor — nunca as CHAVES do JSON.
 *
 * ⚠️ `agora.atencao` (as 4 razões) e `esperando.kind` são CONTRATO de código, e
 * quem os guarda é [9] (contra `RAZOES_OBSERVAVEIS`) e [6] (contra o CHECK do
 * banco). Tratá-los como texto aqui faria [13] acusar o contrato e passar a
 * medir outra coisa. O que ENTRA é qualquer campo de TEXTO ao lado deles.
 */
function textosDoItem(i) {
  const t = [];
  const add = (v) => { if (typeof v === 'string' && v.trim()) t.push(v); };
  if (!i || typeof i !== 'object') return t;
  add(i.detalhe);
  add(i.titulo);
  add(i.estagio_label);
  add(i.pedido);            // R12 — a segunda linha do card no celular
  if (i.proxima_acao) add(i.proxima_acao.texto);
  const listaAtencao = i.atencao || i.agora?.atencao || [];
  for (const a of listaAtencao) {
    if (a && typeof a === 'object') { add(a.texto); add(a.label); add(a.rotulo); }
  }
  // `esperando`: o `kind` é contrato ([6]); qualquer OUTRO texto é do corretor
  const espera = i.esperando || i.agora?.esperando;
  if (espera && typeof espera === 'object') {
    for (const [chave, valor] of Object.entries(espera)) {
      if (['kind', 'desde', 'vence_em', 'fonte_id', 'wait_id', 'estado'].includes(chave)) continue;
      if (typeof valor === 'string') add(valor);
    }
  }
  if (i.agora && typeof i.agora === 'object') {
    add(i.agora.situacao);
    add(i.agora.ha_quanto_tempo);
    if (i.agora.proxima_acao) add(i.agora.proxima_acao.texto);
  }
  return t;
}

/** Os textos da timeline da Ficha (`label`/`detail`/`texto`/`descricao` — nunca
 *  `fonte`/`fonte_id`, que são a AUTORIDADE e existem para o código). */
function textosDaTimeline(timeline) {
  const t = [];
  const add = (v) => { if (typeof v === 'string' && v.trim()) t.push(v); };
  for (const e of (timeline || [])) { add(e.label); add(e.detail); add(e.texto); add(e.descricao); }
  return t;
}

function analisarLinguagemHumana({ fila, casos, ficha }) {
  if (fila?.erro) return [`a projeção da Fila não executou: ${fila.erro}`];
  if (casos?.erro) return [`a projeção de Casos não executou: ${casos.erro}`];
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const p = [];
  const textos = [
    ...itensDe(fila).flatMap(textosDoItem),
    ...itensDe(casos).flatMap(textosDoItem),
    ...textosDaTimeline(ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? []),
  ];
  if (!textos.length) return ['nenhum texto visível foi encontrado nos três payloads (Fila/Casos/Ficha) — nada foi medido (R11)'];
  const achados = new Map();
  for (const texto of textos) {
    const motivos = [];
    if (RE_CHAVE_METRICA.test(texto)) motivos.push('chave de métrica (x.y@n)');
    if (RE_IDENTIFICADOR_PONTO.test(texto)) motivos.push('identificador snake_case.com.ponto');
    const vocab = texto.match(RE_VOCAB_TECNICO);
    if (vocab) motivos.push(`vocabulário técnico ("${vocab[0]}")`);
    // 🔴 A-5 — a REGRA, não a lista
    const snake = texto.match(RE_SNAKE_CASE);
    if (snake) motivos.push(`token snake_case ("${snake[0]}") — é nome de chave, não é frase`);
    if (RE_ARROBA_NUMERO.test(texto)) motivos.push('chave de métrica com janela (`@n`)');
    if (VOCABULARIO_DE_MAQUINA.has(texto.trim().toLowerCase())) {
      motivos.push(`o texto É a chave crua do sistema ("${texto.trim()}") — estágio, motivo de desfecho, razão de atenção ou kind de espera indo direto para o card`);
    }
    if (motivos.length) achados.set(texto, motivos);
  }
  for (const [texto, motivos] of achados) {
    p.push(`texto para o corretor expõe linguagem de máquina: "${texto}" — ${motivos.join('; ')} (R11)`);
  }
  return p;
}

// [14] · schema vivo — nenhuma consulta pediu coluna fora do schema_vivo.json
// (+ as 3 colunas que a migration desta SPEC declara para `attendance_sessions`).
function analisarSchemaVivo({ registros }) {
  const p = [];
  for (const reg of registros) {
    for (const c of (reg || [])) {
      if (c.op === 'select' && (c.colunasInvalidas || []).length) {
        p.push(`consulta a "${c.tabela}" pediu coluna que NÃO EXISTE: ${c.colunasInvalidas.join(', ')} (schema_vivo.json)`);
      }
    }
  }
  return p;
}

// ─────────────────────────────────────────────────────────────────────────────
// 🔴 `--fila-json` — a MESMA execução, servida a quem não é Node
//
// `backend/tests/test_o_clique_da_atendente_nao_apaga_da_fila.py` era regex
// sobre `atendimentos/route.ts` (E13). Ele MIGROU para uma asserção que EXECUTA
// o read model — e executa ESTE, não uma segunda cópia do arnês em python
// (CLAUDE.md §5: consolidar antes de duplicar). Este modo roda a projeção e a
// rota sobre o dublê e imprime o resultado como JSON, nada mais.
// ─────────────────────────────────────────────────────────────────────────────
if (process.argv.includes('--fila-json')) {
  const projecao = await observarProjecao({ opcoes: { group_by: 'stage' } });
  const rota = await observarRota(CAMINHO_FILA);
  const enxugar = (o) => (o.erro ? { erro: o.erro } : { items: itensDe(o) });
  const mundoJson = fixtures();
  process.stdout.write(JSON.stringify({
    projecao: enxugar(projecao),
    rota: enxugar(rota),
    mundo: {
      conversations: mundoJson.conversations.map((c) => ({
        id: c.id, company_id: c.company_id, resolvido_em: c.resolvido_em,
        claimed_by: c.claimed_by, status: c.status, last_message_at: c.last_message_at,
      })),
      work_runs: mundoJson.work_runs.map((r) => ({
        id: r.id, company_id: r.company_id, unblock_state: r.unblock_state,
        case_id: r.input_payload?.case_id ?? null,
      })),
      // 🔴 SPEC-097.1 [L] — sem as LINHAS de espera, quem lê de fora não tem
      // como provar QUAL das duas a projeção escolheu (E6). O guarda python
      // compara o `fonte_id` do item com a linha de menor `vence_em`.
      work_waits: mundoJson.work_waits.map((w) => ({
        id: w.id, company_id: w.company_id, conversation_id: w.conversation_id,
        kind: w.kind, scope: w.scope, status: w.status, vence_em: w.vence_em,
        created_at: w.created_at,
      })),
    },
  }));
  process.exit(0);
}

// ═════════════════════════════════════════════════════════════════════════════
// 🔴 `--mutar [ID]` — O PAINEL DE MUTAÇÃO, E ELE RODA
// ═════════════════════════════════════════════════════════════════════════════
//
// Para cada mutação: copia o arquivo do produto para um `.bak` FORA da árvore,
// aplica a troca (falha ALTO se a âncora não existir — âncora morta é defeito,
// não é "pulei essa"), roda ESTE guarda num subprocesso limpo, restaura por
// cópia num `finally` e confere que o arquivo voltou byte a byte (hash) e que o
// `git status --short` é o MESMO de antes.
//
// Uma mutação que não deixa nada vermelho não é mutação: é edição — e o runner
// sai `rc=1` dizendo qual regra não guarda nada (protocolo §10, CLAUDE.md §9.3).
//
// ⛔ Rodar com a árvore parada. Enquanto alguém edita `app/` ou `lib/`, o
// restauro apagaria a edição daquele segundo.
if (process.argv.includes('--mutar')) {
  const pedido = process.argv[process.argv.indexOf('--mutar') + 1];
  const alvo = pedido && !pedido.startsWith('--') ? String(pedido).toUpperCase() : null;
  const lista = alvo ? MUTACOES.filter((m) => m.id.toUpperCase() === alvo) : MUTACOES;
  if (alvo && !lista.length) {
    console.error(`⛔ não existe mutação "${alvo}". Ids: ${MUTACOES.map((m) => m.id).join(', ')}`);
    process.exit(1);
  }

  const digest = (texto) => crypto.createHash('sha256').update(texto).digest('hex');
  const gitStatus = () => {
    const r = spawnSync('git', ['status', '--short'], { cwd: RAIZ, encoding: 'utf8' });
    return String(r.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean).sort().join('\n');
  };

  const abrigo = fs.mkdtempSync(path.join(os.tmpdir(), 'mutar-097-'));
  const statusAntes = gitStatus();
  // ⛔ a rede de segurança: se o processo morrer no meio (Ctrl-C, exceção), o
  //    arquivo mutado volta mesmo assim. Restaurar por CÓPIA, nunca por `git`:
  //    o trabalho não commitado de quem está editando não pode ser perdido.
  let emAberto = null;
  const restaurar = () => {
    if (!emAberto) return;
    try { fs.copyFileSync(emAberto.bak, emAberto.caminho); } catch { /* último recurso */ }
    emAberto = null;
  };
  process.on('exit', restaurar);
  for (const sinal of ['SIGINT', 'SIGTERM']) {
    process.on(sinal, () => { restaurar(); process.exit(130); });
  }

  console.log('='.repeat(78));
  console.log(`  🔴 PAINEL DE MUTAÇÃO — ${lista.length} mutação(ões) · SPEC-097`);
  console.log(`     backups em ${abrigo} · restauro por CÓPIA, sempre`);
  console.log('='.repeat(78));

  const placar = [];
  for (const m of lista) {
    const caminho = path.join(RAIZ, m.arquivo);
    const original = fs.readFileSync(caminho, 'utf8');
    const hashAntes = digest(original);
    const bak = path.join(abrigo, `${m.id}.bak`);
    fs.writeFileSync(bak, original);
    const veredito = { id: m.id, arquivo: m.arquivo, faltando: [], vermelhos: 0, erro: null };
    try {
      const ocorrencias = original.split(m.ancora).length - 1;
      if (ocorrencias !== 1) {
        // 🔴 FALHA ALTO. Uma âncora morta significa que o produto mudou e a
        //    mutação ficou para trás — o conserto é a âncora, nunca o placar.
        throw new Error(`ÂNCORA MORTA: aparece ${ocorrencias}× em ${m.arquivo} (tem de ser 1)`);
      }
      emAberto = { caminho, bak };
      fs.writeFileSync(caminho, original.replace(m.ancora, () => m.substituto));
      const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url)], {
        cwd: RAIZ, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
      });
      const saida = String(r.stdout || '') + String(r.stderr || '');
      const vermelhos = saida.split('\n')
        .filter((l) => /^\s{2}X\s/.test(l))
        .map((l) => l.replace(/^\s*X\s+/, '').trim());
      veredito.vermelhos = vermelhos.length;
      veredito.rc = r.status;
      veredito.faltando = (m.vermelho || []).filter((esperado) => !vermelhos.some((v) => v.includes(esperado)));
      veredito.acusaram = (m.vermelho || []).filter((esperado) => vermelhos.some((v) => v.includes(esperado)));
      if (r.status === 0) veredito.faltando.push('(a suíte inteira ficou VERDE com a mutação aplicada)');
    } catch (e) {
      veredito.erro = String(e.message);
    } finally {
      fs.copyFileSync(bak, caminho);
      emAberto = null;
    }
    const hashDepois = digest(fs.readFileSync(caminho, 'utf8'));
    if (hashDepois !== hashAntes) veredito.naoRestaurou = true;

    const ok = !veredito.erro && !veredito.faltando.length && !veredito.naoRestaurou;
    console.log(`\n${ok ? '  🔴 VERMELHA' : '  🟢 VERDE   '}  ${m.id}  ${m.arquivo}`);
    console.log(`               ${m.o_que}`);
    if (veredito.erro) console.log(`               ⛔ ${veredito.erro}`);
    else {
      console.log(`               ${veredito.vermelhos} asserção(ões) vermelha(s) na corrida mutada (rc=${veredito.rc})`);
      for (const nome of veredito.acusaram || []) console.log(`               ✔ acusou: ${nome}`);
      for (const nome of veredito.faltando) console.log(`               ✘ NÃO acusou: ${nome}`);
    }
    if (veredito.naoRestaurou) console.log('               ⛔ O ARQUIVO NÃO VOLTOU AO ORIGINAL — confira antes de seguir');
    placar.push(veredito);
  }

  const statusDepois = gitStatus();
  const vermelhas = placar.filter((v) => !v.erro && !v.faltando.length && !v.naoRestaurou);
  const verdes = placar.filter((v) => !vermelhas.includes(v));

  console.log(`\n${'='.repeat(78)}`);
  console.log(`  PLACAR — ${placar.length} mutação(ões) · ${vermelhas.length} VERMELHA(S) POR NOME · ${verdes.length} VERDE(S)`);
  if (verdes.length) {
    console.log('\n  🟢 AS VERDES (uma mutação que não deixa nada vermelho é edição, não mutação):');
    for (const v of verdes) console.log(`     - ${v.id}: ${v.erro || v.faltando.join(' | ')}`);
  }
  if (statusDepois !== statusAntes) {
    console.log('\n  ⛔ A ÁRVORE MUDOU durante o painel:');
    console.log(`     antes: ${JSON.stringify(statusAntes)}`);
    console.log(`     depois: ${JSON.stringify(statusDepois)}`);
  } else {
    console.log(`\n  ✔ árvore idêntica antes e depois (\`git status --short\`, ${statusAntes ? statusAntes.split('\n').length : 0} linha(s))`);
  }
  console.log('='.repeat(78));
  process.exit(verdes.length || statusDepois !== statusAntes ? 1 : 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// A execução
// ─────────────────────────────────────────────────────────────────────────────
console.log('='.repeat(78));
console.log('  A OPERAÇÃO TEM UMA CASA — o guarda da TELA e do BFF  (SPEC-097)');
console.log('='.repeat(78));
console.log(`  📊 fixtures: ${N_CONVERSAS_ALFA} conversas de Alfa (${N_FRESCAS} vivas, ${N_VELHAS} em silêncio,`);
console.log(`     ${N_RESOLVIDAS} com resolvido_em, ${N_ASSUMIDAS} assumidas, 1 HUMAN_REQUESTED) ·`);
console.log(`     ${N_SESSOES_ALFA} episódios (90% com elo) · 5 esperas ativas · 2 runs failed · 1 aprovação · Beta com 50.`);

const mundoDoTeste = fixtures();

const obsFila = await observarProjecao({ opcoes: { group_by: 'stage' } });
const obsCasos = await observarProjecao({ opcoes: {} });
const obsRotaFila = await observarRota(CAMINHO_FILA);
const obsClaim = await observarClaim({});
const obsFicha = await observarRota(CAMINHO_FICHA, { params: { id: CONVERSA_DA_FICHA } });

console.log('\n[1] R5/U5 — FILA E CASOS CHAMAM A MESMA FUNÇÃO');
checar(analisarUmaFuncao({ rota: obsRotaFila, projecao: obsFila }), '[1] a rota da Fila não tem consulta própria: ela lê `projetarCasos`');
checar(analisarQuadro({ quadro: obsFila }), "[1] o Quadro é `group_by:'stage'` da MESMA função (counts somam os items)");
controle(analisarUmaFuncao({
  rota: { registro: [{ op: 'select', tabela: 'conversations', predicados: [{ op: 'eq', coluna: 'company_id' }, { op: 'eq', coluna: 'channel' }] }] },
  projecao: { registro: [{ op: 'select', tabela: 'attendance_sessions', predicados: [{ op: 'eq', coluna: 'company_id' }] }] },
}), '[1] rota-controle com consulta PRÓPRIA (duas funções de leitura)');
controle(analisarQuadro({ quadro: { saida: { items: [1, 2, 3], counts: { em_conversa: 9 } } } }),
  '[1] quadro-controle cujos counts não somam os items');

console.log('\n[2] R1 — SILÊNCIO É `parado`, NUNCA `concluido`');
checar(analisarParado({ observacao: obsFila, mundo: mundoDoTeste }),
  `[2] as ${N_VELHAS} em silêncio viram 'parado' com \`parado_ha\`; só as ${N_RESOLVIDAS} com \`resolvido_em\` são 'concluido'`);
controle(analisarParado({
  observacao: { saida: { items: [
    { key: 'a', stage: 'concluido', conversa_id: 'x1', resolvido_em: null },
    { key: 'b', stage: 'concluido', conversa_id: 'x2', resolvido_em: null },
  ] } },
  mundo: { conversations: [{ id: 'x1', resolvido_em: null }, { id: 'x2', resolvido_em: null }] },
}), '[2] projeção-controle com o `else concluido` do silêncio de volta');
controle(analisarParado({
  observacao: { saida: { items: [{ key: 'a', stage: 'parado', conversa_id: 'x1', parado_ha: '3d', resolvido_em: '2026-09-01T00:00:00Z' }] } },
  mundo: { conversations: [{ id: 'x1', resolvido_em: '2026-09-01T00:00:00Z' }] },
}), '[2] projeção-controle com `resolvido_em` preenchido e stage `parado` (a bicondicional quebrada)');

console.log('\n[3] R1 — O MESMO PAYLOAD NÃO SE CONTRADIZ');
checar(analisarContradicao({ observacao: obsFila, mundo: mundoDoTeste }),
  '[3] `semana.terminaram` conta a partir do MESMO `resolvido_em` que produz os itens "concluido"');
controle(analisarContradicao({
  observacao: { saida: { items: [{ stage: 'concluido' }, { stage: 'concluido' }], semana: { terminaram: 0 } } },
}), '[3] payload-controle com 2 concluídos e `semana.terminaram: 0` (o defeito medido em §1.1)');

console.log('\n[4] R2 — O DONO NÃO É O STATUS');
checar(analisarClaim({ claim: obsClaim }), '[4] o claim grava `claimed_by/claimed_by_name/claimed_at` e NÃO `status`');
checar(analisarDonoAntesDeStatus({ observacao: obsFila }), "[4] a conversa assumida aparece em 'com_equipe' (dono testado ANTES de status)");
controle(analisarClaim({ claim: { updates: [{ payload: { status: 'HUMAN_REQUESTED', claimed_by: U_ALFA, claimed_by_name: 'x', claimed_at: 'y' } }] } }),
  '[4] claim-controle que grava `status` junto do dono');
controle(analisarDonoAntesDeStatus({
  observacao: { saida: { items: [{ key: 'a', stage: 'precisa_de_voce', dono: { id: U_ALFA, nome: 'Ana' } }] } },
}), '[4] cascata-controle que testa status ANTES do dono (com_equipe inalcançável)');
// 🔴 A-3 — a linha em que o defeito histórico mora: dono E `HUMAN_REQUESTED`
checar(analisarDonoVenceStatus({ observacao: obsFila }),
  `[4] a conversa que PEDIU UMA PESSOA e JÁ TEM DONO sai em 'com_equipe' — o dono vence o status (${CONVERSA_DO_DEFEITO}, §1.2/R2)`);
controle(analisarDonoVenceStatus({
  observacao: { saida: { items: [{ key: 'a', conversa_id: CONVERSA_DO_DEFEITO, stage: 'precisa_de_voce', dono: { id: U_ALFA, nome: 'Ana' } }] } },
}), '[4] projeção-controle em que a conversa com dono E `HUMAN_REQUESTED` volta a "precisa de você"');
checar(analisarNaoMandeAssumirComDono({ observacao: obsFila }),
  '[4] a conversa que JÁ TEM DONO não recebe "assuma a conversa" como próxima ação (R2/R7)');
controle(analisarNaoMandeAssumirComDono({
  observacao: { saida: { items: [
    { key: 'a', dono: { id: U_ALFA, nome: 'Ana' }, agora: { proxima_acao: { regra: 'pessoa', texto: 'Assuma a conversa — o cliente pediu para falar com uma pessoa.' } } },
    { key: 'b', dono: null, agora: { proxima_acao: { regra: 'pessoa', texto: 'Assuma a conversa.' } } },
  ] } },
}), '[4] payload-controle que manda ASSUMIR uma conversa que já tem dono');

console.log('\n[5] R3 — O CASO É O EPISÓDIO');
checar(analisarEpisodio({ casos: obsCasos, mundo: mundoDoTeste }),
  '[5] Casos é por episódio (`session_id`), e a sessão sem `conversation_id` continua caso "sem conversa vinculada"');
controle(analisarEpisodio({
  casos: { saida: { items: Array.from({ length: 700 }, (_, i) => ({ key: `conv-${i}`, conversa_id: `cv-${i}`, session_id: null })) } },
  mundo: { conversations: Array.from({ length: 700 }, (_, i) => ({ id: `cv-${i}`, company_id: CO_ALFA })), attendance_sessions: Array.from({ length: 4000 }, (_, i) => ({ id: `as-${i}`, company_id: CO_ALFA })) },
}), '[5] projeção-controle por CONVERSA (700 itens para 4.000 episódios)');
controle(analisarEpisodio({
  casos: { saida: { items: [{ key: 'a', session_id: 'as-1', conversa_id: null, sem_conversa_vinculada: false }] } },
  mundo: { conversations: [], attendance_sessions: [{ id: 'as-1', company_id: CO_ALFA }] },
}), '[5] projeção-controle com episódio órfão SEM o rótulo `sem_conversa_vinculada`');

console.log('\n[6] R4 — A ESPERA VEM DE `work_waits`, NUNCA DO TEXTO');
checar(analisarEspera({ observacao: obsFila }),
  '[6] "esperando a seguradora" só de `work_waits` ativo, com `desde`, id da linha e `due_at` vencido marcado');
controle(analisarEspera({
  observacao: { saida: { items: [{ key: 'a', esperando: { kind: 'esperando_documento', desde: null } }] } },
}), '[6] espera-controle com kind fora do CHECK ("documento" NEM É kind) e sem `desde`/id');

console.log('\n[7] R5 — PAGINAÇÃO POR CURSOR E BUSCA NO BANCO');
const obsPag1 = await observarProjecao({ opcoes: {} });
const obsPag2 = await observarProjecao({ opcoes: { cursor: `${iso(AGORA - 5 * D)}|as-alfa-0100`, limite: 50 } });
const obsBusca = await observarProjecao({ opcoes: { busca: PROTOCOLO_ANTIGO } });
checar(analisarPaginacao({ pagina1: obsPag1, pagina2: obsPag2, busca: obsBusca }),
  '[7] sem `.limit(120)`; cursor `(ultimo_evento_em, id)` pedido ao BANCO; busca com `ilike`/`textSearch`');
checar(analisarBuscaNoCliente({ codigo: existe(CAMINHO_CASOS_CLIENTE) ? fonte(CAMINHO_CASOS_CLIENTE) : null }),
  '[7] o cliente de Casos não filtra a busca em memória — ele manda o termo ao servidor');
controle(analisarPaginacao({
  pagina1: { registro: [{ op: 'select', tabela: 'conversations', limite: 120, predicados: [], ordens: [], or: [], ilike: [], textSearch: [] }] },
  pagina2: { registro: [{ op: 'select', tabela: 'conversations', limite: 120, predicados: [], ordens: [], or: [], ilike: [], textSearch: [] }] },
  busca: { registro: [{ op: 'select', tabela: 'conversations', limite: 120, predicados: [], ordens: [], or: [], ilike: [], textSearch: [] }], saida: { items: [] } },
}), '[7] projeção-controle com `.limit(120)` fixo, sem cursor e com a busca no cliente');
controle(analisarBuscaNoCliente({ codigo: 'const vis = items.filter((i) => !q || i.titulo.includes(q));' }),
  '[7] cliente-controle que ainda filtra a busca em memória');
// 🔴 A-4 — e a FILA, que era o ramo NÃO observado (e é o do defeito de §1.5)
checar(analisarLeituraDaFila({ fila: obsFila }),
  '[7] a FILA lê TODAS as conversas em lotes de 1.000 (`.range(de, de+999)`), sem `.limit(120)` e sem teto silencioso (E11/§1.5)');
controle(analisarLeituraDaFila({
  fila: { registro: [{ op: 'select', tabela: 'conversations', limite: 120, range: null, predicados: [], ordens: [], or: [], ilike: [], textSearch: [] }], saida: { items: [1, 2, 3] } },
}), '[7] fila-controle com `.limit(120)` no ramo do Quadro (o ramo que ninguém observava)');

console.log('\n[8] R5 — `indisponivel` POR FONTE, NUNCA ZERO SILENCIOSO');
const obsFalha = await observarProjecao({ opcoes: { group_by: 'stage' }, falhar: new Set(['work_waits']) });
checar(analisarIndisponivel({ comFalha: obsFalha, semFalha: obsFila }),
  '[8] derrubando `work_waits` no dublê, a fonte é DECLARADA indisponível (e sem falha, nenhuma é)');
controle(analisarIndisponivel({
  comFalha: { saida: { indisponivel: { conversas: false, esperas: false } } },
  semFalha: { saida: { indisponivel: { conversas: false, esperas: false } } },
}), '[8] payload-controle com `indisponivel:false` fixo mesmo com a fonte derrubada');

console.log('\n[9] R6/R7 — O AGORA: 6 DIMENSÕES, 4 RAZÕES OBSERVÁVEIS, PRECEDÊNCIA');
checar(analisarAgora({ observacao: obsFila }),
  '[9] `agora` com as 6 dimensões; atenção só observável; próxima ação com fonte e regra da precedência');
controle(analisarAgora({
  observacao: { saida: { items: [{ key: 'a', agora: { situacao: 'x', dono: null, esperando: null, ha_quanto_tempo: '2d', atencao: ['sla_at_risk'], proxima_acao: { texto: 'cobrar' } } }] } },
}), '[9] agora-controle com razão inventada (`sla_at_risk`) e próxima ação SEM fonte');
controle(analisarAgora({
  observacao: { saida: { items: [{ key: 'a', agora: { situacao: 'x', dono: null, atencao: ['parado'], proxima_acao: { texto: 'x', fonte: 'espera' } } }] } },
}), '[9] agora-controle sem as 6 dimensões (faltam `esperando` e `ha_quanto_tempo`)');

console.log('\n[10] R8 — A TIMELINE NÃO PERDE EVENTO, TEM FONTE, E O SEM HORA VAI PARA O FIM');
// 🔴 A-1 — a Ficha da conversa ASSUMIDA (todas as fontes com hora)
checar(analisarTimeline({ ficha: obsFicha, mundo: mundoDoTeste, conversaId: CONVERSA_DA_FICHA }),
  '[10] a timeline traz UM evento por FATO das fontes (nada é descartado), cada um com `fonte` ∈ {conversa, corredor, trabalho, espera, aprovação, peça} e `fonte_id`, e o que não tem hora vai para o fim, marcado');
checar(analisarTodosComHora({ ficha: obsFicha }),
  '[10] no mundo em que TODA fonte tem hora no banco, nenhum evento da Ficha chega sem hora (📊 E16: 6 de 9 tipos, R8)');
// 🔴 A-1 — e o mundo em que a fonte NÃO tem hora: o evento continua lá
const obsFichaSemHora = await observarRota(CAMINHO_FICHA, { params: { id: CONVERSA_SEM_HORA }, linhas: mundoSemHora() });
checar(analisarNaoEscondeSemHora({ ficha: obsFichaSemHora, mundo: mundoSemHora(), conversaId: CONVERSA_SEM_HORA }),
  '[10] a Ficha NÃO esconde o evento sem hora: ele aparece marcado (`sem_hora`), no FIM da lista, e o que tem hora vem antes (A-1)');
checar(analisarSemWorkEvents({ ficha: obsFicha }), '[10] a ficha NÃO consulta `work_events` (telemetria de motor — §18)');
controle(analisarTimeline({
  ficha: { corpo: { timeline: [
    { at: null, label: 'Cliente identificado', fonte: 'conversa', fonte_id: 'x' },
    { at: '2026-09-05T12:00:00Z', label: 'Encerrado', fonte: 'conversa', fonte_id: 'y' },
  ] } },
  mundo: { conversations: [{ id: 'c1', user_name: 'x', claimed_by: 'u', claimed_at: 'h', resolvido_em: 'r' }] },
  conversaId: 'c1',
}), '[10] timeline-controle com 2 eventos para 4 fatos, um `at: null` MUDO e o com hora depois dele');
controle(analisarTodosComHora({
  ficha: { corpo: { timeline: [{ at: null, label: 'Cliente identificado', sem_hora: true, fonte: 'conversa', fonte_id: 'x' }] } },
}), '[10] timeline-controle com um tipo em `at: null` num mundo que tinha a hora');
controle(analisarNaoEscondeSemHora({
  ficha: { corpo: { timeline: [{ at: '2026-09-05T12:00:00Z', label: 'Ana assumiu', fonte: 'conversa', fonte_id: 'x' }] } },
  mundo: mundoSemHora(),
  conversaId: CONVERSA_SEM_HORA,
}), '[10] ficha-controle que DESCARTOU os dois eventos sem hora (a saída fica impecável e mente por omissão)');
controle(analisarSemWorkEvents({
  ficha: { registro: [{ tabela: 'work_events', op: 'select' }], corpo: { timeline: [{ at: 'x', label: 'run.leased', fonte: 'work_events', fonte_id: 'y' }] } },
}), '[10] ficha-controle que lê `work_events` como fonte da timeline');

console.log('\n[11] R9 — DOIS TENANTS');
const obsBeta = await observarProjecao({ companyId: CO_BETA, opcoes: { group_by: 'stage' } });
const obsCruzada = await observarRota(CAMINHO_FICHA, { companyId: CO_BETA, params: { id: 'cv-alfa-0000' } });
checar(analisarTenant({ beta: obsBeta, mundo: mundoDoTeste, cruzada: obsCruzada }),
  '[11] a sessão de Beta só vê Beta; a conversa de Alfa por id devolve 404; TODA consulta tem `company_id`');
controle(analisarTenant({
  beta: { saida: { items: [{ key: 'x', conversa_id: 'cv-alfa-0000', session_id: null }] }, registro: [{ op: 'select', tabela: 'work_waits', predicados: [{ op: 'eq', coluna: 'status' }] }] },
  mundo: mundoDoTeste,
  cruzada: { status: 200 },
}), '[11] projeção-controle sem `company_id` numa fonte (vazamento) e ficha cruzada com 200');

console.log('\n[12] R10 — CUTOVER: "Histórico" não é mais rótulo, e `parado` entra no vocabulário');
checar(analisarCutover({
  modulos: existe(CAMINHO_MODULOS) ? fonte(CAMINHO_MODULOS) : null,
  filaCliente: existe(CAMINHO_FILA_CLIENTE) ? fonte(CAMINHO_FILA_CLIENTE) : null,
}), '[12] "Histórico" saiu do módulo e do link da Fila (R10/BLOCO K)');
checar(analisarEstagioParado({ estagios: existe(CAMINHO_ESTAGIOS) ? fonte(CAMINHO_ESTAGIOS) : null }),
  "[12] `ATTENDANCE_STAGES` conhece 'parado'");
controle(analisarCutover({
  modulos: "{ key: 'historico', title: 'Histórico', href: '/dashboard/atendimentos/casos' }",
  filaCliente: '<a href="/dashboard/atendimentos/casos">Histórico</a>',
}), '[12] fontes-controle que ainda declaram o rótulo "Histórico"');
controle(analisarEstagioParado({ estagios: "export const ATTENDANCE_STAGES = ['em_conversa','concluido'] as const;" }),
  "[12] lista-controle sem 'parado'");

console.log('\n[13] R11 — LINGUAGEM HUMANA: nenhum texto do corretor é chave/vocabulário de máquina');
checar(analisarLinguagemHumana({ fila: obsFila, casos: obsCasos, ficha: obsFicha }),
  '[13] `detalhe`/`titulo`/`estagio_label`/`proxima_acao.texto`/`atencao`/timeline/`agora.*` não citam chave de métrica, identificador snake_case.com.ponto nem vocabulário técnico (R11)');
controle(analisarLinguagemHumana({
  fila: { saida: { items: [{ key: 'a', detalhe: 'aguardando work_run 3f2a (unblock_state=travado)' }] } },
  casos: { saida: { items: [] } },
  ficha: { corpo: { timeline: [] } },
}), '[13] payload-controle com `detalhe` citando work_run/unblock_state — linguagem de máquina no texto do corretor');
checar(analisarLinguagemHumana({
  fila: { saida: { items: [{ key: 'a', detalhe: 'Aguardando retorno da seguradora há 2 dias.' }] } },
  casos: { saida: { items: [] } },
  ficha: { corpo: { timeline: [{ label: 'Atendimento concluído' }] } },
}), '[13] payload-controle limpo — texto humano não é acusado (prova que o guarda distingue)');

console.log('\n[14] SCHEMA VIVO — nenhuma consulta pediu coluna que não existe no banco');
checar(analisarSchemaVivo({ registros: [
  obsFila.registro, obsCasos.registro, obsRotaFila.registro, obsClaim.registro, obsFicha.registro,
  obsPag1.registro, obsPag2.registro, obsBusca.registro, obsFalha.registro,
  obsBeta.registro, obsCruzada.registro, obsFichaSemHora.registro,
] }), '[14] `projetarCasos`/rotas de atendimento só pedem colunas do schema_vivo.json (+ migration 20260905_01)');

// PAR — a mesma régua, sobre uma consulta com o defeito de propósito e sobre
// uma consulta limpa (protocolo §9.2: toda bateria precisa de controle).
const regSuja14 = [];
const resultadoSuja14 = await dubleSupabase(fixtures(), regSuja14)
  .from('work_waits').select('id, due_at').eq('company_id', CO_ALFA);
checar(
  (!resultadoSuja14.error || resultadoSuja14.error.code !== '42703')
    ? [`o dublê não devolveu 42703 para \`work_waits.due_at\` (recebeu: ${JSON.stringify(resultadoSuja14.error)})`]
    : [],
  '[14] o dublê responde `due_at` em `work_waits` exatamente como o PostgREST — 42703',
);
controle(analisarSchemaVivo({ registros: [regSuja14] }),
  '[14] CONTROLE — select-controle com `due_at` em `work_waits` (coluna que não existe) é acusado por [14]');

const regLimpa14 = [];
const resultadoLimpa14 = await dubleSupabase(fixtures(), regLimpa14)
  .from('work_waits').select('id, kind, status, vence_em').eq('company_id', CO_ALFA);
checar(
  resultadoLimpa14.error ? [`select-controle LIMPO recebeu erro inesperado: ${JSON.stringify(resultadoLimpa14.error)}`] : [],
  '[14] o dublê NÃO falha um select-controle limpo (`vence_em`, não `due_at`)',
);
checar(analisarSchemaVivo({ registros: [regLimpa14] }),
  '[14] CONTROLE — select-controle LIMPO não é acusado por [14] (prova que a régua distingue)');


// ═════════════════════════════════════════════════════════════════════════════
// [15] O QUE A LENTE DO DADO E O RED TEAM ACHARAM — cada conserto, uma régua
// ═════════════════════════════════════════════════════════════════════════════
//
// 🔴 Todas EXECUTAM o produto (§9.4): nenhuma lê o código à procura de uma
// frase. E cada uma tem, ao lado, a observação-CONTROLE com o defeito de volta
// — senão o verde não prova nada (§9.3).

console.log('\n[15] OS CONSERTOS DO DADO E DO RED TEAM');

// ── um mundo pequeno, feito para as bordas que a fixture grande não tem ──────
function mundoDasBordas() {
  const AGORA_ISO = iso(AGORA);
  return {
    conversations: [
      // (a) encerrada há 40 DIAS — fora da janela da semana e fora das ativas
      { id: 'cv-b-velha', company_id: CO_ALFA, channel: 'whatsapp', status: 'closed',
        user_phone: telefone(1), user_name: 'Segurado Borda 1', last_message_preview: 'x',
        last_message_at: iso(AGORA - 40 * D), created_at: iso(AGORA - 60 * D), session_id: 'ss-b-1',
        claimed_by: null, claimed_by_name: null, claimed_at: null,
        resolvido_em: iso(AGORA - 40 * D), resolucao_motivo: 'acionamento_concluido' },
      // (b) SEM relógio nenhum — nem `last_message_at`, nem `created_at`
      { id: 'cv-b-sem-relogio', company_id: CO_ALFA, channel: 'whatsapp', status: 'open',
        user_phone: telefone(2), user_name: 'Segurado Borda 2', last_message_preview: null,
        last_message_at: null, created_at: null, session_id: 'ss-b-2',
        claimed_by: null, claimed_by_name: null, claimed_at: null,
        resolvido_em: null, resolucao_motivo: null },
      // (c) relógio no FUTURO
      { id: 'cv-b-futuro', company_id: CO_ALFA, channel: 'whatsapp', status: 'open',
        user_phone: telefone(3), user_name: 'Segurado Borda 3', last_message_preview: 'x',
        last_message_at: iso(AGORA + 5 * D), created_at: AGORA_ISO, session_id: 'ss-b-3',
        claimed_by: null, claimed_by_name: null, claimed_at: null,
        resolvido_em: null, resolucao_motivo: null },
      // (d) a conversa do encerramento por EPISÓDIO
      { id: 'cv-b-encerrar', company_id: CO_ALFA, channel: 'whatsapp', status: 'open',
        user_phone: telefone(4), user_name: 'Segurado Borda 4', last_message_preview: 'x',
        last_message_at: iso(AGORA - 2 * H), created_at: iso(AGORA - 9 * D), session_id: 'ss-b-4',
        claimed_by: null, claimed_by_name: null, claimed_at: null,
        resolvido_em: null, resolucao_motivo: null },
    ],
    attendance_sessions: [
      // dois episódios da MESMA conversa (d) — um antigo, um corrente
      { id: 'as-b-antigo', company_id: CO_ALFA, conversation_id: 'cv-b-encerrar', counterparty: telefone(4),
        observer_number: '5511900009999', status: 'closed', started_at: iso(AGORA - 9 * D),
        last_event_at: iso(AGORA - 8 * D), resolvido_em: null, resolucao_motivo: null,
        summary: { distilled: { servico: 'guincho' } }, ramo: 'auto', servico: 'guincho' },
      { id: 'as-b-corrente', company_id: CO_ALFA, conversation_id: 'cv-b-encerrar', counterparty: telefone(4),
        observer_number: '5511900009999', status: 'open', started_at: iso(AGORA - 3 * H),
        last_event_at: iso(AGORA - 2 * H), resolvido_em: null, resolucao_motivo: null,
        summary: { distilled: { servico: 'bateria' } }, ramo: 'auto', servico: 'bateria' },
      // um episódio RESOLVIDO nesta semana, com motivo FORA do CHECK
      { id: 'as-b-motivo-estranho', company_id: CO_ALFA, conversation_id: null, counterparty: telefone(5),
        observer_number: '5511900009999', status: 'closed', started_at: iso(AGORA - 4 * D),
        last_event_at: iso(AGORA - 3 * D), resolvido_em: iso(AGORA - 2 * D),
        resolucao_motivo: 'motivo_que_o_check_nao_conhece',
        summary: { distilled: { servico: 'vidros' } }, ramo: 'auto', servico: 'vidros' },
    ],
    work_waits: [],
    work_runs: [
      // o trabalho que parou, com `error_message` de MÁQUINA
      { id: 'wr-b-1', company_id: CO_ALFA, conversation_id: 'cv-b-futuro', status: 'failed',
        runtime_kind: 'acionamento', unblock_state: null, current_step_key: 'ura.menu',
        error_code: 'ura_timeout', error_message: "KeyError: 'x' em unblock_state (work_run 3f2a)",
        created_at: iso(AGORA - 1 * H), input_payload: {} },
    ],
    approval_requests: [],
    messages: [],
  };
}

const bordas = mundoDasBordas();

// ── [15a] P1-1/P3-8 — quem já terminou não se assume, não se devolve, não recebe
const mundoEncerrado = fixtures();
const CONVERSA_ENCERRADA = `cv-alfa-${String(N_FRESCAS).padStart(4, '0')}`;   // uma das 3 com resolvido_em
const claimEncerrado = await observarClaim({ id: CONVERSA_ENCERRADA, linhas: mundoEncerrado });
const releaseEncerrado = await observarClaim({ id: CONVERSA_ENCERRADA, acao: 'release', linhas: fixtures() });
const sendEncerrado = await observarClaim({ id: CONVERSA_ENCERRADA, acao: 'send', corpoExtra: { text: 'oi' }, linhas: fixtures() });

function analisarNaoMexeNoEncerrado({ nome, obs }) {
  if (obs?.erro) return [`${nome} não executou: ${obs.erro}`];
  const p = [];
  if (obs.status !== 409) {
    p.push(`\`${nome}\` numa conversa ENCERRADA devolveu ${obs.status}, não 409 — o desfecho é sobrescrivível pela tela`);
  }
  const escreveuDono = (obs.updates || []).some((u) => u.payload
    && ('claimed_by' in u.payload || 'status' in u.payload));
  if (escreveuDono) {
    p.push(`\`${nome}\` GRAVOU dono/status por cima de um atendimento encerrado — o autor do caso passa a ser quem clicou depois`);
  }
  return p;
}

checar(analisarNaoMexeNoEncerrado({ nome: 'claim', obs: claimEncerrado }),
  '[15] assumir um atendimento ENCERRADO devolve 409 e não grava dono por cima do desfecho (P1-1)');
checar(analisarNaoMexeNoEncerrado({ nome: 'release', obs: releaseEncerrado }),
  '[15] devolver à IA um atendimento ENCERRADO devolve 409 e não apaga o autor (P1-1)');
checar(analisarNaoMexeNoEncerrado({ nome: 'send', obs: sendEncerrado }),
  '[15] escrever num atendimento ENCERRADO devolve 409 — não reabre por escrita (P3-8)');
controle(analisarNaoMexeNoEncerrado({
  nome: 'claim', obs: { status: 200, updates: [{ payload: { claimed_by: U_ALFA, claimed_at: 'x' } }] },
}), '[15] claim-controle que devolve 200 e grava dono numa conversa encerrada');

// ── [15b] P1-5 — o desfecho é gravado no EPISÓDIO CORRENTE, e a conversa espelha
const encerrarPorEpisodio = await observarClaim({
  id: 'cv-b-encerrar', acao: 'close', corpoExtra: { motivo: 'acionamento_concluido' }, linhas: bordas,
});

function analisarEncerraOEpisodio({ obs }) {
  if (obs?.erro) return [`o encerramento não executou: ${obs.erro}`];
  const p = [];
  const naSessao = (obs.updatesDeSessao || []).filter((u) => u.payload && 'resolvido_em' in u.payload);
  if (!naSessao.length) {
    p.push('o "Encerrar" não gravou `resolvido_em` em `attendance_sessions` — o desfecho ficou só na CONVERSA, que é a thread perpétua do telefone (📊 5,8 episódios por contato)');
    return p;
  }
  const motivos = naSessao.map((u) => String(u.payload.resolucao_motivo || ''));
  if (!motivos.includes('acionamento_concluido')) {
    p.push(`o episódio foi encerrado com motivo ${JSON.stringify(motivos)} em vez do que a atendente escolheu`);
  }
  const naConversa = (obs.updates || []).filter((u) => u.payload && 'resolvido_em' in u.payload);
  if (!naConversa.length) p.push('a CONVERSA não recebeu o espelho do desfecho');
  // ⛔ e o episódio ANTIGO da mesma conversa continua aberto
  const antigo = (obs.mundo.attendance_sessions || []).find((x) => x.id === 'as-b-antigo');
  const corrente = (obs.mundo.attendance_sessions || []).find((x) => x.id === 'as-b-corrente');
  if (antigo && antigo.resolvido_em) {
    p.push('o episódio ANTIGO da mesma conversa também foi encerrado — encerrar UM atendimento apagou a história dos outros');
  }
  if (corrente && !corrente.resolvido_em) {
    p.push('o episódio CORRENTE não foi encerrado — o desfecho não chegou onde o caso mora');
  }
  return p;
}
checar(analisarEncerraOEpisodio({ obs: encerrarPorEpisodio }),
  '[15] "Encerrar" grava o desfecho no EPISÓDIO CORRENTE, espelha na conversa e NÃO toca no episódio anterior (P1-5)');
controle(analisarEncerraOEpisodio({
  obs: { updates: [{ payload: { resolvido_em: 'x' } }], updatesDeSessao: [],
    mundo: { attendance_sessions: [{ id: 'as-b-antigo' }, { id: 'as-b-corrente' }] } },
}), '[15] encerramento-controle que grava só na conversa (os 5,8 episódios do telefone num balde)');

// ── [15b′] 🔴 A-7 — E A LEITURA. `[15b]` mede a ESCRITA do desfecho; o
//    derramamento acontecia na PROJEÇÃO, e ninguém olhava. Duas sessões da
//    MESMA conversa, a conversa COM `resolvido_em`: só a sessão que tem
//    desfecho PRÓPRIO pode sair 'concluido'.
const casosDoDerramamento = await observarProjecao({ opcoes: {}, linhas: mundoDoDerramamento() });

function analisarDesfechoNaoDerrama({ obs }) {
  if (obs?.erro) return [`a projeção de Casos não executou: ${obs.erro}`];
  const items = itensDe(obs);
  const fechado = items.find((i) => i.session_id === 'as-d-fechado');
  const aberto = items.find((i) => i.session_id === 'as-d-aberto');
  if (!fechado || !aberto) {
    return [`Casos devolveu ${items.length} item(ns) e não trouxe os DOIS episódios da mesma conversa (as-d-fechado, as-d-aberto) — nada foi medido`];
  }
  const p = [];
  if (fechado.stage !== 'concluido') {
    p.push(`o episódio COM \`resolvido_em\` próprio saiu como '${fechado.stage}' — R1 é bicondicional`);
  }
  if (aberto.stage === 'concluido') {
    p.push('o episódio SEM `resolvido_em` próprio saiu \'concluido\': ele herdou o desfecho DA CONVERSA, e encerrar UM atendimento marca os 5,8 episódios daquele telefone (📊 §1.4, P1-5)');
  }
  if (aberto.resolvido_em) {
    p.push(`o episódio sem desfecho próprio voltou com \`resolvido_em: ${aberto.resolvido_em}\` — o derramamento chegou ao payload`);
  }
  return p;
}
checar(analisarDesfechoNaoDerrama({ obs: casosDoDerramamento }),
  '[15] em CASOS, só o episódio com `resolvido_em` PRÓPRIO é "concluido" — o desfecho da conversa não derrama nos outros episódios (P1-5/A-7)');
controle(analisarDesfechoNaoDerrama({
  obs: { saida: { items: [
    { key: 'epi:as-d-fechado', session_id: 'as-d-fechado', stage: 'concluido', resolvido_em: 'x' },
    { key: 'epi:as-d-aberto', session_id: 'as-d-aberto', stage: 'concluido', resolvido_em: 'x' },
  ] } },
}), '[15] projeção-controle em que o episódio sem desfecho herda o `resolvido_em` da conversa');

// ── [15c] P1-2 — `has_more` é do RESULTADO UNIDO
const paginaCurta = await observarProjecao({ opcoes: { limite: 5 } });
function analisarHasMoreUnido({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const itens = itensDe(obs);
  const p = [];
  if (itens.length > 5) p.push(`a página pediu 5 e devolveu ${itens.length} — o corte da página não é o corte do RESULTADO`);
  if (obs.saida?.has_more !== true) {
    p.push('`has_more` é falso numa página de 5 sobre 4.000 episódios — o botão "carregar mais" some com o acervo atrás dele (P1-2)');
  }
  if (!obs.saida?.cursor) p.push('a página não devolveu cursor — não há como pedir a próxima');
  return p;
}
checar(analisarHasMoreUnido({ obs: paginaCurta }),
  '[15] a página de Casos corta o RESULTADO UNIDO e declara `has_more` (P1-2)');
controle(analisarHasMoreUnido({ obs: { saida: { items: [1, 2, 3, 4, 5], has_more: false, cursor: null } } }),
  '[15] página-controle que corta e diz `has_more: false` (o acervo escondido atrás do botão que sumiu)');

// ── [15d] P2-5 — cursor forjado é DESCARTADO, não vira predicado
const CURSOR_INJETADO = `2026-01-01T00:00:00Z|x,id.gt.0,or(company_id.neq.${CO_ALFA})`;
const comCursorForjado = await observarProjecao({ opcoes: { cursor: CURSOR_INJETADO, limite: 20 } });
function analisarCursorInjetado({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const p = [];
  const sujas = (obs.registro || []).filter((c) => c.or.some((e) => e.includes('id.gt.0') || e.includes('company_id.neq')));
  if (sujas.length) {
    p.push(`${sujas.length} consulta(s) levaram o cursor FORJADO para dentro do \`or(...)\`: ${sujas[0].or.find((e) => e.includes('id.gt.0') || e.includes('company_id.neq'))} — quem controla a URL reescrevia o predicado (P2-5)`);
  }
  if (!itensDe(obs).length) p.push('a projeção devolveu ZERO itens com o cursor inválido — ele deveria ser descartado e a lista voltar à primeira página');
  return p;
}
checar(analisarCursorInjetado({ obs: comCursorForjado }),
  '[15] cursor forjado é descartado (não entra no `or` do PostgREST) e a lista volta à primeira página (P2-5)');
controle(analisarCursorInjetado({
  obs: { registro: [{ or: [`last_event_at.lt.2026-01-01T00:00:00Z,id.gt.0,or(company_id.neq.${CO_ALFA})`], predicados: [] }], saida: { items: [1] } },
}), '[15] projeção-controle que injeta o cursor cru no `or(...)`');

// ── [15e] P2-7 — busca só de curinga devolve NADA, declarado
const buscaSoCuringa = await observarProjecao({ opcoes: { busca: '____' } });
function analisarBuscaSoCuringa({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const p = [];
  const itens = itensDe(obs);
  if (itens.length) {
    p.push(`uma busca por "____" (só curingas do LIKE) devolveu ${itens.length} itens — o acervo inteiro com cara de resultado (P2-7)`);
  }
  if (obs.saida?.busca_invalida !== true) {
    p.push('a lista voltou vazia SEM dizer por quê — "nada encontrado" e "sua busca não tinha nenhuma letra" são respostas diferentes');
  }
  return p;
}
checar(analisarBuscaSoCuringa({ obs: buscaSoCuringa }),
  '[15] busca só com curinga (`____`) devolve lista VAZIA e declarada, nunca o acervo (P2-7)');
controle(analisarBuscaSoCuringa({ obs: { saida: { items: [1, 2, 3], busca_invalida: false } } }),
  '[15] busca-controle que devolve o acervo para um termo sem letra nenhuma');

// ── [15f] P2-8 — o erro do motor não chega ao corretor
const comErroDeMotor = await observarProjecao({ opcoes: { group_by: 'stage' }, linhas: bordas });
function analisarErroDeMotor({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const p = [];
  const textos = itensDe(obs).flatMap((i) => [i.detalhe, i.agora?.situacao, i.agora?.proxima_acao?.texto].filter(Boolean));
  if (!textos.length) return ['nenhum texto foi produzido — nada foi medido'];
  const crus = textos.filter((t) => /KeyError|Traceback|work_run|unblock_state|ura_timeout/.test(String(t)));
  if (crus.length) p.push(`o texto do motor chegou ao corretor: ${JSON.stringify(crus[0])} (R11/P2-8)`);
  const humano = textos.some((t) => /seguradora não respondeu a tempo|precisa de uma pessoa/i.test(String(t)));
  if (!humano) p.push('o trabalho parado não produziu NENHUMA frase humana — o código do erro não virou explicação');
  return p;
}
checar(analisarErroDeMotor({ obs: comErroDeMotor }),
  '[15] `error_code` vira frase de gente; `error_message` NUNCA chega ao card (P2-8)');
controle(analisarErroDeMotor({
  obs: { saida: { items: [{ detalhe: "KeyError: 'x' em unblock_state (work_run 3f2a)" }] } },
}), '[15] payload-controle com `error_message` cru na próxima ação');

// ── [15g] P2-1 — a Ficha de uma conversa encerrada há 40 dias
const fichaVelha = await observarProjecao({
  filtro: { conversa_id: 'cv-b-velha' }, opcoes: { group_by: 'stage' }, linhas: bordas,
});
function analisarFichaForaDaJanela({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const p = [];
  const item = itensDe(obs).find((i) => i.conversa_id === 'cv-b-velha');
  if (!item) {
    p.push('pedir a conversa PELO ID devolveu vazio: ela foi encerrada há 40 dias e não cabe nem em "ativas" nem na janela da semana — a Ficha abriria sem linha nenhuma (P2-1)');
    return p;
  }
  if (item.stage !== 'concluido') {
    p.push(`a conversa encerrada há 40 dias voltou como '${item.stage}' — a Ficha diria que um atendimento do mês passado está acontecendo agora`);
  }
  return p;
}
checar(analisarFichaForaDaJanela({ obs: fichaVelha }),
  '[15] pedir uma conversa PELO ID ignora a janela da semana e devolve o desfecho dela (P2-1)');
controle(analisarFichaForaDaJanela({ obs: { saida: { items: [] } } }),
  '[15] projeção-controle que aplica a janela da Fila a um pedido por id');

// ── [15h] P2-2/P2-3 — a semana conta EPISÓDIO e não perde o motivo estranho
function analisarSemanaPorEpisodio({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const semana = obs.saida?.semana;
  const p = [];
  if (!semana) return ['a projeção não devolveu `semana`'];
  if (!semana.terminaram) {
    p.push('o episódio resolvido nesta semana não entrou em `semana.terminaram` — a conta lê só `conversations` e o card já diz "Encerrado" (P2-2)');
  }
  if (!semana.por_motivo || !semana.por_motivo.outro) {
    p.push('o desfecho com motivo FORA do CHECK sumiu das duas contas — nem terminou, nem morreu esperando; ele existia e não aparecia em lugar nenhum (P2-3)');
  }
  return p;
}
checar(analisarSemanaPorEpisodio({ obs: comErroDeMotor }),
  '[15] `semana` conta o EPISÓDIO resolvido e declara o motivo desconhecido como `outro` (P2-2/P2-3)');
controle(analisarSemanaPorEpisodio({ obs: { saida: { semana: { terminaram: 0, por_motivo: {} } } } }),
  '[15] semana-controle que lê só `conversations` e engole o motivo fora do CHECK');

// ── [15i] P3-1/P3-2 — sem relógio, e relógio no futuro
function analisarRelogio({ obs }) {
  if (obs?.erro) return [`a projeção não executou: ${obs.erro}`];
  const p = [];
  const itens = itensDe(obs);
  const negativas = itens.filter((i) => /-\d/.test(String(i.agora?.ha_quanto_tempo || '')));
  if (negativas.length) {
    p.push(`${negativas.length} caso(s) com duração NEGATIVA (${negativas[0].agora.ha_quanto_tempo}) — um relógio adiantado do provedor produzia "parado há -3 dias" (P3-2)`);
  }
  const semRelogio = itens.find((i) => i.conversa_id === 'cv-b-sem-relogio');
  if (semRelogio && semRelogio.parado_ha === null && semRelogio.stage === 'parado') {
    // ⚠️ `parado` sem duração é aceitável — o que não pode é a tela inventar um número
    if (!/sem movimento|não sabemos|nunca/i.test(String(semRelogio.agora?.situacao || ''))) {
      p.push('o caso SEM relógio nenhum não diz que não há movimento registrado — a tela mostrava "Parado há —", que parece defeito de carga (P3-1)');
    }
  }
  return p;
}
checar(analisarRelogio({ obs: comErroDeMotor }),
  '[15] relógio no futuro não vira duração negativa e a ausência de relógio tem FRASE (P3-1/P3-2)');
controle(analisarRelogio({ obs: { saida: { items: [{ key: 'a', agora: { ha_quanto_tempo: '-3d 4h' } }] } } }),
  '[15] payload-controle com duração negativa ("parado há -3 dias")');

// ── [15j] P3-7 — nenhuma ESCRITA sem `company_id`
function analisarEscritaComTenant({ obs, nome }) {
  if (obs?.erro) return [`${nome} não executou: ${obs.erro}`];
  const escritas = (obs.registro || []).filter((c) => c.op === 'update' || c.op === 'delete');
  const semTenant = escritas.filter((c) => !c.predicados.some((x) => x.coluna === 'company_id'));
  if (!escritas.length) return [`${nome} não fez escrita nenhuma — nada foi medido`];
  return semTenant.length
    ? [`${semTenant.length} escrita(s) em \`${[...new Set(semTenant.map((c) => c.tabela))].join(', ')}\` SEM \`.eq('company_id', …)\` — o backend usa service role e a RLS não protege contra erro de filtro no código (CLAUDE.md §7)`]
    : [];
}
const claimLimpo = await observarClaim({});
checar(analisarEscritaComTenant({ obs: claimLimpo, nome: 'o claim' }),
  '[15] toda escrita das rotas de conversa carrega `company_id` — inclusive a de não-lidas (P3-7)');
controle(analisarEscritaComTenant({
  nome: 'rota-controle',
  obs: { registro: [{ op: 'update', tabela: 'conversations', predicados: [{ op: 'eq', coluna: 'id' }] }] },
}), '[15] escrita-controle sem `company_id` (o UPDATE que atravessa a corretora)');

// ── [15k] P3-3 — a timeline ordena por INSTANTE, não por texto
function analisarOrdemDaTimeline({ ficha }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? [];
  if (timeline.length < 2) return ['a timeline tem menos de 2 eventos — a ordem não foi medida'];
  const p = [];
  for (let i = 1; i < timeline.length; i += 1) {
    const anterior = Date.parse(String(timeline[i - 1].at));
    const atual = Date.parse(String(timeline[i].at));
    if (!Number.isNaN(anterior) && !Number.isNaN(atual) && atual < anterior) {
      p.push(`a timeline está fora de ordem no evento ${i} (${timeline[i].label}): ${timeline[i].at} vem depois de ${timeline[i - 1].at} no texto, mas antes no tempo — `
        + 'o mesmo instante escrito com fuso diferente é a mesma hora e duas strings (P3-3)');
      break;
    }
  }
  return p;
}
checar(analisarOrdemDaTimeline({ ficha: obsFicha }),
  '[15] a timeline da Ficha está ordenada por INSTANTE (fusos diferentes, mesma hora) (P3-3)');
controle(analisarOrdemDaTimeline({
  ficha: { corpo: { timeline: [
    { at: '2026-09-05T12:00:00Z', label: 'a' },
    { at: '2026-09-05T09:00:00-03:00', label: 'b' },
    { at: '2026-09-05T10:00:00Z', label: 'c' },
  ] } },
}), '[15] timeline-controle ordenada por texto (o fuso `-03:00` cai três horas fora do lugar)');

console.log('\n[CTL] O ARNÊS — os dublês conseguem discordar de si mesmos');

const provaDoDuble = await (async () => {
  const reg = [];
  const sb = dubleSupabase(fixtures(), reg);
  const alfa = await sb.from('conversations').select('id').eq('company_id', CO_ALFA);
  const beta = await sb.from('conversations').select('id').eq('company_id', CO_BETA);
  const sem = await sb.from('conversations').select('id');
  const problemas = [];
  if ((alfa.data || []).length !== N_CONVERSAS_ALFA) problemas.push(`o dublê devolveu ${(alfa.data || []).length} conversas de Alfa, não ${N_CONVERSAS_ALFA}`);
  if ((beta.data || []).length !== 50) problemas.push(`o dublê devolveu ${(beta.data || []).length} conversas de Beta, não 50`);
  if ((sem.data || []).length !== N_CONVERSAS_ALFA + 50) problemas.push('sem filtro o dublê não devolve tudo — ele não está aplicando/omitindo nada de forma consistente');
  if (reg.length !== 3) problemas.push(`o registro tem ${reg.length} consultas, não 3`);
  return problemas;
})();
checar(provaDoDuble, '[CTL] o dublê APLICA `company_id` e REGISTRA cada consulta (senão [11] aprova vazamento)');

const provaDaFalha = await (async () => {
  const reg = [];
  const sb = dubleSupabase(fixtures(), reg, new Set(['work_waits']));
  const r = await sb.from('work_waits').select('id').eq('company_id', CO_ALFA);
  return r.error ? [] : ['o dublê com fonte derrubada devolveu sucesso — [8] não mediria nada'];
})();
checar(provaDaFalha, '[CTL] o dublê SABE falhar uma fonte (senão [8] é carimbo)');

const provaDoRegistroDeBusca = await (async () => {
  const reg = [];
  const sb = dubleSupabase(fixtures(), reg);
  await sb.from('attendance_sessions').select('id').ilike('protocolo', `%${PROTOCOLO_ANTIGO}%`).or('a.lt.1,and(a.eq.1,id.lt.2)').order('last_event_at', { ascending: false }).order('id', { ascending: false }).limit(50);
  const c = reg[0];
  const p = [];
  if (!c.ilike.length) p.push('o dublê não registrou `ilike`');
  if (!c.or.length) p.push('o dublê não registrou `or`');
  if (c.ordens.length !== 2) p.push('o dublê não registrou as DUAS ordens');
  if (c.limite !== 50) p.push('o dublê não registrou o `limit`');
  return p;
})();
checar(provaDoRegistroDeBusca, '[CTL] o dublê registra `ilike`/`or`/`order`×2/`limit` (senão [7] aprova busca no cliente)');

/**
 * 🔴 A-8 — O ARNÊS DAS MUTAÇÕES, E ELE AGORA PROVA ALGUMA COISA.
 *
 * A régua antiga conferia id único, caminho existente e `length === 14`. As
 * entradas eram PROSA: sem texto-âncora e sem o nome que deve ficar vermelho.
 * Foi assim que CINCO mutações declaradas nasceram verdes sem ninguém notar.
 *
 * Agora cada entrada tem de ter uma âncora VIVA (exatamente 1 ocorrência no
 * arquivo do produto), um substituto diferente dela, e ao menos um nome de
 * asserção esperado. ⛔ E a âncora não pode ser só comentário: mutar comentário
 * não muda comportamento nenhum, e a mutação ficaria verde por construção.
 */
function analisarMutacoes(lista, esperadas) {
  const p = [];
  const vistos = new Set();
  for (const m of lista) {
    if (vistos.has(m.id)) p.push(`marcador de mutação repetido: ${m.id}`);
    vistos.add(m.id);
    if (!existe(m.arquivo)) {
      p.push(`a mutação ${m.id} aponta para um caminho que não existe: ${m.arquivo}`);
      continue;
    }
    if (!m.ancora || !m.substituto) {
      p.push(`a mutação ${m.id} não tem \`ancora\`/\`substituto\` — ela é PROSA, e prosa não roda (A-8)`);
      continue;
    }
    const ocorrencias = fonte(m.arquivo).split(m.ancora).length - 1;
    if (ocorrencias !== 1) {
      p.push(`a âncora de ${m.id} aparece ${ocorrencias}× em ${m.arquivo} — tem de aparecer EXATAMENTE 1 (zero = âncora morta, o produto mudou e a mutação ficou para trás; duas = a mutação é outra coisa)`);
    }
    if (m.ancora === m.substituto) p.push(`a mutação ${m.id} troca a âncora por ela mesma — é edição, não mutação`);
    if (!Array.isArray(m.vermelho) || !m.vermelho.length) {
      p.push(`a mutação ${m.id} não declara NENHUM nome de asserção que tem de ficar vermelho — sem isso ela passa em silêncio (A-8)`);
    }
    const soComentario = m.ancora.split('\n').every((l) => !l.trim() || l.trim().startsWith('//') || l.trim().startsWith('*'));
    if (soComentario) p.push(`a âncora de ${m.id} é só comentário — mutá-la não muda comportamento nenhum`);
  }
  if (esperadas != null && lista.length !== esperadas) {
    p.push(`MUTACOES tem ${lista.length} entradas; ${esperadas} são deste guarda (as outras 2, U9/U10, são do guarda python)`);
  }
  return p;
}
checar(analisarMutacoes(MUTACOES, 16),
  '[CTL] as 16 mutações deste guarda têm âncora VIVA e ÚNICA no código do produto, substituto e nome-vermelho declarado');
controle(analisarMutacoes([
  { id: 'CTL1', arquivo: CAMINHO_PROJECAO, ancora: '// esta linha nao existe em lugar nenhum do produto', substituto: 'x', vermelho: ['[0]'] },
  { id: 'CTL2', arquivo: CAMINHO_PROJECAO, o_que: 'prosa pura', reprova: 'nada' },
], null), '[CTL] mutações-controle: uma com âncora MORTA (e só comentário) e uma que é só prosa');

// ─────────────────────────────────────────────────────────────────────────────
console.log(`\n${'='.repeat(78)}`);
console.log(`  ${falhas.length} falha(s)`);
if (falhas.length > 0) {
  console.log(`\n  ⛔ ${falhas.length} VERMELHO:`);
  for (const f of falhas) console.log(`     - ${f}`);
  console.log('\n  🔴 Em `7f3f3eb` (a cópia limpa) esta lista É o GATE ZERO da SPEC-097 (§4 BLOCO 0.1).');
  process.exit(1);
}
console.log('\nVERDE — a operação tem uma casa: o desfecho é escrito, o dono é dimensão, o caso é o episódio,');
console.log('        a leitura é uma só, e a timeline tem hora.');
