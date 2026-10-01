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


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-121 F3b · CONSULTAR UM PEDIDO QUE JÁ EXISTE NÃO É ABRIR UM PEDIDO
#
# A Allianz, depois do CPF e do endereço, pergunta se o segurado quer ver o
# pedido que ele JÁ TEM:
#
#     "Identifiquei que temos uma solicitação de serviço feita. O que deseja?
#      *1 -* Ver detalhes  *2 -* Abrir novo atendimento"
#
# Quem responde "Ver detalhes" recebe o RESUMO do pedido ANTIGO — com o número
# de protocolo dele:
#
#     "*RESUMO*  *Protocolo 50195469  *Serviço:* *DESENTUPIMENTO*; ..."
#
# ⛔ Isso NÃO é desfecho. O robô não abriu nada: leu o que alguém abriu antes.
#    📊 29/09 (`scratchpad/f3b/consulta.py` sobre o acervo regerado pela F3): 26
#    telas deste RESUMO em 25 atendimentos da Allianz (regex `^*RESUMO* *Protocolo`
#    sobre allianz-auto/residencial), e o padrão-ouro `*Serviço:*` dele dava a
#    ETIQUETA ao atendimento. No acervo de 28/09 já eram 16 telas em 15. Foi assim que
#    `allianz/residencial/desentupimento` virou ATENDE SOZINHO pela consulta
#    `8ad1d251+1` — rota que nunca abriu um pedido de desentupimento.
#    ("acompanhar é outro outcome" — `servico_ja_aberto`, corridor_playbooks.)
#
# 📊 Onde a tela aparece (`scratchpad/f3b/ident.py`, 29/09, 688 sessões):
#    30 vezes, TODAS na Allianz. Resposta "1" (Ver detalhes) 25 · "2" (Abrir
#    novo) 4 · outra 1. Depois do "1" vêm a lista de pedidos, o RESUMO do pedido
#    antigo e o menu de cancelar/remarcar — nunca uma tela de abertura.
#
# A JANELA DE CONSULTA:
#   abre   a corretora responde "Ver detalhes" à tela de pedido existente
#   fecha  a corretora escolhe "Abrir (um) novo atendimento" em qualquer menu
#          — daí em diante é abertura de novo, e volta a contar — ou a URA
#          anuncia a TRANSFERÊNCIA (`e_fronteira`): a fronteira é tela de
#          tronco (a mesma frase em dezenas de sessões) e fica; o que vem
#          depois já é zona HUMANO e nunca entrou no corpus
#   dentro tudo sai do corpus E da classificação, MENOS a tela que OFERECE
#          "Abrir (um) novo atendimento": ela é a PORTA por onde o corredor sai
#          (📊 `servico_aberto_ver_ou_abrir` responde "2" a ela), e é caminho do
#          corredor de abertura.
#
# ⚠️ Por que tira da CLASSIFICAÇÃO também, e não só do desfecho: com o RESUMO
#    antigo nos pares, o padrão-ouro rotula o atendimento pelo serviço
#    CONSULTADO, e as telas de abertura (CPF, endereço) entram numa rota que o
#    atendimento nunca pediu. 📊 `3db870e0+2`: consultou um ENCANADOR e as telas
#    do caminho pelo menu de AUTO entraram em `allianz/residencial/encanador`
#    como órfãs (87 % → 68 % na régua da F3).
# ═════════════════════════════════════════════════════════════════════════════
_RX_PEDIDO_EXISTENTE = re.compile(
    r"identifiquei que temos uma solicitac[a-z]{2,3} de servic[a-z]{1,2} feita")
_RX_VER_DETALHES = re.compile(r"^ver detalhes$")
_RX_ABRIR_NOVO = re.compile(r"abrir (?:um )?novo atendimento")
_RX_OPCAO = re.compile(r"(?m)^\s*(\d{1,2})\s*[-–]\s*(.+?)\s*;?\s*$")


def _rotulo_escolhido(tela_norm: str, resposta: str) -> str:
    """O RÓTULO que a resposta escolheu na tela (`"1"` → `"ver detalhes"`).

    Resposta que não é número volta normalizada — quem digita o rótulo escolheu
    o rótulo.
    """
    r = norm_para_classificar(resposta or "").strip().rstrip(".;")
    if re.fullmatch(r"\d{1,2}", r):
        for m in _RX_OPCAO.finditer(tela_norm or ""):
            if m.group(1) == r:
                return m.group(2).strip().rstrip(";").strip()
        return ""
    return r


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-123 F6 · A MESMA JANELA NA FAMÍLIA YELUM/HDI (o mesmo bot white-label)
#
# A família não tem "Ver detalhes": ela RECONHECE sozinha que a placa tem
# assistência recente e entra no acompanhamento por duas portas:
#
#   ① "identifiquei que a assistência *N* foi aberta dentro das últimas 72h.
#      Selecione abaixo sobre qual solicitação você quer falar: GUINCHO · MTA"
#      📊 yelum 75400aad (28/04). A tela FICA no corpus (é a PORTA, como a tela
#      "Identifiquei que temos uma solicitação" da Allianz): a janela abre na
#      RESPOSTA a ela. O corredor tem passo para ela (`acompanhar_qual_
#      solicitacao`, corridor_playbooks) — é por onde o caso chega a uma pessoa.
#   ② "A solicitação de *GUINCHO* está concluída. Por favor, selecione abaixo o
#      assunto que você deseja falar: (Pedir outro serviço ·) Questionar atraso ·
#      Questionar entrega · Alterar endereço · Outro…"
#      📊 yelum 75400aad, 859d185c · hdi 27939047, 4b2d0c2a, 4b2d0c2a+1. A tela
#      ABRE a janela e fica DENTRO dela: no produto ela já é gatilho de handoff
#      ("acompanhamento, não abertura", SPEC-120), nunca uma porta do corredor.
#
# ⛔ O que vem depois é conversa sobre o pedido ANTIGO: nem etiqueta, nem
#    desfecho. Fecha como na Allianz (fronteira) — ou quando a corretora pede
#    serviço NOVO ("Pedir outro serviço" / "abrir novo atendimento"), e daí em
#    diante é abertura e volta a contar.
#
# 📊 Controle (30/09, `scratchpad/f6`): a frase ① aparece SÓ em 75400aad e a ②
#    só nas 5 sessões acima, todas da família; a janela da Allianz não muda (as
#    duas regex não casam nenhuma tela da Allianz).
# ═════════════════════════════════════════════════════════════════════════════
_RX_ABERTA_NAS_72H = re.compile(r"foi aberta dentro das ultimas 72\s*h")
_RX_SOLICITACAO_CONCLUIDA = re.compile(r"a solicitac[a-z]{2,3} de .{3,40}? esta conclu")
_RX_PEDIR_NOVO_FAMILIA = re.compile(r"pedir outro servic|abrir (?:um )?novo atendimento")


def consulta_de_pedido_existente(eventos: List[Dict[str, Any]],
                                 seguradora: Optional[str] = None) -> set:
    """Os ÍNDICES de `eventos` (um atendimento, em ordem) que são CONSULTA.

    Devolve `in` e `out` da janela (blocos acima), menos a tela-PORTA. Vazio
    quando o atendimento não consultou nada — e aí o gerador faz exatamente o
    que fazia antes.

    Duas portas: a da Allianz ("Ver detalhes") e as da família Yelum/HDI
    (resposta à tela das 72h, ou a tela "a solicitação de X está concluída").
    """
    dentro: set = set()
    em_consulta = False
    familia = False          # a janela aberta é a da família (fecha com "Pedir outro serviço")
    ultima_tela = ""
    for i, e in enumerate(eventos):
        texto = e.get("text") or ""
        if e.get("direction") == "in":
            if not texto.strip():
                continue
            n = norm_para_classificar(texto)
            if em_consulta and seguradora and e_fronteira(seguradora, n):
                em_consulta = False
            if not em_consulta and _RX_SOLICITACAO_CONCLUIDA.search(n):
                em_consulta, familia = True, True
                dentro.add(i)
                ultima_tela = n
                continue
            if em_consulta and (familia or not _RX_ABRIR_NOVO.search(n)):
                dentro.add(i)
            ultima_tela = n
            continue
        if e.get("direction") != "out" or not texto.strip():
            continue
        escolhido = _rotulo_escolhido(ultima_tela, texto)
        if not em_consulta:
            if (_RX_PEDIDO_EXISTENTE.search(ultima_tela)
                    and _RX_VER_DETALHES.search(escolhido)):
                em_consulta, familia = True, False
            elif (_RX_ABERTA_NAS_72H.search(ultima_tela)
                    and not _RX_PEDIR_NOVO_FAMILIA.search(escolhido)):
                em_consulta, familia = True, True
            continue
        if (_RX_PEDIR_NOVO_FAMILIA if familia else _RX_ABRIR_NOVO).search(escolhido):
            em_consulta = False
            continue
        dentro.add(i)
    return dentro


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
