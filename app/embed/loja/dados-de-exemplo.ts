// modelo: claude-opus-5-5
//
// ⚠️ HARNESS TEMPORÁRIO DE CAPTURA — SPEC-139 · L6 (como o da SPEC-131-B: apagado ao fim da SPEC).
//
// DADOS DE EXEMPLO. Nada aqui vem do banco nem da sessão, e nada aqui é de uma corretora real: nomes de segurado,
// números e textos são inventados para o juiz de design ver as telas montadas. Os números marcados "exemplo" NÃO são
// prova de nada (D-131-26) — existem só para a tela ter o que desenhar.

import {
  APLICATIVO_VISUAL,
  VISUAL_PADRAO,
  type FontesDoComoComecar,
  type ItemDoCatalogo,
  type EstadoDoCard,
} from '@/lib/auxiliaries/catalog';

const NOMES: Record<string, string> = {
  'caca-comissao': 'Caça-Comissão', 'carteira-blindada': 'Carteira Blindada', 'checklist-6h': 'Checklist das 6h',
  'clientes-perdidos': 'Clientes Perdidos', 'cobranca-feita': 'Cobrança Feita', 'contabilidade-pronta': 'Contabilidade Pronta',
  cotacao: 'Cotação Rápida', 'digitacao-zero': 'Digitação Zero', 'follow-up-whatsapp': 'Follow-up do WhatsApp',
  'organizacao-completa': 'Organização Completa', 'protecao-completa': 'Proteção Completa', 'quem-cobra-menos': 'Quem Cobra Menos',
  'radar-mercado-regulacao': 'Radar de Mercado', renovacao: 'Renovação Automática', 'resgatar-cliente': 'Resgatar Cliente',
  'resumo-atendimentos': 'Resumo de Atendimentos', 'sinistralidade-avancada': 'Sinistralidade Avançada', 'tarefas-agendadas': 'Tarefas Agendadas',
};

const FRASES: Record<string, string> = {
  renovacao: 'As renovações amanhecem calculadas, prontas para você conferir.',
  'cobranca-feita': 'Lembra o segurado da parcela em aberto pelo WhatsApp, no tom da sua corretora.',
  'checklist-6h': 'Às 6h, o que pede você hoje — e o que já foi resolvido.',
  'follow-up-whatsapp': 'Um rascunho de retorno para o atendimento que ficou sem resposta.',
  'resumo-atendimentos': 'O resumo de uma conversa longa: o que foi pedido, o que ficou pendente.',
  cotacao: 'Cotação de auto em minutos, no Agger da sua corretora.',
  'quem-cobra-menos': 'Compara as seguradoras e mostra quem cobra menos para o mesmo risco.',
  'radar-mercado-regulacao': 'Avisa quando uma norma do setor muda de verdade.',
  'tarefas-agendadas': 'Um lembrete que roda sozinho, no horário que você escolher.',
};

/** Os estados de exemplo da galeria: 9 disponíveis (alguns ligados) e 9 "Em breve" — como o catálogo de hoje. */
const ESTADOS: Record<string, EstadoDoCard> = {
  renovacao: 'ligado', 'checklist-6h': 'ligado', 'cobranca-feita': 'pausado', 'radar-mercado-regulacao': 'falta_conectar',
  cotacao: 'disponivel', 'quem-cobra-menos': 'disponivel', 'follow-up-whatsapp': 'disponivel', 'resumo-atendimentos': 'disponivel',
  'tarefas-agendadas': 'disponivel',
};

export const SLUGS_DE_EXEMPLO = Object.keys(NOMES).sort();

const DUVIDAS = [
  { pergunta: 'Exemplo: ele manda alguma coisa sem eu ver?', resposta: 'Exemplo de resposta: nada sai sem a regra que você escolheu.' },
  { pergunta: 'Exemplo: posso desligar quando quiser?', resposta: 'Exemplo de resposta: sim, e desligar não apaga nada.' },
];

export function itemDeExemplo(slug: string, extra: Partial<ItemDoCatalogo> = {}): ItemDoCatalogo {
  const v = APLICATIVO_VISUAL[slug] ?? VISUAL_PADRAO;
  const estado = ESTADOS[slug] ?? 'em_breve';
  const emBreve = estado === 'em_breve';
  const instalado = estado === 'ligado' || estado === 'pausado';
  return {
    template_id: `exemplo-${slug}`,
    slug,
    nome: NOMES[slug] ?? slug,
    headline: FRASES[slug] ?? 'Exemplo: o que este aplicativo vai fazer pela corretora.',
    categorias: [],
    estado_catalogo: emBreve ? 'coming_soon' : 'available',
    estado,
    o_que_faz: [
      { tarefa: 'Exemplo: lê o que chegou desde ontem', frequencia: 'todo dia, de madrugada' },
      { tarefa: 'Exemplo: separa o que pede você', frequencia: 'a cada execução' },
    ],
    promessa: 'Exemplo: o tempo que hoje vai em planilha volta para o atendimento.',
    fontes: ['Exemplo: o sistema de gestão da corretora'],
    falta_para_existir: emBreve ? 'Exemplo: falta a conexão com o sistema de gestão.' : null,
    descricao: 'Exemplo de descrição — texto de amostra do harness de captura, não do catálogo.',
    resumo: null,
    conectores_pendentes: estado === 'falta_conectar'
      ? [{ slug: 'insurance_portal', nome: 'Portal da Seguradora', onde: '/dashboard/personalizacao/conectores/portais' }]
      : [],
    conectores_prontos: [],
    instalado,
    install_id: instalado ? `exemplo-instalacao-${slug}` : null,
    ultima_execucao: null,
    rotinas: slug === 'cobranca-feita' && instalado ? 1 : 0,
    tela_de_execucao: null,
    icone: v.icone,
    matiz: v.matiz,
    cover_url: null,
    faq: DUVIDAS,
    destaque: slug === 'renovacao' ? 1 : null,
    conexoes: slug === 'cobranca-feita'
      ? [
          { slug: 'insurance_portal', nome: 'Portal da Seguradora', pronto: true, onde: '/dashboard/personalizacao/conectores/portais' },
          { slug: 'whatsapp_zapi', nome: 'WhatsApp', pronto: false, onde: '/dashboard/personalizacao/corretora/whatsapp' },
        ]
      : [],
    prova: { execucoes: 0, ultima_execucao: null, renovacoes_no_mes: null },
    sem_rotina: slug === 'cotacao' || slug === 'quem-cobra-menos',
    ...extra,
  };
}

/** A Cobrança nos três estados que o juiz captura: não instalada · instalada (Configurar) · instalada (Cobranças). */
export function cobrancaDeExemplo(estado: string | null): ItemDoCatalogo {
  if (estado === 'nao-instalada') {
    return itemDeExemplo('cobranca-feita', { estado: 'disponivel', instalado: false, install_id: null, rotinas: 0 });
  }
  return itemDeExemplo('cobranca-feita');
}

export const FONTES_DE_EXEMPLO: FontesDoComoComecar = {
  prontidao: [
    { chave: 'sistema_de_gestao', estado: 'pronto', detalhe: 'Exemplo: conectado.' },
    { chave: 'agger_da_corretora', estado: 'pronto', detalhe: 'Exemplo: conectado.' },
    { chave: 'equipe', estado: 'em_parte', detalhe: 'Exemplo: 1 de 2 comerciais com Agger.' },
    { chave: 'servicos', estado: 'falta', detalhe: 'Exemplo: regras ainda não escolhidas.' },
  ],
  meuAgger: true,
};

// ── as respostas da API de exemplo (o dublê de `fetch` do harness) ──────────────────────────────────────────────────

const agora = () => Date.now();
const iso = (horasAtras: number) => new Date(agora() - horasAtras * 3_600_000).toISOString();

export function respostaDeExemplo(caminho: string, busca: URLSearchParams, metodo: string, telaBusca: URLSearchParams): unknown | null {
  if (metodo !== 'GET') return { ok: true, exemplo: true };
  const estadoCob = telaBusca.get('estado');
  switch (caminho) {
    case '/api/dashboard/auxiliaries':
      return { ok: true, itens: SLUGS_DE_EXEMPLO.map((s) => itemDeExemplo(s)) };
    case '/api/dashboard/rotinas': {
      if (busca.get('auxiliar') !== 'cobranca-feita' || estadoCob === 'nao-instalada') return { routines: [], runs: [] };
      return {
        routines: [{
          id: 'exemplo-rotina', name: 'Cobrança', instructions: 'Exemplo: varre os portais e lembra o segurado da parcela.',
          knowledge: null, schedule: { kind: 'daily', time: '09:30', weekdays: [1, 2, 3, 4, 5] },
          delivery: { channel: 'whatsapp', number: '55 00 00000-0000' },
          config: { kind: 'billing_collection', send_mode: 'test', portal_keys: ['allianz_corretor'], attendant_name: 'Atendente Exemplo', max_boletos_por_execucao: 10 },
          is_active: true, last_run_at: iso(20), next_run_at: iso(-4), consecutive_failures: 0,
        }],
        runs: [
          { id: 'exemplo-run-1', routine_id: 'exemplo-rotina', started_at: iso(20), status: 'ok' },
          { id: 'exemplo-run-2', routine_id: 'exemplo-rotina', started_at: iso(44), status: 'ok' },
        ],
      };
    }
    case '/api/dashboard/portal-credentials':
      return {
        portals: [
          { key: 'allianz_corretor', name: 'Allianz', category: 'corretor' },
          { key: 'mapfre_corretor', name: 'Mapfre', category: 'corretor' },
        ],
        credentials: [{ portal_key: 'allianz_corretor', has_password: true }],
        cobranca: { operacional: ['allianz_corretor'] },
      };
    case '/api/dashboard/routine-templates':
      return { templates: [] };
    case '/api/dashboard/auxiliaries/cobranca/enviadas':
      return {
        ok: true, periodo: Number(busca.get('periodo') || 30), limite: 200,
        itens: [
          { id: 'ex1', quando: iso(2), segurado: 'Segurado E. (exemplo)', seguradora: 'Allianz', recibo: '000101', situacao: 'Enviada', tom: 'success', teste: false, destino: 'segurado', para_final: '0000' },
          { id: 'ex2', quando: iso(3), segurado: 'Segurada X. (exemplo)', seguradora: 'Allianz', recibo: '000102', situacao: 'Enviada', tom: 'success', teste: true, destino: 'teste', para_final: '0001' },
          { id: 'ex3', quando: iso(27), segurado: 'Segurado M. (exemplo)', seguradora: 'Mapfre', recibo: '000103', situacao: 'Com a equipe, falta encaminhar', tom: 'warning', teste: false, destino: 'equipe', para_final: '0002' },
        ],
      };
    case '/api/dashboard/auxiliaries/cobranca/pendencias':
      return {
        ok: true,
        itens: [{
          id: 'exp1', status: 'entregue_equipe', modalidade: 'equipe', portal_key: 'allianz_corretor', recibo: '0001',
          cliente_nome: 'Segurado Exemplo', apolice_susep: null, to_last4: '0000', sent_at: iso(5), updated_at: iso(5),
          retorno_do_cliente: null, retorno_em: null, encaminhado_ao_cliente_em: null, motivo: null,
        }],
      };
    case '/api/dashboard/briefing':
      return {
        ok: true,
        briefing: { briefing: {
          id: 'exemplo-briefing', headline: 'Exemplo: 2 coisas pedem você hoje', summary_text: 'Exemplo de resumo do dia.',
          published_at: iso(1), item_count: 2, critical_count: 1, briefing_type: 'hoje',
          payload: { headline: 'Exemplo: 2 coisas pedem você hoje', executive_summary: 'Exemplo de resumo executivo.', sections: [] },
        } },
        findings: { findings: [
          { id: 'exf1', title: 'Exemplo: parcela vencendo amanhã sem lembrete', summary: 'Exemplo de achado.', priority_score: 88, severity: 'alta', why_now: 'Exemplo: vence amanhã.' },
          { id: 'exf2', title: 'Exemplo: renovação sem cálculo há 3 dias', summary: 'Exemplo de achado.', priority_score: 60, severity: 'media', why_now: 'Exemplo.' },
        ] },
        recomendacoes: { recomendacoes: [] },
      };
    case '/api/auxiliaries/resumo-atendimentos/conversations':
      return { conversations: [
        { id: 'exc1', title: 'Exemplo — dúvida sobre a parcela', last_message_preview: 'Exemplo de última mensagem.', message_count: 8, updated_at: iso(6) },
        { id: 'exc2', title: 'Exemplo — pedido de 2ª via', last_message_preview: 'Exemplo de última mensagem.', message_count: 4, updated_at: iso(30) },
      ] };
    case '/api/vault/templates':
      return { templates: [] };
    case '/api/vault/connections':
      return { connections: [] };
    default:
      return null;
  }
}
