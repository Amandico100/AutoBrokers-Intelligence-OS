# -*- coding: utf-8 -*-
"""O COMANDO do Founder para os robôs do multicálculo — SPEC-129-B U6 (é o comando da T-120).

    python -m portal_worker.multicalculo.comando_robo <ação> ...     (DENTRO do contêiner do portal-worker)
    python scripts/multicalculo_robo.py <ação> ...                   (no backend / smith-api: o mesmo código)

    cadastrar     --corretora <uuid> --rotulo <texto> --usuario <email> --estado ativo|teste [--teto N]
                  [--janela "seg-sex,07:00-20:00"]      senha: MULTICALCULO_SENHA ou digitada (getpass) — NUNCA argumento
                  (--estado OBRIGATÓRIO: `ativo` = login de ROBÔ em uso real; `teste` = login de PESSOA, só canário)
    pausar        --conta <uuid>
    religar       --conta <uuid> --estado ativo|teste   pausado/bloqueado/ocupada → de volta (o motor NUNCA desfaz)
    trocar-senha  --conta <uuid>                        senha nova (getpass); a conta fica pausada; depois `religar`
    listar        [--corretora <uuid>]                  sem senha; o usuário MASCARADO
    aderir        --canal <uuid> --corretora <uuid>     recusa se o canal não for `platform_canal`
    apagar-senha  --conta <uuid>                        a conta vira `pausado` e fica sem senha

🔴 Mora no pacote do worker porque a imagem do `portal-worker` copia SÓ `backend/portal_worker` (Dockerfile): o
comando tem de rodar onde o robô roda (protocolo §5 ②, ambiente de uso). Por isso usa o cofre do worker
(`portal_worker.vault`, a MESMA chave do smith-api) e o cliente do worker (`worker._supabase`: SUPABASE_URL +
SUPABASE_SERVICE_ROLE_KEY).
⛔ Nada aqui imprime senha, token ou o usuário inteiro. A conta nasce por id de corretora — nenhum nome (§13.9).
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import robos

PORTAL_KEY = robos.PORTAL_KEY
ENV_SENHA = "MULTICALCULO_SENHA"
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class Recusa(Exception):
    """O comando recusou — a mensagem é para o Founder (sem dado sensível)."""


def mascarar(valor: str) -> str:
    """A MESMA regra de `app.services.portal_vault.mask`. O pacote do worker nunca importa `app.*` (a imagem não o
    tem, e `test_contrato_do_calculo_agger` guarda isso): `test_spec129b_o_fio` confere que as duas dizem o mesmo."""
    v = str(valor or "")
    if not v:
        return ""
    if len(v) <= 3:
        return v[0] + "••"
    return v[:2] + "•" * max(3, len(v) - 4) + v[-2:]


def _uuid(valor: str, nome: str) -> str:
    if not _UUID.match(str(valor or "").strip()):
        raise Recusa(f"{nome} precisa ser um uuid")
    return str(valor).strip().lower()


def janela_de_texto(texto: Optional[str]) -> Optional[Dict[str, str]]:
    """`"seg-sex,07:00-20:00"` → `{"dias": "seg-sex", "inicio": "07:00", "fim": "20:00"}` — o objeto que o CHECK do
    banco exige (`jsonb_typeof = 'object'`) e que `robos.dentro_da_janela` lê. Ilegível → `Recusa` (a regra do motor
    é "janela ilegível = fora", e uma conta que nunca trabalha cadastrada em silêncio é pior que a recusa)."""
    if texto is None:
        return None
    t = str(texto).strip()
    dias, _, horas = t.rpartition(",")
    inicio, _, fim = horas.partition("-")
    janela = {"dias": dias.strip(), "inicio": inicio.strip(), "fim": fim.strip()}
    if not dias or robos._dias(janela["dias"]) is None or robos._minutos(janela["inicio"]) is None \
            or robos._minutos(janela["fim"]) is None or janela["inicio"] == janela["fim"]:
        raise Recusa('janela ilegível — use o formato "seg-sex,07:00-20:00"')
    return janela


def _dados(r: Any) -> List[Dict[str, Any]]:
    return list(getattr(r, "data", None) or [])


def _empresa(supa, company_id: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(supa.table("companies").select("id, company_kind").eq("id", company_id).limit(1).execute())
    return linhas[0] if linhas else None


def _conta(supa, conta_id: str) -> Dict[str, Any]:
    linhas = _dados(supa.table("portal_accounts").select("id, company_id, portal_key, robo_estado")
                    .eq("id", conta_id).eq("portal_key", PORTAL_KEY).limit(1).execute())
    if not linhas or linhas[0].get("robo_estado") is None:
        raise Recusa("conta de robô do multicálculo não encontrada")
    return linhas[0]


# ======================================================================================================================
# As ações
# ======================================================================================================================
def cadastrar(supa, args, *, ler_senha: Callable[[], str], cifrar: Callable[[str], str]) -> str:
    corretora = _uuid(args.corretora, "--corretora")
    emp = _empresa(supa, corretora)
    if not emp or emp.get("company_kind") != "client":
        raise Recusa("a corretora precisa ser uma empresa cliente (company_kind='client')")
    estado = args.estado
    if estado not in (robos.ATIVO, robos.TESTE):
        raise Recusa("--estado: ativo ou teste")
    janela = janela_de_texto(args.janela)
    if estado == robos.TESTE and janela is None:
        raise Recusa("conta 'teste' (login de PESSOA) exige --janela (D-129B-04)")
    if args.teto is not None and not 1 <= int(args.teto) <= 600:
        raise Recusa("--teto entre 1 e 600 por hora")
    usuario = str(args.usuario or "").strip()
    if not usuario:
        raise Recusa("--usuario obrigatório")
    rotulo = str(args.rotulo or "").strip()
    if not rotulo:
        raise Recusa("--rotulo obrigatório")
    existe = _dados(supa.table("portal_accounts").select("id, robo_estado").eq("company_id", corretora)
                    .eq("portal_key", PORTAL_KEY).eq("account_label", rotulo).limit(1).execute())
    if existe:
        # conserto 129-B (juiz P3): a linha FICA (apagar-senha não a remove) — o caminho é trocar a senha e religar
        cid = existe[0]["id"]
        raise Recusa(f"já existe a conta {cid} com este rótulo nesta corretora (estado {existe[0].get('robo_estado')})"
                     f" — para trocar a senha: `trocar-senha --conta {cid}` e depois `religar --conta {cid} --estado "
                     f"ativo|teste`; ou cadastre com OUTRO rótulo")
    senha = ler_senha()
    if not senha:
        raise Recusa(f"senha vazia (use {ENV_SENHA} ou digite quando pedir)")
    linha = {"company_id": corretora, "portal_key": PORTAL_KEY, "account_label": rotulo, "username": usuario,
             "secret_encrypted": cifrar(senha), "health": "unknown", "robo_estado": estado,
             "robo_teto_por_hora": int(args.teto) if args.teto is not None else None, "robo_janela": janela}
    senha = ""  # noqa: F841 — a senha em claro não sobrevive à cifra
    criada = _dados(supa.table("portal_accounts").insert(linha).execute())
    conta_id = criada[0]["id"] if criada else "?"
    return (f"robô cadastrado: conta {conta_id} · corretora {corretora} · rótulo {rotulo} · usuário "
            f"{mascarar(usuario)} · estado {estado}" + (f" · janela {args.janela}" if janela else ""))


def pausar(supa, args) -> str:
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    supa.table("portal_accounts").update({"robo_estado": robos.PAUSADO}).eq("id", conta["id"]).eq(
        "company_id", conta["company_id"]).execute()
    return f"robô pausado: conta {conta['id']} (era {conta.get('robo_estado')})"


def religar(supa, args) -> str:
    """Conserto 129-B (juiz P3, red P8): `pausado`/`bloqueado`/`ocupada` → `ativo` ou `teste` — o ÚNICO caminho de
    volta (o motor nunca desfaz uma pausa). `--estado` obrigatório: religar o login de uma PESSOA como `ativo` o põe em
    uso real, e isso tem de ser escrito, nunca padrão. Recusa conta sem senha e `teste` sem janela."""
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    estado = args.estado
    if estado not in (robos.ATIVO, robos.TESTE):
        raise Recusa("--estado: ativo ou teste")
    linha = _dados(supa.table("portal_accounts").select("id, secret_encrypted, robo_janela").eq("id", conta["id"])
                   .eq("company_id", conta["company_id"]).limit(1).execute())
    if not linha or not linha[0].get("secret_encrypted"):
        raise Recusa("a conta está sem senha — rode `trocar-senha` antes de religar")
    if estado == robos.TESTE and not linha[0].get("robo_janela"):
        raise Recusa("conta 'teste' (login de PESSOA) exige janela — cadastre de novo com --janela")
    de = (robos.PAUSADO, robos.BLOQUEADO, robos.OCUPADA)
    if conta.get("robo_estado") not in de:
        raise Recusa(f"a conta está '{conta.get('robo_estado')}' — religar só desfaz pausado, bloqueado ou ocupada")
    feito = _dados(supa.table("portal_accounts").update({"robo_estado": estado, "robo_ocupada_ate": None})
                   .eq("id", conta["id"]).eq("company_id", conta["company_id"]).in_("robo_estado", list(de)).execute())
    if not feito:
        raise Recusa("a conta mudou de estado enquanto o comando rodava — rode `listar` e tente de novo")
    return f"robô religado: conta {conta['id']} ({conta.get('robo_estado')} → {estado})"


def trocar_senha(supa, args, *, ler_senha: Callable[[], str], cifrar: Callable[[str], str]) -> str:
    """Conserto 129-B: a senha nova (getpass ou MULTICALCULO_SENHA), cifrada. A conta fica `pausado` — o gatilho do
    banco já faz isso quando o segredo muda; aqui é escrito junto para não depender dele — e volta com `religar`."""
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    senha = ler_senha()
    if not senha:
        raise Recusa(f"senha vazia (use {ENV_SENHA} ou digite quando pedir)")
    cifrada = cifrar(senha)
    senha = ""  # noqa: F841 — a senha em claro não sobrevive à cifra
    supa.table("portal_accounts").update({"secret_encrypted": cifrada, "robo_estado": robos.PAUSADO}).eq(
        "id", conta["id"]).eq("company_id", conta["company_id"]).execute()
    return (f"senha trocada e robô pausado: conta {conta['id']} — para voltar a usar: "
            f"`religar --conta {conta['id']} --estado ativo|teste`")


def apagar_senha(supa, args) -> str:
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    supa.table("portal_accounts").update({"secret_encrypted": None, "robo_estado": robos.PAUSADO}).eq(
        "id", conta["id"]).eq("company_id", conta["company_id"]).execute()
    return f"senha apagada e robô pausado: conta {conta['id']}"


def listar(supa, args) -> List[str]:
    q = (supa.table("portal_accounts")
         .select("id, company_id, account_label, username, secret_encrypted, robo_estado, robo_teto_por_hora, "
                 "robo_janela, robo_ocupada_ate, robo_dono, robo_batida_em")
         .eq("portal_key", PORTAL_KEY))
    if args.corretora:
        q = q.eq("company_id", _uuid(args.corretora, "--corretora"))
    saida = []
    for c in _dados(q.order("company_id").execute()):
        if c.get("robo_estado") is None:
            continue
        j = c.get("robo_janela")
        janela = f"{j.get('dias')},{j.get('inicio')}-{j.get('fim')}" if isinstance(j, dict) else "-"
        saida.append(
            f"{c['id']} · corretora {c['company_id']} · {c.get('account_label')} · {mascarar(c.get('username') or '')}"
            f" · {c.get('robo_estado')} · senha {'sim' if c.get('secret_encrypted') else 'NÃO'}"
            f" · teto {c.get('robo_teto_por_hora') or robos.TETO_PADRAO_POR_HORA}/h · janela {janela}"
            f" · em uso {'sim' if c.get('robo_dono') else 'não'}")
    return saida or ["nenhum robô do multicálculo cadastrado"]


def aderir(supa, args) -> str:
    canal = _uuid(args.canal, "--canal")
    corretora = _uuid(args.corretora, "--corretora")
    if canal == corretora:
        raise Recusa("canal e corretora são a mesma empresa")
    ec, ek = _empresa(supa, canal), _empresa(supa, corretora)
    if not ec or ec.get("company_kind") != "platform_canal":
        raise Recusa("--canal não é a empresa do canal (company_kind='platform_canal')")
    if not ek or ek.get("company_kind") != "client":
        raise Recusa("--corretora não é uma corretora cliente")
    existe = _dados(supa.table("multicalculo_adesoes").select("id, ativa").eq("canal_company_id", canal)
                    .eq("corretora_company_id", corretora).limit(1).execute())
    if existe:
        supa.table("multicalculo_adesoes").update({"ativa": True, "desativada_em": None}).eq(
            "id", existe[0]["id"]).eq("canal_company_id", canal).execute()
        return f"adesão reativada: canal {canal} → corretora {corretora}"
    supa.table("multicalculo_adesoes").insert({"canal_company_id": canal, "corretora_company_id": corretora,
                                               "ativa": True}).execute()
    return f"adesão criada: canal {canal} → corretora {corretora}"


# ======================================================================================================================
# A linha de comando
# ======================================================================================================================
def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="multicalculo_robo", description="Os robôs do multicálculo (SPEC-129-B U6).")
    sub = p.add_subparsers(dest="acao", required=True)
    c = sub.add_parser("cadastrar", help="cadastra um login de robô (senha por MULTICALCULO_SENHA ou digitada)")
    c.add_argument("--corretora", required=True)
    c.add_argument("--rotulo", required=True)
    c.add_argument("--usuario", required=True)
    # 🔴 conserto 129-B (juiz P2/P3): SEM padrão — `ativo` põe o login em uso REAL; o login de uma pessoa é `teste`
    c.add_argument("--estado", required=True, choices=(robos.ATIVO, robos.TESTE),
                   help="ativo (login de ROBÔ, uso real) ou teste (login de PESSOA, só no canário, exige --janela)")
    c.add_argument("--teto", type=int, default=None)
    c.add_argument("--janela", default=None, help='ex.: "seg-sex,07:00-20:00" (horário de Brasília)')
    for nome, ajuda in (("pausar", "pausa um robô"), ("apagar-senha", "apaga a senha e pausa"),
                        ("trocar-senha", "troca a senha (digitada ou MULTICALCULO_SENHA) e pausa; depois `religar`")):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("--conta", required=True)
    s = sub.add_parser("religar", help="pausado/bloqueado/ocupada → ativo ou teste (o único caminho de volta)")
    s.add_argument("--conta", required=True)
    s.add_argument("--estado", required=True, choices=(robos.ATIVO, robos.TESTE))
    s = sub.add_parser("listar", help="lista os robôs (sem senha)")
    s.add_argument("--corretora", default=None)
    s = sub.add_parser("aderir", help="liga o canal a uma corretora")
    s.add_argument("--canal", required=True)
    s.add_argument("--corretora", required=True)
    return p


def _senha_do_ambiente_ou_digitada() -> str:
    senha = os.environ.get(ENV_SENHA, "")
    if senha:
        return senha
    return getpass.getpass("senha do login do robô (não aparece na tela): ")


def main(argv: Optional[List[str]] = None, *, supa=None, ler_senha: Optional[Callable[[], str]] = None,
         cifrar: Optional[Callable[[str], str]] = None, escrever: Callable[[str], Any] = print) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:   # argumento faltando/errado: o argparse já explicou; é RECUSA (2), não exceção
        if e.code in (0, None):
            return 0
        escrever("RECUSADO: argumentos inválidos (veja a mensagem acima ou --help)")
        return 2
    try:
        if supa is None:
            from ..worker import _supabase

            if not (os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                                                    or os.getenv("SUPABASE_SERVICE_KEY"))):
                raise Recusa("faltam SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ambiente")
            supa = _supabase()
        if args.acao == "cadastrar":
            if cifrar is None:
                from .. import vault

                cifrar = vault.encrypt
            escrever(cadastrar(supa, args, ler_senha=ler_senha or _senha_do_ambiente_ou_digitada, cifrar=cifrar))
        elif args.acao == "pausar":
            escrever(pausar(supa, args))
        elif args.acao == "religar":
            escrever(religar(supa, args))
        elif args.acao == "trocar-senha":
            if cifrar is None:
                from .. import vault

                cifrar = vault.encrypt
            escrever(trocar_senha(supa, args, ler_senha=ler_senha or _senha_do_ambiente_ou_digitada, cifrar=cifrar))
        elif args.acao == "apagar-senha":
            escrever(apagar_senha(supa, args))
        elif args.acao == "listar":
            for linha in listar(supa, args):
                escrever(linha)
        elif args.acao == "aderir":
            escrever(aderir(supa, args))
        return 0
    except Recusa as e:
        escrever(f"RECUSADO: {e}")
        return 2
    except Exception as e:  # noqa: BLE001 — nunca o corpo da exceção (pode trazer a linha com o segredo)
        escrever(f"ERRO: {type(e).__name__} — nada foi alterado além do que a mensagem acima disse")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
