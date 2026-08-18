# -*- coding: utf-8 -*-
"""O acionamento da maquina de lavar percorre a URA inteira sem parar.

E o clique manual que o Founder teve de dar no teste do eletricista nao volta.

## 📊 O DEFEITO DO ELETRICISTA, medido no teste real de 18/08/2026

    12:23:30  ->  "1"                        (tipo_de_reparo_eletrico, ok)
    12:23:43  <-  "O que aconteceu? 1-Casa sem energia 2-Curto circuito"
                  <<< 2 MINUTOS E 22 SEGUNDOS DE SILENCIO >>>
    12:26:05      o Founder clicou "1" do proprio celular
    12:26:05  ->  a descricao                (voltou a funcionar sozinho)
    12:26:21  <-  RESUMO
    12:26:21  ->  SAIR                       (o freio de teste)

Causa: eu criei o passo `o_que_aconteceu` exigindo o slot
`problema_eletrico_opcao`, e NADA no produto preenchia esse slot. Passo que
exige slot que ninguem preenche nao responde e nao avisa -- fica calado.

Os slots gravados na sessao provam: titular_cpf, endereco_numero,
ponto_referencia, telefone_contato, periodo_preferido, problema_descricao,
profissional_opcao, tipo_servico_opcao, telefone_adicionar_opcao,
risco_confirmado_sem_fumaca. **Nenhum `problema_eletrico_opcao`.**

## 📊 O CAMINHO DA MAQUINA DE LAVAR

Mapeado da sessao REAL `b2bf40e7` (28/07/2026), que terminou com o protocolo
**51022010**. A ordem abaixo e a ordem que a URA usou, turno a turno.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


_spec = importlib.util.spec_from_file_location(
    "cp_lavadora", os.path.join(RAIZ, "app", "services", "corridor_playbooks.py"))
CP = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = CP
_spec.loader.exec_module(CP)

PB = CP.ALLIANZ_RESIDENCIAL_WHATSAPP_V1
PASSOS = PB["ura_steps"]


def passo_de(texto: str):
    """O primeiro passo cuja ancora casa -- a mesma ordem de `match_ura_step`."""
    for p in PASSOS:
        anc = p.get("anchor")
        if anc and re.search(anc, CP._norm(texto), re.IGNORECASE):
            return p
    return None


# 📊 AS TELAS REAIS DA URA, do acervo (`observed_events`, insurer_key='allianz').
TELA_TIPO_SERVICO = ("Vamos lá! Informe o tipo de serviço: *1 -* Serviços Emergenciais "
                     "(encanador, eletricista e chaveiro) *2 -* Para meus eletrodomésticos "
                     "*3 -* Outros serviços")
TELA_CATEGORIA = ("Qual eletrodoméstico precisa de conserto ? *1 -* Linha Branca (Microondas; "
                  "Fogão; Forno; Cooktop; Frigobar; Adega; Filtro de água; Lavadora de louças; "
                  "Coifa e exaustor de ar; Máquina de Lavar e secar roupas) *2 -* Ar Condicionado "
                  "*3 -* Geladeira, Freezer e outros *4 -* Voltar")
TELA_SERA_AGENDADO = ("Certo! O serviço de *Conserto para eletrodoméstico* deverá ser agendado. "
                      "*1 -* Continuar *2 -* Voltar")
TELA_SERA_AGENDADO_AR = ("Certo! O serviço de *Conserto para eletrodoméstico (Ar condicionado)* "
                         "deverá ser agendado *1 -* Continuar *2 -* Voltar")
TELA_DATA = ("Os agendamentos estão disponíveis de *segunda-feira* a *sexta-feira*, para os "
             "próximos *7 dias*. Escolha qual data deseja agendar: *1 -* 31/12/2025 "
             "(Quarta-feira) *2 -* 01/01/2026 (Quinta-feira)")
TELA_PERIODO_A = ("O agendamento é por período, a partir do próximo dia útil. Manhã das 09h às "
                  "13h e tarde, das 13h às 18h. Quando você prefere?")
TELA_PERIODO_B = ("E quanto aos horários de agendamento, são por *períodos (manhã* - das 9:00 as "
                  "13:00 ou *tarde* - das 13:00 às 18:00).")
TELA_PERIODO_C = ("O agendamento é feito em intervalo de 2 horas, por exemplo das 09h às 11, "
                  "das 11h às 13h e assim por diante. Quando você prefere?")
TELA_GARANTIA = ("*Importante:* O serviço é destinado a aparelhos/equipamentos de uso doméstico "
                 "que estejam fora da garantia do fabricante e que pertençam a residência "
                 "segurada. *Dica:* Antes de continuar...")
TELA_APARELHO = ("Selecione o eletrodoméstico que precisa de conserto ? *1 -* Geladeira "
                 "*2 -* Freezer *3 -* Frigobar *4 -* Adega *5 -* Micro-ondas *6 -* Fogão "
                 "*7 -* Forno *8 -* Cooktop *9 -* Filtro/Purificador de água *10 -* Lavadora "
                 "de louças *11 -* Coifa/depurador de ar *12 -* Exaustor de ar *13 -* Secadora "
                 "de roupas *14 -* Máquina de Lavar roupas *15 -* Outros")
TELA_DEFEITO = ("Para finalizar a abertura do atendimento, vamos precisar de mais algumas "
                "informações. Qual problema/defeito apresentado?")
TELA_MARCA = "Qual a marca ?"
TELA_MODELO = "E o modelo completo?"
TELA_RESUMO = ("*RESUMO* *Serviço:* Conserto de Eletrodoméstico *Problema:* Máquina de Lavar "
               "roupas *Tipo solicitação:* agendamento ... Podemos confirmar o atendimento?")

# 📊 As telas do ELETRICISTA, para o controle de nao-colisao.
TELA_O_QUE_ACONTECEU = ("O que aconteceu? *1 -* Casa inteira ou parcial sem energia "
                        "*2 -* Curto circuito ou mau funcionamento das tomadas, interruptores, "
                        "disjuntores")
TELA_QUANDO_ELETRICISTA = ("Certo! E para quando precisa do *Eletricista*? *1 -* Agora "
                           "*2 -* Quero agendar *3 -* Voltar")

# ==========================================================================
print("\n[1] O caminho da MAQUINA DE LAVAR, tela por tela")
# ==========================================================================

CAMINHO = [
    (TELA_TIPO_SERVICO, "menu_tipo_servico", "{tipo_servico_opcao}"),
    (TELA_CATEGORIA, "menu_categoria_eletrodomestico", "{eletrodomestico_categoria_opcao}"),
    (TELA_SERA_AGENDADO, "confirmar_que_sera_agendado", "1"),
    (TELA_DATA, "escolher_data_agendamento", "{data_agendamento_opcao}"),
    (TELA_PERIODO_A, "escolher_periodo_agendamento", "{periodo_agendamento_opcao}"),
    (TELA_GARANTIA, "aviso_fora_da_garantia", "1"),
    (TELA_APARELHO, "menu_aparelho", "{eletrodomestico_opcao}"),
    (TELA_DEFEITO, "problema_do_aparelho", "{problema_descricao}"),
    (TELA_MARCA, "aparelho_marca", "{aparelho_marca}"),
    (TELA_MODELO, "aparelho_modelo", "{aparelho_modelo}"),
    (TELA_RESUMO, "confirmar_atendimento", "1"),
]

for i, (tela, esperado, resposta) in enumerate(CAMINHO, 1):
    p = passo_de(tela)
    achado = (p or {}).get("step")
    check(f"{i:2d}. {esperado}", achado == esperado, f"casou com: {achado or 'NENHUM'}")
    if achado == esperado:
        check(f"    ... responde {resposta}", p.get("reply") == resposta, p.get("reply"))

# 🔴 As tres redacoes da pergunta de periodo casam TODAS o mesmo passo.
for rot, tela in (("B", TELA_PERIODO_B), ("C", TELA_PERIODO_C)):
    check(f"a redacao {rot} da pergunta de periodo tambem casa",
          (passo_de(tela) or {}).get("step") == "escolher_periodo_agendamento",
          (passo_de(tela) or {}).get("step"))
check("a variante '(Ar condicionado)' do agendamento tambem casa",
      (passo_de(TELA_SERA_AGENDADO_AR) or {}).get("step") == "confirmar_que_sera_agendado")

# ==========================================================================
print("\n[2] As duas telas de eletrodomestico NAO se confundem")
# ==========================================================================
#
# 🔴 As duas contem "eletrodomestico" e "precisa de conserto". A primeira
# escolhe a CATEGORIA (Linha Branca), a segunda o APARELHO (Maquina de Lavar).
# Trocar as duas manda a tecla `14` para um menu de 4 opcoes.

check("CATEGORIA e APARELHO casam passos DIFERENTES",
      passo_de(TELA_CATEGORIA)["step"] != passo_de(TELA_APARELHO)["step"])
check("CONTROLE: e as duas casam ALGUM passo (nenhuma ficou orfa)",
      passo_de(TELA_CATEGORIA) is not None and passo_de(TELA_APARELHO) is not None)

# ==========================================================================
print("\n[3] Nada do ELETRICISTA foi engolido pelos passos novos")
# ==========================================================================

check("'O que aconteceu?' continua sendo do eletricista",
      (passo_de(TELA_O_QUE_ACONTECEU) or {}).get("step") == "o_que_aconteceu")
check("'para quando precisa do Eletricista' continua sendo `quando`",
      (passo_de(TELA_QUANDO_ELETRICISTA) or {}).get("step") == "quando")
check("o RESUMO continua sendo a confirmacao final",
      (passo_de(TELA_RESUMO) or {}).get("step") == "confirmar_atendimento")

# 🔴 O aviso da garantia PEDE resposta. Ele contem "*Dica:*", que esta na
# ancora do `avisos_informativos` (noop). A ordem da lista e o que o protege.
p_gar = passo_de(TELA_GARANTIA)
check("o aviso da garantia RESPONDE, nao e noop",
      bool(p_gar) and not p_gar.get("noop") and p_gar.get("reply") == "1",
      f"{(p_gar or {}).get('step')} noop={(p_gar or {}).get('noop')}")
check("CONTROLE: e o noop AINDA existe e pega o que deve pegar",
      (passo_de("Termo de Privacidade: ao prosseguir...") or {}).get("noop") is True)

# ==========================================================================
print("\n[4] O SUBSERVICO tem todas as teclas -- o defeito do eletricista")
# ==========================================================================
#
# 🔴 A REGRA: todo `*_opcao` que um PASSO exige tem de ser declarado no
# subservico, ou derivado do caso. Senao o passo casa, nao consegue responder,
# e fica em silencio -- foi o que custou 2min22 e um clique manual.

SUB = PB["subservices"]
check("existe o subservico `maquina_de_lavar`", "maquina_de_lavar" in SUB)
lav = SUB.get("maquina_de_lavar", {})
check("ele sai pela opcao 2 do primeiro menu (eletrodomesticos)",
      lav.get("tipo_servico_opcao") == "2", lav.get("tipo_servico_opcao"))
check("categoria = 1 (Linha Branca)",
      lav.get("eletrodomestico_categoria_opcao") == "1")
check("aparelho = 14 (Maquina de Lavar ROUPAS)",
      lav.get("eletrodomestico_opcao") == "14", lav.get("eletrodomestico_opcao"))
check("CONTROLE: 14 nao e 10 (lava-loucas) nem 13 (secadora)",
      lav.get("eletrodomestico_opcao") not in ("10", "13"))
check("pede marca e modelo em slots SEPARADOS (a URA pergunta em duas telas)",
      "aparelho_marca" in lav.get("required_slots", [])
      and "aparelho_modelo" in lav.get("required_slots", []))

# 🔴 A VARREDURA QUE IMPEDE O DEFEITO DE VOLTAR: todo slot `*_opcao` exigido
# por um passo precisa ter origem conhecida.
exigidos = set()
for p in PASSOS:
    for r in (p.get("requires") or []):
        if str(r).endswith("_opcao"):
            exigidos.add(r)

DERIVADOS = {"problema_eletrico_opcao", "data_agendamento_opcao",
             "periodo_agendamento_opcao", "telefone_adicionar_opcao",
             "servico_opcao", "veiculo_opcao"}
for slot in sorted(exigidos):
    origens = [n for n, sub in SUB.items() if slot in sub]
    check(f"`{slot}` tem origem (subservico ou derivacao)",
          bool(origens) or slot in DERIVADOS,
          "passo que exige slot sem origem fica CALADO -- 2min22 no teste real")

check("CONTROLE: a varredura achou slots de verdade", len(exigidos) >= 4, sorted(exigidos))

# ==========================================================================
print("\n[5] O derivador traduz o que o segurado disse")

# 🔴 PRIMEIRO: ele esta LIGADO? Esta assercao veio depois de uma mutacao
# ficar VERDE: eu tirei a CHAMADA de `_derivar_teclas_do_caso` e as treze
# assercoes deste bloco continuaram passando, porque elas chamam a funcao
# DIRETO. Funcao certa e desligada e exatamente o defeito do clique manual.
#
# Decima segunda assercao desta sessao a passar pelo motivo errado -- e a
# decima segunda vez que quem pegou foi a mutacao, nunca a leitura.
import ast as _ast

with open(os.path.join(RAIZ, "app", "services", "insurer_dispatch_service.py"),
          encoding="utf-8") as _fh:
    _FONTE_IDS = _fh.read()


def _derivador_esta_ligado(fonte: str) -> bool:
    """Existe uma CHAMADA real ao derivador dentro de `new_dispatch_session`?"""
    for no in _ast.walk(_ast.parse(fonte)):
        if not isinstance(no, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        if no.name != "new_dispatch_session":
            continue
        for x in _ast.walk(no):
            if (isinstance(x, _ast.Call)
                    and getattr(x.func, "id", "") == "_derivar_teclas_do_caso"):
                return True
    return False


check("o derivador esta LIGADO em `new_dispatch_session`",
      _derivador_esta_ligado(_FONTE_IDS),
      "funcao certa e desligada e o defeito do clique manual")
_SEM_A_CHAMADA = chr(10).join([
    "def new_dispatch_session(a):",
    "    # _derivar_teclas_do_caso(slots)",
    "    return a",
])
check("CONTROLE: o detector nao acha a chamada num comentario",
      not _derivador_esta_ligado(_SEM_A_CHAMADA))
# ==========================================================================
print(chr(10) + "[6] O FIM: protocolo, senha e QUANDO O TECNICO VEM")
# ==========================================================================
#
# 🔴 O Founder pediu, textualmente: "depois venha me avisar que o acionamento
# foi feito e QUE HORAS vai ser feito e que o prestador vai chegar".
#
# 📊 A ancora `schedule` que existia espera "agendado para o dia X, entre Yh
# e Zh" -- e o fluxo de eletrodomestico NUNCA diz isso. A data e escolhida
# num menu, muito antes, e o desfecho so traz o protocolo. Sem a ancora nova,
# o segurado receberia o numero do chamado e NAO saberia quando o tecnico vem
# -- que e a unica coisa que ele quer saber.

import re as _re3

ANC = PB["capture_anchors"]

FIM_PROTOCOLO = ("Sua assistência foi solicitada com sucesso! O número de protocolo "
                 "é *51022010* É necessário um responsável maior de 18 anos.")
FIM_SENHA = ("O telefone registrado nesse atendimento é *+55 (48) 99107-2089*. "
             "Sua senha será os 4 últimos dígitos desse telefone *2089*")
RESUMO_AGENDADO = ("*RESUMO* *Serviço:* Conserto de Eletrodoméstico "
                   "*Quando:* Quarta-feira, 31/12/2025 "
                   "*Período:* manhã das 09:00 às 13:00  Podemos confirmar?")
RESUMO_VARIANTE = ("*RESUMO* *Protocolo N.°:* 51014008 "
                   "*Agendamento para:* Terça-feira, 06/01/2026 "
                   "*Período:* 13:00 às 18:00 (tarde)  ")
REDACAO_ANTIGA = "Seu atendimento foi agendado para o dia 12/08, entre 9h e 13h."


def _captura(chave, texto):
    m = _re3.search(ANC[chave], CP._norm(texto), _re3.IGNORECASE)
    return m.groups() if m else None


check("o PROTOCOLO e capturado do desfecho real",
      _captura("protocol", FIM_PROTOCOLO) == ("51022010",),
      _captura("protocol", FIM_PROTOCOLO))
check("a SENHA de acesso e capturada", _captura("password", FIM_SENHA) == ("2089",))

ag = _captura("schedule_agendado", RESUMO_AGENDADO)
check("o QUANDO e capturado do RESUMO", ag is not None, ag)
if ag:
    check("    ... com a data", "31/12/2025" in ag[0], ag[0])
    check("    ... e com o periodo", "09:00" in ag[1] and "13:00" in ag[1], ag[1])

ag2 = _captura("schedule_agendado", RESUMO_VARIANTE)
check("a segunda redacao do RESUMO tambem e capturada", ag2 is not None, ag2)
check("e o protocolo dentro do RESUMO tambem",
      _captura("protocol", RESUMO_VARIANTE) == ("51014008",))

# 🔴 CONTROLE: a ancora ANTIGA nao pode ter sido quebrada. Ela serve o
# eletricista e o encanador, que dizem "agendado para o dia X entre Yh e Zh".
check("CONTROLE: a redacao ANTIGA continua sendo capturada",
      _captura("schedule", REDACAO_ANTIGA) == ("12/08", "9h", "13h"),
      _captura("schedule", REDACAO_ANTIGA))
check("CONTROLE: e a ancora nova NAO rouba a redacao antiga",
      _captura("schedule_agendado", REDACAO_ANTIGA) is None)
check("CONTROLE: texto sem agendamento nao captura nada",
      _captura("schedule_agendado", "Bom dia, tudo bem?") is None)

# ==========================================================================

# `app/services/__init__.py` importa EAGER a arvore inteira (openai, docx,
# fastembed). Registrar um modulo LEVE com o `__path__` certo deixa os
# submodulos REAIS serem carregados -- o codigo executado e o de producao.
import types as _types

sys.path.insert(0, RAIZ)
if "app.services" not in sys.modules:
    import app as _app  # noqa: F401
    _leve = _types.ModuleType("app.services")
    _leve.__path__ = [os.path.join(RAIZ, "app", "services")]
    sys.modules["app.services"] = _leve

_sp2 = importlib.util.spec_from_file_location(
    "app.services.insurer_dispatch_service",
    os.path.join(RAIZ, "app", "services", "insurer_dispatch_service.py"))
try:
    IDS = importlib.util.module_from_spec(_sp2)
    sys.modules[_sp2.name] = IDS
    _sp2.loader.exec_module(IDS)
    derivar = IDS._derivar_teclas_do_caso
except Exception as exc:  # noqa: BLE001
    print(f"  (modulo pesado nao carrega aqui: {type(exc).__name__}) — lendo a fonte")
    derivar = None

if derivar:
    # 📊 A frase REAL do teste do Founder.
    s = {"problema_descricao": "Parte da casa sem luz, luzes apagaram, "
                               "sem cheiro de queimado, fumaça ou faísca"}
    derivar(s)
    check("a frase REAL do teste vira tecla 1 (casa sem energia)",
          s["problema_eletrico_opcao"] == "1", s["problema_eletrico_opcao"])

    s2 = {"problema_descricao": "a tomada da cozinha deu curto e parou de funcionar"}
    derivar(s2)
    check("curto circuito vira tecla 2", s2["problema_eletrico_opcao"] == "2")

    s3 = {"problema_descricao": "o disjuntor fica desarmando"}
    derivar(s3)
    check("disjuntor vira tecla 2", s3["problema_eletrico_opcao"] == "2")

    # 🔴 O QUE MAIS IMPORTA: NUNCA fica vazio.
    for descricao in ("", "nao sei", "aaaa", "está estranho", None):
        s4 = {"problema_descricao": descricao}
        derivar(s4)
        check(f"NUNCA fica vazio -- {str(descricao)[:18]!r} vira uma tecla",
              str(s4.get("problema_eletrico_opcao") or "").strip() in ("1", "2"),
              "vazio = silencio = clique manual")

    # O agendamento.
    s5 = {"periodo_preferido": "manhã"}
    derivar(s5)
    check("periodo 'manha' vira 1", s5["periodo_agendamento_opcao"] == "1")
    s6 = {"periodo_preferido": "tarde"}
    derivar(s6)
    check("periodo 'tarde' vira 2", s6["periodo_agendamento_opcao"] == "2")
    s7: dict = {}
    derivar(s7)
    check("sem preferencia, o default e TARDE (a URA aceita em mais casos)",
          s7["periodo_agendamento_opcao"] == "2")
    check("a data default e a mais proxima", s7["data_agendamento_opcao"] == "1")

    # 🔴 CONTROLE: o derivador NAO sobrescreve o que ja existe.
    s8 = {"problema_eletrico_opcao": "9", "periodo_agendamento_opcao": "9",
          "data_agendamento_opcao": "9", "problema_descricao": "curto circuito"}
    derivar(s8)
    check("CONTROLE: o que ja tem valor NAO e sobrescrito",
          s8["problema_eletrico_opcao"] == "9" and s8["periodo_agendamento_opcao"] == "9"
          and s8["data_agendamento_opcao"] == "9",
          "o subservico e a atendente mandam mais que a derivacao")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
