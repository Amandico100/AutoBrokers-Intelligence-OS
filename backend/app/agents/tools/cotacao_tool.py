# -*- coding: utf-8 -*-
"""A COTAÇÃO RÁPIDA no chat — SPEC-132-B (B1). Três ferramentas do agente CORE, um caminho:

    cotacao_preparar(campos…)        valida, a placa supre o carro, a apólice anexada supre o que tiver → o que FALTA
                                     (em português de gente) ou o RESUMO + `confirmacao_id` (30 min, uma vez)
    cotacao_disparar(confirmacao_id) o "sim" do corretor → `porta.calcular(servico="cotacao", solicitante_user_id=…)`
                                     → o Work Run `cotacao.chat` (responde NESTA conversa) → "Calculando…"
    cotacao_ajustar(pedido_id, …)    o recálculo (franquia, comissão, coberturas…) SÓ pela `porta.recalcular`

⛔ Não é motor paralelo (CLAUDE.md §5): quem calcula é a PORTA + o motor do portal-worker; quem decide a conta é o
   `qual_agger` (a pessoa → a corretora com aviso); quem publica é a B2; quem espera e responde é o Work OS.
🔴 `company_id` vem do CONSTRUTOR (o grafo é por corretora); `user_id` e `session_id` vêm do TURNO, injetados pelo
   `tool_node` (nunca do modelo — o grafo é cacheado e reusado entre pessoas). A conversa é a desta sessão NESTA
   corretora, e tem de ser de quem está pedindo.
🔴 O CPF nunca volta cru ao modelo: toda saída passa por `resposta.sem_documento_inteiro`.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

NOMES = ("cotacao_preparar", "cotacao_disparar", "cotacao_ajustar")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class Recusa(Exception):
    def __init__(self, frase: str):
        self.frase = frase
        super().__init__(frase)


def _saida(texto: str) -> str:
    from app.services.cotacao.resposta import sem_documento_inteiro

    return sem_documento_inteiro(texto)


# =====================================================================================================================
# os esquemas (o que o MODELO preenche) — nenhum campo de identidade (empresa, pessoa, conversa) mora aqui
# =====================================================================================================================
class _PrepararIn(BaseModel):
    ramo: Optional[str] = Field(None, description="carro (padrão), residencial, condomínio ou empresarial")
    cpf_cnpj: Optional[str] = Field(None, description="CPF do cliente (ou CNPJ, se empresa), como o corretor escreveu")
    nome: Optional[str] = Field(None, description="nome completo do cliente")
    nascimento: Optional[str] = Field(None, description="data de nascimento do cliente, dd/mm/aaaa")
    sexo: Optional[str] = Field(None, description="masculino ou feminino, só se o corretor disse")
    cep: Optional[str] = Field(None, description="CEP do cliente")
    email: Optional[str] = None
    telefone: Optional[str] = None
    placa: Optional[str] = Field(None, description="placa do carro — com ela o Agger acha modelo, ano e combustível")
    descricao_do_veiculo: Optional[str] = Field(None, description="o carro como o corretor falou (ex.: 'Onix 2022')")
    fipe: Optional[str] = Field(None, description="código FIPE, só se o corretor deu (sem placa)")
    ano_fabricacao: Optional[str] = None
    ano_modelo: Optional[str] = None
    combustivel: Optional[str] = Field(None, description="flex, gasolina, álcool, diesel, elétrico, híbrido")
    zero_km: Optional[str] = Field(None, description="sim/não")
    cep_pernoite: Optional[str] = Field(None, description="CEP onde o carro dorme, se for diferente do CEP do cliente")
    anos_de_carteira: Optional[str] = Field(None, description="há quantos anos o principal condutor tem carteira")
    jovem_condutor: Optional[str] = Field(None, description="alguém de 18 a 25 anos dirige? sim/não")
    condutor_cpf: Optional[str] = Field(None, description="CPF de quem mais dirige, só se NÃO for o cliente")
    condutor_nome: Optional[str] = None
    condutor_nascimento: Optional[str] = None
    condutor_sexo: Optional[str] = None
    risco: Optional[Dict[str, Any]] = Field(
        None, description="RE (residencial/condomínio/empresarial): o imóvel — cep, logradouro, numero, bairro, "
                          "cidade, uf, valor_basica (o valor a segurar contra incêndio) e os campos que a ferramenta "
                          "pedir pelo nome (ex.: tipo_imovel, construcao, uso, objeto, atividade)")
    usar_apolice_anexada: Optional[bool] = Field(
        False, description="true quando o corretor anexou a apólice atual do cliente nesta conversa")
    nome_do_anexo: Optional[str] = Field(None, description="o nome do PDF, se houver mais de um anexo")
    seguradora_atual: Optional[str] = Field(None, description="a seguradora do seguro atual, se o corretor disse")
    premio_atual_anual: Optional[str] = Field(None, description="quanto o cliente paga hoje por ano, se disse")


class _DispararIn(BaseModel):
    confirmacao_id: str = Field(description="o confirmacao_id que a cotacao_preparar devolveu")


class _AjustarIn(BaseModel):
    pedido_id: str = Field(description="o pedido_id que a cotacao_disparar devolveu")
    tipo: str = Field(description="franquia · comissao · desconto · assistencia · carro_reserva · vidros")
    valor: str = Field(description="ex.: franquia 'reduzida' ou 'normal'; comissão '15'; assistência 'completa'")
    opcao: Optional[str] = Field("recomendada", description="qual versão: recomendada (padrão), mais em conta, "
                                                           "mais completa")
    seguradora: Optional[int] = Field(None, description="o código da seguradora, se o ajuste é só numa")


# =====================================================================================================================
# a base: o turno (quem, em qual conversa)
# =====================================================================================================================
class _Cotacao(BaseTool):
    exige_async: ClassVar[bool] = True
    company_id: Optional[str] = None
    supabase: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, *a: Any, **k: Any) -> str:
        raise RuntimeError(f"{self.name} exige execução assíncrona — o executor precisa aguardar `_arun`.")

    def _db(self) -> Any:
        return getattr(self.supabase, "client", self.supabase)

    def _turno(self, user_id: Optional[str], session_id: Optional[str]) -> Tuple[Any, str, str, str]:
        """(db, company_id, user_id, conversation_id) — ou `Recusa` com a frase."""
        company_id = str(self.company_id or "").strip()
        if not company_id:
            raise Recusa("Não consegui identificar a corretora desta conversa.")
        if not user_id:
            try:
                from app.core.request_context import get_current_user_id

                user_id = get_current_user_id()
            except Exception:  # noqa: BLE001
                user_id = None
        if not user_id or not _UUID.match(str(user_id)):
            raise Recusa("Não consegui identificar quem está pedindo a cotação — recarregue a página e peça de novo.")
        if not session_id:
            raise Recusa("Não consegui identificar esta conversa — recarregue a página e peça de novo.")
        db = self._db()
        linhas = list(getattr(db.table("conversations").select("id, company_id, user_id, session_id, created_at")
                              .eq("company_id", company_id).eq("session_id", str(session_id))
                              .order("created_at", desc=True).limit(1).execute(), "data", None) or [])
        linhas = [c for c in linhas if str(c.get("company_id")) == company_id]
        if not linhas:
            raise Recusa("Não achei esta conversa na sua corretora — mande a mensagem de novo para eu abrir a conversa.")
        conversa = linhas[0]
        if conversa.get("user_id") and str(conversa["user_id"]) != str(user_id):
            raise Recusa("Esta conversa é de outra pessoa da equipe — a cotação sai na conversa de quem pediu.")
        from portal_worker.multicalculo import robos as ROB

        if not ROB.membro_ativo(db, company_id, str(user_id)):
            raise Recusa("Só quem está ativo na equipe desta corretora pode pedir cotação.")
        return db, company_id, str(user_id), str(conversa["id"])


# =====================================================================================================================
# preparar
# =====================================================================================================================
class CotacaoPrepararTool(_Cotacao):
    name: str = "cotacao_preparar"
    description: str = (
        "PREPARA uma cotação de seguro (carro, residencial, condomínio, empresarial) com o que o corretor já disse — "
        "use quando ele pedir para cotar, calcular ou fazer o preço de um seguro. Passe só o que veio na conversa "
        "(nunca invente); com a placa o Agger acha o carro; se ele anexou a apólice, use usar_apolice_anexada=true. "
        "A ferramenta devolve o que FALTA (pergunte tudo numa mensagem só, sem pedir o que já veio) ou um RESUMO com "
        "um confirmacao_id. Mostre o resumo e peça um 'sim' explícito; só depois chame cotacao_disparar. "
        "Moto, frota e RCF-V não saem por aqui.")
    args_schema: Type[BaseModel] = _PrepararIn

    async def _arun(self, user_id: Optional[str] = None, session_id: Optional[str] = None, **campos: Any) -> str:
        try:
            return _saida(await self._preparar(user_id, session_id, campos))
        except Recusa as r:
            return _saida(r.frase)
        except Exception as exc:  # noqa: BLE001
            logger.error("[COTACAO] preparar falhou (%s)", type(exc).__name__)
            return "Não consegui preparar a cotação agora — o problema é do nosso lado. Tente de novo em instantes."

    async def _preparar(self, user_id: Optional[str], session_id: Optional[str], campos: Dict[str, Any]) -> str:
        from app.services.cotacao import confirmacao as CONF
        from app.services.cotacao import pedido_da_conversa as PC
        from app.services.cotacao.resposta import onde_calcula
        from app.services.multicalculo import qual_agger

        db, company_id, user_id, conversa = await asyncio.to_thread(self._turno, user_id, session_id)
        avisos: List[str] = []
        ficha = None
        if campos.get("usar_apolice_anexada") or campos.get("nome_do_anexo"):
            ficha, aviso = await PC.ficha_do_anexo(db, company_id, conversa, nome=campos.get("nome_do_anexo"))
            if aviso:
                avisos.append(aviso)
        textos = await asyncio.to_thread(PC.textos_crus_da_conversa, db, conversa)
        cfg = await asyncio.to_thread(_config, company_id, db)
        dados = {k: v for k, v in campos.items() if k not in ("usar_apolice_anexada", "nome_do_anexo")}
        try:
            m = PC.montar(dados, ficha=ficha, textos_crus=textos, config=cfg)
        except PC.ForaDoEscopo as fora:
            return fora.frase
        if not m.completa:
            linhas = [x for x in avisos]
            linhas.append("PARA O CORRETOR — " + PC.frase_do_que_falta(m))
            linhas.append("(Pergunte tudo isso numa mensagem só; não peça de novo o que ele já disse. Quando ele "
                          "responder, chame a cotacao_preparar de novo com TODOS os dados.)")
            if m.ramo != PC.RAMO_AUTO and m.faltam:
                linhas.append("Campos do imóvel para a próxima chamada (em `risco`): "
                              + ", ".join(sorted({f.split(".", 1)[1] for f in m.faltam if f.startswith("risco.")})))
            return "\n".join(linhas)
        opcoes = PC.opcoes_da_cotacao(cfg, m.ramo)
        decisao = await asyncio.to_thread(qual_agger.decidir, db, company_id=company_id, servico="cotacao",
                                          solicitante_user_id=user_id)
        conteudo = {"ramo": m.ramo, "campos": {g: dict(v) for g, v in m.pedido.campos.items()},
                    "assumidos": sorted(m.pedido.assumidos), "opcoes": list(opcoes), "situacao": m.situacao,
                    "apolice_atual": m.apolice_atual, "descricao": m.descricao}
        try:
            cid = await CONF.guardar(company_id=company_id, user_id=user_id, conversation_id=conversa,
                                     conteudo=conteudo)
        except CONF.ConfirmacaoRecusada as r:
            return r.frase
        partes = avisos + [PC.resumo(m, onde=onde_calcula(decisao), opcoes=opcoes),
                           f"confirmacao_id: {cid}",
                           "(Para o assistente: mostre o resumo acima e pergunte se pode calcular. Só com um 'sim' "
                           "explícito do corretor chame cotacao_disparar com este confirmacao_id — ele vale 30 minutos "
                           "e uma vez. Não mostre o confirmacao_id ao corretor.)"]
        return "\n".join(partes)


def _config(company_id: str, db: Any) -> Optional[Dict[str, Any]]:
    try:
        from app.services.multicalculo import config as CFG

        return CFG.carregar(company_id, db=db, servico="cotacao")
    except Exception as exc:  # noqa: BLE001 — sem a config, as opções do produto
        logger.warning("[COTACAO] config da cotação ilegível (%s) — vale o padrão", type(exc).__name__)
        return None


# =====================================================================================================================
# disparar
# =====================================================================================================================
def _porta(db: Any) -> Any:
    from app.services.multicalculo.porta import MulticalculoProvider
    from app.services.multicalculo.repositorio import RepositorioMulticalculo

    return MulticalculoProvider(RepositorioMulticalculo(db))


def frase_da_recusa_da_porta(exc: BaseException) -> str:
    """O que a porta recusou, em português de gente (nunca o nome da exceção)."""
    from app.services.cotacao.pedido_da_conversa import _juntar, rotulos_do_que_falta
    from app.services.multicalculo import porta as P

    if isinstance(exc, P.ContaRecusada):
        return exc.frase
    if isinstance(exc, (P.PedidoIncompleto, P.PerfilIncompleto)):
        return "Ainda falta: " + _juntar(rotulos_do_que_falta(list(exc.campos), tem_placa=True)) + \
            ". Me diga isso e eu preparo de novo."
    if isinstance(exc, P.NaoAutorizado):
        return "Não consegui calcular por esta corretora — a cotação só sai pela própria corretora de quem pediu."
    if isinstance(exc, P.ChaveAusente):
        return "A cotação está desligada neste ambiente (falta uma configuração do lado do AutoBrokers)."
    if isinstance(exc, P.RamoNaoSuportado):
        return "Esse ramo eu ainda não calculo por aqui — cote direto no Agger."
    return "Não consegui começar o cálculo agora — o problema é do nosso lado, não dos dados. Tente de novo em instantes."


class CotacaoDispararTool(_Cotacao):
    name: str = "cotacao_disparar"
    description: str = (
        "CALCULA a cotação que a cotacao_preparar resumiu — SÓ depois de o corretor confirmar o resumo com um 'sim' "
        "explícito ('sim', 'pode', 'calcula'). Recebe o confirmacao_id (vale uma vez, por 30 minutos). O resultado "
        "volta sozinho nesta conversa em 1 a 2 minutos; repita ao corretor a frase que a ferramenta devolver.")
    args_schema: Type[BaseModel] = _DispararIn

    async def _arun(self, confirmacao_id: str = "", user_id: Optional[str] = None, session_id: Optional[str] = None,
                    **_: Any) -> str:
        try:
            return _saida(await self._disparar(confirmacao_id, user_id, session_id))
        except Recusa as r:
            return _saida(r.frase)
        except Exception as exc:  # noqa: BLE001
            logger.error("[COTACAO] disparar falhou (%s)", type(exc).__name__)
            return frase_da_recusa_da_porta(exc)

    async def _disparar(self, confirmacao_id: str, user_id: Optional[str], session_id: Optional[str]) -> str:
        from app.services.cotacao import confirmacao as CONF
        from app.services.cotacao import workflow as WF
        from app.services.cotacao.resposta import frase_calculando, onde_pelas_contas
        from app.services.multicalculo.pedido import PedidoDeCalculo

        db, company_id, user_id, conversa = await asyncio.to_thread(self._turno, user_id, session_id)
        try:
            c = await CONF.consumir(company_id=company_id, user_id=user_id, conversation_id=conversa,
                                    confirmacao_id=confirmacao_id)
        except CONF.ConfirmacaoRecusada as r:
            return r.frase
        pedido = PedidoDeCalculo.de_dict(c.get("campos") or {}, ramo=int(c.get("ramo") or 31),
                                         assumidos=c.get("assumidos") or ())
        try:
            aberto = await _porta(db).calcular(company_id=company_id, pedido=pedido,
                                               opcoes=tuple(c.get("opcoes") or ("padrao",)),
                                               servico="cotacao", solicitante_user_id=user_id)
        except Exception as exc:  # noqa: BLE001 — nomes de exceção e campos no log; valores nunca
            logger.warning("[COTACAO] a porta recusou (%s %s)", type(exc).__name__,
                           ",".join(getattr(exc, "campos", []) or []))
            return frase_da_recusa_da_porta(exc)
        contas = await asyncio.to_thread(WF.contas_do_pedido, db, company_id, aberto.pedido_id)
        run_id = await asyncio.to_thread(WF.abrir, db, company_id=company_id, user_id=user_id,
                                         conversation_id=conversa, pedido_id=aberto.pedido_id,
                                         situacao=str(c.get("situacao") or "novo_sem_apolice"),
                                         apolice_atual=c.get("apolice_atual"))
        if not run_id:
            return ("O cálculo começou, mas não consegui acompanhá-lo para responder aqui — o resultado fica em "
                    "Cotação Rápida → Cotações.")
        return (frase_calculando(onde_pelas_contas(contas))
                + f"\n(Para o assistente: pedido_id {aberto.pedido_id} — use-o na cotacao_ajustar; não o mostre.)")


# =====================================================================================================================
# ajustar
# =====================================================================================================================
_OPCAO_DO_TEXTO = {"recomendada": "padrao", "padrao": "padrao", "mais em conta": "economica", "economica": "economica",
                   "mais completa": "completa_mais", "completa_mais": "completa_mais", "completa": "padrao"}
_TIPOS = ("franquia", "comissao", "desconto", "assistencia", "carro_reserva", "vidros")


def _rotulo_do_ajuste(tipo: str, valor: Any) -> str:
    v = str(valor).strip()
    return {"franquia": f"a franquia {v}", "comissao": f"comissão de {v}%", "desconto": f"desconto de {v}%",
            "assistencia": f"a assistência {v}", "carro_reserva": f"carro reserva de {v}",
            "vidros": f"vidros {v}"}.get(tipo, f"o ajuste de {tipo}")


def _calculo_para_ajustar(contas: List[Dict[str, Any]], opcao: str) -> Optional[Dict[str, Any]]:
    """O cálculo MAIS RECENTE da cadeia da opção (a base ou o último ajuste dela) que já tem negócio no Agger."""
    por_id = {str(c["id"]): c for c in contas}

    def _raiz(c: Dict[str, Any]) -> Optional[str]:
        vistos = set()
        while c and c.get("opcao") == "ajuste" and c.get("origem_calculo_id") and str(c["id"]) not in vistos:
            vistos.add(str(c["id"]))
            c = por_id.get(str(c["origem_calculo_id"]))
        return (c or {}).get("opcao")

    cadeia = [c for c in contas if _raiz(c) == opcao and c.get("negocio_ref")]
    return max(cadeia, key=lambda c: str(c.get("criado_em") or "")) if cadeia else None


class CotacaoAjustarTool(_Cotacao):
    name: str = "cotacao_ajustar"
    description: str = (
        "RECALCULA uma cotação que já voltou, com um ajuste: franquia reduzida, comissão, desconto, assistência, "
        "carro reserva ou vidros — na mesma negociação do Agger. Use quando o corretor pedir 'e com franquia "
        "reduzida?', 'baixa a comissão para 15'. Recebe o pedido_id que a cotacao_disparar devolveu. O resultado "
        "volta nesta conversa.")
    args_schema: Type[BaseModel] = _AjustarIn

    async def _arun(self, pedido_id: str = "", tipo: str = "", valor: str = "", opcao: Optional[str] = "recomendada",
                    seguradora: Optional[int] = None, user_id: Optional[str] = None, session_id: Optional[str] = None,
                    **_: Any) -> str:
        try:
            return _saida(await self._ajustar(pedido_id, tipo, valor, opcao, seguradora, user_id, session_id))
        except Recusa as r:
            return _saida(r.frase)
        except Exception as exc:  # noqa: BLE001
            logger.error("[COTACAO] ajustar falhou (%s)", type(exc).__name__)
            return "Não consegui recalcular agora — o problema é do nosso lado. Tente de novo em instantes."

    async def _ajustar(self, pedido_id: str, tipo: str, valor: Any, opcao: Optional[str], seguradora: Optional[int],
                       user_id: Optional[str], session_id: Optional[str]) -> str:
        from app.services.cotacao import workflow as WF
        from app.services.cotacao.pedido_da_conversa import _sem_acento
        from app.services.cotacao.resposta import frase_calculando, onde_pelas_contas
        from app.services.multicalculo import porta as P

        db, company_id, user_id, conversa = await asyncio.to_thread(self._turno, user_id, session_id)
        if not _UUID.match(str(pedido_id or "")):
            return "Não achei essa cotação — me diga qual cotação você quer ajustar."
        ped = [p for p in (getattr(db.table("multicalculo_pedidos")
                                   .select("id, company_id, servico, solicitante_user_id, status")
                                   .eq("id", str(pedido_id)).eq("company_id", company_id).limit(1).execute(),
                                   "data", None) or []) if str(p.get("company_id")) == company_id]
        if not ped or ped[0].get("servico") != "cotacao":
            return "Não achei essa cotação na sua corretora."
        if str(ped[0].get("solicitante_user_id") or "") != user_id:
            return "Essa cotação foi pedida por outra pessoa da equipe — o ajuste sai pela conversa de quem pediu."
        t = _sem_acento(tipo).strip().replace(" ", "_")
        if t not in _TIPOS:
            return "Eu sei recalcular com: franquia, comissão, desconto, assistência, carro reserva ou vidros."
        alvo = _OPCAO_DO_TEXTO.get(_sem_acento(opcao or "recomendada").strip(), "padrao")
        contas = await asyncio.to_thread(WF.contas_do_pedido, db, company_id, str(pedido_id))
        origem = _calculo_para_ajustar(contas, alvo)
        if origem is None:
            return "Essa cotação ainda está calculando — espere ela voltar aqui para eu ajustar."
        v: Any = _sem_acento(valor).strip()
        if t in ("comissao", "desconto"):
            try:
                v = float(str(v).replace("%", "").replace(",", ".").strip())
            except ValueError:
                return "A comissão e o desconto precisam ser um número (ex.: 15)."
        try:
            res = await _porta(db).recalcular(company_id=company_id, calculo_id=str(origem["id"]),
                                              ajuste={"tipo": t, "valor": v, "seguradora": seguradora})
        except P.ContaRecusada as exc:
            return exc.frase
        except ValueError as exc:
            return _frase_do_ajuste_recusado(t, exc)
        rotulo = _rotulo_do_ajuste(t, valor)
        if res.get("repetido"):
            return f"Esse recálculo com {rotulo} já está rodando — o resultado volta aqui."
        await asyncio.to_thread(WF.abrir, db, company_id=company_id, user_id=user_id, conversation_id=conversa,
                                pedido_id=str(pedido_id), ajuste=rotulo, ajuste_calculo_id=str(res.get("id")))
        return frase_calculando(onde_pelas_contas([origem]), ajuste=rotulo)


def _frase_do_ajuste_recusado(tipo: str, exc: BaseException) -> str:
    """P-1310-04: a recusa do recálculo numa frase humana."""
    texto = str(exc)
    if "espere o disparo" in texto or "ainda não tem" in texto:
        return "Essa cotação ainda está calculando no Agger — espere ela voltar para eu ajustar."
    if "cancelado" in texto:
        return "Essa cotação foi cancelada — peça uma cotação nova."
    try:
        from portal_worker.multicalculo.presets import VALORES_DO_AJUSTE

        aceitos = sorted(VALORES_DO_AJUSTE.get(tipo) or {})
    except Exception:  # noqa: BLE001
        aceitos = []
    if aceitos:
        return f"Para {tipo.replace('_', ' ')} eu sei recalcular com: {', '.join(aceitos)}."
    return "Não consegui aplicar esse ajuste — me diga o valor de outro jeito (ex.: 'franquia reduzida', 'comissão 15')."


def ferramentas_de_cotacao(*, company_id: str, supabase: Any) -> List[BaseTool]:
    """As três ferramentas da Cotação Rápida para o agente CORE desta corretora (a costura B4 as anexa no grafo)."""
    return [CotacaoPrepararTool(company_id=str(company_id), supabase=supabase),
            CotacaoDispararTool(company_id=str(company_id), supabase=supabase),
            CotacaoAjustarTool(company_id=str(company_id), supabase=supabase)]
