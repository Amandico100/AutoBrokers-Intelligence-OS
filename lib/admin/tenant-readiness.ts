// TA2-B — checklist de prontidão (readiness) PURO. Deriva estado real, sem score
// inventado. Não liga flags, não abre portal, não envia nada: só reflete config.

export type ReadinessStatus = 'ready' | 'pending' | 'not_applicable' | 'blocked';

export interface ReadinessItem {
  key: string;
  label: string;
  status: ReadinessStatus;
  reason: string;
  action: string;
  href: string | null;
  critical: boolean; // itens que bloqueiam "produção pronta"
}

// Entrada: o store preenche com dados reais. `null/undefined` = ainda não configurado.
export interface ReadinessInput {
  company_name?: string | null;
  core_provisioned?: boolean;
  even_provisioned?: boolean;
  core_personalized?: boolean;
  even_personalized?: boolean;
  even_active?: boolean;
  team_count?: number;
  handoff_defined?: boolean;
  active_corridors?: number;
  installed_auxiliaries?: number;
  whatsapp_connected?: boolean;
  knowledge_configured?: boolean;
  approvers_defined?: boolean;
}

const P = '/dashboard/personalizacao';

function flag(ok: boolean | undefined, okReason: string, pendReason: string): { status: ReadinessStatus; reason: string } {
  if (ok === true) return { status: 'ready', reason: okReason };
  return { status: 'pending', reason: pendReason };
}

/** Constrói os itens do checklist a partir do estado real (puro). */
export function buildReadiness(input: ReadinessInput): { items: ReadinessItem[]; production_ready: boolean; ready_count: number; total: number } {
  const items: ReadinessItem[] = [];
  const add = (key: string, label: string, f: { status: ReadinessStatus; reason: string }, action: string, href: string | null, critical = false) =>
    items.push({ key, label, status: f.status, reason: f.reason, action, href, critical });

  add('dados', 'Dados da corretora', flag(Boolean(input.company_name), 'Cadastro básico preenchido.', 'Complete o cadastro da corretora.'), 'Abrir cadastro', `${P}/corretora`);
  add('core', 'AutoBrokers provisionado', flag(input.core_provisioned, 'AutoBrokers ativo.', 'AutoBrokers ainda não provisionado.'), 'Ver agente', `${P}/agentes/autobrokers`);
  add('even', 'Even provisionada', flag(input.even_provisioned, 'Even criada.', 'Even ainda não provisionada.'), 'Ver Even', `${P}/agentes/even`);
  add('core_pers', 'Personalização do AutoBrokers', flag(input.core_personalized, 'Personalizado.', 'Ajuste tom e identidade do AutoBrokers.'), 'Personalizar', `${P}/agentes/autobrokers`);
  add('even_pers', 'Personalização da Even', flag(input.even_personalized, 'Personalizada.', 'Ajuste nome, voz e mensagens da Even.'), 'Personalizar', `${P}/agentes/even`);
  add('handoff', 'Handoff humano definido', flag(input.handoff_defined, 'Destino de handoff configurado.', 'Defina para quem a Even transfere casos.'), 'Definir handoff', `${P}/corretora/suporte-humano`, true);
  add('equipe', 'Equipe configurada', flag((input.team_count ?? 0) >= 1, 'Equipe cadastrada.', 'Cadastre a equipe da corretora.'), 'Abrir equipe', `${P}/equipe`);
  add('corredor', 'Pelo menos um corredor ativo', flag((input.active_corridors ?? 0) >= 1, `${input.active_corridors ?? 0} corredor(es) ativo(s).`, 'Ative ao menos um corredor.'), 'Ativar corredor', `${P}/corredores`, true);

  // Auxiliares: opcional — não bloqueia produção.
  if ((input.installed_auxiliaries ?? 0) >= 1) add('auxiliar', 'Auxiliares instalados', { status: 'ready', reason: `${input.installed_auxiliaries} instalado(s).` }, 'Ver auxiliares', '/dashboard/auxiliares/meus');
  else add('auxiliar', 'Auxiliares (opcional)', { status: 'not_applicable', reason: 'Nenhum auxiliar instalado (opcional).' }, 'Explorar galeria', '/dashboard/auxiliares/galeria');

  add('whatsapp', 'Canal WhatsApp conectado', flag(input.whatsapp_connected, 'WhatsApp conectado.', 'Conecte o WhatsApp para atender segurados.'), 'Conectar canal', `${P}/conectores`, true);
  add('even_ativa', 'Even ativa', input.even_active ? { status: 'ready', reason: 'Even ativa.' } : { status: 'pending', reason: 'Even inativa — ative após configurar e testar.' }, 'Ver Even', `${P}/agentes/even`, true);
  add('conhecimento', 'Conhecimento privado', flag(input.knowledge_configured, 'Conhecimento configurado.', 'Adicione documentos/fontes da corretora.'), 'Abrir conhecimento', `${P}/conhecimento`);
  add('aprovadores', 'Aprovadores definidos', flag(input.approvers_defined, 'Aprovadores definidos.', 'Defina quem aprova ações sensíveis.'), 'Definir aprovadores', `${P}/equipe`);

  const ready_count = items.filter((i) => i.status === 'ready').length;
  const total = items.length;
  // produção pronta só quando TODOS os itens críticos estão ready.
  const production_ready = items.filter((i) => i.critical).every((i) => i.status === 'ready');
  return { items, production_ready, ready_count, total };
}
