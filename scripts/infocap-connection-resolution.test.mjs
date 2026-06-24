#!/usr/bin/env node
/**
 * R1A.1 - InfoCap contract-probe connection resolution (offline).
 *
 * Estes testes cobrem apenas a selecao segura de tenant_connections para o
 * Contract Capture Gate. Nunca usam Supabase, Vault, rede, provider real ou PII.
 */
import {
  resolveInfocapContractProbeConnection,
  sanitizeConnectionResolutionForOutput,
} from '../lib/attendance/connectors/infocap-connection-resolution.ts';

let pass = 0;
let fail = 0;
const failures = [];

function assert(name, condition, detail) {
  if (condition) {
    pass += 1;
    console.log(`  [ok] ${name}`);
  } else {
    fail += 1;
    failures.push({ name, detail });
    console.log(`  [X] ${name}${detail ? ` - ${detail}` : ''}`);
  }
}

const baseConfig = { base_url: 'https://infocap.example.test' };

function conn(overrides = {}) {
  return {
    id: Object.hasOwn(overrides, 'id') ? overrides.id : 'conn-valid',
    company_id: Object.hasOwn(overrides, 'company_id') ? overrides.company_id : 'company-1',
    connector_template_id: Object.hasOwn(overrides, 'connector_template_id') ? overrides.connector_template_id : 'tpl-infocap',
    status: Object.hasOwn(overrides, 'status') ? overrides.status : 'connected',
    health_status: Object.hasOwn(overrides, 'health_status') ? overrides.health_status : 'healthy',
    encrypted_secret_ref: Object.hasOwn(overrides, 'encrypted_secret_ref') ? overrides.encrypted_secret_ref : 'vault-ciphertext',
    connection_config: Object.hasOwn(overrides, 'connection_config') ? overrides.connection_config : baseConfig,
    metadata: Object.hasOwn(overrides, 'metadata') ? overrides.metadata : {},
    created_at: Object.hasOwn(overrides, 'created_at') ? overrides.created_at : '2026-06-24T12:00:00.000Z',
  };
}

function resolve(connections, env = {}) {
  return resolveInfocapContractProbeConnection(connections, {
    companyId: 'company-1',
    connectorTemplateId: 'tpl-infocap',
    providerDefaultBaseUrl: env.providerDefaultBaseUrl ?? '',
  });
}

function publicJson(resolution) {
  return JSON.stringify(sanitizeConnectionResolutionForOutput(resolution));
}

console.log('== R1A.1 - InfoCap connection resolution ==\n');

{
  const result = resolve([
    conn({ id: 'new-missing-secret', encrypted_secret_ref: '', created_at: '2026-06-24T13:00:00.000Z' }),
    conn({ id: 'older-valid', created_at: '2026-06-24T12:00:00.000Z' }),
  ]);
  assert('mais recente sem segredo: escolhe a anterior valida', result.selectedConnectionId === 'older-valid', result.selectedConnectionId);
  assert('mais recente sem segredo: status pronto', result.selectionStatus === 'connection_usable', result.selectionStatus);
  assert('conta total de conexoes', result.summary.total_infocap_connections === 2, result.summary.total_infocap_connections);
  assert('conta secrets presentes', result.summary.vault_secret_present_count === 1, result.summary.vault_secret_present_count);
}

{
  const result = resolve([
    conn({ id: 'new-archived', status: 'archived', created_at: '2026-06-24T13:00:00.000Z' }),
    conn({ id: 'older-valid', created_at: '2026-06-24T12:00:00.000Z' }),
  ]);
  assert('mais recente arquivada: escolhe a anterior valida', result.selectedConnectionId === 'older-valid', result.selectedConnectionId);
  assert('conta inativas/arquivadas', result.summary.inactive_connection_count === 1, result.summary.inactive_connection_count);
}

{
  const result = resolve([
    conn({ id: 'a', encrypted_secret_ref: '' }),
    conn({ id: 'b', encrypted_secret_ref: null }),
  ]);
  assert('sem segredo: nenhuma conexao elegivel', result.selectedConnectionId === null, result.selectedConnectionId);
  assert('sem segredo: reconnect_required', result.selectionStatus === 'reconnect_required', result.selectionStatus);
  assert('sem segredo: status externo blocked_missing_credentials', result.responseStatus === 'blocked_missing_credentials', result.responseStatus);
}

{
  const result = resolve([
    conn({ id: 'valid-a', created_at: '2026-06-24T13:00:00.000Z' }),
    conn({ id: 'valid-b', created_at: '2026-06-24T12:00:00.000Z' }),
  ]);
  assert('duas validas: nenhuma escolha silenciosa', result.selectedConnectionId === null, result.selectedConnectionId);
  assert('duas validas: ambiguous_connection', result.responseStatus === 'ambiguous_connection', result.responseStatus);
  assert('duas validas: limpeza manual requerida', result.selectionStatus === 'manual_connection_cleanup_required', result.selectionStatus);
}

{
  const result = resolve([
    conn({
      id: 'leaky-id',
      encrypted_secret_ref: 'secret-ciphertext',
      connection_config: { base_url: 'https://private.example.test', token: 'token-secret' },
      metadata: { cpf: '04760897941', nome: 'Pessoa Teste', policy: '99599', nosnum: 'N1', codigo: 'C1', codfil: '1' },
    }),
  ]);
  const raw = publicJson(result);
  assert('saida publica nao contem encrypted_secret_ref', !raw.includes('encrypted_secret_ref') && !raw.includes('secret-ciphertext'), raw);
  assert('saida publica nao contem connection id', !raw.includes('leaky-id'), raw);
  assert('saida publica nao contem valor de base URL', !raw.includes('private.example'), raw);
  assert('saida publica nao contem CPF', !raw.includes('04760897941'), raw);
  assert('saida publica nao contem nome', !raw.includes('Pessoa Teste'), raw);
  assert('saida publica nao contem apolice', !raw.includes('99599'), raw);
  assert('saida publica nao contem nosnum/codigo/codfil', !raw.includes('N1') && !raw.includes('C1') && !raw.includes('"codfil"'), raw);
  assert('saida publica nao contem token/senha', !raw.includes('token-secret') && !raw.includes('senha'), raw);
  assert('saida publica contem apenas resumo de selecao', raw.includes('eligible_connection_count') && raw.includes('selection_status'), raw);
}

{
  const result = resolve([
    conn({ id: 'wrong-company', company_id: 'company-2' }),
    conn({ id: 'wrong-template', connector_template_id: 'tpl-other' }),
    conn({ id: 'right-one' }),
  ]);
  assert('escopo empresa/template: ignora conexoes fora do escopo', result.selectedConnectionId === 'right-one', result.selectedConnectionId);
}

{
  const result = resolve([
    conn({ id: 'with-provider-default', connection_config: {} }),
  ], { providerDefaultBaseUrl: 'https://default.example.test' });
  assert('base_url efetiva pode vir do default do provider', result.selectedConnectionId === 'with-provider-default', result.selectedConnectionId);
  assert('conta base_url configurada por default', result.summary.base_url_configured_count === 1, result.summary.base_url_configured_count);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f.name}${f.detail ? `: ${f.detail}` : ''}`);
  process.exit(1);
}
process.exit(0);
