# -*- coding: utf-8 -*-
"""O SIMULADOR DE CORREDOR — SPEC-119 F4, bateria 2 (e a 5 por rota).

> ## Casar a tela não é responder certo. E a lista por rota tem de dizer as duas coisas.

```bash
python backend/scripts/simular_corredor.py --todas
python backend/scripts/simular_corredor.py --todas --formato markdown \
    --gravar docs/canon/reports/SIMULACAO-DOS-CORREDORES.md
python backend/scripts/simular_corredor.py --seguradora allianz --ramo auto --servico guincho --detalhado
python backend/scripts/simular_corredor.py --bateria-5
```

Cada rota (seguradora × ramo × serviço) é atravessada com as telas **REAIS** do
corpus versionado, tela a tela, e cada passo responde as **DUAS** perguntas do
CLAUDE.md §9.5:

```
(a) o passo CASOU a tela?              -> `replay.py`, que já é o motor
(b) e a RESPOSTA está confirmada?      -> `conferir_respostas.py`, que já são as três
     A · o slot tem origem?                      passo que fica CALADO
     B · a constante está na tela?               rótulo que a URA rejeita · tecla que decide pelo cliente
     C · o passo é do ofício da tela?            passo de um ofício respondendo tela de outro
```

## 🔴 ESTE ARQUIVO NÃO IMPLEMENTA NENHUMA DAS DUAS PERGUNTAS

Ele **não tem um regex sobre tela** e **não tem uma definição de defeito**. As duas
já existem no repositório, e reescrevê-las aqui seria o defeito nº 1 deste projeto
(CLAUDE.md §5, *"consolidar e migrar antes de duplicar"*) na sua forma mais barata:

```
(a) `scripts/replay.py`             SPEC-083 §3.3 — a única medida que reproduziu
(b) `scripts/conferir_respostas.py` P-084-14 — as três perguntas, cada uma nascida
                                    de um defeito que as outras duas não pegam
```

📊 **O que faltava, medido em 27/09/2026:** `conferir_respostas.Achado` **não
carrega o serviço** — ele é por `(seguradora, ramo)`. `conferir_respostas.py
--todas` devolve ZERO desde a SPEC-085, e ainda assim o Founder não consegue ler
a linha *"allianz × residencial × encanador atende sozinho?"* em nenhum lugar.
🔴 **O que este arquivo acrescenta é a ROTA, e nada mais.**

E a atribuição do achado à rota é feita **pelo MOTOR**, não por string: para cada
tela da rota, `match_ura_step(playbook, tela, subservice=<serviço da rota>)` diz
qual passo responde ali; se esse par (passo, tela) está no índice de achados, o
achado é daquela rota. ⚠️ Comparar nomes de passo sem rodar o motor mediria o
playbook, não o corredor (CLAUDE.md §9.4).

## AS TRÊS FAIXAS, e a ordem em que se decide

```
①  o corpus não tem UMA tela desta rota                 FALTA CAPTURA  sem_corpus
②  o desenho do produto ENCAMINHA (link, formulário)    HANDOFF        por_desenho_link
③  a rota tem tela de CONDOMÍNIO/EMPRESA ou SINISTRO
   que o produto NÃO manda para gente                   HANDOFF        bateria_5_furada
④  ≥ 1 achado GRAVE em A, B ou C                        HANDOFF        defeito_de_resposta
⑤  ≥ 1 tela ÓRFÃ FUNCIONAL (pede algo, ninguém responde) FALTA CAPTURA  tela_orfa
⑥  nenhuma sessão chegou ao fim                         FALTA CAPTURA  sem_desfecho
⑦  o resto                                              ATENDE SOZINHO —
```

🔴 **④ vem antes de ⑤ de propósito, e é a lição do CLAUDE.md §9.5:** *"Um passo que
trava é barulhento; um passo que responde errado é silencioso e chega ao cliente."*
Quando a rota tem os dois, o motivo que o Founder tem de ler primeiro é o da
resposta errada.

⚠️ **As faixas são três porque a SPEC-119 §5 F4 pediu três** — e a `causa` existe
para que `HANDOFF` não volte a ser um rótulo que junta coisas opostas (o que a §5
F5 chama de *"a coluna mentirosa"*). `HANDOFF por_desenho_link` é o produto certo:
a Tokio entrega link, e isso já é handoff pela SPEC-118. `HANDOFF
defeito_de_resposta` é uma rota que **tem conserto**. Misturar os dois foi o
defeito que esta SPEC existe para desfazer.

💭 As alternativas, pontuadas: (a) quatro faixas, com DEFEITO separado — 74, cria
vocabulário que a SPEC não pediu e a aba do painel não tem; (b) três faixas sem
`causa` — 40, é a coluna mentirosa de novo; (c) três faixas + `causa` obrigatória
— **90**.

## 🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2)

`--controle` roda o simulador contra quatro corredores SINTÉTICOS montados sobre
**telas reais do corpus**: um limpo (tem de sair **sem achado nenhum**) e três com
UM defeito plantado cada — A, B e C. Sem o limpo, um acerto se credita ao lugar
errado; sem os três, o conferidor pode estar mudo por estar quebrado.

## O que este arquivo NÃO faz

```
⛔ não chama modelo nenhum (OpenAI/Anthropic) — é corpus + motor, offline
⛔ não lê o banco: `observed_events` é da coluna DEMANDA, que é da F5
⛔ não decide nota: quem dá nota é `medir_rota.py`. Aqui a pergunta é
   "DÁ PARA LIGAR?", que é binária de propósito (SPEC-119 §5 F5③)
```
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conferir_respostas as CR   # noqa: E402  — as TRÊS perguntas (b)
import regua_motor as M           # noqa: E402  — o motor do produto
import replay as RP               # noqa: E402  — a pergunta (a)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIXA_ATENDE = "ATENDE SOZINHO"
FAIXA_HANDOFF = "HANDOFF"
FAIXA_FALTA_CAPTURA = "FALTA CAPTURA"


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=RAIZ, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 BATERIA 5 — CONDOMÍNIO · EMPRESARIAL · SINISTRO NUNCA SÃO TENTADOS SOZINHOS
# ═════════════════════════════════════════════════════════════════════════════
#
# O Founder, 27/09/2026, pedido explícito (SPEC-119 §5, F4 bateria 5): estes três
# **vão a uma pessoa, com o dossiê completo e em português**.
#
# 🔴 E A DISTINÇÃO QUE CUSTARIA QUATRO ROTAS SE EU NÃO A TIVESSE MEDIDO:
#
# 📊 Medido em 27/09/2026 sobre os 16 corpora versionados (o comando está no
#    relatório da F4a). A palavra "condomínio" aparece em DUAS telas que não têm
#    nada a ver uma com a outra::
#
#    ① A APÓLICE — é a do Founder, e decide a COBERTURA
#       "Qual seguro deseja utilizar?  1 - Residencial: para sua casa ou
#        apartamento individual   2 - Condomínio: para áreas comuns e estrutura
#        do condomínio   3 - Empresarial: para proteger seu negócio"
#       allianz-residencial, sessão c6b63f95 · 📊 37 sessões no acervo
#
#    ② O PRÉDIO — é uma pergunta de LOGÍSTICA, e NÃO é a do Founder
#       "Sua residência é uma casa individual ou está localizada em um
#        condomínio?  Botão 1: Casa   Botão 2: Condomínio"
#       hdi-residencial 26c0546f · yelum-residencial af3b817e · 📊 4 sessões
#
#    🔴 Um apartamento é "condomínio" na ② e **Residencial** na ①. Mandar a ②
#       para uma pessoa tiraria do ar `hdi/residencial/*` e `yelum/residencial/*`
#       inteiros — quatro rotas que hoje atendem — para proteger um caso que não
#       existe. ⚠️ É por isso que este bloco casa a ① e **não** casa a ②, e é por
#       isso que a distinção está escrita aqui e não só no commit.
#
# 🔴 E O SINISTRO TEM A MESMA ARMADILHA, com um preço medido no produto:
#    `corridor_playbooks.py:3603` registra que o gatilho `sinistro` CRU derrubava
#    *"mais da metade das sessões boas"* — porque menus reais LISTAM "Sinistro"
#    como opção (Porto opção 6, Bradesco 2) e isso não significa que o caso é
#    sinistro. Aqui só entra a tela em que a URA **pede alguma coisa SOBRE** o
#    sinistro: abrir, comunicar, preencher o formulário dele.
#
# ⚠️ Os padrões rodam sobre `_norm` (CLAUDE.md §9.4, o dialeto): sem acento, sem
#    `*`, minúsculo. Um padrão com `necessário` acentuado perderia metade do
#    acervo; um que exigisse `*sinistro*` perderia tudo.
_SITUACOES_QUE_VAO_PARA_GENTE: Dict[str, Tuple[str, str]] = {
    # chave: (padrão sobre `_norm`, a frase que uma PESSOA lê)
    "apolice_de_condominio_ou_empresa": (
        # ① a tela que ESCOLHE a apólice — as três opções juntas, nesta ordem
        r"qual seguro deseja utilizar\?[\s\S]{0,160}condominio:?[\s\S]{0,120}empresarial"
        # a porta do galho: o CNPJ do titular pedido para áreas comuns
        r"|exclusivamente (?:destinados? [a]s|a servicos nas) [a]reas comuns"
        # e o aviso de cobertura do galho, que só existe dentro dele
        r"|servicos sao exclusivamente destinados",
        "a seguradora está pedindo para escolher entre a apólice residencial, a de "
        "condomínio e a empresarial — e condomínio e empresa cobrem áreas comuns, "
        "não a unidade do segurado",
    ),
    # 🔴 A PRIMEIRA VERSÃO DESTE PADRÃO TINHA `sinistro de automovel`, E ELE ERA
    #    UM FALSO POSITIVO — medido em 27/09/2026, e é a mesma armadilha que
    #    `corridor_playbooks.py:3603` já documentava no produto.
    #
    #    📊 `sinistro de automovel` casava o MENU RAIZ da Porto em 4 rotas
    #       (bateria/chaveiro/guincho/tecnico, sessões 67296ad9, d0d64bfc,
    #       a9560e3a, b1ff65f2): *"Como eu posso te ajudar? Serviços para veículo
    #       … Sinistro de automóvel …"*. Ali "sinistro" é o RÓTULO DE UMA OPÇÃO
    #       VIZINHA, e o passo `menu_como_ajudar` responde "Serviços para veículo"
    #       — que é o oposto de abrir sinistro pelo cliente, e o próprio passo diz
    #       isso em `constante_justificada`.
    #
    #    🔴 Quatro rotas que atendem sairiam do ar por um padrão meu. O que entra
    #       aqui é só a tela em que a URA pede alguma coisa SOBRE o sinistro.
    "sinistro": (
        r"abrir (?:um )?sinistro"
        r"|comunicar (?:o )?sinistro|comunique seu sinistro"
        r"|conseguiu comunicar o seu sinistro"
        r"|preencher o formulario\*? de sinistro|formulario de sinistro"
        r"|abertura de \*?sinistro"
        r"|avisar ou acompanhar um sinistro",
        "a conversa entrou em sinistro — abrir, comunicar ou preencher formulário "
        "de sinistro é trabalho de uma pessoa, sempre",
    ),
}

#: 🔴 O CONTROLE do bloco acima, e ele é uma tela REAL, não um negativo abstrato.
#: A pergunta de LOGÍSTICA ("casa ou condomínio/prédio?") tem de sair de fora: se
#: um dia ela entrar, quatro rotas que atendem hoje param. O guarda de bateria 5
#: afirma isto por medição, com o `session_id` ao lado.
_CONTROLE_NAO_E_A_APOLICE = (
    r"residencia (?:e|é) uma casa individual ou esta localizada em um condominio"
    r"|sua residencia (?:e|é) uma casa ou fica em um condominio")


def situacao_que_vai_para_gente(texto: str) -> Optional[Tuple[str, str]]:
    """`("sinistro", "a frase em português")` — ou `None`.

    🔴 Sobre `M._norm`, que é o mesmo normalizador que o motor usa para casar
    âncora. Medir num texto e aplicar noutro é o §9.4 do CLAUDE.md.
    """
    n = M._norm(texto)
    if re.search(_CONTROLE_NAO_E_A_APOLICE, n, re.IGNORECASE):
        # a pergunta do PRÉDIO, não a da apólice — ver o bloco acima
        return None
    for chave, (padrao, frase) in _SITUACOES_QUE_VAO_PARA_GENTE.items():
        if re.search(padrao, n, re.IGNORECASE | re.DOTALL):
            return chave, frase
    return None


#: 🔴 OS SLOTS DO CASO QUE FAZEM A PERGUNTA SER A DO FOUNDER — e sem eles o guarda
#: não teria como ficar vermelho (CLAUDE.md §9.3).
#:
#: 📊 Medido em 27/09/2026: com `slots={}`, a tela que escolhe a apólice cai em
#:    `ramo_indeterminado` (tecla vazia → uma pessoa) **em qualquer versão do
#:    código**, inclusive na que respondia "2" sozinha. O guarda ficaria verde por
#:    motivo errado, que é o defeito nº 1 da SPEC-118.
#:
#: 🔴 A pergunta da bateria 5 só existe quando a apólice É de condomínio. O valor
#:    é o que `new_dispatch_session` escreve de verdade
#:    (`rotulo_do_ramo_da_apolice` → `_ROTULO_DO_RAMO["cond"]`), não um inventado.
_CASO_DE_CONDOMINIO = {"qual_seguro_opcao": "Condomínio"}

_SLOTS_DA_SITUACAO: Dict[str, Dict[str, Any]] = {
    "apolice_de_condominio_ou_empresa": _CASO_DE_CONDOMINIO,
}


def o_produto_manda_para_gente(pb: Dict[str, Any], texto: str,
                               servico: Optional[str] = None,
                               slots: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """O PRODUTO manda esta tela para uma pessoa? `(sim/não, por qual caminho)`

    🔴 Pelas funções do produto e na ORDEM do produto (`handle_insurer_message`):
    um passo que casa responde ANTES do gatilho de handoff, então um gatilho que
    existe "atrás" de um passo não protege ninguém. É exatamente o furo que a
    bateria 5 procura.

    Os três caminhos legítimos, todos do motor:

    ```
    passo que NÃO responde      `noop` sem resposta, e nada sai
    gatilho de handoff          `detect_handoff_trigger`
    a tecla vai a uma pessoa    `resolver_tecla(...)["destino"] == "humano"`
    ```

    ⚠️ `slots` importa: é o CASO. Ver `_SLOTS_DA_SITUACAO`.
    """
    passo = M.match_ura_step(pb, texto, subservice=servico)
    if passo is not None:
        # a TECLA é conferida contra a tela real — e ela pode mandar a uma pessoa
        sessao = {"slots": dict(slots or {}), "origem_das_teclas": {}}
        try:
            tecla = M.IDS.resolver_tecla(pb, passo, sessao, texto)
        except Exception:  # noqa: BLE001 — o simulador nunca derruba por borda
            tecla = None
        if tecla is not None and tecla.get("destino") == "humano":
            return True, f"a tecla do passo `{passo.get('step')}` vai a uma pessoa " \
                         f"({tecla.get('reason')})"
        if passo.get("noop") and not str(passo.get("reply") or "").strip():
            return True, f"o passo `{passo.get('step')}` é `noop`: o robô não " \
                         f"responde nada nesta tela"
        return False, f"o passo `{passo.get('step')}` responde " \
                      f"{str(passo.get('reply'))!r} sozinho"
    gatilho = M.detect_handoff_trigger(pb, texto)
    if gatilho:
        return True, f"gatilho de handoff `{gatilho}`"
    classe = M.IDS.classe_da_tela(pb, texto, slots=dict(slots or {}))
    if classe.get("handoff"):
        return True, f"tela desconhecida de aposta alta ({classe.get('chave')})"
    return False, "nenhum passo casa e nenhum gatilho dispara — a tela vai para o " \
                  "caminho adaptativo, que não é uma pessoa"


# ═════════════════════════════════════════════════════════════════════════════
# (b) A RESPOSTA ESTÁ CONFIRMADA? — atribuída À ROTA, pelo motor
# ═════════════════════════════════════════════════════════════════════════════

def indice_de_achados(seguradora: str, ramo: str,
                      derivados: Set[str]) -> Dict[Tuple[str, str], List[Any]]:
    """`{(passo, tela_normalizada[:60]): [Achado, ...]}` para (seguradora, ramo).

    🔴 A chave é a MESMA que `conferir_respostas.conferir` usa para não repetir
    achado (`(nome, M._norm(texto)[:60])`). Ela é copiada de lá de propósito:
    duas chaves diferentes fariam a atribuição perder achado em silêncio — e o
    silêncio é o defeito que este projeto mais paga.
    """
    fora: Dict[Tuple[str, str], List[Any]] = collections.defaultdict(list)
    for a in CR.conferir(seguradora, ramo, derivados):
        fora[(a.passo, M._norm(a.tela)[:60])].append(a)
    return fora


def achados_da_rota(rota, telas: List[Any], pb: Dict[str, Any],
                    indice: Dict[Tuple[str, str], List[Any]]) -> List[Any]:
    """Os achados A/B/C que caem NESTA rota — perguntando ao MOTOR quem responde.

    ⚠️ `CR.conferir` roda sobre o corpus inteiro de (seguradora, ramo), incluindo
    as telas de sessão NÃO CLASSIFICADA, que não são de rota nenhuma. Um achado
    que não casa rota nenhuma **não desaparece**: ele sai na linha
    `fora de rota` do relatório (`achados_fora_de_rota`).
    """
    fora: List[Any] = []
    vistos: Set[Tuple[str, str, str]] = set()
    for t in telas:
        passo = M.match_ura_step(pb, t.texto, subservice=rota.servico)
        if not passo:
            continue
        chave = (str(passo.get("step") or "?"), M._norm(t.texto)[:60])
        for a in indice.get(chave, []):
            marca = (a.regra, a.passo, a.porque)
            if marca in vistos:
                continue
            vistos.add(marca)
            fora.append(a)
    return fora


# ═════════════════════════════════════════════════════════════════════════════
# A SIMULAÇÃO DE UMA ROTA
# ═════════════════════════════════════════════════════════════════════════════

class Desfecho(NamedTuple):
    """Chegou ao fim? E em QUAL sessão — a SPEC-119 G2 exige o nome dela."""

    chegou: bool
    como: str
    sessoes: List[str]


class Simulacao(NamedTuple):
    rota: Any
    replay: Any
    achados: List[Any]
    desfecho: Desfecho
    situacoes: List[Tuple[str, str, str, bool, str]]  # chave, ses, tela, vai?, caminho
    faixa: str
    causa: str
    motivo: str

    @property
    def graves(self) -> List[Any]:
        return [a for a in self.achados if a.grave]

    @property
    def por_regra(self) -> Dict[str, int]:
        return dict(collections.Counter(a.regra for a in self.graves))

    @property
    def situacoes_furadas(self) -> List[Tuple[str, str, str, bool, str]]:
        return [s for s in self.situacoes if not s[3]]


def _desfecho(pb: Dict[str, Any], rota, telas: List[Any]) -> Desfecho:
    """A rota chegou ao fim pelo menos UMA vez? Pelas funções do produto.

    Três formas de "fim", e a que vale depende do DESENHO da rota:

    ```
    protocolo capturado    `extract_capture_anchors` devolve algo
    a URA vai CONFIRMAR    `detect_finalize_anchor` casa (o freio do corredor)
    o encaminhamento       `detect_referral_step` casa — a rota `encaminha` de
                           propósito (Tokio é link, SPEC-118), e o link É o fim
    ```
    """
    protocolo = [t.session_id for t in telas if M.extract_capture_anchors(pb, t.texto)]
    if protocolo:
        return Desfecho(True, "a seguradora devolveu protocolo/agendamento",
                        sorted(set(protocolo)))
    finaliza = [t.session_id for t in telas if M.detect_finalize_anchor(pb, t.texto)]
    if finaliza:
        return Desfecho(True, "a URA chegou à tela que CONFIRMA a abertura",
                        sorted(set(finaliza)))
    if str(M.CP.subservice_outcome(pb, rota.servico) or "") == M.CP.OUTCOME_ENCAMINHA:
        encaminha = [t.session_id for t in telas
                     if M.CP.detect_referral_step(pb, t.texto)]
        if encaminha:
            return Desfecho(True, "a seguradora entregou o link/formulário, que é o "
                                  "fim desta rota por desenho", sorted(set(encaminha)))
    return Desfecho(False, "nenhuma sessão do corpus chegou ao protocolo, à "
                           "confirmação ou ao encaminhamento", [])


def _faixa(rota, rp, achados: List[Any], desfecho: Desfecho,
           situacoes: List[Tuple[str, str, str, bool, str]],
           pb: Dict[str, Any]) -> Tuple[str, str, str]:
    """`(faixa, causa, motivo em português)` — a tabela de decisão da docstring."""
    graves = [a for a in achados if a.grave]
    furadas = [s for s in situacoes if not s[3]]

    # ① sem uma tela no corpus, não há nada a afirmar
    if not rp.telas:
        return (FAIXA_FALTA_CAPTURA, "sem_corpus",
                "o acervo não tem UMA conversa desta rota. Não é que o robô falhe: "
                "ninguém nunca ligou para esta seguradora pedindo este serviço "
                "pelo WhatsApp da corretora (ou o classificador não soube etiquetar "
                "a conversa que existe)")

    # ② o desenho ENCAMINHA — é o produto certo, não um defeito
    if str(M.CP.subservice_outcome(pb, rota.servico) or "") == M.CP.OUTCOME_ENCAMINHA:
        return (FAIXA_HANDOFF, "por_desenho_link",
                "esta seguradora não abre o chamado pela conversa: ela devolve um "
                "link ou um formulário. O robô entrega o link e o caso segue com "
                "uma pessoa — é o desenho, não uma falha")

    # ③ condomínio · empresarial · sinistro que o produto NÃO manda para gente
    if furadas:
        chave, ses, tela, _, caminho = furadas[0]
        frase = _SITUACOES_QUE_VAO_PARA_GENTE[chave][1]
        return (FAIXA_HANDOFF, "bateria_5_furada",
                f"{frase}. E hoje o robô NÃO para aqui: {caminho} "
                f"(conversa {ses})")

    # ④ a resposta errada vem antes da resposta que falta (CLAUDE.md §9.5)
    if graves:
        a = graves[0]
        return (FAIXA_HANDOFF, "defeito_de_resposta",
                f"o robô responde a tela e responde ERRADO em {len(graves)} "
                f"ponto(s). O primeiro: no passo `{a.passo}`, {a.porque}")

    # ⑤ tela que pede algo e ninguém responde
    if rp.orfas_funcionais:
        t = rp.orfas_funcionais[0]
        return (FAIXA_FALTA_CAPTURA, "tela_orfa",
                f"{len(rp.orfas_funcionais)} tela(s) desta rota pedem alguma coisa e "
                f"o robô não tem resposta escrita para elas. A primeira, na conversa "
                f"{t.session_id}: “{' '.join(t.texto.split())[:110]}”")

    # ⑥ nunca chegou ao fim
    if not desfecho.chegou:
        return (FAIXA_FALTA_CAPTURA, "sem_desfecho",
                f"o robô responde todas as telas que o acervo mostra, mas "
                f"{desfecho.como} — então não há prova de que esta rota vá até o "
                f"protocolo. Falta uma conversa que termine")

    # ⑦
    return (FAIXA_ATENDE, "",
            f"todas as {rp.pedem_algo} telas que pedem algo são respondidas, "
            f"nenhuma resposta decide pelo segurado sem evidência, e "
            f"{desfecho.como} em {len(desfecho.sessoes)} conversa(s) — "
            # 🔴 G2 da SPEC-119: *"com a sessão nomeada"*. Um "sim" sem o nome da
            #    conversa não é verificável, e foi o que fez o Founder acreditar
            #    por meses num 72 que era o mesmo número repetido em 10 linhas.
            f"a primeira é `{desfecho.sessoes[0]}`")


def simular(rota, *, indice: Optional[Dict[Tuple[str, str], List[Any]]] = None,
            derivados: Optional[Set[str]] = None) -> Simulacao:
    """A rota atravessada tela a tela, com as DUAS perguntas do §9.5."""
    pb = M.get_playbook(rota.ref) or {}
    rp = RP.replay(rota)
    if indice is None:
        indice = indice_de_achados(rota.seguradora, rota.ramo,
                                   derivados if derivados is not None
                                   else CR._slots_derivados())
    achados = achados_da_rota(rota, rp.telas, pb, indice)
    desf = _desfecho(pb, rota, rp.telas)

    situacoes: List[Tuple[str, str, str, bool, str]] = []
    vistas: Set[Tuple[str, str]] = set()
    for t in rp.telas:
        sit = situacao_que_vai_para_gente(t.texto)
        if not sit:
            continue
        chave = (sit[0], M._norm(t.texto)[:60])
        if chave in vistas:
            continue
        vistas.add(chave)
        vai, caminho = o_produto_manda_para_gente(
            pb, t.texto, rota.servico, slots=_SLOTS_DA_SITUACAO.get(sit[0]))
        situacoes.append((sit[0], t.session_id, " ".join(t.texto.split()), vai, caminho))

    faixa, causa, motivo = _faixa(rota, rp, achados, desf, situacoes, pb)
    return Simulacao(rota, rp, achados, desf, situacoes, faixa, causa, motivo)


def simular_todas(rotas: Optional[List[Any]] = None) -> List[Simulacao]:
    """As 73 rotas — com UM `conferir_respostas` por (seguradora, ramo), não por rota."""
    derivados = CR._slots_derivados()
    indices: Dict[Tuple[str, str], Dict[Tuple[str, str], List[Any]]] = {}
    fora: List[Simulacao] = []
    for rota in (rotas if rotas is not None else M.rotas()):
        chave = (rota.seguradora, rota.ramo)
        if chave not in indices:
            indices[chave] = indice_de_achados(rota.seguradora, rota.ramo, derivados)
        fora.append(simular(rota, indice=indices[chave], derivados=derivados))
    return fora


def achados_fora_de_rota(sims: List[Simulacao]) -> List[Any]:
    """Os achados de (seguradora, ramo) que NENHUMA rota reivindicou.

    🔴 Existe porque *"truncar calado lê-se como 'cobrimos tudo'"* (SPEC-083 §7).
    Um achado numa tela de sessão não classificada é real; ele só não tem rota.
    """
    derivados = CR._slots_derivados()
    reivindicados = {(a.regra, a.passo, a.porque) for s in sims for a in s.achados}
    fora: List[Any] = []
    for seg, ramo in sorted({(s.rota.seguradora, s.rota.ramo) for s in sims}):
        for a in CR.conferir(seg, ramo, derivados):
            if (a.regra, a.passo, a.porque) not in reivindicados:
                fora.append(a)
    return fora


# ═════════════════════════════════════════════════════════════════════════════
# AS SAÍDAS
# ═════════════════════════════════════════════════════════════════════════════

def _cabecalho() -> List[str]:
    return [f"> gerado em {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}"
            f" · commit `{_commit()}` · corpus `backend/tests/corpus/telas_reais/`",
            "",
            "🔴 **Offline por construção:** corpus versionado + motor do produto. "
            "Nenhum modelo foi chamado, nenhum `observed_events` foi lido.",
            ""]


def tabela(sims: List[Simulacao]) -> str:
    L = ["=== O SIMULADOR DE CORREDOR (SPEC-119 F4 · bateria 2) ==="]
    L += _cabecalho()
    L.append(f"{'rota':44s} {'telas':>5s} {'resp':>5s} {'orfa':>4s} "
             f"{'A':>2s} {'B':>2s} {'C':>2s} {'fim':>3s}  faixa")
    for s in sims:
        g = s.por_regra
        L.append(f"{str(s.rota):44s} {len(s.replay.telas):5d} {s.replay.respondidas:5d} "
                 f"{len(s.replay.orfas_funcionais):4d} "
                 f"{g.get('A', 0):2d} {g.get('B', 0):2d} {g.get('C', 0):2d} "
                 f"{('sim' if s.desfecho.chegou else '—'):>3s}  "
                 f"{s.faixa}" + (f" ({s.causa})" if s.causa else ""))
    L.append("")
    contagem = collections.Counter(s.faixa for s in sims)
    for faixa in (FAIXA_ATENDE, FAIXA_HANDOFF, FAIXA_FALTA_CAPTURA):
        L.append(f"  {faixa:16s} {contagem.get(faixa, 0):3d} de {len(sims)}")
    por_causa = collections.Counter(s.causa for s in sims if s.causa)
    L.append("  causas: " + " · ".join(f"{k}={v}" for k, v in sorted(por_causa.items())))
    # 🔴 SPEC-083 §7: *"truncar calado lê-se como 'cobrimos tudo'"*. O achado que
    #    nenhuma rota reivindicou é REAL — ele só não tem rota, porque a tela em que
    #    acontece foi etiquetada com OUTRO serviço. Sem esta linha, a soma
    #    `A=0 B=0 C=0` na coluna de cada rota leria-se como "o conferidor está mudo".
    orfaos = achados_fora_de_rota(sims)
    L.append(f"  achados do conferidor FORA de rota: {len(orfaos)}")
    for a in orfaos:
        L.append(str(a))
    return "\n".join(L)


def markdown(sims: List[Simulacao]) -> str:
    contagem = collections.Counter(s.faixa for s in sims)
    L = ["# A simulação dos corredores — a lista por rota",
         ""]
    L += _cabecalho()
    L += ["Cada rota foi atravessada com as **telas reais** do acervo, tela a tela, "
          "e cada passo respondeu às duas perguntas do `CLAUDE.md` §9.5: *o passo "
          "casou a tela?* **e** *a resposta está confirmada?*",
          "",
          "| faixa | rotas | o que significa |",
          "|---|---:|---|",
          f"| **{FAIXA_ATENDE}** | {contagem.get(FAIXA_ATENDE, 0)} | o robô "
          "responde tudo o que o acervo mostra, sem decidir pelo segurado, e já "
          "chegou ao protocolo pelo menos uma vez |",
          f"| **{FAIXA_HANDOFF}** | {contagem.get(FAIXA_HANDOFF, 0)} | vai a uma "
          "pessoa — por desenho (a seguradora só dá link) ou porque ainda responde "
          "algo errado |",
          f"| **{FAIXA_FALTA_CAPTURA}** | {contagem.get(FAIXA_FALTA_CAPTURA, 0)} | "
          "falta conversa: ou o acervo não tem nenhuma, ou tem uma tela sem "
          "resposta escrita, ou nenhuma chegou ao fim |",
          ""]
    for faixa in (FAIXA_ATENDE, FAIXA_HANDOFF, FAIXA_FALTA_CAPTURA):
        doface = [s for s in sims if s.faixa == faixa]
        L += [f"## {faixa} — {len(doface)} rota(s)", ""]
        if not doface:
            L += ["_nenhuma._", ""]
            continue
        L += ["| rota | telas | respondidas | órfãs | A | B | C | chegou ao fim | por quê |",
              "|---|---:|---:|---:|---:|---:|---:|:---:|---|"]
        for s in doface:
            g = s.por_regra
            motivo = s.motivo
            L.append(f"| `{s.rota.seguradora}/{s.rota.ramo}/{s.rota.servico}` | "
                     f"{len(s.replay.telas)} | {s.replay.respondidas} | "
                     f"{len(s.replay.orfas_funcionais)} | {g.get('A', 0)} | "
                     f"{g.get('B', 0)} | {g.get('C', 0)} | "
                     f"{'sim' if s.desfecho.chegou else 'não'} | {motivo} |")
        L.append("")
    orfaos = achados_fora_de_rota(sims)
    L += ["## Os achados que NENHUMA rota reivindicou", "",
          "🔴 *“truncar calado lê-se como ‘cobrimos tudo’”* (SPEC-083 §7). Estes "
          "achados do conferidor são reais — eles só não têm rota, porque a tela em "
          "que acontecem foi etiquetada com **outro** serviço, e o motor não casa "
          "aquele passo para o serviço da rota. Eles não entram na faixa de nenhuma "
          "rota, e é por isso que aparecem aqui.", ""]
    if not orfaos:
        L += ["_nenhum._", ""]
    else:
        L += ["| regra | seguradora | ramo | passo | por quê |", "|---|---|---|---|---|"]
        for a in orfaos:
            L.append(f"| {'🔴' if a.grave else '⚠️'} {a.regra} | {a.seguradora} | "
                     f"{a.ramo} | `{a.passo}` | {a.porque} |")
        L.append("")
    fura = [(s, x) for s in sims for x in s.situacoes]
    L += ["## Bateria 5 — condomínio · empresarial · sinistro", ""]
    if not fura:
        L += ["_nenhuma tela destes três assuntos no acervo das rotas._", ""]
    else:
        L += ["| rota | assunto | conversa | vai para uma pessoa? | por qual caminho |",
              "|---|---|---|:---:|---|"]
        for s, (chave, ses, _tela, vai, caminho) in fura:
            L.append(f"| `{s.rota.seguradora}/{s.rota.ramo}/{s.rota.servico}` | "
                     f"{chave} | `{ses}` | {'sim' if vai else '🔴 **NÃO**'} | "
                     f"{caminho} |")
        L.append("")
    return "\n".join(L)


def detalhado(s: Simulacao) -> str:
    L = [RP.imprimir_detalhado(s.replay), "",
         f"  FAIXA ................... {s.faixa}" + (f" ({s.causa})" if s.causa else ""),
         f"  por quê ................. {s.motivo}",
         f"  chegou ao fim ........... {'sim' if s.desfecho.chegou else 'nao'} — "
         f"{s.desfecho.como}"
         + (f" (conversas {', '.join(s.desfecho.sessoes[:4])})" if s.desfecho.sessoes else "")]
    if s.achados:
        L.append("")
        L.append("  (b) A RESPOSTA ESTA CONFIRMADA? — os achados desta rota:")
        for a in s.achados:
            L.append(str(a))
    else:
        L.append("")
        L.append("  (b) A RESPOSTA ESTA CONFIRMADA? — nenhum achado nesta rota")
    if s.situacoes:
        L.append("")
        L.append("  bateria 5 — condominio/empresarial/sinistro nesta rota:")
        for chave, ses, tela, vai, caminho in s.situacoes:
            L.append(f"    {'OK ' if vai else '🔴 '}[{chave}] {ses}: {caminho}")
            L.append(f"        tela: {tela[:100]}")
    return "\n".join(L)


def como_json(sims: List[Simulacao]) -> str:
    return json.dumps([{
        "seguradora": s.rota.seguradora, "ramo": s.rota.ramo, "servico": s.rota.servico,
        "telas": len(s.replay.telas), "respondidas": s.replay.respondidas,
        "orfas_funcionais": len(s.replay.orfas_funcionais),
        "achados_graves": s.por_regra, "chegou_ao_fim": s.desfecho.chegou,
        "sessoes_de_desfecho": s.desfecho.sessoes,
        "faixa": s.faixa, "causa": s.causa, "motivo": s.motivo,
        "bateria_5": [{"assunto": c, "sessao": ses, "vai_para_gente": v,
                       "caminho": cm} for c, ses, _t, v, cm in s.situacoes],
    } for s in sims], ensure_ascii=False, indent=1)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 A LINHA DE CONTROLE — CLAUDE.md §9.2
# ═════════════════════════════════════════════════════════════════════════════
#
# *"A linha de controle é o que dá direito à conclusão."* Sem ela, um simulador
# que devolvesse "zero achados" por estar quebrado leria igual a um produto limpo.

class Controle(NamedTuple):
    nome: str
    pb: Dict[str, Any]
    tela: str
    servicos_da_tela: Set[str]   # os serviços em que o ACERVO viu esta tela
    esperada: Optional[str]      # a regra que TEM de acusar — None = nenhuma


def corredores_de_controle() -> List[Controle]:
    """Quatro corredores SINTÉTICOS sobre telas REAIS do acervo.

    ```
    limpo     ecoa um dado que o caso tem      -> ZERO achado   (o CONTROLE)
    A         slot que nada preenche           -> 1 achado A
    B         tecla que a tela não oferece      -> 1 achado B
    C         only_subservices de outro ofício  -> 1 achado C
    ```

    🔴 As telas vêm do acervo, nunca da imaginação (CLAUDE.md §9.4), e o playbook
    é montado com a MESMA forma dos playbooks do produto, para que
    `match_ura_step`, `origens_do_slot` e `decide_pelo_cliente` rodem sobre ele
    sem nenhum caminho especial.

    🔴 E a `C` EXIGE a terceira coluna. `match_ura_step` já respeita
    `only_subservices` — um passo restrito a `eletricista` **nunca** casa sob
    `encanador`. O defeito nº 1 do CLAUDE.md §9.5 não é "o passo casou o serviço
    errado": é *"o passo do eletricista casou uma tela que só aparece em sessões
    de OUTRO ofício"*. Quem sabe disso é o CORPUS, não o playbook — e foi
    justamente por não passar essa coluna que a primeira versão deste controle
    ficou verde com o defeito plantado (medido, 27/09/2026).
    """
    linhas = RP.carregar_corpus("allianz", "residencial")

    def _uma(padrao: str, so_de: Optional[str] = None,
             menu: bool = False) -> Tuple[str, Set[str]]:
        """A primeira tela real que casa `padrao`, com os serviços em que foi vista."""
        vistos: Dict[str, Set[str]] = collections.defaultdict(set)
        textos: Dict[str, str] = {}
        for l in linhas:
            k = M._norm(l["text"])[:60]
            textos[k] = l["text"]
            sv = l.get("servico")
            if sv and not str(sv).startswith("?"):
                vistos[k].add(str(sv))
        for k, texto in textos.items():
            if not re.search(padrao, M._norm(texto), re.IGNORECASE | re.DOTALL):
                continue
            if menu and len(M.IDS.opcoes_numeradas(texto)) < 3:
                continue
            if so_de is not None and vistos.get(k) != {so_de}:
                continue
            return texto, set(vistos.get(k) or ())
        return "", set()

    tela_menu, sv_menu = _uma(r"qual seguro deseja utilizar", menu=True)
    tela_livre, sv_livre = _uma(r"informe .{0,30}refer[e]ncia")
    # 📊 a tela do PET é vista SÓ em sessões de `consulta_veterinaria` — é ela que
    #    deixa a `C` ter como ficar vermelha (medido, allianz-residencial, 27/09).
    tela_pet, sv_pet = _uma(r"informe o endereco onde esta o pet",
                            so_de="consulta_veterinaria")
    base = {"insurer_key": "controle", "line_kind": "residencial",
            "subservices": {"encanador": {"required_slots": ["titular_cpf"]},
                            "eletricista": {"required_slots": ["titular_cpf"]},
                            "consulta_veterinaria": {"required_slots": ["titular_cpf"]}},
            "handoff_triggers": [], "finalize_anchors": [], "capture_anchors": {}}

    def pb(step: Dict[str, Any]) -> Dict[str, Any]:
        return {**base, "ura_steps": [step]}

    ancora_menu = r"qual seguro deseja utilizar"
    ancora_livre = r"informe .{0,30}refer[êe]ncia"
    ancora_pet = r"informe o endere[çc]o onde est[áa] o pet"
    return [
        Controle("limpo", pb({"step": "eco_do_cpf", "anchor": ancora_livre,
                              "reply": "{titular_cpf}"}), tela_livre, sv_livre, None),
        Controle("A · slot sem origem",
                 pb({"step": "fala_de_um_slot_que_ninguem_preenche",
                     "anchor": ancora_livre, "reply": "{numero_da_sorte}"}),
                 tela_livre, sv_livre, "A"),
        Controle("B · tecla que a tela nao oferece",
                 pb({"step": "responde_uma_tecla_inexistente",
                     "anchor": ancora_menu, "reply": "9"}), tela_menu, sv_menu, "B"),
        Controle("C · oficio errado",
                 pb({"step": "passo_do_eletricista", "anchor": ancora_pet,
                     "reply": "{titular_cpf}", "only_subservices": ["eletricista"]}),
                 tela_pet, sv_pet, "C"),
    ]


def relatorio_de_controle() -> Tuple[str, int]:
    """Roda os quatro e confere. Devolve `(texto, falhas)`."""
    derivados = CR._slots_derivados()
    L = ["=== 🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2) ===", "",
         "  limpo -> ZERO achado · A/B/C -> UM achado da regra, e da regra certa", ""]
    falhas = 0
    for c in corredores_de_controle():
        if not c.tela:
            L.append(f"  🔴 {c.nome}: a tela REAL não está no corpus — controle INVÁLIDO")
            falhas += 1
            continue
        regras = sorted(set(regras_acusadas(c.pb, c.tela, derivados, c.servicos_da_tela)))
        ok = (regras == []) if c.esperada is None else (regras == [c.esperada])
        L.append(f"  {'OK ' if ok else '🔴 '}{c.nome:36s} esperado "
                 f"{('nenhuma' if c.esperada is None else c.esperada):8s} "
                 f"saiu {regras or 'nenhuma'}")
        if not ok:
            falhas += 1
    L.append("")
    L.append(f"  {'OK — o controle dá direito à conclusão' if not falhas else f'🔴 {falhas} falha(s)'}")
    return "\n".join(L), falhas


def regras_acusadas(pb: Dict[str, Any], tela: str, derivados: Set[str],
                    servicos_da_tela: Optional[Set[str]] = None) -> List[str]:
    """As regras (A/B/C) que o CONFERIDOR DO PRODUTO acusa neste par (pb, tela).

    🔴 Nenhuma das três é definida aqui. `origens_do_slot` (A),
    `decide_pelo_cliente` + `opcoes_numeradas` (B) e o filtro `only_subservices`
    contra os serviços OBSERVADOS (C) são todos de `conferir_respostas.py` e do
    motor. Este helper existe para aplicá-las a um playbook SINTÉTICO — que é o
    que o corpus versionado não consegue oferecer, porque ele não tem defeito
    plantado (e é isso que torna a linha de controle possível).
    """
    regras: List[str] = []
    servicos = sorted(pb.get("subservices") or {})
    for servico in servicos:
        passo = M.match_ura_step(pb, tela, subservice=servico)
        if not passo or passo.get("noop"):
            continue
        reply = str(passo.get("reply") or "")
        # A — o slot tem origem? (a definição é do produto)
        if not passo.get("sem_chute"):
            for slot in CR._RX_SLOT.findall(reply):
                if not CR.origens_do_slot(pb, slot, derivados):
                    regras.append("A")
        # B — a constante está confirmada pela tela?
        if reply and "{" not in reply and not passo.get("constante_justificada"):
            ops = dict(M.IDS.opcoes_numeradas(tela))
            if reply.strip().isdigit() and ops and reply.strip() not in ops:
                regras.append("B")
            elif CR.decide_pelo_cliente(tela, reply):
                regras.append("B")
        # C — o passo é do ofício da TELA? (quem sabe é o corpus)
        restrito = passo.get("only_subservices")
        conhecidos = {s for s in (servicos_da_tela or set()) if s in servicos}
        if restrito and conhecidos and not (conhecidos & set(restrito)):
            regras.append("C")
    return regras


# ═════════════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--todas", action="store_true")
    p.add_argument("--seguradora")
    p.add_argument("--ramo")
    p.add_argument("--servico")
    p.add_argument("--formato", choices=("tabela", "markdown", "json"), default="tabela")
    p.add_argument("--detalhado", action="store_true")
    p.add_argument("--gravar", help="caminho, relativo à raiz do repositório")
    p.add_argument("--controle", action="store_true",
                   help="🔴 a linha de controle: o que TEM de falhar, e falha")
    p.add_argument("--bateria-5", action="store_true",
                   help="só condomínio · empresarial · sinistro")
    a = p.parse_args(argv)

    if a.controle:
        texto, falhas = relatorio_de_controle()
        print(texto)
        return 1 if falhas else 0

    if a.seguradora and a.ramo and a.servico:
        rota = M.rota_de(a.seguradora, a.ramo, a.servico)
        if rota is None:
            print(f"🔴 rota {a.seguradora}/{a.ramo}/{a.servico} não existe no produto")
            return 2
        sims = simular_todas([rota])
    else:
        sims = simular_todas()

    if a.bateria_5:
        furadas = [(s, x) for s in sims for x in s.situacoes if not x[3]]
        todas = [(s, x) for s in sims for x in s.situacoes]
        print("=== BATERIA 5 · condomínio · empresarial · sinistro ===")
        print(f"  telas destes assuntos nas rotas ....... {len(todas)}")
        print(f"  🔴 que o produto NÃO manda para gente .. {len(furadas)}")
        for s, (chave, ses, tela, _v, caminho) in todas:
            print(f"  {'OK ' if (s, (chave, ses, tela, _v, caminho)) not in furadas else '🔴 '}"
                  f"{str(s.rota):40s} [{chave}] {ses}")
            print(f"      {caminho}")
        return 1 if furadas else 0

    if a.detalhado:
        for s in sims:
            print(detalhado(s))
            print()
        return 0

    texto = {"tabela": tabela, "markdown": markdown,
             "json": lambda x: como_json(x)}[a.formato](sims)
    if a.gravar:
        destino = os.path.join(os.path.dirname(RAIZ), a.gravar) \
            if not os.path.isabs(a.gravar) else a.gravar
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write(texto + "\n")
        print(f"gravado: {destino}")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
