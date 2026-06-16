#!/usr/bin/env node
/**
 * 42W1.1 — Global intent/corridor resolver (offline, sem rede, sem LLM).
 *
 *   node scripts/attendance-intent-resolver.test.mjs
 *
 * Garante: WhatsApp deixou de ser nichado em Allianz/Eletricista; fluxo
 * residencial/eletricista continua; outros intents viram triagem/candidato
 * quando não há corredor; sem hardcoding quando não inferido.
 */
import {
  classifyAttendanceIntent,
  resolveAttendanceIntentAndCorridor,
  buildAttendanceCaseFieldsFromResolvedIntent,
} from '../lib/attendance/attendance-intent-resolver.ts';

let pass = 0, fail = 0;
const failures = [];
function assert(name, cond, detail) {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; failures.push({ name, detail }); console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`); }
}

// Apenas o corredor residencial/eletricista existe hoje (como em produção).
const CORRIDORS = [
  {
    corridor_key: 'allianz_residential_assistance',
    subcorridor_key: 'electrician',
    insurer_key: 'allianz',
    line_kind: 'residential',
    macro_service: 'residential_assistance',
    service_type: 'electrician',
    display_name: 'Allianz Residencial / Eletricista',
    scope: 'global',
  },
];

console.log('== 42W1.1 — Global intent/corridor resolver ==');

// [1] Classificação de intenção.
console.log('\n[1] classificação');
{
  assert('sem luz → residential', classifyAttendanceIntent('estou sem luz na cozinha').bucket === 'residential_assistance');
  assert('disjuntor → residential', classifyAttendanceIntent('o disjuntor caiu').bucket === 'residential_assistance');
  assert('pneu → auto', classifyAttendanceIntent('meu carro furou o pneu').bucket === 'auto_assistance');
  assert('bati o carro → claim', classifyAttendanceIntent('bati o carro agora').bucket === 'claim');
  assert('cobertura → policy_question', classifyAttendanceIntent('tenho cobertura para eletricista?').bucket === 'policy_question');
  assert('consultar apólice → policy_consultation', classifyAttendanceIntent('quero consultar minha apólice').bucket === 'policy_consultation');
  assert('previsão prestador → followup', classifyAttendanceIntent('qual a previsão do prestador?').bucket === 'followup_existing_case');
  assert('boleto → billing', classifyAttendanceIntent('preciso do meu boleto').bucket === 'billing_document');
  assert('vago → unknown', classifyAttendanceIntent('preciso de ajuda').bucket === 'unknown');
}

// [2] Residencial mapeia para o corredor existente (fluxo preservado).
console.log('\n[2] residencial → corredor existente');
{
  const r = resolveAttendanceIntentAndCorridor({ text: 'estou sem luz só na cozinha', availableCorridors: CORRIDORS });
  assert('seleciona allianz_residential_assistance', r.selected_corridor_key === 'allianz_residential_assistance', r.selected_corridor_key);
  assert('subcorridor electrician', r.selected_subcorridor_key === 'electrician');
  assert('confidence high', r.confidence === 'high', r.confidence);
  assert('insurer do template', r.insurer_key === 'allianz');
  assert('line do template', r.line_kind === 'residential');
  assert('sem clarification', r.needs_clarification === false);
}

// [3] Auto/sinistro sem corredor → triagem (não vira residencial!).
console.log('\n[3] auto/sinistro sem corredor → triagem');
{
  const auto = resolveAttendanceIntentAndCorridor({ text: 'meu carro furou o pneu', availableCorridors: CORRIDORS });
  assert('auto → sem corredor (triagem)', auto.selected_corridor_key === null, auto.selected_corridor_key);
  assert('auto → needs_clarification', auto.needs_clarification === true);
  assert('auto NÃO vira residencial/allianz', auto.insurer_key === null && auto.line_kind === null);
  const claim = resolveAttendanceIntentAndCorridor({ text: 'bati o carro', availableCorridors: CORRIDORS });
  assert('sinistro → triagem', claim.selected_corridor_key === null && claim.intent === 'claim', claim.intent);
}

// [4] Sem corredor nenhum disponível → triagem.
console.log('\n[4] nenhum corredor disponível');
{
  const r = resolveAttendanceIntentAndCorridor({ text: 'estou sem luz', availableCorridors: [] });
  assert('sem template → triagem', r.selected_corridor_key === null);
  assert('needs_clarification', r.needs_clarification === true);
}

// [5] Fallback por env só se configurado E disponível.
console.log('\n[5] fallback por env');
{
  const r = resolveAttendanceIntentAndCorridor({
    text: 'preciso de ajuda', // unknown
    availableCorridors: CORRIDORS,
    defaultCorridorKey: 'allianz_residential_assistance',
    defaultSubcorridorKey: 'electrician',
  });
  assert('unknown + default disponível → usa default', r.selected_corridor_key === 'allianz_residential_assistance', r.selected_corridor_key);
  assert('confidence medium (default)', r.confidence === 'medium', r.confidence);
  const noDefault = resolveAttendanceIntentAndCorridor({ text: 'preciso de ajuda', availableCorridors: CORRIDORS });
  assert('unknown sem default → triagem', noDefault.selected_corridor_key === null);
  const badDefault = resolveAttendanceIntentAndCorridor({ text: 'preciso de ajuda', availableCorridors: CORRIDORS, defaultCorridorKey: 'inexistente' });
  assert('default inexistente → triagem (não inventa)', badDefault.selected_corridor_key === null);
}

// [6] followup não cria corredor (bridge busca case existente).
console.log('\n[6] followup');
{
  const r = resolveAttendanceIntentAndCorridor({ text: 'qual a previsão?', availableCorridors: CORRIDORS });
  assert('followup → sem corredor', r.selected_corridor_key === null && r.intent === 'followup_existing_case');
  assert('followup → não pede clarificação fria', r.needs_clarification === false);
}

// [7] Tenant corridor prioriza global.
console.log('\n[7] tenant prioriza global');
{
  const corridors = [
    ...CORRIDORS,
    { corridor_key: 'corretora_residencial', subcorridor_key: 'electrician', insurer_key: 'porto', line_kind: 'residential', macro_service: 'residential_assistance', scope: 'tenant' },
  ];
  const r = resolveAttendanceIntentAndCorridor({ text: 'estou sem luz', availableCorridors: corridors });
  assert('prioriza tenant', r.selected_corridor_key === 'corretora_residencial', r.selected_corridor_key);
  assert('insurer do tenant', r.insurer_key === 'porto');
}

// [8] Case fields builder.
console.log('\n[8] case fields builder');
{
  const matched = resolveAttendanceIntentAndCorridor({ text: 'sem luz', availableCorridors: CORRIDORS });
  const f = buildAttendanceCaseFieldsFromResolvedIntent(matched, { channel: 'whatsapp' });
  assert('com corredor → collecting_slots', f.status === 'collecting_slots');
  assert('com corredor → corridor key set', f.selected_corridor_key === 'allianz_residential_assistance');
  const triage = resolveAttendanceIntentAndCorridor({ text: 'meu carro furou o pneu', availableCorridors: CORRIDORS });
  const tf = buildAttendanceCaseFieldsFromResolvedIntent(triage, { channel: 'whatsapp' });
  assert('triagem → status triage', tf.status === 'triage', tf.status);
  assert('triagem → corridor null', tf.selected_corridor_key === null);
  assert('triagem → next_step é a pergunta', typeof tf.next_step === 'string' && tf.next_step.length > 0);
  assert('triagem → sem insurer hardcoded', tf.insurer_key === null);
}

// [9] 42W1.2 P1: família (subcorridor null) + eletricista → escolhe eletricista.
console.log('\n[9] prefere subcorredor operacional (não família null)');
{
  const withFamily = [
    { corridor_key: 'allianz_residential_assistance', subcorridor_key: null, insurer_key: 'allianz', line_kind: 'residential', macro_service: 'residential_assistance', service_type: null, scope: 'global' },
    { corridor_key: 'allianz_residential_assistance', subcorridor_key: 'electrician', insurer_key: 'allianz', line_kind: 'residential', macro_service: 'residential_assistance', service_type: 'electrician', scope: 'global' },
  ];
  const r = resolveAttendanceIntentAndCorridor({ text: 'estou sem luz só na cozinha', availableCorridors: withFamily });
  assert('escolhe subcorridor electrician (não null)', r.selected_subcorridor_key === 'electrician', String(r.selected_subcorridor_key));
  assert('corridor key correto', r.selected_corridor_key === 'allianz_residential_assistance');
  const f = buildAttendanceCaseFieldsFromResolvedIntent(r, { channel: 'whatsapp' });
  assert('case fields subcorridor electrician', f.selected_subcorridor_key === 'electrician');
  // ordem invertida no array não muda o resultado
  const r2 = resolveAttendanceIntentAndCorridor({ text: 'disjuntor caiu', availableCorridors: [withFamily[1], withFamily[0]] });
  assert('ordem do array não afeta (electrician)', r2.selected_subcorridor_key === 'electrician', String(r2.selected_subcorridor_key));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`); process.exit(1); }
process.exit(0);
