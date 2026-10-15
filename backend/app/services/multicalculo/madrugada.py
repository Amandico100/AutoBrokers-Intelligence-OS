"""A MADRUGADA DA RENOVAÇÃO — os passos do dia como Work Runs do Work OS. SPEC-131-A (F1).

Nenhum scheduler, fila ou executor novo (CLAUDE.md §5): o tick do `smith-worker` (`intelligence/tick.py`) enfileira,
por corretora com o aplicativo de Renovação ligado, no fuso dela, um Work Run por passo e por dia — a chave
`renov:<passo>:<company>:<dia>` torna dois ticks no mesmo minuto UM run. O Smith Worker executa (lease, retomada,
espera durável da SPEC-129-A).

    00:30  renovacao.preparar   InfoCap /renovacoes → lista congelada (upsert) → por item, EM SÉRIE: dono → ficha →
                                de_apolice → `pronta` | `pendente(motivo)`
    01:00  renovacao.calcular   ESPERA a lista das 00:30 terminar; `pronta` com calcular_em ≤ dia (+ a antecipação),
                                vencimento mais próximo primeiro → porta.calcular(servico='renovacao', prioridade=7,
                                politica_de_sessao='madrugada', renovacao_id=…) → `calculando`; depois DORME e relê a
                                cada 10 min (o estado é DERIVADO dos cálculos — nunca callback)
    05:55  (ultimo_inicio)      a HORA-LIMITE: o que ainda não começou no Agger é cancelado na fila e volta
                                `pronta(ficou_para_a_proxima_noite)` — entra primeiro na noite seguinte
    06:05  renovacao.conferir   `conferencia_da_renovacao.py` (OUTRO caminho: relê a InfoCap, não esta lista)
    06:15  renovacao.desvio     aguardando_agger / falhou passageiro → o Agger da CORRETORA, com aviso nomeado
    06:45  renovacao.avisar     "N prontas no seu Agger · M pendentes (porquê) · K falharam" por pessoa e à corretora

A CONTA DA JANELA (SPEC-132, Founder 14/10: "nunca só 12 — às 7h tudo cotado no Agger"). O teto de 12 da D-131-33 era
NIVELAMENTO (📊 pico de 42 de um dono num dia, BLOCO 0 131-A §1), não limite do motor: a vencida já saía toda, o 12 só
limitava a antecipação, e NADA olhava o relógio — 42 no mesmo login invadiam a manhã sem ninguém saber. O gargalo real
é a FILA: renovação de madrugada = 1 sessão do Agger por corretora (`teto_sessoes_corretora` 1, D-131-30), pedidos em
série. 📊 LAUDO-I1 §2.4: um pedido de 3 opções = login 34–54 s + cálculo (1ª oferta 6 s, fecha em 64 s, p90 406 s, teto
480 s) + logout 12–14 s → típico ~2,5 min · p90 ~8 min · pior ~9,1 min (54+480+14 = 548 s).
    antes   02:00 → 05:30 = 210 min, sem hora-limite         típico 84 · pior 23 por corretora por noite
    agora   01:00 → 05:55 = 295 min de começo + 10 de margem  típico 118 · p90 36 · pior 32 (295/9,13) — ≥ 30 mesmo no pior
O último que começa às 05:55 termina (pior) às 06:04, antes da conferência das 06:05 e com o Agger da corretora livre
para o desvio das 06:15; o aviso sai 06:45, antes das 07:00. O que sobra fica marcado e tem até `antecipar_ate_dias`
(7) noites antes de vencer a antecedência: a antecipação puxa o que vence nos próximos dias quando sobra relógio.

As BORDAS (InfoCap, a ficha, a porta) são funções deste módulo que o teste troca — o resto é o código do produto.
⛔ Nada aqui fala com o cliente. ⛔ Nenhum nome de corretora (CLAUDE.md §13.9): tudo por `company_id`.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.services.multicalculo import renovacao as R
from app.services.work.workflows import executar_passo, registrar_workflow

logger = logging.getLogger(__name__)

PASSOS: Tuple[str, ...] = ("preparar", "calcular", "conferir", "desvio", "avisar")
WORKFLOW_DO_PASSO: Dict[str, str] = {p: f"renovacao.{p}" for p in PASSOS}
TITULO_DO_PASSO: Dict[str, str] = {
    "preparar": "Renovações: montar a lista do dia",
    "calcular": "Renovações: calcular no Agger",
    "conferir": "Renovações: conferir que nenhuma ficou esquecida",
    "desvio": "Renovações: levar ao Agger da corretora o que travou",
    "avisar": "Renovações: avisar a equipe",
}
PRIORIDADE_DA_RENOVACAO = 7          # a cotação continua 5 e passa na frente
POLITICA_DE_SESSAO = "madrugada"
RELEITURA_S = 600                    # o passo calcular relê os cálculos a cada 10 min
JANELA_DO_TICK = timedelta(hours=1)  # o tick roda a cada 5 min; um deploy no horário não pode perder o dia
IDADE_MAXIMA_S = 6 * 3600
#: o aplicativo na loja (📊 BLOCO 0: o slug novo é `renovacao` — 131-B; `renovacao-maxima` é o antigo, 0 instalados)
SLUGS_DO_APLICATIVO: Tuple[str, ...] = ("renovacao", "renovacao-maxima")
#: o motivo que um cálculo deixa e que é PASSAGEIRO (o desvio das 06:15 tenta no Agger da corretora)
MOTIVOS_PASSAGEIROS: Tuple[str, ...] = ("agger_da_pessoa_em_uso", "agger_da_pessoa_sem_resposta",
                                        "agger_da_pessoa_indisponivel", "calculo_expirado")
TIPO_PESSOA_EM_USO = "agger_da_pessoa_em_uso"     # o evento que o motor grava (motor.TIPO_PESSOA_EM_USO)
ESTADOS_TERMINAIS_DO_CALCULO: Tuple[str, ...] = ("fechado", "falhou", "incerto", "cancelado", "expirado")
MOTIVO_DO_DESVIO = "renovacao_desvio_0615"


class SemConexao(RuntimeError):
    """A InfoCap da corretora não abriu / não respondeu a lista."""


class DesvioIndisponivel(RuntimeError):
    """A porta desta versão não aceita forçar o Agger da corretora (`forcar_corretora_motivo`)."""


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _cliente(db: Any) -> Any:
    return getattr(db, "client", db)


def _dia(valor: Any) -> date:
    d = R.data_de(valor)
    if d is None:
        raise ValueError("dia precisa ser AAAA-MM-DD")
    return d


def _hora(texto: Any, padrao: str) -> time:
    for t in (texto, padrao):
        try:
            h, m = str(t).split(":")[:2]
            return time(int(h), int(m))
        except Exception:  # noqa: BLE001
            continue
    return time(0, 0)


def _tz(nome: Optional[str]):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome or R.FUSO_PADRAO)
    except Exception:  # noqa: BLE001
        return timezone(timedelta(hours=-3))


# ---------------------------------------------------------------------------------------------------------------------
# AS BORDAS — o teste troca estas (InfoCap HTTP, a ficha, a porta); o produto usa as peças que já existem
# ---------------------------------------------------------------------------------------------------------------------
async def abrir_fonte(db: Any, company_id: str) -> Any:
    """A InfoCap DESTA corretora pelo caminho canônico (`dono.abrir_fonte` → `_abrir`, nunca por nome — §13.9)."""
    from app.services.sistema_de_gestao import dono as DONO

    return await DONO.abrir_fonte(db, company_id)


async def dono_da_apolice(db: Any, company_id: str, *, codfil: Any, nosnum: Any, fonte: Any) -> Any:
    from app.services.sistema_de_gestao import dono as DONO

    return await DONO.dono_da_apolice(db, company_id, codfil=codfil, nosnum=nosnum, fonte=fonte)


async def ficha_da_apolice(db: Any, company_id: str, item: Mapping[str, Any], fonte: Any) -> Tuple[Any, Any]:
    """A FICHA ÚNICA COMPLETA (130-B), numa ÚNICA leitura da InfoCap: o pack do detalhe com a evidência documental →
    (a `Apolice` do cadastro RECONCILIADA com o documento, a `ApoliceDocumental` — linhas, franquias, objeto do risco,
    estado da leitura — ou None quando o documento não foi lido). É o par que `detalhar_apolice` + `documento_oficial`
    devolveriam, sem pedir o detalhe (e o PDF) duas vezes. `infocap:<codfil>:<nosnum>` é o locator técnico que o
    provider aceita (📊 `infocap_connector.py`).
    ⚠️ costura F4: antes era só `detalhar_apolice` e a ficha ia `None` — o `anterior` saía sem as linhas do PDF."""
    from app.providers.infocap_policy_provider import (InfoCapProvider, apolice_documental_do_pack,
                                                       apolice_reconciliada_do_pack)

    import os

    from app.core.database import create_async_supabase_client

    ref = f"infocap:{item.get('codfil') or 1}:{item.get('nosnum')}"
    # 🔴 costura F4 (canário 13/10): o conector do detalhe é a ROTA interna — exige a chave interna e o cliente ASSÍNCRONO
    # do banco (`await db.client.table(...)`), como o chamador do chat (`infocap_tool.py`, `_internal_key` +
    # `create_async_supabase_client`). Com o cliente síncrono do worker e sem a chave, TODO item virava `sem_conexao`
    chave = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    bruto = await InfoCapProvider().detail(company_id=company_id, policy_ref=ref, document_evidence_requested=True,
                                           db=await create_async_supabase_client(), internal_key=chave)
    pack = bruto.get("policy_evidence_pack") if isinstance(bruto, dict) else None
    if not isinstance(pack, dict):
        raise SemConexao(f"a InfoCap não devolveu a ficha (status={(bruto or {}).get('status')!r})")
    return apolice_reconciliada_do_pack(pack, apolice_ref=ref), apolice_documental_do_pack(pack)


async def perfil_do_segurado(db: Any, company_id: str, item: Mapping[str, Any], fonte: Any, *, apolice: Any = None,
                             ficha: Any = None, config: Optional[Mapping[str, Any]] = None
                             ) -> Optional[Dict[str, Dict[str, Any]]]:
    """O PERFIL do pedido ({grupo: {campo: valor}}: segurado, condutor, veículo, o endereço do risco — o que a `Apolice`
    NÃO carrega), montado por `perfil_da_renovacao.montar` (SPEC-131-A F5): a InfoCap MEDIDA (`/documento` → `/cliente`,
    `/itens` na data) → a ficha → a regra declarada da renovação, cada suposição em `nao_conferidos` (o objeto devolvido
    é um `PerfilMontado`: um dict com o atributo `nao_conferidos`).
    Conserto C1 (J-B1): sem a fonte, ou a InfoCap FALHOU (`FalhaDaInfocap`) → `SemConexao` — o item não é "falta um
    dado" quando o que faltou foi a InfoCap responder. Outro erro do montador → None: o item fica `pendente(falta_dado)`
    com os NOMES do que falta — nunca um dado inventado. ⛔ Nada é logado além do tipo do erro."""
    if fonte is None:
        raise SemConexao("sem a InfoCap da corretora, o perfil não se monta")
    from app.services.multicalculo import perfil_da_renovacao as PR

    try:
        perfil, nao = await asyncio.to_thread(PR.montar, company_id, item, apolice, ficha, fonte, config=config)
    except Exception as exc:  # noqa: BLE001 — o tipo basta; a mensagem pode carregar dado
        logger.info("[RENOV] perfil do segurado indisponível (%s)", type(exc).__name__)
        if type(exc).__name__ == "FalhaDaInfocap":
            raise SemConexao("a InfoCap não respondeu o perfil") from None
        return None
    return PR.PerfilMontado(perfil, nao)


async def _o_perfil(db: Any, company_id: str, item: Mapping[str, Any], fonte: Any, **contexto: Any) -> Any:
    """Chama a borda `perfil_do_segurado` com o contexto (apólice, ficha, config) que ELA aceita — o dublê de 4
    argumentos (os testes da F1/F4) continua servindo."""
    borda = perfil_do_segurado
    try:
        params = inspect.signature(borda).parameters
        livre = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        contexto = {k: v for k, v in contexto.items() if livre or k in params}
    except (TypeError, ValueError):
        contexto = {}
    return await borda(db, company_id, item, fonte, **contexto)


def _com_os_nao_conferidos(pedido: Any, nao: Mapping[str, str]) -> Any:
    """F5: o que o perfil SUPÔS vira `assumido` no pedido (o robô e a página sabem que não veio da pessoa) — só os
    nomes do catálogo do ramo; o porquê de cada um vai no evento do item."""
    from dataclasses import replace

    from app.services.multicalculo.perfil_da_renovacao import nomes_do_catalogo

    nomes = nomes_do_catalogo(int(getattr(pedido, "ramo")), nao)
    if not nomes:
        return pedido
    return replace(pedido, assumidos=frozenset(set(pedido.assumidos) | set(nomes)))


def comissao_anterior(fonte: Any, item: Mapping[str, Any]) -> Optional[float]:
    """D-131-16: o `per_c` do ano anterior (`FonteInfocap.comissao_da_corretora`, 📊 BLOCO 0 A5). Falhou → None (fica a
    comissão de hoje; nunca derruba o item)."""
    if fonte is None or not hasattr(fonte, "comissao_da_corretora"):
        return None
    try:
        return fonte.comissao_da_corretora(item.get("codfil") or 1, item.get("nosnum"))
    except Exception as exc:  # noqa: BLE001
        logger.info("[RENOV] comissão anterior ilegível (%s)", type(exc).__name__)
        return None


def de_apolice(apolice: Any, *, ficha: Any, config: Mapping[str, Any], perfil: Optional[Mapping[str, Any]] = None,
               comissao_anterior_pct: Optional[float] = None) -> Any:
    """`pedido.de_apolice` pelo CONTRATO da F2: a ficha COMPLETA, a config DA RENOVAÇÃO (as opções vêm dela) e a
    comissão do ano anterior."""
    from app.services.multicalculo import pedido as P

    return P.de_apolice(apolice, perfil, ficha=ficha, config=config, comissao_anterior_pct=comissao_anterior_pct)


#: o que a porta completa sozinha antes de conferir o pedido (`porta.calcular`): a comissão do ramo no RE (D-129C-05)
CAMPOS_QUE_A_PORTA_COMPLETA = frozenset({"comissao_desconto.comissao_percentual"})


def o_que_falta(pedido: Any) -> List[str]:
    """Os NOMES ("grupo.campo") que a porta recusaria (`PedidoIncompleto`) — a MESMA conta da porta (`faltando` na
    origem `auxiliar` + `sem_codigo`), menos o que ela mesma completa. Vazio = o pedido pode ir ao Agger."""
    try:
        # F5: a MESMA conta da porta na renovação — a placa supre FIPE/ano/combustível (`SERVICOS_EM_QUE_A_PLACA_SUPRE`)
        faltam = list(pedido.faltando(origem="auxiliar", servico="renovacao"))
        faltam += [c for c in pedido.sem_codigo() if c not in faltam]
    except Exception as exc:  # noqa: BLE001 — um pedido que nem se confere não está pronto
        return [f"pedido:{type(exc).__name__}"]
    return [c for c in faltam if c not in CAMPOS_QUE_A_PORTA_COMPLETA]


async def calcular_na_porta(db: Any, company_id: str, *, pedido: Any, renovacao_id: str, opcoes: List[str],
                            dono_user_id: Optional[str], vence_em_dias: int,
                            forcar_corretora_motivo: Optional[str] = None) -> str:
    """`porta.calcular` pelo CONTRATO REAL da F3 (async, devolve `PedidoAberto`). Devolve o `pedido_id`.
    As opções e as coberturas são as que o PEDIDO montou da ficha (F2: `opcoes`, `coberturas_por_opcao` — a
    `franquia_reduzida` cedida já não está lá); `opcoes` da config só quando o pedido não declarou as dele."""
    from app.services.multicalculo.porta import MulticalculoProvider

    porta = MulticalculoProvider()
    do_pedido = [str(o) for o in (getattr(pedido, "opcoes", None) or ())]
    coberturas = getattr(pedido, "coberturas_por_opcao", None)
    kw: Dict[str, Any] = dict(company_id=company_id, pedido=pedido, opcoes=do_pedido or list(opcoes),
                              servico="renovacao", dono_user_id=dono_user_id, vence_em_dias=vence_em_dias,
                              prioridade=PRIORIDADE_DA_RENOVACAO, politica_de_sessao=POLITICA_DE_SESSAO,
                              renovacao_id=renovacao_id)
    if isinstance(coberturas, Mapping) and coberturas:
        kw["coberturas"] = {str(k): dict(v) for k, v in coberturas.items()}
    if forcar_corretora_motivo is not None:
        if "forcar_corretora_motivo" not in inspect.signature(porta.calcular).parameters:
            raise DesvioIndisponivel("a porta desta versão não força o Agger da corretora")
        kw["forcar_corretora_motivo"] = forcar_corretora_motivo
        # 🔴 costura F4: o desvio vai ao Agger da CORRETORA — a política da madrugada (Prosseguir sobre a sessão da
        # DONA) não se aplica e a porta a RECUSA junto do desvio (`_da_madrugada`). Com o dublê da F1 o desvio
        # "passava"; com a porta real, todo desvio das 06:15 virava `falhou`
        kw["politica_de_sessao"] = None
    aberto = await porta.calcular(**kw)
    pid = aberto.get("pedido_id") if isinstance(aberto, Mapping) else getattr(aberto, "pedido_id", None)
    if not pid:
        raise RuntimeError("a porta não devolveu o pedido")
    return str(pid)


def carregar_config(db: Any, company_id: str) -> Dict[str, Any]:
    from app.services.multicalculo import config as C

    return C.carregar(company_id, db=_cliente(db), servico="renovacao")


# ---------------------------------------------------------------------------------------------------------------------
# Quem tem o aplicativo, em que fuso, e que passo venceu agora (o tick pergunta)
# ---------------------------------------------------------------------------------------------------------------------
def aplicativo_ligado(db: Any, company_id: str) -> bool:
    """O aplicativo de Renovação instalado E ativo (`tenant_auxiliaries`, o gesto "ligar" da loja que já existe)."""
    try:
        r = (_cliente(db).table("tenant_auxiliaries").select("slug, status, company_id")
             .eq("company_id", str(company_id)).in_("slug", list(SLUGS_DO_APLICATIVO)).eq("status", "active")
             .limit(1).execute())
        return any(str(x.get("company_id")) == str(company_id) for x in (r.data or []))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] aplicativos ilegíveis: %s", type(exc).__name__)
        return False


def fuso_da_corretora(db: Any, company_id: str) -> str:
    """O fuso da corretora (`renovacao.fuso_da_corretora`: o perfil do briefing; sem ele, São Paulo).
    🔴 BLOCO 0 A8: `tick._janela` rotula em UTC — os horários e o DIA da chave da madrugada vêm DESTE fuso."""
    return R.fuso_da_corretora(db, company_id)


def passos_devidos(db: Any, company_id: str, agora: datetime) -> List[Tuple[str, str]]:
    """[(passo, dia-local)] cujo horário (da janela da corretora, no fuso dela) chegou há ≤ 1 h. Puro sobre o banco
    lido: sem aplicativo ligado → []."""
    if not aplicativo_ligado(db, company_id):
        return []
    try:
        params = R.parametros(carregar_config(db, company_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] config ilegível (%s): a madrugada não roda sem ela", type(exc).__name__)
        return []
    return passos_na_janela(params["janela"], agora, fuso_da_corretora(db, company_id))


def passos_na_janela(janela: Mapping[str, Any], agora: datetime, fuso: str) -> List[Tuple[str, str]]:
    tz = _tz(fuso)
    local = agora.astimezone(tz)
    saida = []
    for passo in PASSOS:
        alvo = _hora(janela.get(passo), R.JANELA_PADRAO[passo])
        momento = local.replace(hour=alvo.hour, minute=alvo.minute, second=0, microsecond=0)
        if momento <= local <= momento + JANELA_DO_TICK:
            saida.append((passo, local.date().isoformat()))
    return saida


def _momento_local(janela: Mapping[str, Any], passo: str, dia: date, fuso: str) -> datetime:
    alvo = _hora(janela.get(passo), R.JANELA_PADRAO[passo])
    return datetime(dia.year, dia.month, dia.day, alvo.hour, alvo.minute, tzinfo=_tz(fuso))


# ---------------------------------------------------------------------------------------------------------------------
# Os motivos — o que a ficha/o pedido/a porta disseram, em código curto
# ---------------------------------------------------------------------------------------------------------------------
def motivo_da_excecao(exc: BaseException, *, ficha: Any = None) -> Tuple[str, str]:
    """(estado, motivo) de uma recusa ao montar ou pedir o cálculo. `RamoIndisponivel` nunca vira AUTO (mutação 3)."""
    nome = type(exc).__name__
    if nome == "RamoIndisponivel":
        motivo = getattr(exc, "motivo", None)
        return "pendente", motivo if motivo in ("ramo_nao_cotado", "ramo_desconhecido") else "ramo_nao_cotado"
    if nome == "RamoNaoSuportado":
        return "pendente", "ramo_nao_cotado"
    if nome == "FichaIncompleta":
        return "pendente", "sem_pdf" if ficha is None else "falta_dado"
    if nome in ("PedidoIncompleto", "PerfilIncompleto", "CampoDesconhecido"):
        return "pendente", "falta_dado"
    if nome == "DocumentoInvalido":
        return "pendente", "documento_invalido"
    if nome == "ContaRecusada":
        return "falhou", "conta_recusada"
    if nome == "DesvioIndisponivel":
        return "falhou", "desvio_indisponivel"
    if nome in ("ChaveAusente", "PresetIndisponivel", "NaoAutorizado", "OrigemRecusada"):
        return "falhou", "porta_recusou"
    return "falhou", "erro_inesperado"


#: os motivos que o MOTOR (F3) põe na frente do `erro` do cálculo e que a renovação grava como estão: a dona no
#: próprio Agger (`agger_*`, passageiros — o desvio os leva à corretora) e a licença do Agger vencida (D-131-36: falha
#: com motivo humano; NÃO é passageiro — a conta da corretora também precisa da licença)
MOTIVO_LICENCA_VENCIDA = "licenca_agger_vencida"


def _motivo_do_calculo(calc: Mapping[str, Any]) -> str:
    erro = str(calc.get("erro") or "").strip()
    cabeca = erro.split(" ", 1)[0] if erro else ""
    # conserto C1: a recusa de RAMO/VEÍCULO que o motor escrever com o código na frente ("ramo_nao_cotado — …",
    # "veiculo_… — …") passa como está — ela é DEFINITIVA (`falhou_definitivo`) e tem a frase do ramo
    if cabeca and R.motivo_valido(cabeca) and (cabeca.startswith("agger_") or cabeca == MOTIVO_LICENCA_VENCIDA
                                               or cabeca in R.MOTIVOS_NAO_COTAVEIS or cabeca.startswith("veiculo_")):
        return cabeca
    return "calculo_" + str(calc.get("status") or "falhou")


#: conserto C1 (J-B2 · RT-P7 · J-P2): o `falhou` que a próxima noite repetiria IGUAL — todas as seguradoras recusaram
#: (`calculo_fechado` sem oferta), alguém cancelou, o ramo/veículo que o Agger não cota. Não volta a `pronta` sozinho.
MOTIVOS_DEFINITIVOS: Tuple[str, ...] = ("calculo_fechado", "calculo_cancelado")
#: os cálculos que já estão NO ROBÔ (o `repositorio.cancelar` do desvio só cancela os `na_fila`)
STATUS_NO_ROBO: Tuple[str, ...] = ("disparando", "calculando")


def falhou_definitivo(motivo: Any) -> bool:
    m = str(motivo or "")
    return m in MOTIVOS_DEFINITIVOS or m in R.MOTIVOS_NAO_COTAVEIS or m.startswith("veiculo_")


def _ts(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def noites_que_falhou(repo: Any, company_id: str, renovacao_id: str, fuso: str) -> int:
    """Em quantas NOITES (o dia local da corretora) o item chegou a `falhou` — contado pelos eventos da máquina."""
    tz = _tz(fuso)
    noites = set()
    for e in repo.eventos(company_id, renovacao_id):
        if e.get("para") != "falhou":
            continue
        t = _ts(e.get("criado_em"))
        if t is not None:
            noites.add(t.astimezone(tz).date())
    return len(noites)


def estado_derivado(calculos: List[Mapping[str, Any]], ofertas: int, pessoa_em_uso: bool) -> Tuple[str, Optional[str]]:
    """O estado da renovação DERIVADO dos cálculos do pedido (pull, nunca callback do motor).

    todos terminais + ≥ 1 oferta → calculada · todos terminais sem oferta → falhou(motivo do 1º cálculo) ·
    algum em curso com a dona no próprio Agger (evento do motor) → aguardando_agger · senão → calculando."""
    if not calculos:
        return "calculando", None
    terminais = all(str(c.get("status")) in ESTADOS_TERMINAIS_DO_CALCULO for c in calculos)
    if terminais:
        if ofertas > 0:
            return "calculada", None
        motivo = _motivo_do_calculo(calculos[0])
        # confirmação N1: a moto que só a PLACA revelou (o Agger devolve tipoVeic "m") não é falha do robô — é um ramo
        # que o aplicativo não cota (D-131-28): vira pendência "renove manualmente", fora do denominador dos cotáveis
        if motivo == "veiculo_moto":
            return "pendente", "ramo_nao_cotado"
        return "falhou", motivo
    if pessoa_em_uso:
        return "aguardando_agger", None
    return "calculando", None


def _ler_o_pedido(db: Any, company_id: str, pedido_id: str) -> Tuple[List[Dict[str, Any]], int, bool]:
    """Os cálculos, as ofertas e o evento "a dona está no Agger" do pedido — com a corretora no filtro (§7)."""
    cli = _cliente(db)
    calcs = [dict(x) for x in (cli.table("multicalculo_calculos")
                               .select("id, status, erro, batida_em, solicitante_company_id")
                               .eq("pedido_id", pedido_id).eq("solicitante_company_id", company_id)
                               .execute().data or [])
             if str(x.get("solicitante_company_id")) == str(company_id)]
    ofertas = [x for x in (cli.table("multicalculo_ofertas").select("id, solicitante_company_id")
                           .eq("pedido_id", pedido_id).eq("solicitante_company_id", company_id)
                           .execute().data or [])
               if str(x.get("solicitante_company_id")) == str(company_id)]
    em_curso = {str(c["id"]) for c in calcs if str(c.get("status")) not in ESTADOS_TERMINAIS_DO_CALCULO}
    pessoa = False
    if em_curso:
        evs = (cli.table("multicalculo_eventos").select("calculo_id, tipo, solicitante_company_id")
               .eq("pedido_id", pedido_id).eq("solicitante_company_id", company_id).eq("tipo", TIPO_PESSOA_EM_USO)
               .execute().data or [])
        pessoa = any(str(e.get("calculo_id")) in em_curso for e in evs)
    return calcs, len(ofertas), pessoa


# ---------------------------------------------------------------------------------------------------------------------
# O PASSO 1 — preparar
# ---------------------------------------------------------------------------------------------------------------------
async def _ler_a_lista(db: Any, company_id: str, dia: date, params: Mapping[str, Any]) -> Tuple[Any, List[Dict]]:
    try:
        fonte = await abrir_fonte(db, company_id)
    except Exception as exc:  # noqa: BLE001 — o tipo basta; a mensagem pode carregar dado da conexão
        raise SemConexao(f"a InfoCap da corretora não abriu ({type(exc).__name__})") from None
    # D-131-33: a lista cobre também o que o calcular pode ANTECIPAR (os próximos `antecipar_ate_dias`)
    fim = dia + timedelta(days=int(params["antecedencia_dias"]) + int(params["antecipar_ate_dias"])
                          + int(params["margem_dias"]))
    try:
        crus = await asyncio.to_thread(fonte.renovacoes_cruas, dia, fim)
    except Exception as exc:  # noqa: BLE001
        raise SemConexao(f"a InfoCap não respondeu as renovações ({type(exc).__name__})") from None
    return fonte, list(crus or [])


async def _avaliar(db: Any, company_id: str, item: Mapping[str, Any], fonte: Any, cfg: Mapping[str, Any]
                   ) -> Tuple[str, Optional[str], Any, Optional[Dict[str, Any]]]:
    """(estado, motivo, pedido, dados do evento) de UM item: ficha COMPLETA → perfil → comissão anterior → de_apolice
    → a MESMA conferência da porta. `pronta` = o pedido que a porta aceitaria; o que falta vira `pendente(falta_dado)`
    com os NOMES dos campos no evento (nunca valores). Nada é gravado aqui."""
    sigla = str(item.get("ramo_sigla") or "").strip()
    if sigla:
        # 🔴 costura F4 (canário 13/10): o ramo da LISTA decide antes da ficha — o ramo que o Agger não cota (ou que
        # ninguém reconhece) não gasta a leitura da ficha (o PDF e o modelo) e não vira `sem_conexao` quando a InfoCap
        # do detalhe falha: ele é `ramo_nao_cotado`/`ramo_desconhecido`, e SAI das cotáveis
        from app.services.multicalculo import pedido as P

        try:
            P._ramo_do_agger(SimpleNamespace(ramo=sigla))
        except P.RamoIndisponivel as exc:
            return (*motivo_da_excecao(exc), None, None)
    if fonte is None:
        # conserto C1 (J-B1): sem a InfoCap o item NÃO é reavaliado — o que faltou foi a conexão, nunca um dado
        return "pendente", "sem_conexao", None, None
    try:
        apolice, ficha = await ficha_da_apolice(db, company_id, item, fonte)
    except Exception as exc:  # noqa: BLE001
        logger.info("[RENOV] ficha indisponível (%s)", type(exc).__name__)
        return "pendente", "sem_conexao", None, None
    nao: Dict[str, str] = {}
    infocap_caiu = False
    try:
        perfil = await _o_perfil(db, company_id, item, fonte, apolice=apolice, ficha=ficha, config=cfg)
    except SemConexao:
        perfil, infocap_caiu = None, True       # J-B1: a InfoCap caiu no meio do perfil
    except Exception as exc:  # noqa: BLE001
        estado, motivo = motivo_da_excecao(exc, ficha=ficha)
        return (estado, motivo, None, None) if estado == "pendente" else ("pendente", "falta_dado", None, None)
    try:
        nao = dict(getattr(perfil, "nao_conferidos", None) or {})
        # sem o perfil (a InfoCap não respondeu o `/documento`) o pedido não fecha — e a comissão anterior leria o MESMO
        # `/documento` de novo (mais 3 tentativas, ~9 s por item): não se pede o que não muda o resultado
        pedido = de_apolice(apolice, ficha=ficha, config=cfg, perfil=perfil,
                            comissao_anterior_pct=comissao_anterior(fonte, item) if perfil is not None else None)
        if nao:
            pedido = _com_os_nao_conferidos(pedido, nao)
    except Exception as exc:  # noqa: BLE001
        if infocap_caiu:
            return "pendente", "sem_conexao", None, None
        estado, motivo = motivo_da_excecao(exc, ficha=ficha)
        if estado != "pendente":
            estado, motivo = "pendente", "falta_dado"
        return estado, motivo, None, None
    # F5: o porquê de cada suposição vai no evento (só NOMES e as frases das regras — nunca valores)
    supostos = {"nao_conferidos": dict(sorted(nao.items()))} if nao else {}
    faltam = o_que_falta(pedido)
    if faltam and infocap_caiu:
        return "pendente", "sem_conexao", None, None     # o que falta é o que a InfoCap não respondeu
    if faltam:
        return "pendente", "falta_dado", None, {"faltando": faltam[:40], **supostos}
    return "pronta", None, pedido, (supostos or None)


async def preparar_dia(db: Any, company_id: str, dia: Any, *, por: str = "madrugada.preparar",
                       canario: bool = False) -> Dict[str, int]:
    """A LISTA CONGELADA do dia e, por item, EM SÉRIE (📊 "10 paralelas → um 500", dono.py), pronta|pendente.
    `canario=True` (só `scripts/canario_madrugada_renovacao.py`): os itens NOVOS nascem com `renovacoes.canario`."""
    cid = R._uuid(company_id)
    d = _dia(dia)
    repo = R.RepositorioDeRenovacoes(db)
    cfg = carregar_config(db, cid)
    params = R.parametros(cfg)
    fonte, crus = await _ler_a_lista(db, cid, d, params)
    vistos = set()
    listadas = 0
    for cru in crus:
        campos = R.linha_da_infocap(cru, hmac_chave=None) if _tem_chave_hmac() else _sem_hmac(cru)
        if campos is None:
            continue
        chave = R.chave_do_item(campos)
        if chave in vistos:
            continue
        vistos.add(chave)
        _linha, criada = repo.upsert_da_lista(cid, campos, por=por, canario=canario)
        listadas += int(criada)

    resultado = {"listadas": listadas, "prontas": 0, "pendentes": 0, "ja_em_curso": 0, "falhou_definitivo": 0,
                 "precisa_de_voce": 0}
    fuso = fuso_da_corretora(db, cid)
    for item in sorted(repo.listar(cid, estados=R.ESTADOS_PREPARAVEIS), key=lambda x: (str(x["fimvig"]),
                                                                                       str(x["nosnum"]))):
        if R.chave_do_item(item) not in vistos:
            continue      # fora da lista de hoje (endosso, cancelamento): a conferência decide, não a preparação
        # conserto C1 (J-B2 · RT-P7 · J-P2): a retentativa tem FIM. O `falhou` definitivo não volta sozinho; o
        # passageiro volta no máximo `VOLTAS_DO_FALHOU` noites e depois vira `pendente(precisa_de_voce)` — que também
        # não volta sozinho (a pessoa decide)
        if item["estado"] == "pendente" and item.get("motivo") == "precisa_de_voce":
            resultado["precisa_de_voce"] += 1
            continue
        if item["estado"] == "falhou":
            if falhou_definitivo(item.get("motivo")):
                resultado["falhou_definitivo"] += 1
                continue
            noites = noites_que_falhou(repo, cid, str(item["id"]), fuso)
            if noites > R.VOLTAS_DO_FALHOU:
                repo.transicionar(cid, item["id"], "pendente", por=por, motivo="precisa_de_voce",
                                  dados={"noites_que_falhou": noites, "ultimo_motivo": str(item.get("motivo") or "")})
                resultado["precisa_de_voce"] += 1
                resultado["pendentes"] += 1
                continue
        fim = _dia(item["fimvig"])
        campos: Dict[str, Any] = {"calcular_em": (fim - timedelta(days=int(params["antecedencia_dias"]))).isoformat()}
        dono = await dono_da_apolice(db, cid, codfil=item["codfil"], nosnum=item["nosnum"], fonte=fonte)
        status = str(getattr(dono, "status", "") or "")
        if status == "sem_conexao":
            repo.transicionar(cid, item["id"], "pendente", por=por, motivo="sem_conexao", campos=campos)
            resultado["pendentes"] += 1
            continue
        uid = getattr(dono, "user_id", None) if status == "ok" else None
        campos["dono_user_id"] = uid
        campos["dono_motivo"] = status or None
        campos["responsavel_user_id"] = repo.substituto_de(cid, uid, d.isoformat()) or uid
        estado, motivo, pedido, dados = await _avaliar(db, cid, item, fonte, cfg)
        if estado == "pronta" and _ficou_de_ontem(item):
            motivo = R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE      # SPEC-132: a marca sobrevive à reavaliação da lista
        if pedido is not None:
            try:
                campos["ramo_agger"] = int(getattr(pedido, "ramo"))
            except (TypeError, ValueError):
                pass
        repo.transicionar(cid, item["id"], estado, por=por, motivo=motivo, campos=campos, dados=dados)
        resultado["prontas" if estado == "pronta" else "pendentes"] += 1
    return resultado


def _tem_chave_hmac() -> bool:
    import os

    return bool(os.environ.get("MULTICALCULO_HMAC_KEY"))


def _sem_hmac(cru: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Sem `MULTICALCULO_HMAC_KEY` a lista ainda se monta — com o documento só MASCARADO (o HMAC fica nulo)."""
    logger.warning("[RENOV] MULTICALCULO_HMAC_KEY ausente: a lista sai sem o HMAC do documento")
    limpo = dict(cru)
    doc = limpo.pop("cic", None)
    limpo.pop("cpf_cnpj", None)
    campos = R.linha_da_infocap(limpo)
    if campos is not None:
        campos["documento_mascarado"] = R.mascarar_documento(doc)
    return campos


# ---------------------------------------------------------------------------------------------------------------------
# O PASSO 2 — calcular (disparar) e acompanhar (derivar)
# ---------------------------------------------------------------------------------------------------------------------
def _pedido_de_hoje(db: Any, cid: str, item: Mapping[str, Any], dia: date) -> Optional[str]:
    """O pedido que a porta JÁ gravou hoje (dia local da corretora) para esta renovação, não cancelado e diferente do
    que o item já aponta — o rastro de uma queda entre a porta e o `calculando`. Banco ilegível → None (segue a porta,
    que ainda devolve o `aberto`)."""
    try:
        linhas = (_cliente(db).table("multicalculo_pedidos").select("id, company_id, status, criado_em")
                  .eq("company_id", cid).eq("renovacao_id", str(item["id"])).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] pedidos da renovação ilegíveis (%s)", type(exc).__name__)
        return None
    inicio = datetime(dia.year, dia.month, dia.day, tzinfo=_tz(fuso_da_corretora(db, cid)))
    atual = str(item.get("pedido_id") or "")
    vivos = [x for x in linhas if str(x.get("company_id")) == cid and str(x.get("status")) != "cancelado"
             and str(x.get("id")) != atual and (_ts(x.get("criado_em")) or inicio - timedelta(days=1)) >= inicio]
    # confirmação N3: adotar só o que ainda vale — `aberto` (a queda entre a porta e o `calculando`) ou `fechado` COM
    # oferta; um pedido do dia que fechou SEM oferta não é adotado (o recálculo legítimo segue para a porta)
    def _vale(x: Mapping[str, Any]) -> bool:
        st = str(x.get("status"))
        if st == "aberto":
            return True
        if st != "fechado":
            return False
        try:
            return bool(_cliente(db).table("multicalculo_ofertas").select("id").eq("pedido_id", str(x["id"]))
                        .eq("solicitante_company_id", cid).limit(1).execute().data)
        except Exception:  # noqa: BLE001 — ilegível: não adota (a porta ainda devolve o `aberto`)
            return False
    vivos = [x for x in vivos if _vale(x)]
    if not vivos:
        return None
    return str(max(vivos, key=lambda x: _ts(x.get("criado_em")))["id"])


async def _pedir(db: Any, cid: str, item: Mapping[str, Any], dia: date, cfg: Mapping[str, Any], params: Mapping,
                 fonte: Any, *, por: str, forcar: Optional[str] = None) -> str:
    """Monta o pedido de novo (a ficha de AGORA) e chama a porta. Devolve o estado novo do item.
    Conserto C1 (J-P5): a queda entre `porta.calcular` e o `calculando` deixava o item `pronta` com o pedido já
    gravado — a retomada abria o 2º. Agora o pedido DE HOJE da renovação (não cancelado, e que não é o que o item já
    aponta) é ADOTADO, sem ir à porta."""
    repo = R.RepositorioDeRenovacoes(db)
    ja = _pedido_de_hoje(db, cid, item, dia)
    if ja is not None:
        logger.info("[RENOV] a renovação já tem o pedido de hoje: adotado, nenhum pedido novo")
        repo.transicionar(cid, item["id"], "calculando", por=por, campos={"pedido_id": ja},
                          dados={"adotado": True, **({"desvio": True} if forcar else {})})
        return "calculando"
    estado, motivo, pedido, dados = await _avaliar(db, cid, item, fonte, cfg)
    if pedido is None:
        novo = estado if item["estado"] != "aguardando_agger" else "falhou"
        repo.transicionar(cid, item["id"], novo, por=por, motivo=motivo, dados=dados)
        return novo
    vence = (_dia(item["fimvig"]) - dia).days
    try:
        pid = await calcular_na_porta(db, cid, pedido=pedido, renovacao_id=str(item["id"]),
                                      opcoes=list(params["opcoes"]), dono_user_id=item.get("dono_user_id"),
                                      vence_em_dias=vence, forcar_corretora_motivo=forcar)
    except Exception as exc:  # noqa: BLE001
        novo, motivo = motivo_da_excecao(exc)
        if novo == "pendente" and item["estado"] in ("aguardando_agger",):
            novo = "falhou"
        logger.info("[RENOV] a porta recusou (%s → %s)", type(exc).__name__, motivo)
        repo.transicionar(cid, item["id"], novo, por=por, motivo=motivo)
        return novo
    repo.transicionar(cid, item["id"], "calculando", por=por, campos={"pedido_id": pid},
                      dados={"desvio": bool(forcar)} if forcar else None)
    return "calculando"


def _ficou_de_ontem(x: Mapping[str, Any]) -> bool:
    return x.get("estado") == "pronta" and x.get("motivo") == R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE


def escolher_da_noite(prontas: List[Mapping[str, Any]], dia: date, *, teto: Optional[int], antecipar_ate_dias: int
                      ) -> Tuple[List[Mapping[str, Any]], Dict[str, int]]:
    """O que sai ESTA noite e em que ORDEM, puro (SPEC-132; era D-131-33 com teto 12 fixo):

    · as VENCIDAS (calcular_em ≤ dia — o atraso de ontem entra hoje) saem TODAS; nenhum teto as corta
    · a ANTECIPAÇÃO: `pronta` que vencem nos próximos `antecipar_ate_dias` (calcular_em ≤ dia + N). `teto=None` (o
      padrão) = TODAS entram na fila e o RELÓGIO decide até onde a noite chega (`ultimo_inicio`); com teto (30–500,
      da corretora), por conta do Agger (`renovacao.chave_da_conta`), só até ele — a vencida acima dele conta em
      `acima_do_teto` e sai assim mesmo (o atraso é pior)
    Ordem do disparo = a da fila do motor: vencidas, depois antecipadas; dentro de cada, o VENCIMENTO MAIS PRÓXIMO
    primeiro e, no empate, a que ficou da noite anterior (`ficou_para_a_proxima_noite`) na frente."""
    hoje, limite = dia.isoformat(), (dia + timedelta(days=max(0, int(antecipar_ate_dias)))).isoformat()
    chave = lambda x: (str(x.get("fimvig")), 0 if _ficou_de_ontem(x) else 1,  # noqa: E731
                       int(x.get("ramo_agger") or 999), str(x.get("nosnum")))
    vencidas = sorted((x for x in prontas if str(x.get("calcular_em") or "") <= hoje), key=chave)
    futuras = sorted((x for x in prontas if hoje < str(x.get("calcular_em") or "9999") <= limite), key=chave)
    if teto is None:
        return vencidas + futuras, {"vencidas": len(vencidas), "antecipadas": len(futuras), "acima_do_teto": 0}
    usados: Dict[str, int] = {}
    for x in vencidas:
        usados[R.chave_da_conta(x)] = usados.get(R.chave_da_conta(x), 0) + 1
    antecipadas = []
    for x in futuras:
        conta = R.chave_da_conta(x)
        if usados.get(conta, 0) < teto:
            usados[conta] = usados.get(conta, 0) + 1
            antecipadas.append(x)
    acima = sum(max(0, n - teto) for n in usados.values())
    return vencidas + antecipadas, {"vencidas": len(vencidas), "antecipadas": len(antecipadas), "acima_do_teto": acima}


def ultimo_inicio(janela: Mapping[str, Any], dia: date, fuso: str) -> datetime:
    """SPEC-132 — a HORA-LIMITE do dia: depois dela nenhum cálculo de renovação COMEÇA (a régua de `config`)."""
    from app.services.multicalculo import config as C

    alvo = _hora(C.ultimo_inicio_coerente(janela), R.JANELA_PADRAO["ultimo_inicio"])
    return datetime(dia.year, dia.month, dia.day, alvo.hour, alvo.minute, tzinfo=_tz(fuso))


def _marcar_para_a_proxima_noite(repo: Any, cid: str, item: Mapping[str, Any], d: date, *, por: str,
                                 hora: str) -> bool:
    try:
        repo.transicionar(cid, item["id"], "pronta", por=por, motivo=R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE,
                          dados={"noite": d.isoformat(), "hora_limite": hora})
        return True
    except (R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        logger.warning("[RENOV] não marquei para a próxima noite (%s)", type(exc).__name__)
        return False


async def calcular_dia(db: Any, company_id: str, dia: Any, *, por: str = "madrugada.calcular",
                       agora: Optional[datetime] = None) -> Dict[str, int]:
    """Tudo o que está `pronta` e vence (calcular_em ≤ dia), mais a antecipação (SPEC-132: sem teto por padrão),
    enfileirado de uma vez, o vencimento mais próximo primeiro — a fila do motor serializa por login e a madrugada usa
    uma sessão por corretora. `agora` (o workflow passa o relógio): passou da hora-limite (`ultimo_inicio`) → NADA
    começa; as escolhidas ficam `pronta(ficou_para_a_proxima_noite)`. Sem `agora` (o canário, os testes de unidade),
    o relógio não é consultado."""
    cid = R._uuid(company_id)
    d = _dia(dia)
    repo = R.RepositorioDeRenovacoes(db)
    cfg = carregar_config(db, cid)
    params = R.parametros(cfg)
    limite = d + timedelta(days=int(params["antecipar_ate_dias"]))
    prontas = repo.listar(cid, estados=("pronta",), calcular_ate=limite.isoformat())
    itens, escolha = escolher_da_noite(prontas, d, teto=params["teto_por_conta_noite"],
                                       antecipar_ate_dias=int(params["antecipar_ate_dias"]))
    resultado = {"disparados": 0, "pendentes": 0, "falharam": 0, "ficaram_para_a_proxima_noite": 0, **escolha}
    if not itens:
        return resultado
    if agora is not None:
        hora_limite = ultimo_inicio(params["janela"], d, fuso_da_corretora(db, cid))
        if agora >= hora_limite:
            logger.warning("[RENOV] o calcular chegou depois da hora-limite: nada começa, %s ficam para a próxima "
                           "noite", len(itens))
            hora = hora_limite.strftime("%H:%M")
            resultado["ficaram_para_a_proxima_noite"] = sum(
                _marcar_para_a_proxima_noite(repo, cid, x, d, por=por, hora=hora) for x in itens)
            return resultado
    try:
        fonte = await abrir_fonte(db, cid)
    except Exception as exc:  # noqa: BLE001 — sem a InfoCap a ficha não se monta
        logger.warning("[RENOV] calcular sem a InfoCap (%s): as prontas ficam sem_conexao", type(exc).__name__)
        fonte = None
    if fonte is None:
        # 🔴 conserto C1 (J-B1): sem a fonte o item NÃO é reavaliado (antes o `_pedir` rodava assim mesmo e a `pronta`
        # virava `pendente(falta_dado)`). `pendente(sem_conexao)`: o aviso diz "a InfoCap não respondeu", a completude
        # não o conta como feito, e a preparação da próxima noite o reavalia
        for item in itens:
            try:
                repo.transicionar(cid, item["id"], "pendente", por=por, motivo="sem_conexao",
                                  dados={"passo": "calcular"})
            except (R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
                logger.warning("[RENOV] item não marcado sem_conexao (%s)", type(exc).__name__)
                continue
            resultado["pendentes"] += 1
        resultado["sem_conexao"] = len(itens)
        return resultado
    for item in itens:
        novo = await _pedir(db, cid, item, d, cfg, params, fonte, por=por)
        chave = {"calculando": "disparados", "pendente": "pendentes"}.get(novo, "falharam")
        resultado[chave] += 1
    return resultado


async def cancelar_na_porta(db: Any, company_id: str, *, pedido_id: str) -> int:
    """A BORDA do cancelamento: `porta.cancelar` (pedido → cancelado; SÓ os cálculos `na_fila` → cancelado; os que já
    estão no robô o motor termina). Devolve quantos cálculos saíram da fila."""
    from app.services.multicalculo.porta import MulticalculoProvider

    return int(await MulticalculoProvider().cancelar(company_id=company_id, pedido_id=pedido_id) or 0)


async def adiar_o_que_nao_comecou(db: Any, company_id: str, dia: Any, *, por: str = "madrugada.calcular"
                                  ) -> Dict[str, int]:
    """SPEC-132 — a HORA-LIMITE chegou: todo item `calculando` cujo pedido tem TODOS os cálculos ainda `na_fila`
    (nenhum começou no Agger) tem o pedido cancelado e volta `pronta(ficou_para_a_proxima_noite)` — a noite seguinte o
    pega primeiro. Um cálculo que já começou NÃO é tocado (termina e é derivado). Se a fila perdeu a corrida (o motor
    pegou um no meio do cancelamento: cancelou menos que todos), o item fica `calculando` — nunca dois negócios."""
    cid = R._uuid(company_id)
    d = _dia(dia)
    repo = R.RepositorioDeRenovacoes(db)
    params = R.parametros(carregar_config(db, cid))
    hora = ultimo_inicio(params["janela"], d, fuso_da_corretora(db, cid)).strftime("%H:%M")
    r = {"ficaram_para_a_proxima_noite": 0, "ja_no_robo": 0}
    for item in repo.listar(cid, estados=("calculando",)):
        pid = str(item.get("pedido_id") or "")
        if not pid:
            continue
        calcs, ofertas, _pessoa = _ler_o_pedido(db, cid, pid)
        if not calcs or ofertas or any(str(c.get("status")) != "na_fila" for c in calcs):
            r["ja_no_robo"] += 1
            continue
        try:
            cancelados = await cancelar_na_porta(db, cid, pedido_id=pid)
        except Exception as exc:  # noqa: BLE001 — a porta recusou: o item segue como está (o motor o leva)
            logger.warning("[RENOV] não consegui tirar da fila (%s)", type(exc).__name__)
            continue
        if cancelados < len(calcs):
            logger.warning("[RENOV] a fila perdeu a corrida: %s de %s cálculos já tinham começado", len(calcs) - cancelados,
                           len(calcs))
            r["ja_no_robo"] += 1
            continue
        r["ficaram_para_a_proxima_noite"] += int(_marcar_para_a_proxima_noite(repo, cid, item, d, por=por, hora=hora))
    return r


def acompanhar(db: Any, company_id: str, *, por: str) -> Dict[str, int]:
    """UMA releitura: cada item em voo recebe o estado DERIVADO dos cálculos do pedido dele."""
    cid = R._uuid(company_id)
    repo = R.RepositorioDeRenovacoes(db)
    contagem = {"calculadas": 0, "falharam": 0, "em_voo": 0}
    for item in repo.listar(cid, estados=R.ESTADOS_EM_VOO):
        if not item.get("pedido_id"):
            contagem["em_voo"] += 1
            continue
        calcs, ofertas, pessoa = _ler_o_pedido(db, cid, str(item["pedido_id"]))
        estado, motivo = estado_derivado(calcs, ofertas, pessoa)
        if estado != item["estado"]:
            try:
                repo.transicionar(cid, item["id"], estado, por=por, motivo=motivo)
            except (R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
                logger.warning("[RENOV] releitura não gravou (%s)", type(exc).__name__)
        if estado == "calculada":
            contagem["calculadas"] += 1
        elif estado == "falhou":
            contagem["falharam"] += 1
        else:
            contagem["em_voo"] += 1
    return contagem


async def _acompanhar_ou_dormir(ctx: dict, db: Any, cid: str, dia: date, *, ate_passo: str, passo: str) -> Any:
    """Relê; ainda há item em voo e o relógio não passou de `ate_passo` → DORME 10 min (espera durável 129-A).
    SPEC-132 (passo calcular): passou da HORA-LIMITE (`ultimo_inicio`) → o que ainda não começou fica para a próxima
    noite (`adiar_o_que_nao_comecou`); antes dela, o sono acorda NA hora-limite, nunca 10 min depois."""
    contagem = await asyncio.to_thread(acompanhar, db, cid, por=f"madrugada.{passo}")
    if contagem["em_voo"] <= 0:
        return contagem
    params = R.parametros(carregar_config(db, cid))
    fuso = fuso_da_corretora(db, cid)
    limite = _momento_local(params["janela"], ate_passo, dia, fuso)
    agora = _agora()
    acordar_em = float(RELEITURA_S)
    if passo == "calcular":
        hora_limite = ultimo_inicio(params["janela"], dia, fuso)
        if agora >= hora_limite:
            adiadas = await adiar_o_que_nao_comecou(db, cid, dia, por=f"madrugada.{passo}")
            contagem["ficaram_para_a_proxima_noite"] = adiadas["ficaram_para_a_proxima_noite"]
            contagem["em_voo"] = max(0, contagem["em_voo"] - adiadas["ficaram_para_a_proxima_noite"])
            if contagem["em_voo"] <= 0:
                return contagem
        else:
            acordar_em = min(acordar_em, (hora_limite - agora).total_seconds())
    if agora >= limite:
        return contagem
    falta = (limite - agora).total_seconds()
    return ctx["runs"].dormir(ctx["run_id"], lease_token=ctx.get("lease_token"),
                              acordar_em_s=min(acordar_em, max(60, falta)),
                              wait_for={"tipo": "renovacao_calculos", "ref": f"{passo}:{dia.isoformat()}",
                                        "prazo_s": int(falta) + 900, "passo": "acompanhar"},
                              company_id=cid)


# ---------------------------------------------------------------------------------------------------------------------
# O PASSO 4 — o desvio das 06:15 (o Agger da corretora, COM aviso nomeado — nunca calado)
# ---------------------------------------------------------------------------------------------------------------------
async def desvio_dia(db: Any, company_id: str, dia: Any, *, por: str = "madrugada.desvio",
                     work_run_id: Optional[str] = None) -> Dict[str, int]:
    cid = R._uuid(company_id)
    d = _dia(dia)
    repo = R.RepositorioDeRenovacoes(db)
    resultado = {"desviados": 0, "falharam": 0, "esperando_o_robo": 0, "sem_conexao": 0}
    # 🔴 conserto C1 (RT-B1): o estado GRAVADO é da última releitura do calcular (a hora da conferência); a retentativa do motor
    # pode ter calculado no Agger da DONA entre a conferência e o desvio. RELÊ os cálculos ANTES de escolher o que desviar —
    # o item que já saiu vira `calculada` aqui e não abre o 2º negócio no Agger da corretora
    try:
        acompanhar(db, cid, por=por)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] desvio: releitura antes da lista falhou (%s)", type(exc).__name__)
    alvo = []
    for x in repo.listar(cid, estados=("aguardando_agger", "falhou"), calcular_ate=d.isoformat()):
        if not (x["estado"] == "aguardando_agger" or str(x.get("motivo") or "") in MOTIVOS_PASSAGEIROS):
            continue
        if x.get("pedido_id"):
            # e, por item, o pedido da dona de AGORA: com oferta (já saiu) ou com cálculo NO ROBÔ (o `cancelar` da
            # porta só cancela `na_fila` — desviar deixaria dois negócios vivos) → não desvia; a releitura do passo
            # desvio deriva o resultado
            calcs, ofertas, _pessoa = _ler_o_pedido(db, cid, str(x["pedido_id"]))
            if ofertas > 0 or any(str(c.get("status")) in STATUS_NO_ROBO for c in calcs):
                resultado["esperando_o_robo"] += 1
                continue
        alvo.append(x)
    if not alvo:
        return resultado
    cfg = carregar_config(db, cid)
    params = R.parametros(cfg)
    try:
        fonte = await abrir_fonte(db, cid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] desvio sem a InfoCap (%s): nada é reavaliado", type(exc).__name__)
        fonte = None
    if fonte is None:
        # J-B1 também aqui: sem a InfoCap o pedido não se monta — o item fica como está (a releitura do passo desvio
        # deriva o que o motor fizer com ele) e nada vira "falta um dado"
        resultado["sem_conexao"] = len(alvo)
        return resultado
    hora = params["janela"].get("desvio", "06:15")
    por_pessoa: Dict[Optional[str], Dict[str, int]] = {}
    for item in sorted(alvo, key=lambda x: (int(x.get("ramo_agger") or 999), str(x.get("fimvig")))):
        razao = "aguardando_agger" if item["estado"] == "aguardando_agger" else str(item.get("motivo") or "")
        novo = await _pedir(db, cid, item, d, cfg, params, fonte, por=por, forcar=MOTIVO_DO_DESVIO)
        if novo == "calculando":
            resultado["desviados"] += 1
            pessoa = item.get("responsavel_user_id") or item.get("dono_user_id")
            razoes = por_pessoa.setdefault(pessoa, {})
            razoes[razao] = razoes.get(razao, 0) + 1
        else:
            resultado["falharam"] += 1
    for pessoa, razoes in por_pessoa.items():
        n = sum(razoes.values())
        # o aviso diz o PORQUÊ verdadeiro de cada item: "não ficou livre" só quando a dona estava no próprio Agger
        porques = [(_frase_do_desvio(r, hora) + (f" ({q})" if len(razoes) > 1 else "")) for r, q in sorted(razoes.items())]
        texto = (f"{n} renovação(ões) {'sua(s) ' if pessoa else ''}foram calculadas no Agger da CORRETORA: "
                 + "; ".join(porques) + ".")
        R.registrar_aviso(db, cid, dia=d.isoformat(), assunto="desvio", texto=texto, user_id=pessoa,
                          severidade="medium", valores={"desviadas": n}, work_run_id=work_run_id,
                          fuso=fuso_da_corretora(db, cid), janela=params["janela"])
    return resultado


def _frase_do_desvio(razao: str, hora: Any) -> str:
    if razao in ("aguardando_agger", "agger_da_pessoa_em_uso"):
        return f"o Agger do dono não ficou livre até as {hora}"
    return R.frase_do_motivo(razao)


# ---------------------------------------------------------------------------------------------------------------------
# O PASSO 5 — avisar (06:45)
# ---------------------------------------------------------------------------------------------------------------------
def _texto(n: int, m: int, k: int, motivos: Mapping[str, int], *, seu: bool, antecipadas: int = 0,
           acima: int = 0, falhas: Optional[Mapping[str, int]] = None, proxima_noite: int = 0) -> str:
    texto = f"{n} prontas no {'seu ' if seu else ''}Agger · {m} pendentes"
    if m:
        texto += " (" + ", ".join(f"{R.frase_do_motivo(mo)}: {q}" for mo, q in sorted(motivos.items())) + ")"
    texto += f" · {k} falharam"
    if k and falhas:
        # conserto C1 (J-P7): o "K falharam" diz POR QUÊ, em frase de gente
        texto += " (" + ", ".join(f"{R.frase_do_motivo(mo)}: {q}" for mo, q in sorted(falhas.items())) + ")"
    if antecipadas:
        texto += f" · {antecipadas} antecipada(s) dos próximos dias"
    if acima:
        texto += f" · {acima} acima do limite da noite (saíram mesmo assim: o atraso é pior)"
    if proxima_noite:
        # SPEC-132: o relógio da madrugada acabou antes delas começarem — nunca caladas
        texto += f" · {proxima_noite} ficaram para a próxima noite (o horário acabou; entram primeiro)"
    return texto


TIPO_LICENCA = "licenca_agger"        # o evento que o motor grava no login (motor.TIPO_LICENCA, F3)
LICENCA_AVISO_DIAS = 7                # D-131-36: avisa ANTES de vencer


def _limite_da_licenca(motivo: Any) -> Optional[date]:
    """A data-limite que o motor escreveu no evento (`dataLimiteCalculo=AAAA-MM-DD`, e sem ela `licenca=`) — a mesma
    precedência de `motor.dias_para_o_limite`. Só datas: o evento nunca leva token nem corpo do login."""
    texto = str(motivo or "")
    for chave in ("dataLimiteCalculo", "licenca"):
        for parte in texto.split("·"):
            k, _, v = parte.strip().partition("=")
            if k.strip() == chave:
                d = R.data_de(v.strip())
                if d is not None:
                    return d
    return None


def licencas_do_agger(db: Any, company_id: str, hoje: date) -> Dict[str, int]:
    """D-131-36 — pelo ÚLTIMO evento `licenca_agger` de cada conta do Agger DESTA corretora (filtro `company_id`, §7):
    quantas vencem em ≤ 7 dias e quantas já venceram, e o menor prazo. Banco ilegível → nada (o aviso não cai)."""
    cid = R._uuid(company_id)
    try:
        linhas = (_cliente(db).table("multicalculo_eventos").select("company_id, tipo, chave, motivo, criado_em")
                  .eq("company_id", cid).eq("tipo", TIPO_LICENCA).order("criado_em", desc=True).limit(200)
                  .execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] eventos da licença ilegíveis (%s)", type(exc).__name__)
        return {"vencendo": 0, "vencidas": 0}
    ultimo: Dict[str, Tuple[str, Optional[date]]] = {}
    for e in linhas:
        if str(e.get("company_id")) != cid:
            continue
        partes = str(e.get("chave") or "").split("|")
        conta = partes[1] if len(partes) >= 3 else ""
        quando = str(e.get("criado_em") or "")
        if conta and (conta not in ultimo or quando > ultimo[conta][0]):
            ultimo[conta] = (quando, _limite_da_licenca(e.get("motivo")))
    prazos = [(lim - hoje).days for _q, lim in ultimo.values() if lim is not None]
    saida = {"vencendo": sum(1 for p in prazos if 0 < p <= LICENCA_AVISO_DIAS),
             "vencidas": sum(1 for p in prazos if p <= 0)}
    if prazos:
        saida["menor_prazo_dias"] = min(prazos)
    return saida


def _frase_da_licenca(lic: Mapping[str, int]) -> str:
    texto = ""
    if lic.get("vencidas"):
        texto += f" · 🔴 a licença do Agger venceu em {lic['vencidas']} conta(s): nenhum cálculo sai nela até renovar"
    if lic.get("vencendo"):
        texto += (f" · ⚠️ a licença do Agger vence em até {LICENCA_AVISO_DIAS} dias em {lic['vencendo']} conta(s) "
                  "(renove com o Agger antes)")
    return texto


def _da_noite(itens: List[Mapping[str, Any]], d: date) -> List[Mapping[str, Any]]:
    """O que o aviso conta: o que VENCE (calcular_em ≤ dia, fimvig ≥ dia) + o que foi ANTECIPADO esta noite (calcular_em
    futuro, mas já saiu ao Agger). Uma antecipável que ficou `pronta`/`pendente` é do dia dela, não de hoje."""
    hoje = d.isoformat()
    saida = []
    for x in itens:
        if x.get("estado") == "substituida" or str(x.get("fimvig")) < hoje:
            continue
        if str(x.get("calcular_em") or "") <= hoje or x.get("estado") in (R.ESTADOS_CALCULADOS + R.ESTADOS_EM_VOO
                                                                          + ("falhou",)):
            saida.append(x)
    return saida


def _calculadas_de_cotaveis(medida: Mapping[str, Any], do_dia: List[Mapping[str, Any]], hoje: str) -> Tuple[int, int]:
    """(calculadas, cotáveis) do DIA: os da conferência (as esperadas que vencem hoje) quando ela os gravou; sem eles
    (sem conferência, ou `sem_conexao`), a mesma conta sobre a lista do dia (calcular_em ≤ hoje)."""
    if medida.get("calculadas") is not None and medida.get("cotaveis") is not None:
        return int(medida["calculadas"]), int(medida["cotaveis"])
    vencem = [x for x in do_dia if str(x.get("calcular_em") or "") <= hoje]
    calculadas = sum(1 for x in vencem if x.get("estado") in R.ESTADOS_CALCULADOS)
    nao_cot = sum(1 for x in vencem if x.get("estado") == "pendente" and x.get("motivo") in R.MOTIVOS_NAO_COTAVEIS)
    return calculadas, len(vencem) - nao_cot


def avisar_dia(db: Any, company_id: str, dia: Any, *, work_run_id: Optional[str] = None) -> Dict[str, int]:
    """Por pessoa (o responsável: dono ou substituto) e à corretora: N prontas · M pendentes (porquê) · K falharam
    (+ antecipadas e acima do teto, D-131-33). Pelo briefing (o canal in-app que já existe), só no painel."""
    cid = R._uuid(company_id)
    d = _dia(dia)
    repo = R.RepositorioDeRenovacoes(db)
    params = R.parametros(carregar_config(db, cid))
    fuso = fuso_da_corretora(db, cid)
    hoje = d.isoformat()
    limite = (d + timedelta(days=int(params["antecipar_ate_dias"]))).isoformat()
    lidos = repo.listar(cid, calcular_ate=limite)
    do_dia = _da_noite(lidos, d)
    # SPEC-132: sem teto (o padrão) nada fica "acima do teto"; o que o relógio deixou para amanhã é contado à parte
    teto = params["teto_por_conta_noite"]
    proxima: Dict[Optional[str], int] = {}
    for x in lidos:
        if _ficou_de_ontem(x):
            dono = x.get("responsavel_user_id") or None
            proxima[dono] = proxima.get(dono, 0) + 1
    por_conta: Dict[str, int] = {}
    for x in do_dia:
        if str(x.get("calcular_em") or "") <= hoje and x.get("estado") in R.ESTADOS_CALCULADOS + R.ESTADOS_EM_VOO:
            por_conta[R.chave_da_conta(x)] = por_conta.get(R.chave_da_conta(x), 0) + 1
    grupos: Dict[Optional[str], List[Mapping[str, Any]]] = {}
    for x in do_dia:
        grupos.setdefault(x.get("responsavel_user_id") or None, []).append(x)
    avisos = 0
    total = {"n": 0, "m": 0, "k": 0, "antecipadas": 0,
             "acima_do_teto": 0 if teto is None else sum(max(0, v - teto) for v in por_conta.values()),
             "proxima_noite": sum(proxima.values())}
    for pessoa in proxima:
        grupos.setdefault(pessoa, [])      # quem só tem renovação para amanhã também recebe o aviso dela
    motivos_total: Dict[str, int] = {}
    falhas_total: Dict[str, int] = {}
    for pessoa, itens in grupos.items():
        n = sum(1 for x in itens if x["estado"] in R.ESTADOS_CALCULADOS)
        pend = [x for x in itens if x["estado"] == "pendente"]
        k = sum(1 for x in itens if x["estado"] == "falhou")
        ant = sum(1 for x in itens if str(x.get("calcular_em") or "") > hoje)
        acima = max(0, por_conta.get(str(pessoa), 0) - teto) if (pessoa and teto is not None) else 0
        prox = proxima.get(pessoa, 0)
        motivos: Dict[str, int] = {}
        for x in pend:
            motivos[str(x.get("motivo"))] = motivos.get(str(x.get("motivo")), 0) + 1
            motivos_total[str(x.get("motivo"))] = motivos_total.get(str(x.get("motivo")), 0) + 1
        falhas: Dict[str, int] = {}
        for x in itens:
            if x["estado"] == "falhou":
                falhas[str(x.get("motivo"))] = falhas.get(str(x.get("motivo")), 0) + 1
                falhas_total[str(x.get("motivo"))] = falhas_total.get(str(x.get("motivo")), 0) + 1
        total["n"] += n
        total["m"] += len(pend)
        total["k"] += k
        total["antecipadas"] += ant
        if pessoa is None:
            continue      # sem dono: entra no aviso da corretora (abaixo)
        R.registrar_aviso(db, cid, dia=hoje, assunto="avisar", user_id=pessoa,
                          texto=_texto(n, len(pend), k, motivos, seu=True, antecipadas=ant, acima=acima,
                                       falhas=falhas, proxima_noite=prox),
                          severidade="medium" if (pend or k or prox) else "info",
                          valores={"prontas": n, "pendentes": len(pend), "falharam": k, "antecipadas": ant,
                                   "acima_do_teto": acima, "ficaram_para_a_proxima_noite": prox},
                          work_run_id=work_run_id, fuso=fuso, janela=params["janela"])
        avisos += 1
    medida = repo.dia(cid, hoje) or {}
    texto = _texto(total["n"], total["m"], total["k"], motivos_total, seu=False, antecipadas=total["antecipadas"],
                   acima=total["acima_do_teto"], falhas=falhas_total, proxima_noite=total["proxima_noite"])
    estado_do_dia = str(medida.get("estado") or "")
    # 🔴 conserto C1 (J-P9 · RT-P2): a completude da SPEC conta `pendente` com motivo como feito — o número que diz se o
    # trabalho ACONTECEU é "calculadas de cotáveis", e ele vai SEMPRE no aviso (da conferência; sem ela, da lista do dia)
    calc_cot = _calculadas_de_cotaveis(medida, do_dia, hoje)
    if estado_do_dia == "vermelho":
        texto += f" · 🔴 a conferência achou {medida.get('faltaram') or 0} renovação(ões) que a lista do dia esqueceu"
    elif estado_do_dia == "sem_conexao":
        texto += f" · a conferência das {params['janela'].get('conferir', R.JANELA_PADRAO['conferir'])} não conseguiu ler a InfoCap"
    elif estado_do_dia and calc_cot[0] == 0 and calc_cot[1] >= 1:
        texto += " · nenhuma renovação cotável foi calculada hoje"     # nunca "100 %" num dia sem cálculo
    elif estado_do_dia:
        texto += f" · completude {medida.get('completude_pct')}%"
    texto += f" · {calc_cot[0]} calculada(s) de {calc_cot[1]} cotável(is)"
    lic = licencas_do_agger(db, cid, d)
    texto += _frase_da_licenca(lic)
    R.registrar_aviso(db, cid, dia=hoje, assunto="avisar", user_id=None, texto=texto,
                      severidade="high" if (estado_do_dia in ("vermelho", "sem_conexao") or lic.get("vencidas"))
                      else ("medium" if (total["m"] or total["k"] or total["proxima_noite"] or lic.get("vencendo"))
                            else "info"),
                      valores={"prontas": total["n"], "pendentes": total["m"], "falharam": total["k"],
                               "antecipadas": total["antecipadas"], "acima_do_teto": total["acima_do_teto"],
                               "ficaram_para_a_proxima_noite": total["proxima_noite"],
                               "calculadas": calc_cot[0], "cotaveis": calc_cot[1],
                               "licenca_vencendo": lic.get("vencendo", 0), "licenca_vencida": lic.get("vencidas", 0)},
                      work_run_id=work_run_id, fuso=fuso, janela=params["janela"])
    return {"avisos": avisos + 1, "n": total["n"], "m": total["m"], "k": total["k"]}


# ---------------------------------------------------------------------------------------------------------------------
# OS WORK RUNS — registrados no MESMO registro do Work OS (SPEC-055), carregados por `work.workflows.carregar_extras`
# ---------------------------------------------------------------------------------------------------------------------
#: SPEC-132 — o calcular (01:00) relê se a lista do dia terminou a cada isto
ESPERA_DA_LISTA_S = 120


def preparacao_em_curso(db: Any, company_id: str, dia: date) -> bool:
    """O run `renovacao.preparar` DESTE dia DESTA corretora (a chave do tick, `renov:preparar:<company>:<dia>`) existe e
    ainda não terminou. Sem run (o tick não o criou) ou banco ilegível → False: o calcular segue (o padrão de antes)."""
    from app.services.work.runs import ESTADOS_TERMINAIS

    chave = f"renov:preparar:{company_id}:{dia.isoformat()}"
    try:
        linhas = (_cliente(db).table("work_runs").select("id, company_id, status, idempotency_key")
                  .eq("company_id", str(company_id)).eq("idempotency_key", chave).limit(5).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOV] não li o run da lista (%s): o calcular segue", type(exc).__name__)
        return False
    return any(str(x.get("company_id")) == str(company_id) and str(x.get("status")) not in ESTADOS_TERMINAIS
               for x in linhas)


def _contexto(ctx: dict) -> Tuple[Any, str, date]:
    db = _cliente(ctx["db"])
    cid = R._uuid(ctx["company_id"])
    return db, cid, _dia((ctx.get("payload") or {}).get("dia"))


@registrar_workflow(WORKFLOW_DO_PASSO["preparar"], idade_maxima_s=IDADE_MAXIMA_S)
async def workflow_preparar(ctx: dict) -> str:
    db, cid, dia = _contexto(ctx)

    async def _preparar() -> Any:
        return await preparar_dia(db, cid, dia)

    r = await executar_passo(ctx, step_key="preparar", ordinal=1, nome="Montar a lista de renovações do dia",
                             step_type="analysis", fn=_preparar, guardar=("listadas", "prontas", "pendentes"))
    return (f"{(r or {}).get('prontas', 0)} pronta(s) e {(r or {}).get('pendentes', 0)} pendente(s) "
            f"({(r or {}).get('listadas', 0)} nova(s) na lista).")


@registrar_workflow(WORKFLOW_DO_PASSO["calcular"], idade_maxima_s=IDADE_MAXIMA_S)
async def workflow_calcular(ctx: dict) -> Any:
    from app.services.work.workflows import _runs_mod

    db, cid, dia = _contexto(ctx)

    async def _disparar() -> Any:
        # SPEC-132: o calcular começa às 01:00 — mas só DEPOIS da lista das 00:30 (a preparação e o disparo nunca
        # mexem no mesmo item ao mesmo tempo). Lista ainda em curso e antes da hora-limite → DORME 2 min (durável)
        agora = _agora()
        params = R.parametros(carregar_config(db, cid))
        hora_limite = ultimo_inicio(params["janela"], dia, fuso_da_corretora(db, cid))
        if agora < hora_limite and preparacao_em_curso(db, cid, dia):
            falta = (hora_limite - agora).total_seconds()
            return ctx["runs"].dormir(ctx["run_id"], lease_token=ctx.get("lease_token"),
                                      acordar_em_s=min(ESPERA_DA_LISTA_S, max(1.0, falta)),
                                      wait_for={"tipo": "renovacao_lista", "ref": f"lista:{dia.isoformat()}",
                                                "prazo_s": int(falta) + 900, "passo": "disparar"},
                                      company_id=cid)
        return await calcular_dia(db, cid, dia, agora=agora)

    r = await executar_passo(ctx, step_key="disparar", ordinal=1, nome="Pedir os cálculos no Agger",
                             step_type="portal", fn=_disparar, efeito="idempotente",
                             guardar=("disparados", "pendentes", "falharam", "vencidas", "antecipadas",
                                      "acima_do_teto", "ficaram_para_a_proxima_noite"))
    if isinstance(r, _runs_mod().Esperando):
        return r

    async def _acompanhar() -> Any:
        return await _acompanhar_ou_dormir(ctx, db, cid, dia, ate_passo="conferir", passo="calcular")

    a = await executar_passo(ctx, step_key="acompanhar", ordinal=2, nome="Acompanhar os cálculos",
                             step_type="analysis", fn=_acompanhar, guardar=("calculadas", "falharam", "em_voo"))
    if isinstance(a, _runs_mod().Esperando):
        return a
    return (f"{(r or {}).get('disparados', 0)} renovação(ões) pedidas; {(a or {}).get('calculadas', 0)} calculada(s), "
            f"{(a or {}).get('em_voo', 0)} ainda em curso.")


@registrar_workflow(WORKFLOW_DO_PASSO["conferir"], idade_maxima_s=IDADE_MAXIMA_S)
async def workflow_conferir(ctx: dict) -> str:
    from app.services.multicalculo import conferencia_da_renovacao as CONF

    db, cid, dia = _contexto(ctx)

    async def _conferir() -> Any:
        return await CONF.conferir_dia(db, cid, dia, work_run_id=ctx.get("run_id"))

    r = await executar_passo(ctx, step_key="conferir", ordinal=1, nome="Conferir contra a InfoCap",
                             step_type="analysis", fn=_conferir,
                             guardar=("estado", "esperadas", "faltaram"))
    return f"Conferência do dia: {(r or {}).get('estado')} · faltaram {(r or {}).get('faltaram')}."


@registrar_workflow(WORKFLOW_DO_PASSO["desvio"], idade_maxima_s=IDADE_MAXIMA_S)
async def workflow_desvio(ctx: dict) -> Any:
    from app.services.work.workflows import _runs_mod

    db, cid, dia = _contexto(ctx)

    async def _desviar() -> Any:
        return await desvio_dia(db, cid, dia, work_run_id=ctx.get("run_id"))

    r = await executar_passo(ctx, step_key="desviar", ordinal=1, nome="Levar ao Agger da corretora o que travou",
                             step_type="portal", fn=_desviar, efeito="idempotente", guardar=("desviados", "falharam"))

    async def _acompanhar() -> Any:
        return await _acompanhar_ou_dormir(ctx, db, cid, dia, ate_passo="avisar", passo="desvio")

    a = await executar_passo(ctx, step_key="acompanhar", ordinal=2, nome="Acompanhar os cálculos desviados",
                             step_type="analysis", fn=_acompanhar, guardar=("calculadas", "falharam", "em_voo"))
    if isinstance(a, _runs_mod().Esperando):
        return a
    return f"{(r or {}).get('desviados', 0)} renovação(ões) levadas ao Agger da corretora, com aviso."


@registrar_workflow(WORKFLOW_DO_PASSO["avisar"], idade_maxima_s=IDADE_MAXIMA_S)
async def workflow_avisar(ctx: dict) -> str:
    db, cid, dia = _contexto(ctx)

    async def _avisar() -> Any:
        return await asyncio.to_thread(avisar_dia, db, cid, dia, work_run_id=ctx.get("run_id"))

    r = await executar_passo(ctx, step_key="avisar", ordinal=1, nome="Avisar a equipe", step_type="notification",
                             fn=_avisar, efeito="idempotente", guardar=("avisos", "n", "m", "k"))
    return f"{(r or {}).get('avisos', 0)} aviso(s) no painel."
