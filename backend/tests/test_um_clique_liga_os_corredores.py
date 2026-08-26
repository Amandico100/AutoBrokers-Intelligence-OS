# -*- coding: utf-8 -*-
"""Um clique liga os 14 — e a escolha da corretora vence. SPEC-093, BLOCO G.

> 🔴 **Decisão do Founder, 25/08:** *"na hora que a corretora ligar o
> atendimento, tudo pode estar ligado automaticamente. Ela pode desligar no
> dashboard."*

📊 Medido em `build_corridor_catalog()`, que é a fonte da tela:

```
CARTÕES que a tela lista .....  14      (10 seguradoras · auto 10 + residencial 4)
SUBSERVIÇOS somados ..........  73
```

Os 73 aparecem como **texto dentro do cartão**, nunca como coisa clicável — ela
clica no máximo 14, já hoje. ⛔ Por isso o redesenho da tela saiu do escopo.

## 🔴 A DECISÃO DO G.2, TOMADA PELO EXECUTOR

A SPEC deixou a escolha em aberto: **lotear a âncora**, ou aceitar o laço e
escrever por que ele é retomável.

**Loteou.** 📊 O motivo é medido: `ensureCorridorAnchor` fazia `SELECT + INSERT`
por corredor, e `corridor_templates` tem **2 linhas, ambas `scope='global'` com
`company_id` NULO** — enquanto a busca filtrava `.eq('company_id', companyId)`.
Ela não achava nenhuma e inseria uma âncora nova para cada corredor: **42 idas
sequenciais ao Supabase** num botão que precisa parecer instantâneo.

> ⚠️ E lotear torna a retomabilidade **mais fácil** de provar, não mais difícil:
> são três passos, cada um idempotente sozinho.

## Onde cada gate é provado

| gate | onde | como |
|---|---|---|
| ① ② ③ ④ ⑥ | `scripts/spec093-corredores.test.mjs` | `node` executa a decisão pura |
| ⑤ | aqui | o corredor pausado cai no mesmo `needs_human` que já existe |
| a fiação | aqui | leitura de fonte: o gatilho, o lote, e o `onConflict` |
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ.parent
MJS = WEB / "scripts" / "spec093-corredores.test.mjs"
DECISAO_TS = WEB / "lib" / "admin" / "corridor-bulk-decision.ts"
STORE_TS = WEB / "lib" / "admin" / "tenant-corridor-store.ts"
ROTA_TS = WEB / "app" / "api" / "dashboard" / "agents" / "[agentKey]" / "route.ts"

_NODE = shutil.which("node")
_sem_node = pytest.mark.skipif(_NODE is None, reason="node ausente neste ambiente")


def _rodar_mjs(caminho: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_NODE, str(caminho)], cwd=str(WEB), capture_output=True, text=True,
        timeout=90, encoding="utf-8", errors="replace",
        env={**os.environ, "NODE_OPTIONS": ""})


# ---------------------------------------------------------------------------
# O EXECUTOR — e a prova de que ele enxerga vermelho
# ---------------------------------------------------------------------------

@_sem_node
def test_os_gates_do_bloco_G_passam():
    """① ② ③ ④ ⑥, executados de verdade em `node`."""
    r = _rodar_mjs(MJS)
    assert r.returncode == 0, (r.stdout or "")[-2500:] + (r.stderr or "")[-600:]
    assert "0 falharam" in (r.stdout or ""), (r.stdout or "")[-800:]


@_sem_node
def test_CONTROLE_o_executor_CONSEGUE_ver_vermelho():
    """§9.3 — um executor que nunca vê falha não guarda nada."""
    falso = MJS.parent / "_controle_corredores_falha.test.mjs"
    linhas = [
        "let p=0,f=0;",
        "function assert(n,c){if(c){p++}else{f++;console.log('  x '+n)}}",
        "assert('esta asserção é falsa DE PROPÓSITO', false);",
        "console.log(`== Resumo: ${p} passaram, ${f} falharam ==`);",
        "process.exit(f ? 1 : 0);",
    ]
    falso.write_text(chr(10).join(linhas), encoding="utf-8")
    try:
        r = _rodar_mjs(falso)
        assert r.returncode != 0, "o executor devolveu 0 para um teste que FALHA"
        assert "1 falharam" in (r.stdout or "")
    finally:
        falso.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# A FIAÇÃO — sem ela os gates acima guardam uma função que ninguém chama
# ---------------------------------------------------------------------------

def test_ligar_o_atendimento_LIGA_os_corredores():
    """> *"na hora que a corretora ligar o atendimento, tudo pode estar ligado"*

    🔴 O gate em `node` prova a DECISÃO. Esta linha prova que alguém a chama —
    📊 e neste repositório já houve um `.test.mjs` guardando código que nenhum
    caminho de produção alcançava.
    """
    rota = ROTA_TS.read_text(encoding="utf-8")
    assert "ativarTodosOsCorredores(" in rota, (
        "o toggle do atendimento parou de ligar os corredores — o botão do "
        "Founder voltou a ser catorze cliques")
    # ⚠️ Só no RELIGAMENTO. Um clique que não muda nada não é evento.
    assert "religou" in rota, (
        "o gatilho perdeu a condição de religamento — apertar `ligar` num "
        "agente já ligado passaria a disparar uma rodada do nada")
    # 🔴 E falhar em ligar corredor não pode desfazer o toggle.
    #
    # ⚠️ JANELA POR MARCA, NÃO POR CONTAGEM DE CARACTERES. A primeira versão
    # usava `rota[i-900 : i+500]` e quebrou no mesmo dia, quando o comentário
    # que explica o conserto do painel cresceu — 📊 exatamente o defeito que
    # `test_orquestracao_pareamento` acabou de pagar. Guarda que quebra quando
    # ninguém errou ensina a ignorar guarda.
    ini = rota.index("let corredores")
    trecho = rota[ini:rota.index("if (decisao.acao === 'toggle')", ini)]
    assert "try {" in trecho and "catch" in trecho, (
        "a ativação dos corredores deixou de ser best-effort — uma falha ali "
        "passaria a desfazer um toggle que já aconteceu")
    assert "console.error" in trecho, (
        "a falha ficou muda: um 'ligou tudo' que ligou nada é a família de "
        "silêncio que esta SPEC existe para matar")


def test_a_decisao_e_PURA_e_mora_em_arquivo_SEM_IMPORT():
    """📊 `node` não resolve o alias `@/`. Um gate que precisasse do store
    seria um gate que ninguém roda."""
    fonte = DECISAO_TS.read_text(encoding="utf-8")
    assert "export function decidirLoteDeAtivacao" in fonte
    linhas_de_import = [l for l in fonte.splitlines()
                        if l.strip().startswith("import ")]
    assert linhas_de_import == [], (
        f"`corridor-bulk-decision.ts` ganhou import: {linhas_de_import}. "
        "O gate em `node` puro para de conseguir carregá-lo.")

    store = STORE_TS.read_text(encoding="utf-8")
    assert "decidirLoteDeAtivacao(" in store, (
        "o store parou de usar a decisão pura — a lógica voltou para dentro do "
        "IO, onde o gate não a alcança")


def test_a_ancora_vai_em_LOTE_e_a_singular_NAO_e_uma_segunda_copia():
    """🔴 A decisão do G.2, em código — e o §5 junto.

    ⚠️ `ensureCorridorAnchor` (singular) chama a plural com um item. Duas
    implementações divergiriam na primeira correção que só uma recebesse.
    """
    store = STORE_TS.read_text(encoding="utf-8")
    assert "async function ensureCorridorAnchors(" in store
    # 🔴 O CORPO INTEIRO, NÃO "a chamada existe em algum lugar".
    #
    # 📊 A primeira versão deste guarda ficou VERDE sob a mutação
    # `return null; // MUTACAO`: a chamada continuava no corpo, e a âncora
    # singular passava a falhar SEMPRE — `setTenantCorridorStatus` devolveria
    # `ancora_indisponivel` em todo clique de um corredor só.
    #
    # ⚠️ Guarda que só procura substring aprova isso. Este exige as duas
    # linhas, e por isso a mutação o derruba.
    i = store.index("async function ensureCorridorAnchor(" + chr(10))
    corpo = store[i:store.index(chr(10) + "}", i)]
    esperado = chr(10).join([
        "  const mapa = await ensureCorridorAnchors(supabase, companyId, [corridor]);",
        "  return mapa.get(corridor.corridor_id) ?? null;",
    ])
    # 🔴 IGUAL, NÃO "CONTÉM". A versão anterior passava sob mutação por
    # INSERÇÃO — um `return null;` ANTES das duas linhas as deixa intactas:
    #
    #     ): Promise<string | null> {
    #   +   return null; // MUTACAO
    #       const mapa = await ensureCorridorAnchors(...);
    #
    # ⚠️ É a mesma família da qual o comentário acima dizia ter aprendido.
    corpo_util = chr(10).join(
        l for l in corpo.splitlines()
        if l.strip() and not l.strip().startswith(("//", "*", "/*"))
        and not l.strip().startswith("async function ensureCorridorAnchor(")
        and l.strip() not in ("supabase: SupabaseClient,", "companyId: string,",
                              "corridor: CorridorFromCode,",
                              "): Promise<string | null> {"))
    assert corpo_util == esperado, (
        "o corpo da âncora singular tem MAIS do que as duas linhas:" + chr(10)
        + corpo_util + chr(10) + "--- esperado ---" + chr(10) + esperado)
    assert esperado in corpo, (
        "a âncora singular mudou de forma. Ela tem de ser exatamente estas "
        "duas linhas:" + chr(10) + esperado + chr(10) +
        "Uma segunda cópia da plural divergiria na primeira correção que só "
        "uma recebesse (§5) — e um `return null` deixaria todo clique de "
        "corredor único sem âncora.")
    # e o lote é UM insert, não um por corredor
    assert ".insert(faltando.map(" in store, (
        "o insert das âncoras voltou a ser um por corredor")


def test_o_upsert_do_status_e_UM_lote_com_onConflict():
    """④ retomabilidade: o passo que escreve é idempotente por construção."""
    store = STORE_TS.read_text(encoding="utf-8")
    i = store.index("export async function ativarTodosOsCorredores(")
    corpo = store[i:]
    assert ".upsert(novas, { onConflict: 'company_id,corridor_template_id' })" in corpo, (
        "o lote de status deixou de ser um upsert idempotente — retomar uma "
        "rodada interrompida passaria a estourar em vez de convergir")
    assert corpo.count(".upsert(") == 1, (
        "apareceu um segundo upsert: dois escritores da mesma coluna é como o "
        "`unblock_state` ganhou duas cópias, uma com guarda e outra sem")


def test_o_filtro_por_corretora_esta_em_TODA_leitura_e_escrita():
    """⑥ CLAUDE.md §7 — nenhum dado atravessa tenants."""
    store = STORE_TS.read_text(encoding="utf-8")
    i = store.index("export async function ativarTodosOsCorredores(")
    corpo = store[i:]
    assert corpo.count(".eq('company_id', companyId)") >= 1
    assert "company_id: companyId," in corpo
    assert "UUID.test(companyId)" in corpo, (
        "o `company_id` deixou de ser validado — um valor forjado entraria "
        "direto no `.or()` de `loadAnchors`")


# ---------------------------------------------------------------------------
# ⑤ corredor pausado recebe atendimento → handoff, não falha
# ---------------------------------------------------------------------------

def test_GATE_5_corredor_que_nao_sabe_responder_vai_para_HANDOFF():
    """📊 O caminho já existe e o bloco só precisa que o pausado entre nele.

    ⚠️ Guarda de leitura, e é o honesto: a degradação mora no motor Python
    (`insurer_dispatch_service`), e o que o BLOCO G promete é **não criar um
    segundo caminho de falha** ao lado dele.
    """
    motor = (RAIZ / "app" / "services" / "insurer_dispatch_service.py").read_text(
        encoding="utf-8")
    assert "needs_human" in motor and "human_phase" in motor
    # ⛔ e o store de corredores NÃO executa nada — nem canal, nem mensagem
    store = STORE_TS.read_text(encoding="utf-8")
    for proibido in ("send_message", "sendMessage", "fetch(`${backendUrl}/api/dispatch",
                     "evolution", "wa.send"):
        assert proibido not in store, (
            f"`{proibido}` apareceu no store de corredores — ele é estado de "
            "configuração e não pode executar nada")
