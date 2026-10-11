// TA2-B — políticas de autorização PURAS (testáveis offline, sem I/O).
// Centralizam quem pode o quê; as rotas só decodificam a sessão e chamam estas.

/** Papéis tenant que podem ESCREVER configuração da própria corretora. */
export const TENANT_WRITE_ROLES = ['owner', 'admin', 'admin_company', 'master_admin'];

// ─────────────────────────────────────────────────────────────────────────────
// SPEC-131-0 parte A · F1 (D-131-0-14) — o PAPEL DE ACESSO e as FUNÇÕES DE TRABALHO
//
// 🔴 Duas coisas diferentes, de propósito (o modelo é o do Slack: papéis de acesso fechados, separados do que a
// pessoa faz):
//   · o PAPEL diz o que a pessoa PODE no sistema — lista FECHADA; o banco tem o MESMO CHECK
//     (`ck_company_members_role`, migration 20261011_02_spec1310_membros.sql) e o teste
//     `scripts/spec1310-membros.test.mjs` compara as duas listas;
//   · as FUNÇÕES dizem o que a pessoa FAZ na corretora (quem tem carteira, quem calcula, quem conversa com o
//     cliente). ⛔ Função NÃO dá acesso a nada: nenhuma função acima a recebe, e `canWriteTenantConfig` nem a vê.
// ─────────────────────────────────────────────────────────────────────────────

/** Os papéis de acesso que existem — a lista fechada do CHECK `ck_company_members_role`. */
export const PAPEIS_DE_ACESSO = ['owner', 'admin_company', 'member', 'attendant'] as const;
export type PapelDeAcesso = (typeof PAPEIS_DE_ACESSO)[number];

/** Os que a tela da equipe pode dar. `owner` não: o dono nasce no provisionamento da corretora (`is_owner`). */
export const PAPEIS_QUE_A_EQUIPE_DA: readonly PapelDeAcesso[] = PAPEIS_DE_ACESSO.filter((p) => p !== 'owner');

/** As funções de trabalho — a lista fechada do CHECK `ck_company_members_funcoes`. */
export const FUNCOES_DE_TRABALHO = ['comercial', 'calculista', 'negociador'] as const;
export type FuncaoDeTrabalho = (typeof FUNCOES_DE_TRABALHO)[number];

/** O nome de cada papel na tela. Os rótulos dizem quem a pessoa é; `O_QUE_O_PAPEL_PODE` diz o que ela pode. */
export const ROTULO_DO_PAPEL: Record<string, string> = {
  owner: 'Dono', admin_company: 'Administrador', member: 'Membro', attendant: 'Atendente',
  // legados que a política ainda reconhece (nunca gravados em company_members — o CHECK recusa)
  admin: 'Administrador', master_admin: 'Master',
};

export const O_QUE_O_PAPEL_PODE: Record<string, string> = {
  owner: 'configura tudo e responde pela corretora',
  admin_company: 'configura tudo: equipe, agentes, conexões e serviços',
  member: 'usa o sistema e liga e desliga o agente de atendimento',
  attendant: 'liga e desliga o agente de atendimento (o mesmo poder do Membro)',
};

export const ROTULO_DA_FUNCAO: Record<FuncaoDeTrabalho, string> = {
  comercial: 'Comercial', calculista: 'Calculista', negociador: 'Negociador',
};

/** A linha de ajuda da tela, em português de gente. */
export const AJUDA_DAS_FUNCOES =
  'Comercial: tem carteira e Agger próprio. Calculista: monta cálculos, não fala com cliente. Negociador: conversa com o cliente.';

/** O papel pedido pela tela da equipe, se for um que ela pode dar; senão `null` (a rota responde 400 — nunca troca calada). */
export function papelQueAEquipeDa(v: unknown): PapelDeAcesso | null {
  const s = typeof v === 'string' ? v : '';
  return (PAPEIS_QUE_A_EQUIPE_DA as readonly string[]).includes(s) ? (s as PapelDeAcesso) : null;
}

/**
 * Lê as funções pedidas. Lista fechada: um item desconhecido RECUSA o pedido inteiro (nunca é descartado em
 * silêncio). Repetidas viram uma; a ordem é a da lista oficial.
 */
export function lerFuncoes(v: unknown): { ok: true; funcoes: FuncaoDeTrabalho[] } | { ok: false; erro: string } {
  if (!Array.isArray(v)) return { ok: false, erro: 'As funções vêm numa lista.' };
  const desconhecidas = v.filter((x) => typeof x !== 'string' || !(FUNCOES_DE_TRABALHO as readonly string[]).includes(x));
  if (desconhecidas.length) {
    return {
      ok: false,
      erro: `Função desconhecida: ${desconhecidas.map((x) => String(x)).join(', ')}. As funções são Comercial, Calculista e Negociador.`,
    };
  }
  return { ok: true, funcoes: FUNCOES_DE_TRABALHO.filter((f) => v.includes(f)) };
}

/**
 * O papel que vai para o espelho legado `users_v2.role`. 📊 O banco só aceita `admin_company` ou `member` ali
 * (`users_v2_role_check`, lido do catálogo em 11/10/2026) — `attendant` vira `member`, que não administra nada.
 * Só os leitores LEGADOS (cobrança, portal admin antigo) leem o espelho; o acesso ao painel lê `company_members`.
 */
export function papelNoCadastroLegado(papel: string | null | undefined): 'admin_company' | 'member' {
  return papel === 'admin_company' || papel === 'owner' ? 'admin_company' : 'member';
}

/**
 * Papéis que podem LIGAR/DESLIGAR o agente de ATENDIMENTO — e nada mais.
 *
 * 🔴 SPEC-093 BLOCO A. `attendant` existe para uma frase só: a Regina e a
 * Saionara apertam LIGAR de manhã e DESLIGAR quando saem.
 *
 * 📊 O problema medido em 25/08/2026: `company_members` tem **8 admin_company e
 * 2 member**, e o botão exige `TENANT_WRITE_ROLES` — `member` recebe 403. Dar
 * `admin_company` às duas resolveria o botão **e abriria a configuração
 * inteira**: prompt do agente, integrações, billing.
 *
 * ⚠️ **A separação é o ponto, e ela é por CAMPO.** Se o mesmo `PATCH` aceitasse
 * `is_active` e `variables`, dar `attendant` a alguém daria o prompt junto.
 *
 * ✅ E não precisa de migration: 📊 `company_members.role` é `character varying`
 * **sem CHECK e sem enum** — as únicas constraints são as duas FK, a PK e a
 * UNIQUE `(user_id, company_id)`. Criar o papel é dado, não schema.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * 🔴 DECISÃO DO FOUNDER, 09/09/2026 — `member` ENTRA NESTA LISTA.
 *
 * O papel `attendant` foi criado em 25/08 para a Regina e a Saionara — e o
 * cadastro real delas nunca mudou: elas continuam **Membro** em
 * `company_members`, e são elas que ligam o agente de manhã e desligam quando
 * saem. O papel existia; a permissão não chegava a quem precisava dela.
 *
 * ⚠️ **E abrir isto NÃO abre mais nada.** `member` continua fora de
 * `TENANT_WRITE_ROLES` — prompt, tom, nome do agente, equipe, cobrança e chaves
 * seguem exigindo administrador. O portão por CAMPO de `decidirPatchDeAgente` é
 * o que torna esta abertura segura: quem só está aqui passa apenas pelo corpo
 * `{is_active}` do agente de **atendimento**, e por mais nada.
 *
 * ⛔ E o tenant não se move: a corretora vem de `requireCompanyMember`, que a lê
 * da sessão e confere o vínculo ativo. Membro da A não liga o agente da B.
 */
export const ATTENDANCE_TOGGLE_ROLES = [...TENANT_WRITE_ROLES, 'attendant', 'member'];

/**
 * Pode alternar o `is_active` do agente de ATENDIMENTO da própria corretora?
 *
 * 🔴 SEPARADA de `canWriteTenantConfig` de propósito. Quem puder escrever
 * configuração continua podendo tudo; quem for só `attendant` só passa por
 * aqui — e a rota exige, além disto, que o agente seja o de **atendimento** e
 * que o corpo do pedido **não traga mais nada**.
 */
export function canToggleAttendanceAgent(p: { role: string | null; isOwner: boolean }): boolean {
  return Boolean(p.isOwner || (p.role && ATTENDANCE_TOGGLE_ROLES.includes(p.role)));
}

/**
 * O que este `PATCH` de agente está pedindo, e quem pode.
 *
 * 🔴 PURA de propósito: a rota decodifica a sessão e chama esta. É ela que o
 * gate do BLOCO A testa — testar a rota exigiria sessão, cookie e banco, e um
 * gate que precisa de tudo isso é um gate que ninguém roda.
 *
 * ⚠️ **O portão é por CAMPO**, e as três condições fecham portas diferentes:
 *
 * 1. **o corpo pede SÓ o toggle.** Um corpo misto (`{is_active, variables}`)
 *    é hoje aceito com as `variables` **descartadas em silêncio**. Para quem só
 *    tem `attendant`, isso vira 403 — silêncio que parece sucesso é a família
 *    de defeito que este projeto passou a semana matando.
 * 2. **o agente é o de ATENDIMENTO.** 📊 A SPEC-093 não escreve esta condição, e
 *    ela é necessária: `roleForKey('autobrokers')` devolve `'core'`, e um
 *    `attendant` não tem por que ligar ou desligar o agente central.
 * 3. **o papel pode alternar.**
 *
 * ⛔ Quem já escrevia configuração continua podendo tudo o que podia — inclusive
 * corpo misto e agente central.
 *
 * ⚠️ **E o corpo misto faz as DUAS coisas.** 📊 O painel pegou a primeira versão
 * mandando `{is_active, variables}` só para o ramo `config`: as variáveis eram
 * aplicadas e **o desligamento sumia com 200 OK**. Antes desta SPEC o toggle
 * vencia; agora os dois acontecem, e é `tambemAlterna` que diz isso à rota.
 */
export function decidirPatchDeAgente(p: {
  role: string | null;
  isOwner: boolean;
  agentRole: string | null;
  camposDoCorpo: string[];
}): {
  permitido: boolean;
  acao: 'toggle' | 'config';
  motivo: string;
  /** 🔴 Este `PATCH` também alterna `is_active`? */
  tambemAlterna: boolean;
  /** 🔴 Quem chamou pode escrever CONFIGURAÇÃO da corretora? */
  escreveConfiguracao: boolean;
} {
  const pedeToggle = p.camposDoCorpo.includes('is_active');
  const soPedeToggle = p.camposDoCorpo.length > 0
    && p.camposDoCorpo.every((k) => k === 'is_active');
  const escreve = canWriteTenantConfig({ role: p.role, isOwner: p.isOwner });

  if (soPedeToggle) {
    if (p.agentRole === 'attendance' && canToggleAttendanceAgent({ role: p.role, isOwner: p.isOwner })) {
      return {
        permitido: true, acao: 'toggle', motivo: 'toggle_de_atendimento',
        tambemAlterna: true, escreveConfiguracao: escreve,
      };
    }
    if (escreve) {
      return {
        permitido: true, acao: 'toggle', motivo: 'escreve_configuracao',
        tambemAlterna: true, escreveConfiguracao: true,
      };
    }
    return {
      permitido: false, acao: 'toggle', motivo: 'admin_required',
      tambemAlterna: false, escreveConfiguracao: false,
    };
  }

  // 🔴 CORPO MISTO: O TOGGLE NÃO PODE SER ENGOLIDO EM SILÊNCIO.
  //
  // ⚠️ O painel achou a inversão: antes deste bloco, `typeof body.is_active
  // === 'boolean'` era testado PRIMEIRO, então `{is_active:false, variables:{}}`
  // DESLIGAVA o agente (e descartava as variáveis). A primeira versão desta
  // função mandava o mesmo corpo para o ramo `config` — as variáveis eram
  // aplicadas e **o desligamento sumia, com 200 OK**.
  //
  // 🔴 Quem clicou "desligar" leria sucesso e o robô continuaria respondendo
  // segurado. É a família *"silêncio que parece sucesso"* que esta SPEC inteira
  // existe para matar — reintroduzida por um conserto de autorização.
  //
  // Agora o corpo misto faz as DUAS coisas, que é o que o chamador pediu.
  return escreve
    ? {
        permitido: true, acao: 'config', motivo: 'escreve_configuracao',
        tambemAlterna: pedeToggle, escreveConfiguracao: true,
      }
    : {
        permitido: false, acao: 'config', motivo: 'admin_required',
        tambemAlterna: false, escreveConfiguracao: false,
      };
}

/** master_admin de plataforma = role master_admin SEM company travada. */
export function isPlatformMaster(p: { role: string | null; companyId: string | null }): boolean {
  return p.role === 'master_admin' && !p.companyId;
}

/** Usuário tenant pode escrever (editar AutoBrokers/Even) na própria corretora? */
export function canWriteTenantConfig(p: { role: string | null; isOwner: boolean }): boolean {
  return Boolean(p.isOwner || (p.role && TENANT_WRITE_ROLES.includes(p.role)));
}

/** Admin pode LER/ESPELHAR a config de `targetCompanyId` no Portal Admin? */
export function canAdminReadCompany(p: { role: string | null; sessionCompanyId: string | null; targetCompanyId: string }): boolean {
  if (isPlatformMaster({ role: p.role, companyId: p.sessionCompanyId })) return true;
  // company_admin só a própria company.
  return p.role === 'company_admin' && !!p.sessionCompanyId && p.sessionCompanyId === p.targetCompanyId;
}

/** Apenas master pode provisionar/alterar estrutura de qualquer corretora. */
export function canProvisionTenant(p: { role: string | null; companyId: string | null }): boolean {
  return isPlatformMaster(p);
}

/**
 * Same-origin para mutações (defesa em profundidade junto do cookie sameSite=lax).
 * Sem Origin → não bloqueia (alguns clientes legítimos não enviam). Com Origin →
 * o host precisa bater com o Host do servidor.
 */
export function sameOriginOk(p: { origin: string | null; host: string | null }): boolean {
  if (!p.origin) return true;
  if (!p.host) return false;
  try { return new URL(p.origin).host === p.host; } catch { return false; }
}

/**
 * Consistência sessão × banco para usuário tenant. O banco é a fonte de verdade:
 * se a sessão declara uma empresa diferente da de `users_v2`, bloquear.
 */
export function tenantCompanyConsistent(p: { sessionCompanyId: string | null; dbCompanyId: string | null }): boolean {
  if (!p.dbCompanyId) return false; // sem empresa no banco = sem acesso
  if (!p.sessionCompanyId) return true; // sessão sem empresa: usa a do banco
  return p.sessionCompanyId === p.dbCompanyId;
}
