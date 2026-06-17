// Fixtures SANITIZADAS para os goldens E2E de atendimento (42B7.2).
// Sem PII real: telefones são gerados em runtime; o CPF vem de E2E_CPF (env),
// nunca hardcoded. Estas fixtures descrevem sequências de mensagens e invariantes.

// Sequência residencial/eletricista por WhatsApp (CPF entra via placeholder).
export const WA_RESIDENTIAL_SEQUENCE = [
  'Oi',
  'estou sem luz',
  'só na cozinha',
  'não tem cheiro de queimado nem faísca',
  '<CPF>', // substituído por process.env.E2E_CPF em runtime
  'a primeira',
  'é na cozinha',
  'fico totalmente sem energia na cozinha',
  'sim, é o mesmo endereço da apólice',
];

// Ordem fora do padrão (resposta de risco tardia).
export const WA_OUT_OF_ORDER_SEQUENCE = ['estou sem luz', 'só na cozinha', 'não tem cheiro de queimado', '<CPF>'];

// Mensagens de triagem global (sem corredor pronto → triage).
export const WA_TRIAGE_MESSAGES = {
  claim: 'bati o carro e preciso de ajuda',
  policy_question: 'quero saber se minha apólice cobre eletricista',
  policy_consultation: 'quero consultar minha apólice',
  ambiguous: 'preciso de ajuda',
};

// Invariantes de segurança que NUNCA podem aparecer no output público.
export const FORBIDDEN_PATTERNS = [
  { name: 'token', re: /"token"\s*:|client_token|Client-Token/i },
  { name: 'raw_payload', re: /"audioUrl"|"imageUrl"|"connectedPhone"/i },
];

// Estados esperados (documentais) por cenário.
export const EXPECTED = {
  residential: {
    upgrade_corridor: 'allianz_residential_assistance',
    subcorridor: 'electrician',
    dispatch_before_hitl: 'hitl_required',
    verification_before_hitl: 'verified_by_connector',
    verification_after_hitl: 'verified_by_human',
    dispatch_after_hitl: 'ready_for_human_approval',
  },
  claim: { intent: 'claim', status: 'triage', corridor: null, subcorridor: null },
  outbound: { dry_run: true, sent: false },
};
