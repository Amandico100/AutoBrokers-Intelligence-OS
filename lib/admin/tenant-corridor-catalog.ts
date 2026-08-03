// SPEC-063 (03/08/2026) — montagem PURA do catálogo de corredores (sem I/O).
//
// O QUE MUDOU, E POR QUÊ
// ======================
// Havia DUAS coisas chamadas corredor, e esta tela lia a errada:
//
//   corridor_templates       TABELA     2 linhas       ← a tela lia isto
//   corridor_playbooks.py    CÓDIGO    13 corredores   ← isto EXECUTA
//
// O resultado é que a página mostrava "Allianz Residencial" e "Allianz
// Residencial — Eletricista", e os dez corredores de auto que rodam há meses
// nunca apareceram ali. O GLOSSARIO já declara que o corredor mora em
// `corridor_playbooks.py`; agora a tela lê de lá (via GET /api/corridors/catalog).
//
// `corridor_templates` NÃO é mais o catálogo. Ela sobra como ÂNCORA DE ID da
// ativação — ver `tenant-corridor-store.ts`, que explica por quê.
//
// UM CARD POR (SEGURADORA × RAMO). Decisão do founder, literal:
//   "o corretor não quer saber se tem subcorredores, subserviços... vai
//    confundir ele. Allianz Residencial e aí já vai tudo no pacote."
// Os subserviços vivem DENTRO do corredor, como texto. Nunca como coisa
// ligável: 13 cards, não 40.
//
// Este módulo não conhece seguradora nenhuma. Se alguém precisar escrever
// "porto" ou "guincho" aqui, o catálogo voltou a ter duas fontes.

/** Como o trabalho TERMINA naquela seguradora (declarado no playbook). */
export type CorridorOutcome = 'abre' | 'encaminha';

export interface CorridorSubservice {
  key: string;
  label: string;
  /** `abre` = segue até o protocolo · `encaminha` = a seguradora entrega
   *  formulário/orientação e o caso encerra resolvido por encaminhamento. */
  outcome: CorridorOutcome | string;
  /** `formulario` | `orientacao` — só quando `outcome === 'encaminha'`. */
  referral_kind: string | null;
  /** Há tecla de menu OBSERVADA para este trabalho nesta seguradora? */
  menu_mapeado: boolean;
}

/** Um corredor, exatamente como o código que o executa o declara. */
export interface CorridorFromCode {
  corridor_id: string;
  playbook_ref: string;
  version?: number | null;
  insurer_key: string;
  insurer_label: string;
  line_kind: string;
  line_label: string;
  channel: string;
  channel_label: string;
  title: string;
  description?: string;
  subservices: CorridorSubservice[];
  /** `abre` · `encaminha` · `misto` (uns abrem, outros encaminham). */
  outcome_summary: string;
  handoff_sinistro: boolean;
  menu_mapeado: boolean;
}

export interface TenantCorridorRow { corridor_template_id: string; status: string | null }

export type CorridorUiStatus = 'available' | 'active' | 'paused';

export interface CorridorCatalogItem extends CorridorFromCode {
  status: CorridorUiStatus;
  installed: boolean;
  /** Próximo passo humano — honesto sobre o que a ativação faz e não faz. */
  next_step: string;
}

/**
 * Chaves ANTIGAS de `corridor_templates` que apontam para um corredor do código.
 *
 * 📊 Produção, 03/08/2026: uma corretora tem duas ativações vivas, ambas na
 * família `allianz_residential_assistance` (a do corredor e a do subcorredor
 * "Eletricista"). As duas viraram o MESMO card. Sem esta ponte, a corretora
 * abriria a tela e veria como "disponível" um corredor que ela já ligou.
 *
 * Isto NÃO é catálogo: é tradução de identificador legado, e some no dia em que
 * essas linhas forem repontadas para a âncora nova.
 */
export const LEGACY_TEMPLATE_KEYS: Record<string, string> = {
  allianz_residential_assistance: 'allianz-residencial-whatsapp',
};

/** O corredor a que uma linha de `corridor_templates` pertence. */
export function corridorIdForTemplateKey(templateKey: string): string {
  const key = String(templateKey || '').trim();
  return LEGACY_TEMPLATE_KEYS[key] ?? key;
}

/**
 * Uma decisão só, a partir de N linhas de ativação do mesmo corredor.
 * Ativo vence pausado: se qualquer âncora está ativa, o corredor está ativo.
 * Nenhuma ativação → `null` (nunca instalado).
 */
export function foldActivationStatus(statuses: Array<string | null | undefined>): string | null {
  let paused = false;
  for (const s of statuses) {
    const v = String(s ?? '').trim();
    if (v === 'active') return 'active';
    if (v === 'paused') paused = true;
  }
  return paused ? 'paused' : null;
}

function nextStep(status: CorridorUiStatus, corridor: CorridorFromCode): string {
  if (status === 'active') {
    return corridor.menu_mapeado
      ? 'Ativo para esta corretora. Quem aciona é o roteiro de atendimento.'
      : 'Ativo para esta corretora. Sem menu mapeado, o atendimento chega até a seguradora e uma pessoa assume.';
  }
  if (status === 'paused') return 'Pausado. Retome quando quiser voltar a usá-lo.';
  return 'Disponível. Ative para registrar que sua corretora usa este corredor.';
}

/**
 * Une o catálogo do CÓDIGO com o estado por corretora.
 *
 * @param corridors    os corredores como o motor os declara (nunca uma cópia).
 * @param statusByCorridorId  `corridor_id` → status gravado em `tenant_corridors`
 *                            (`active` | `paused`), ou ausente/`null` se a
 *                            corretora nunca ativou. Corredor não ativado
 *                            aparece como DISPONÍVEL — é assim que ela descobre
 *                            o que pode ligar.
 */
export function buildCorridorCatalog(
  corridors: CorridorFromCode[],
  statusByCorridorId: Record<string, string | null | undefined>,
): CorridorCatalogItem[] {
  return (corridors ?? []).map((c) => {
    const gravado = String(statusByCorridorId?.[c.corridor_id] ?? '').trim();
    const status: CorridorUiStatus =
      gravado === 'active' ? 'active' : gravado === 'paused' ? 'paused' : 'available';
    return {
      ...c,
      subservices: [...(c.subservices ?? [])],
      status,
      installed: status !== 'available',
      next_step: nextStep(status, c),
    };
  });
}

/** Resolve o novo status a partir da ação do usuário (puro). */
export function nextCorridorStatus(action: string): 'active' | 'paused' | null {
  if (action === 'activate' || action === 'resume') return 'active';
  if (action === 'pause') return 'paused';
  return null;
}
