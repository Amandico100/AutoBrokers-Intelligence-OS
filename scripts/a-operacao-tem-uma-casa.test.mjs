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
// 🔴 MUTAÇÕES — por CÓPIA, e por que elas NÃO rodam sozinhas aqui
// ─────────────────────────────────────────────────────────────────────────────
//
// ⛔ Este guarda NÃO escreve em arquivo de produto. Ele nasce enquanto os
// builders escrevem `app/`, `lib/` e `components/` no mesmo diretório: mutar em
// disco e restaurar por cópia apagaria a edição de quem estivesse salvando
// naquele segundo. Toda linha de CONTROLE aqui é SINTÉTICA e mora em memória —
// mesma superfície, veredito oposto (protocolo §5).
//
// A lista abaixo é para o BUILDER e para a confirmação mecânica, com a árvore
// parada. Uma mutação que não deixa nada vermelho não é mutação: é edição.
// Marcador único por mutação (`_MUTADO_U…`), e a âncora no CÓDIGO que persiste —
// nunca em docstring ou comentário.
//
export const MUTACOES = [
  { id: 'U1', arquivo: 'lib/atendimento/casos.ts',
    o_que: "reintroduzir o ramo `else stage = 'concluido'` do silêncio (48h)",
    reprova: '[2] (640 conversas velhas voltam a ser "encerradas" sem `resolvido_em`)' },
  { id: 'U2', arquivo: 'app/api/dashboard/conversas/[id]/route.ts',
    o_que: "o claim volta a gravar `status: 'HUMAN_REQUESTED'` junto de `claimed_by`",
    reprova: '[4] (o dono e o status voltam a ser a mesma coisa — ACHADO-1b)' },
  { id: 'U3', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'a cascata volta a testar `status` ANTES de `claimed_by`',
    reprova: '[4] (a coluna "com a equipe" volta a ser inalcançável)' },
  { id: 'U4', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'voltar `.limit(120)` fixo na leitura de conversas',
    reprova: '[7] (73% do acervo da AutoFleet some de novo)' },
  { id: 'U5', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'ignorar `opcoes.busca` na consulta (a busca volta a ser do cliente)',
    reprova: '[7] (um protocolo de 60 dias devolve "nada encontrado")' },
  { id: 'U6', arquivo: 'lib/atendimento/casos.ts',
    o_que: 'fixar `indisponivel: false` em vez de marcar a fonte que falhou',
    reprova: '[8] (zero silencioso: a tela mostra 0 num dia em que ninguém olhou)' },
  { id: 'U7', arquivo: 'app/api/dashboard/atendimentos/ficha/[id]/route.ts',
    o_que: 'um tipo de evento da timeline volta a nascer com `at: null`',
    reprova: '[10] (a timeline volta a ter evento sem hora — R8)' },
  { id: 'U8', arquivo: 'app/api/dashboard/atendimentos/route.ts',
    o_que: 'a rota volta a montar a lista com consulta própria em vez de chamar `projetarCasos`',
    reprova: '[1] (duas funções de leitura: Fila e Casos divergem — G4 regride)' },
  { id: 'U11', arquivo: 'lib/atendimento/casos.ts',
    o_que: "remover o `.eq('company_id', …)` de UMA das fontes da projeção",
    reprova: '[11] (vazamento entre corretoras — CLAUDE.md §7)' },
  { id: 'U12', arquivo: 'app/api/dashboard/atendimentos/ficha/[id]/route.ts',
    o_que: "acrescentar `work_events` como fonte da timeline",
    reprova: '[10] (telemetria de motor vira evento do atendimento — §18/R8)' },
  { id: 'M13', arquivo: 'lib/atendimento/casos.ts',
    o_que: "o rótulo do estágio vira a chave crua (`estagio_label = estagio`)",
    reprova: "[13] (o corretor vê 'precisa_de_voce' em vez de \"pediu uma pessoa\" — R11)" },
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
import path from 'node:path';
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
    conversations.push({
      id: `cv-alfa-${String(i).padStart(4, '0')}`,
      company_id: CO_ALFA,
      channel: 'whatsapp',
      // 📊 §1.1: `closed` NÃO existe no acervo (0/728). O status nunca foi o desfecho.
      status: pediuPessoa ? 'HUMAN_REQUESTED' : 'open',
      user_phone: telefone(i),
      user_name: `Segurado Alfa ${i}`,
      last_message_preview: 'mensagem de exemplo',
      last_message_at: iso(AGORA - (fresca ? (i + 1) * H : (3 + i) * D)),
      created_at: iso(AGORA - (30 + i) * D),
      session_id: `ss-alfa-${i}`,
      claimed_by: assumida ? U_ALFA : null,
      claimed_by_name: assumida ? 'Ana da Equipe' : null,
      claimed_at: assumida ? iso(AGORA - 6 * H) : null,
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

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso (o molde de 095/096).
// ─────────────────────────────────────────────────────────────────────────────
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }

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
    cadeia.select = (colunas, opcoes) => { consulta.op = consulta.payload ? consulta.op : 'select'; consulta.colunas = String(colunas ?? ''); consulta.opcoes = opcoes ?? {}; return cadeia; };
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
        return { data: null, count: null, error: { message: String(e.message), code: 'FONTE_INDISPONIVEL' } };
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
async function observarClaim({ companyId = CO_ALFA, acao = 'claim', corpoExtra = {} } = {}) {
  const mundo = fixtures();
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
    const resposta = await silenciando(() => mod.POST(pedido, { params: Promise.resolve({ id: 'cv-alfa-0000' }) }));
    const updates = registro.filter((c) => c.tabela === 'conversations' && c.op === 'update');
    return { corpo: resposta?.body, status: resposta?.status ?? 200, registro, updates, mundo };
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

// [10] R8 — a timeline: `at` em todo item, `fonte` e `fonte_id`, sem `work_events`.
const FONTES_DA_TIMELINE = new Set(['conversa', 'corredor', 'trabalho', 'espera', 'aprovacao', 'aprovação', 'peca', 'peça']);
function analisarTimeline({ ficha }) {
  if (ficha?.erro) return [`a ficha não executou: ${ficha.erro}`];
  const p = [];
  const timeline = ficha.corpo?.ficha?.timeline ?? ficha.corpo?.timeline ?? ficha.corpo?.linha_do_tempo ?? [];
  if (!Array.isArray(timeline) || !timeline.length) return ['a ficha não devolveu timeline — nada foi medido'];
  const semAt = timeline.filter((e) => e.at == null);
  if (semAt.length) {
    p.push(`${semAt.length} de ${timeline.length} eventos com \`at: null\` (📊 E16: 6 de 9 hoje) — ${semAt.slice(0, 4).map((e) => JSON.stringify(e.label)).join(', ')} (R8)`);
  }
  const semFonte = timeline.filter((e) => !e.fonte && !e.source_authority);
  if (semFonte.length) p.push(`${semFonte.length} evento(s) sem \`fonte\` — R8 exige a autoridade de onde o item veio`);
  const semId = timeline.filter((e) => !e.fonte_id && !e.source_id);
  if (semId.length) p.push(`${semId.length} evento(s) sem \`fonte_id\` — sem o id, ninguém volta à autoridade`);
  const fontesRuins = [...new Set(timeline.map((e) => String(e.fonte || e.source_authority || '')).filter(Boolean))]
    .filter((f) => !FONTES_DA_TIMELINE.has(f));
  if (fontesRuins.length) p.push(`fonte fora da lista: ${fontesRuins.join(', ')} — R8 fixa ${[...FONTES_DA_TIMELINE].slice(0, 6).join(', ')}`);
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

/** Só os TEXTOS que a tela mostra ao corretor — nunca as CHAVES do JSON. */
function textosDoItem(i) {
  const t = [];
  const add = (v) => { if (typeof v === 'string' && v.trim()) t.push(v); };
  if (!i || typeof i !== 'object') return t;
  add(i.detalhe);
  add(i.titulo);
  add(i.estagio_label);
  if (i.proxima_acao) add(i.proxima_acao.texto);
  const listaAtencao = i.atencao || i.agora?.atencao || [];
  for (const a of listaAtencao) {
    if (typeof a === 'string') add(a);
    else if (a && typeof a === 'object') { add(a.texto); add(a.label); add(a.rotulo); }
  }
  if (i.agora && typeof i.agora === 'object') {
    add(i.agora.situacao);
    add(i.agora.ha_quanto_tempo);
    if (i.agora.proxima_acao) add(i.agora.proxima_acao.texto);
  }
  return t;
}

/** Os textos da timeline da Ficha (`label`/`texto`/`descricao` — nunca `fonte`/`fonte_id`). */
function textosDaTimeline(timeline) {
  const t = [];
  const add = (v) => { if (typeof v === 'string' && v.trim()) t.push(v); };
  for (const e of (timeline || [])) { add(e.label); add(e.texto); add(e.descricao); }
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
    if (motivos.length) achados.set(texto, motivos);
  }
  for (const [texto, motivos] of achados) {
    p.push(`texto para o corretor expõe linguagem de máquina: "${texto}" — ${motivos.join('; ')} (R11)`);
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
    },
  }));
  process.exit(0);
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

console.log('\n[10] R8 — A TIMELINE TEM HORA, FONTE E `fonte_id`; NADA DE `work_events`');
checar(analisarTimeline({ ficha: obsFicha }), '[10] nenhum item de timeline com `at` nulo; cada um com `fonte` ∈ {conversa, corredor, trabalho, espera, aprovação, peça} e `fonte_id`');
checar(analisarSemWorkEvents({ ficha: obsFicha }), '[10] a ficha NÃO consulta `work_events` (telemetria de motor — §18)');
controle(analisarTimeline({
  ficha: { corpo: { timeline: [{ at: null, label: 'Cliente identificado', fonte: 'conversa', fonte_id: 'x' }] } },
}), '[10] timeline-controle com um tipo em `at: null`');
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

const provaDasMutacoes = (() => {
  const p = [];
  const vistos = new Set();
  for (const m of MUTACOES) {
    if (vistos.has(m.id)) p.push(`marcador de mutação repetido: ${m.id}`);
    vistos.add(m.id);
    // 🔴 o caminho pode ainda não existir (o builder não escreveu) — mas não pode ser fantasma
    if (!existe(m.arquivo) && !m.arquivo.startsWith('lib/atendimento/casos')) {
      p.push(`a mutação ${m.id} aponta para um caminho que não existe: ${m.arquivo}`);
    }
  }
  if (MUTACOES.length !== 11) p.push(`MUTACOES tem ${MUTACOES.length} entradas; 11 são deste guarda (as outras 2 são do guarda python)`);
  return p;
})();
checar(provaDasMutacoes, '[CTL] as 11 mutações deste guarda têm marcador único e caminho real');

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
