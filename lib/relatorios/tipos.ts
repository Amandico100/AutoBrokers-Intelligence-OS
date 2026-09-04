// SPEC-095 A.2 — o mapa ÚNICO de tipos de relatório.
//
// 📊 04/09/2026, medido antes de escrever este arquivo:
//
//     lista   `route.ts:242` mandava `origem: a.kind` CRU — "report", em inglês
//     detalhe `[artifactId]/page.tsx:56-61` tinha um `AUXILIAR_DO_TEMPLATE` só
//             para si, com TRÊS chaves → 35 de 136 peças (25,7%) abriam sem
//             produtor, e um Pulso 360 abria como "Origem: chat"
//
// Duas telas respondendo "o que é isto?" com dicionários diferentes é a forma
// mais barata de o produto se contradizer na frente do dono da corretora. Este
// arquivo é o único lugar onde a resposta mora — a lista e o detalhe leem daqui
// (CLAUDE.md §5: consolidar antes de duplicar).
//
// 🔴 SEM import de runtime, de propósito. Ele é lido por três consumidores com
// ambientes diferentes (route handler Node, Server Component, cliente) e pelos
// guardas, que transpilam a fonte e resolvem `require` à mão. `IconName` entra
// como `import type` — apagado na transpilação — e ainda assim prova em tempo
// de compilação que a chave existe em `lib/icons.ts`, o registro único de
// ícones.
import type { IconName } from '@/lib/icons';

export interface TipoDeRelatorio {
  /** O que o corretor chama a peça. Nunca a `template_key`, nunca o `kind`. */
  tipoHumano: string;
  /** Chave do registro único de ícones (`lib/icons.ts`). */
  icone: IconName;
  /** Quem assina quando o publicador não gravou `subject_ref.produtor`. */
  produtorPadrao: string;
  /** O Auxiliar dono, quando existe tela dele para abrir (`lib/auxiliaries/catalog`). */
  slugDoAuxiliar?: string;
}

/**
 * As seis `template_key` que existem hoje no banco, na tabela da SPEC-095 A.2.
 *
 * Chave nova entra AQUI, uma linha — nunca num `if` dentro de uma tela.
 */
export const TIPO_POR_TEMPLATE: Record<string, TipoDeRelatorio> = {
  'briefing.daily_operational': {
    tipoHumano: 'Briefing do dia',
    icone: 'briefingDiario',
    produtorPadrao: 'Checklist das 6h',
    slugDoAuxiliar: 'checklist-6h',
  },
  'briefing.weekly_executive': {
    tipoHumano: 'Resumo da semana',
    icone: 'resumoSemanal',
    produtorPadrao: 'Checklist das 6h',
    slugDoAuxiliar: 'checklist-6h',
  },
  'executive.pulse360': {
    tipoHumano: 'Pulso 360',
    icone: 'pulso',
    produtorPadrao: 'AutoBrokers',
  },
  'commercial.pipeline': {
    tipoHumano: 'Raio-X comercial',
    icone: 'raioX',
    produtorPadrao: 'AutoBrokers',
  },
  'renewals.radar': {
    tipoHumano: 'Radar de renovações',
    icone: 'radar',
    produtorPadrao: 'AutoBrokers',
  },
  'financial.billing_collection': {
    tipoHumano: 'Cobrança',
    icone: 'cobranca',
    produtorPadrao: 'Cobrança Feita',
    slugDoAuxiliar: 'cobranca-feita',
  },
};

/** A peça de `template_key` desconhecida continua tendo nome, ícone e assinatura. */
export const TIPO_PADRAO: TipoDeRelatorio = {
  tipoHumano: 'Relatório',
  icone: 'documento',
  produtorPadrao: 'AutoBrokers',
};

export function tipoDoRelatorio(templateKey: string | null | undefined): TipoDeRelatorio {
  return TIPO_POR_TEMPLATE[templateKey ?? ''] ?? TIPO_PADRAO;
}

/**
 * O `kind` da coluna em português.
 *
 * `kind` é a palavra do banco ("report"), não a do corretor. Ele só aparece
 * quando o `template_key` não diz nada — é o último recurso, não o primeiro.
 */
export function tipoHumanoPorKind(kind: string | null | undefined): string {
  switch (kind) {
    case 'report':
      return 'Relatório';
    case 'proposal':
      return 'Proposta';
    case 'letter':
      return 'Carta';
    case 'dashboard':
      return 'Painel';
    default:
      return kind || 'Documento';
  }
}

/**
 * Quem produziu a peça, em português — e se isso é DECLARADO ou INFERIDO.
 *
 * 🔴 `legacy_inferred` (proposta §51/§151): o mapa por `origin` + `template_key`
 * é um palpite honesto sobre as 📊 136 peças que nasceram antes de o publicador
 * gravar `subject_ref.produtor` — nunca autoridade. A resposta carrega a
 * procedência para que o guarda a confira; o card NÃO imprime a palavra, porque
 * "AutoBrokers (inferido)" não ajuda ninguém a trabalhar.
 */
export type ProdutorOrigem = 'declarado' | 'inferido';

export interface Produtor {
  nome: string;
  origem: ProdutorOrigem;
}

/** O que a `origin` significa quando nem o template nem o publicador dizem. */
const PRODUTOR_POR_ORIGEM: Record<string, string> = {
  chat: 'AutoBrokers',
  routine: 'Auxiliar',
  manual: 'Você',
  api: 'AutoBrokers',
};

/**
 * O que o publicador GRAVA e o que o corretor LÊ não são a mesma palavra.
 *
 * 📊 `subject_ref.produtor` guarda o slug do produtor (`checklist-6h`,
 * `autobrokers.chat`) — certo para o código, ilegível na tela. Traduzir aqui é
 * o que impede um `autobrokers.chat` de chegar ao card. Valor declarado que não
 * esteja neste mapa passa como veio: quem gravou sabia o que estava escrevendo.
 */
const NOME_DO_PRODUTOR: Record<string, string> = {
  'checklist-6h': 'Checklist das 6h',
  'cobranca-feita': 'Cobrança Feita',
  autobrokers: 'AutoBrokers',
  'autobrokers.chat': 'AutoBrokers',
  'autobrokers.routine': 'Auxiliar',
};

export function produtor(
  origin: string | null | undefined,
  templateKey: string | null | undefined,
  subjectRef: unknown,
): Produtor {
  const declarado = leiaTexto(subjectRef, 'produtor');
  if (declarado) return { nome: NOME_DO_PRODUTOR[declarado] ?? declarado, origem: 'declarado' };

  const doTemplate = TIPO_POR_TEMPLATE[templateKey ?? ''];
  if (doTemplate) return { nome: doTemplate.produtorPadrao, origem: 'inferido' };

  return {
    nome: PRODUTOR_POR_ORIGEM[origin ?? ''] ?? TIPO_PADRAO.produtorPadrao,
    origem: 'inferido',
  };
}

/**
 * O período de que a peça fala — não a hora em que ela foi escrita.
 *
 * 📊 04/09/2026: `subject_ref.id` não vazio em 5/136 peças e `label` em nenhuma;
 * por isso o retorno cai na data da peça quando o publicador não disse de que
 * período ela é. É uma data honesta ("de quando é"), nunca uma afirmação sobre
 * o dado (isso é `data_as_of`, e a SPEC-095 §1.9 mostra por que os dois não são
 * a mesma coisa).
 */
export function periodoDoRelatorio(subjectRef: unknown, quando: string | null | undefined): string {
  const label = leiaTexto(subjectRef, 'label') || leiaTexto(subjectRef, 'id');
  if (label) return label;
  if (!quando) return '';
  const d = new Date(quando);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'America/Sao_Paulo',
  });
}

/** A peça nasceu de um teste do produto (SPEC-095 B.2: `tags @> {canario}`). */
export function ehPecaDeTeste(tags: unknown): boolean {
  return Array.isArray(tags) && tags.some((t) => String(t) === 'canario');
}

/** Campo de texto de um jsonb que chega como `unknown` do supabase-js. */
function leiaTexto(objeto: unknown, campo: string): string {
  if (!objeto || typeof objeto !== 'object' || Array.isArray(objeto)) return '';
  const valor = (objeto as Record<string, unknown>)[campo];
  return typeof valor === 'string' ? valor.trim() : '';
}
