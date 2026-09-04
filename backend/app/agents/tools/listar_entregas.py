# -*- coding: utf-8 -*-
"""O chat lembra o que já entregou — SPEC-094.1 · BLOCO C.

📊 Medido em 03/09/2026 (§1.2 da SPEC-094.1): `grep -rn 'table("artifacts")'
backend/app/agents/` → **0**. O produto publicou **126 Artifacts** em três
corretoras e o chat que os publicou não conseguia citar um. O dono pergunta
*"o que você já me entregou este mês?"* e a resposta era prosa de memória —
quando havia resposta.

## O que esta tool é, e o que ela não é

```
✅ uma tool FINA sobre `ArtifactService.listar(company_id, limite)`
⛔ não é um segundo catálogo de entregas          (CLAUDE.md §5)
⛔ não é um segundo caminho de publicação          quem publica é `_publicar`
⛔ não devolve `payload` cru                       nem um pedaço dele
```

🔴 **O `payload` NUNCA sai daqui.** Ele carrega o `evidence_pack` inteiro e,
no Pulso 360, a chave `rotulos_de_produtor` — que é o único lugar do produto
onde o NOME de uma pessoa mora de propósito (SPEC-094 §2, mutação M16). Uma
listagem que devolvesse o payload levaria esse nome para dentro da string do
modelo, que é exatamente a fronteira que a 094 gastou um bloco fechando. O que
sai é a ficha: título, data, template, `pack_id`, estado e o LINK.

🔴 **`pack_id` é o ELO, e é por isso que ele vale a segunda consulta.** Com ele
o dono pergunta *"e sobre aquele relatório de agosto?"* e a
`executive_intelligence` responde do MESMO pacote, sem reconsultar a carteira —
os números continuam sendo os mesmos números. Sem ele, cada pergunta de
acompanhamento seria uma leitura nova, e duas leituras da mesma carteira em
minutos diferentes não devolvem o mesmo número.

⚠️ O link é o AUTENTICADO do dashboard (`_link`, o mesmo formato das duas
tools da 081). O link público de `compartilhar()` fica FORA: 📊 `artifact_shares`
= 0 — ele nunca funcionou em produção, e está registrado em
`P-094.1-LINK-PUBLICO`.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

#: 💭 Quantas entregas cabem numa resposta de chat sem virar despejo. Vinte
#: são cerca de meio ano de trabalho numa corretora ativa.
TETO_PADRAO = 20
#: 🔴 O teto DURO. O modelo preenche `limite`; um pedido de 5.000 viraria uma
#: leitura de tabela inteira disfarçada de pergunta.
TETO_MAXIMO = 60

CARIMBO_PRONTO = "ENTREGAS_LISTADAS"
CARIMBO_VAZIO = "ENTREGAS_VAZIO"
CARIMBO_FALHOU = "ENTREGAS_FALHOU"

ABERTURA = "<<ENTREGAS"
FECHAMENTO = "ENTREGAS>>"

COMO_FALAR = (
    "Cite SÓ as entregas do bloco ENTREGAS acima, com o título e a data como "
    "estão lá, e ofereça o link de cada uma. NUNCA invente uma entrega que não "
    "esteja no bloco, e nunca descreva o CONTEÚDO de um relatório a partir "
    "desta lista — ela tem a ficha da peça, não os números dela. Para falar dos "
    "números, abra o relatório ou peça um panorama novo. Se uma entrega trouxer "
    "`pack_id`, você pode repassá-lo à ferramenta de panorama executivo para "
    "responder sobre AQUELE mesmo pacote, sem reconsultar."
)


class RecusaSemTenant(RuntimeError):
    """Não há corretora nesta sessão. 🔴 Levanta — não lista "tudo".

    ⚠️ O prefixo `Recusa` não é decorativo: `_erro_legivel` classifica a
    exceção pelo NOME da classe, e é ele que faz o motivo chegar legível ao
    modelo em vez de virar jargão de encanamento.

    🔴 E a razão de levantar, em vez de devolver lista vazia: o backend roda com
    **service role**, então `RLS` sem filtro no código não protege nada
    (CLAUDE.md §7). Uma consulta a `artifacts` sem `company_id` devolveria as
    entregas de TODAS as corretoras. Lista vazia esconderia o defeito; a
    exceção o mostra na primeira execução.
    """


class PlanoDeEntregas(BaseModel):
    """O que o modelo preenche. Três campos, e nenhum deles é uma consulta."""

    periodo: str = Field(
        default="",
        description=(
            "O período que o dono pediu, COMO ELE FALOU: 'este mês', 'agosto', "
            "'2025', 'últimos 30 dias'. Vazio = tudo o que existe, do mais "
            "recente para o mais antigo — que é o certo para 'o que você já me "
            "entregou?'. NUNCA pergunte o período de volta."),
    )
    template: str = Field(
        default="",
        description=(
            "Filtre por TIPO de entrega quando ele nomear um: 'pulso', "
            "'renovações', 'raio-x', 'cobrança'. Vazio = todos os tipos."),
    )
    limite: int = Field(
        default=TETO_PADRAO,
        description=(
            "Quantas entregas no máximo. Vazio/0 = %d. Só aumente se ele pedir "
            "explicitamente uma lista longa." % TETO_PADRAO),
    )


# ==========================================================================
# As peças de leitura
# ==========================================================================
def _quando(linha: Dict[str, Any]) -> Optional[date]:
    """A data de criação da entrega, ou `None` quando ilegível.

    ⚠️ Ilegível **não** vira "hoje" nem é descartada em silêncio: a entrega
    entra na lista sem data, e o filtro de período a mantém fora só quando o
    dono pediu um período. Inventar a data faria a peça aparecer no mês errado.
    """
    bruto = str(linha.get("created_at") or "").strip()
    if not bruto:
        return None
    try:
        return datetime.fromisoformat(bruto.replace("Z", "+00:00")).date()
    except Exception:  # noqa: BLE001
        try:
            return date(int(bruto[0:4]), int(bruto[5:7]), int(bruto[8:10]))
        except Exception:  # noqa: BLE001
            return None


def _casa_o_template(linha: Dict[str, Any], pedido: str) -> bool:
    """O tipo pedido casa esta entrega? Sobre `template_key`, `title` e `kind`.

    ⚠️ O casamento é por SUBSTRING normalizada porque o campo do modelo é texto
    livre ("pulso", "renovações") e a chave é técnica (`executive.pulse360`).
    Isto é um FILTRO de listagem — nada é calculado a partir dele, e o pior
    caso é uma lista mais curta do que o dono queria, que ele corrige numa
    frase. (Compare com `dimension` da 094, que recorta NÚMERO e por isso exige
    lista fechada.)
    """
    if not pedido:
        return True
    from app.comercial.evidence_pack import normalizar_rotulo

    alvo = normalizar_rotulo(pedido)
    if not alvo:
        return True
    campos = " ".join(str(linha.get(c) or "") for c in
                      ("template_key", "title", "subtitle", "kind"))
    return alvo in normalizar_rotulo(campos)


def _packs_das_versoes(db: Any, company_id: str,
                       ids: List[str]) -> Dict[str, str]:
    """`{artifact_id: pack_id}` — da versão CORRENTE, quando houver.

    🔴 A leitura é filtrada por `company_id` **e** por `status='published'`. O
    filtro de tenant é a proteção real (service role, CLAUDE.md §7); o de
    status é o que garante que o `pack_id` devolvido é o da peça que o link
    abre, e não o de um rascunho superado.

    ⚠️ Falha aqui NÃO derruba a listagem: `pack_id` é um extra: a lista sem ele
    continua respondendo à pergunta do dono. O que ela não pode é sumir porque
    uma segunda consulta falhou.

    ⛔ E ela seleciona `payload` porque não há outro lugar onde o `pack_id`
    exista — mas o payload morre DENTRO desta função. Nada dele sobe.
    """
    if not ids:
        return {}
    try:
        r = (db.table("artifact_versions")
             .select("artifact_id, payload, status")
             .eq("company_id", company_id).eq("status", "published")
             .in_("artifact_id", ids).execute())
        linhas = getattr(r, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[094.1] pack_id nao resolvido (%s)", type(exc).__name__)
        return {}
    saida: Dict[str, str] = {}
    for v in linhas:
        pacote = ((v.get("payload") or {}).get("evidence_pack") or {})
        ident = str(pacote.get("pack_id") or "").strip()
        if ident:
            saida[str(v.get("artifact_id"))] = ident
    return saida


def _ficha(linha: Dict[str, Any], pack_id: str, link: str) -> Dict[str, Any]:
    """A ficha de UMA entrega — a lista fechada de campos que podem sair.

    🔴 Esta função é o único lugar que monta o item do bloco, e ela nomeia os
    campos um a um. Não é verbosidade: um `dict(linha)` com um `pop("payload")`
    passaria a vazar no dia em que a `listar()` selecionasse uma coluna nova, e
    o vazamento seria silencioso.
    """
    return {
        "artifact_id": str(linha.get("id") or ""),
        "titulo": str(linha.get("title") or "").strip() or "(sem título)",
        "criado_em": str(linha.get("created_at") or "")[:10],
        "template": str(linha.get("template_key") or ""),
        "tipo": str(linha.get("kind") or ""),
        "status": str(linha.get("status") or ""),
        "pack_id": pack_id,
        "link": link,
    }


class ListarEntregasTool(BaseTool):
    """As entregas que esta corretora já recebeu, com o link de cada uma."""

    exige_async: ClassVar[bool] = True

    name: str = "listar_entregas"
    description: str = (
        "AS ENTREGAS QUE VOCÊ JÁ FEZ para esta corretora: os relatórios e "
        "peças publicados, do mais recente para o mais antigo, com título, "
        "data e o LINK de cada um. "
        "Use quando o dono perguntar: o que você já me entregou, quais "
        "relatórios eu tenho, me manda o link daquele relatório, o que saiu "
        "este mês, cadê o panorama que você fez. "
        "Ela lista as PEÇAS — não os números dentro delas. Para números, use a "
        "ferramenta de panorama executivo. "
        "Se ele não disser o período, mande string vazia — NUNCA pergunte de "
        "volta."
    )
    args_schema: Type[BaseModel] = PlanoDeEntregas

    company_id: Optional[str] = None
    supabase: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        raise RuntimeError(
            "ListarEntregasTool exige execução assíncrona. Quem chamou ignorou "
            "`exige_async=True` — o executor precisa aguardar `_arun`.")

    async def _arun(self, periodo: str = "", template: str = "",
                    limite: int = TETO_PADRAO, **_: Any) -> str:
        try:
            return await asyncio.to_thread(self._montar, periodo, template,
                                           limite)
        except Exception as exc:  # noqa: BLE001
            logger.error("[094.1 ENTREGAS] falhou (%s): %s",
                         type(exc).__name__, exc)
            return self._erro_legivel(exc)

    # ------------------------------------------------------------------ #
    def _montar(self, periodo: str, template: str, limite: int) -> str:
        company_id = str(self.company_id or "").strip()
        # 🔴 A primeira linha do corpo, antes de qualquer consulta E antes de
        # qualquer import. A recusa por falta de tenant não pode depender de um
        # módulo pesado carregar: se ela ficasse depois do import, um
        # `ImportError` transformaria "não há corretora nesta sessão" em "a
        # consulta não completou" — e as duas frases mandam o dono fazer coisas
        # diferentes.
        if not company_id:
            raise RecusaSemTenant(
                "não há corretora nesta sessão: listar entregas sem "
                "`company_id` leria as peças de TODAS as corretoras")

        db = getattr(self.supabase, "client", self.supabase)
        if db is None:
            raise RuntimeError("sem cliente de banco para listar entregas")

        from app.services.artifacts.service import ArtifactService

        teto = TETO_PADRAO if not limite or limite < 1 else min(int(limite),
                                                                TETO_MAXIMO)
        janela, rotulo = self._janela(periodo)

        # ⚠️ O teto do SERVIÇO é o teto do filtro, e não o da resposta: filtrar
        # por período depois de cortar em 20 devolveria "nenhuma entrega em
        # março" só porque março ficou abaixo das 20 mais recentes.
        bruto = ArtifactService(db).listar(company_id, limite=TETO_MAXIMO * 4)
        linhas = [x for x in bruto if _casa_o_template(x, template)]
        if janela is not None:
            inicio, fim = janela
            linhas = [x for x in linhas
                      if (_quando(x) is not None
                          and inicio <= _quando(x) <= fim)]
        linhas = linhas[:teto]

        if not linhas:
            return (f"{CARIMBO_VAZIO} · nenhuma entrega{rotulo}"
                    f"{self._sufixo_do_tipo(template)}. Diga isso ao dono e "
                    "ofereça gerar uma agora. NÃO invente entrega nenhuma.")

        from app.agents.tools.relatorios_comerciais import _link

        packs = _packs_das_versoes(db, company_id,
                                   [str(x.get("id")) for x in linhas if x.get("id")])
        fichas = [_ficha(x, packs.get(str(x.get("id")), ""),
                         _link(str(x.get("id")))) for x in linhas]
        corpo = json.dumps({"company_id": company_id,
                            "periodo": rotulo.strip(" ·em") or "tudo",
                            "total": len(fichas), "entregas": fichas},
                           ensure_ascii=False, allow_nan=False)
        return (f"{CARIMBO_PRONTO} · {len(fichas)} entrega(s){rotulo}.\n\n"
                f"{ABERTURA}\n{corpo}\n{FECHAMENTO}\n\n{COMO_FALAR}")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _janela(periodo: str) -> Tuple[Optional[Tuple[date, date]], str]:
        """`((inicio, fim) ou None, rótulo para a frase)`.

        🔴 Período vazio devolve `None`, e `None` quer dizer **sem filtro** —
        não "o ano corrente". `entender_periodo` nunca levanta e cai num padrão
        quando não entende (📊 `calculos.py:347`), então usá-lo com string vazia
        esconderia as entregas do ano passado atrás de um filtro que o dono não
        pediu.
        """
        if not (periodo or "").strip():
            return None, ""
        from app.comercial import calculos

        p = calculos.entender_periodo(periodo)
        if getattr(p, "e_padrao", False):
            # Não entendemos o que ele disse. Listar TUDO e avisar é honesto;
            # listar um período inventado é responder outra pergunta.
            return None, " (não entendi o período; listei tudo)"
        return (p.inicio, p.fim), " em %s" % p.rotulo

    @staticmethod
    def _sufixo_do_tipo(template: str) -> str:
        return " do tipo '%s'" % template.strip() if (template or "").strip() else ""

    @staticmethod
    def _erro_legivel(exc: Exception) -> str:
        """O que o modelo deve DIZER quando não deu. Instrução, não relato.

        Mesma classificação por NOME de classe da 081/094: o tratador de erro
        não importa nada, porque na 081 a versão que importava quebrava junto
        quando o que falhava ERA o import.
        """
        nome = type(exc).__name__
        conhecida = nome.startswith("Falha") or nome.startswith("Recusa")
        motivo = str(exc)[:220] if conhecida else nome
        return (
            f"{CARIMBO_FALHOU} · a lista de entregas NÃO foi levantada. É "
            "PROIBIDO citar qualquer relatório ou mandar qualquer endereço "
            "agora. Diga a verdade: a consulta não completou, e ofereça tentar "
            f"de novo. Motivo interno: {motivo}"
        )


# --------------------------------------------------------------------------
def ferramenta_de_entregas(*, company_id: Optional[str],
                           supabase: Any) -> List[BaseTool]:
    """A tool, ou lista vazia. Nunca levanta na montagem do grafo.

    🔴 Ela entra pela LISTA de `ferramentas_comerciais`, e não por uma chamada
    nova em `graph.py`: assim herda o `if` fechado por papel (📊 `graph.py:528`)
    que já está provado, em vez de depender de alguém repetir a condição. Fora
    daquele `if`, o agente de ATENDIMENTO — que fala com o SEGURADO — passaria a
    poder listar os relatórios internos da corretora.
    """
    if not company_id or supabase is None:
        return []
    supabase = getattr(supabase, "client", supabase)
    return [ListarEntregasTool(company_id=str(company_id), supabase=supabase)]
