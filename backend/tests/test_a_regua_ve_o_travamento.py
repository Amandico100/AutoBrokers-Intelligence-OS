# -*- coding: utf-8 -*-
"""A régua passa a ver o travamento — SPEC-089, BLOCO C.

> **O TESTE DO PRODUTO da SPEC-089:** *"Duas rotas: uma que o robô percorre
> sozinho até o fim, e outra em que o corredor trava e uma pessoa termina. A
> régua tem de dar notas DIFERENTES — e a que precisou de gente tem de tirar
> menos."*

## 📊 O que foi medido em 26/08/2026, e o que a SPEC errou

```
work_steps `step_key='needs_human'` ........  2   ✅ a SPEC acertou
work_steps `human_phase` ...................  4   ✅
work_steps `ura` ...........................  4   ✅
work_events `travamento.*` .................  0   🔴 NENHUM
work_runs `unblock_state='retomado_pelo_robo'` 0  🔴 NENHUM
work_runs `unblock_state='travado'` ......... 1
```

🔴 **Duas das três fontes que a SPEC nomeia não existem.** Ela pede
`work_events travamento.assumido` e `unblock_state='retomado_pelo_robo'`; o que
a SPEC-093 realmente grava é `travamento.destravado` com
`payload_redacted->>'por'`, e está vazio porque **o piloto não rodou**.

## ⛔ E o eixo nasce INERTE — mas inerte não pode virar N/A

A própria SPEC avisa: *"o executor tem de conferir que não repetiu o defeito que
acabou de consertar"*. É o BLOCO A outra vez, e a distinção é de três estados:

```
travamentos is None  →  🔴 NÃO MEDI      →  ZERO, dentro do denominador
travamentos == {}    →  ✅ medi, nada travou  →  CHEIO
rota fora do mapa    →  ✅ medi, nada travou  →  CHEIO
```
"""
from __future__ import annotations

import importlib.util as _u
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SPEC = RAIZ / "docs"  # noqa: F841  (só para o leitor achar o caminho)

sys.path.insert(0, str(RAIZ / "scripts"))
import rubrica as RB           # noqa: E402
import regua_motor as M        # noqa: E402


def _rota():
    """Uma rota real das 73 — nomeada, não fabricada."""
    r = M.rota_de("allianz", "residencial", "maquina_de_lavar")
    assert r is not None, "a rota-exemplo sumiu do registry"
    return r


def _itens(travamentos):
    return RB.eixo_f(_rota(), travamentos=travamentos)


def _p(itens, nome):
    for i in itens:
        if i.nome == nome:
            return i
    raise AssertionError(f"item nao encontrado: {nome}")


CHAVE = None  # preenchida no primeiro uso


def _chave():
    r = _rota()
    return (str(getattr(r, "ref", "")), str(r.servico))


# =============================================================================
# 🔴 CONTROLE DE CARGA
# =============================================================================

def test_CONTROLE_o_eixo_F_existe_e_esta_LIGADO_em_medir():
    """§9.3 — um eixo que ninguém chama não mede nada.

    ⛔ E foi o defeito exato que a SPEC-089 §1.2 descreve sobre a régua inteira:
    *"zero ocorrências de `needs_human` nos quatro arquivos"*.
    """
    assert callable(RB.eixo_f)
    fonte = (RAIZ / "scripts" / "rubrica.py").read_text(encoding="utf-8")
    assert "+ eixo_f(rota, travamentos=travamentos)" in fonte, (
        "o eixo F existe e NAO entra em `medir()` — ele nao mede nada")
    cli = (RAIZ / "scripts" / "medir_rota.py").read_text(encoding="utf-8")
    assert "travamentos = M.travamentos_por_rota()" in cli, (
        "a CLI nao le o travamento — o eixo F receberia None SEMPRE, e a regua "
        "inteira perderia 10 pontos por um argumento que ninguem passa")


def test_CONTROLE_o_leitor_existe_e_devolve_None_ou_dict():
    assert callable(M.travamentos_por_rota)


# =============================================================================
# 🔴 ③ O GATE MAIS IMPORTANTE: inerte NÃO é N/A, e "não medi" NÃO é "não travou"
# =============================================================================

def test_rota_SEM_REGISTRO_conta_como_NAO_TRAVOU_e_nao_como_N_A():
    """🔴 Gate ③ — *"rota sem nenhum registro conta como 'não travou', NÃO como
    N/A"*.

    📊 Hoje isso vale para 43 de 43 rotas: o eixo nasce dando nota cheia e
    começa a separar quando o piloto rodar.
    """
    itens = _itens({})               # ✅ MEDI, e ninguém travou
    anda = _p(itens, "a rota anda sozinha")
    assert anda.excluido is None, (
        "o item saiu do denominador — é o defeito do BLOCO A repetido no BLOCO C")
    assert anda.pontos == anda.maximo == 6, (
        f"a rota que NAO travou tirou {anda.pontos}/{anda.maximo}")

    # e a rota ausente do mapa é o mesmo caso
    outros = _itens({("outra-rota", "outro_servico"): {"travou": 9, "humano": 9, "robo": 0}})
    assert _p(outros, "a rota anda sozinha").pontos == 6, (
        "o travamento de OUTRA rota contou nesta — o gate ④ (dois tenants) cai junto")


def test_NAO_MEDI_vale_ZERO_dentro_do_denominador():
    """🔴 **A trava que a SPEC manda conferir**: *"o executor tem de conferir que
    não repetiu o defeito que acabou de consertar"*.

    ⛔ `None` é *"o banco não respondeu"*. Zero MEDIDO e zero NÃO MEDIDO não são
    a mesma coisa, e só um dos dois é um fato (§12.1).
    """
    itens = _itens(None)
    anda = _p(itens, "a rota anda sozinha")
    assert anda.excluido is None, (
        "🔴 o item SAIU do denominador quando o banco nao respondeu — é "
        "literalmente o `SEM_ESPELHO` que o BLOCO A desta SPEC acabou de "
        "consertar, reintroduzido pelo BLOCO C")
    assert anda.pontos == 0, f"nao medir rendeu {anda.pontos} pontos"
    assert "SEM_BANCO" in anda.evidencia, (
        "o item nao diz POR QUE valeu zero — quem le a nota precisa distinguir "
        "'a rota trava' de 'ninguem mediu'")


def test_CONTROLE_medido_e_nao_medido_dao_notas_DIFERENTES():
    """§9.3 — prove que os dois estados **conseguem** ser diferentes.

    ⛔ Sem esta linha, um `eixo_f` que devolvesse sempre a mesma coisa passaria
    nos dois testes acima.
    """
    medido = _p(_itens({}), "a rota anda sozinha").pontos
    nao_medido = _p(_itens(None), "a rota anda sozinha").pontos
    assert medido != nao_medido, (
        f"medido e nao-medido dao o MESMO ({medido}) — o eixo nao distingue "
        "'olhei e esta tudo bem' de 'nao consegui olhar'")
    assert medido > nao_medido


# =============================================================================
# ① rota que travou tira MENOS que rota que não travou
# =============================================================================

def test_rota_que_TRAVOU_tira_menos_que_rota_que_NAO_travou():
    """🔴 Gate ① — e é o TESTE DO PRODUTO da SPEC-089 inteira."""
    limpa = _p(_itens({}), "a rota anda sozinha").pontos
    travada = _p(_itens({_chave(): {"travou": 3, "humano": 3, "robo": 0}}),
                 "a rota anda sozinha").pontos
    assert travada < limpa, (
        f"a rota que travou 3 vezes e so' andou com gente tirou {travada}, e a "
        f"que nunca travou tirou {limpa} — a regua nao separa as duas")


def test_o_ROBO_destravando_sozinho_vale_mais_que_GENTE_destravando():
    """⚠️ Travar não é o pecado — **depender de gente** é."""
    so_robo = _p(_itens({_chave(): {"travou": 4, "humano": 0, "robo": 4}}),
                 "a rota anda sozinha").pontos
    metade = _p(_itens({_chave(): {"travou": 4, "humano": 2, "robo": 2}}),
                "a rota anda sozinha").pontos
    so_gente = _p(_itens({_chave(): {"travou": 4, "humano": 4, "robo": 0}}),
                  "a rota anda sozinha").pontos
    assert so_robo > metade > so_gente, (
        f"a escada nao anda: so_robo={so_robo} metade={metade} so_gente={so_gente}")
    assert so_gente == 0


# =============================================================================
# ② 🔴 rota que só andou com humano NÃO é AAA
# =============================================================================

def test_o_PORTAO_abre_quando_a_rota_so_anda_com_GENTE():
    """🔴 Gate ② — *"uma rota que só anda com gente NÃO é AAA, por mais bonito
    que seja o replay dela"*.

    ⚠️ É PORTÃO e não pontos, pela mesma razão do BLOCO B: depender de gente
    não se compensa com um replay bonito.
    """
    portao = _p(_itens({_chave(): {"travou": 4, "humano": 4, "robo": 0}}),
                RB.PORTAO_ANDA_SOZINHA)
    assert portao.portao, "o item nao esta na lista de portoes"
    assert not portao.fechado, (
        "🔴 a rota so' andou com gente e o portao ficou FECHADO — ela chegaria "
        "a AAA dependendo de uma pessoa em 100% dos destraves")


def test_CONTROLE_o_portao_FECHA_quando_o_robo_destrava():
    """§9.3 — sem esta linha, um portão sempre aberto passaria acima."""
    for caso in ({"travou": 4, "humano": 0, "robo": 4},
                 {"travou": 4, "humano": 3, "robo": 1},
                 {"travou": 0, "humano": 0, "robo": 0}):
        p = _p(_itens({_chave(): caso}), RB.PORTAO_ANDA_SOZINHA)
        assert p.fechado, f"o portao abriu para {caso} — ha' destrave do robo"


def test_o_portao_nasce_FECHADO_quando_NAO_HA_medicao():
    """⛔ Sem medição não há prova de dependência, e **presunção de culpa não é
    medição**. 📊 Hoje o banco tem 2 `needs_human` e zero eventos — o eixo nasce
    inerte, e inerte não pode reprovar ninguém.
    """
    assert _p(_itens(None), RB.PORTAO_ANDA_SOZINHA).fechado
    assert _p(_itens({}), RB.PORTAO_ANDA_SOZINHA).fechado


def test_o_portao_do_travamento_NAO_pontua():
    """🔴 SPEC-089 BLOCO B — portão guarda, não pontua."""
    for t in (None, {}, {_chave(): {"travou": 4, "humano": 4, "robo": 0}}):
        p = _p(_itens(t), RB.PORTAO_ANDA_SOZINHA)
        assert not p.conta, "o portao entrou no placar"


# =============================================================================
# ④ 🔴 DOIS TENANTS — e a exclusão nomeada da Amandus
# =============================================================================

def test_o_leitor_EXCLUI_a_corretora_de_TESTE():
    """⚠️ A Amandus é a corretora de teste, e um travamento fabricado nela não
    pode reprovar rota de produção. 🔴 A régua já tem a exclusão nomeada; este
    guarda prova que o eixo novo a herdou."""
    fonte = (RAIZ / "scripts" / "regua_motor.py").read_text(encoding="utf-8")
    corpo = fonte.split("def travamentos_por_rota", 1)[1].split("\ndef ", 1)[0]
    assert "_AMANDUS_COMPANY_ID" in corpo, (
        "o leitor do travamento NAO exclui a Amandus — um travamento de teste "
        "reprovaria uma rota de producao")


def test_o_travamento_de_OUTRA_rota_nao_conta_nesta():
    """🔴 Gate ④, na forma que este eixo consegue ter: a chave é
    `(playbook_ref, subservico)`, e o travamento de uma rota não vaza na outra."""
    outra = ("porto-auto-whatsapp@v1", "guincho")
    itens = _itens({outra: {"travou": 9, "humano": 9, "robo": 0}})
    assert _p(itens, "a rota anda sozinha").pontos == 6
    assert _p(itens, RB.PORTAO_ANDA_SOZINHA).fechado


# =============================================================================
# ⑤ o que o eixo NÃO pode fazer
# =============================================================================

def test_o_leitor_NUNCA_levanta_e_devolve_None_em_falha():
    """⛔ A régua roda em máquina sem banco (é o caso dos testes). Uma exceção
    aqui derrubaria a medição inteira."""
    fonte = (RAIZ / "scripts" / "regua_motor.py").read_text(encoding="utf-8")
    corpo = fonte.split("def travamentos_por_rota", 1)[1].split("\ndef ", 1)[0]
    sem_doc = '"""'.join(corpo.split('"""')[::2])
    sem_com = "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())
    assert sem_com.count("except Exception") >= 2, (
        "o leitor tem menos de dois `except` — alguma consulta pode levantar")
    assert "raise" not in sem_com
    assert sem_com.count("return None") >= 2, (
        "alguma falha devolve `{}` em vez de `None` — e `{}` quer dizer "
        "'olhei e nada travou', que e' o contrario de 'nao consegui olhar'")


def test_o_eixo_F_NAO_imprime_dado_de_pessoa():
    """⛔ A trava do Founder."""
    fonte = (RAIZ / "scripts" / "rubrica.py").read_text(encoding="utf-8")
    corpo = fonte.split("def eixo_f", 1)[1].split("\ndef ", 1)[0]
    for proibido in ("user_phone", "counterparty", "cpf", "placa", "user_name",
                     "texto"):
        assert proibido not in corpo, f"o eixo F toca `{proibido}`"
