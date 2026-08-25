# -*- coding: utf-8 -*-
"""A tela destrava, e o `release` para de apagar — SPEC-085, BLOCOS E e F.

📊 **O produto não tinha destravamento de acionamento.** `dispatch_monitor.py`
tinha 52 linhas e só GET; `app/admin/acionamentos/page.tsx` era leitura pura;
`admin_spec034.py` não tinha POST de sessão.

> O único destravamento humano do produto era o do PORTAL.

📊 E o resultado media-se em zero, sobre **26.803 eventos**: `work_events` com
`run.resumed` / `run.paused` / `approval.*` / `step.retried` → **0**.
`work_runs.paused_at IS NOT NULL` → 0. `human_review_tasks` → 0 linhas.
**Não é que a retomada falhou — ela não tinha como ser registrada.**

## 🔴 As duas armadilhas deste bloco, e as duas têm guarda aqui

**(1) SOMAR, não substituir.** A Fila já mostra acionamento travado, lendo o
Redis. A linha durável **acrescenta** o que o Redis perde depois das 6h de TTL.
Trocar uma pela outra tiraria da tela todo acionamento EM VOO — e esvaziaria o
dedup por telefone, fazendo as conversas suprimidas voltarem DUPLICADAS.

**(2) LER O GÊMEO.** A tela lê `work_steps.output_redacted`, nunca
`output_summary`. Aquele é o payload de restauração e guarda CPF em claro,
porque a URA precisa dele. A coluna ao lado existe para esta tela.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
ROTA = RAIZ / "app" / "api" / "dashboard" / "acionamentos-travados" / "route.ts"
FILA = RAIZ / "app" / "api" / "dashboard" / "atendimentos" / "route.ts"
CONVERSA = RAIZ / "app" / "api" / "dashboard" / "conversas" / "[id]" / "route.ts"
VIGIA = RAIZ / "backend" / "app" / "tasks" / "handoff_watchdog.py"
PORTAL = RAIZ / "app" / "api" / "dashboard" / "portal-jobs" / "route.ts"


def _codigo(caminho: Path) -> str:
    """Sem comentário de linha e sem bloco `/* */`. Guarda estático que lê
    comentário guarda o comentário — e aqui os comentários CITAM o defeito
    antigo de propósito, para que ele não volte por esquecimento."""
    texto = caminho.read_text(encoding="utf-8")
    fora, dentro = [], False
    for linha in texto.splitlines():
        crua = linha
        if dentro:
            if "*/" in crua:
                dentro = False
                crua = crua.split("*/", 1)[1]
            else:
                continue
        if "/*" in crua:
            antes, resto = crua.split("/*", 1)
            crua = antes + (resto.split("*/", 1)[1] if "*/" in resto else "")
            dentro = "*/" not in resto
        crua = crua.split("//", 1)[0]
        if crua.strip():
            fora.append(crua)
    return "\n".join(fora)


# ---------------------------------------------------------------------------
# 1. A ROTA EXISTE, E TEM EXATAMENTE DOIS BOTÕES
# ---------------------------------------------------------------------------

def test_a_rota_de_destravamento_existe():
    assert ROTA.exists(), (
        "sumiu a rota de destravamento — o acionamento volta a ser o único "
        "trabalho do produto que ninguém consegue assumir")


def test_dois_botoes_e_nao_mais_que_dois():
    """§E.2. Cada botão a mais é uma decisão que alguém precisa tomar com o
    segurado esperando."""
    codigo = _codigo(ROTA)
    assert "'assumir'" in codigo and "'arquivar'" in codigo
    for inventado in ("'retry'", "'reenviar'", "'ignorar'", "'fechar'"):
        assert inventado not in codigo, f"apareceu um terceiro botão: {inventado}"


def test_arquivar_exige_motivo_escrito():
    """Arquivar é dizer 'ninguém vai continuar isto'. Sem motivo, o caso some e
    ninguém sabe por quê — que é o defeito desta SPEC com outro nome."""
    codigo = _codigo(ROTA)
    assert "motivo" in codigo and "arquivar exige um motivo escrito" in codigo


def test_assumir_e_ATOMICO():
    """Duas atendentes não podem assumir o mesmo caso. Mesma escolha do `claim`
    de conversa, que devolve 409 quando outro humano chegou primeiro."""
    codigo = _codigo(ROTA)
    assert ".eq('unblock_state', TRAVADO)" in codigo, (
        "o `assumir` deixou de ser condicional ao estado — duas pessoas podem "
        "assumir o mesmo acionamento e as duas acham que é delas")
    assert "409" in codigo


# ---------------------------------------------------------------------------
# 2. 🔴 A TELA LÊ O GÊMEO, NUNCA O PAYLOAD
# ---------------------------------------------------------------------------

def test_a_tela_le_o_gemeo_mascarado():
    codigo = _codigo(ROTA)
    assert "output_redacted" in codigo, (
        "a tela deixou de ler o gêmeo mascarado")


def test_a_tela_NUNCA_pede_o_payload_cru():
    """🔴 `output_summary` guarda CPF, telefone e endereço em claro, porque a
    URA precisa deles na restauração. Pedi-lo numa tela é trazer PII para um
    lugar que existe justamente para não precisar dela."""
    for arquivo in (ROTA, FILA):
        assert "output_summary" not in _codigo(arquivo), (
            f"{arquivo.name} pede `output_summary` — é o payload de "
            "restauração, com PII em claro. O gêmeo é `output_redacted`")


# ---------------------------------------------------------------------------
# 3. 🔴 O CONTROLE DA REGRESSÃO — a Fila SOMA, não substitui
# ---------------------------------------------------------------------------

def test_a_fila_continua_lendo_a_fonte_QUENTE():
    """🔴 CONTROLE 2 do §E. A linha durável só nasce em `needs_human`; o Redis
    tem TODO acionamento em voo. Substituir tiraria da tela `ura`,
    `human_phase` e `monitoring` — o produto inteiro funcionando."""
    codigo = _codigo(FILA)
    assert "/api/dispatch/active" in codigo, (
        "a Fila deixou de ler os acionamentos EM VOO — some da tela todo "
        "acionamento que está indo bem")
    assert "dispatchClientPhones" in codigo, (
        "sumiu o dedup por telefone — as conversas suprimidas voltam "
        "DUPLICADAS ao lado do acionamento")


def test_a_fila_ACRESCENTA_o_travamento_duravel():
    codigo = _codigo(FILA)
    assert "unblock_state" in codigo and "'travado'" in codigo, (
        "a Fila não lê a linha durável — o travamento com mais de 6h continua "
        "sem lugar nenhum para aparecer, que é a SPEC inteira")


def test_o_durravel_vem_DEPOIS_da_fonte_quente():
    """A ordem importa: o dedup por `case_id` compara com o que veio do Redis,
    e para isso o Redis precisa já ter sido lido."""
    codigo = _codigo(FILA)
    assert codigo.index("/api/dispatch/active") < codigo.index("unblock_state"), (
        "a leitura durável passou na frente da quente — o dedup compara com "
        "uma lista vazia e o mesmo caso aparece duas vezes")


# ---------------------------------------------------------------------------
# 4. O ESCOPO POR CORRETORA — CLAUDE.md §7
# ---------------------------------------------------------------------------

def test_toda_consulta_e_por_corretora():
    """O backend usa service role: RLS sem policy não protege nada contra erro
    de filtro no código."""
    codigo = _codigo(ROTA)
    consultas = codigo.count(".from('work_runs')") + codigo.count(".from('work_steps')")
    filtros = codigo.count("company_id")
    assert consultas >= 3, f"esperava ao menos 3 consultas, achei {consultas}"
    assert filtros >= consultas, (
        f"{consultas} consultas e só {filtros} menções a company_id — alguma "
        "consulta pode estar sem o filtro de corretora")


def test_a_rota_usa_a_mesma_porta_do_PORTAL():
    """§E.3: a referência é o portal, que já passou no gate. Mesma forma de
    autenticação e mesma exigência de mesma origem — nunca uma segunda."""
    rota, portal = _codigo(ROTA), _codigo(PORTAL)
    for peca in ("resolveSessionCompany", "getSupabaseAdmin", "assertSameOrigin"):
        assert peca in rota, f"a rota não usa `{peca}`"
        assert peca in portal, f"o portal deixou de usar `{peca}` — mudou a referência"


# ---------------------------------------------------------------------------
# 5. BLOCO F — `HUMAN_REQUESTED` deixa de ter dois sentidos
# ---------------------------------------------------------------------------

def test_o_vigia_LE_claimed_by():
    """📊 O select dele nem PEDIA a coluna que distingue os dois sentidos de
    `HUMAN_REQUESTED`. Uma conversa já assumida continuava gerando
    *"ATENDIMENTO PRECISA DE VOCÊ"* a cada 6h."""
    fonte = VIGIA.read_text(encoding="utf-8")
    codigo = "\n".join(l.split("#", 1)[0] for l in fonte.splitlines()
                       if l.split("#", 1)[0].strip())
    assert "claimed_by" in codigo, "o Vigia continua sem pedir `claimed_by`"
    assert 'is_("claimed_by", "null")' in codigo, (
        "o Vigia lê `claimed_by` e não FILTRA por ele — ler sem usar é o mesmo "
        "que não ler")


def test_o_teto_deixou_de_ser_um_continue_MUDO():
    fonte = VIGIA.read_text(encoding="utf-8")
    trecho = fonte.split("if _n > _MAX_LEMBRETES:", 1)[-1][:900]
    assert "logger." in trecho, (
        "o teto voltou a calar em silêncio — passar do teto é o sinal mais "
        "forte de que ninguém assumiu em 24h, e ele não aparecia em lugar nenhum")


def test_o_release_NAO_apaga_o_pedido_da_IA():
    """🔴 §E.4 / §F.3. Ele devolvia SEMPRE para `open`, e o pedido sumia da Fila
    e do select do Vigia. Era o que tornava MENTIRA a última mensagem do Vigia:
    *"ela continua na Fila do painel — de lá ninguém a tira sozinho."*"""
    codigo = _codigo(CONVERSA)
    trecho = codigo.split("action === 'release'", 1)[-1][:900]
    assert "human_handoff_reason" in trecho, (
        "o `release` voltou a ignorar se havia um handoff aberto")
    assert "'HUMAN_REQUESTED'" in trecho and "'open'" in trecho, (
        "o `release` deixou de escolher entre a fila e o `open`")


def test_CONTROLE_o_release_ainda_devolve_para_open_quando_NAO_ha_handoff():
    """E o controle: uma pessoa que só entrou para dar um oi não pode criar um
    pedido de atendimento ao sair. Se o `release` mandasse tudo para a fila, o
    Vigia passaria a cobrar conversas que ninguém pediu."""
    codigo = _codigo(CONVERSA)
    trecho = codigo.split("action === 'release'", 1)[-1][:900]
    assert "handoffAberto ?" in trecho, (
        "o `release` virou incondicional — ou some o pedido, ou inventa um")


def test_o_loadScoped_traz_os_campos_que_a_regra_usa():
    """Regra que lê campo não selecionado lê `undefined`, e `undefined` é
    falsy: o `release` voltaria a mandar tudo para `open`, em silêncio."""
    codigo = _codigo(CONVERSA)
    select = codigo.split("from('conversations')", 1)[-1][:400]
    for campo in ("human_handoff_reason", "resolvido_em"):
        assert campo in select, (
            f"`{campo}` não está no select — a regra do `release` lê "
            "`undefined` e decide errado sem erro nenhum")
