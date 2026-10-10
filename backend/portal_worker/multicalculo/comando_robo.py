# -*- coding: utf-8 -*-
"""O COMANDO do Founder para os robôs do multicálculo — SPEC-129-B U6 (é o comando da T-120).

    python -m portal_worker.multicalculo.comando_robo <ação> ...     (DENTRO do contêiner do portal-worker)
    python scripts/multicalculo_robo.py <ação> ...                   (no backend / smith-api: o mesmo código)

    cadastrar     --corretora <uuid> --rotulo <texto> --usuario <email> --estado ativo|teste [--teto N]
                  [--janela "seg-sex,07:00-20:00"]      senha: MULTICALCULO_SENHA ou digitada (getpass) — NUNCA argumento
                  (--estado OBRIGATÓRIO: `ativo` = login de ROBÔ em uso real; `teste` = login de PESSOA, só canário)
    pausar        --conta <uuid>
    religar       --conta <uuid> --estado ativo|teste   pausado/bloqueado/ocupada -> de volta (o motor NUNCA desfaz)
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
from typing import Any, Callable, Dict, List, Optional

from . import conta_do_robo as CR
from . import robos

PORTAL_KEY = robos.PORTAL_KEY
ENV_SENHA = "MULTICALCULO_SENHA"
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# 🔴 SPEC-133-A.1 F3: as regras de gravar a conta do robô moram em `conta_do_robo` — o MESMO serviço que a tela de
# conexões ("Agger da corretora") chama. Aqui fica só a linha de comando: argumentos, senha digitada e a frase.
Recusa = CR.Recusa
mascarar = CR.mascarar
janela_de_texto = CR.janela_de_texto


def _uuid(valor: str, nome: str) -> str:
    if not _UUID.match(str(valor or "").strip()):
        raise Recusa(f"{nome} precisa ser um uuid")
    return str(valor).strip().lower()


def _dados(r: Any) -> List[Dict[str, Any]]:
    return list(getattr(r, "data", None) or [])


def _empresa(supa, company_id: str) -> Optional[Dict[str, Any]]:
    return CR.empresa(supa, company_id)


def _conta(supa, conta_id: str) -> Dict[str, Any]:
    return CR.conta_por_id(supa, conta_id)


# ======================================================================================================================
# As ações
# ======================================================================================================================
def cadastrar(supa, args, *, ler_senha: Callable[[], str], cifrar: Callable[[str], str]) -> str:
    corretora = _uuid(args.corretora, "--corretora")

    def _senha() -> str:   # só é pedida DEPOIS das recusas (o Founder não digita à toa)
        s = ler_senha()
        if not s:
            raise Recusa(f"senha vazia (use {ENV_SENHA} ou digite quando pedir)")
        return s

    janela = janela_de_texto(args.janela)
    criada = CR.cadastrar(supa, company_id=corretora, rotulo=args.rotulo, usuario=args.usuario, senha=_senha,
                          estado=args.estado, janela=janela, teto=args.teto, cifrar=cifrar)
    return (f"robô cadastrado: conta {criada.get('id') or '?'} · corretora {corretora} · rótulo {criada['account_label']}"
            f" · usuário {mascarar(criada['username'])} · estado {criada['robo_estado']}"
            + (f" · janela {args.janela}" if janela else ""))


def pausar(supa, args) -> str:
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    CR.pausar(supa, conta)
    return f"robô pausado: conta {conta['id']} (era {conta.get('robo_estado')})"


def religar(supa, args) -> str:
    """`pausado`/`bloqueado`/`ocupada` -> `ativo` ou `teste` — o ÚNICO caminho de volta (o motor nunca desfaz uma
    pausa). `--estado` obrigatório: religar o login de uma PESSOA como `ativo` o põe em uso real."""
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    CR.religar(supa, conta, args.estado)
    return f"robô religado: conta {conta['id']} ({conta.get('robo_estado')} -> {args.estado})"


def trocar_senha(supa, args, *, ler_senha: Callable[[], str], cifrar: Callable[[str], str]) -> str:
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    senha = ler_senha()
    if not senha:
        raise Recusa(f"senha vazia (use {ENV_SENHA} ou digite quando pedir)")
    CR.trocar_senha(supa, conta, senha, cifrar=cifrar)
    senha = ""  # noqa: F841 — a senha em claro não sobrevive à cifra
    return (f"senha trocada e robô pausado: conta {conta['id']} — para voltar a usar: "
            f"`religar --conta {conta['id']} --estado ativo|teste`")


def apagar_senha(supa, args) -> str:
    conta = _conta(supa, _uuid(args.conta, "--conta"))
    CR.apagar_senha(supa, conta)
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
        janela = CR.janela_em_texto(j)
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
        return f"adesão reativada: canal {canal} -> corretora {corretora}"
    supa.table("multicalculo_adesoes").insert({"canal_company_id": canal, "corretora_company_id": corretora,
                                               "ativa": True}).execute()
    return f"adesão criada: canal {canal} -> corretora {corretora}"


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
    s = sub.add_parser("religar", help="pausado/bloqueado/ocupada -> ativo ou teste (o único caminho de volta)")
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
    # console Windows (cp1252) quebrava ao imprimir caractere fora da tabela DEPOIS de gravar no banco (confirmação
    # 129-B, P-0): a saída nunca derruba o comando — o que não cabe vira "?"
    for _fluxo in (sys.stdout, sys.stderr):
        try:
            _fluxo.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001 — fluxo substituído (testes, pipes)
            pass
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
