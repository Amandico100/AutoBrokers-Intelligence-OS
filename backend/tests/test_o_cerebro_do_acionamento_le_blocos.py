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
    assert "extract_text_from_content" in fonte, (
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
def test_o_sentinela_consulta_a_classe_da_tela():
    """🔴 `classe_da_tela` passa a ter DOIS chamadores, e o Sentinela é um deles."""
    fonte = WD_PY.read_text(encoding="utf-8")
    assert "classe_da_tela" in fonte, (
        "🔴 o Sentinela voltou a não consultar a classe da tela — e aí ele "
        "responde, 30 s depois, a mesma tela de `aceite_de_custo` que o corredor "
        "manda a uma PESSOA (medido em 27/09/2026)")
    assert "tela_que_decide:" in fonte, (
        "o motivo do handoff do Sentinela deixou de ser o MESMO do corredor — "
        "duas famílias de motivo para a mesma causa é o que o guarda de "
        "triagem (`test_o_travamento_vira_linha`) existe para pegar")


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
