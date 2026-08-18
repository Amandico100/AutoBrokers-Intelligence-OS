# -*- coding: utf-8 -*-
"""A carteira da corretora, em lote, para relatório — SPEC-081 Bloco A.

## Por que este módulo existe, e por que ele NÃO é um segundo conector

📊 Já existe `backend/app/api/infocap_connector.py`, com 4.253 linhas. Ele faz
uma coisa muito bem: **consulta UMA apólice por vez**, por CPF, para o agente de
atendimento responder "qual é a minha apólice?". 62 invocações bem-sucedidas.

Este módulo faz o oposto: **lê a carteira inteira de um período**, cruza
endpoints e devolve números agregados. Nenhuma das duas coisas serve para a
outra, e adaptar o conector — que o Atendimento usa em produção — na véspera de
uma apresentação seria trocar risco baixo por risco alto sem ganho.

CLAUDE.md §5 proíbe motor paralelo ao existente. Não é o caso: é capacidade
nova, com contrato próprio, que não duplica o trabalho de ninguém.

## As armadilhas, todas MEDIDAS em 18/08/2026

Cada uma delas custou uma versão errada da SPEC antes de ser medida.

**1. `prod_docs[]` dentro de `/renovacoes` é REDUZIDO.**
Não confundir com o endpoint `/prod_docs` avulso. 📊 Os campos que existem:

    agente · automat · cod_age · cod_pro · ordem · per_r · produtor · val_r

Não existem: `indireto`, `nome_produtor`, `base_r`, `nome_agente`. A primeira
versão desta camada foi escrita contra `ordem==1 AND indireto=="F"` — contra uma
API imaginária.

**2. `/renovacoes` NÃO tem `val_c`.** 📊 Vem `None`. A comissão da corretora só
existe em `/documentos_bi`. Sem o cruzamento por `nosnum`, não há relatório.

**3. As duas populações são quase disjuntas.** `/documentos_bi` filtra por
`inivig`; `/renovacoes` por `fimvig`. 📊 A interseção de 2025 com 2025 é de
**2,8%** (100 de 3.536) — porque apólice anual que COMEÇA em 2025 TERMINA em
2026. Por isso o mapa de produtores varre VÁRIOS anos de vencimento.

**4. `tipo_doc=A` dobra a cobertura.** 📊 Medido:

        TODOS   3.272 docs  R$ 2.276.444   41,4% com produtor
        A       1.680 docs  R$ 1.863.831   80,6% com produtor

O que ficava de fora eram endossos e propostas. O filtro vai na REQUISIÇÃO.

**5. Janela grande devolve 502.** 📊 `/documentos_bi` de 7 anos morre aos 28 s;
`/renovacoes` de 2018 a 2032 também. Ano a ano funciona sempre.

**6. `quant_produtores` mente.** 📊 Uma linha com `quant_produtores: 3` trouxe
`prod_docs` com 2 itens. A lista é a verdade; o contador é pista.

**7. Concorrência derruba.** 📊 10 chamadas paralelas: 1 devolveu HTTP 500.
Daí o retry com espera crescente.

## Semântica de erro da API (📊 medida, não documentada)

    404  →  vazio, não erro
    500  →  janela grande demais
    502  →  janela grande demais (o Gateway desistiu)
    403 com texto SigV4  →  **a rota não existe** (nunca é permissão)

🔴 O último já custou caro: `docs/canon/global_knowledge/infocap-corpapi-mapa.md`
concluiu "endpoint negado, pedir liberação à corretora" a partir desse 403, e
essa conclusão errada está injetada no conhecimento dos agentes.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

BASE_PADRAO = "https://api.corpnuvem.com"

# 📊 Medido: chamada leve 0,7-1,0 s; lote de 3.272 linhas em 4,5 s; lote de
# 5.879 em 6,1 s. 240 s dá folga de uma ordem de grandeza sobre o pior caso
# observado, e ainda fica abaixo de qualquer paciência humana num relatório.
TIMEOUT_S = 240

# 📊 1 em 10 chamadas paralelas devolveu 500. Três tentativas com espera
# crescente cobrem isso sem transformar um erro real em espera de um minuto.
TENTATIVAS = 3
ESPERA_BASE_S = 3

# 📊 O ano é a maior janela que a API atende de forma confiável nos dois
# endpoints. Não é escolha de desenho: é o teto medido.
JANELA_MAXIMA_DIAS = 366


class FalhaDaInfocap(RuntimeError):
    """A InfoCap não respondeu, ou respondeu o que não dá para usar.

    Existe como tipo próprio para que quem chama consiga dizer ao corretor
    "a seguradora não respondeu" em vez de "Exception" — o defeito que já
    custou uma rodada inteira de diagnóstico em 17/08.
    """


# --------------------------------------------------------------------------
# O que sai daqui
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Apolice:
    """Uma apólice de produção, com o dinheiro dela.

    Só os campos que algum relatório usa. Trazer o registro cru inteiro
    convidaria a próxima pessoa a somar um campo que ninguém validou.
    """

    nosnum: str
    cliente: str
    codcli: str
    seguradora: str
    ramo: str
    inivig: str
    fimvig: str
    premio: float          # pretot
    comissao: float        # val_c — o que a CORRETORA recebe
    base_comissao: float   # base_c
    e_renovacao: bool      # nosnum_ren preenchido


@dataclass(frozen=True)
class ProdutorDaApolice:
    """Quem vendeu, e quanto dessa comissão vai embora como repasse."""

    nosnum: str
    codigo: str      # cod_pro
    nome: str        # 🔴 o campo é `produtor`, NUNCA `nome_produtor`
    repasse: float   # val_r
    percentual: float  # per_r


@dataclass(frozen=True)
class Vencimento:
    """Uma apólice a vencer, com o contato do segurado e o vendedor."""

    nosnum: str
    cliente: str
    codcli: str
    seguradora: str
    ramo: str
    fimvig: str
    dias_a_vencer: int
    premio: float
    produtor: str
    telefone: str
    email: str
    tipdoc: str
    tem_sinistro: bool


# --------------------------------------------------------------------------
# O cliente
# --------------------------------------------------------------------------
class FonteInfocap:
    """Leitura em lote da carteira. **Nunca escreve na InfoCap.**

    Uso:
        fonte = FonteInfocap.para_empresa("resulta")
        apolices = fonte.producao(date(2025, 1, 1), date(2025, 12, 31))
        mapa = fonte.mapa_de_produtores([2024, 2025, 2026, 2027])
    """

    def __init__(self, login: str, senha: str, aplicacao: str = "0",
                 base_url: str = BASE_PADRAO, rotulo: str = "") -> None:
        if not login or not senha:
            raise FalhaDaInfocap(
                f"a corretora {rotulo or '?'} não tem credencial da InfoCap "
                f"configurada no ambiente")
        self._login_email = login
        self._senha = senha
        self._aplicacao = aplicacao
        self._base = (base_url or BASE_PADRAO).rstrip("/")
        self._rotulo = rotulo or login
        self._token: Optional[str] = None

    # ---------------------------------------------------------------- fábrica
    @classmethod
    def para_empresa(cls, slug: str) -> "FonteInfocap":
        """Resolve credencial por SLUG, no mesmo padrão do Cartógrafo.

        📊 Precedente: `backend/scripts/build_cartographer_dataset.py:168-173`
        já lê `CORP_INFOCAP_{SLUG}_LOGIN/PASSWORD/APPLICATION`, e o ambiente de
        produção já tem as duas corretoras configuradas.

        💭 Dívida registrada: quando a terceira corretora entrar, isto migra
        para `tenant_connections` (o Vault), que é onde credencial de tenant
        deve morar. Env por slug não escala — mas trocar o mecanismo de
        credencial na véspera de uma apresentação escalaria menos ainda.
        """
        s = str(slug or "").strip().upper()
        return cls(
            login=os.getenv(f"CORP_INFOCAP_{s}_LOGIN", ""),
            senha=os.getenv(f"CORP_INFOCAP_{s}_PASSWORD", ""),
            aplicacao=os.getenv(f"CORP_INFOCAP_{s}_APPLICATION", "0"),
            base_url=os.getenv(f"CORP_INFOCAP_{s}_BASE_URL", BASE_PADRAO),
            rotulo=str(slug or ""),
        )

    # ------------------------------------------------------------------ rede
    def _autenticar(self) -> str:
        if self._token:
            return self._token
        corpo = json.dumps({
            "email": self._login_email,
            "senha": self._senha,
            "aplicacao": int(str(self._aplicacao or "0") or 0),
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base}/login", data=corpo,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            raise FalhaDaInfocap(
                f"login na InfoCap falhou para {self._rotulo} "
                f"({type(exc).__name__})") from exc
        tok = str((d or {}).get("token") or "")
        if not tok:
            raise FalhaDaInfocap(
                f"a InfoCap aceitou o login de {self._rotulo} mas não devolveu "
                f"token")
        # 🔴 O header é `Authorization: <token>` PURO. Sem "Bearer".
        self._token = tok
        return tok

    def _get(self, rota: str, params: Dict[str, Any]) -> Any:
        """GET com retry. Levanta `FalhaDaInfocap` com motivo LEGÍVEL."""
        url = f"{self._base}{rota}?{urllib.parse.urlencode(params)}"
        ultimo = ""
        for tentativa in range(TENTATIVAS):
            try:
                req = urllib.request.Request(
                    url, headers={"Authorization": self._autenticar()})
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as exc:
                # 404 é VAZIO, não erro. A API responde assim quando o filtro
                # não casa nada, e tratar como falha faria um período sem
                # movimento derrubar o relatório inteiro.
                if exc.code == 404:
                    return {}
                if exc.code == 401:
                    self._token = None  # expirou: reautentica na próxima volta
                ultimo = f"HTTP {exc.code}"
                if exc.code in (500, 502, 503, 504):
                    ultimo += " (janela grande demais, ou instabilidade)"
                if exc.code == 403:
                    # 🔴 403 aqui é ROTA INEXISTENTE, não permissão. Ver o
                    # cabeçalho deste arquivo.
                    raise FalhaDaInfocap(
                        f"a rota {rota} não existe na InfoCap (403 do Gateway). "
                        f"Não é permissão — não adianta pedir liberação.") from exc
            except Exception as exc:  # noqa: BLE001
                ultimo = type(exc).__name__
            if tentativa < TENTATIVAS - 1:
                time.sleep(ESPERA_BASE_S * (tentativa + 1))
        raise FalhaDaInfocap(f"a InfoCap não respondeu {rota}: {ultimo}")

    @staticmethod
    def _linhas(resposta: Any, chave: str) -> List[Dict[str, Any]]:
        """A lista de dentro do envelope.

        📊 As respostas vêm como `{"header": {...}, "<chave>": [...]}` —
        `documentos` no BI, `renovacoes` no radar. O fallback por "a primeira
        lista de dicionários" existe porque descobrir o nome errado da chave
        custou uma medição inteira devolvendo zero linhas com a API respondendo
        certo.
        """
        if isinstance(resposta, list):
            return [x for x in resposta if isinstance(x, dict)]
        if not isinstance(resposta, dict):
            return []
        alvo = resposta.get(chave)
        if isinstance(alvo, list):
            return [x for x in alvo if isinstance(x, dict)]
        for v in resposta.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return []

    # ------------------------------------------------------------- produção
    def producao(self, inicio: date, fim: date) -> List[Apolice]:
        """As APÓLICES emitidas no período, com prêmio e comissão.

        🔴 `tipo_doc="A"` vai na REQUISIÇÃO. 📊 Sem ele vêm 3.272 documentos dos
        quais só 1.680 são apólice — o resto é endosso, proposta, cancelamento.
        Filtrar depois desperdiça metade do payload E derruba a cobertura de
        produtor de 80,6% para 41,4%, porque `/renovacoes` só conhece apólices.

        🔴 `data="INIVIG"` — início de vigência. 📊 A API recusa `DATEMI` com
        400 e devolve a lista dos valores válidos.
        """
        saida: List[Apolice] = []
        for ini, f in _fatiar_por_ano(inicio, fim):
            bruto = self._get("/documentos_bi", {
                "datini": ini.strftime("%d/%m/%Y"),
                "datfim": f.strftime("%d/%m/%Y"),
                "data": "INIVIG",
                "tipo_doc": "A",
            })
            for x in self._linhas(bruto, "documentos"):
                saida.append(Apolice(
                    nosnum=str(x.get("nosnum") or ""),
                    cliente=str(x.get("cliente") or ""),
                    codcli=str(x.get("codcli") or ""),
                    seguradora=str(x.get("seguradora") or "").strip(),
                    ramo=str(x.get("ramo") or "").strip(),
                    inivig=str(x.get("inivig") or ""),
                    fimvig=str(x.get("fimvig") or ""),
                    premio=_num(x.get("pretot")),
                    comissao=_num(x.get("val_c")),
                    base_comissao=_num(x.get("base_c")),
                    # 🔴 `nosnum_ren` aponta a apólice ANTERIOR. Preenchido =
                    # renovação; vazio = negócio novo. É uma lista encadeada
                    # dentro do próprio endpoint.
                    e_renovacao=bool(str(x.get("nosnum_ren") or "").strip()),
                ))
        logger.info("[COMERCIAL] produção %s→%s: %d apólices",
                    inicio, fim, len(saida))
        return saida

    # ----------------------------------------------------------- produtores
    def mapa_de_produtores(self, anos: Iterable[int]) -> Dict[str, ProdutorDaApolice]:
        """`nosnum` → quem vendeu. Varre VÁRIOS anos de VENCIMENTO.

        🔴 Por que vários anos: `/renovacoes` filtra por `fimvig`, e apólice
        anual que começa em 2025 vence em 2026. 📊 A interseção de
        `fimvig-2025` com `inivig-2025` é de apenas **2,8%**. Pedir um ano só
        deixaria 97% da produção sem vendedor.

        📊 Com `fimvig` 2024+2025+2026+2027 o mapa tem 8.894 apólices e cobre
        80,6% da produção de 2025 (86,2% da comissão).

        🔴 `ordem == 1` é o produtor DIRETO — e é SÓ isso. A SPEC original
        exigia `indireto == "F"` junto; 📊 esse campo **não existe** neste
        endpoint. Sem o `ordem==1`, somar todos os produtores TRIPLICARIA o
        faturamento: 📊 a média é de 3 produtores por apólice.
        """
        mapa: Dict[str, ProdutorDaApolice] = {}
        for ano in sorted({int(a) for a in anos}):
            bruto = self._get("/renovacoes", {
                "dt_ini": f"01/01/{ano}", "dt_fim": f"31/12/{ano}",
                "qtd_pag": 5000, "pag": 1, "ordem": "nosnum",
                "orientacao": "asc", "texto": "",
                "cancelado": "F", "resgates": "F",
            })
            for x in self._linhas(bruto, "renovacoes"):
                nos = str(x.get("nosnum") or "")
                if not nos:
                    continue
                # 🔴 A LISTA é a verdade. 📊 Uma linha com
                # `quant_produtores: 3` trouxe `prod_docs` com 2 itens —
                # iterar pelo contador leria fora do array.
                direto = next(
                    (p for p in (x.get("prod_docs") or [])
                     if isinstance(p, dict) and str(p.get("ordem")) == "1"),
                    None)
                nome = str((direto or {}).get("produtor")
                           or x.get("produtor") or "").strip()
                if not nome:
                    continue
                mapa[nos] = ProdutorDaApolice(
                    nosnum=nos,
                    codigo=str((direto or {}).get("cod_pro") or ""),
                    nome=nome,
                    repasse=_num((direto or {}).get("val_r")),
                    percentual=_num((direto or {}).get("per_r")),
                )
        logger.info("[COMERCIAL] mapa de produtores: %d apólices em %s anos",
                    len(mapa), len(list(anos)) if not isinstance(anos, list) else len(anos))
        return mapa

    # ----------------------------------------------------------- vencimentos
    def carteira_a_vencer(self, inicio: date, fim: date) -> List[Vencimento]:
        """O que vence no período, com contato do segurado e vendedor.

        🔴 Filtra `tipdoc == "A"` e `cancelado` AQUI, no cliente — e não numa
        chamada extra a `/producao`. 📊 Os dois campos vêm na própria linha de
        `/renovacoes`, o que resolve a invariante "cancelada não entra em
        número nenhum" sem custar uma requisição.

        📊 `dias_a_vencer` pode ser NEGATIVO (medido: -429). A API devolve
        vencidas dentro da janela; quem chama decide se as quer.
        """
        saida: List[Vencimento] = []
        for ini, f in _fatiar_por_ano(inicio, fim):
            bruto = self._get("/renovacoes", {
                "dt_ini": ini.strftime("%d/%m/%Y"),
                "dt_fim": f.strftime("%d/%m/%Y"),
                "qtd_pag": 5000, "pag": 1, "ordem": "nosnum",
                "orientacao": "asc", "texto": "",
                "cancelado": "F", "resgates": "F",
            })
            for x in self._linhas(bruto, "renovacoes"):
                if str(x.get("tipdoc") or "").strip().upper() != "A":
                    continue
                if str(x.get("cancelado") or "").strip().upper() in ("T", "S", "TRUE", "1"):
                    continue
                direto = next(
                    (p for p in (x.get("prod_docs") or [])
                     if isinstance(p, dict) and str(p.get("ordem")) == "1"),
                    None)
                saida.append(Vencimento(
                    nosnum=str(x.get("nosnum") or ""),
                    cliente=str(x.get("cliente") or ""),
                    codcli=str(x.get("codcli") or ""),
                    seguradora=str(x.get("seguradora") or "").strip(),
                    ramo=str(x.get("ramo") or "").strip(),
                    fimvig=str(x.get("fimvig") or ""),
                    dias_a_vencer=int(_num(x.get("dias_a_vencer"))),
                    premio=_num(x.get("pretot")),
                    produtor=str((direto or {}).get("produtor")
                                 or x.get("produtor") or "").strip(),
                    telefone=str(x.get("fone") or "").strip(),
                    email=str(x.get("email") or "").strip(),
                    tipdoc=str(x.get("tipdoc") or ""),
                    tem_sinistro=bool(str(x.get("sin_situacao") or "").strip()),
                ))
        logger.info("[COMERCIAL] carteira a vencer %s→%s: %d apólices",
                    inicio, fim, len(saida))
        return saida


# --------------------------------------------------------------------------
# Ajudantes puros
# --------------------------------------------------------------------------
def _num(v: Any) -> float:
    """Número, com zero para o que não é número.

    📊 A API devolve `None` em `val_c` de `/renovacoes` e vírgula decimal em
    alguns campos de texto. Um `float()` cru derruba o relatório inteiro por
    causa de uma linha.
    """
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(".", "").replace(",", ".")
                     if str(v).count(",") == 1 and str(v).count(".") != 1
                     else str(v))
    except (TypeError, ValueError):
        return 0.0


def _fatiar_por_ano(inicio: date, fim: date) -> List[tuple]:
    """Quebra a janela em pedaços de no máximo um ano.

    🔴 Não é otimização: é o teto MEDIDO. 📊 `/documentos_bi` de 2020 a 2026
    devolve **HTTP 502 aos 28 segundos**; `/renovacoes` de 2018 a 2032 também.
    Ano a ano nunca falhou — 8 s, 4 s e 3 s nas três medições.

    Fatiar no limite do ano CIVIL, e não em blocos de 366 dias corridos, porque
    a API pensa em ano e porque assim duas chamadas para o mesmo ano produzem a
    mesma chave de cache.
    """
    if fim < inicio:
        inicio, fim = fim, inicio
    pedacos: List[tuple] = []
    ano = inicio.year
    while ano <= fim.year:
        ini = max(inicio, date(ano, 1, 1))
        f = min(fim, date(ano, 12, 31))
        if ini <= f:
            pedacos.append((ini, f))
        ano += 1
    return pedacos


def anos_de_vencimento_para(inicio: date, fim: date) -> List[int]:
    """Quais anos de `fimvig` cobrem a produção deste período.

    🔴 A regra vem da medição, não da intuição: apólice que COMEÇA no ano N
    vence no ano N+1 (anual) ou depois (plurianual). 📊 Varrer de N-1 a N+2 deu
    80,6% de cobertura em 2025; um ano só daria 2,8%.

    N-1 entra porque existe apólice de vigência curta que começa e termina no
    mesmo ano, e apólice retroativa.
    """
    return list(range(inicio.year - 1, fim.year + 3))
