# -*- coding: utf-8 -*-
"""Replay OFFLINE do portal de vidros a partir dos HAR reais — EXTRA-001.10.

🔴 O que este arquivo é, e o que ele deliberadamente NÃO é
==========================================================
É um **dublê de BORDA**: uma `page` falsa cujo `evaluate` responde com o corpo
que o portal respondeu de verdade, lido do HAR em tempo de execução por
`app.services.portals.lab.trafego.importar_har` — a MESMA função que a CLI
`portal_factory lab har` usa. ⛔ Não existe segundo leitor de HAR em `tests/`.

Do outro lado da borda, **tudo é o motor real**: `abrir_atendimento_api`,
`SessaoVidros`, `PortalActionGuard`, `vidros_estado`, `vidros_questionario`.

🔴 E o dublê NUNCA nasce de um dicionário escrito à mão a partir da leitura do
código. Se eu escrevesse as respostas, eu estaria testando a minha leitura do
portal, não o portal. É a diferença entre 72 asserções verdes e um agendamento
que nunca chegava ao cliente.

⛔ PII
=====
Os HAR contêm CPF, placa, chassi, nome, telefone, e-mail, token, nº de apólice
e nº de atendimento. **Nada disso vira constante.** Os `params` do teste são
DERIVADOS do próprio HAR em tempo de execução (`params_do_har`), e as asserções
falam de CHAVES, ORDEM, TIPOS e valores de CATÁLOGO (códigos de item, de motivo,
de serviço, de cidade, enums) — nunca de um valor pessoal.

Os HAR são intake e não estão no Git (`docs/intake/` está no `.gitignore`).
Sem eles, `carregar` levanta `HarAusente` e o teste dá `skip` com o caminho.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
if str(RAIZ_BACKEND) not in sys.path:
    sys.path.insert(0, str(RAIZ_BACKEND))

from app.services.portals.lab.trafego import importar_har  # noqa: E402

RAIZ_REPO = RAIZ_BACKEND.parent
HOST_PORTAL = "abraseuatendimento.com.br"
HOST_API = "api.autoglass.com.br"
BASE = "/atendimentos/api/web-app"

# Os quatro acervos, pelo que cada um PROVA.
HARS: Dict[str, Path] = {
    # para-brisa · categoria V · questionário de 3 perguntas · reparo aceito ·
    # concluiu com loja direta
    "NOVO": RAIZ_REPO / "docs/intake/materiais/portal-vidros/YELUM/YELUM PARA BRISA/YELUM PARA BRISA.har",
    # lataria · categoria L · multi-peça · ZERO questionário · loja direta
    "LAT": RAIZ_REPO / "docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har",
    # vidro de porta · categoria V · sem oferta de reparo · AGENDA com 1 loja
    "ANT": RAIZ_REPO / "docs/intake/materiais/portal-vidros/YELUM/YELUM VIDROS ANTIGO/abraseuatendimento.com.br.har",
    # lanterna · Porto · TipoAtendimento = 1 · terminou em abandono
    "PORTO": RAIZ_REPO / "docs/intake/materiais/portal-vidros/PORTO/VIDRO LANTERNA.har",
    # EXTRA-001.10.1 · capturas de 21/09/2026
    # vidro de porta · V · AGENDA com 1 loja · 📊 o `POST /agendamentos` [048]
    # CONCLUÍDO (Encaixe:true, 16:00) e o "Agendado para" lido em [049]
    "LATERAL": RAIZ_REPO / "docs/intake/materiais/portal-vidros/YELUM/YELUM VIDRO LATERAL/YELUM VIDRO LATERAL.har",
    # 🔴 o MESMO arquivo tem DUAS execuções: [0–60] repete o vidro lateral e
    # [61–113] é a LATARIA — ilha normal + opção de vistoria (ramo 7 do
    # roteador do SPA): prioridade [092] + ocorrência [093] → analista.
    # A faixa (a 2ª abertura) está em FAIXAS.
    "LATARIA2": RAIZ_REPO / "docs/intake/materiais/portal-vidros/YELUM/YELUM LATARIA/YELUM LATARIA.har",
}

# 🔴 FAIXA: um HAR pode conter mais de uma execução. `N` = começa na N-ésima
# `POST /atendimentos` (com os GET de preflight que a antecedem colados).
# 📊 `YELUM LATARIA.har`: 2 aberturas, em [003] e [062] (`importar_har`).
FAIXAS: Dict[str, int] = {"LATARIA2": 2}

# 🔴 Endereços cuja resposta depende da QUERY, e não só do caminho.
# 📊 `horarios-disponiveis` do LATERAL: [044] `DataAgendamento=2026-09-21` → 0
# blocos; [045] `=2026-09-22` → 40 blocos. Responder o dia 23 com os blocos do
# dia 22 seria o dublê INVENTANDO agenda — e o motor agendaria num dia que o
# portal nunca publicou. Dia que o acervo não viu → 404 e `fora_do_acervo`.
QUERY_ESTRITA = ("/agendamentos/horarios-disponiveis",)

# 🔴 BARREIRAS: escritas que MUDAM o que a leitura seguinte devolve.
# 📊 LATERAL: o motor lê `GET /atendimentos` logo depois de
# `opcoes-disponiveis` [037]; o próximo GET do HAR é o [049] — DEPOIS do
# `POST /agendamentos` [048], já com "Agendado para". Servir aquele agregado a
# um motor que ainda não agendou é o dublê contando o futuro. Com a barreira,
# a leitura cai no estado mais recente ANTES dela ([032]).
BARREIRAS = {("POST", "/agendamentos"), ("POST", "/atendimentos-prioridades"),
             ("POST", "/ocorrencias")}

# 🔴 O motor NÃO cancela e NÃO abandona. As entradas a partir da desistência
# ficam FORA do acervo do replay: deixá-las dentro faria uma leitura tardia do
# motor cair num agregado já cancelado e "provar" um desfecho que o fluxo real
# nunca teve.
CAMINHOS_DE_DESISTENCIA = ("/atendimentos/cancelar", "/atendimentos/abandonar")


class HarAusente(FileNotFoundError):
    """O acervo é intake, não é versionado. Ausência vira `skip`, não vermelho."""


def caminho_de(chamada: Any) -> str:
    """Caminho relativo à base da API, sem query."""
    p = chamada.caminho
    return p[len(BASE):] if p.startswith(BASE) else p


def _chave(metodo: str, caminho: str) -> Tuple[str, str]:
    """Casamento tolerante a query e a código na URL."""
    return (str(metodo).upper(),
            re.sub(r"/\d{4,}", "/{codigo}", str(caminho).split("?")[0]))


def carregar(nome: str, *, a_partir: Optional[int] = None) -> List[Any]:
    """As chamadas de API do HAR, na ordem, até a desistência (exclusive).

    `a_partir=N` (ou `FAIXAS[nome]`) começa na N-ésima `POST /atendimentos`,
    levando junto os GET de preflight (`/seguradoras/`, `/apolices`) colados
    antes dela — é a execução inteira, e só ela.
    """
    caminho = HARS[nome]
    if not caminho.exists():
        raise HarAusente(
            f"o HAR {nome} nao esta nesta maquina: {caminho}. Ele e material de "
            "INTAKE (docs/intake/ esta no .gitignore) e nao viaja no Git.")
    trafego = importar_har(caminho, host_portal=HOST_PORTAL)
    api = [c for c in trafego
           if c.host == HOST_API and c.metodo.upper() != "OPTIONS"]
    n = a_partir if a_partir is not None else FAIXAS.get(nome)
    if n:
        aberturas = [i for i, c in enumerate(api)
                     if c.metodo.upper() == "POST" and caminho_de(c) == "/atendimentos"]
        if len(aberturas) < n:
            raise ValueError(f"o HAR {nome} tem {len(aberturas)} abertura(s), "
                             f"nao {n}")
        ini = aberturas[n - 1]
        while ini > 0 and api[ini - 1].metodo.upper() == "GET" \
                and caminho_de(api[ini - 1]) in ("/apolices", "/seguradoras/"):
            ini -= 1
        api = api[ini:]
    corte = len(api)
    for i, c in enumerate(api):
        if caminho_de(c) in CAMINHOS_DE_DESISTENCIA:
            corte = i
            break
    return api[:corte]


def indice(chamadas: List[Any], metodo: str, caminho: str, *, n: int = 1) -> int:
    """Posição da N-ésima chamada que casa (método, caminho). `-1` se não há."""
    alvo = _chave(metodo, caminho)
    vistos = 0
    for i, c in enumerate(chamadas):
        if _chave(c.metodo, caminho_de(c)) == alvo:
            vistos += 1
            if vistos == n:
                return i
    return -1


def corpo_json(chamada: Any, *, requisicao: bool = False) -> Any:
    bruto = chamada.corpo_req if requisicao else chamada.corpo_resp
    if not bruto:
        return None
    try:
        return json.loads(bruto)
    except (ValueError, TypeError):
        return None


def primeira(chamadas: List[Any], metodo: str, caminho: str,
             *, requisicao: bool = False) -> Any:
    """O corpo da primeira chamada que casa (método, caminho)."""
    alvo = _chave(metodo, caminho)
    for c in chamadas:
        if _chave(c.metodo, caminho_de(c)) == alvo:
            return corpo_json(c, requisicao=requisicao)
    return None


def todas(chamadas: List[Any], metodo: str, caminho: str,
          *, requisicao: bool = False) -> List[Any]:
    alvo = _chave(metodo, caminho)
    return [corpo_json(c, requisicao=requisicao) for c in chamadas
            if _chave(c.metodo, caminho_de(c)) == alvo]


# ==========================================================================
# A página falsa — a ÚNICA peça dublada
# ==========================================================================
class PaginaDeReplay:
    """`page.evaluate` respondendo com o que o portal respondeu de verdade.

    A escolha da resposta é **por método + caminho, na ordem, tolerante a
    query**: procura a próxima entrada ainda não consumida a partir do cursor;
    não achando, procura qualquer não consumida; não achando, REUTILIZA a última
    resposta vista para aquele endereço (e marca isso). A reutilização existe
    porque o HAR foi gravado por um humano clicando — ele releu telas que o
    motor não relê, e parou onde o motor não para.
    """

    def __init__(self, chamadas: List[Any], *, cursor: int = 0) -> None:
        """`cursor=i`: a página já "viveu" as entradas `[0, i)` — é como se
        retoma um atendimento no MEIO do HAR (a continuação é outro job, mas o
        portal é o mesmo e já passou por aquelas telas)."""
        self.chamadas = chamadas
        self.consumidas = [i < cursor for i in range(len(chamadas))]
        self.cursor = cursor
        self.registro: List[Dict[str, Any]] = []
        self.sem_resposta: List[Tuple[str, str]] = []
        # pedidos a um endereço de QUERY_ESTRITA com uma query que o acervo não
        # viu (ex.: um dia de agenda que o humano não abriu). Não é defeito do
        # motor: é o limite do que foi capturado.
        self.fora_do_acervo: List[Tuple[str, str]] = []

    # -- o que o teste pergunta ------------------------------------------
    def emitidas(self, *, apenas_escritas: bool = False) -> List[Tuple[str, str]]:
        return [(r["metodo"], r["caminho"]) for r in self.registro
                if not apenas_escritas
                or r["metodo"] in ("POST", "PUT", "PATCH", "DELETE")]

    def escritas(self) -> List[Tuple[str, str]]:
        return self.emitidas(apenas_escritas=True)

    def quantas(self, metodo: str, caminho: str) -> int:
        alvo = _chave(metodo, caminho)
        return sum(1 for r in self.registro
                   if _chave(r["metodo"], r["caminho"]) == alvo)

    def corpo_de(self, metodo: str, caminho: str) -> Any:
        alvo = _chave(metodo, caminho)
        for r in self.registro:
            if _chave(r["metodo"], r["caminho"]) == alvo:
                return r["corpo"]
        return None

    def ordem_de(self, metodo: str, caminho: str) -> int:
        """Índice da chamada no que o MOTOR emitiu. `-1` = nunca saiu."""
        alvo = _chave(metodo, caminho)
        for i, r in enumerate(self.registro):
            if _chave(r["metodo"], r["caminho"]) == alvo:
                return i
        return -1

    # -- a borda ----------------------------------------------------------
    async def evaluate(self, _js: str, arg: Dict[str, Any]) -> Dict[str, Any]:
        url = str(arg.get("url") or "")
        metodo = str(arg.get("metodo") or "GET").upper()
        caminho = url.split(HOST_API, 1)[-1]
        caminho = caminho[len(BASE):] if caminho.startswith(BASE) else caminho
        self.registro.append({"metodo": metodo, "caminho": caminho,
                              "corpo": arg.get("corpo"),
                              "cabecalhos": dict(arg.get("cabecalhos") or {})})

        if caminho.split("?")[0] in QUERY_ESTRITA:
            indice = self._achar_pela_query(metodo, caminho)
            if indice is None:
                self.fora_do_acervo.append((metodo, caminho.split("?")[0]))
                return {"ok": False, "status": 404, "text": ""}
            chamada = self.chamadas[indice]
            return {"ok": 200 <= int(chamada.status or 0) < 400,
                    "status": int(chamada.status or 0),
                    "text": chamada.corpo_resp or ""}

        indice = self._achar(metodo, caminho)
        if indice is None:
            self.sem_resposta.append((metodo, caminho))
            return {"ok": False, "status": 404, "text": ""}
        chamada = self.chamadas[indice]
        return {"ok": 200 <= int(chamada.status or 0) < 400,
                "status": int(chamada.status or 0),
                "text": chamada.corpo_resp or ""}

    def _achar_pela_query(self, metodo: str, caminho: str) -> Optional[int]:
        """A entrada do mesmo endereço E da mesma query. Sem ela, `None`."""
        from urllib.parse import parse_qsl, urlsplit

        alvo = _chave(metodo, caminho)
        pedida = dict(parse_qsl(urlsplit(caminho).query))
        iguais = [i for i, c in enumerate(self.chamadas)
                  if _chave(c.metodo, caminho_de(c)) == alvo
                  and {str(k): str(v) for k, v in (c.query or {}).items()} == pedida]
        if not iguais:
            return None
        livres = [i for i in iguais if not self.consumidas[i]]
        i = (livres or iguais)[0]
        self.consumidas[i] = True
        return i

    def _achar(self, metodo: str, caminho: str) -> Optional[int]:
        alvo = _chave(metodo, caminho)
        # 🔴 A segunda passada vai PARA TRAS a partir do cursor, e nao para a
        # frente a partir do zero. O estado do pedido avanca: a resposta mais
        # RECENTE e a que vale. 📊 No HAR do vidro de porta ha cinco
        # `GET /atendimentos`, e so os dois ULTIMOS trazem o CodigoAtendimento —
        # varrendo do zero, o replay devolvia o primeiro (sem numero) e o
        # desfecho `agenda` chegava ao segurado sem o que anotar.
        for n_faixa, faixa in enumerate((range(self.cursor, len(self.chamadas)),
                                         range(self.cursor, -1, -1))):
            for i in faixa:
                if n_faixa == 0 and not self.consumidas[i] and                         _chave(self.chamadas[i].metodo, caminho_de(self.chamadas[i]))                         in BARREIRAS and _chave(self.chamadas[i].metodo,
                                                caminho_de(self.chamadas[i])) != alvo:
                    # 🔴 uma leitura não atravessa uma escrita que o motor
                    # AINDA não fez: o estado de depois dela não existe.
                    break
                if self.consumidas[i]:
                    continue
                if _chave(self.chamadas[i].metodo, caminho_de(self.chamadas[i])) == alvo:
                    self.consumidas[i] = True
                    self.cursor = i
                    return i
        # reutiliza a última vista para o mesmo endereço
        for i in range(len(self.chamadas) - 1, -1, -1):
            if _chave(self.chamadas[i].metodo, caminho_de(self.chamadas[i])) == alvo:
                return i
        return None


# ==========================================================================
# Os `params` — DERIVADOS do HAR, nunca digitados
# ==========================================================================
def params_do_har(chamadas: List[Any], *, extra: Optional[Dict[str, Any]] = None
                  ) -> Dict[str, Any]:
    """O que a conversa teria coletado, reconstruído do que o portal recebeu.

    🔴 Cada campo sai de uma resposta ou de um corpo REAL. Nenhum valor pessoal
    é digitado aqui nem impresso em lugar nenhum — eles entram em memória, vão
    para o motor e morrem com o processo.

    Duas coisas NÃO vêm do HAR, de propósito, porque são contrato NOSSO e não do
    portal: `contato.relacao` é sempre `"6"` (Corretor — D-E00110-01) e
    `contato.tipo_telefone` é um nome do nosso vocabulário, resolvido pelo motor
    contra `GET /tipos-telefone`.
    """
    abertura = primeira(chamadas, "POST", "/atendimentos", requisicao=True) or {}
    patch = primeira(chamadas, "PATCH", "/atendimentos", requisicao=True) or {}
    solicitante = primeira(chamadas, "POST", "/solicitantes", requisicao=True) or {}
    corretor = primeira(chamadas, "PUT", "/atendimentos/corretores",
                        requisicao=True) or {}
    itens = primeira(chamadas, "GET", "/apolices/itens-cobertos") or []
    motivos = primeira(chamadas, "GET", "/motivos-dano") or []
    cidades = primeira(chamadas, "GET", "/cidades") or []
    servicos = primeira(chamadas, "GET", "/atendimentos/servicos-itens") or []

    def descricao_do_item(codigo: str) -> str:
        for i in itens:
            if isinstance(i, dict) and i.get("CodigoItemCoberto") == codigo:
                return str(i.get("Descricao") or "")
        return ""

    def descricao_do_motivo(codigo: Any) -> str:
        for m in motivos:
            if isinstance(m, dict) and m.get("CodigoObjetoCausa") == codigo:
                return str(m.get("DescricaoObjetoCausa") or "")
        return ""

    def cidade(codigo: Any) -> Dict[str, str]:
        for c in cidades:
            if isinstance(c, dict) and c.get("Codigo") == codigo:
                return {"uf": str(c.get("UF") or ""), "cidade": str(c.get("Nome") or "")}
        return {"uf": "", "cidade": ""}

    def peca_de_lataria(codigo: Any) -> str:
        for s in servicos:
            if isinstance(s, dict) and s.get("Codigo") == codigo:
                return str(s.get("Descricao") or "")
        return ""

    # 📊 O portal recebeu `DataSinistro` como ISO-8601 COM hora e `Z`
    # (`2026-09-20T03:00:00.000Z` — meia-noite local de um fuso UTC-3). A
    # conversa produz `DD/MM/AAAA`; devolver a data nesse formato aqui faz o
    # parser real do motor (`data_iso`) rodar no replay em vez de ser pulado.
    iso = str(abertura.get("DataSinistro") or "")[:10]
    data_de_gente = "-".join(reversed(iso.split("-"))).replace("-", "/") if iso else ""

    telefones = solicitante.get("Telefones") or []
    numero = str((telefones[0] or {}).get("Numero") or "") if telefones else ""

    # As respostas do questionário, com o TEXTO que o portal devolveu — é o que
    # a conversa teria em mãos depois de perguntar ao segurado.
    especificos: Dict[str, Any] = {}
    gravado = primeira(chamadas, "POST", "/questionarios")
    for resposta in (gravado or []):
        if isinstance(resposta, dict) and resposta.get("DescricaoResposta"):
            especificos[f"pergunta_{resposta.get('CodigoPergunta')}"] = \
                str(resposta.get("DescricaoResposta"))

    params: Dict[str, Any] = {
        "insurer_name": str(abertura.get("Seguradora") or ""),
        "cpf_cnpj": str(abertura.get("CpfCnpjSegurado") or ""),
        "placa": str(abertura.get("PlacaInformada") or ""),
        "data_dano": data_de_gente,
        "dano": {
            "peca": descricao_do_item(str(patch.get("CodigoItemCoberto") or "")),
            "como": descricao_do_motivo(patch.get("CodigoObjetoCausa")),
            "onde": str(patch.get("PerimetroDano") or ""),
            "descricao": str(patch.get("AvaliacaoDano") or ""),
            "pecas_lataria": [peca_de_lataria(s.get("CodigoServico"))
                              for s in (patch.get("ServicosMartelinhoLataria") or [])
                              if isinstance(s, dict)],
        },
        "local": {"cidade_servico": cidade(patch.get("CodigoCidade")),
                  "cep": str(patch.get("Cep") or "")},
        "especificos": especificos,
        "contato": {
            "relacao": "6",
            "telefone": numero,
            "tipo_telefone": "segurado",
            "email_segurado": str(solicitante.get("EmailSegurado") or ""),
            "email_corretora": str(solicitante.get("EmailTitularAplice") or ""),
            "nome_solicitante": str(solicitante.get("NomeSolicitante") or ""),
            "documento_corretor": str(corretor.get("Documento") or ""),
        },
        "confirm": True,
    }
    for chave, valor in (extra or {}).items():
        if isinstance(valor, dict) and isinstance(params.get(chave), dict):
            params[chave] = {**params[chave], **valor}
        else:
            params[chave] = valor
    return params
