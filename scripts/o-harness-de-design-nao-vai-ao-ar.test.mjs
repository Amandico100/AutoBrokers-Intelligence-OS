// SPEC-139 (red team P1 / confirmação C5): o harness de design `app/embed/loja/**` é TEMPORÁRIO — ele é público, troca o
// `fetch` da página por um dublê e responde `ok` a todo POST sem gravar. Ele NUNCA pode ir ao ar.
// Este guarda fica VERMELHO se a pasta voltar (rode: node --test scripts/o-harness-de-design-nao-vai-ao-ar.test.mjs).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const RAIZ = process.env.HARNESS_RAIZ || process.cwd();

test('o harness de design da loja não existe na árvore entregue', () => {
  assert.equal(existsSync(join(RAIZ, 'app', 'embed', 'loja')), false, 'app/embed/loja voltou: apague antes da entrega');
});

test('nenhuma pasta de harness sob app/embed além do embed real do agente ([agentId])', () => {
  const embed = join(RAIZ, 'app', 'embed');
  const pastas = existsSync(embed)
    ? readdirSync(embed, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name)
    : [];
  assert.deepEqual(pastas.filter((p) => p !== '[agentId]'), [], `pasta inesperada em app/embed: ${pastas.join(', ')}`);
});
