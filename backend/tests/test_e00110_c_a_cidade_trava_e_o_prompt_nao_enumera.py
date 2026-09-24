# -*- coding: utf-8 -*-
"""G4 — a CIDADE DO SERVIÇO trava o pedido, e o prompt parou de enumerar campos.

SPEC-EXTRA-001.10 P0-5. Duas metades, e elas medem coisas diferentes de
propósito: a primeira é COMPORTAMENTO (o motor recusa), a segunda é FORMA (o
texto do prompt não repete a lista).

## 🔴 O defeito que a primeira metade impede de voltar

📊 `CodigoCidade` é chave obrigatória do `PATCH /atendimentos` nas 4 capturas de
20/09/2026, e 📊 a cidade é perguntada em **8 de 8 blocos** do roteiro da
atendente humana — junto com a data, a única presente em todos.

🔴 E ela **não** é o CEP da apólice: o CEP é o de casa. Quem quebra o vidro
viajando conserta onde está. Sem cobrar a cidade antes, o robô entra no portal e
para numa tela que ninguém consegue responder por ele — **depois** de o pedido
já ter começado a nascer.

## 🔴 Por que a segunda metade é regex sobre o texto, e isso é legítimo

CLAUDE.md §9.4 manda chamar o MOTOR, não o regex. A exceção escrita lá é
exatamente esta: *"regex sobre a âncora como TEXTO, para conferir a FORMA da
declaração"*. O alvo aqui é a forma do prompt — que ele **aponte** para a
ferramenta em vez de **repetir** a lista —, e forma de texto não tem motor.

📊 O que havia antes, em `prompts.py:136`: *"Você só precisa de: CPF (da
conversa) + DATA do dano + o RELATO"*. Três coisas, para uma função que recusava
por seis. O modelo lia o prompt (o mais errado dos três lugares), chamava a
ferramenta, e recebia de volta um pedido do que o prompt dissera que não
precisava — um laço de ida e volta que custa mensagens ao segurado.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import perguntas_do_portal_de_vidros as P  # noqa: E402

# ⚠️ ATUALIZADO em 20/09/2026 (§9.3) — red B3. A UF deixou de ser assumida da
# apolice: ela tem de vir ESCRITA pelo segurado, senao o job nao nasce. 📊 O
# red team mediu o custo do jeito antigo: "Curitiba" + UF da apolice (SC) ->
# CURITIBANOS/SC, outra cidade a 300 km. E o nome vai em CAIXA ALTA, que e
# como o portal devolve a lista de cidades.
PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:300] if extra else ""))


# ⛔ Nada aqui é de uma corretora de verdade (CLAUDE.md §13.9): nome inventado,
# CPF de teste, placa de manual. O produto é de QUALQUER corretora.
PERFIL = {"nome": "Corretora Exemplo", "email": "operacao@exemplo.test",
          "telefone": "4830000000", "cpf_cnpj": "00000000000191"}

INFOCAP = {
    "ok": True,
    "policy": {"numapo": "000000", "seguradora": "LIBERTY SEGUROS S/A"},
    "vehicle": {"placa": "AAA0A91", "veiculo": "MODELO EXEMPLO 1.0",
                "chassi": "9XX0000000000000"},
    "client": {"nome": "Segurado Exemplo", "cep": "88000-000",
               "logradouro": "Rua Exemplo", "numero": "1", "bairro": "Centro",
               "cidade": "Florianopolis", "estado": "SC",
               "telefone": "48900000000", "email": "segurado@exemplo.test"},
}

BASE = {
    "cpf_cnpj": "52998224725",
    "data_dano": "05/07/2026",
    "peca": "vidro de porta",
    "como_ocorreu": "ENCONTROU O VEICULO DANIFICADO",
    "onde_ocorreu": "urbano",
    "descricao": "o carro estava estacionado e o vidro da porta foi quebrado",
}
# ⚠️ ATUALIZADO em 20/09/2026 (CLAUDE.md §9.3): "completo" mudou de novo. As
# perguntas que o portal REALMENTE FAZ no questionario passaram a ser cobradas
# antes da fronteira A — 📊 na captura do vidro de porta ele perguntou pelicula
# (P4), dianteira/traseira (P39) e lado (P35). **Nao existe journey de
# continuacao**: o token vive so em memoria e `safe_to_retry_open` e False
# depois do POST, entao faltar uma resposta vira atendimento terminado a mao.
ESPECIFICOS_SEM_CIDADE = {"onde_realizar_o_servico": "loja",
                          "pelicula": "tem insulfilm sim",
                          "porta_dianteira_ou_traseira": "dianteira",
                          "lado_motorista_ou_carona": "do lado do carona"}
ESPECIFICOS_COM_CIDADE = {**ESPECIFICOS_SEM_CIDADE,
                          "cidade_para_o_servico": "Joinville/SC"}


# ==========================================================================
def g4a_o_par_de_vereditos_opostos() -> None:
    """(a) Sem a cidade o job NÃO nasce; com ela, nasce. O par é a prova."""
    print("\n[G4a] o par: sem a cidade recusa · com a cidade abre")

    sem, erro = PP.build_portal_params(
        {**BASE, "especificos": ESPECIFICOS_SEM_CIDADE}, PERFIL, INFOCAP)
    checar(sem is None and bool(erro),
           "sem a cidade do servico, build_portal_params RECUSA",
           f"params={sem is not None}")
    checar(erro and "cidade" in erro.lower(),
           "e o erro NOMEIA o campo, em portugues de gente",
           (erro or "")[:200])
    checar(erro and "Em qual cidade" in erro,
           "e entrega a PERGUNTA pronta para o agente fazer",
           (erro or "")[:300])
    checar(erro and "cidade_para_o_servico" in erro,
           "e diz COMO a resposta volta (senao a pergunta volta para sempre)",
           (erro or "")[:400])

    # 🔴 O PAR. Sem ele, uma funcao que recusasse SEMPRE passaria nas quatro
    # assercoes acima — e o portal de vidros nunca mais abriria.
    com, erro2 = PP.build_portal_params(
        {**BASE, "especificos": ESPECIFICOS_COM_CIDADE}, PERFIL, INFOCAP)
    checar(com is not None and erro2 is None,
           "PAR: COM a cidade, o job nasce normalmente", str(erro2)[:200])
    checar(com and com["local"]["cidade_servico"] == {"uf": "SC", "cidade": "JOINVILLE"},
           "e ela chega no contrato da SPEC §5: local.cidade_servico {uf, cidade}",
           str((com or {}).get("local")))


def g4a_os_tres_formatos_de_gente() -> None:
    """O segurado escreve de quatro jeitos; os quatro são a mesma cidade."""
    print("\n[G4a-bis] 'Joinville/SC', 'Joinville - SC', 'Joinville' + UF da apolice")

    for texto, esperado, origem in (
        ("Joinville/SC", {"uf": "SC", "cidade": "JOINVILLE"}, "segurado"),
        ("Joinville - SC", {"uf": "SC", "cidade": "JOINVILLE"}, "segurado"),
        ("joinville sc", {"uf": "SC", "cidade": "JOINVILLE"}, "segurado"),
        # Sem UF: cai para a da apolice (SC, em INFOCAP) e isso fica DECLARADO.
    ):
        p, _ = PP.build_portal_params(
            {**BASE, "especificos": {**ESPECIFICOS_SEM_CIDADE,
                                     "cidade_para_o_servico": texto}},
            PERFIL, INFOCAP)
        checar(p and p["local"]["cidade_servico"] == esperado,
               f"'{texto}' vira {esperado}",
               str((p or {}).get("local", {}).get("cidade_servico")))
        checar(p and p["local"]["cidade_servico_uf_de"] == origem,
               f"'{texto}': a origem da UF fica declarada ({origem})",
               "UF assumida em silencio manda o pedido para a cidade homonima "
               "de outro estado, e isso nao se desfaz")

    # 🔴 CONTROLE do padrao: com a apolice de OUTRO estado, o default muda —
    # senao "SC" poderia estar cravado e as quatro linhas acima nao provariam
    # que a UF veio mesmo da apolice.
    outra = {**INFOCAP, "client": {**INFOCAP["client"], "estado": "PR"}}
    # 🔴 ATUALIZADO em 20/09/2026 (§9.3) — red B3. O par que existia aqui media
    # a UF ASSUMIDA da apolice, e ela MORREU: 📊 "Curitiba" com a apolice em SC
    # virava CURITIBANOS/SC, outra cidade a 300 km, e o vidraceiro esperava la.
    # O par novo mede o que passou a valer: sem UF escrita, o job NAO nasce.
    sem_uf, erro_sem_uf = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS_SEM_CIDADE,
                                 "cidade_para_o_servico": "Joinville"}},
        PERFIL, INFOCAP)
    checar(sem_uf is None and bool(erro_sem_uf),
           "sem a UF escrita pelo segurado, o job NAO nasce",
           f"params={sem_uf is not None}")
    checar("ESTADO" in str(erro_sem_uf).upper(),
           "e a recusa pergunta o ESTADO, com a sigla como exemplo",
           str(erro_sem_uf)[:160])
    com_uf, erro_com_uf = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS_SEM_CIDADE,
                                 "cidade_para_o_servico": "Joinville SC"}},
        PERFIL, INFOCAP)
    checar(com_uf is not None and erro_com_uf is None,
           "CONTROLE: com a UF escrita, o job nasce — os dois casos DIFEREM",
           str(erro_com_uf)[:120])
    checar(com_uf and com_uf["local"]["cidade_servico"] == {"uf": "SC", "cidade": "JOINVILLE"},
           "e a cidade chega no contrato da SPEC §5",
           str((com_uf or {}).get("local", {}).get("cidade_servico")))

    # E o segurado continua podendo contrariar a apolice — e o caso do viajante.
    p, _ = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS_SEM_CIDADE,
                                 "cidade_para_o_servico": "Curitiba/PR"}},
        PERFIL, INFOCAP)
    checar(p and p["local"]["cidade_servico"] == {"uf": "PR", "cidade": "CURITIBA"},
           "CONTROLE: apolice em SC e servico em PR — quem manda e o segurado",
           "e o caso inteiro pelo qual esta pergunta existe")


def g4a_a_cidade_do_cadastro_continua_existindo() -> None:
    """As duas convivem, e confundi-las é um vidraceiro na cidade errada."""
    print("\n[G4a-ter] cidade do CADASTRO x cidade do SERVICO")
    p, _ = PP.build_portal_params(
        {**BASE, "especificos": ESPECIFICOS_COM_CIDADE}, PERFIL, INFOCAP)
    checar(p and p["local"]["cidade"] == "Florianopolis",
           "local.cidade continua sendo onde ele MORA (da InfoCap)",
           str((p or {}).get("local")))
    checar(p and p["local"]["cidade_servico"]["cidade"] == "JOINVILLE",
           "local.cidade_servico e onde ele QUER o servico",
           "sao duas coisas, e o PATCH usa a segunda")
    checar(p and p["local"]["cidade"] != p["local"]["cidade_servico"]["cidade"],
           "CONTROLE: neste caso as duas sao DIFERENTES",
           "com as duas iguais, o teste nao provaria separacao nenhuma")


def g4a_a_cidade_e_a_modalidade_nao_se_respondem() -> None:
    """`cidade_para_o_servico` (lugar) × `onde_realizar_o_servico` (modalidade)."""
    print("\n[G4a-quater] lugar nao responde modalidade")
    # ⚠️ ATUALIZADO em 23/09/2026 (CLAUDE.md §9.3) — SPEC-EXTRA-001.10.1,
    # D-E001101-05: o DOMICILIO saiu do produto e a MODALIDADE deixou de ser
    # perguntada — `build_portal_params` manda sempre "loja". A afirmacao antiga
    # ("respondida a cidade, a modalidade continua faltando") so continuava verde
    # porque a pelicula tambem faltava — um guarda verde pelo motivo errado. A
    # licao migra: lugar e modalidade seguem sendo DUAS chaves, e a modalidade
    # agora e fixa, nunca perguntada.
    so_cidade, erro = PP.build_portal_params(
        {**BASE, "especificos": {k: v for k, v in ESPECIFICOS_COM_CIDADE.items()
                                 if k != "onde_realizar_o_servico"}},
        PERFIL, INFOCAP)
    checar(so_cidade is not None and erro is None,
           "respondida a CIDADE (sem modalidade), o pedido NASCE — domicilio nao trava",
           (erro or "")[:200])
    checar(bool(so_cidade)
           and so_cidade["especificos"].get("onde_realizar_o_servico") == "loja"
           and so_cidade["local"]["cidade_servico"]["cidade"] == "JOINVILLE",
           "e as duas chaves seguem separadas: modalidade 'loja' fixa, lugar = Joinville",
           str((so_cidade or {}).get("especificos")))
    dom, _ = PP.build_portal_params(
        {**BASE, "especificos": {**ESPECIFICOS_COM_CIDADE,
                                 "onde_realizar_o_servico": "domicilio"}},
        PERFIL, INFOCAP)
    checar(bool(dom) and dom["especificos"]["onde_realizar_o_servico"] == "loja",
           "CONTROLE: um 'domicilio' que ainda chegue vira 'loja' (o produto nao o entrega)",
           str((dom or {}).get("especificos")))
    so_modalidade, erro2 = PP.build_portal_params(
        {**BASE, "especificos": ESPECIFICOS_SEM_CIDADE}, PERFIL, INFOCAP)
    checar(so_modalidade is None and erro2 and "cidade" in erro2.lower(),
           "e respondida a MODALIDADE, a CIDADE continua faltando",
           (erro2 or "")[:200])


# ==========================================================================
def _bloco_de_vidros_do_prompt() -> str:
    """As linhas do prompt que falam do portal de vidros — lidas do arquivo."""
    caminho = os.path.join(RAIZ, "app", "core", "prompts.py")
    texto = open(caminho, encoding="utf-8").read()
    linhas = [l for l in texto.split("\n")
              if "portal_action" in l or "Retorno do portal (vidros)" in l
              or l.strip().startswith("- Vidros —")]
    return "\n".join(linhas)


def g4b_o_prompt_nao_enumera_campos() -> None:
    """(b) FORMA: o prompt APONTA para a ferramenta, não repete a lista dela."""
    print("\n[G4b] o bloco de vidros do prompt nao ENUMERA campos")

    bloco = _bloco_de_vidros_do_prompt()
    checar(bool(bloco.strip()), "o bloco de vidros foi encontrado no prompt",
           "sem ele, todas as assercoes abaixo passariam por vacuidade")

    # 1) A frase exata que existia, e as variações dela.
    for frase in ("só precisa", "so precisa", "voce so precisa", "você só precisa"):
        checar(frase not in bloco.lower(),
               f"a frase '{frase}' NAO esta mais no bloco de vidros",
               bloco[:300])

    # 2) E a regra geral, que pega a reescrita criativa: o bloco não pode
    #    NOMEAR três ou mais dos campos de coleta. Nomear um ou dois é
    #    inevitável (exemplo, contexto); nomear três é uma LISTA disfarçada.
    #
    #    ⚠️ `placa`, `CEP` e `endereço` ficam de fora da conta de propósito: no
    #    prompt eles aparecem numa PROIBIÇÃO ("nunca peça isso ao cliente"),
    #    que é o oposto de uma lista de coleta.
    nomes_de_coleta = ("CPF", "DATA do dano", "RELATO", "película", "insulfilm",
                       "trincado", "dianteira ou traseira", "cidade para",
                       "como aconteceu", "peça quebrou", "QUAL PECA")
    citados = [n for n in nomes_de_coleta if n.lower() in bloco.lower()]
    checar(len(citados) < 3,
           f"o bloco nomeia menos de 3 campos de coleta (citou {len(citados)})",
           f"citados={citados} — isso e a lista de novo, so que reescrita")

    # 3) E o positivo: ele tem de MANDAR usar a ferramenta como fonte.
    checar("ferramenta" in bloco.lower() and
           ("próxima pergunta" in bloco.lower() or "proxima pergunta" in bloco.lower()),
           "e ele APONTA para a ferramenta como quem sabe o que falta",
           bloco[:300])

    # 4) 🔴 As proibições que existiam TÊM de continuar existindo. Reescrever o
    #    bloco sem elas trocaria um defeito por outro pior: o modelo voltaria a
    #    inventar placa e a re-chamar a ferramenta depois de falha.
    for proibicao, apelido in (
        ("NUNCA invente placa", "nao inventar placa/CEP/endereco"),
        ("NUNCA re-chame a ferramenta com os MESMOS dados após falha",
         "nao re-chamar depois de falha"),
        ("AUTO ATIVAS", "so apolices auto ativas"),
        ("policy_number", "re-chamar com policy_number quando ha mais de uma"),
        ("placa_informada", "re-chamar com placa_informada quando ela pedir"),
    ):
        checar(proibicao in bloco, f"a proibicao/instrucao continua no prompt: {apelido}",
               "tirar uma proibicao junto com a lista trocaria um defeito por outro")


def g4b_a_descricao_da_tool_e_gerada() -> None:
    """A terceira verdade virou projeção da primeira."""
    print("\n[G4b-bis] a description da tool SAI de TRANSPORTAVEIS")

    texto = PP.descricao_da_tool()
    # Todo campo que trava e que se pergunta ao segurado aparece no texto —
    # não porque alguém o escreveu, mas porque ele está em TRANSPORTAVEIS.
    for campo in PP.TRANSPORTAVEIS:
        p = P.pergunta_do_campo(campo)
        if p is None or p.de_quem != P.DO_SEGURADO:
            continue
        checar(campo in texto, f"'{campo}' aparece na description por GERACAO",
               texto[:300])

    # 🔴 CONTROLE: a geração tem de conseguir mudar. Um texto cravado passaria
    # em tudo acima enquanto a lista não mudasse.
    antes = PP.TRANSPORTAVEIS
    try:
        PP.TRANSPORTAVEIS = antes + ("posicao_do_trincado",)
        checar("posicao_do_trincado" in PP.descricao_da_tool(),
               "CONTROLE: mexer em TRANSPORTAVEIS MUDA a description",
               "se nao mudasse, ela seria um texto cravado disfarcado de geracao")
    finally:
        PP.TRANSPORTAVEIS = antes
    checar("posicao_do_trincado" not in PP.descricao_da_tool(),
           "CONTROLE: e volta ao normal quando a lista volta")


if __name__ == "__main__":
    print("=" * 72)
    print("G4 — a cidade do servico trava, e o prompt parou de enumerar")
    print("=" * 72)
    g4a_o_par_de_vereditos_opostos()
    g4a_os_tres_formatos_de_gente()
    g4a_a_cidade_do_cadastro_continua_existindo()
    g4a_a_cidade_e_a_modalidade_nao_se_respondem()
    g4b_o_prompt_nao_enumera_campos()
    g4b_a_descricao_da_tool_e_gerada()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
