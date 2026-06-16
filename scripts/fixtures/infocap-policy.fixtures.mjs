// Fixtures SANITIZADAS para testes do Policy Evidence Pack (42I3A).
// Shapes baseados no /documento e /cliente_ligacoes reais da CorpAPI/InfoCap,
// SEM PII real: CPFs/nomes/números são fictícios. NUNCA usar dados reais aqui.

// 1. multiple_matches: 3 apólices do mesmo cliente (shape /cliente_ligacoes).
export const MULTIPLE_MATCHES_DOCS = [
  {
    nosnum: '97652',
    seguradora_abrev: 'ALLI',
    ramo_abrev: 'RESI',
    sit_acompanhamento_txt: 'Recebido e não entregue ao cliente',
    inivig: '01/01/2026',
    fimvig: '01/01/2027',
    cancelado: 'f',
    cliente: 'Fulano Teste',
    numapo: '0001234567',
  },
  {
    nosnum: '97572',
    seguradora_abrev: 'ALLI',
    ramo_abrev: 'RESI',
    sit_acompanhamento_txt: 'Vigente',
    inivig: '01/06/2024',
    fimvig: '01/06/2025', // vencida
    cancelado: 'f',
    cliente: 'Fulano Teste',
    numapo: '0007654321',
  },
  {
    nosnum: '93643',
    seguradora_abrev: 'ALLI',
    ramo_abrev: 'AUTO',
    sit_acompanhamento_txt: 'Cancelado',
    inivig: '01/03/2023',
    fimvig: '01/03/2024',
    cancelado: 't',
    cliente: 'Fulano Teste',
    numapo: '0009999999',
  },
];

// 2. policy_detail SEM coberturas/itens (existência confirmada, cobertura não).
export const DETAIL_NO_COVERAGE = {
  nosnum: '97652',
  seguradora_abrev: 'ALLI',
  ramo_abrev: 'RESI',
  sit_acompanhamento_txt: 'Vigente',
  inivig: '01/01/2026',
  fimvig: '01/01/2027',
  cancelado: 'f',
  cliente: 'Fulano Teste',
  numapo: '0001234567',
  cidade: 'São Paulo',
  estado: 'SP',
  itens: [],
};

// 3. policy_detail COM sinais de assistência residencial/elétrico.
export const DETAIL_WITH_SIGNALS = {
  nosnum: '97652',
  seguradora_abrev: 'ALLI',
  ramo_abrev: 'RESI',
  produto: 'Residencial',
  sit_acompanhamento_txt: 'Vigente',
  inivig: '01/01/2026',
  fimvig: '01/01/2027',
  cancelado: 'f',
  cliente: 'Fulano Teste',
  numapo: '0001234567',
  cidade: 'São Paulo',
  estado: 'SP',
  objeto: 'Imóvel residencial',
  itens: [
    { descricao: 'Assistência residencial 24 horas', valor: '0' },
    { descricao: 'Eletricista emergencial', valor: '500' },
    { descricao: 'Incêndio', is: '150000' },
  ],
};

// 4. policy_detail CANCELADA (não confirmar cobertura).
export const DETAIL_CANCELLED = {
  nosnum: '93643',
  seguradora_abrev: 'ALLI',
  ramo_abrev: 'RESI',
  produto: 'Residencial',
  sit_acompanhamento_txt: 'Cancelado',
  inivig: '01/03/2023',
  fimvig: '01/03/2024',
  cancelado: 't',
  cliente: 'Fulano Teste',
  numapo: '0009999999',
  itens: [{ descricao: 'Assistência residencial', valor: '0' }],
};
