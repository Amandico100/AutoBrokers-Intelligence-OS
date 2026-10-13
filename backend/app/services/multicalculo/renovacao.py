"""A RENOVAÇÃO de uma apólice — o repositório e a máquina de estados. SPEC-131-A (F1).

Uma linha de `renovacoes` por (corretora, sistema, codfil, nosnum, fimvig): a LISTA CONGELADA do dia. O estado de cada
item só muda por `RepositorioDeRenovacoes.transicionar`, que:

    · consulta `TRANSICOES` (o que pode virar o quê) — o resto é `TransicaoInvalida`
    · RECUSA estado reservado (`EstadoReservado`): a máquina inteira existe no CHECK do banco, mas NENHUM escritor desta
      SPEC grava `vista`, `em_negociacao`, … — a guarda é deste módulo, e não do banco (o banco aceita o estado, para o
      dia em que a 135/a emissão o ligarem)
    · exige motivo em `pendente`/`falhou` (o banco também: `ck_renovacoes_motivo`)
    · grava com CAS (`estado` e `versao` lidos) e escreve UMA linha em `renovacao_eventos` (de, para, por, motivo)

🔴 CLAUDE.md §7: o backend usa service role — TODA leitura e escrita aqui leva `company_id` no filtro. Um id de outra
corretora devolve "não existe", nunca a linha.
⛔ Nunca telefone; CPF/CNPJ só mascarado (no máximo os 2 últimos dígitos) + HMAC (o mesmo de `porta.cpf_hmac`, com
`MULTICALCULO_HMAC_KEY`); nome só o PRIMEIRO (exibição).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

TABELA = "renovacoes"
TABELA_EVENTOS = "renovacao_eventos"
TABELA_DIAS = "renovacao_dias"
TABELA_AUSENCIAS = "membro_ausencias"

SISTEMA_PADRAO = "infocap"

#: ligados na 131-A — os únicos que um escritor pode gravar
ESTADOS_LIGADOS: Tuple[str, ...] = ("listada", "pronta", "pendente", "calculando", "calculada", "falhou",
                                    "aguardando_agger", "apresentada", "enviada", "substituida")
#: reservados — existem no CHECK do banco (a máquina inteira, D-131-14) e NINGUÉM os grava nesta SPEC
ESTADOS_RESERVADOS: Tuple[str, ...] = ("vista", "em_negociacao", "recalculo", "aceita", "emissao_pendente", "emitida",
                                       "registrada", "recusada", "perdida")
ESTADOS_COM_MOTIVO: Tuple[str, ...] = ("pendente", "falhou", "perdida")

#: o que cada estado pode virar (a máquina). `substituida` é o fim (endosso que mudou o fimvig).
TRANSICOES: Dict[str, Tuple[str, ...]] = {
    "listada": ("pronta", "pendente", "substituida"),
    "pronta": ("pronta", "pendente", "calculando", "falhou", "substituida"),
    "pendente": ("pronta", "pendente", "substituida"),
    # confirmação N1: o cálculo pode revelar que o item não é cotável (a moto pela placa) → pendente(ramo_nao_cotado)
    "calculando": ("calculada", "falhou", "pendente", "aguardando_agger", "substituida"),
    "aguardando_agger": ("calculando", "calculada", "falhou", "pendente", "aguardando_agger", "substituida"),
    "falhou": ("calculando", "pronta", "pendente", "falhou", "substituida"),
    "calculada": ("apresentada", "substituida"),
    "apresentada": ("enviada", "substituida"),
    "enviada": ("substituida",),
    "substituida": (),
}

#: os estados em que o item ainda é "trabalho da preparação" (ela pode reavaliá-lo no dia seguinte)
ESTADOS_PREPARAVEIS: Tuple[str, ...] = ("listada", "pronta", "pendente", "falhou")
#: o que conta como FEITO na completude (o item saiu calculado — e o que veio depois dele)
ESTADOS_CALCULADOS: Tuple[str, ...] = ("calculada", "apresentada", "enviada")
#: o item em voo (o passo calcular ainda acompanha)
ESTADOS_EM_VOO: Tuple[str, ...] = ("calculando", "aguardando_agger")

#: os motivos de PENDÊNCIA (a renovação não vai ao Agger esta noite, e a corretora vê por quê)
MOTIVOS_DE_PENDENCIA: Tuple[str, ...] = ("ramo_nao_cotado", "ramo_desconhecido", "falta_dado", "sem_conexao", "sem_pdf",
                                         "sem_dono_e_sem_conta", "documento_invalido", "precisa_de_voce")
#: conserto C1 (J-B2/RT-P7): o `falhou` passageiro que já falhou em mais noites que isto vira `pendente(precisa_de_voce)`
VOLTAS_DO_FALHOU = 2
#: os motivos de pendência que tiram o item das COTÁVEIS (`calculadas ÷ cotáveis`)
MOTIVOS_NAO_COTAVEIS: Tuple[str, ...] = ("ramo_nao_cotado", "ramo_desconhecido")

FRASE_DO_MOTIVO: Dict[str, str] = {
    "ramo_nao_cotado": "ramo que o Agger não cota (renove manualmente)",
    "ramo_desconhecido": "ramo que o sistema não reconhece (renove manualmente)",
    "falta_dado": "falta um dado da apólice",
    "sem_conexao": "a InfoCap não respondeu",
    "sem_pdf": "sem o PDF da apólice",
    "sem_dono_e_sem_conta": "sem dono e sem Agger da corretora",
    "documento_invalido": "CPF/CNPJ inválido no cadastro",
    # o que um CÁLCULO deixa (o motor, F3) e a renovação mostra — costura F4 (D-131-36)
    "licenca_agger_vencida": "a licença do Agger venceu (renove com o Agger)",
    "conta_recusada": "o Agger recusou a conta",
    # conserto C1 (J-P7): todo motivo que chega a um aviso tem frase de gente — nunca o código com espaços
    "precisa_de_voce": f"falhou em mais de {VOLTAS_DO_FALHOU} noites: o robô parou de tentar, precisa de você",
    "calculo_fechado": "nenhuma seguradora devolveu oferta (confira o pedido no Agger)",
    "calculo_falhou": "o robô não conseguiu calcular no Agger",
    "calculo_incerto": "o Agger não confirmou se o cálculo saiu (confira no Agger)",
    "calculo_cancelado": "o cálculo foi cancelado no Agger",
    "calculo_expirado": "o cálculo esperou demais na fila do Agger do dono",
    "agger_da_pessoa_em_uso": "o dono estava usando o próprio Agger",
    "agger_da_pessoa_sem_resposta": "o login no Agger do dono não chegou ao fim",
    "agger_da_pessoa_indisponivel": "o Agger do dono está pausado ou bloqueado",
    "porta_recusou": "a configuração do multicálculo recusou o pedido (confira a configuração)",
    "desvio_indisponivel": "o Agger da corretora não pôde receber o desvio",
    "erro_inesperado": "erro inesperado do sistema",
    # confirmação N1: os motivos de veículo que o robô escreve com o código na frente
    "veiculo_moto": "a placa é de uma moto: o aplicativo ainda não cota moto (renove manualmente)",
    "veiculo_sem_combustivel": "o combustível do veículo não veio da InfoCap nem da FIPE (complete no Agger)",
}

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MOTIVO = re.compile(r"^[a-z0-9_]{1,80}$")
#: os campos que uma transição pode mudar JUNTO com o estado (nunca o estado, nunca a chave, nunca a corretora)
CAMPOS_DA_TRANSICAO = frozenset({"pedido_id", "conta_agger_id", "conta_motivo", "dono_user_id", "dono_motivo",
                                 "responsavel_user_id", "ramo_agger", "calcular_em", "proposta_ref"})


class EstadoReservado(ValueError):
    """Um escritor tentou gravar um estado reservado (vista, em_negociacao, …). Nenhum caminho desta SPEC o faz."""


class TransicaoInvalida(ValueError):
    """`de → para` fora da máquina (`TRANSICOES`)."""


class MotivoObrigatorio(ValueError):
    """`pendente`/`falhou` sem motivo — o banco também recusa (`ck_renovacoes_motivo`)."""


class ConcorrenciaPerdida(RuntimeError):
    """O CAS não pegou: outro processo mudou o item entre a leitura e a escrita."""


class NaoEncontrada(LookupError):
    """A renovação não existe PARA ESTA corretora (não diz se existe noutra)."""


# ---------------------------------------------------------------------------------------------------------------------
# As peças pequenas (puras)
# ---------------------------------------------------------------------------------------------------------------------
def _uuid(valor: Any, nome: str = "company_id") -> str:
    texto = str(valor or "").strip()
    if not _UUID.match(texto):
        raise ValueError(f"{nome} precisa ser um uuid")
    return texto.lower()


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dados(resp: Any) -> List[Dict[str, Any]]:
    dados = getattr(resp, "data", None) if resp is not None else None
    if isinstance(dados, list):
        return [dict(x) for x in dados]
    return [dict(dados)] if isinstance(dados, dict) else []


def _comparavel(dados: Any) -> Any:
    """Os `dados` de um evento na forma que o jsonb devolve (tupla → lista, data → texto, chaves ordenadas): o que a
    máquina vai gravar e o que ela gravou se comparam pelo CONTEÚDO. Vazio e ausente são o mesmo (o evento grava {})."""
    import json

    if not dados:
        return {}
    return json.loads(json.dumps(dados, default=str, sort_keys=True))


def guardar_estado(estado: str) -> str:
    """A GUARDA de todo escritor: estado reservado → `EstadoReservado`; desconhecido → `TransicaoInvalida`."""
    if estado in ESTADOS_RESERVADOS:
        raise EstadoReservado(f"o estado '{estado}' é reservado: nenhum escritor desta versão o grava")
    if estado not in ESTADOS_LIGADOS:
        raise TransicaoInvalida(f"estado desconhecido: {estado!r}")
    return estado


def data_de(valor: Any) -> Optional[date]:
    """`DD/MM/AAAA` (a forma de `/renovacoes`), `AAAA-MM-DD` ou um `date`. Fora disso → None."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()[:10]
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def codfil_de(valor: Any) -> int:
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return 1
    return n if n >= 1 else 1


def nosnum_de(valor: Any) -> str:
    texto = str(valor if valor is not None else "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def mascarar_documento(documento: Any) -> Optional[str]:
    """CPF → `***.***.***-NN`, CNPJ → `**.***.***/****-NN`: só os 2 últimos dígitos (o banco confere: ≤ 2 dígitos)."""
    digitos = re.sub(r"\D", "", str(documento or ""))
    if not digitos:
        return None
    fim = digitos[-2:]
    if len(digitos) > 11:
        return f"**.***.***/****-{fim}"
    return f"***.***.***-{fim}"


def hmac_do_documento(documento: Any, *, chave: Optional[str] = None) -> Optional[str]:
    """O MESMO HMAC da porta (`porta.cpf_hmac`, `MULTICALCULO_HMAC_KEY`). Sem documento → None; sem a chave → levanta
    (`porta.ChaveAusente`: fail-closed, nunca hash sem sal)."""
    if not re.sub(r"\D", "", str(documento or "")):
        return None
    from app.services.multicalculo.porta import cpf_hmac

    return cpf_hmac(str(documento), chave=chave)


def primeiro_nome(nome: Any) -> Optional[str]:
    """Só o primeiro nome, para EXIBIÇÃO ("Maria", nunca o nome inteiro). Sem letras → None."""
    for parte in str(nome or "").split():
        limpo = "".join(ch for ch in parte if ch.isalpha() or ch in "'-")
        if limpo and any(ch.isalpha() for ch in limpo):
            return limpo[:1].upper() + limpo[1:].lower()[:39]
    return None


def motivo_valido(motivo: Any) -> bool:
    return bool(motivo) and bool(_MOTIVO.match(str(motivo)))


def frase_do_motivo(motivo: Any) -> str:
    m = str(motivo or "")
    return FRASE_DO_MOTIVO.get(m, m.replace("_", " "))


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def chave_do_item(item: Mapping[str, Any]) -> Tuple[str, int, str, str]:
    """(sistema, codfil, nosnum, fimvig-ISO) — a UNIQUE da tabela, sem a corretora."""
    fim = data_de(item.get("fimvig"))
    return (str(item.get("sistema") or SISTEMA_PADRAO), codfil_de(item.get("codfil")), nosnum_de(item.get("nosnum")),
            fim.isoformat() if fim else "")


def linha_da_infocap(cru: Mapping[str, Any], *, sistema: str = SISTEMA_PADRAO,
                     hmac_chave: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Uma linha de `/renovacoes` → os campos do item (SEM a corretora e SEM estado). Fora do formato → None.
    Só apólice (`tipdoc == "A"`), nunca cancelada — a mesma regra de `carteira_a_vencer` e de `dono.medir_regra`."""
    if str(cru.get("tipdoc") or "A").strip().upper() != "A":
        return None
    if str(cru.get("cancelado") or "").strip().upper() in ("T", "S", "TRUE", "1"):
        return None
    nosnum = nosnum_de(cru.get("nosnum"))
    fim = data_de(cru.get("fimvig"))
    if not nosnum or fim is None:
        return None
    premio = cru.get("pretot")
    try:
        premio_num = round(float(premio), 2) if premio not in (None, "") else None
    except (TypeError, ValueError):
        premio_num = None
    documento = cru.get("cic") if cru.get("cic") is not None else cru.get("cpf_cnpj")
    return {
        "sistema": sistema, "codfil": codfil_de(cru.get("codfil")), "nosnum": nosnum, "fimvig": fim.isoformat(),
        "ramo_sigla": (str(cru.get("ramo") or "").strip().upper() or None),
        "seguradora_atual": (str(cru.get("seguradora") or "").strip() or None),
        "premio_atual": premio_num if (premio_num or 0) > 0 else None,
        "cliente_nome_curto": primeiro_nome(cru.get("cliente")),
        "documento_mascarado": mascarar_documento(documento),
        "documento_hmac": hmac_do_documento(documento, chave=hmac_chave),
    }


# ---------------------------------------------------------------------------------------------------------------------
# O repositório — company_id em TODO filtro (CLAUDE.md §7)
# ---------------------------------------------------------------------------------------------------------------------
class RepositorioDeRenovacoes:
    def __init__(self, db: Any, *, agora: Any = None):
        self.db = getattr(db, "client", db)
        self._agora = agora or _agora_iso

    def _t(self, tabela: str) -> Any:
        return self.db.table(tabela)

    # ------------------------------------------------------------------ leituras
    def por_id(self, company_id: str, renovacao_id: str) -> Dict[str, Any]:
        cid = _uuid(company_id)
        rid = _uuid(renovacao_id, "renovacao_id")
        linhas = _dados(self._t(TABELA).select("*").eq("id", rid).eq("company_id", cid).limit(1).execute())
        linha = next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)
        if linha is None:
            raise NaoEncontrada("renovação inexistente nesta corretora")
        return linha

    def por_chave(self, company_id: str, chave: Tuple[str, int, str, str]) -> Optional[Dict[str, Any]]:
        cid = _uuid(company_id)
        sistema, codfil, nosnum, fimvig = chave
        linhas = _dados(self._t(TABELA).select("*").eq("company_id", cid).eq("sistema", sistema)
                        .eq("codfil", codfil).eq("nosnum", nosnum).eq("fimvig", fimvig).limit(1).execute())
        return next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)

    def listar(self, company_id: str, *, estados: Optional[Iterable[str]] = None,
               calcular_ate: Optional[str] = None, limite: int = 5000) -> List[Dict[str, Any]]:
        cid = _uuid(company_id)
        q = self._t(TABELA).select("*").eq("company_id", cid)
        if estados is not None:
            q = q.in_("estado", list(estados))
        if calcular_ate is not None:
            q = q.lte("calcular_em", calcular_ate)
        linhas = _dados(q.limit(limite).execute())
        # 🔴 a segunda trava: mesmo que o filtro do banco falhasse, nada de outra corretora sai daqui
        return [x for x in linhas if str(x.get("company_id", "")).lower() == cid]

    def eventos(self, company_id: str, renovacao_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cid = _uuid(company_id)
        q = self._t(TABELA_EVENTOS).select("*").eq("company_id", cid)
        if renovacao_id is not None:
            q = q.eq("renovacao_id", _uuid(renovacao_id, "renovacao_id"))
        return [x for x in _dados(q.order("criado_em").limit(5000).execute())
                if str(x.get("company_id", "")).lower() == cid]

    def dia(self, company_id: str, dia: str) -> Optional[Dict[str, Any]]:
        cid = _uuid(company_id)
        linhas = _dados(self._t(TABELA_DIAS).select("*").eq("company_id", cid).eq("dia", dia).limit(1).execute())
        return next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)

    def substituto_de(self, company_id: str, user_id: Optional[str], dia: str) -> Optional[str]:
        """O substituto de `user_id` com ausência ATIVA no `dia` (D-131-08) — ou None."""
        if not user_id:
            return None
        cid = _uuid(company_id)
        try:
            linhas = _dados(self._t(TABELA_AUSENCIAS).select("user_id, substituto_user_id, de, ate, company_id")
                            .eq("company_id", cid).eq("user_id", _uuid(user_id, "user_id"))
                            .lte("de", dia).gte("ate", dia).limit(5).execute())
        except Exception as exc:  # noqa: BLE001
            logger.warning("[RENOV] ausências ilegíveis: %s", type(exc).__name__)
            return None
        linha = next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)
        return str(linha["substituto_user_id"]) if linha and linha.get("substituto_user_id") else None

    # ------------------------------------------------------------------ escritas
    def _evento(self, cid: str, rid: str, de: Optional[str], para: str, por: str, motivo: Optional[str],
                dados: Optional[Mapping[str, Any]] = None) -> None:
        self._t(TABELA_EVENTOS).insert({
            "company_id": cid, "renovacao_id": rid, "de": de, "para": para, "por": str(por)[:80],
            "motivo": motivo, "dados": dict(dados or {}), "criado_em": self._agora(),
        }).execute()

    def _dados_do_ultimo_evento(self, cid: str, rid: str) -> Any:
        """Os `dados` do evento mais recente do item (o que a máquina disse por último) — None se não houver. Pela
        lista em ordem crescente (`eventos`): no empate de `criado_em` (o relógio injetado), o último gravado é o último."""
        linhas = self.eventos(cid, rid)
        return linhas[-1].get("dados") if linhas else None

    def upsert_da_lista(self, company_id: str, campos: Mapping[str, Any], *, por: str,
                        canario: bool = False, motivo_do_evento: Optional[str] = None) -> Tuple[Dict[str, Any], bool]:
        """O item da lista congelada pela UNIQUE (company_id, sistema, codfil, nosnum, fimvig) — NUNCA duplica.

        Já existe → atualiza só o descritivo (prêmio, seguradora, ramo, nome curto, documento) e devolve `(linha, False)`.
        Não existe → nasce `listada` (evento `de=None → listada`) e devolve `(linha, True)`. Se a MESMA apólice
        (codfil, nosnum) tem um item ainda vivo com OUTRO fimvig (o endosso mudou o vencimento), o velho vira
        `substituida` pela máquina."""
        cid = _uuid(company_id)
        chave = chave_do_item(campos)
        if not chave[2] or not chave[3]:
            raise ValueError("item sem nosnum ou sem fimvig")
        descritivo = {k: campos.get(k) for k in ("ramo_sigla", "seguradora_atual", "premio_atual", "cliente_nome_curto",
                                                 "documento_mascarado", "documento_hmac") if k in campos}
        existente = self.por_chave(cid, chave)
        if existente is not None:
            mudou = {k: v for k, v in descritivo.items() if v is not None and existente.get(k) != v}
            if mudou:
                mudou["atualizado_em"] = self._agora()
                linhas = _dados(self._t(TABELA).update(mudou).eq("id", existente["id"]).eq("company_id", cid)
                                .execute())
                existente = next(iter(linhas), {**existente, **mudou})
            return existente, False

        nova = {"company_id": cid, "sistema": chave[0], "codfil": chave[1], "nosnum": chave[2], "fimvig": chave[3],
                "estado": "listada", "canario": bool(canario), "criado_em": self._agora(),
                "atualizado_em": self._agora(), "versao": 1, **descritivo}
        try:
            linha = next(iter(_dados(self._t(TABELA).insert(nova).execute())), None)
        except Exception as exc:  # noqa: BLE001
            # outro processo inseriu o mesmo item entre a leitura e a escrita: a UNIQUE decidiu — o dele vale
            ja = self.por_chave(cid, chave)
            if ja is not None:
                return ja, False
            raise exc
        if linha is None:
            linha = self.por_chave(cid, chave) or nova
        self._evento(cid, str(linha["id"]), None, "listada", por, motivo_do_evento)
        self._substituir_os_antigos(cid, linha, por)
        return linha, True

    def _substituir_os_antigos(self, cid: str, nova: Mapping[str, Any], por: str) -> int:
        """Endosso que muda o fimvig: o item ANTIGO da mesma apólice, ainda vivo, vira `substituida`."""
        linhas = _dados(self._t(TABELA).select("*").eq("company_id", cid).eq("sistema", nova["sistema"])
                        .eq("codfil", nova["codfil"]).eq("nosnum", nova["nosnum"]).limit(50).execute())
        trocados = 0
        for velha in linhas:
            if str(velha.get("company_id", "")).lower() != cid or velha.get("id") == nova.get("id"):
                continue
            if str(velha.get("fimvig")) == str(nova.get("fimvig")) or velha.get("estado") == "substituida":
                continue
            if "substituida" not in TRANSICOES.get(str(velha.get("estado")), ()):
                continue
            try:
                self.transicionar(cid, str(velha["id"]), "substituida", por=por, motivo="endosso_mudou_o_fimvig",
                                  dados={"substituida_por": str(nova.get("id"))})
                trocados += 1
            except (ConcorrenciaPerdida, TransicaoInvalida) as exc:
                logger.warning("[RENOV] não substituí o item antigo: %s", type(exc).__name__)
        return trocados

    def transicionar(self, company_id: str, renovacao_id: str, para: str, *, por: str,
                     motivo: Optional[str] = None, dados: Optional[Mapping[str, Any]] = None,
                     campos: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """A ÚNICA porta do estado. `de == para` com o mesmo motivo, nenhum campo novo e os MESMOS `dados` do último
        evento = nada (idempotente). SPEC-131-A F6: os `dados` mudaram (o "faltando" de um pendente que mudou, o que
        passou a ser suposto) → o estado fica, a versão sobe e o evento NOVO guarda o porquê de agora — o evento velho
        nunca fica como explicação de um item cujo motivo mudou por dentro. `dados=None` = quem chama não diz nada."""
        guardar_estado(para)
        cid = _uuid(company_id)
        if para in ESTADOS_COM_MOTIVO and not motivo_valido(motivo):
            raise MotivoObrigatorio(f"'{para}' exige motivo (código curto: letras minúsculas, dígitos e _)")
        if motivo is not None and not motivo_valido(motivo):
            raise ValueError("motivo é um código curto (letras minúsculas, dígitos e _)")
        extra = dict(campos or {})
        proibidos = set(extra) - CAMPOS_DA_TRANSICAO
        if proibidos:
            raise ValueError("campos que a transição não muda: " + ", ".join(sorted(proibidos)))
        atual = self.por_id(cid, renovacao_id)
        de = str(atual.get("estado") or "")
        if para not in TRANSICOES.get(de, ()):
            raise TransicaoInvalida(f"{de} → {para} não está na máquina")
        motivo_final = motivo if para in ESTADOS_COM_MOTIVO else None
        novos = {k: v for k, v in extra.items() if atual.get(k) != v}
        if de == para and (atual.get("motivo") or None) == motivo_final and not novos:
            if dados is None or _comparavel(dados) == _comparavel(self._dados_do_ultimo_evento(cid, str(atual["id"]))):
                return atual
        versao = int(atual.get("versao") or 1)
        patch = {"estado": para, "motivo": motivo_final, "versao": versao + 1, "atualizado_em": self._agora(), **novos}
        linhas = _dados(self._t(TABELA).update(patch).eq("id", atual["id"]).eq("company_id", cid)
                        .eq("estado", de).eq("versao", versao).execute())
        linha = next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)
        if linha is None:
            raise ConcorrenciaPerdida(f"a renovação mudou durante a transição {de} → {para}")
        self._evento(cid, str(atual["id"]), de, para, por, motivo if motivo is not None else None, dados)
        return linha

    def gravar_dia(self, company_id: str, dia: str, campos: Mapping[str, Any]) -> Dict[str, Any]:
        """A medida do dia (só a conferência chama). Upsert pela PK (company_id, dia)."""
        cid = _uuid(company_id)
        linha = {"company_id": cid, "dia": dia, **dict(campos), "atualizado_em": self._agora()}
        existente = self.dia(cid, dia)
        if existente is None:
            try:
                return next(iter(_dados(self._t(TABELA_DIAS).insert(linha).execute())), linha)
            except Exception:  # noqa: BLE001 — corrida pela PK: a outra gravou; esta atualiza
                pass
        atualizacao = {k: v for k, v in linha.items() if k not in ("company_id", "dia")}
        return next(iter(_dados(self._t(TABELA_DIAS).update(atualizacao).eq("company_id", cid).eq("dia", dia)
                                .execute())), linha)


def contar(itens: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    """Quantos itens em cada estado (puro — para o aviso e para a conferência)."""
    saida: Dict[str, int] = {}
    for x in itens:
        e = str(x.get("estado") or "")
        saida[e] = saida.get(e, 0) + 1
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# Os parâmetros do serviço (as chaves de `config.py`, F2) — lidos aqui para a madrugada E para a conferência
# ---------------------------------------------------------------------------------------------------------------------
ANTECEDENCIA_PADRAO = 10          # D-131-01 (era 15)
MARGEM_DE_LEITURA_DIAS = 3        # 💭 SPEC §4: a lista lê +3 dias além da antecedência
#: D-131-33 (o pico: 📊 um dia de 42 renovações de UM dono na corretora maior — 11× a média, BLOCO 0): o calcular
#: aplica um TETO por conta do Agger por noite e ANTECIPA o que vence nos próximos dias para preencher a sobra
TETO_POR_CONTA_NOITE_PADRAO = 12
ANTECIPAR_ATE_DIAS_PADRAO = 7
OPCOES_PADRAO: Tuple[str, ...] = ("anterior", "franquia_reduzida", "completa_mais")
OPCOES_PROIBIDAS: Tuple[str, ...] = ("economica", "minima")    # ⛔ nunca na renovação (mutação 7)
JANELA_PADRAO: Dict[str, Any] = {"preparar": "00:30", "calcular": "02:00", "conferir": "05:30", "desvio": "06:15",
                                 "avisar": "06:45", "prosseguir_de": "01:00", "prosseguir_ate": "06:30",
                                 "retentativa_min": 60}
FUSO_PADRAO = "America/Sao_Paulo"


def _inteiro(bloco: Mapping[str, Any], chave: str, padrao: int, minimo: int, maximo: int) -> int:
    valor = bloco.get(chave, padrao)
    if isinstance(valor, bool):
        return padrao
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return padrao
    return n if minimo <= n <= maximo else padrao


def parametros(cfg: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """`servicos.renovacao.{antecedencia_dias, janela, opcoes, teto_por_conta_noite, antecipar_ate_dias}` da config
    EFETIVA (`config.carregar(servico='renovacao')`, F2), com o padrão da SPEC quando a chave falta ou sai da faixa."""
    bloco: Mapping[str, Any] = {}
    if isinstance(cfg, Mapping):
        servicos = cfg.get("servicos")
        if isinstance(servicos, Mapping) and isinstance(servicos.get("renovacao"), Mapping):
            bloco = servicos["renovacao"]
    janela = dict(JANELA_PADRAO)
    if isinstance(bloco.get("janela"), Mapping):
        for k, v in bloco["janela"].items():
            if k in janela:
                janela[k] = v
    bruto = bloco.get("opcoes")
    lista = bruto if isinstance(bruto, (list, tuple)) and bruto else OPCOES_PADRAO
    opcoes: List[str] = []
    for o in lista:
        o = str(o)
        if o not in OPCOES_PROIBIDAS and o not in opcoes:   # ⛔ econômica/mínima nunca entram (SPEC §4)
            opcoes.append(o)
    opcoes = opcoes[:3] or list(OPCOES_PADRAO)
    return {"antecedencia_dias": _inteiro(bloco, "antecedencia_dias", ANTECEDENCIA_PADRAO, 1, 60),
            "janela": janela, "opcoes": opcoes, "margem_dias": MARGEM_DE_LEITURA_DIAS,
            "teto_por_conta_noite": _inteiro(bloco, "teto_por_conta_noite", TETO_POR_CONTA_NOITE_PADRAO, 1, 500),
            "antecipar_ate_dias": _inteiro(bloco, "antecipar_ate_dias", ANTECIPAR_ATE_DIAS_PADRAO, 0, 30)}


def chave_da_conta(item: Mapping[str, Any]) -> str:
    """A chave do TETO por conta (D-131-33). A conta de verdade é a que o `qual_agger` decidir no disparo; ANTES dele,
    a aproximação é o DONO (o Agger dele é o padrão da renovação) — sem dono, o Agger da corretora. ⚠️ Aproximação
    documentada: o item cujo dono não tem Agger cai na conta da corretora na hora e conta aqui no teto do dono."""
    return str(item.get("conta_agger_id") or item.get("dono_user_id") or "corretora")


# ---------------------------------------------------------------------------------------------------------------------
# O AVISO in-app — pelo canal que JÁ existe: o BRIEFING (`briefing_service.publicar` → `briefing_publications` +
# `briefing_items` → `DeliveryExecutor._dashboard`: "está no painel, em Entregas"). 📊 BLOCO 0 A8 (12/10): não há tabela
# de notificação por pessoa (só `admin_inbox_states`, a caixa da PLATAFORMA). ⛔ Nunca publisher novo; o perfil de
# entrega passado é SÓ `dashboard` — nada sai por e-mail/WhatsApp, nada vai ao cliente.
# ---------------------------------------------------------------------------------------------------------------------
#: o instante de cada assunto na janela (o período da publicação: um por assunto por dia — o índice idempotente
#: `ux_briefing_publications_idempotente` não deixa duplicar)
PASSO_DO_ASSUNTO: Dict[str, str] = {"conferencia": "conferir", "desvio": "desvio", "avisar": "avisar"}
SECAO_DO_AVISO = "renovacao"


def _instante(dia: str, hhmm: Any, fuso: str) -> str:
    from zoneinfo import ZoneInfo

    d = data_de(dia) or date.today()
    try:
        h, m = (int(x) for x in str(hhmm).split(":")[:2])
    except Exception:  # noqa: BLE001
        h, m = 6, 45
    return datetime(d.year, d.month, d.day, h, m, tzinfo=ZoneInfo(fuso or FUSO_PADRAO)).isoformat()


def assunto_da_publicacao(publicacao: Mapping[str, Any]) -> Optional[str]:
    """O assunto de um aviso da renovação (o teste e a 131-B leem por aqui)."""
    payload = publicacao.get("payload") if isinstance(publicacao, Mapping) else None
    for secao in (payload or {}).get("sections") or []:
        if secao.get("key") == SECAO_DO_AVISO:
            for item in secao.get("items") or []:
                return (item.get("action_payload") or {}).get("assunto")
    return None


def registrar_aviso(db: Any, company_id: str, *, dia: str, assunto: str, texto: str, user_id: Optional[str] = None,
                    severidade: str = "info", valores: Optional[Mapping[str, Any]] = None,
                    work_run_id: Optional[str] = None, fuso: str = FUSO_PADRAO,
                    janela: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """UMA publicação por (corretora, dia, assunto, pessoa). `user_id=None` = a da CORRETORA (o admin a vê no painel);
    com `user_id` = a da pessoa (a publicação já guarda a pessoa; a tela que filtra por pessoa é da 131-B). O texto leva
    só CONTAGENS e motivos — nunca nome, documento ou apólice."""
    from app.services.intelligence.briefing_service import BriefingService, BriefingSpec, ItemDeBriefing

    cid = _uuid(company_id)
    pessoa = _uuid(user_id, "user_id") if user_id else None
    passo = PASSO_DO_ASSUNTO.get(assunto, "avisar")
    hhmm = (janela or JANELA_PADRAO).get(passo) or JANELA_PADRAO[passo]
    instante = _instante(dia, hhmm, fuso)
    alerta = severidade in ("high", "critical")
    limpos = {k: v for k, v in dict(valores or {}).items() if isinstance(v, (int, float, str, bool)) or v is None}
    d = data_de(dia)
    spec = BriefingSpec(
        briefing_type="critical_alert" if (alerta and assunto == "conferencia") else "on_demand",
        company_id=cid, period_start=instante, period_end=instante,
        headline=f"Renovações de {d.strftime('%d/%m') if d else dia}",
        executive_summary=texto[:1200],
        secoes=[(SECAO_DO_AVISO, "Renovações")],
        itens=[ItemDeBriefing(item_type="result", section=SECAO_DO_AVISO, headline=texto[:200], summary=texto[:1200],
                              confidence=1.0, priority_score=90.0 if alerta else 50.0, work_run_id=work_run_id,
                              action_payload={"dia": dia, "assunto": assunto, "severidade": severidade, **limpos})],
        methodology="contagem dos itens de renovação da corretora (a lista do dia e a conferência na InfoCap)",
        sources_summary=["renovacoes", "renovacao_dias"],
        user_id=pessoa, profile_id=None,
    )
    try:
        r = BriefingService(db).publicar(spec, perfil={"channels": ["dashboard"], "timezone": fuso},
                                         work_run_id=work_run_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[RENOV] aviso não publicado (%s): %s", assunto, type(exc).__name__)
        return None
    if not (r or {}).get("ok"):
        logger.error("[RENOV] aviso não publicado (%s): %s", assunto, (r or {}).get("erro"))
        return None
    return r.get("publication")


def fuso_da_corretora(db: Any, company_id: str) -> str:
    """O fuso que a corretora já declarou (o perfil do briefing, `briefing_profiles.timezone`); sem ele, São Paulo."""
    cid = _uuid(company_id)
    try:
        linhas = _dados(getattr(db, "client", db).table("briefing_profiles").select("timezone, company_id")
                        .eq("company_id", cid).limit(5).execute())
        linha = next((x for x in linhas if str(x.get("company_id", "")).lower() == cid and x.get("timezone")), None)
        if linha:
            return str(linha["timezone"])
    except Exception:  # noqa: BLE001
        pass
    return FUSO_PADRAO
