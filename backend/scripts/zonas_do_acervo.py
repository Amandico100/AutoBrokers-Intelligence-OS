"""Quem está falando: a URA, ou uma pessoa? — a marcação de ZONA.

`direction='in'` é a **direção** da mensagem, não o **emissor**. Depois que a URA
transfere o caso, quem escreve `in` é o **atendente humano da seguradora**.

📊 Medido em 21/08/2026: **4.805 de 16.242 eventos `in` (29,6%)** são posteriores
à tela de transferência, em 140 sessões.

🔴 **E é por isso que este módulo existe, não por elegância.** O eixo B da rubrica
pergunta *"alguma tela do corpus não casa passo nenhum e pede algo?"*. Medido na
Allianz:

```
telas distintas que PEDEM algo:   zona humana 472   ·   zona URA 126   (3,7×)
```

**472 reprovações automáticas, permanentes e insanáveis.** Nenhuma rota da Allianz
seria liberada: todas bateriam o teto de 3 voltas. A SPEC não falharia com erro —
falharia **reprovando tudo**, e o executor procuraria o defeito no corredor a vida
inteira.

📊 **O CONTROLE que prova que as duas zonas são coisas diferentes** — se fossem a
mesma, os percentuais seriam parecidos:

```
zona                          eventos    texto em 1 sessão só
HUMANO                          4.674           44,8 %
URA          CONTROLE           3.509           11,7 %      ← 3,8× menos
```

**URA se repete; gente não.**

═══════════════════════════════════════════════════════════════════════════════
PROVENIÊNCIA — 📊 minerado em 21/08/2026 por 8 mineradores, um por seguradora.
Cada padrão traz a contagem de sessões medida ao lado. As correções em relação à
tabela escrita nas rodadas de juiz estão marcadas 🔴 no lugar.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import regua_motor as M

# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-EXTRA-001.4 D1 — AS TABELAS MUDARAM DE CASA, e este script as IMPORTA.
#
# `FRONTEIRAS`, `APRESENTACAO_HUMANA`, `AVISO_DE_ESPERA`, `APRESENTACAO_DO_ROBO`,
# `NAO_E_FRONTEIRA` — com a proveniência medida ao lado de cada padrão — e a
# normalização que as mediu moram agora em
# `backend/app/services/quem_fala_na_seguradora.py`, que o MOTOR importa.
# Uma fonte, dois consumidores. ⛔ Não recrie a tabela aqui (CLAUDE.md §5).
# ═════════════════════════════════════════════════════════════════════════════
from app.services.quem_fala_na_seguradora import (  # noqa: E402,F401
    _CACHE,
    APRESENTACAO_DO_ROBO,
    APRESENTACAO_HUMANA,
    AVISO_DE_ESPERA,
    FRONTEIRAS,
    NAO_E_FRONTEIRA,
    _compilados,
    _fronteira_de,
    e_fronteira,
    e_o_robo_se_apresentando,
    limpar_invisiveis,
    norm_para_classificar,
    tem_apresentacao_humana,
)

# ─────────────────────────────────────────────────────────────────────────────
# A CLASSIFICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

# 🔴 O `session_id` chega de dois jeitos e os dois significam "não tem sessão":
#    `None` quando vem direto do PostgREST, e a STRING `"None"` quando o acervo
#    passou por um `json.dump` no meio. ⚠️ Uma checagem `if not sid` pega o
#    primeiro e **deixa passar o segundo** — e a diferença apareceu como duas
#    sessões-fantasma no guarda de completude, com "seguradora" allianz e porto.
#    É a mesma família do bucket órfão que produziu o off-by-one da SPEC.
_SEM_SESSAO = (None, "", "None", "none", "null")


def _tem_sessao(sid: Any) -> bool:
    return sid not in _SEM_SESSAO



# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-121 F3 · O ROBÔ RECOMEÇA DEPOIS DA PESSOA — e o acervo não via.
#
# Até 29/09/2026 `zonas()` marcava HUMANO **tudo** o que vinha depois da primeira
# transferência. Mas a sessão de WhatsApp da corretora com a seguradora é UMA só
# por dias: a pessoa da seguradora encerra, a corretora escreve "oi" de novo, e
# **o robô recomeça do Termo de Privacidade**. Esse segundo acionamento inteiro
# ficava fora do corpus.
#
# 📊 BLOCO 0 da SPEC-121 §6 (`bloco0/zonas_fim.py`, 29/09): na Allianz
#    residencial, 39 sessões têm o protocolo SÓ na zona humana, e em 19 delas o
#    robô recomeçou. Exemplo: `8ad1d251` faz uma máquina de lavar INTEIRA pelo
#    robô (menu, aparelho, data, período, resumo, protocolo) depois de uma
#    transferência — e nada disso chegava ao acervo.
#
# 🔴 O CRITÉRIO QUE DISTINGUE ROBÔ DE PESSOA É O QUE O MÓDULO JÁ TINHA:
#    `APRESENTACAO_DO_ROBO` (`quem_fala_na_seguradora`, o controle negativo da
#    apresentação humana — *"sou a assistente virtual"*, *"atendimento
#    digital"*), lido por `e_o_robo_se_apresentando`. Nenhuma tabela nova.
#
#    ⛔ E ele sozinho NÃO basta — a medição achou a exceção: 📊 `334a4892` (hdi)
#    tem, depois da pessoa, *"Olá, eu sou a assistente virtual da HDI… a
#    solicitação de … para a assistência N foi aberta com sucesso"*. É o robô,
#    sim, mas é AVISO de uma solicitação que a PESSOA abriu. Contá-lo daria à
#    rota um "chegou ao protocolo" que o corredor nunca percorreu. Por isso o
#    recomeço exige as DUAS coisas:
#
#      ① o robô se apresenta (`APRESENTACAO_DO_ROBO`), na direção `in`, e
#      ② a corretora RESPONDE a ele (≥ 1 `out`) antes da próxima transferência.
#
#    Sem ②, é notificação → continua HUMANO, como sempre foi.
#
# 📊 O CONTROLE que dá direito ao critério (29/09, `scratchpad/f3_medir_reabre.py`
#    sobre as 688 sessões de `observed_events`): das 41 sessões em que o robô se
#    reapresenta depois de uma fronteira (allianz 31 · hdi 2 · porto 2 · yelum 2 ·
#    mapfre 1 …), **ZERO** têm uma pessoa se apresentando depois da reapresentação
#    sem uma NOVA fronteira no meio. O robô que recomeça fala sozinho até
#    transferir de novo — e aí a zona volta a ser HUMANO.
# ═════════════════════════════════════════════════════════════════════════════
MOTIVO_RECOMECO = "RECOMECO"


def _o_robo_recomeca(eventos: List[Dict[str, Any]], i: int, seguradora: str) -> bool:
    """O evento `i` abre um NOVO atendimento do robô? ① e ② do bloco acima."""
    e = eventos[i]
    if e.get("direction") != "in":
        return False
    if not e_o_robo_se_apresentando(e.get("text") or ""):
        return False
    for f in eventos[i + 1:]:
        if not _tem_sessao(f.get("session_id")):
            continue
        if f.get("direction") == "out" and (f.get("text") or "").strip():
            return True
        if f.get("direction") == "in" and e_fronteira(
                seguradora, norm_para_classificar(f.get("text") or "")):
            return False
    return False


def zonas(eventos_da_sessao: Iterable[Dict[str, Any]],
          seguradora: str) -> Iterator[Tuple[Dict[str, Any], str, Optional[str]]]:
    """Devolve `(evento, zona, motivo)` para cada evento, em ordem de tempo.

    Zonas — 🔴 são TRÊS, não duas:

      URA      a seguradora falando por robô          → o corpus
      HUMANO   atendente da seguradora digitando      → preservada, insumo da 084
      ORFAO    `session_id is null`                   → fora de tudo + PENDENCIAS

    🔴 `ORFAO` existe porque **sem sessão não há "antes/depois da transferência"**.
    📊 493 eventos `in` (3,0%). E há fala humana entre eles: uma marca de
    fronteira da porto tem `session_id` nulo — sem esta zona ela entraria como URA.

    🔴 **NÃO existe zona CORRETORA.** A tela que cita a corretora **fica no
    corpus, mascarada**. 📊 Descartá-la tiraria 66 telas de URA, uma delas a tela
    do CPF da tokio — que é o ponto de entrada obrigatório do fio dela.

    🔴 SPEC-121 F3 — a zona HUMANO **acaba** quando o robô recomeça (bloco
    acima): o evento da reapresentação volta como `(e, "URA", "RECOMECO")`, e é
    por esse motivo que o gerador sabe onde começa o NOVO atendimento. Uma nova
    fronteira depois dele devolve a zona a HUMANO.
    """
    ordenados = sorted(eventos_da_sessao, key=lambda x: (x.get("wa_timestamp") or ""))
    humano = False
    for i, e in enumerate(ordenados):
        if not _tem_sessao(e.get("session_id")):
            yield e, "ORFAO", "session_id nulo"
            continue
        if humano:
            if _o_robo_recomeca(ordenados, i, seguradora):
                humano = False
                yield e, "URA", MOTIVO_RECOMECO
                continue
            yield e, "HUMANO", None
            continue
        n = norm_para_classificar(e.get("text") or "")
        motivo = e_fronteira(seguradora, n)
        if motivo:
            humano = True
            # 🔴 A própria fronteira ainda é URA: é a URA anunciando.
            yield e, "URA", motivo
            continue
        yield e, "URA", None


def atendimentos(eventos_da_sessao: Iterable[Dict[str, Any]],
                 seguradora: str) -> List[List[Tuple[Dict[str, Any], str]]]:
    """A sessão partida em ATENDIMENTOS: um a cada vez que o robô recomeça.

    `[[(evento, zona), ...], ...]` — o 1º começa no 1º evento; cada `RECOMECO`
    de `zonas()` abre o seguinte. Sessão sem recomeço = UM atendimento, igual à
    sessão inteira (e o gerador faz exatamente o que fazia antes de 29/09).

    🔴 Por que partir, e não só devolver as telas ao corpus: 📊 `8ad1d251` tem,
    na MESMA sessão, um acompanhamento de DESENTUPIMENTO e depois uma MÁQUINA DE
    LAVAR inteira. Com uma etiqueta só por sessão, as telas da máquina entrariam
    na rota do desentupimento como órfãs — telas que aquele corredor nunca vê.
    Cada atendimento tem o SEU serviço.
    """
    partes: List[List[Tuple[Dict[str, Any], str]]] = [[]]
    for e, zona, motivo in zonas(eventos_da_sessao, seguradora):
        if motivo == MOTIVO_RECOMECO and partes[-1]:
            partes.append([])
        partes[-1].append((e, zona))
    return [p for p in partes if p]


def sessao_tem_fronteira(seguradora: str, eventos) -> bool:
    """A URA anunciou a transferência em algum ponto?"""
    for e in eventos:
        if e.get("direction") != "in":
            continue
        if e_fronteira(seguradora, norm_para_classificar(e.get("text") or "")):
            return True
    return False


def guarda_de_completude_da_fronteira(
        acervo_por_seguradora: Dict[str, Dict[Any, List[Dict[str, Any]]]]
) -> Dict[str, Dict[str, Any]]:
    """🔴 A `FRONTEIRAS` perdeu alguém? — a pista do Founder virada guarda.

    Para cada seguradora, conta as sessões em que **alguém se apresenta pelo nome
    e não há nenhuma marca de fronteira antes**. Cada uma dessas é uma marca que
    falta na tabela.

    ```
    sessoes_com_apresentacao_sem_fronteira == 0   → VERDE
                                             > 0  → VERMELHO, e a tabela está incompleta
    ```

    🔴 **PROVADO NOS DOIS SENTIDOS** (CLAUDE.md §9.3), 📊 21/08/2026:

    ```
                 ANTES da mineração          DEPOIS
      porto        4 sem fronteira  🔴          0  ✅
      hdi          3                🔴          0  ✅
      yelum        3-4              🔴          0  ✅
      bradesco     2                🔴          0  ✅   (a tabela dizia `[]`)
      allianz      0                ✅          0  ✅
      zurich/tokio/alfa  0          ✅          0  ✅   (não há humano no acervo)
    ```

    **Um guarda que nunca esteve vermelho não prova nada.** Este esteve, em
    quatro seguradoras, e foi ele que produziu as marcas que a tabela ganhou.
    """
    fora: Dict[str, Dict[str, Any]] = {}
    for seg, sessoes in acervo_por_seguradora.items():
        com_apres: set = set()
        com_fronteira: set = set()
        for sid, eventos in sessoes.items():
            if not _tem_sessao(sid):
                continue
            for e, _zona, motivo in zonas(eventos, seg):
                if e.get("direction") != "in":
                    continue
                n = norm_para_classificar(e.get("text") or "")
                if motivo == "FRONTEIRA":
                    com_fronteira.add(sid)
                if tem_apresentacao_humana(seg, n):
                    com_apres.add(sid)
        orfas = com_apres - com_fronteira
        fora[seg] = {
            "com_apresentacao": len(com_apres),
            "com_fronteira": len(com_fronteira),
            "apresentacao_sem_fronteira": sorted(str(s)[:8] for s in orfas),
            "verde": not orfas,
        }
    return fora


# ─────────────────────────────────────────────────────────────────────────────
# O TESTE OBRIGATÓRIO DA TABELA (SPEC-084 §2.5.1.4)
# ─────────────────────────────────────────────────────────────────────────────
def cruzamento_fronteira_x_nao_fronteira() -> List[Tuple[str, str, str]]:
    """Todo padrão de `FRONTEIRAS` roda contra `NAO_E_FRONTEIRA`. Tem de dar ZERO.

    🔴 *"Um guarda sem controle negativo não distingue 'transferiu' de 'não
    conseguiu transferir'."* Devolve a lista de colisões — vazia é o esperado.
    """
    colisoes = []
    for seg, positivos in FRONTEIRAS.items():
        for negativo in NAO_E_FRONTEIRA.get(seg, []):
            # o padrão negativo é usado como TEXTO de exemplo, sem os metacaracteres
            exemplo = re.sub(r"[\\^$.|?*+()\[\]{}]", " ", negativo)
            exemplo = re.sub(r"\s+", " ", exemplo).strip()
            for p in positivos:
                if re.search(p, exemplo):
                    colisoes.append((seg, p, negativo))
    return colisoes


# 📊 Sessões cuja DIREÇÃO está invertida no banco — `direction='in'` assinado
#    pela corretora. Defeito de ingestão, achado pelo minerador da hdi:
#    *"7 sessões / 16 eventos com `in` começando por `{NOME} - resulta seguros`
#    ou `{NOME} - autofleet seguros`"*.
# 🔴 NÃO é a zona CORRETORA (que foi eliminada por medição) — é DADO ERRADO.
#    Sai do corpus e vai para `PENDENCIAS.md` com dono 🤖.
_RX_DIRECAO_INVERTIDA = re.compile(
    r"^\s*\{?nome\}?\s*-\s*(resulta|autofleet)|^\s*[a-z]{3,20}\s*-\s*(resulta|autofleet)")


def direcao_invertida(texto_norm: str) -> bool:
    """A mensagem `in` foi, na verdade, escrita pela corretora?

    ⚠️ CUIDADO — este é o oposto do caso legítimo. 📊 A URA da tokio SAÚDA a
    corretora pelo nome (*"olá, {NOME} - {CORRETORA} seguros! digite o cpf"*) e
    aquilo É tela de URA. O que distingue é a mensagem ser **só** a assinatura,
    sem tela em volta.
    """
    if not _RX_DIRECAO_INVERTIDA.match(texto_norm):
        return False
    # a tela da tokio continua com "digite o cpf/cnpj" etc. — texto longo.
    return len(texto_norm.strip()) <= 60
