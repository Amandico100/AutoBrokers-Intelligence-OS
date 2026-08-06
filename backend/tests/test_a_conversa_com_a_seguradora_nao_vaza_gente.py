# -*- coding: utf-8 -*-
"""O acervo das seguradoras pode virar conhecimento sem levar gente junto.

Por que este arquivo existe
---------------------------
São 551 conversas reais com a URA de dez seguradoras, 19.421 eventos, e nenhuma
delas tinha virado conhecimento até 06/08/2026. Para lê-las é preciso exportá-las
mascaradas — e este material tem PII que o acervo de atendimento não tinha, em
formas que o `templatize` de então não conhecia.

📊 Medido em 06/08/2026 sobre as 319 sessões substanciais, antes dos consertos:

    ~240 ocorrências   primeiro nome de segurado, escrito pela própria URA
     266 ocorrências   logradouro com número, em prosa, sem rótulo nenhum
    ~750 ocorrências   palavra de MENU na mesma posição do nome

A última linha é o problema inteiro. "Magda, só mais uma informação:" e
"Guincho, borracheiro e chaveiro" têm exatamente a mesma forma, e um mascarador
que não separe as duas ou vaza nome ou apaga o vocabulário da URA — que é o
conhecimento que este acervo existe para extrair.

O caminho até a regra que separa
--------------------------------
Quatro hipóteses foram medidas, e três foram REFUTADAS pela própria medição:

| hipótese | o que dizia | o que a medição respondeu |
|---|---|---|
| forma | capitalizada + vírgula é nome | 76% dos casamentos eram menu |
| raridade | nome aparece em poucas sessões | "Saionara" em 97, "Microondas" em 9 |
| vocativo puro | nome só aparece como vocativo | Roubo, Chaveiro e Vidros caíram junto |
| **vocabulário** | **o que a seguradora OFERECE como opção nunca é gente** | **separa: menor opção 4 sessões, maior nome 3** |

Cada guarda aqui vem com um CONTROLE
------------------------------------
Um mascarador testado só contra vazamento fica mais guloso a cada correção, e o
custo aparece onde ninguém olha: no conhecimento que silenciosamente não existe.
Por isso todo caso proibido tem ao lado um caso permitido, com a mesma forma,
que PRECISA sobreviver. É o que dá direito de dizer que a regra separa as duas
coisas em vez de recusar tudo.

Os textos são reais, copiados de `observed_events` de produção — com os nomes de
pessoa trocados por outros nomes de pessoa.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str, caminho: str):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


DESTILACAO = os.path.join(RAIZ, "scripts", "destilacao_max")
sys.path.insert(0, DESTILACAO)
M = _carregar("mascarar_seg", os.path.join(DESTILACAO, "mascarar.py"))
templatize = M.templatize


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ev(direcao: str, hora: str, texto: str, tipo: str = "text",
        interativo=None, sessao: str = "s1") -> dict:
    return {"session_id": sessao, "direction": direcao, "wa_timestamp": hora,
            "msg_type": tipo, "text": texto, "interactive": interativo}


# ── 1. o prefixo de papel não pode virar rótulo ───────────────────────────────

def teste_remascarar_conhece_os_papeis_do_acervo_de_seguradora():
    print("\n[1] `remascarar` não come a instrução da seguradora")
    # `_LABELED_VALUE` casa `segurado` no começo da linha. Sem o prefixo
    # `SEGURADORA` na lista de papéis de `remascarar`, o templatize vê
    # "SEGURADORA: Por favor, informe o CPF..." como "rótulo: valor" e a
    # instrução inteira colapsa em `SEGURADO{VALOR}` — que é exatamente o
    # conhecimento que o acervo existe para extrair.
    linha = "SEGURADORA: Por favor, informe o *CPF ou CNPJ* do(a) titular."
    checar(M.remascarar(linha) == linha,
           "a instrução da seguradora atravessa `remascarar` intacta",
           f"virou {M.remascarar(linha)!r}")
    checar(M.remascarar("NOS: oi") == "NOS: oi",
           "e a nossa fala também")

    # CONTROLE: prove que o colapso É REAL, com a MESMA linha. `templatize`
    # aplicado direto no transcript montado destrói a instrução; `remascarar`
    # não. A diferença entre os dois é só arrancar o prefixo de papel antes —
    # e é ela que este teste existe para guardar. Sem esta linha, o caso acima
    # passaria igual se o `_LABELED_VALUE` estivesse morto.
    checar(templatize(linha) != linha,
           "CONTROLE: `templatize` DIRETO na mesma linha destrói a instrução",
           f"sobreviveu como {templatize(linha)!r} — então a regra 1 não prova nada")
    checar("{VALOR}" in templatize(linha),
           "e o que sobra dela é um {VALOR}", templatize(linha))


# ── 2. nome depois de saudação: os dois lados ─────────────────────────────────

def teste_saudacao_mascara_nome_e_devolve_o_verbo():
    print("\n[2] Depois da saudação: nome sai, instrução fica")
    for frase, esperado in (
            ("Olá, Magda! Como posso ajudar?", "Olá, {NOME}! Como posso ajudar?"),
            ("Ola, Magda! Como posso ajudar?", "Ola, {NOME}! Como posso ajudar?")):
        checar(templatize(frase) == esperado, f"{frase[:22]!r} → nome mascarado",
               f"virou {templatize(frase)!r}")

    # CONTROLE que conserta perda de conhecimento REAL. O `(?i)` valia para o
    # padrão inteiro, então `[A-ZÀ-Ú][a-zà-ú]{2,}` casava minúscula também:
    # 📊 em 06/08/2026, `templatize("Ola, quero abrir um sinistro")` devolvia
    # "Ola, {NOME} um sinistro" — duas palavras de conhecimento apagadas por
    # uma regra de PII, na frase em que o segurado diz o que quer.
    for frase in ("Ola, quero abrir um sinistro",
                  "Oi, preciso de guincho agora",
                  "Olá, digite o CPF",
                  "Bem-vindo à Central de Atendimento"):
        checar(templatize(frase) == frase,
               f"CONTROLE: {frase[:28]!r} sobrevive inteira",
               f"virou {templatize(frase)!r}")


def teste_tratamento_mascara_nome_e_poupa_papel():
    print("\n[3] 'Sr. Fulano' vira {NOME}; 'Sr. Corretor' não")
    checar(templatize("Sr Gustavo, o guincho chegou") == "Sr {NOME}, o guincho chegou",
           "nome depois de tratamento é mascarado",
           templatize("Sr Gustavo, o guincho chegou"))
    # CONTROLE: tratamento também precede PAPEL, e papel é conhecimento.
    for frase in ("Sr. Corretor, segue o boleto",
                  "A senhora poderia informar o CEP",
                  "A segurada informou o sinistro"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:26]!r} sobrevive",
               templatize(frase))


# ── 3. logradouro: o dígito é a regra inteira ─────────────────────────────────

def teste_logradouro_com_numero_sai_e_prosa_fica():
    print("\n[4] Endereço em prosa sai; a palavra 'rua' continua sendo palavra")
    # 📊 266 ocorrências nas 319 sessões substanciais, 195 logradouros
    # distintos, todos com número — residência ou local de sinistro de gente.
    for frase in ("R. Manoel Loureiro, 1653 - Barreiros",
                  "Av. Santos Dumont, 4828 - Joinville",
                  "Rua das Flores, 123",
                  "Rua Joinville 13777"):
        saida = templatize(frase)
        checar("{ENDERECO}" in saida, f"{frase[:26]!r} → mascarado", saida)
        checar(saida.split()[0] == frase.split()[0],
               "e o TIPO do logradouro fica (é ele que ensina o que a URA pede)",
               saida)

    # CONTROLE: sem número não é endereço, é prosa — e prosa é conhecimento.
    # Sem esta metade, a regra viraria um comedor de vocabulário: 📊 das 345
    # ocorrências que a busca por vocabulário achava, 79 não tinham número e
    # nenhuma delas era endereço.
    for frase in ("a rua é conhecida na região",
                  "O condomínio está vazando",
                  "apartamento individual",
                  "A Porto pede rua e numero do local",
                  "A cobertura vale para rodovia pedagiada"):
        checar(templatize(frase) == frase, f"CONTROLE: {frase[:30]!r} sobrevive",
               templatize(frase))


# ── 4. o transcript diz quem é quem ───────────────────────────────────────────

PORTO_MENU = ("O que você precisa?\nGuincho (reboque)\nBateria\nTroca de pneu\n"
              "Conserto de vidro\nChaveiro para o veículo")


def teste_o_transcript_nao_chama_a_seguradora_de_cliente():
    print("\n[5] `direction` significa outra coisa neste acervo")
    # No acervo de atendimento, `out` é a atendente e `in` é o segurado. Aqui
    # `out` somos NÓS acionando e `in` é a SEGURADORA respondendo. Reusar o
    # rotulador de lá faria o destilador ler o robô da Porto como se fosse um
    # segurado — o erro que a regra 8 do prompt antigo levou cinco destiladores
    # para descobrir. Aqui o rótulo sai certo da fonte.
    eventos = [_ev("out", "1", "oi"), _ev("in", "2", "Aguarde um momento")]
    saida = M.transcript_seguradora(eventos).split("\n")
    checar(saida[0] == "NOS: oi", "o que nós enviamos é NOS", saida[0])
    checar(saida[1] == "SEGURADORA: Aguarde um momento",
           "o que a seguradora respondeu é SEGURADORA", saida[1])

    # CONTROLE: o rotulador do acervo ANTIGO continua vivo e continua dizendo
    # o contrário — as duas leituras existem de propósito, para acervos
    # diferentes. Se este controle quebrar, alguém unificou o que não devia.
    antigo = M.transcript(eventos).split("\n")
    checar(antigo[0].startswith("ATENDENTE:") and antigo[1].startswith("CLIENTE:"),
           "CONTROLE: `transcript` (atendimento) mantém ATENDENTE/CLIENTE",
           str(antigo))


def teste_o_clique_sem_texto_recupera_o_rotulo():
    print("\n[6] O clique mudo tem rótulo em `interactive` — e às vezes não tem")
    # 📊 937 dos 1.861 `button_reply` do acervo têm texto vazio; 914 têm o
    # rótulo em `interactive.title`. Sem lê-lo, metade dos cliques vira
    # `[button_reply]` e o transcript perde o caminho percorrido dentro da URA.
    eventos = [
        # Uma linha só de propósito: a tela real da Porto tem quebras de linha,
        # e o transcript é quebrado por mensagem, não por evento — comparar por
        # índice de linha num menu multilinha testaria o `split`, não a regra.
        _ev("in", "1", "O que você precisa?", "list"),
        _ev("out", "2", "", "button_reply", {"kind": "button_reply", "title": "Guincho (reboque)"}),
        _ev("out", "3", "", "button_reply", {"kind": "button_reply", "id": "btn_3a9f"}),
    ]
    saida = M.transcript_seguradora(eventos).split("\n")
    checar(saida[1] == "NOS: Guincho (reboque)",
           "o rótulo do clique vem de `interactive.title`", saida[1])
    # CONTROLE: sem rótulo em lugar nenhum, o transcript DIZ que não sabe.
    # Escrever `btn_3a9f` faria o destilador ler um id opaco como se a
    # seguradora tivesse escrito isso — rótulo não se inventa.
    checar(saida[2] == "NOS: [clique sem rótulo]",
           "CONTROLE: sem rótulo, o transcript se declara ignorante", saida[2])
    checar("btn_3a9f" not in "\n".join(saida),
           "e o id opaco NÃO aparece no lugar do rótulo")


# ── 5. o vocativo: a regra que custou quatro hipóteses ────────────────────────

MENU = frozenset({"guincho", "reboque", "roubo", "chaveiro", "vidros",
                  "borracheiro", "conserto", "bateria"})


def _uma_linha(texto: str, vocab=MENU, direcao: str = "in") -> str:
    return M.transcript_seguradora([_ev(direcao, "1", texto)], vocab).split(": ", 1)[1]


def teste_o_vocativo_sai_e_o_menu_fica():
    print("\n[7] 'Magda,' vira {NOME}; 'Guincho,' continua sendo guincho")
    checar(_uma_linha("Magda, só mais uma informação:") == "{NOME}, só mais uma informação:",
           "o vocativo da URA é mascarado", _uma_linha("Magda, só mais uma informação:"))
    checar(_uma_linha("Certo, Magda! Antes de continuar") == "Certo, {NOME}! Antes de continuar",
           "e o vocativo ATRÁS de uma interjeição também",
           _uma_linha("Certo, Magda! Antes de continuar"))

    # CONTROLE — é a linha que dá direito à conclusão. A palavra de menu tem a
    # MESMA forma do nome e precisa sobreviver; se ela cair, a regra não separa
    # nada, só recusa tudo, e passaria no teste de cima sem separar coisa alguma.
    for frase in ("Guincho, borracheiro e chaveiro estão disponíveis",
                  "Roubo, furto e incêndio têm franquia própria",
                  "Vidros, retrovisores e faróis entram no mesmo pedido"):
        checar("{NOME}" not in _uma_linha(frase),
               f"CONTROLE: {frase[:30]!r} não perde a primeira palavra",
               _uma_linha(frase))

    # CONTROLE 2: e as interjeições, que não são menu nem nome, também ficam.
    for frase in ("Agora, me informe o CEP do local",
                  "Certo, vou verificar",
                  "Perfeito, seu protocolo está gerado"):
        checar("{NOME}" not in _uma_linha(frase),
               f"CONTROLE: interjeição {frase.split(',')[0]!r} sobrevive",
               _uma_linha(frase))


def teste_a_resposta_a_uma_pergunta_por_nome_e_um_nome():
    print("\n[8] Quem sabe o que a resposta é não é ela, é a pergunta")
    # "Nesse caso, qual é o nome de quem estará na residência?" / "Magda".
    # Nenhuma regra de forma alcança isso: a resposta é uma palavra capitalizada
    # solta, igual a "Guincho". A pergunta está na linha de cima.
    eventos = [
        _ev("in", "1", "Nesse caso, qual é o nome de quem estará na residência?"),
        _ev("out", "2", "Fernanda"),
        _ev("in", "3", "Certo. Informe um número de celular com DDD, por favor."),
        _ev("out", "4", "Conserto de vidro"),
    ]
    saida = M.transcript_seguradora(eventos, MENU).split("\n")
    checar(saida[1] == "NOS: {NOME}", "a resposta à pergunta por nome é mascarada",
           saida[1])
    # CONTROLE: a resposta à pergunta SEGUINTE não é nome e não pode ser
    # mascarada. Sem isto, a regra poderia estar mascarando toda resposta nossa.
    checar(saida[3] == "NOS: Conserto de vidro",
           "CONTROLE: a resposta à pergunta seguinte NÃO é tocada", saida[3])


def teste_o_vocabulario_de_menu_precisa_se_repetir_entre_sessoes():
    print("\n[9] Opção de verdade se repete; eco do cadastro aparece uma vez")
    # 📊 Sem limiar, um nome entrava no vocabulário porque a URA o ECOA dentro
    # de uma linha de lista. Medido: menor palavra de menu = 4 sessões
    # (elogios), maior nome = 3 (joao). O limiar é 4.
    eventos = []
    for i in range(4):
        eventos.append(_ev("in", "1", "O que você precisa?\nBotão 1: Guincho\nBotão 2: Bateria",
                           "buttons", {"kind": "buttons"}, sessao=f"s{i}"))
    # o eco do cadastro: uma linha de lista com o nome do titular, em UMA sessão
    eventos.append(_ev("in", "2", "Escolha:\nBotão 1: Falar com Gustavo", "buttons",
                       {"kind": "buttons"}, sessao="s0"))
    vocab = M.vocabulario_de_menu(eventos)
    checar("guincho" in vocab and "bateria" in vocab,
           "a opção que aparece em 4 sessões entra no vocabulário",
           str(sorted(vocab)))
    checar("gustavo" not in vocab,
           "CONTROLE: o nome ecoado em 1 sessão NÃO entra",
           "se entrasse, o vocabulário protegeria justamente quem devia denunciar")

    # CONTROLE 2: prove que o limiar É o que separa — com limiar 1, o nome
    # entra. Sem isto, o caso acima passaria igual se o vocabulário estivesse
    # sempre vazio.
    frouxo = M.vocabulario_de_menu(eventos, min_sessoes=1)
    checar("gustavo" in frouxo,
           "CONTROLE: com limiar 1 o nome entraria — é o limiar que decide",
           str(sorted(frouxo)))


# ── 6. a marca de já-destilada e o corte ──────────────────────────────────────

def teste_o_exportador_nao_corta_em_silencio():
    print("\n[10] O exportador sabe dizer o que deixou de fora")
    fonte = open(os.path.join(DESTILACAO, "exportar_seguradoras.py"),
                 encoding="utf-8").read()
    checar('"já destilada"' in fonte,
           "sessão já destilada é contada como descarte, não some")
    checar("distill_falhas" in fonte,
           "e a que falhou três vezes também — a mesma marca do `exportar.py`")
    checar("fora do cap de --lotes" in fonte,
           "o cap por `--lotes` se declara no índice",
           "cap silencioso é defeito (CLAUDE.md §11)")
    checar("truncadas" in fonte and "INDICE" in fonte,
           "e o transcript cortado no teto vai para o índice com o id")
    # CONTROLE: o exportador NÃO pode escrever no banco. Uma reindexação de
    # 10.818 cartas estava rodando em produção quando ele foi escrito.
    #
    # `sys.path.insert` é descontado à mão: um guarda que confunde manipulação
    # de caminho com escrita em banco cria alarme falso, e alarme falso é o que
    # ensina a ignorar alarme.
    escritas = fonte.replace("sys.path.insert(", "").replace("path.insert(", "")
    for proibido in (".update(", ".insert(", ".upsert(", ".delete(", ".rpc("):
        checar(proibido not in escritas,
               f"CONTROLE: o exportador não chama {proibido!r} em lugar nenhum",
               "ele lê, mascara e larga arquivo — quem grava é outro script")
    checar("path.insert(" in fonte,
           "CONTROLE do controle: `path.insert` existe mesmo e foi descontado",
           "se ele sumir, o desconto acima passa a esconder uma escrita real")


def main() -> int:
    print("=" * 74)
    print("A CONVERSA COM A SEGURADORA VIRA CONHECIMENTO SEM LEVAR GENTE JUNTO")
    print("=" * 74)
    for teste in (teste_remascarar_conhece_os_papeis_do_acervo_de_seguradora,
                  teste_saudacao_mascara_nome_e_devolve_o_verbo,
                  teste_tratamento_mascara_nome_e_poupa_papel,
                  teste_logradouro_com_numero_sai_e_prosa_fica,
                  teste_o_transcript_nao_chama_a_seguradora_de_cliente,
                  teste_o_clique_sem_texto_recupera_o_rotulo,
                  teste_o_vocativo_sai_e_o_menu_fica,
                  teste_a_resposta_a_uma_pergunta_por_nome_e_um_nome,
                  teste_o_vocabulario_de_menu_precisa_se_repetir_entre_sessoes,
                  teste_o_exportador_nao_corta_em_silencio):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O NOME SAI, O MENU FICA — E CADA GUARDA PROVOU AS DUAS DIREÇÕES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
