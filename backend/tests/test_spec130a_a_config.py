# -*- coding: utf-8 -*-
"""SPEC-130-A · F1 · U2 — a CONFIGURAÇÃO comercial, o MANUAL de negociação e a migration (G7 estático, G8).

    PADRAO_DO_PRODUTO   o ÚNICO lugar com os números de D-MC-62…72 (G8: o guarda procura os números fora dela)
    carregar            padrão ⊕ a linha DA corretora — filtro company_id no repositório, DOIS tenants no dublê
    manual              alavancas (ordem D-MC-67, limites D-MC-68), as 9 objeções reais, as 3 estratégias, FAQ,
                        sinistro — com os números DA config dentro do texto
    migration           lida como TEXTO (sem parser SQL na venv e ⛔ sem aplicar no banco: o gerente aplica):
                        APPLY/VERIFY/ROLLBACK no cabeçalho, idempotente, RLS sem policy + REVOKE (molde 129-B)
"""
from __future__ import annotations

import ast
import copy
import re
from pathlib import Path

import pytest

from app.services.multicalculo import config as CFG
from app.services.multicalculo import manual_de_negociacao as MANUAL
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, ConfigIndisponivel, carregar, mesclar, validade_dias

BACKEND = Path(__file__).resolve().parents[1]
SERVICO = BACKEND / "app" / "services" / "multicalculo"
MIGRACAO = BACKEND / "supabase" / "migrations" / "20261006_01_spec130a_config.sql"
MANIFEST = BACKEND / "supabase" / "migrations" / "MANIFEST.md"

A = "a1300000-0000-4000-8000-00000000000a"
B = "b1300000-0000-4000-8000-00000000000b"


# =====================================================================================================================
# o banco DUBLÊ — só o transporte (honra eq/limit e REGISTRA os filtros: quem sabe de tenant é o código)
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros, self.lim = banco, tabela, [], None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.filtros.append((c, str(v)))
        return self

    def limit(self, n):
        self.lim = n
        return self

    def execute(self):
        if self.banco.quebrado:
            raise ConnectionError("banco fora")
        self.banco.consultas.append((self.tabela, tuple(self.filtros)))
        linhas = [l for l in self.banco.tabelas.get(self.tabela, [])
                  if all(str(l.get(c)) == v for c, v in self.filtros)]
        return _Resp(copy.deepcopy(linhas[: self.lim] if self.lim else linhas))


class Banco:
    def __init__(self, linhas=(), quebrado=False):
        self.tabelas = {"multicalculo_config": [dict(l) for l in linhas]}
        self.consultas, self.quebrado = [], quebrado

    def table(self, nome):
        return _Consulta(self, nome)


# =====================================================================================================================
# o padrão do produto (as decisões, por número)
# =====================================================================================================================
def test_o_padrao_tem_as_decisoes_do_founder():
    p = PADRAO_DO_PRODUTO
    assert (p["comissao"]["entrada"], p["comissao"]["autonomo_minimo"], p["comissao"]["piso"]) == (15.0, 12.0, 10.0)
    assert (p["alvo_abaixo_da_atual_pct"]["minimo"], p["alvo_abaixo_da_atual_pct"]["maximo"]) == (10.0, 15.0)
    assert p["validade"]["padrao_dias"] == 5 and p["validade"]["por_seguradora"] == {}
    assert p["lembretes"]["primeiro_apos_h"] == 24
    assert sum(p["nota"]["pesos"].values()) == 100
    assert (p["opcoes"]["no_whatsapp"], p["opcoes"]["na_pagina"]) == (2, 3)
    assert p["seguradoras_que_obedecem_desconto"] == ["porto", "azul", "itau"]
    assert p["ordem_do_mais_barato"] == ["desconto", "comissao", "franquia", "carro_reserva", "vidros", "assistencia"]
    assert p["remuneracao_cnsp_382"]["ligada"] is False
    assert CFG.casa_seguradora("Porto Seguro", p["seguradoras_que_obedecem_desconto"])
    assert CFG.casa_seguradora("Itaú", p["seguradoras_que_obedecem_desconto"])
    assert not CFG.casa_seguradora("Bradesco", p["seguradoras_que_obedecem_desconto"])
    assert not CFG.casa_seguradora("Liberty Site", ["bert"])


# =====================================================================================================================
# carregar: padrão ⊕ a corretora · DOIS tenants · fail-closed
# =====================================================================================================================
def test_carregar_dois_tenants_cada_um_le_so_a_sua_linha():
    db = Banco([{"company_id": A, "config": {"comissao": {"piso": 11.0}, "validade": {"padrao_dias": 4}}},
                {"company_id": B, "config": {"opcoes": {"no_whatsapp": 1}}}])
    ca, cb = carregar(A, db=db), carregar(B, db=db)
    assert ca["comissao"]["piso"] == 11.0 and ca["validade"]["padrao_dias"] == 4 and ca["opcoes"]["no_whatsapp"] == 2
    assert cb["comissao"]["piso"] == 10.0 and cb["validade"]["padrao_dias"] == 5 and cb["opcoes"]["no_whatsapp"] == 1
    # 🔴 o filtro company_id foi PEDIDO ao banco, por quem lê (o backend usa service role — §7)
    assert db.consultas == [("multicalculo_config", (("company_id", A),)),
                            ("multicalculo_config", (("company_id", B),))]
    # o padrão do produto nunca é contaminado
    assert PADRAO_DO_PRODUTO["comissao"]["piso"] == 10.0


def test_sem_linha_e_o_padrao_e_banco_fora_recusa():
    assert carregar(A, db=Banco()) == PADRAO_DO_PRODUTO
    with pytest.raises(ConfigIndisponivel):
        carregar(A, db=Banco(quebrado=True))
    with pytest.raises(ValueError):
        carregar("nao-e-uuid", db=Banco())


def test_valor_quebrado_ou_regua_incoerente_fica_o_padrao():
    c = mesclar({"comissao": {"piso": 13.0}})                     # piso acima do autônomo
    assert c["comissao"] == PADRAO_DO_PRODUTO["comissao"]
    c = mesclar({"nota": {"pesos": {"preco": 90, "franquia": 25, "coberturas": 15}}})   # soma 130
    assert c["nota"] == PADRAO_DO_PRODUTO["nota"]
    c = mesclar({"comissao": {"entrada": "quinze"}, "chave_inventada": 1, "opcoes": {"na_pagina": 0}})
    assert c["comissao"]["entrada"] == 15.0 and "chave_inventada" not in c and c["opcoes"]["na_pagina"] == 3
    c = mesclar({"validade": {"por_seguradora": {"Porto Seguro": 7, "Tokio": 4}}, "faq": [{"pergunta": "p", "resposta": "r"}]})
    assert validade_dias(c, ["Porto Seguro", "Youse"]) == 5 and validade_dias(c, ["Tokio", "Porto Seguro"]) == 4
    assert validade_dias(PADRAO_DO_PRODUTO, []) == 5


# =====================================================================================================================
# o MANUAL como dado
# =====================================================================================================================
def test_manual_alavancas_objecoes_estrategias_com_os_numeros_da_config():
    m = MANUAL.montar()
    assert [a["chave"] for a in m["alavancas"]] == PADRAO_DO_PRODUTO["ordem_do_mais_barato"]
    assert [a["corta_cobertura"] for a in m["alavancas"]] == [False, False, True, True, True, True]
    assert len(m["objecoes"]) == 9 and m["objecoes"][-1]["chave"] == "uso_aplicativo"
    assert set(m["estrategias"]) == {"renovacao", "novo_com_apolice", "novo_sem_apolice"}
    assert "até 12 %" in m["limites"]["regra"] and "10 %" in m["limites"]["regra"]
    outra = mesclar({"comissao": {"entrada": 14.0, "autonomo_minimo": 11.0, "piso": 9.0}})
    m2 = MANUAL.montar(outra)
    assert "até 11 %" in m2["limites"]["regra"] and "9 %" in m2["limites"]["regra"] and "12 %" not in m2["limites"]["regra"]
    assert "de 14 % para 11 %" in m2["alavancas"][1]["como"]


def test_faq_e_sinistro_padrao_e_os_da_corretora():
    faq = MANUAL.faq_padrao()
    assert len(faq) == 9 and all(set(i) == {"pergunta", "resposta"} for i in faq)
    texto = " ".join(i["resposta"] for i in faq).lower()
    assert "mais barato do mercado" not in texto and "garant" not in texto
    sin = MANUAL.sinistro_padrao()
    assert sin[0].startswith("Avise a sua corretora pelo WhatsApp") and len(sin) >= 3
    cfg = mesclar({"faq": [{"pergunta": "Posso pagar no boleto?", "resposta": "Pode."}], "sinistro": ["Ligue para nós"]})
    assert MANUAL.faq_padrao(cfg) == [{"pergunta": "Posso pagar no boleto?", "resposta": "Pode."}]
    assert MANUAL.sinistro_padrao(cfg) == ["Ligue para nós"]
    assert MANUAL.faq_padrao(mesclar({"faq": [{"pergunta": "sem resposta"}]})) == faq     # incompleto → o padrão


# =====================================================================================================================
# G8 · 🔴 nenhum número comercial fora da config
# =====================================================================================================================
_CAMINHOS_COMERCIAIS = ("comissao", "alvo_abaixo_da_atual_pct", "renovacao", "validade.padrao_dias", "lembretes",
                        "nota", "opcoes", "negociacao.max_seguradoras", "negociacao.max_tentativas_por_etapa",
                        "link")
#: números genéricos demais para proibir (0, 1, 2 e 100 aparecem em arredondamento, índice, nota máxima)
_GENERICOS = {0, 1, 2, 100}
#: o que da porta.py é desta SPEC (o resto da porta é da 129-B e não entra na varredura)
_FUNCOES_DA_PORTA = {"_negociacao_da_dona", "_config_e_andamento", "ordem_do_mais_barato", "_enfileirar",
                     "cotacao_alvo", "avaliar_cotacao_alvo", "_avaliar"}
_RE_NUMERO_COM_UNIDADE = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(%|pp\b|dias?\b|h\b|horas?\b)")


def _numeros(obj, caminho=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _numeros(v, f"{caminho}.{k}" if caminho else k)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        yield caminho, obj


def proibidos():
    saida = set()
    for caminho, v in _numeros(PADRAO_DO_PRODUTO):
        if any(caminho == c or caminho.startswith(c + ".") for c in _CAMINHOS_COMERCIAIS):
            saida.add(float(v))
    return saida - {float(g) for g in _GENERICOS}


def varrer(fonte: str, nome: str, *, so_funcoes=None):
    arvore = ast.parse(fonte)
    alvos = [arvore] if so_funcoes is None else [
        n for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in so_funcoes]
    proib = proibidos()
    achados = []
    for alvo in alvos:
        for n in ast.walk(alvo):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                if float(n.value) in proib:
                    achados.append(f"{nome}:{n.lineno} número {n.value!r}")
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                for m in _RE_NUMERO_COM_UNIDADE.finditer(n.value):
                    if float(m.group(1).replace(",", ".")) in proib:
                        achados.append(f"{nome}:{n.lineno} texto {m.group(0)!r}")
    return achados


def test_g8_nenhum_numero_comercial_fora_da_config():
    """🔴 GUARDA (mutação registrada na entrega): `LIMITE = 12.0` em negociacao.py deixa este teste VERMELHO."""
    achados = []
    for arq in ("comparacao.py", "negociacao.py", "manual_de_negociacao.py"):
        achados += varrer((SERVICO / arq).read_text(encoding="utf-8"), arq)
    achados += varrer((SERVICO / "porta.py").read_text(encoding="utf-8"), "porta.py", so_funcoes=_FUNCOES_DA_PORTA)
    assert achados == []
    # as funções da porta EXISTEM (senão a varredura dela passaria vazia)
    arvore = ast.parse((SERVICO / "porta.py").read_text(encoding="utf-8"))
    nomes = {n.name for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert _FUNCOES_DA_PORTA <= nomes


def test_g8_controle_a_varredura_acha_o_numero_quando_ele_esta_la():
    assert {15.0, 12.0, 10.0, 5.0, 24.0, 60.0, 25.0} <= proibidos()
    assert varrer("PISO = 10.0\n", "x.py") == ["x.py:1 número 10.0"]
    assert varrer("t = 'aplica até 12 % sozinho'\n", "x.py") == ["x.py:1 texto '12 %'"]
    assert varrer("t = f'válido por {d} dias, 5 dias no máximo'\n", "x.py") == ["x.py:1 texto '5 dias'"]
    assert varrer("def ordem_do_mais_barato():\n    return 15\ndef outra():\n    return 15\n", "p.py",
                  so_funcoes={"ordem_do_mais_barato"}) == ["p.py:2 número 15"]
    assert varrer("x = round(v, 2)\nnota = min(100, n)\n", "x.py") == []


# =====================================================================================================================
# G7 (estático) · a migration lida como texto — ⛔ não se aplica aqui
# =====================================================================================================================
def _cabecalho_e_corpo():
    texto = MIGRACAO.read_text(encoding="utf-8")
    linhas = texto.splitlines()
    corpo = "\n".join(l for l in linhas if not l.lstrip().startswith("--"))
    cab = "\n".join(l for l in linhas if l.lstrip().startswith("--"))
    return texto, cab, corpo


def test_g7_migration_tem_apply_verify_rollback_antes_do_sql():
    texto, cab, corpo = _cabecalho_e_corpo()
    primeira_instrucao = re.search(r"^create table if not exists", texto, re.M).start()   # a 1ª linha de SQL
    for bloco in ("-- APPLY:", "-- VERIFY", "-- ROLLBACK", "-- EXPAND-FIRST: sim", "-- DESTRUTIVA:   não"):
        assert bloco in texto and texto.index(bloco) < primeira_instrucao, bloco
    assert "raise notice 'VERIFY 20261006_01 OK" in cab and "raise exception 'ROLLBACK 20261006_01 recusado" in cab


def test_g7_migration_idempotente_rls_sem_policy_e_revoke():
    _texto, _cab, corpo = _cabecalho_e_corpo()
    c = re.sub(r"\s+", " ", corpo.lower())
    assert "create table if not exists public.multicalculo_config" in c
    assert "company_id uuid primary key references public.companies(id) on delete cascade" in c
    assert "config jsonb not null default '{}'::jsonb" in c
    assert "atualizado_em timestamptz not null default now()" in c
    assert "atualizado_por uuid null references public.users_v2(id) on delete set null" in c
    assert "if not exists (select 1 from pg_constraint where conname = 'ck_mc_config_objeto')" in c
    assert "alter table public.multicalculo_config enable row level security" in c
    assert "revoke all on table public.multicalculo_config from anon, authenticated" in c
    assert "comment on table public.multicalculo_config" in c
    assert "create policy" not in c and "grant " not in c
    for proibido in ("drop ", "truncate", "delete from", "update public."):
        assert proibido not in c, proibido


def test_g7_manifest_registra_a_migration_aplicada_com_o_verify():
    # §9.3: o fato mudou em 06/10 (aplicada pelo gerente, versão 20261006084655) — a lição migra: a linha tem de
    # trazer a versão registrada e o VERIFY esperado, nunca "aplicada" sem prova.
    texto = MANIFEST.read_text(encoding="utf-8")
    assert "20261006_01_spec130a_config.sql" in texto
    linha = next(l for l in texto.splitlines() if "20261006_01_spec130a_config.sql" in l)
    assert "**APLICADA**" in linha and "NÃO APLICADA" not in linha
    assert "20261006084655" in linha and "1·1·1·0·0·1·4" in linha and "VERIFY 20261006_01 OK" in linha
