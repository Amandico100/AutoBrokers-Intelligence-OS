#!/usr/bin/env node
/**
 * O GUARDA DA AUTORIZAÇÃO DE ENVIO — SPEC-078 Bloco B.
 *
 * O PROBLEMA QUE ESTE TESTE EXISTE PARA CONGELAR
 * ==============================================
 * 📊 Medido em 17/08/2026: o dashboard pareia o WhatsApp da corretora com
 * `purpose='observer'` (`app/api/dashboard/whatsapp-channel/route.ts`), e
 * `observer` está em `IntegrationService.PROPOSITOS_QUE_NUNCA_ENVIAM`. O número
 * que a corretora pareou **não conseguia enviar o boleto** — era essa a causa
 * de o Auxiliar de Cobrança nunca ter fechado o ciclo.
 *
 * A correção NÃO foi afrouxar a proibição (isso é desfazer a SPEC-063 D, cuja
 * razão está escrita em `integration_service.py:176-192`). Foi separar duas
 * coisas que estavam coladas:
 *
 *     envio de PLATAFORMA   o produto falando por conta própria      proibido
 *     envio de AUXILIAR     trabalho que a corretora instalou e ligou  se autorizar
 *
 * O PAR QUE PROVA, e por que ele tem que estar no MESMO teste
 * ===========================================================
 * Provar só que o `auxiliar` autorizado envia seria provar meia coisa: um
 * `pode_enviar` que devolvesse `True` para tudo passaria nesse teste. O que dá
 * direito à conclusão é a linha de CONTROLE (CLAUDE.md §9.2):
 *
 *   1. observer SEM autorização  -> proibido nos DOIS regimes
 *   2. observer COM autorização  -> proibido em plataforma, permitido em auxiliar
 *   3. attendance / auxiliary    -> permitidos nos dois
 *   4. 🔴 CONTROLE: chamador que NÃO passa `para=` continua com o comportamento
 *      antigo, byte a byte. É a asserção mais importante do arquivo: se a
 *      assinatura nova afrouxar por omissão, os ~dez chamadores que ninguém
 *      editou passam a poder enviar pelo número que deve ficar calado.
 *
 * COMO ELE LÊ O PYTHON
 * ====================
 * Não reescrevendo a regra em JavaScript — uma cópia da regra não guarda a
 * regra. O harness abaixo faz `ast.parse` no arquivo REAL, recorta a classe
 * `IntegrationService` deixando só as constantes e `pode_enviar`, e **executa
 * esses bytes**. Recorta porque importar o módulo inteiro puxa
 * `app.services.__init__` -> `openai`, que não está instalado (📊 verificado
 * em 17/08/2026 nesta máquina).
 *
 * O mesmo vale para `billing_collection._find_whatsapp_integration`: ele roda
 * de verdade, contra um cliente Supabase de mentira, e é assim que a ordem de
 * preferência (`auxiliary` na frente de `attendance`) é provada.
 *
 * ⚠ Não roda no CI: 📊 `.github/workflows/gate.yml` não executa `.mjs`. Rode
 * `npm run test:canal-auxiliary` antes de mexer em canal de saída.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

const PY_INTEGRATION = 'backend/app/services/integration_service.py';
const PY_BILLING = 'backend/app/services/billing_collection.py';
const SQL_MIGRATION = 'backend/supabase/migrations/20260817_02_spec078_canal_auxiliary.sql';
const TS_ROTA = 'app/api/dashboard/whatsapp-channel/route.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c, detalhe) {
  if (c) { pass++; console.log(`  ok   ${n}`); return; }
  fail++; failures.push(n);
  console.log(`  X    ${n}${detalhe ? `\n         ${detalhe}` : ''}`);
}

// ---------------------------------------------------------------------------
// O harness Python. Ele não decide nada — só executa o código real e imprime
// o que aconteceu. Toda asserção vive do lado do JavaScript, à vista.
// ---------------------------------------------------------------------------
const HARNESS = String.raw`
import ast, json, sys, types

RAIZ = sys.argv[1]

def fonte(rel):
    with open(RAIZ + "/" + rel, encoding="utf-8") as f:
        return f.read()

saida = {"erros": []}

# --- 1. A classe real, recortada: constantes + pode_enviar ------------------
# Duas arvores do MESMO arquivo, de proposito: o recorte abaixo MUTILA a que
# usa (apaga os metodos que nao interessam para poder executar a classe sem
# importar o modulo inteiro). A intacta e a que a inspecao do bloco 3 le --
# a primeira versao deste teste reusou a mutilada e concluiu que
# get_platform_whatsapp_integration "nao existia".
_fonte_int = fonte("backend/app/services/integration_service.py")
arvore_int = ast.parse(_fonte_int)
arvore_int_intacta = ast.parse(_fonte_int)
classe = next((n for n in arvore_int.body
               if isinstance(n, ast.ClassDef) and n.name == "IntegrationService"), None)
if classe is None:
    saida["erros"].append("classe IntegrationService nao encontrada")
    print(json.dumps(saida)); sys.exit(0)

mantidos = [n for n in classe.body
            if isinstance(n, ast.Assign)
            or (isinstance(n, ast.FunctionDef) and n.name == "pode_enviar")]
tem_pode_enviar = any(isinstance(n, ast.FunctionDef) for n in mantidos)
classe.body = mantidos or [ast.Pass()]
modulo = ast.Module(body=[classe], type_ignores=[])
ast.fix_missing_locations(modulo)
ns = {}
exec(compile(modulo, "<integration_service recortado>", "exec"), ns)
I = ns["IntegrationService"]

saida["extracao"] = {
    "pode_enviar_encontrado": tem_pode_enviar,
    "proibidos": sorted(getattr(I, "PROPOSITOS_QUE_NUNCA_ENVIAM", [])),
    "coluna": getattr(I, "COLUNA_AUTORIZACAO_AUXILIAR", None),
    "aceita_para": "para" in getattr(I.pode_enviar, "__wrapped__", I.pode_enviar).__code__.co_varnames
                   if tem_pode_enviar else False,
}

COL = getattr(I, "COLUNA_AUTORIZACAO_AUXILIAR", "permite_envio_de_auxiliar")

def linha(purpose, autorizado=None):
    r = {"id": purpose, "purpose": purpose, "provider": "evolution-go",
         "company_id": "c1", "is_active": True}
    if autorizado is not None:
        r[COL] = autorizado
    return r

casos = {
    "observer_sem_coluna":      linha("observer"),
    "observer_negado":          linha("observer", False),
    "observer_autorizado":      linha("observer", True),
    "observer_autorizado_str":  linha("observer", "true"),
    "observer_autorizado_um":   linha("observer", 1),
    "attendance":               linha("attendance"),
    "auxiliary":                linha("auxiliary"),
    "OBSERVER_maiusculo":       linha("  OBSERVER "),
}
saida["matriz"] = {}
for nome, reg in casos.items():
    saida["matriz"][nome] = {
        "omisso":     I.pode_enviar(reg),
        "plataforma": I.pode_enviar(reg, para="plataforma"),
        "auxiliar":   I.pode_enviar(reg, para="auxiliar"),
        "desconhecido": I.pode_enviar(reg, para="qualquer-coisa"),
    }
saida["matriz"]["nada"] = {
    "omisso": I.pode_enviar(None), "plataforma": I.pode_enviar(None, para="plataforma"),
    "auxiliar": I.pode_enviar(None, para="auxiliar"), "desconhecido": I.pode_enviar(None, para="x"),
}

# --- 2. O seletor REAL da cobranca, contra um Supabase de mentira ----------
falso = types.ModuleType("app.services.integration_service")
falso.IntegrationService = I
sys.modules.setdefault("app", types.ModuleType("app"))
sys.modules.setdefault("app.services", types.ModuleType("app.services"))
sys.modules["app.services.integration_service"] = falso

arvore_bil = ast.parse(fonte("backend/app/services/billing_collection.py"))
fn = next((n for n in arvore_bil.body
           if isinstance(n, ast.FunctionDef) and n.name == "_find_whatsapp_integration"), None)
saida["extracao"]["find_encontrado"] = fn is not None
if fn is not None:
    mod2 = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(mod2)
    from typing import Any, Dict, Optional
    ns2 = {"Any": Any, "Dict": Dict, "Optional": Optional}
    exec(compile(mod2, "<billing_collection recortado>", "exec"), ns2)
    achar = ns2["_find_whatsapp_integration"]

    class _Q:
        def __init__(self, linhas): self._l = linhas
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def execute(self): return types.SimpleNamespace(data=self._l)

    class _C:
        def __init__(self, linhas): self._l = linhas
        def table(self, _n): return _Q(self._l)

    cenarios = {
        "so_observer_sem_autorizacao": [linha("observer", False)],
        "so_observer_autorizado":      [linha("observer", True)],
        "observer_autorizado_e_attendance": [linha("observer", True), linha("attendance")],
        "attendance_e_auxiliary":      [linha("attendance"), linha("auxiliary")],
        "auxiliary_depois_de_observer": [linha("observer", True), linha("auxiliary")],
        "vazio": [],
    }
    saida["cobranca"] = {}
    for nome, linhas in cenarios.items():
        escolhida = achar(_C(linhas), "c1")
        saida["cobranca"][nome] = None if escolhida is None else escolhida.get("purpose")

# --- 3. Quem PEDE o regime de auxiliar, e quem nao pede --------------------
def kw_para(no):
    """O valor textual do keyword 'para=' em cada chamada a pode_enviar."""
    achados = []
    for sub in ast.walk(no):
        if not isinstance(sub, ast.Call):
            continue
        alvo = sub.func
        nome = alvo.attr if isinstance(alvo, ast.Attribute) else getattr(alvo, "id", "")
        if nome != "pode_enviar":
            continue
        valor = None
        for kw in sub.keywords:
            if kw.arg != "para":
                continue
            if isinstance(kw.value, ast.Constant):
                valor = kw.value.value
            elif isinstance(kw.value, ast.Attribute):
                valor = kw.value.attr
        achados.append(valor)
    return achados

def chamadas_em(arvore, nome_fn):
    for n in ast.walk(arvore):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nome_fn:
            return kw_para(n)
    return None

saida["chamadores"] = {
    "billing._find_whatsapp_integration": chamadas_em(arvore_bil, "_find_whatsapp_integration"),
    "get_platform_whatsapp_integration": chamadas_em(arvore_int_intacta, "get_platform_whatsapp_integration"),
}

print(json.dumps(saida))
`;

function rodarPython() {
  for (const exe of ['python', 'py', 'python3']) {
    const r = spawnSync(exe, ['-', RAIZ], { input: HARNESS, encoding: 'utf8' });
    if (r.error) continue;
    if (r.status !== 0) {
      console.log(`\nO harness Python (${exe}) falhou:\n${r.stderr || r.stdout}`);
      process.exit(1);
    }
    try {
      return JSON.parse(r.stdout.trim().split('\n').pop());
    } catch {
      console.log(`\nSaída do harness não é JSON:\n${r.stdout}\n${r.stderr}`);
      process.exit(1);
    }
  }
  console.log('\nNenhum interpretador Python encontrado (python/py/python3).');
  process.exit(1);
}

console.log('== O número pareado pode enviar pelos Auxiliares — sem contaminar o atendimento ==\n');

const R = rodarPython();

// ---------------------------------------------------------------------------
// Um guarda que passa quando não conseguiu ler a fonte não guarda nada.
// ---------------------------------------------------------------------------
console.log('-- a fonte foi mesmo lida e executada --');
assert('harness rodou sem erro declarado', (R.erros || []).length === 0, (R.erros || []).join(' · '));
if (fail > 0) { console.log('\nSem fonte não há o que provar.'); process.exit(1); }
assert(`${PY_INTEGRATION}: pode_enviar foi recortado e executado`, R.extracao.pode_enviar_encontrado);
assert(`${PY_INTEGRATION}: 'observer' continua na lista de proibidos`,
  R.extracao.proibidos.includes('observer'), `proibidos: ${R.extracao.proibidos.join(', ') || '(vazio)'}`);
assert(`${PY_INTEGRATION}: pode_enviar aceita o parâmetro 'para'`, R.extracao.aceita_para === true);
assert(`${PY_INTEGRATION}: a coluna de autorização tem nome declarado`,
  R.extracao.coluna === 'permite_envio_de_auxiliar', `COLUNA_AUTORIZACAO_AUXILIAR = ${R.extracao.coluna}`);
assert(`${PY_BILLING}: _find_whatsapp_integration foi recortado e executado`, R.extracao.find_encontrado);
if (fail > 0) { console.log('\nO recorte falhou — corrija o parser ou a declaração.'); process.exit(1); }

const M = R.matriz;

console.log('\n-- 1. o observador SEM autorização: proibido nos dois regimes --');
for (const caso of ['observer_sem_coluna', 'observer_negado']) {
  assert(`${caso}: proibido como canal de plataforma`, M[caso].plataforma === false);
  assert(`${caso}: proibido como canal de Auxiliar`, M[caso].auxiliar === false);
  assert(`${caso}: proibido por omissão (chamador antigo)`, M[caso].omisso === false);
}

console.log('\n-- 2. o observador COM autorização: o par que separa os dois usos --');
// As duas metades juntas. Só a de baixo seria "afrouxou tudo"; só a de cima
// seria "não consertou nada". É a diferença entre elas que é a SPEC-078 B.
assert('observer_autorizado: CONTINUA proibido como canal de plataforma',
  M.observer_autorizado.plataforma === false,
  'alerta do Vigia e follow-up voltariam a sair pelo número que deve calar');
assert('observer_autorizado: PERMITIDO como canal de Auxiliar',
  M.observer_autorizado.auxiliar === true,
  'a cobrança continua sem canal — o defeito que a SPEC-078 B veio consertar');

console.log('\n-- 2b. só o booleano verdadeiro autoriza (fail-closed) --');
// `"true"` de um JSON mal tipado e `1` de um driver antigo NÃO são consentimento.
assert('observer com "true" (string) NÃO é autorização', M.observer_autorizado_str.auxiliar === false);
assert('observer com 1 (inteiro) NÃO é autorização', M.observer_autorizado_um.auxiliar === false);
assert('regime desconhecido cai para o lado do silêncio',
  M.observer_autorizado.desconhecido === false,
  'um `para="auxiliares"` com S sobrando não pode virar permissão');
assert('integração inexistente nunca é canal',
  M.nada.omisso === false && M.nada.plataforma === false && M.nada.auxiliar === false);
assert("'  OBSERVER ' (espaço e maiúscula) continua proibido",
  M.OBSERVER_maiusculo.plataforma === false && M.OBSERVER_maiusculo.auxiliar === false,
  '📊 `purpose` é texto livre: não há CHECK nessa coluna (pg_constraint, 17/08/2026)');

console.log('\n-- 3. quem já podia enviar continua podendo, nos dois regimes --');
for (const caso of ['attendance', 'auxiliary']) {
  assert(`${caso}: permitido em plataforma`, M[caso].plataforma === true);
  assert(`${caso}: permitido em auxiliar`, M[caso].auxiliar === true);
  assert(`${caso}: permitido por omissão`, M[caso].omisso === true);
}

console.log('\n-- 4. 🔴 CONTROLE: a assinatura nova não afrouxou nada por omissão --');
// Se esta bateria ficar verde por acidente, o teste inteiro perde o direito de
// concluir: seria possível "consertar a cobrança" liberando o observador para
// todo mundo, que é exatamente o que a SPEC-063 D proíbe.
assert('omitir `para=` é IDÊNTICO a pedir o regime de plataforma, caso a caso',
  Object.keys(M).every((k) => M[k].omisso === M[k].plataforma),
  Object.keys(M).filter((k) => M[k].omisso !== M[k].plataforma)
    .map((k) => `${k}: omisso=${M[k].omisso} plataforma=${M[k].plataforma}`).join(' · '));
assert('o observador autorizado NÃO vira canal para quem omite o regime',
  M.observer_autorizado.omisso === false);
assert('get_platform_whatsapp_integration NÃO pede o regime de auxiliar',
  Array.isArray(R.chamadores.get_platform_whatsapp_integration)
  && R.chamadores.get_platform_whatsapp_integration.length > 0
  && R.chamadores.get_platform_whatsapp_integration.every((v) => v === null),
  `pedidos encontrados: ${JSON.stringify(R.chamadores.get_platform_whatsapp_integration)}`);

console.log('\n-- 5. a cobrança, rodando o seletor de verdade --');
assert('billing._find_whatsapp_integration PEDE o regime de auxiliar',
  Array.isArray(R.chamadores['billing._find_whatsapp_integration'])
  && R.chamadores['billing._find_whatsapp_integration'].some(
    (v) => v === 'auxiliar' || v === 'ENVIO_DE_AUXILIAR'),
  `pedidos encontrados: ${JSON.stringify(R.chamadores['billing._find_whatsapp_integration'])}`);
const C = R.cobranca;
// 🔴 CONTROLE da SPEC-063 D, agora no caminho real da cobrança: a corretora que
// só tem observador NÃO AUTORIZADO continua sem canal. 📊 Em 17/08/2026 as duas
// únicas integrações ativas do banco são exatamente assim.
assert('só observador NÃO autorizado -> a corretora continua SEM canal',
  C.so_observer_sem_autorizacao === null, `escolheu: ${C.so_observer_sem_autorizacao}`);
assert('só observador AUTORIZADO -> a cobrança ganha canal',
  C.so_observer_autorizado === 'observer', `escolheu: ${C.so_observer_autorizado}`);
assert('sem nenhuma integração -> sem canal', C.vazio === null);
assert('entre observador autorizado e attendance, ganha attendance',
  C.observer_autorizado_e_attendance === 'attendance',
  `escolheu: ${C.observer_autorizado_e_attendance} — a autorização é porta de emergência, não primeira escolha`);
assert('entre attendance e auxiliary, ganha auxiliary',
  C.attendance_e_auxiliary === 'auxiliary', `escolheu: ${C.attendance_e_auxiliary}`);
assert('entre observador autorizado e auxiliary, ganha auxiliary',
  C.auxiliary_depois_de_observer === 'auxiliary', `escolheu: ${C.auxiliary_depois_de_observer}`);

console.log('\n-- 6. o esquema e a tela acompanham o código --');
// Um `is True` sobre coluna que não existe é sempre False: sem a migration, o
// conserto não existe em produção mesmo com o código no ar.
assert(`${SQL_MIGRATION} existe`, existsSync(join(RAIZ, SQL_MIGRATION)));
if (existsSync(join(RAIZ, SQL_MIGRATION))) {
  const sql = readFileSync(join(RAIZ, SQL_MIGRATION), 'utf8');
  assert('a migration adiciona `permite_envio_de_auxiliar`',
    /add column if not exists\s+permite_envio_de_auxiliar\s+boolean/i.test(sql));
  assert('a coluna nasce `not null default false` (o hoje é preservado)',
    /permite_envio_de_auxiliar\s+boolean\s+not null\s+default\s+false/i.test(sql));
  assert('🔴 a migration NÃO liga a autorização para ninguém (sem backfill)',
    !/^\s*update\s+public\.integrations/im.test(sql),
    'um UPDATE não comentado aqui seria a surpresa que a SPEC-063 D proíbe');
}
const rota = readFileSync(join(RAIZ, TS_ROTA), 'utf8');
// 🔴 Procura o TRATADOR, não o nome da ação. A primeira versão desta linha era
// `rota.includes("'set-auxiliary-authorization'")` — e ela ficou VERDE com o
// tratador renomeado, porque o mesmo texto aparece no rótulo que a tela lê.
// Um guarda que casa com a etiqueta em vez do motor não guarda o motor.
assert(`${TS_ROTA}: existe o TRATADOR da ação que grava a autorização`,
  /if\s*\(action === 'set-auxiliary-authorization'\)\s*\{/.test(rota));
assert(`${TS_ROTA}: o rótulo que a tela recebe é o mesmo nome que o tratador atende`,
  /acao:\s*'set-auxiliary-authorization'/.test(rota));
assert(`${TS_ROTA}: a leitura devolve os três papéis para a tela`,
  /papeis,\s*permite_envio_de_auxiliar/.test(rota),
  'o payload de status precisa carregar `papeis` e o estado da autorização');
assert(`${TS_ROTA}: a gravação filtra por company_id (service role ignora RLS)`,
  /update\(\{\s*permite_envio_de_auxiliar[\s\S]{0,300}?\.eq\('company_id'/.test(rota));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f}`);
  console.log('\nA regra canônica é `IntegrationService.pode_enviar`.');
  console.log('Antes de "consertar" o teste, releia integration_service.py:176-192:');
  console.log('a proibição do observador protege o silêncio que a corretora pediu ao');
  console.log('parear. O que a SPEC-078 acrescenta é uma autorização EXPLÍCITA dela —');
  console.log('nunca um afrouxamento por omissão.');
  process.exit(1);
}
process.exit(0);
