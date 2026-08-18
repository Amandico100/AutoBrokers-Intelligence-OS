import type { IconName } from '@/lib/icons';

export interface NavItem {
  key: string;
  label: string;
  /** Rótulo curto para a bottom-nav mobile (opcional). */
  short?: string;
  href: string;
  icon: IconName;
}

/**
 * Os CINCO pilares da navegação da corretora — SPEC-064 Bloco B.
 *
 * Eram sete, e dois deles eram Auxiliares disfarçados de item de menu:
 *
 *     Briefing    é um Auxiliar. Virou "Checklist das 6h", no catálogo.
 *     Pesquisas   é uma Skill do chat. O resultado se reencontra em Entregas.
 *
 * E havia três itens no secundário respondendo a MESMA pergunta — "o que já
 * aconteceu aqui?": Atividades, Histórico e Conversas. Viraram um pilar só,
 * **Entregas**, com filtro por tipo.
 *
 * A ordem é a do dia do corretor: ele fala com o AutoBrokers, olha os
 * atendimentos, confere quem trabalha por ele, vê o que ficou pronto, e só
 * então mexe em configuração.
 */
export const PILLARS: NavItem[] = [
  { key: 'autobrokers', label: 'AutoBrokers', href: '/dashboard', icon: 'autobrokers' },
  { key: 'atendimentos', label: 'Atendimentos', href: '/dashboard/atendimentos', icon: 'atendimentos' },
  { key: 'auxiliares', label: 'Auxiliares', href: '/dashboard/auxiliares', icon: 'auxiliares' },
  // 🔴 SEXTO PILAR, TEMPORARIO — pedido do Founder em 18/08/2026, para a
  // apresentacao do dia 19.
  //
  // A regra abaixo diz que o menu nao cresce, e ela continua certa. Esta linha
  // e uma EXCECAO CONSCIENTE, autorizada, com data de validade — nao uma
  // revogacao da regra.
  //
  // O motivo: a tela do Segundo Cerebro existe, esta pronta e mostra 📊 17.995
  // cartas de conhecimento, 29 mapas de URA e 18 playbooks de conduta. Ela
  // vivia em `/dashboard/personalizacao/memorias`, dois cliques fundo, dentro
  // do pilar de CONFIGURACAO — e memoria da corretora nao e configuracao, e
  // patrimonio. Ninguem que nao soubesse o endereco a encontrava.
  //
  // QUANDO TIRAR: depois da apresentacao, a decisao certa e uma das duas --
  // ou Memorias vira pilar de verdade (e a regra de cinco muda por escrito),
  // ou volta para dentro de um pilar existente com um caminho visivel ate ela.
  // Ficar aqui sem decisao e a pior das tres.
  { key: 'memorias', label: 'Memórias', href: '/dashboard/memorias', icon: 'conhecimento' },
  { key: 'entregas', label: 'Entregas', href: '/dashboard/entregas', icon: 'success' },
  { key: 'personalizacao', label: 'Personalização', short: 'Config', href: '/dashboard/personalizacao', icon: 'personalizacao' },
];

/**
 * Não existe mais navegação secundária — e isso é o resultado, não a intenção.
 *
 * Ela tinha quatro itens: Atividades, Histórico, Conversas e Configurações.
 *
 *   Atividades · Histórico   respondiam "o que já aconteceu?" → Entregas
 *   Conversas                era uma SEGUNDA tela de conversa da corretora,
 *                            chamando /api/admin/conversations de dentro do
 *                            dashboard. A tela canônica é
 *                            /dashboard/atendimentos/conversas (SPEC-043).
 *                            A duplicata foi removida.
 *   Configurações            é Personalização com outro nome.
 *
 * Um menu secundário existe para o que é raro e legítimo. Quando tudo que
 * está nele ou duplica um pilar ou pertence a um, ele não é secundário: é
 * dívida com barra de rolagem.
 */
export const SECONDARY: NavItem[] = [];

/**
 * A regra que fica: **o menu não cresce.**
 *
 * Coisa nova entra DENTRO de um item que já existe. Se não couber em nenhum,
 * a pergunta certa é se o desenho dos itens está errado — não se falta um item.
 *
 * Ela já existia aqui, escrita, e foi violada duas vezes: Briefing (SPEC-059)
 * e Pesquisas (SPEC-060) entraram como pilares porque "tela sem link é tela
 * que não existe". O diagnóstico estava certo e a conclusão errada — as duas
 * eram Auxiliar e Skill, e o lugar delas era dentro de um pilar existente.
 *
 * Por isso agora a regra é TESTE, não comentário:
 * `backend/tests/test_menu_nao_cresce.py` conta os pilares. Comentário que
 * ninguém é obrigado a obedecer é decoração.
 *
 * Histórico das telas que já mudaram de casa:
 *   /admin/team|agent|documents|billing  → dentro da Personalização
 *   /dashboard/equipe|agente|documentos|plano → idem (redirecionam)
 *   /dashboard/briefing        → /dashboard/auxiliares/checklist-6h
 *   /dashboard/pesquisas       → /dashboard/entregas?tipo=pesquisa
 *   /dashboard/memorias        → /dashboard/personalizacao/memorias
 *   /dashboard/atividades      → /dashboard/entregas
 *   /dashboard/historico       → /dashboard/entregas?tipo=conversa
 *   /dashboard/conversas       → /dashboard/atendimentos/conversas
 */
export const MENU_NAO_CRESCE = 5 as const;

/**
 * Estado ativo da navegação.
 * AutoBrokers (/dashboard) também fica ativo em /dashboard/chat (mesma experiência).
 * Os demais usam match exato ou de subrota.
 */
export function isActiveRoute(pathname: string, href: string): boolean {
  if (href === '/dashboard') {
    return pathname === '/dashboard' || pathname === '/dashboard/chat';
  }
  return pathname === href || pathname.startsWith(href + '/');
}
