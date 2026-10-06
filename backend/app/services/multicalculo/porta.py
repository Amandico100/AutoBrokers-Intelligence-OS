# -*- coding: utf-8 -*-
"""A PORTA do multicálculo — SPEC-129-B U2 (D-MC-37: `MulticalculoProvider`).

Qualquer parte do produto pede "calcule este pedido nas corretoras X e Y, padrão e econômica" e recebe o andamento por
eventos, sem saber qual login rodou. A porta NÃO calcula: autoriza, valida, cifra e ENFILEIRA em
`multicalculo_calculos`; o motor do `portal-worker` (F3) consome a fila; `consultar` devolve o que o motor gravou.

🔴 `company_id` é SEMPRE o 1º parâmetro nomeado (keyword-only) e é o SOLICITANTE — molde
`app/providers/policy_data_provider.py:PolicyDataProvider`. Nenhuma operação deduz tenant de contexto.

🔴 A AUTORIZAÇÃO (D-129B-05), antes de gravar qualquer linha:
    cada corretora pedida é uma empresa `client`, e
       corretora == solicitante, OU
       o solicitante é `platform_canal` E existe adesão ATIVA canal → corretora.
    Qualquer outra → `NaoAutorizado`. A mesma regra vale no `recalcular` e na LEITURA de ofertas/eventos de
    outra corretora no `consultar` (adesão desativada depois do pedido → o canal deixa de ver aquela corretora).

🔴 Comissão (G2): `comissao_percentual` só sai quando quem consulta É a corretora dona da oferta; o canal recebe None.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from portal_worker.multicalculo.contrato import RAMO_AUTO, TIPOS_DE_AJUSTE, Ajuste

from app.services.multicalculo.pedido import PedidoDeCalculo
from app.services.multicalculo.repositorio import RepositorioMulticalculo

logger = logging.getLogger(__name__)

OPCOES: Tuple[str, ...] = ("padrao", "economica")
ORIGENS: Tuple[str, ...] = ("auxiliar", "canal", "teste")
KIND_CANAL = "platform_canal"
KIND_CORRETORA = "client"
ENV_CANARIO = "AUTOBROKERS_CANARIO"
ENV_HMAC = "MULTICALCULO_HMAC_KEY"

#: D-129B-07 — a fila tem dono do tempo. 💭 valores: o canal tem alguém esperando no WhatsApp (prioridade 0, vence em
#: 10 min); o auxiliar trabalha de madrugada se precisar (5, vence em 24 h); o teste é o canário (0, 30 min).
PRIORIDADE: Dict[str, int] = {"canal": 0, "teste": 0, "auxiliar": 5}
VALIDADE: Dict[str, timedelta] = {"canal": timedelta(minutes=10), "teste": timedelta(minutes=30),
                                  "auxiliar": timedelta(hours=24)}

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# ---------------------------------------------------------------------------------------------------------------------
# As recusas — a mensagem leva NOMES de campo e motivos, nunca valores
# ---------------------------------------------------------------------------------------------------------------------
class NaoAutorizado(PermissionError):
    """O solicitante não pode calcular (ou ler) nesta corretora."""


class OrigemRecusada(PermissionError):
    """`origem='teste'` fora do canário (sem AUTOBROKERS_CANARIO=1), ou origem desconhecida (D-129B-04)."""


class PedidoIncompleto(ValueError):
    def __init__(self, campos: Sequence[str]):
        self.campos = list(campos)
        super().__init__("faltam campos obrigatórios: " + ", ".join(self.campos))


class PerfilIncompleto(ValueError):
    """No canal se PERGUNTA o perfil (D-MC-59): garagem, uso, km, jovem condutor."""

    def __init__(self, campos: Sequence[str]):
        self.campos = list(campos)
        super().__init__("o perfil precisa ser perguntado: " + ", ".join(self.campos))


class ChaveAusente(RuntimeError):
    """MULTICALCULO_HMAC_KEY ausente: a porta recusa calcular (fail-closed; nunca hash sem sal)."""


class NaoEncontrado(LookupError):
    """Pedido/cálculo inexistente PARA ESTE solicitante (não diz se existe noutro)."""


class PresetIndisponivel(RuntimeError):
    """Sem coberturas para a opção: nem explícitas nem preset. Nenhum cálculo sai sem coberturas."""


# ---------------------------------------------------------------------------------------------------------------------
# O que volta
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PedidoAberto:
    pedido_id: str
    calculos: Tuple[Dict[str, str], ...]   # ({"id", "corretora_company_id", "opcao"}, ...)


@dataclass(frozen=True)
class Andamento:
    pedido_id: str
    status: str
    estados: Tuple[Dict[str, Any], ...]    # por cálculo: corretora × opção, status, posicao_na_fila
    ofertas: Tuple[Dict[str, Any], ...]    # menor prêmio primeiro
    eventos: Tuple[Dict[str, Any], ...]    # id > desde_evento, em ordem
    ultimo_evento: int


# ---------------------------------------------------------------------------------------------------------------------
# As peças pequenas
# ---------------------------------------------------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _uuid(valor: Any, nome: str) -> str:
    texto = str(valor or "").strip()
    if not _UUID.match(texto):
        raise ValueError(f"{nome} precisa ser um uuid")
    return texto.lower()


def cpf_hmac(documento: str, *, chave: Optional[str] = None) -> str:
    """HMAC-SHA256(MULTICALCULO_HMAC_KEY, só os dígitos). Sem a chave → `ChaveAusente`."""
    segredo = chave if chave is not None else os.environ.get(ENV_HMAC, "")
    if not segredo:
        raise ChaveAusente(f"{ENV_HMAC} ausente — a porta não calcula sem ela")
    digitos = re.sub(r"\D", "", str(documento or ""))
    if not digitos:
        raise PedidoIncompleto(["segurado.cpf_cnpj"])
    return hmac.new(segredo.encode("utf-8"), digitos.encode("utf-8"), hashlib.sha256).hexdigest()


def _preset_padrao(opcao: str) -> Dict[str, Any]:
    """Os presets 💭 de `portal_worker/multicalculo/presets.py` (F2, D-129B-08): `PRESETS[opcao]` → dict.
    Ausente → `PresetIndisponivel` (fail-closed)."""
    try:
        from portal_worker.multicalculo import presets as _p
    except Exception as exc:  # noqa: BLE001
        raise PresetIndisponivel(f"presets indisponíveis ({type(exc).__name__})") from None
    tabela = getattr(_p, "PRESETS", None)
    if not isinstance(tabela, Mapping) or not isinstance(tabela.get(opcao), Mapping):
        raise PresetIndisponivel(f"sem preset para a opção {opcao}")
    return dict(tabela[opcao])


def _ajuste_codificado(ajuste: Ajuste) -> Ajuste:
    """F4 (costura): o rótulo do ajuste vira o CÓDIGO que o robô manda (`presets.VALORES_DO_AJUSTE`, medidos);
    rótulo sem código → `ValueError` na porta, nunca um recálculo recusado lá na frente."""
    from portal_worker.multicalculo.presets import VALORES_DO_AJUSTE

    valores = VALORES_DO_AJUSTE.get(ajuste.tipo)
    if valores is None or not isinstance(ajuste.valor, str):
        return ajuste
    texto = ajuste.valor.strip()
    if texto.isdigit():
        return Ajuste(tipo=ajuste.tipo, valor=int(texto), seguradora=ajuste.seguradora)
    chave = unicodedata.normalize("NFKD", texto)
    chave = "".join(c for c in chave if not unicodedata.combining(c)).lower()
    if chave not in valores:
        raise ValueError(f"ajuste {ajuste.tipo}: valor sem código medido (aceitos: {', '.join(sorted(valores))})")
    return Ajuste(tipo=ajuste.tipo, valor=valores[chave], seguradora=ajuste.seguradora)


def _aplicar_ajuste(coberturas: Mapping[str, Any], ajuste: Ajuste) -> Dict[str, Any]:
    """As coberturas da ORIGEM + o ajuste, nas chaves do AGGER (as de `calculos.coberturas`, que o montador aplica).
    `cobertura` com dict funde chave a chave; os outros tipos trocam a chave do item que o montador troca
    (`presets.CAMPO_DO_AJUSTE`, gêmeo do `montador.js`); `percentual_fipe` é do automóvel e não entra aqui.
    Ajuste de UMA seguradora não muda as coberturas gerais (o robô o aplica só no item dela)."""
    from portal_worker.multicalculo.presets import CAMPO_DO_AJUSTE

    novas = dict(coberturas or {})
    if ajuste.seguradora is not None:
        return novas
    if ajuste.tipo == "cobertura" and isinstance(ajuste.valor, Mapping):
        novas.update(dict(ajuste.valor))
    elif ajuste.tipo in CAMPO_DO_AJUSTE:
        novas[CAMPO_DO_AJUSTE[ajuste.tipo]] = ajuste.valor
    return novas


def _erro_publico(erro: Any) -> Optional[str]:
    """O `erro` do cálculo como a corretora o lê: o motor já o gravou saneado; a porta saneia DE NOVO (URL, chave,
    PII) e corta — o banco não é confiado como única rede."""
    if not erro:
        return None
    from portal_worker.redaction import redigir_texto, sem_url_nem_chave

    return re.sub(r"\s+", " ", redigir_texto(sem_url_nem_chave(erro))).strip()[:200] or None


def _oferta_publica(linha: Mapping[str, Any], *, company_id: str) -> Dict[str, Any]:
    saida = {k: v for k, v in dict(linha).items() if k not in ("comissao_percentual", "pdf_path")}
    saida["corretora_company_id"] = str(linha.get("company_id"))
    saida.pop("company_id", None)
    # 🔴 G2: a comissão é INTERNA — só a corretora DONA da oferta a vê
    saida["comissao_percentual"] = (linha.get("comissao_percentual")
                                    if str(linha.get("company_id")) == str(company_id) else None)
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# A PORTA
# ---------------------------------------------------------------------------------------------------------------------
class MulticalculoProvider:
    """A porta. `repositorio` e `cifrar` são injetáveis (testes: dublê em memória; produção: o cofre do smith-api)."""

    provider_key: str = "agger"

    def __init__(self, repositorio: Optional[RepositorioMulticalculo] = None, *,
                 cifrar: Optional[Callable[[str], str]] = None,
                 presets: Optional[Callable[[str], Mapping[str, Any]]] = None,
                 ambiente: Optional[Mapping[str, str]] = None,
                 agora: Callable[[], datetime] = _agora):
        self.repo = repositorio or RepositorioMulticalculo()
        if cifrar is None:
            from app.services import portal_vault

            cifrar = portal_vault.encrypt
        self._cifrar = cifrar
        self._preset = presets or _preset_padrao
        self._ambiente = ambiente
        self._agora = agora

    def _env(self, nome: str) -> str:
        fonte = self._ambiente if self._ambiente is not None else os.environ
        return str(fonte.get(nome, "") or "")

    # ------------------------------------------------------------------ capacidades
    def capacidades(self, ramo: int = RAMO_AUTO) -> Dict[str, Any]:
        if int(ramo) != RAMO_AUTO:
            return {"ramo": int(ramo), "suportado": False, "motivo": "a v1 calcula só o AUTO (31)"}
        return {"ramo": RAMO_AUTO, "suportado": True, "portal": self.provider_key, "opcoes": OPCOES,
                "ajustes": TIPOS_DE_AJUSTE, "origens": ORIGENS, "renovacao": True,
                "entrega": "eventos (consultar com desde_evento)", "pdf": "pdf(company_id, oferta_id) → bytes"}

    # ------------------------------------------------------------------ autorização
    async def _autorizar(self, *, company_id: str, corretoras: Sequence[str]) -> str:
        """Devolve o `company_kind` do solicitante, ou levanta `NaoAutorizado`. Nada é gravado antes disto."""
        tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id, *corretoras])
        kind = tipos.get(company_id)
        if not kind:
            raise NaoAutorizado("solicitante desconhecido")
        for c in corretoras:
            if tipos.get(c) != KIND_CORRETORA:
                raise NaoAutorizado("a corretora pedida não é uma corretora cliente")
        outras = [c for c in corretoras if c != company_id]
        if outras:
            if kind != KIND_CANAL:
                raise NaoAutorizado("só o canal calcula noutra corretora")
            aderidas = await asyncio.to_thread(self.repo.adesoes_ativas, canal_company_id=company_id,
                                               corretoras=outras)
            if set(outras) - aderidas:
                raise NaoAutorizado("o canal não tem adesão ativa com a corretora pedida")
        return kind

    def _conferir_origem(self, origem: str) -> None:
        if origem not in ORIGENS:
            raise OrigemRecusada(f"origem desconhecida: {origem!r}")
        if origem == "teste" and self._env(ENV_CANARIO) != "1":
            raise OrigemRecusada("origem 'teste' só no canário (AUTOBROKERS_CANARIO=1)")

    # ------------------------------------------------------------------ calcular
    async def calcular(self, *, company_id: str, pedido: PedidoDeCalculo,
                       corretoras: Optional[Iterable[str]] = None,
                       opcoes: Iterable[str] = OPCOES,
                       coberturas: Optional[Mapping[str, Mapping[str, Any]]] = None,
                       origem: str, quadro_s: int = 60) -> PedidoAberto:
        company_id = _uuid(company_id, "company_id")
        self._conferir_origem(origem)
        alvo: List[str] = []
        for c in (corretoras if corretoras is not None else [company_id]):
            u = _uuid(c, "corretora")
            if u not in alvo:
                alvo.append(u)
        if not alvo:
            raise ValueError("nenhuma corretora pedida")
        escolhidas = [o for o in OPCOES if o in set(opcoes)]
        desconhecidas = set(opcoes) - set(OPCOES)
        if desconhecidas or not escolhidas:
            raise ValueError("opções aceitas: padrao, economica")
        quadro = int(quadro_s)
        if not 5 <= quadro <= 600:
            raise ValueError("quadro_s entre 5 e 600")
        if not isinstance(pedido, PedidoDeCalculo):
            raise TypeError("pedido precisa ser um PedidoDeCalculo")

        await self._autorizar(company_id=company_id, corretoras=alvo)

        # F4 (costura): o que falta E o que veio sem código medido no Agger (o robô recusaria só no disparo)
        faltam = pedido.faltando() + [c for c in pedido.sem_codigo() if c not in pedido.faltando()]
        if faltam:
            raise PedidoIncompleto(faltam)
        if origem == "canal":
            perfil = pedido.perfil_faltando()
            if perfil:
                raise PerfilIncompleto(perfil)
        else:
            pedido = pedido.assumindo_perfil()          # D-128-07: auxiliar (e o canário) assumem o padrão da tela

        hmac_doc = cpf_hmac(pedido.documento, chave=self._env(ENV_HMAC))   # fail-closed ANTES de gravar

        por_opcao: Dict[str, Dict[str, Any]] = {}
        for o in escolhidas:
            explicitas = (coberturas or {}).get(o)
            cob = dict(explicitas) if explicitas is not None else dict(self._preset(o) or {})
            if not cob:
                raise PresetIndisponivel(f"sem coberturas para a opção {o}")
            por_opcao[o] = cob

        cifrado = self._cifrar(json.dumps(pedido.para_dict(), ensure_ascii=False, sort_keys=True))
        agora = self._agora()
        pedido_id = str(uuid.uuid4())
        linha_pedido = {
            "id": pedido_id, "company_id": company_id, "origem": origem, "ramo": pedido.ramo,
            "opcoes": escolhidas, "corretoras": alvo, "pedido_cifrado": cifrado, "cpf_hmac": hmac_doc,
            "quadro_s": quadro, "status": "aberto",
        }
        linhas_calc = [{
            "id": str(uuid.uuid4()), "pedido_id": pedido_id, "solicitante_company_id": company_id,
            "company_id": corretora, "opcao": o, "coberturas": por_opcao[o], "status": "na_fila",
            "prioridade": PRIORIDADE[origem], "expira_em": (agora + VALIDADE[origem]).isoformat(),
            "disponivel_em": agora.isoformat(),
        } for corretora in alvo for o in escolhidas]
        _p, gravados = await asyncio.to_thread(self.repo.gravar_pedido, linha_pedido, linhas_calc)
        logger.info("[MULTICALCULO] pedido enfileirado: %s cálculo(s), origem=%s", len(linhas_calc), origem)
        return PedidoAberto(pedido_id=pedido_id, calculos=tuple(
            {"id": str(c["id"]), "corretora_company_id": str(c["company_id"]), "opcao": str(c["opcao"])}
            for c in (gravados or linhas_calc)))

    # ------------------------------------------------------------------ consultar
    async def consultar(self, *, company_id: str, pedido_id: str, desde_evento: int = 0) -> Andamento:
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        if not ped or str(ped.get("company_id")) != company_id:
            raise NaoEncontrado("pedido não encontrado")
        calculos = await asyncio.to_thread(self.repo.calculos_do_pedido, company_id=company_id, pedido_id=pedido_id)
        ofertas = await asyncio.to_thread(self.repo.ofertas_do_pedido, company_id=company_id, pedido_id=pedido_id)
        eventos = await asyncio.to_thread(self.repo.eventos_do_pedido, company_id=company_id,
                                          pedido_id=pedido_id, desde_evento=desde_evento)

        # a LEITURA de outra corretora exige o canal com adesão ATIVA agora (reconferida a cada consulta)
        corretoras = sorted({str(c.get("company_id")) for c in calculos} | {str(o.get("company_id")) for o in ofertas}
                            | {str(e.get("company_id")) for e in eventos})
        visiveis = {company_id}
        outras = [c for c in corretoras if c != company_id]
        if outras:
            tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
            if tipos.get(company_id) == KIND_CANAL:
                visiveis |= await asyncio.to_thread(self.repo.adesoes_ativas, canal_company_id=company_id,
                                                    corretoras=outras)

        fila = [c for c in calculos if c.get("status") == "na_fila"]
        a_frente = await asyncio.to_thread(self.repo.fila_a_frente) if fila else []
        estados = []
        for c in calculos:
            if str(c.get("company_id")) not in visiveis:
                continue
            posicao = None
            if c.get("status") == "na_fila":
                chave = (int(c.get("prioridade") or 0), str(c.get("disponivel_em") or ""))
                posicao = 1 + sum(1 for f in a_frente
                                  if (int(f.get("prioridade") or 0), str(f.get("disponivel_em") or "")) < chave)
            estados.append({"calculo_id": str(c["id"]), "corretora_company_id": str(c["company_id"]),
                            "opcao": c.get("opcao"), "status": c.get("status"), "posicao_na_fila": posicao,
                            "primeira_oferta_em": c.get("primeira_oferta_em"),
                            "quadro_pronto_em": c.get("quadro_pronto_em"), "fechado_em": c.get("fechado_em"),
                            "origem_calculo_id": c.get("origem_calculo_id"),
                            # conserto 129-B (juiz P4): o PORQUÊ do falhou/incerto/cancelado, saneado de novo
                            "erro": _erro_publico(c.get("erro"))})
        ofertas_v = sorted((_oferta_publica(o, company_id=company_id) for o in ofertas
                            if str(o.get("company_id")) in visiveis),
                           key=lambda o: float(o.get("premio_total") or 0))
        eventos_v = []
        for e in eventos:
            if str(e.get("company_id")) not in visiveis:
                continue
            item = {k: v for k, v in dict(e).items() if k != "company_id"}
            item["corretora_company_id"] = str(e.get("company_id"))
            eventos_v.append(item)
        ultimo = max([int(desde_evento or 0)] + [int(e.get("id") or 0) for e in eventos])
        return Andamento(pedido_id=pedido_id, status=str(ped.get("status")), estados=tuple(estados),
                         ofertas=tuple(ofertas_v), eventos=tuple(eventos_v), ultimo_evento=ultimo)

    # ------------------------------------------------------------------ recalcular
    async def recalcular(self, *, company_id: str, calculo_id: str, ajuste: Any) -> Dict[str, str]:
        """Nova versão do MESMO negócio, na MESMA corretora (D-MC-41), a partir da versão CERTA (a da origem)."""
        company_id = _uuid(company_id, "company_id")
        calculo_id = _uuid(calculo_id, "calculo_id")
        if isinstance(ajuste, Mapping):
            ajuste = Ajuste(tipo=str(ajuste.get("tipo")), valor=ajuste.get("valor"),
                            seguradora=ajuste.get("seguradora"))
        if not isinstance(ajuste, Ajuste):
            raise TypeError("ajuste precisa ser um contrato.Ajuste ou um dict {tipo, valor, seguradora}")
        ajuste = _ajuste_codificado(ajuste)
        origem = await asyncio.to_thread(self.repo.calculo, company_id=company_id, calculo_id=calculo_id)
        if not origem or str(origem.get("solicitante_company_id")) != company_id:
            raise NaoEncontrado("cálculo não encontrado")
        corretora = str(origem["company_id"])
        await self._autorizar(company_id=company_id, corretoras=[corretora])   # reconfere a adesão do canal
        if origem.get("negocio_ref") is None or origem.get("versao") is None:
            raise ValueError("o cálculo de origem ainda não tem negócio no portal — espere o disparo")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=str(origem["pedido_id"]))
        if not ped:
            raise NaoEncontrado("pedido não encontrado")
        if ped.get("status") == "cancelado":
            raise ValueError("pedido cancelado")
        self._conferir_origem(str(ped.get("origem")))
        # 🔴 conserto 129-B (red P4): o clique duplo não vira 2º calcularV2 — o MESMO ajuste da MESMA origem ainda
        # na fila ou no robô é DEVOLVIDO (o motor também cancela o repetido que escapar desta conferência)
        em_curso = await asyncio.to_thread(self.repo.ajustes_em_curso, company_id=company_id,
                                           origem_calculo_id=calculo_id)
        pedido_igual = {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora}
        for c in em_curso:
            aj = c.get("ajuste") if isinstance(c.get("ajuste"), Mapping) else {}
            if str(c.get("company_id")) == corretora and \
                    {k: aj.get(k) for k in ("tipo", "valor", "seguradora")} == pedido_igual:
                return {"id": str(c["id"]), "corretora_company_id": corretora, "opcao": "ajuste",
                        "origem_calculo_id": calculo_id, "repetido": True}
        agora = self._agora()
        novo = {
            "id": str(uuid.uuid4()), "pedido_id": str(origem["pedido_id"]), "solicitante_company_id": company_id,
            "company_id": corretora, "opcao": "ajuste", "origem_calculo_id": calculo_id,
            "coberturas": _aplicar_ajuste(origem.get("coberturas") or {}, ajuste),
            "ajuste": {"tipo": ajuste.tipo, "valor": ajuste.valor, "seguradora": ajuste.seguradora,
                       "versao_base": int(origem["versao"]), "negocio_ref": str(origem["negocio_ref"])},
            "status": "na_fila", "prioridade": PRIORIDADE.get(str(ped.get("origem")), 5),
            "expira_em": (agora + VALIDADE.get(str(ped.get("origem")), timedelta(hours=24))).isoformat(),
            "disponivel_em": agora.isoformat(),
        }
        gravado = await asyncio.to_thread(self.repo.inserir_calculo, novo)
        # F4 (costura): o motor só serve pedido `aberto` — o recálculo de um pedido já fechado o reabre
        await asyncio.to_thread(self.repo.reabrir_pedido, company_id=company_id, pedido_id=str(origem["pedido_id"]))
        return {"id": str(gravado.get("id") or novo["id"]), "corretora_company_id": corretora, "opcao": "ajuste",
                "origem_calculo_id": calculo_id}

    # ------------------------------------------------------------------ o PDF
    async def pdf(self, *, company_id: str, oferta_id: str) -> Optional[bytes]:
        """O PDF da oferta (a FICHA: "baixa o PDF" — conserto 129-B, juiz B2), lido do NOSSO bucket privado, onde o
        motor o copiou (`multicalculo/{corretora}/{calculo}/{oferta}.pdf`). Nunca o link do fornecedor.

        Quem pode: o SOLICITANTE do pedido (se a oferta é de outra corretora, só o canal com adesão ATIVA agora —
        a mesma regra do `consultar`) ou a CORRETORA de registro (o login dela calculou). Qualquer outro →
        `NaoEncontrado` (não diz se existe). Sem PDF copiado → None."""
        company_id = _uuid(company_id, "company_id")
        oferta_id = _uuid(oferta_id, "oferta_id")
        oferta = await asyncio.to_thread(self.repo.oferta_do_solicitante, company_id=company_id, oferta_id=oferta_id)
        if oferta and str(oferta.get("solicitante_company_id")) == company_id:
            dona = str(oferta.get("company_id"))
            if dona != company_id:
                tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
                if tipos.get(company_id) != KIND_CANAL or dona not in await asyncio.to_thread(
                        self.repo.adesoes_ativas, canal_company_id=company_id, corretoras=[dona]):
                    raise NaoEncontrado("oferta não encontrada")
        else:
            oferta = await asyncio.to_thread(self.repo.oferta_da_corretora, company_id=company_id,
                                             oferta_id=oferta_id)
            if not oferta or str(oferta.get("company_id")) != company_id:
                raise NaoEncontrado("oferta não encontrada")
        caminho = str(oferta.get("pdf_path") or "")
        esperado = f"multicalculo/{oferta.get('company_id')}/{oferta.get('calculo_id')}/{oferta.get('id')}.pdf"
        if not caminho:
            return None
        if caminho != esperado:
            # o caminho gravado não é o que o motor escreve para ESTA oferta: nunca se lê outro arquivo do bucket
            logger.warning("[MULTICALCULO] pdf_path fora do padrão na oferta %s — recusado", oferta_id)
            return None
        try:
            dados = await asyncio.to_thread(self.repo.baixar_pdf, caminho)
        except Exception as exc:  # noqa: BLE001 — o storage fora não derruba quem chama
            logger.warning("[MULTICALCULO] baixar o PDF falhou (%s)", type(exc).__name__)
            return None
        if not dados or dados[:4] != b"%PDF":
            return None
        return dados

    # ------------------------------------------------------------------ cancelar
    async def cancelar(self, *, company_id: str, pedido_id: str) -> int:
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        if not ped:
            raise NaoEncontrado("pedido não encontrado")
        return await asyncio.to_thread(self.repo.cancelar, company_id=company_id, pedido_id=pedido_id)

    # ------------------------------------------------------------------ SPEC-130-A U3: a negociação
    # 🔴 Só a corretora DONA negocia (D-MC-63): o canal recebe a comissão como None e não decide margem alheia →
    # `{"status": "so_a_corretora_negocia"}`, ANTES de qualquer leitura de oferta ou efeito. A decisão é PURA
    # (`negociacao.py`); a porta autoriza, lê pela `consultar` e ENFILEIRA pela `recalcular` (que já existe).
    async def _negociacao_da_dona(self, *, company_id: str) -> Optional[Dict[str, Any]]:
        tipos = await asyncio.to_thread(self.repo.tipos_de_empresa, [company_id])
        kind = tipos.get(company_id)
        if kind == KIND_CANAL:
            return {"status": "so_a_corretora_negocia",
                    "motivo": "a margem é da corretora: só ela negocia comissão e desconto (D-MC-63)"}
        if kind != KIND_CORRETORA:
            raise NaoAutorizado("só uma corretora cliente negocia")
        return None

    async def _config_e_andamento(self, *, company_id: str, pedido_id: str) -> Tuple[Dict[str, Any], "Andamento"]:
        from app.services.multicalculo.config import carregar

        andamento = await self.consultar(company_id=company_id, pedido_id=pedido_id)
        cfg = await asyncio.to_thread(carregar, company_id, db=self.repo.db)
        return cfg, andamento

    async def ordem_do_mais_barato(self, *, company_id: str, oferta_ref: Mapping[str, Any],
                                   concorrencia_declarada: bool = False) -> Dict[str, Any]:
        """Os `Ajuste`s, na ordem D-MC-67, que a seguradora da oferta OBEDECE (desconto onde ela ignora a comissão —
        a lista vem da config). `oferta_ref = {"pedido_id", "oferta_id"}`; a oferta tem de ser DESTA corretora."""
        from app.services.multicalculo import negociacao

        company_id = _uuid(company_id, "company_id")
        if not isinstance(oferta_ref, Mapping):
            raise TypeError("oferta_ref = {'pedido_id': …, 'oferta_id': …}")
        pedido_id = _uuid(oferta_ref.get("pedido_id"), "pedido_id")
        oferta_id = _uuid(oferta_ref.get("oferta_id"), "oferta_id")
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        oferta = next((o for o in andamento.ofertas if str(o.get("id")) == oferta_id
                       and str(o.get("corretora_company_id")) == company_id), None)
        if oferta is None:
            raise NaoEncontrado("oferta não encontrada")
        passos = negociacao.ordem_do_mais_barato(oferta, config=cfg, concorrencia_declarada=concorrencia_declarada)
        return {"status": "ok", "ajustes": [p.ajuste for p in passos], "passos": [p.para_dict() for p in passos]}

    async def _enfileirar(self, *, company_id: str, plano: Mapping[str, Any]) -> Dict[str, Any]:
        tentativas = list(plano.get("tentativas") or ())
        feitos = await asyncio.gather(*(self.recalcular(company_id=company_id, calculo_id=t["origem_calculo_id"],
                                                        ajuste=t["ajuste"]) for t in tentativas),
                                      return_exceptions=True)
        enfileiradas, falhas = [], []
        for t, r in zip(tentativas, feitos):
            publico = {k: v for k, v in t.items() if k != "ajuste"}
            if isinstance(r, BaseException):
                if isinstance(r, (NaoAutorizado, OrigemRecusada)):
                    raise r
                falhas.append({**publico, "erro": type(r).__name__})
                continue
            enfileiradas.append({**publico, "calculo_id": str(r.get("id")), "repetido": bool(r.get("repetido"))})
        aguardam = [{k: v for k, v in t.items() if k != "ajuste"} for t in plano.get("precisa_aprovacao") or ()]
        status = "em_andamento" if enfileiradas else ("precisa_aprovacao" if aguardam else "sem_caminho")
        saida = {"status": status, "tentativas": enfileiradas, "precisa_aprovacao": aguardam, "falhas": falhas,
                 "custo": "1 recálculo da corretora inteira por tentativa"}
        if plano.get("melhor_parcial"):
            saida["melhor_parcial"] = plano["melhor_parcial"]
        return saida

    async def cotacao_alvo(self, *, company_id: str, pedido_id: str, alvo: float, seguradora: Any = None,
                           aprovado_pelo_corretor: bool = False, concorrencia_declarada: bool = False,
                           tentativas_anteriores: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
        """D-MC-72 "fecha por R$ X?": planeja (puro) e ENFILEIRA as tentativas pela `recalcular`, em paralelo.
        Devolve `em_andamento` com os cálculos; quem chama lê depois com `avaliar_cotacao_alvo`. Com
        `tentativas_anteriores` (o que a avaliação devolveu como `proxima_etapa`), enfileira a etapa ENCADEADA.
        Abaixo de `comissao.autonomo_minimo` sem `aprovado_pelo_corretor` → fica em `precisa_aprovacao`; o piso só
        com `concorrencia_declarada`; nunca abaixo dele."""
        from app.services.multicalculo import negociacao
        from app.services.multicalculo.comparacao import comparar

        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        try:
            alvo = float(alvo)
        except (TypeError, ValueError):
            raise ValueError("alvo precisa ser um número") from None
        if alvo <= 0:
            raise ValueError("alvo precisa ser positivo")
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        if tentativas_anteriores:
            avaliacao = await self._avaliar(company_id=company_id, andamento=andamento, cfg=cfg, alvo=alvo,
                                            tentativas=tentativas_anteriores,
                                            concorrencia_declarada=concorrencia_declarada,
                                            aprovado_pelo_corretor=aprovado_pelo_corretor)
            if avaliacao["status"] != "proxima_etapa":
                return avaliacao
            return await self._enfileirar(company_id=company_id, plano=avaliacao)
        ped = await asyncio.to_thread(self.repo.pedido, company_id=company_id, pedido_id=pedido_id)
        quadro = comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg,
                          ramo=int((ped or {}).get("ramo") or RAMO_AUTO))
        por_id = {str(o.get("id")): o for o in andamento.ofertas}
        candidatas = [por_id[e["oferta_id"]] for e in quadro.ranking(quadro.opcao_completa, company_id)
                      if e["oferta_id"] in por_id]
        plano = negociacao.planejar(candidatas, alvo=alvo, config=cfg, seguradora=seguradora,
                                    concorrencia_declarada=concorrencia_declarada,
                                    aprovado_pelo_corretor=aprovado_pelo_corretor)
        if plano["status"] != "planejado":
            return dict(plano)
        return await self._enfileirar(company_id=company_id, plano=plano)

    async def avaliar_cotacao_alvo(self, *, company_id: str, pedido_id: str, alvo: float,
                                   tentativas: Sequence[Mapping[str, Any]], concorrencia_declarada: bool = False,
                                   aprovado_pelo_corretor: bool = False) -> Dict[str, Any]:
        """Lê as tentativas pela `consultar` e DECIDE (sem efeito): `em_andamento` (ainda calculando) · `chegou`
        (a de MAIOR comissão, margem antes de cobertura, cortes listados e se recomenda) · `proxima_etapa` (o plano
        encadeado — enfileira-se com `cotacao_alvo(tentativas_anteriores=…)`) · `sem_caminho` ("não recomendo")."""
        company_id = _uuid(company_id, "company_id")
        pedido_id = _uuid(pedido_id, "pedido_id")
        alvo = float(alvo)
        recusa = await self._negociacao_da_dona(company_id=company_id)
        if recusa:
            return recusa
        cfg, andamento = await self._config_e_andamento(company_id=company_id, pedido_id=pedido_id)
        return await self._avaliar(company_id=company_id, andamento=andamento, cfg=cfg, alvo=alvo,
                                   tentativas=tentativas, concorrencia_declarada=concorrencia_declarada,
                                   aprovado_pelo_corretor=aprovado_pelo_corretor)

    async def _avaliar(self, *, company_id: str, andamento: "Andamento", cfg: Mapping[str, Any], alvo: float,
                       tentativas: Sequence[Mapping[str, Any]], concorrencia_declarada: bool,
                       aprovado_pelo_corretor: bool) -> Dict[str, Any]:
        from app.services.multicalculo import negociacao

        status = {str(e.get("calculo_id")): e.get("status") for e in andamento.estados}
        meus = [t for t in tentativas if str(t.get("calculo_id")) in status]
        if not meus:
            raise NaoEncontrado("nenhuma tentativa deste pedido")
        pendentes = [t for t in meus if status.get(str(t["calculo_id"])) in negociacao.STATUS_PENDENTES]
        if pendentes:
            return {"status": "em_andamento", "pendentes": len(pendentes), "total": len(meus)}
        resultados = [{**dict(t), "oferta": negociacao.resultado_da_tentativa(t, andamento.ofertas,
                                                                              company_id=company_id, config=cfg)}
                      for t in meus]
        etapa = negociacao.proxima_etapa(resultados, alvo=alvo, config=cfg,
                                         concorrencia_declarada=concorrencia_declarada,
                                         aprovado_pelo_corretor=aprovado_pelo_corretor)
        if isinstance(etapa.get("escolhida"), dict):
            etapa["escolhida"] = {k: v for k, v in etapa["escolhida"].items() if k != "_oferta"}
        return etapa
