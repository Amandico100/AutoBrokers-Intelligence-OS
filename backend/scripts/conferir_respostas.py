# -*- coding: utf-8 -*-
"""🔴 O COMPARADOR CONTAVA CASAMENTO. AGORA ELE CONFERE A RESPOSTA — P-084-14.

> ## Um passo que responde ERRADO conta igual a um que responde certo.

📊 Foi isso que escondeu os SETE defeitos do BLOCO 1. Nenhum deles apareceu como
perda no `--comparar-com`, porque todos os sete **casavam a tela**:

```
allianz  o_que_aconteceu        respondia a tecla do ELETRICISTA na tela do ENCANADOR
allianz  aviso_fora_da_garantia respondia "1" onde 1 = "Ate 10 anos"
allianz  menu_qual_seguro       respondia "1" num menu onde 2 = Condominio
zurich   vidros_orientacao      casava o CARDAPIO e encerrava o caso
azul     menu_inicial           casava ZERO (nem aparecia)
azul     cor_menu               respondia "Outra cor", rotulo que nao esta na tela
tokio    (4 rotas)              prometiam protocolo numa seguradora que so da LINK
```

Os blocos 2 a 5 escrevem MUITO mais passo que o bloco 1. Cego, o comparador
esconderia mais sete.

## As tres perguntas, e por que sao tres

Cada uma nasceu de um defeito que as outras duas NAO pegariam:

```
A · SLOT SEM ORIGEM     nada preenche -> o passo fica CALADO (2min22 medidos)
B · CONSTANTE NAO CONFIRMADA PELA TELA
      · rotulo que nao esta na tela        -> a URA rejeita, o turno se perde
      · digito que escolhe ALTERNATIVA     -> o corredor decide POR ELE
C · OFICIO ERRADO       passo de um oficio respondendo a tela de outro
```

🔴 **A `C` existe porque o defeito nº 1 nao seria pego por nenhuma das outras.**
`o_que_aconteceu` tinha slot COM origem (A passa), respondia um slot e nao uma
constante (B nao se aplica), e nao roubava passo nenhum — a tela do encanador
estava ORFA. So a `C` ve: um passo `only_subservices=["eletricista"]` casando
uma tela que so aparece em sessoes de `encanador`.

## O que a `B` aceita como confirmacao

```
rotulo   o texto do rotulo APARECE na tela que o passo casa
digito   a tela tem a opcao N, E a opcao e de NAVEGACAO
         (continuar / voltar / sair / prosseguir / ...)
```

🔴 **Quando o digito escolhe uma ALTERNATIVA DE CONTEUDO — "Ate 10 anos" x "Mais
de 10 anos", "Residencial" x "Condominio" — a constante afirma um fato do
segurado, e o passo precisa dizer POR QUE em `constante_justificada`.**

Isso nao e burocracia: e a diferenca entre o corredor *navegar* e o corredor
*decidir pelo cliente*. As duas coisas parecem iguais no log.
"""

from __future__ import annotations

import ast
import collections
import os
import re
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M   # noqa: E402
import replay as RP       # noqa: E402


# ═════════════════════════════════════════════════════════════════════════════
# As opcoes de uma tela
# ═════════════════════════════════════════════════════════════════════════════
#
# 📊 As quatro formas medidas no acervo, e a razao de cada uma estar aqui:
#     "*1 -* Ate 10 anos"        allianz, alfa       (asterisco fora do numero)
#     "*1* - Recarga"            azul, zurich        (asterisco no numero)
#     "1 - Guincho (reboque)"    azul numerada 2025
#     "Botao 1: Sim"             yelum, hdi, porto   (botoes do WhatsApp)
#
# ⚠️ E o `_norm` COME os asteriscos antes de qualquer coisa. Estes padroes rodam
#    sobre o texto normalizado, entao nenhum deles procura `*`.
_OPCAO = re.compile(
    r"(?:^|\n|\s)(?:bot[aã]o\s*)?(\d{1,2})\s*(?:-|:|–)\s*([^\n|]{1,80})",
    re.IGNORECASE,
)

# 🔴 O VOCABULARIO DA NAVEGACAO — a lista que separa "andar" de "decidir".
#
# Uma opcao daqui nao afirma nada sobre o segurado: ela move o fluxo. Uma
# constante que escolhe uma delas e navegacao, e passa sem justificativa.
# Qualquer outra coisa e ALTERNATIVA DE CONTEUDO.
_NAVEGACAO = (
    "continuar", "voltar", "sair", "prosseguir", "seguir", "avancar", "proximo",
    "encerrar", "encerrar atendimento", "finalizar", "menu inicial", "menu principal",
    "ok", "confirmar", "confirmo", "novo atendimento", "outro servico",
    "nao entendi", "nao encontrei o assunto", "mais opcoes", "outros",
    "tudo certo", "nao, esta tudo correto", "sim", "nao",
)


def opcoes_da_tela(texto: str) -> Dict[str, str]:
    """`{"1": "ate 10 anos", "2": "mais de 10 anos"}` — pelo texto NORMALIZADO."""
    n = M._norm(texto)
    fora: Dict[str, str] = {}
    for m in _OPCAO.finditer(n):
        chave, rotulo = m.group(1), " ".join(m.group(2).split())
        # a PRIMEIRA ocorrencia manda: a URA repete o numero no corpo as vezes
        fora.setdefault(chave, rotulo)
    return fora


def opcoes_em_lista(texto: str) -> List[str]:
    """As opcoes que a URA manda como LISTA, sem numero e sem "Botao N:".

    📊 A forma, literal, do corpus da porto:

    ```
    Posso confirmar sua solicitacao?
    Sim
    Nao, alterar endereco
    Sair e nao agendar
    ```

    🔴 Sem isto, a `B` nao teria como ver que `confirmar_solicitacao` responde
    "Confirmar solicitacao" — um rotulo que **nao esta entre as tres opcoes**.
    E esse e o mesmo defeito ja documentado na azul ("Sair e nao agendar"): a
    URA rejeita, o cancelamento nao acontece, e a sessao fica parada do lado da
    seguradora com o nosso lado marcado `test_aborted`.

    ⚠️ A regra e conservadora de proposito: so conta como lista quando ha **duas
       ou mais** linhas curtas depois da linha que faz a pergunta. Uma linha so
       e frase, nao opcao.
    """
    linhas = [" ".join(l.split()) for l in texto.split(chr(10))]
    linhas = [l for l in linhas if l]
    corte = -1
    for i, l in enumerate(linhas):
        if l.rstrip().endswith("?"):
            corte = i
    if corte < 0:
        return []
    # ⚠️ LINHA DE ECO NAO E OPCAO. 📊 A hdi confirma endereco assim:
    #      "Certo! Poderia confimar o endereco?
    #       *Rua:* {VALOR}
    #       *Numero:* {VALOR}
    #       *Bairro:* {VALOR}"
    #    Sao CAMPOS ecoados, nao alternativas -- e ler isso como lista fazia o
    #    guarda acusar `confirmar_endereco_digitado` de responder um rotulo que
    #    "nao esta entre as opcoes". Nao ha opcoes: ha botoes que o ingestor
    #    nao gravou (P-084-15).
    candidatas = [l for l in linhas[corte + 1:]
                  if 0 < len(l) <= 48 and not _RX_ECO_DE_CAMPO.match(l)]
    return candidatas if len(candidatas) >= 2 else []


def e_navegacao(rotulo: str) -> bool:
    r = " ".join(M._norm(rotulo).split())
    if not r:
        return True
    for nav in _NAVEGACAO:
        if r == nav or r.startswith(nav + " ") or r.startswith(nav + ","):
            return True
    return False


# ═════════════════════════════════════════════════════════════════════════════
# A · DE ONDE UM SLOT PODE VIR
# ═════════════════════════════════════════════════════════════════════════════
def _slots_derivados() -> Set[str]:
    """Os slots que `_derivar_teclas_do_caso` REALMENTE escreve.

    🔴 Lido da FONTE por AST, nunca de uma lista paralela. Uma lista escrita a
    mao envelhece calada — e foi assim que `TETO_DE_INDEFINIDO` ficou declarado
    e nunca lido, e que `schedule_agendado` existiu sem leitor por tres dias.
    """
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "app", "services", "insurer_dispatch_service.py")
    with open(caminho, encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    fora: Set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.FunctionDef) or no.name != "_derivar_teclas_do_caso":
            continue
        for x in ast.walk(no):
            # `slots["chave"] = ...`
            if isinstance(x, ast.Assign):
                for alvo in x.targets:
                    if (isinstance(alvo, ast.Subscript)
                            and isinstance(alvo.value, ast.Name)
                            and alvo.value.id == "slots"
                            and isinstance(alvo.slice, ast.Constant)
                            and isinstance(alvo.slice.value, str)):
                        fora.add(alvo.slice.value)
    return fora


def _slots_com_padrao_do_motor() -> Dict[str, Set[str]]:
    """O que `new_dispatch_session` preenche SOZINHO — a QUARTA origem.

    🔴 Esta funcao existe no produto desde a SPEC-082 e diz, na propria
    docstring, por que: *"perguntar ao cliente algo cuja resposta o motor ja
    sabe e a outra metade do defeito"*. O conferidor nao a conhecia, e por isso
    acusava 37 passos de ficarem CALADOS quando o motor os preenche.

    Devolve `{"auto": {...}, "residencial": {...}}` — a lista de auto e maior,
    e isso e do produto, nao um acidente: o corredor de auto sabe a placa, a
    cor e o servico antes de abrir.

    ⚠️ Lido da FONTE por AST. Uma copia escrita a mao foi exatamente o que
    mentiu no guarda da maquina de lavar: `servico_opcao`,
    `telefone_adicionar_opcao` e `veiculo_opcao` estavam declarados como
    DERIVADOS, e nada os deriva.
    """
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "app", "services", "insurer_dispatch_service.py")
    with open(caminho, encoding="utf-8") as fh:
        arvore = ast.parse(fh.read())
    comuns: Set[str] = set()
    so_auto: Set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.FunctionDef) or no.name != "_slots_com_padrao_do_motor":
            continue
        for x in ast.walk(no):
            literais = {e.value for e in ast.walk(x)
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            if isinstance(x, ast.Assign):
                comuns |= {v for v in literais if v.endswith(("_opcao", "_texto"))
                           or v in ("ponto_referencia",)}
            # o ramo `if line_kind == "auto"` acrescenta os de auto
            if isinstance(x, ast.If):
                so_auto |= {v for v in literais
                            if v not in ("auto", "line_kind", "")}
    return {"auto": comuns | so_auto, "residencial": comuns}


_PADRAO_DO_MOTOR = _slots_com_padrao_do_motor()

# 🔴 O motor tambem escolhe a LINHA da lista de veiculos pela placa
#    (`dynamic: "vehicle_by_plate"` -> `pick_option_by_plate`). Nao e derivacao
#    nem coleta: e o motor lendo a TELA. 📊 Foi a correcao de 12/07/2026, quando
#    "1" fixo pegou o carro ERRADO numa apolice com dois veiculos.
_ESCOLHIDOS_PELO_MOTOR = {"veiculo_opcao"}


def origens_do_slot(pb: Dict[str, Any], slot: str, derivados: Set[str]) -> List[str]:
    """As QUATRO origens legitimas de um slot.

    ```
    constante-por-subservico   declarada no bloco do subservico
    derivacao                  `_derivar_teclas_do_caso` traduz o relato
    coleta                     `required_slots` -> o corredor PERGUNTA ao cliente
    padrao-do-motor            `_slots_com_padrao_do_motor` / injecao de endereco
    ```

    🔴 Fora das quatro, o passo fica CALADO — e silencio e pior que resposta
       errada, porque nem o log registra.
    """
    fora = []
    subs = pb.get("subservices") or {}
    if any(slot in sub for sub in subs.values()):
        fora.append("constante-por-subservico")
    if slot in derivados:
        fora.append("derivacao")
    if any(slot in (sub.get("required_slots") or []) for sub in subs.values()):
        fora.append("coleta")
    if slot in _INJETADOS:
        fora.append("padrao-do-motor:endereco")
    if slot in _ESCOLHIDOS_PELO_MOTOR:
        fora.append("padrao-do-motor:escolhe-pela-placa")
    ramo = "auto" if str(pb.get("line_kind") or "") == "auto" else "residencial"
    if slot in _PADRAO_DO_MOTOR.get(ramo, set()):
        fora.append("padrao-do-motor")
    return fora


# 📊 `inject_address_slots` deriva estes de `local_atual` / `local_destino`.
#    Nao sao "sem origem": tem origem no MOTOR, e ela e verificavel na fonte.
_INJETADOS = {
    "local_uf", "local_cidade", "local_rua", "local_numero", "local_bairro",
    "local_cep", "local_complemento",
    "destino_uf", "destino_cidade", "destino_rua", "destino_numero",
    "destino_bairro", "destino_cep",
}


class Achado(NamedTuple):
    grave: bool          # 🔴 vermelho (reprova) x ⚠️ amarelo (registra)
    regra: str           # A / B / C
    seguradora: str
    ramo: str
    passo: str
    porque: str
    tela: str

    def __str__(self) -> str:
        marca = "🔴" if self.grave else "⚠️ "
        return (f"  {marca} [{self.regra}] {self.seguradora}/{self.ramo} · "
                f"{self.passo}\n        {self.porque}\n        tela: {self.tela[:88]}")


# `*Rua:* {VALOR}` / `Numero: 233` -- rotulo curto seguido de dois-pontos.
_RX_ECO_DE_CAMPO = re.compile(r"^\*?[A-Za-zÀ-ÿ ]{2,22}\*?\s*:", re.IGNORECASE)

_RX_SLOT = re.compile(r"\{([a-z0-9_]+)\}", re.IGNORECASE)


def conferir(seguradora: str, ramo: str, derivados: Set[str]) -> List[Achado]:
    """As tres perguntas, contra o corpus versionado, pelo MOTOR real."""
    ref = M.resolve_playbook_ref(seguradora, ramo)
    pb = M.get_playbook(ref) if ref else None
    if not pb:
        return []
    servicos = sorted((pb.get("subservices") or {}))
    linhas = RP.carregar_corpus(seguradora, ramo)
    if not linhas:
        return []

    # {texto_normalizado: (texto, {servicos observados})}
    telas: Dict[str, Tuple[str, Set[str], Set[str]]] = {}
    for l in linhas:
        k = M._norm(l["text"])
        if k not in telas:
            telas[k] = (l["text"], set(), set())
        sv_l = l.get("servico")
        if sv_l and not str(sv_l).startswith("?"):
            telas[k][1].add(sv_l)
        telas[k][2].add(l["session_id"])

    fora: List[Achado] = []
    ja_vistos: Set[Tuple[str, str]] = set()

    for _, (texto, servicos_da_tela, ses_da_tela) in telas.items():
        for sv in servicos:
            passo = M.match_ura_step(pb, texto, subservice=sv)
            if not passo:
                continue
            nome = str(passo.get("step") or "?")
            if passo.get("noop"):
                continue
            reply = str(passo.get("reply") or "")
            chave = (nome, M._norm(texto)[:60])
            if chave in ja_vistos:
                continue
            ja_vistos.add(chave)

            # ---------------------------------------------------- A · SLOT
            slots = _RX_SLOT.findall(reply)
            for slot in slots:
                if origens_do_slot(pb, slot, derivados):
                    continue
                # 🔴 E AQUI ESTA A DIFERENCA QUE FAZ ESTE GUARDA UTIL EM VEZ
                #    DE BARULHENTO: `fallback_adaptive` MUDA O DESFECHO.
                #
                #    Sem ele, `render_reply` devolve `ok=False`, o motor nao tem
                #    o que mandar e a tela conhecida vira `needs_human` na hora
                #    -- que esta dentro de `_TERMINAL_STATES` do Vigia. E o
                #    travamento de 19/08, medido: 2min22 de silencio.
                #
                #    Com ele, o cerebro LE A TELA e responde. O corredor nao
                #    sabe a resposta, e isso continua valendo registro -- mas
                #    nao e o mesmo defeito, e chamar os dois de vermelho faria
                #    o guarda gritar 119 vezes e ninguem olhar.
                grave = not passo.get("fallback_adaptive")
                fora.append(Achado(
                    grave, "A", seguradora, ramo, nome,
                    (f"o slot `{slot}` nao tem origem (nem constante, nem "
                     f"derivacao, nem coleta) -- o passo fica CALADO")
                    if grave else
                    (f"o slot `{slot}` nao tem origem; o passo nao trava porque "
                     f"tem `fallback_adaptive` -- mas quem responde e o cerebro, "
                     f"nao o corredor"),
                    " ".join(texto.split())))

            # ------------------------------------------------ B · CONSTANTE
            if reply and not slots:
                ops = opcoes_da_tela(texto)
                n = M._norm(texto)
                if reply.strip().isdigit():
                    tecla = reply.strip()
                    if tecla not in ops:
                        # 🔴 So e vermelho quando da para VER que a tecla nao
                        #    existe. Tela sem opcao nenhuma no `text` e botao que
                        #    o ingestor nao gravou -- 937 respostas vazias medidas
                        #    (P-084-15). Acusar ali e acusar o CORPUS.
                        # ⚠️ `constante_justificada` vale aqui tambem: 📊 a alfa
                        #    escreve a opcao 1 SEM numero, e so numera a 2. E
                        #    formatacao quebrada DA SEGURADORA, e o passo diz isso
                        #    por escrito em vez de fingir que a tela e outra.
                        fora.append(Achado(
                            bool(ops) and not passo.get("constante_justificada"),
                            "B", seguradora, ramo, nome,
                            (f"responde `{tecla}` e a tela oferece apenas "
                             f"{sorted(ops)} -- a URA rejeita")
                            if ops else
                            (f"responde `{tecla}` e a tela nao expoe opcao nenhuma "
                             f"no `text` -- botao nao gravado pelo ingestor "
                             f"(P-084-15). Nao da para confirmar daqui"),
                            " ".join(texto.split())))
                    elif not e_navegacao(ops[tecla]) and not passo.get("constante_justificada"):
                        substantivas = [v for v in ops.values() if not e_navegacao(v)]
                        if len(substantivas) >= 2:
                            fora.append(Achado(
                                True, "B", seguradora, ramo, nome,
                                f"a constante `{tecla}` escolhe "
                                f"'{ops[tecla][:44]}' entre {len(substantivas)} "
                                f"ALTERNATIVAS DE CONTEUDO -- o corredor decide "
                                f"pelo cliente. Falta `constante_justificada`",
                                " ".join(texto.split())))
                else:
                    # 🔴 UM ROTULO SO PODE ESTAR ERRADO CONTRA UMA LISTA QUE
                    #    DA PARA VER. Se a tela nao expoe opcao nenhuma, a
                    #    resposta literal pode ser TEXTO LIVRE (o nome que damos
                    #    em "me informe o seu nome") ou um botao que o ingestor
                    #    nao gravou -- 📊 e sao 937 respostas de botao vazias.
                    #    Chamar isso de vermelho seria acusar o corpus, nao o
                    #    corredor.
                    if M._norm(reply) not in n:
                        em_lista = opcoes_em_lista(texto)
                        tem_opcoes = bool(ops) or bool(em_lista)
                        fora.append(Achado(
                            tem_opcoes, "B", seguradora, ramo, nome,
                            (f"responde o rotulo '{reply}' e ele NAO ESTA entre as "
                             f"opcoes da tela ({(list(ops.values()) or em_lista)[:4]}) "
                             f"-- a URA rejeita e o turno se perde")
                            if tem_opcoes else
                            (f"responde o rotulo '{reply}' e a tela nao expoe opcao "
                             f"nenhuma no `text` -- pode ser texto livre ou botao "
                             f"nao gravado pelo ingestor (P-084-15). Nao da para "
                             f"confirmar daqui"),
                            " ".join(texto.split())))

            # ------------------------------------------------- C · OFICIO
            restrito = passo.get("only_subservices")
            if restrito and servicos_da_tela:
                conhecidos = {s for s in servicos_da_tela if s in servicos}
                if conhecidos and not (conhecidos & set(restrito)):
                    # ⚠️ A `C` DEPENDE DA CLASSIFICACAO DO SERVICO ESTAR CERTA,
                    #    e ela e inferida por `padroes_de_servico`. Uma tela vista
                    #    numa sessao SO e evidencia fraca: pode ser a tela que
                    #    esta no lugar errado, ou a SESSAO que foi classificada
                    #    errado -- e o guarda nao sabe qual.
                    #
                    # 📊 Duas ou mais sessoes concordando e o que separa "achado"
                    #    de "ruido": foi com 4 sessoes que a tela do encanador da
                    #    allianz denunciou o passo do eletricista.
                    grave = len(ses_da_tela) >= 2
                    fora.append(Achado(
                        grave, "C", seguradora, ramo, nome,
                        f"e restrito a {sorted(restrito)} e esta respondendo uma "
                        f"tela que so aparece em sessoes de {sorted(conhecidos)} "
                        f"({len(ses_da_tela)} sessao/sessoes)" +
                        ("" if grave else " -- 1 sessao so: pode ser a CLASSIFICACAO"),
                        " ".join(texto.split())))
    return fora


def conferir_tudo(so_graves: bool = True) -> List[Achado]:
    derivados = _slots_derivados()
    fora: List[Achado] = []
    for seg in M.seguradoras():
        for ramo in ("auto", "residencial"):
            fora.extend(conferir(seg, ramo, derivados))
    return [a for a in fora if a.grave or not so_graves]


def relatorio() -> Tuple[str, int]:
    achados = conferir_tudo()
    L = ["=== A RESPOSTA ESTA CERTA? (P-084-14) ===",
         "",
         "  A · slot sem origem        -> o passo fica CALADO",
         "  B · constante nao confirmada pela tela",
         "  C · passo de um oficio respondendo tela de outro",
         ""]
    if not achados:
        L.append("  OK nenhum passo responde sem confirmacao")
        return "\n".join(L), 0
    por_regra = collections.Counter(a.regra for a in achados)
    for a in achados:
        L.append(str(a))
    L.append("")
    L.append(f"  🔴 {len(achados)} achados · " +
             " · ".join(f"{k}={v}" for k, v in sorted(por_regra.items())))
    return "\n".join(L), len(achados)


if __name__ == "__main__":
    texto, n = relatorio()
    print(texto)
    sys.exit(1 if n else 0)
