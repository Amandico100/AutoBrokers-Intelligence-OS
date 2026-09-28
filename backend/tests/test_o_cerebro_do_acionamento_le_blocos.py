# -*- coding: utf-8 -*-
"""O cérebro do acionamento LÊ BLOCOS — e a tela que DECIDE vale para o Sentinela.

SPEC-119, fatia F4b. Dois consertos, um arquivo, porque foi a MESMA medição que
achou os dois: a bateria 4 (`scripts/bateria_do_vigia.py`) rodando o laço
Vigia→Sentinela→Cérebro de verdade.

## 🔴 CONSERTO 1 — `.content` DE MODELO DE RACIOCÍNIO É UMA **LISTA DE BLOCOS**

📊 27/09/2026, `python scripts/bateria_do_vigia.py --cerebro real --k 2`, laço
REAL, rota `dispatch` = `anthropic:claude-opus-5-5` (a de produção). O que
`_adaptive_reply` devolvia:

```
"[{'id': 'rs_0ba608366c83e343…', 'summary': [], 'type': 'reasoning',
   'content': [], 'encrypted_content': 'gAAAAABqubKOcQyFEQwA9aHVs7xg…'}]"
```

E o resultado do laço, nas DUAS tentativas:

```
estado_final         needs_human
motivo_final         sentinela_stall
enviou_a_seguradora  []
atos                 ['sem_resposta_aprovada', 'esgotou', 'stall_unanswered']
DESENTRAVOU?         🔴 NÃO
```

🔴 **O cérebro do acionamento estava 100 % fora do ar** desde que a SPEC-116 U8
apontou a rota `dispatch` para um modelo de raciocínio. O fiscal recusava por
`too_long` (o blob passa de 400 caracteres), a escada esgotava e TODO travamento
virava handoff. Nada acusava: o sintoma era *"o Sentinela nunca recupera"*, que
se lê como URA difícil.

⚠️ **E o que salvava não era desenho, era SORTE.** Com uma resposta de ≤ 400
caracteres o fiscal teria APROVADO, e o raciocínio cifrado iria para a seguradora
como se fosse a tecla do menu. É por isso que o teste 3 abaixo existe.

📊 **TRÊS pontos de chamada, o mesmo defeito** — medido por `grep -n
invocar_com_reserva` + as 3 linhas seguintes de cada um:

```
app/tasks/dispatch_watchdog.py   `str(content).strip() if content else None`
app/api/webhook.py               `return getattr(result, "content", None)`
app/services/dispatch_router.py  `str(getattr(resposta, "content", resposta) or "")`
```

⛔ O conserto usa `app/agents/utils.py:extract_text_from_content`, a função do
PRODUTO que pega os blocos `type=text` e ignora os de `reasoning` — a mesma que o
`agent_node` usa. Nenhum extrator novo (CLAUDE.md §5).

## 🔴 CONSERTO 2 — A TELA QUE DECIDE VALE PARA O SENTINELA TAMBÉM

A F3 desta SPEC criou `insurer_dispatch_service.classe_da_tela`, e duas famílias
dela têm `handoff: True`. 📊 `grep -n classe_da_tela` achava **UM** chamador,
dentro de `handle_insurer_message`. O Sentinela não passava por lá.

📊 Medido pela bateria 4, cena ②, sobre a tela REAL da allianz (acervo
`allianz-auto.jsonl`, sessão 4971b50b, serviço guincho):

```
tela ..... "Podemos levar o veículo para um oficina referenciada Allianz?
            … Desconto de até {VALOR_RS} na franquia"
classe ... aceite_de_custo · handoff=True
corredor . needs_human, reason=tela_que_decide:aceite_de_custo
🔴 SENTINELA (antes) ... enviou "1" para a seguradora
✅ SENTINELA (depois) .. needs_human, tela_que_decide:aceite_de_custo, 0 bytes
```

🔴 Trinta segundos depois, o MESMO texto recebia veredito OPOSTO — e o caminho que
aceitava a franquia em nome do segurado era o que chegava à seguradora.

## AS LINHAS DE CONTROLE (CLAUDE.md §9.2)

```
· string CRUA continua passando igual (o conserto 1 não pode mudar o provedor
  que já devolvia texto)
· `alternativa_de_conteudo` — o menu desconhecido — CONTINUA indo ao cérebro.
  É o que prova que a cirurgia do conserto 2 é estreita, e não "handoff para tudo"
· uma resposta CURTA de bloco de raciocínio (que o fiscal APROVARIA) prova que a
  proteção de hoje é o extrator, não o teto de 400 caracteres
```

    cd backend && python -m pytest tests/test_o_cerebro_do_acionamento_le_blocos.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WD_PY = RAIZ / "app" / "tasks" / "dispatch_watchdog.py"
WEBHOOK_PY = RAIZ / "app" / "api" / "webhook.py"
ROUTER_PY = RAIZ / "app" / "services" / "dispatch_router.py"

#: 📊 O bloco REAL que o braço devolveu em 27/09/2026, com o `encrypted_content`
#: cortado (⛔ nada de segredo no repositório — CLAUDE.md §13.3).
BLOCO_DE_RACIOCINIO = {"id": "rs_0ba608366c83e343016ab9b28e928c87d28c70011fcf48590a",
                       "summary": [], "type": "reasoning", "content": [],
                       "encrypted_content": "<cortado>"}


# ═════════════════════════════════════════════════════════════════════════════
# 1 · O EXTRATOR DO PRODUTO FAZ O QUE O CONSERTO PRECISA — chamando o MOTOR
# ═════════════════════════════════════════════════════════════════════════════
def test_o_extrator_do_produto_descarta_o_raciocinio():
    """⚠️ CLAUDE.md §9.4: a asserção é sobre a FUNÇÃO do produto, não sobre um
    regex que imite o que ela faz."""
    from app.agents.utils import extract_text_from_content

    # o formato real: um bloco de raciocínio + o texto
    assert extract_text_from_content(
        [BLOCO_DE_RACIOCINIO, {"type": "text", "text": "1"}]) == "1"
    # só raciocínio: NADA de texto, e é isso que vira `None` no chamador
    assert extract_text_from_content([BLOCO_DE_RACIOCINIO]) == ""
    # 🔴 LINHA DE CONTROLE: string crua continua passando igual
    assert extract_text_from_content("2 - Nao") == "2 - Nao"
    assert extract_text_from_content(None) == ""


# ═════════════════════════════════════════════════════════════════════════════
# 2 · OS TRÊS PONTOS DE CHAMADA USAM O EXTRATOR
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("arquivo,ancora", [
    (WD_PY, "invocar_com_reserva"),
    (WEBHOOK_PY, "invocar_com_reserva"),
    (ROUTER_PY, "invocar_com_reserva"),
])
def test_quem_chama_o_cerebro_do_acionamento_extrai_o_texto(arquivo: Path, ancora: str):
    """🔴 Os três consomem `.content` do MESMO papel (`dispatch`).

    A asserção é de FORMA sobre o código, e é legítima aqui pelo mesmo motivo da
    exceção escrita na CLAUDE.md §9.4: o alvo é a DECLARAÇÃO (quem lê `.content`
    cru), e os três caminhos precisam de provedor de verdade para rodar. Quem
    prova o COMPORTAMENTO é o teste 1 (o motor) e a bateria 4 (o laço real).
    """
    fonte = arquivo.read_text(encoding="utf-8")
    assert ancora in fonte, f"{arquivo.name} deixou de chamar o cérebro do acionamento"

    # 🔴 EM LINHA DE CÓDIGO, NÃO EM COMENTÁRIO — e esta linha nasceu de uma
    # MUTAÇÃO QUE FICOU VERDE (G7, 27/09/2026).
    #
    # 📊 A primeira forma deste guarda era `"extract_text_from_content" in fonte`.
    # Desfiz o conserto do `webhook.py` inteiro e o guarda passou: o COMENTÁRIO
    # do conserto cita o nome da função, e o `in fonte` se contentou com ele.
    # Um guarda que um comentário satisfaz é carimbo — é o mesmo detalhe de
    # mutação que deixou um guarda verde duas vezes na SPEC-118.
    codigo = [l for l in fonte.splitlines() if not l.lstrip().startswith("#")]
    assert any("extract_text_from_content" in l for l in codigo), (
        f"🔴 {arquivo.name} consome `.content` do papel `dispatch` sem extrair o "
        "texto dos blocos. Com a rota em modelo de raciocínio, o que segue é "
        "`[{'type': 'reasoning', 'encrypted_content': …}]` — medido em 27/09/2026.")

    # 🔴 E NENHUM `str(content)` cru sobreviveu: protocolo §0.4 — mudou um valor,
    #    `grep` do ANTIGO no arquivo inteiro; sobrevivente é defeito.
    #
    # ⚠️ Só em linha de CÓDIGO. 📊 A primeira forma deste guarda ficou vermelha
    # nos COMENTÁRIOS dos próprios consertos, que citam `str(content)` para
    # dizer o que ele devolvia — e um guarda que proíbe descrever o defeito
    # consertado empurra o porquê para fora do arquivo.
    _CRU = re.compile(
        r'str\(\s*(?:getattr\(\s*\w+\s*,\s*["\']content["\']|content)\s*[,)]')
    crus = [(n, l.strip()) for n, l in enumerate(fonte.splitlines(), 1)
            if not l.lstrip().startswith("#") and _CRU.search(l)]
    assert not crus, (
        f"🔴 sobrou leitura CRUA de `.content` em {arquivo.name}: {crus}")


# ═════════════════════════════════════════════════════════════════════════════
# 3 · 🔴 O TETO DE 400 NÃO É A PROTEÇÃO — e este teste é o que prova
# ═════════════════════════════════════════════════════════════════════════════
def test_o_fiscal_aprovaria_um_bloco_curto_entao_o_extrator_e_a_defesa():
    """A recusa de 27/09 foi por `too_long`. Isso é SORTE, não desenho.

    Um bloco de raciocínio CURTO passa pelo fiscal. Logo, o que impede o blob de
    ir à seguradora é o extrator — e o guarda 2 é quem o vigia.
    """
    from app.services.insurer_dispatch_service import guard_human_phase_reply

    sessao = {"playbook_ref": "yelum-auto-whatsapp@v3", "slots": {}, "captured": {}}
    tela = "Houve a abertura do sinistro?\nBotao 1: Sim\nBotao 2: Nao"

    curto = "[{'type': 'reasoning', 'encrypted_content': 'gAAAA'}]"
    assert len(curto) <= 400
    veredito = guard_human_phase_reply(curto, sessao, insurer_message=tela)
    assert veredito["ok"] is True, (
        "se o fiscal passou a barrar isto, ÓTIMO — mas então este teste precisa "
        "de outra frase, e o comentário do conserto precisa mudar com ele "
        f"(veredito: {veredito})")

    # …e o mesmo blob LONGO é recusado por tamanho, que é o que aconteceu de fato
    longo = "[{'type': 'reasoning', 'encrypted_content': '" + "g" * 500 + "'}]"
    assert guard_human_phase_reply(longo, sessao, insurer_message=tela) == {
        "ok": False, "reason": "too_long", "reply": longo}


# ═════════════════════════════════════════════════════════════════════════════
# 4 · O SENTINELA HONRA O HANDOFF DA CLASSE DE TELA (conserto 2)
# ═════════════════════════════════════════════════════════════════════════════
#: 📊 A tela REAL da allianz, do acervo `allianz-auto.jsonl` (sessão 4971b50b,
#: serviço guincho), que `classe_da_tela` marca `aceite_de_custo`/`handoff=True`.
TELA_DE_CUSTO = ("Podemos levar o veículo para um oficina referenciada Allianz?\n\n"
                 "Confira alguns dos benefícios que você pode ter:\n"
                 "- Desconto de até {VALOR_RS} na franquia")
#: 📊 A tela REAL da yelum (sessão c0c3c694) que é `alternativa_de_conteudo` —
#: `handoff=False`, e o cérebro CONTINUA respondendo. É a linha de controle.
TELA_DE_MENU = "Houve a abertura do sinistro?\nBotão 1: Sim ✅\nBotão 2: Não ❌"


def _sessao_travada_na(tela: str, ref: str) -> dict:
    """Uma sessão em `ura` cuja última entrada é a tela da seguradora."""
    from datetime import datetime, timezone
    agora = datetime.now(timezone.utc).isoformat()
    return {"case_id": "guarda-f4b", "company_id": "guarda-f4b", "playbook_ref": ref,
            "subservice": "guincho", "state": "ura", "live": True, "created_at": agora,
            "slots": {"titular_cpf": "52998224725", "veiculo_placa": "ABC1D23",
                      "local_atual": "R. Exemplo Um, 0, Centro",
                      "local_destino": "Oficina Central, Rua B, 50",
                      "telefone_contato": "48991234567"},
            "transcript": [{"direction": "in", "text": tela, "at": agora}]}


def _rodar_o_sentinela(tela: str, ref: str, *, resposta_do_cerebro: str = "1") -> dict:
    """`_sentinela_recover` REAL, com a BORDA dublada. ⛔ Nada vai para a rede.

    ⚠️ CLAUDE.md §9.4: quem responde é o MOTOR. O cérebro é dublê (a borda que
    custaria API), e o resto — `classe_da_tela`, a escada, o fiscal, o dossiê —
    é o código que roda no ar.
    """
    import asyncio

    import app.tasks.dispatch_watchdog as WD

    enviadas: list = []
    atos: list = []
    dossies: list = []

    class _Wa:
        def send_message(self, to, text, integration=None):
            enviadas.append({"para": to, "texto": text})
            return {"ok": True}

    async def _cerebro(_c, _s, _t):
        return resposta_do_cerebro

    async def _ato(_c, _s, desfecho, payload=None):
        atos.append(desfecho)

    async def _dossie(_c, _s, dossier, _wa, _i):
        dossies.append(str(dossier)[:200])
        return True

    async def _avisa(_s, _wa, _i):
        return True

    async def _ler(*_a, **_k):
        return None

    async def _ato_agente(*_a, **_k):
        return None

    from app.services import dispatch_router as ROUTER

    guardados = [(WD, "_adaptive_reply", WD._adaptive_reply),
                 (WD, "_ato_do_sentinela", WD._ato_do_sentinela),
                 (WD, "_entregar_dossie_com_marcador", WD._entregar_dossie_com_marcador),
                 (WD, "_avisar_o_segurado", WD._avisar_o_segurado),
                 (ROUTER, "_ler_do_redis", getattr(ROUTER, "_ler_do_redis", None)),
                 (ROUTER, "registrar_ato_do_agente",
                  getattr(ROUTER, "registrar_ato_do_agente", None))]
    sessao = _sessao_travada_na(tela, ref)
    try:
        WD._adaptive_reply = _cerebro
        WD._ato_do_sentinela = _ato
        WD._entregar_dossie_com_marcador = _dossie
        WD._avisar_o_segurado = _avisa
        ROUTER._ler_do_redis = _ler
        ROUTER.registrar_ato_do_agente = _ato_agente
        acao = asyncio.run(WD._sentinela_recover(
            "guarda-f4b", "5500000000000", sessao, _Wa(),
            {"id": "int-teste", "provider": "evolution_go"}))
    finally:
        for mod, nome, antigo in guardados:
            if antigo is not None:
                setattr(mod, nome, antigo)
    return {"acao": acao, "estado": sessao.get("state"),
            "motivo": str(sessao.get("reason") or ""), "enviadas": enviadas,
            "atos": atos, "dossies": len(dossies)}


def test_o_sentinela_nao_responde_a_tela_que_decide():
    """🔴 O CONSERTO 2, provado pelo MOTOR — e este teste nasceu de uma mutação
    que ficou VERDE.

    📊 A primeira forma deste guarda era `"classe_da_tela" in fonte`. Apaguei o
    bloco inteiro do conserto e ele passou: o nome sobrevive no `import` e nos
    COMENTÁRIOS. Guarda de TEXTO sobre um conserto de COMPORTAMENTO é carimbo —
    e a CLAUDE.md §9.4 diz por quê: o que se afirma é o comportamento do MOTOR.
    """
    r = _rodar_o_sentinela(TELA_DE_CUSTO, "allianz-auto-whatsapp@v1")
    assert r["enviadas"] == [], (
        "🔴 O SENTINELA RESPONDEU UMA TELA DE ACEITE DE CUSTO. O corredor manda "
        "esta mesma tela a uma PESSOA (`tela_que_decide:aceite_de_custo`); trinta "
        f"segundos depois o Sentinela aceitava a franquia em nome do segurado. "
        f"Enviou: {r['enviadas']}")
    assert r["acao"] == "tela_que_decide", r
    assert r["estado"] == "needs_human"
    assert r["motivo"] == "tela_que_decide:aceite_de_custo", (
        "o motivo do handoff do Sentinela deixou de ser o MESMO do corredor — "
        f"duas famílias de motivo para a mesma causa ({r['motivo']!r})")
    assert r["dossies"] == 1, "handoff sem dossiê deixa quem vai socorrer sem o caso"


def test_controle_o_menu_desconhecido_continua_indo_ao_cerebro():
    """🔴 A LINHA DE CONTROLE do conserto 2, e é ela que dá direito ao teste acima.

    Se os dois lados dessem `needs_human`, o guarda não estaria medindo a classe
    da tela — estaria medindo "o Sentinela desistiu". 📊 Das 624 telas
    desconhecidas do acervo a F3 mediu que 594 seguem o caminho de antes: mandar
    todas a uma pessoa desfaria a decisão do Founder de 05/08/2026.
    """
    r = _rodar_o_sentinela(TELA_DE_MENU, "yelum-auto-whatsapp@v3")
    assert r["enviadas"] and r["enviadas"][0]["texto"] == "1", (
        "🔴 o menu desconhecido parou de ser respondido pelo cérebro — a "
        f"cirurgia deixou de ser estreita ({r})")
    assert r["acao"] == "recovered", r
    assert r["estado"] == "ura", r
    # E os dois lados CONSEGUEM ser diferentes (o corolário da §9.3).
    custo = _rodar_o_sentinela(TELA_DE_CUSTO, "allianz-auto-whatsapp@v1")
    assert r["estado"] != custo["estado"] and r["acao"] != custo["acao"]


def test_a_tela_da_allianz_e_aceite_de_custo_e_o_menu_nao_e():
    """🔴 A LINHA DE CONTROLE do conserto 2 — e ela é a metade que importa.

    A cirurgia tem de ser ESTREITA: a tela de custo vai a uma pessoa, e o menu
    desconhecido CONTINUA indo ao cérebro. 📊 Das 624 telas desconhecidas do
    acervo, a F3 mediu que 594 seguem o caminho de antes; mandar todas a uma
    pessoa desfaria a decisão do Founder de 05/08/2026.
    """
    from app.services.corridor_playbooks import get_playbook
    from app.services.insurer_dispatch_service import classe_da_tela

    pb = get_playbook("allianz-auto-whatsapp@v1")
    custo = ("Podemos levar o veículo para um oficina referenciada Allianz?\n\n"
             "Confira alguns dos benefícios que você pode ter:\n"
             "- Desconto de até {VALOR_RS} na franquia")
    c = classe_da_tela(pb, custo, slots={})
    assert c["chave"] == "aceite_de_custo" and c["handoff"] is True, c

    menu = "Houve a abertura do sinistro?\nBotao 1: Sim\nBotao 2: Nao"
    m = classe_da_tela(get_playbook("yelum-auto-whatsapp@v3"), menu, slots={})
    assert m["handoff"] is False, (
        "🔴 o menu desconhecido passou a virar handoff — a cirurgia do conserto 2 "
        f"deixou de ser estreita e a Regina vai receber handoff por palavra "
        f"trocada de menu ({m})")
