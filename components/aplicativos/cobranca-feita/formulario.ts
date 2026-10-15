// SPEC-139 · L2 — o formulário de uma ROTINA, EXTRAÍDO de `components/auxiliares/PainelDeRotinas.tsx` (D-139-04).
//
// 🔴 PURO de propósito: nenhum React, nenhuma rede. Aqui mora TUDO o que decide o que é gravado — o estado do
// formulário, cada "clique" (uma função que recebe o estado e devolve o novo), as validações do botão Salvar e o
// CORPO da requisição a `/api/dashboard/rotinas`. Quem desenha (o modal do PainelDeRotinas e a aba Configurar da
// Cobrança) só chama estas funções — por isso os dois gravam o MESMO corpo, e o teste dourado
// (`scripts/a-cobranca-na-casca.test.mjs`) prova isso com hash, contra o código do modal como ele era antes da
// extração. Mudou um byte aqui, o dourado fica vermelho: a Cobrança envia de verdade a segurados.
//
// Cada trecho abaixo é o do PainelDeRotinas (commit 5f9bdac), MOVIDO sem mudar a regra; os porquês históricos
// (SPEC-078, SPEC-EXTRA-001, SPEC-EXTRA-001.6) vieram junto.

export const BILLING_KIND = 'billing_collection';

/**
 * Qual modelo de rotina cada aplicativo configura.
 *
 * 📊 17/08/2026: não há coluna no banco ligando `auxiliary_templates` a `routine_templates` —
 * `auxiliary_templates.default_config` nem sequer tem `kind`, e usa nomes DIFERENTES para os mesmos campos
 * (`portais` vs `portal_keys`). Copiar um no outro faria a seleção de seguradoras cair no default sem avisar.
 * ⚠️ Enquanto essa coluna não existir, um aplicativo novo com rotina própria precisa de uma linha aqui.
 */
export const ROTINA_DO_AUXILIAR: Record<string, string> = {
  'cobranca-feita': BILLING_KIND,
};

export interface Routine {
  id: string;
  name: string;
  instructions: string;
  knowledge?: string | null;
  schedule: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery: { channel?: string; number?: string };
  config?: Record<string, unknown> | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  consecutive_failures: number;
}

export interface Run {
  id: string;
  routine_id: string;
  started_at: string;
  status: string;
  output_preview: string | null;
  error: string | null;
}

export type ModeloDeRotina = {
  id?: string;
  name: string;
  instructions: string;
  schedule_default?: { kind?: string; time?: string; minutes?: number; weekdays?: number[] };
  delivery_default?: { channel?: string };
  config_default?: Record<string, unknown>;
};

/**
 * SPEC-069 — os portais que a Cobrança varre vêm da CONEXÃO, não do código. A lista é a das seguradoras que a
 * própria corretora conectou; as que ainda não têm automação aparecem desligadas e DITAS.
 */
export type PortalOpcao = {
  key: string;
  name: string;
  category: string;
  conectado: boolean;
  automatizado: boolean;
};

/** O estado do formulário — o MESMO `form` que o modal tinha. */
export interface FormDaRotina {
  name: string;
  instructions: string;
  knowledge: string;
  kind: string;
  time: string;
  weekdays: string;
  minutes: number;
  channel: string;
  number: string;
  config: Record<string, unknown>;
}

/** O que está sendo editado: uma rotina que existe, ou uma nova. */
export type Edicao = Routine | 'new';

export const FORM_INICIAL: FormDaRotina = {
  name: '', instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '' as string,
  minutes: 60, channel: 'whatsapp', number: '', config: {} as Record<string, unknown>,
};

/**
 * Os dias da semana, do jeito que gente lê. 🔴 SPEC-078 D.6: a convenção é a do `datetime.weekday()` do Python
 * (0 = segunda … 6 = domingo), confirmada em três lugares do motor — e não é o corretor quem decora isso.
 */
export const DIAS_DA_SEMANA: { valor: number; curto: string; longo: string }[] = [
  { valor: 0, curto: 'seg', longo: 'segunda' },
  { valor: 1, curto: 'ter', longo: 'terça' },
  { valor: 2, curto: 'qua', longo: 'quarta' },
  { valor: 3, curto: 'qui', longo: 'quinta' },
  { valor: 4, curto: 'sex', longo: 'sexta' },
  { valor: 5, curto: 'sáb', longo: 'sábado' },
  { valor: 6, curto: 'dom', longo: 'domingo' },
];

/**
 * Os modos de envio que TÊM MOTOR — SPEC-078 E.1 + SPEC-EXTRA-001.
 *
 *   test     o único que envia em teste. Destino: só o `test_number`.
 *   none     não envia nada — o comportamento correto.
 *   equipe   a atendente recebe o pacote pronto (texto + boleto) e repassa. Um número só, o da corretora.
 *   cliente  o segurado recebe texto e boleto. Exige `confirmacao_cliente` — o motor recusa sem ela.
 *
 * `approval` e `live` NÃO voltam: continuam sem motor (`retido_legado`). Nenhum controle sem motor por trás.
 * O espelho em Python é `MODOS_COM_MOTOR` de `backend/app/services/billing_collection.py`.
 */
export const MODOS_COM_MOTOR = [
  { valor: 'test', rotulo: 'Teste — envia para o meu número de teste' },
  { valor: 'none', rotulo: 'Somente relatório — não envia nada' },
  { valor: 'equipe', rotulo: 'Encaminhar para minha equipe — a atendente recebe o pacote pronto e repassa' },
  { valor: 'cliente', rotulo: 'Enviar diretamente ao cliente — o segurado recebe texto e boleto' },
] as const;

/**
 * As chaves que `build_customer_message` de fato substitui (📊 `billing_collection.py`). Uma chave que não está lá
 * SOME da frase — `_MessageData.__missing__` devolve string vazia. ⚠️ Cópia do Python: o guarda contra o
 * envelhecimento lê o Python.
 */
export const CHAVES_DA_MENSAGEM = [
  '{primeiro_nome}', '{nome_segurado}', '{cliente_nome}', '{nome_atendente}',
  '{nome_corretora}', '{nome_seguradora}', '{numero_parcela}', '{item_segurado}',
  '{numero_apolice}', '{vencimento}', '{valor}', '{apolice}', '{recibo}', '{portal}',
];

/** 📊 `DEFAULT_MESSAGE_TEMPLATE` de `billing_collection.py`, sem cortar. */
export const MENSAGEM_PADRAO = [
  'Olá {primeiro_nome},',
  '',
  'Aqui é a {nome_atendente}, da {nome_corretora}, tudo bem?',
  '',
  'A Seguradora {nome_seguradora} informou que a parcela {numero_parcela} do seguro do {item_segurado} ainda está pendente.',
  '',
  'Desta forma, a seguradora gerou um novo boleto para pagamento pra você não ficar sem cobertura, ok!?',
  '',
  'Qualquer dúvida estou à disposição.',
  '',
  'Segue o boleto abaixo.',
  'Apólice: {numero_apolice}',
].join('\n');

/** Dados fictícios só para a pré-visualização. Nenhum segurado real aqui. */
export const EXEMPLO_DA_PREVIA: Record<string, string> = {
  '{primeiro_nome}': 'Ana', '{nome_segurado}': 'Ana Ribeiro', '{cliente_nome}': 'Ana Ribeiro',
  '{nome_atendente}': 'Maria', '{nome_corretora}': 'sua corretora',
  '{nome_seguradora}': 'ALLIANZ', '{numero_parcela}': '3/12',
  '{item_segurado}': 'HONDA CIVIC ABC1D23', '{numero_apolice}': '0000123456',
  '{vencimento}': '25/08/2026', '{valor}': 'R$ 412,90',
  '{apolice}': '0000123456', '{recibo}': '987654', '{portal}': 'ALLIANZ',
};

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Abrir o formulário (o `openEditor` do modal, em três ramos)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

/** Uma rotina que já existe, como ela está gravada. */
export function formDaRotinaSalva(r: Routine): FormDaRotina {
  return {
    name: r.name,
    instructions: r.instructions,
    knowledge: r.knowledge || '',
    kind: r.schedule?.kind === 'interval' ? 'interval' : 'daily',
    time: r.schedule?.time || '08:00',
    weekdays: (r.schedule?.weekdays || []).join(','),
    minutes: r.schedule?.minutes || 60,
    channel: r.delivery?.channel || 'whatsapp',
    number: r.delivery?.number || '',
    config: (r.config || {}) as Record<string, unknown>,
  };
}

/**
 * 🔴 SPEC-078 D — a rotina nova NASCE PREENCHIDA pelo modelo do aplicativo. O nome é o do APLICATIVO, não o do
 * modelo (D.1). Seg–sex por padrão quando o modelo não diz nada: cobrança em fim de semana não é o esperado.
 */
export function formDoModelo(t: ModeloDeRotina, auxiliarNome: string): FormDaRotina {
  const s = t.schedule_default || {};
  return {
    name: auxiliarNome,
    instructions: t.instructions,
    knowledge: '',
    kind: s.kind === 'interval' ? 'interval' : 'daily',
    time: s.time || '08:00',
    weekdays: (s.weekdays && s.weekdays.length ? s.weekdays : [0, 1, 2, 3, 4]).join(','),
    minutes: s.minutes || 60,
    channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',
    number: '',
    config: t.config_default || {},
  };
}

/** A rotina nova de um aplicativo sem modelo: o corretor ainda pode criar do zero. */
export function formEmBranco(auxiliarNome: string): FormDaRotina {
  return { name: auxiliarNome, instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '0,1,2,3,4', minutes: 60, channel: 'none', number: '', config: {} };
}

/**
 * O modelo deste aplicativo dentro da lista de `/api/dashboard/routine-templates`. Resolver pelo `kind` e não pelo
 * uuid é o que sobrevive a um reseed do template — uuid novo, mesmo `kind`.
 */
export function modeloDoAplicativo(lista: ModeloDeRotina[], auxiliarSlug: string): ModeloDeRotina | null {
  const kind = ROTINA_DO_AUXILIAR[auxiliarSlug];
  if (!kind) return null;
  return lista.find((x) => String(x.config_default?.kind || '') === kind) || null;
}

/** As seguradoras de `/api/dashboard/portal-credentials` (a capacidade já vem resolvida contra o runtime no ar). */
export function portaisDaResposta(j: any): { portais: PortalOpcao[]; degradada: boolean } {
  const comCredencial = new Set(
    ((j?.credentials || []) as { portal_key: string; has_password?: boolean }[])
      .filter((c) => c.has_password)
      .map((c) => c.portal_key),
  );
  // Se o backend não conseguiu confirmar (`degraded`), nenhum portal é marcado como automatizado: dizer "não
  // consegui confirmar" custa uma tentativa, dizer "está pronto" sem estar custa um job que morre.
  const operacional = new Set<string>(
    Array.isArray(j?.cobranca?.operacional) ? j.cobranca.operacional.map(String) : [],
  );
  return {
    degradada: Boolean(j?.cobranca?.degraded),
    portais: ((j?.portals || []) as { key: string; name: string; category: string; cred_kind?: string }[])
      .filter((p) => p.category === 'corretor')
      .map((p) => ({
        key: p.key,
        name: p.name,
        category: p.category,
        conectado: comCredencial.has(p.key) || p.cred_kind === 'public',
        automatizado: operacional.has(p.key),
      })),
  };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O que a tela mostra, derivado do estado (nada aqui é gravado por conta própria)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

export interface DerivadosDaCobranca {
  billingConfig: Record<string, unknown> | null;
  billingPortalKeys: string[];
  billingSendMode: string;
  billingModoLegado: boolean;
  billingTeamNumber: string;
  billingTeamDigitos: string;
  billingConfirmacaoCliente: boolean;
  textoDaMensagem: string;
  chavesDesconhecidas: string[];
  previaDaMensagem: string;
  billingMaxBoletos: number;
  billingTestNumber: string;
  billingAttendantName: string;
  billingDiasEntreCobrancas: number;
}

export function derivarDaCobranca(form: FormDaRotina, portais: PortalOpcao[]): DerivadosDaCobranca {
  const billingConfig = form.config?.kind === BILLING_KIND ? form.config : null;
  // Rotina nova nasce marcando o que é operacional HOJE — derivado, não decorado. Rotina existente mantém
  // exatamente o que a corretora escolheu: uma seguradora nova no registry não liga sozinha a cobrança de ninguém.
  const billingPortalKeys = billingConfig && Array.isArray(billingConfig.portal_keys)
    ? billingConfig.portal_keys.map((v) => String(v))
    : portais.filter((p) => p.automatizado && p.conectado).map((p) => p.key);
  const billingSendMode = String(billingConfig?.send_mode || 'test');
  // 🔴 SPEC-EXTRA-001 — config que ainda carrega `approval`/`live` NÃO é convertida em silêncio para `cliente`:
  // promover uma escolha antiga, feita quando nada saía, em autorização para cobrar segurados de verdade seria
  // decidir pela corretora a coisa mais cara desta tela. O seletor fica SEM valor até alguém escolher.
  const billingModoLegado = !!billingConfig
    && !MODOS_COM_MOTOR.some((m) => m.valor === billingSendMode);
  const billingTeamNumber = String(billingConfig?.team_number || '');
  const billingTeamDigitos = billingTeamNumber.replace(/\D/g, '');
  const billingConfirmacaoCliente = billingConfig?.confirmacao_cliente === true;
  // 🔴 SPEC-078 D.7 — o campo abria VAZIO quando não havia template salvo; o corretor nunca via a mensagem.
  const textoDaMensagem = String(billingConfig?.message_template || '') || MENSAGEM_PADRAO;
  // Chaves escritas que o motor não conhece SOMEM da frase. Avisar antes de salvar é mais barato que o segurado.
  const chavesDesconhecidas = Array.from(
    new Set((textoDaMensagem.match(/\{[a-z_]+\}/g) || []).filter((c) => !CHAVES_DA_MENSAGEM.includes(c))),
  );
  const previaDaMensagem = CHAVES_DA_MENSAGEM.reduce(
    (txt, chave) => txt.split(chave).join(EXEMPLO_DA_PREVIA[chave] ?? ''),
    textoDaMensagem,
  ).replace(/\{[a-z_]+\}/g, '');
  const billingMaxBoletos = Number(billingConfig?.max_boletos_por_execucao || 10);
  const billingTestNumber = String(billingConfig?.test_number || '');
  // 🔴 SPEC-EXTRA-001.6 P0.4 — quem assina a mensagem. Nos modos reais o motor RETÉM a rotina sem ele.
  const billingAttendantName = String(billingConfig?.attendant_name || '');
  // 🔴 SPEC-EXTRA-001.6 B1.3 — o ritmo de cobrança do MESMO segurado (o motor clampa em 1–30; o padrão 7).
  const billingDiasEntreCobrancas = Number(
    billingConfig?.dias_entre_cobrancas_do_mesmo_segurado || 7,
  );
  return {
    billingConfig, billingPortalKeys, billingSendMode, billingModoLegado, billingTeamNumber, billingTeamDigitos,
    billingConfirmacaoCliente, textoDaMensagem, chavesDesconhecidas, previaDaMensagem, billingMaxBoletos,
    billingTestNumber, billingAttendantName, billingDiasEntreCobrancas,
  };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Os cliques — cada um recebe o estado e devolve o novo (o `setForm` do modal, sem o React)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

/** O `setBillingConfig` do modal: todo campo da cobrança entra em `config`, com `kind` garantido. */
export function comCobranca(form: FormDaRotina, patch: Record<string, unknown>): FormDaRotina {
  return {
    ...form,
    config: {
      ...(form.config || {}),
      kind: BILLING_KIND,
      ...patch,
    },
  };
}

/** Liga/desliga UM portal sem mexer nos outros (trocar o array inteiro era o que impedia marcar dois). */
export function alternarPortal(form: FormDaRotina, portais: PortalOpcao[], key: string, marcado: boolean): FormDaRotina {
  const { billingPortalKeys } = derivarDaCobranca(form, portais);
  const semEle = billingPortalKeys.filter((k) => k !== key);
  return comCobranca(form, { portal_keys: (marcado ? [...semEle, key] : semEle).sort() });
}

/** Marca/desmarca um dia da semana; a lista fica em ordem (0 = segunda). */
export function alternarDia(form: FormDaRotina, valor: number): FormDaRotina {
  const marcados = form.weekdays.split(',').map((x) => x.trim()).filter(Boolean);
  const ativo = marcados.includes(String(valor));
  const sem = marcados.filter((x) => x !== String(valor));
  const novos = ativo ? sem : [...sem, String(valor)];
  return {
    ...form,
    weekdays: novos.sort((a, b) => Number(a) - Number(b)).join(','),
  };
}

/**
 * O número DIGITADO num campo da cobrança (máximo de boletos, dias entre cobranças) — o MESMO valor que o modal de
 * `5f9bdac` gravava: `onChange={(e) => setBillingConfig({ max_boletos_por_execucao: parseInt(e.target.value || '10', 10) })}`
 * (e `|| '7'` nos dias). Conserto A da 139 (red team B3): o campo novo fazia `Number(v.replace(/\D/g, ''))` e "2,5"
 * virava 25 boletos por execução. Aqui é o `parseInt` do modal: "2,5" → 2, "1.5" → 1, "07" → 7, "0" → 0, "-5" → -5,
 * vazio → o padrão. Nada de faixa: o modal não prendia, e quem prende é o MOTOR (`_int_clamped`, 1–50 e 1–30).
 * Letras: o `<input type="number">` do modal entregava `''` ao handler (o navegador não aceita texto ali) → o padrão;
 * aqui o mesmo, em vez de gravar `NaN` (que o JSON viraria `null`).
 */
export function numeroDigitadoNoModal(texto: string, padrao: string): number {
  const n = parseInt(texto || padrao, 10);
  return Number.isNaN(n) ? parseInt(padrao, 10) : n;
}

/** Os dias marcados (para a tela pintar o botão). */
export function diasMarcados(form: FormDaRotina): string[] {
  return form.weekdays.split(',').map((x) => x.trim()).filter(Boolean);
}

/** Um campo que não é da cobrança (`instructions`, `knowledge`, `kind`, `time`, `minutes`, `channel`, `number`). */
export function comCampo(form: FormDaRotina, patch: Partial<FormDaRotina>): FormDaRotina {
  return { ...form, ...patch };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Gravar — a rota, o corpo e quando o botão trava
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

/** A ÚNICA rota que grava uma rotina (create/update/pause/activate/delete). */
export const ROTA_DAS_ROTINAS = '/api/dashboard/rotinas';

/**
 * O corpo do POST de gravação — o `saveRoutine` do modal, byte a byte (a ordem das chaves faz parte do hash).
 * 🔴 SPEC-078 C.3 — o dono vai JUNTO (`auxiliar`): "Rotina nunca existe sozinha" (ONTOLOGIA:51).
 */
export function corpoDaGravacao(
  form: FormDaRotina, editing: Edicao, auxiliarSlug: string, portais: PortalOpcao[] = [],
): Record<string, unknown> {
  const { billingConfig, billingSendMode, billingTestNumber } = derivarDaCobranca(form, portais);
  const schedule: Record<string, unknown> = form.kind === 'interval'
    ? { kind: 'interval', minutes: Number(form.minutes) }
    : {
        kind: 'daily', time: form.time,
        ...(form.weekdays.trim()
          ? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }
          : {}),
      };
  const delivery = form.channel === 'whatsapp' ? { channel: 'whatsapp', number: form.number } : { channel: 'none' };
  const outgoingConfig = billingConfig && billingSendMode === 'test' && !billingTestNumber.trim() && form.channel === 'whatsapp'
    ? { ...(form.config || {}), test_number: form.number }
    : form.config;
  return {
    action: editing === 'new' ? 'create' : 'update',
    id: editing !== 'new' && editing ? editing.id : undefined,
    auxiliar: auxiliarSlug,
    name: form.name, instructions: form.instructions, knowledge: form.knowledge, schedule, delivery, config: outgoingConfig,
  };
}

/** O corpo das ações da lista (pausar, reativar, apagar) — o `act` do modal. */
export function corpoDaAcao(id: string, action: 'pause' | 'activate' | 'delete'): Record<string, unknown> {
  return { id, action };
}

/**
 * Por que o botão Salvar está travado — `null` = pode salvar. As condições são as do modal, na mesma ordem; a rota
 * confere as mesmas (o botão é cortesia, a rota é a barreira). 🔴 SPEC-078 D.5: o botão exige o que o servidor
 * exige, e `instructions` não é exigido em aplicativo com motor próprio (o campo é inerte lá, D.2).
 */
export function motivoParaNaoSalvar(form: FormDaRotina, portais: PortalOpcao[] = []): string | null {
  const {
    billingConfig, billingSendMode, billingTestNumber, billingModoLegado, billingTeamDigitos, billingConfirmacaoCliente,
  } = derivarDaCobranca(form, portais);
  if (form.name.trim().length < 3) return 'Falta o nome.';
  if (!billingConfig && form.instructions.trim().length < 10) return 'Descreva o que ele faz (pelo menos 10 letras).';
  if (form.channel === 'whatsapp' && form.number.replace(/\D/g, '').length < 10) {
    return 'Falta o número de WhatsApp que recebe o relatório (DDI + DDD + número).';
  }
  if (billingConfig && billingSendMode === 'test'
      && billingTestNumber.replace(/\D/g, '').length < 10
      && form.number.replace(/\D/g, '').length < 10) {
    return 'Falta o número que recebe a simulação.';
  }
  // 🔴 SPEC-EXTRA-001 — as condições dos modos REAIS.
  if (billingConfig && billingModoLegado) return 'Esta configuração é antiga e não envia nada: escolha uma modalidade.';
  if (billingConfig && billingSendMode === 'equipe'
      && (billingTeamDigitos.length < 10 || billingTeamDigitos.length > 13)) {
    return 'Falta o WhatsApp de quem recebe o pacote na sua equipe (DDI + DDD + número).';
  }
  if (billingConfig && billingSendMode === 'cliente' && !billingConfirmacaoCliente) {
    return 'Para enviar direto ao cliente, marque a confirmação do envio direto.';
  }
  return null;
}

/** O `disabled` do botão Salvar do modal. */
export function salvarTravado(form: FormDaRotina, saving: boolean, portais: PortalOpcao[] = []): boolean {
  return !!(saving || motivoParaNaoSalvar(form, portais) !== null);
}

/** "diária às 08:00 (seg, ter)" · "a cada 60 min" — a linha da lista e do Configurar. */
export function rotuloDaAgenda(s: Routine['schedule']): string {
  if (s?.kind === 'interval') return `a cada ${s.minutes} min`;
  const days = s?.weekdays?.length ? ` (${s.weekdays.map((d) => DIAS_DA_SEMANA[d]?.curto ?? d).join(', ')})` : '';
  return `diária às ${s?.time || '?'}${days}`;
}

/** A mensagem de erro da gravação, em português, com a causa técnica do banco quando ela vem (`details[0]`). */
export function erroDaGravacao(j: any): string {
  const tecnico = Array.isArray(j?.details) ? String(j.details[0] || '').trim() : '';
  return (j?.error || 'Não deu para salvar.') + (tecnico ? ` — ${tecnico}` : '');
}
