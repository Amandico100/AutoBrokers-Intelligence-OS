# -*- coding: utf-8 -*-
"""A conta do ROBÔ do multicálculo — o SERVIÇO único que grava, pausa, religa e desconecta (SPEC-133-A.1 F3).

Dois portões chamam este módulo, e só ele escreve a conta do robô em `portal_accounts`:

    o comando do Founder   `comando_robo` (cadastrar · pausar · religar · trocar-senha · apagar-senha)
    a TELA de conexões      `app/api/portal.py` → "Agger da corretora" (D-133A1-03/04)

🔴 Por que UM serviço e não duas cópias: a tela e o comando gravam a MESMA linha (rótulo, estado, janela, senha no
cofre). Duas cópias da regra divergem no primeiro conserto — e aqui a divergência é um robô que nunca trabalha
(janela ilegível) ou que trabalha com o login de uma pessoa (`teste` virando `ativo`).

Mora no pacote do worker porque a imagem do `portal-worker` copia SÓ `backend/portal_worker` (o comando roda onde o
robô roda). O smith-api tem o backend inteiro e importa daqui (como já importa `portal_worker.journeys`). Este módulo
NUNCA importa `app.*` e NUNCA cifra sozinho: quem chama passa `cifrar` (o cofre do lado dele — a MESMA chave).

⛔ Nada aqui devolve, registra ou levanta exceção com a senha, o segredo cifrado ou o usuário inteiro.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from . import robos

PORTAL_KEY = robos.PORTAL_KEY

#: D-133A1-04 — a conta GLOBAL do Agger da corretora (o Quem Cobra Menos e quem não tem Agger próprio). É a ÚNICA
#: conta de robô que a tela enxerga e grava: o rótulo é a identidade dela. As outras (o rodízio `robo-2`, o canário
#: com login de pessoa) continuam só do comando — e os Aggers dos comerciais são da SPEC-131-0.
ROTULO_DA_CORRETORA = "agger-da-corretora"
NOME_DA_CORRETORA = "Agger da corretora"

#: 💭 a janela padrão da conta que nasce pela tela: segunda a sábado, 07:00–22:00 (Brasília). Editável na tela.
#: Sem janela (`None` = sempre) a conta trabalharia de madrugada e no domingo — quando ninguém da corretora vê um
#: bloqueio de senha. O teto por hora fica NULO: vale `robos.TETO_PADRAO_POR_HORA`.
JANELA_PADRAO: Dict[str, str] = {"dias": "seg-sab", "inicio": "07:00", "fim": "22:00"}
DIAS_DA_TELA = ("seg-sex", "seg-sab", "seg-dom")


class Recusa(Exception):
    """O serviço recusou — a mensagem é para quem pediu (sem dado sensível)."""


def mascarar(valor: str) -> str:
    """A MESMA regra de `app.services.portal_vault.mask`. O pacote do worker nunca importa `app.*`:
    `test_spec129b_o_fio` confere que as duas dizem o mesmo."""
    v = str(valor or "")
    if not v:
        return ""
    if len(v) <= 3:
        return v[0] + "••"
    return v[:2] + "•" * max(3, len(v) - 4) + v[-2:]


def _dados(r: Any) -> List[Dict[str, Any]]:
    return list(getattr(r, "data", None) or [])


# ======================================================================================================================
# A janela
# ======================================================================================================================
def janela_valida(janela: Any) -> Dict[str, str]:
    """`{"dias", "inicio", "fim"}` legível pelo motor (`robos.dentro_da_janela`) — ou `Recusa`. A regra do motor é
    "janela ilegível = fora", e uma conta que nunca trabalha gravada em silêncio é pior que a recusa."""
    if not isinstance(janela, dict):
        raise Recusa('janela ilegível — use o formato "seg-sex,07:00-20:00"')
    j = {"dias": str(janela.get("dias") or "").strip(), "inicio": str(janela.get("inicio") or "").strip(),
         "fim": str(janela.get("fim") or "").strip()}
    if not j["dias"] or robos._dias(j["dias"]) is None or robos._minutos(j["inicio"]) is None \
            or robos._minutos(j["fim"]) is None or j["inicio"] == j["fim"]:
        raise Recusa('janela ilegível — use o formato "seg-sex,07:00-20:00"')
    return j


def janela_de_texto(texto: Optional[str]) -> Optional[Dict[str, str]]:
    """`"seg-sex,07:00-20:00"` -> `{"dias": "seg-sex", "inicio": "07:00", "fim": "20:00"}` — o objeto que o CHECK do
    banco exige (`jsonb_typeof = 'object'`) e que `robos.dentro_da_janela` lê."""
    if texto is None:
        return None
    dias, _, horas = str(texto).strip().rpartition(",")
    inicio, _, fim = horas.partition("-")
    return janela_valida({"dias": dias, "inicio": inicio, "fim": fim})


def janela_em_texto(janela: Any) -> str:
    return f"{janela.get('dias')},{janela.get('inicio')}-{janela.get('fim')}" if isinstance(janela, dict) else "-"


# ======================================================================================================================
# Leitura
# ======================================================================================================================
def empresa(supa, company_id: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(supa.table("companies").select("id, company_kind").eq("id", company_id).limit(1).execute())
    return linhas[0] if linhas else None


def conta_por_id(supa, conta_id: str, company_id: Optional[str] = None) -> Dict[str, Any]:
    """A conta de robô (portal agger, `robo_estado` não nulo). Com `company_id`, SÓ se for desta corretora."""
    q = (supa.table("portal_accounts").select("id, company_id, portal_key, robo_estado")
         .eq("id", conta_id).eq("portal_key", PORTAL_KEY))
    if company_id is not None:
        q = q.eq("company_id", company_id)
    linhas = _dados(q.limit(1).execute())
    if not linhas or linhas[0].get("robo_estado") is None:
        raise Recusa("conta de robô do multicálculo não encontrada")
    return linhas[0]


# ======================================================================================================================
# As escritas — as ÚNICAS que gravam a conta do robô
# ======================================================================================================================
def cadastrar(supa, *, company_id: str, rotulo: str, usuario: str, senha: Union[str, Callable[[], str]],
              estado: str, janela: Optional[Dict[str, str]], teto: Optional[int],
              cifrar: Callable[[str], str]) -> Dict[str, Any]:
    """Cria a conta do robô: senha cifrada no cofre, `robo_estado` = `ativo` (login de ROBÔ) ou `teste` (login de
    PESSOA, só canário, exige janela). Devolve a linha criada SEM o segredo.

    `senha` pode ser uma função: ela só é chamada DEPOIS de todas as recusas (o comando pede a senha digitada só
    quando ela vai ser usada)."""
    emp = empresa(supa, company_id)
    if not emp or emp.get("company_kind") != "client":
        raise Recusa("a corretora precisa ser uma empresa cliente (company_kind='client')")
    if estado not in (robos.ATIVO, robos.TESTE):
        raise Recusa("--estado: ativo ou teste")
    janela = janela_valida(janela) if janela is not None else None
    if estado == robos.TESTE and janela is None:
        raise Recusa("conta 'teste' (login de PESSOA) exige --janela (D-129B-04)")
    if teto is not None and not 1 <= int(teto) <= 600:
        raise Recusa("--teto entre 1 e 600 por hora")
    usuario = str(usuario or "").strip()
    if not usuario:
        raise Recusa("--usuario obrigatório")
    rotulo = str(rotulo or "").strip()
    if not rotulo:
        raise Recusa("--rotulo obrigatório")
    existe = _dados(supa.table("portal_accounts").select("id, robo_estado").eq("company_id", company_id)
                    .eq("portal_key", PORTAL_KEY).eq("account_label", rotulo).limit(1).execute())
    if existe:
        # conserto 129-B (juiz P3): a linha FICA (apagar-senha não a remove) — o caminho é trocar a senha e religar
        cid = existe[0]["id"]
        raise Recusa(f"já existe a conta {cid} com este rótulo nesta corretora (estado {existe[0].get('robo_estado')})"
                     f" — para trocar a senha: `trocar-senha --conta {cid}` e depois `religar --conta {cid} --estado "
                     f"ativo|teste`; ou cadastre com OUTRO rótulo")
    if callable(senha):
        senha = senha()
    if not senha:
        raise Recusa("senha vazia")
    linha = {"company_id": company_id, "portal_key": PORTAL_KEY, "account_label": rotulo, "username": usuario,
             "secret_encrypted": cifrar(senha), "health": "unknown", "robo_estado": estado,
             "robo_teto_por_hora": int(teto) if teto is not None else None, "robo_janela": janela}
    senha = ""  # noqa: F841 — a senha em claro não sobrevive à cifra
    criada = _dados(supa.table("portal_accounts").insert(linha).execute())
    linha.pop("secret_encrypted", None)
    return {**linha, "id": criada[0]["id"] if criada else None}


def pausar(supa, conta: Dict[str, Any]) -> None:
    supa.table("portal_accounts").update({"robo_estado": robos.PAUSADO}).eq("id", conta["id"]).eq(
        "company_id", conta["company_id"]).execute()


def religar(supa, conta: Dict[str, Any], estado: str) -> None:
    """Conserto 129-B (juiz P3, red P8): `pausado`/`bloqueado`/`ocupada` -> `ativo` ou `teste` — o ÚNICO caminho de
    volta (o motor nunca desfaz uma pausa). Recusa conta sem senha e `teste` sem janela. CAS no estado de origem."""
    if estado not in (robos.ATIVO, robos.TESTE):
        raise Recusa("--estado: ativo ou teste")
    linha = _dados(supa.table("portal_accounts").select("id, secret_encrypted, robo_janela, robo_estado")
                   .eq("id", conta["id"]).eq("company_id", conta["company_id"]).limit(1).execute())
    if not linha or not linha[0].get("secret_encrypted"):
        raise Recusa("a conta está sem senha — rode `trocar-senha` antes de religar")
    if estado == robos.TESTE and not linha[0].get("robo_janela"):
        raise Recusa("conta 'teste' (login de PESSOA) exige janela — cadastre de novo com --janela")
    de = (robos.PAUSADO, robos.BLOQUEADO, robos.OCUPADA)
    atual = linha[0].get("robo_estado")
    if atual not in de:
        raise Recusa(f"a conta está '{atual}' — religar só desfaz pausado, bloqueado ou ocupada")
    feito = _dados(supa.table("portal_accounts").update({"robo_estado": estado, "robo_ocupada_ate": None})
                   .eq("id", conta["id"]).eq("company_id", conta["company_id"]).in_("robo_estado", list(de)).execute())
    if not feito:
        raise Recusa("a conta mudou de estado enquanto o comando rodava — rode `listar` e tente de novo")


def trocar_senha(supa, conta: Dict[str, Any], senha: str, *, cifrar: Callable[[str], str],
                 usuario: Optional[str] = None) -> None:
    """A senha nova (e, se veio, o login novo), cifrada. A conta fica `pausado` — o gatilho do banco
    (`trg_portal_accounts_robo_pausa`) já faz isso quando o segredo muda; aqui é escrito junto para não depender dele —
    e volta com `religar`."""
    if not senha:
        raise Recusa("senha vazia")
    patch: Dict[str, Any] = {"secret_encrypted": cifrar(senha), "robo_estado": robos.PAUSADO}
    if usuario is not None:
        usuario = str(usuario).strip()
        if not usuario:
            raise Recusa("login vazio")
        patch["username"] = usuario
    supa.table("portal_accounts").update(patch).eq("id", conta["id"]).eq("company_id", conta["company_id"]).execute()


def apagar_senha(supa, conta: Dict[str, Any]) -> None:
    """A senha sai do cofre e a conta fica `pausado`. A LINHA fica: os cálculos apontam para ela (FK composta de
    `multicalculo_calculos`) — o histórico não se apaga."""
    supa.table("portal_accounts").update({"secret_encrypted": None, "robo_estado": robos.PAUSADO}).eq(
        "id", conta["id"]).eq("company_id", conta["company_id"]).execute()


def mudar_janela(supa, conta: Dict[str, Any], janela: Dict[str, str]) -> None:
    janela = janela_valida(janela)
    supa.table("portal_accounts").update({"robo_janela": janela}).eq("id", conta["id"]).eq(
        "company_id", conta["company_id"]).execute()


# ======================================================================================================================
# A TELA — o "Agger da corretora" (D-133A1-03/04). `company_id` vem SEMPRE da sessão (o proxy Next).
# ======================================================================================================================
_COLUNAS_DA_TELA = ("id, company_id, account_label, username, secret_encrypted, robo_estado, robo_teto_por_hora, "
                    "robo_janela, robo_ocupada_ate, robo_dono, robo_batida_em, updated_at")


def conta_da_corretora(supa, company_id: str) -> Optional[Dict[str, Any]]:
    """A conta GLOBAL do robô desta corretora (rótulo fixo) — filtro por `company_id` sempre."""
    linhas = _dados(supa.table("portal_accounts").select(_COLUNAS_DA_TELA).eq("company_id", company_id)
                    .eq("portal_key", PORTAL_KEY).eq("account_label", ROTULO_DA_CORRETORA).limit(1).execute())
    return linhas[0] if linhas and linhas[0].get("robo_estado") is not None else None


def _ultimo_calculo(supa, conta: Dict[str, Any]) -> Optional[str]:
    linhas = _dados(supa.table("multicalculo_calculos").select("disparado_em")
                    .eq("company_id", conta["company_id"]).eq("account_id", conta["id"])
                    .not_.is_("disparado_em", "null").order("disparado_em", desc=True).limit(1).execute())
    return str(linhas[0]["disparado_em"]) if linhas else None


def retrato(supa, company_id: str, *, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """O que a tela mostra — SEM senha, SEM segredo cifrado, SEM a lease, com o login MASCARADO.

    `situacao`: nao_conectado · desconectado · senha_recusada · pausado · ocupada · teste · calculando ·
    funcionando · aguardando. O texto humano vem DAQUI (a tela não traduz estado cru)."""
    agora = agora or datetime.now(timezone.utc)
    c = conta_da_corretora(supa, company_id)
    base = {"nome": NOME_DA_CORRETORA, "janela_padrao": dict(JANELA_PADRAO), "dias_possiveis": list(DIAS_DA_TELA),
            "teto_padrao_por_hora": robos.TETO_PADRAO_POR_HORA}
    if c is None:
        return {**base, "conectado": False, "situacao": "nao_conectado",
                "rotulo": "Ainda não conectado — coloque o login e a senha do Agger da corretora.",
                "acoes": ["conectar"]}
    estado = c.get("robo_estado")
    tem_senha = bool(c.get("secret_encrypted"))
    ultimo = _ultimo_calculo(supa, c)
    janela = c.get("robo_janela")
    na_janela = robos.dentro_da_janela(janela, agora)
    lease = robos._ts(c.get("robo_batida_em"))
    em_uso = bool(c.get("robo_dono")) and lease is not None and (agora - lease).total_seconds() < robos.LEASE_VENCE_S
    if not tem_senha:
        situacao, rotulo, acoes = ("desconectado", "Desconectado — a senha foi apagada. O robô não calcula.",
                                   ["conectar"])
    elif estado == robos.BLOQUEADO:
        situacao, rotulo, acoes = ("senha_recusada", "O Agger recusou a senha. Troque a senha para o robô voltar.",
                                   ["trocar_senha", "desconectar"])
    elif estado == robos.PAUSADO:
        situacao, rotulo, acoes = ("pausado", "Pausado — o robô não calcula até você religar.",
                                   ["religar", "trocar_senha", "desconectar"])
    elif estado == robos.OCUPADA:
        situacao, rotulo, acoes = ("ocupada", "Alguém entrou no Agger com este login. O robô volta sozinho em "
                                              "alguns minutos.", ["pausar", "trocar_senha", "desconectar"])
    elif estado == robos.TESTE:
        situacao, rotulo, acoes = ("teste", "Em teste (só o canário usa esta conta).",
                                   ["pausar", "trocar_senha", "desconectar"])
    elif em_uso:
        situacao, rotulo, acoes = ("calculando", "Funcionando — calculando agora.",
                                   ["pausar", "trocar_senha", "desconectar"])
    elif ultimo:
        situacao, rotulo, acoes = ("funcionando", "Funcionando.", ["pausar", "trocar_senha", "desconectar"])
    else:
        situacao, rotulo, acoes = ("aguardando", "Conectado — aguardando o 1º cálculo.",
                                   ["pausar", "trocar_senha", "desconectar"])
    return {**base, "conectado": tem_senha, "situacao": situacao, "rotulo": rotulo, "acoes": acoes + ["janela"],
            "id": c["id"], "usuario": mascarar(c.get("username") or ""), "tem_senha": tem_senha, "estado": estado,
            "ultimo_uso": ultimo, "ocupada_ate": c.get("robo_ocupada_ate") if estado == robos.OCUPADA else None,
            "janela": janela if isinstance(janela, dict) else None, "dentro_da_janela": na_janela,
            "teto_por_hora": robos.teto_da_conta(c), "atualizado_em": c.get("updated_at")}


def conectar_da_corretora(supa, company_id: str, *, usuario: str, senha: str, cifrar: Callable[[str], str],
                          janela: Optional[Dict[str, str]] = None) -> None:
    """Conectar e trocar a senha são o MESMO gesto na tela: login + senha → a conta global em uso real.

    Sem conta: `cadastrar` (o MESMO do comando) com `ativo`, a janela padrão (ou a escolhida) e o teto padrão.
    Com conta: `trocar_senha` (pausa — e o gatilho do banco pausaria de qualquer jeito) e `religar` como `ativo`;
    o login em branco mantém o guardado (trocar só a senha).

    🔴 D-133A1-03 (revê a D-129B-11): a tela aceita o Agger porque o login agora é DEDICADO ao robô (cotador@) e
    quem o põe é o admin da corretora, de propósito. Por isso a conta da tela nasce e volta SEMPRE `ativo` — nunca
    `teste`: login de PESSOA continua proibido para o robô em uso real, e a conta de pessoa (canário) só o comando
    cadastra, com outro rótulo."""
    usuario = str(usuario or "").strip()
    c = conta_da_corretora(supa, company_id)
    if not senha or (c is None and not usuario):
        raise Recusa("Informe o login e a senha do Agger.")
    if c is None:
        cadastrar(supa, company_id=company_id, rotulo=ROTULO_DA_CORRETORA, usuario=usuario, senha=senha,
                  estado=robos.ATIVO, janela=janela or dict(JANELA_PADRAO), teto=None, cifrar=cifrar)
        return
    # login em branco ao trocar a senha = mantém o login que já está guardado
    trocar_senha(supa, c, senha, cifrar=cifrar, usuario=usuario or None)
    if janela is not None:
        mudar_janela(supa, c, janela)
    religar(supa, c, robos.ATIVO)


def agir_da_corretora(supa, company_id: str, acao: str, *, janela: Optional[Dict[str, str]] = None) -> None:
    """pausar · religar · desconectar · janela — sempre sobre a conta GLOBAL desta corretora."""
    c = conta_da_corretora(supa, company_id)
    if c is None:
        raise Recusa("O Agger da corretora ainda não está conectado.")
    if acao == "pausar":
        pausar(supa, c)
    elif acao == "religar":
        if not c.get("secret_encrypted"):
            raise Recusa("Sem senha guardada — conecte de novo com o login e a senha.")
        if c.get("robo_estado") == robos.BLOQUEADO:
            raise Recusa("O Agger recusou esta senha — troque a senha para religar.")
        if c.get("robo_estado") == robos.ATIVO:
            return
        religar(supa, c, robos.ATIVO)
    elif acao == "desconectar":
        apagar_senha(supa, c)
    elif acao == "janela":
        if janela is None:
            raise Recusa("Informe os dias e o horário.")
        mudar_janela(supa, c, janela)
    else:
        raise Recusa("ação desconhecida")


__all__ = (
    "PORTAL_KEY", "ROTULO_DA_CORRETORA", "NOME_DA_CORRETORA", "JANELA_PADRAO", "Recusa", "mascarar",
    "janela_valida", "janela_de_texto", "janela_em_texto", "empresa", "conta_por_id", "cadastrar", "pausar",
    "religar", "trocar_senha", "apagar_senha", "mudar_janela", "conta_da_corretora", "retrato",
    "conectar_da_corretora", "agir_da_corretora",
)
