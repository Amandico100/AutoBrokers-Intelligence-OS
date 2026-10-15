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
  // SPEC-139 (EXTRA-001.9): a tela diz o PAPEL — "Agente de Atendimento" —, nunca um nome
  // próprio (cada corretora batiza o seu; o nome oficial do produto é AutoBrokers —
  // CLAUDE.md §1). As chaves `even*` e os campos de entrada ficam: são código, não tela.
  add('even', 'Agente de Atendimento criado', flag(input.even_provisioned, 'Agente de Atendimento criado.', 'O Agente de Atendimento ainda não foi criado.'), 'Ver agente de atendimento', `${P}/corretora/agente-de-atendimento`);
  add('core_pers', 'Personalização do AutoBrokers', flag(input.core_personalized, 'Personalizado.', 'Ajuste tom e identidade do AutoBrokers.'), 'Personalizar', `${P}/agentes/autobrokers`);
  add('even_pers', 'Personalização do Agente de Atendimento', flag(input.even_personalized, 'Personalizado.', 'Ajuste nome, voz e mensagens do Agente de Atendimento.'), 'Personalizar', `${P}/corretora/agente-de-atendimento`);
  add('handoff', 'Suporte humano definido', flag(input.handoff_defined, 'Destino do suporte humano configurado.', 'Defina para quem o Agente de Atendimento transfere casos.'), 'Definir suporte humano', `${P}/corretora/suporte-humano`, true);
  add('equipe', 'Equipe configurada', flag((input.team_count ?? 0) >= 1, 'Equipe cadastrada.', 'Cadastre a equipe da corretora.'), 'Abrir equipe', `${P}/corretora/equipe`);
  add('corredor', 'Pelo menos um corredor ativo', flag((input.active_corridors ?? 0) >= 1, `${input.active_corridors ?? 0} corredor(es) ativo(s).`, 'Ative ao menos um corredor.'), 'Ativar corredor', `${P}/corredores`, true);

  // Auxiliares: opcional — não bloqueia produção.
  if ((input.installed_auxiliaries ?? 0) >= 1) add('auxiliar', 'Aplicativos instalados', { status: 'ready', reason: `${input.installed_auxiliaries} instalado(s).` }, 'Ver aplicativos', '/dashboard/auxiliares/meus');
  else add('auxiliar', 'Aplicativos (opcional)', { status: 'not_applicable', reason: 'Nenhum aplicativo instalado (opcional).' }, 'Explorar aplicativos', '/dashboard/auxiliares/galeria');

  add('whatsapp', 'Canal WhatsApp conectado', flag(input.whatsapp_connected, 'WhatsApp conectado.', 'Conecte o WhatsApp para atender segurados.'), 'Conectar canal', `${P}/conectores`, true);
  add('even_ativa', 'Agente de Atendimento ligado', input.even_active ? { status: 'ready', reason: 'Agente de Atendimento ligado.' } : { status: 'pending', reason: 'Agente de Atendimento desligado — ligue depois de configurar e testar.' }, 'Ver agente de atendimento', `${P}/corretora/agente-de-atendimento`, true);
  add('conhecimento', 'Conhecimento privado', flag(input.knowledge_configured, 'Conhecimento configurado.', 'Adicione documentos/fontes da corretora.'), 'Abrir conhecimento', `${P}/corretora/conhecimento`);
  add('aprovadores', 'Aprovadores definidos', flag(input.approvers_defined, 'Aprovadores definidos.', 'Defina quem aprova ações sensíveis.'), 'Definir aprovadores', `${P}/corretora/equipe`);

  const ready_count = items.filter((i) => i.status === 'ready').length;
  const total = items.length;
  // produção pronta só quando TODOS os itens críticos estão ready.
  const production_ready = items.filter((i) => i.critical).every((i) => i.status === 'ready');
  return { items, production_ready, ready_count, total };
}
