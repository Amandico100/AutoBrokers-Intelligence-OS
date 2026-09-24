# -*- coding: utf-8 -*-
"""G8 — as mensagens da continuação: o agendamento EXATO, a agenda com horários,
e nenhuma promessa sem a prova da journey.

SPEC-EXTRA-001.10.1 C3. Funções puras de `portal_params` — o MESMO escritor que
a tool (dentro dos 150 s) e o vigia (fora deles) usam.

## 🔴 Por que existe

📊 B0.6: o e-mail que o portal manda ao segurado (os dois de 21/09) diz só
"registrado com sucesso" + franquia + link — SEM loja, dia ou hora. Quem entrega
o agendamento é o NOSSO agente. Se a mensagem errar um byte do horário, o
segurado leva o carro na hora errada.

E o outro lado: até 23/09 toda parada dizia "a equipe assume", porque não havia
continuação. Agora há — mas só quando a journey PROVA (`continuacao.possivel is
True`). O par de textos (com e sem a prova) é o guarda.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.agents.tools import portal_params as PP  # noqa: E402

PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:400] if extra else ""))


# 💭 Fictício (CLAUDE.md §12.1 e §13.9). O formato é o do contrato A→C §5.
AGENDAMENTO = {"loja": "Loja Exemplo Centro", "endereco": "Av. de Exemplo, 1 - Centro",
               "referencia": "em frente a praca de exemplo", "data": "22/09/2026",
               "horario": "16:00", "permanencia": "90", "confirmado_pelo_portal": True}
DESFECHO_AGENDADO = {"tipo": "agendado", "codigo_atendimento": "88888888",
                     "franquias": [{"titulo": "Valor para troca", "valor": "630"}],
                     "link_area_segurado": "https://exemplo.test/acompanhe/88888888",
                     "agendamento": AGENDAMENTO}
DESFECHO_AGENDA = {
    "tipo": "agenda", "codigo_atendimento": "77777777",
    "lojas": [
        {"codigo_cliente": 40001, "nome": "Loja Exemplo Centro", "endereco": "Av. de Exemplo, 1",
         "cidade": "Joinville", "uf": "SC", "tem_agenda": True,
         "horarios": {"25/09": ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
                                "11:00", "11:30"],
                      "26/09": ["14:00"], "27/09": ["15:00"], "28/09": ["16:00"]}},
        {"codigo_cliente": 40002, "nome": "Loja Exemplo Norte", "tem_agenda": True,
         # lixo que NÃO pode chegar ao segurado (G8): dict, None, texto não-hora
         "horarios": {"25/09": [{"Horario": "09:00"}, None, "depois"], "xx": ["10:00"]}},
    ],
}
COM = {"possivel": True, "acao_esperada": "agendar"}
SEM = {"possivel": False}

PROIBIDOS = ("{", "[", "None")


def _limpa(texto: str) -> bool:
    return not any(p in texto for p in PROIBIDOS)


def g8_o_agendado_e_exato() -> None:
    print("\n[G8-agendado] os valores EXATOS do desfecho, o numero primeiro")
    m = PP.mensagem_do_desfecho(DESFECHO_AGENDADO)
    checar(m.index("88888888") < m.index("Agendei o serviço"),
           "o NUMERO vem antes do agendamento", m[:200])
    for rotulo, valor in (("Loja", "Loja Exemplo Centro"),
                          ("Endereço", "Av. de Exemplo, 1 - Centro"),
                          ("Ponto de referência", "em frente a praca de exemplo"),
                          ("Dia", "22/09/2026"), ("Horário", "16:00")):
        checar(f"{rotulo}: {valor}" in m, f"'{rotulo}: {valor}' copiado exato", m)
    checar("Tempo que o carro fica na loja: 90 minutos" in m,
           "permanencia 90 (📊 minutos, HAR [045]) sai com a unidade", m)
    checar("R$ 630" in m, "a franquia sai", m)
    checar("https://exemplo.test/acompanhe/88888888" in m, "o link da Area do Segurado sai")
    checar(PP.AVISO_ANTIFRAUDE in m, "e o aviso antifraude")
    checar("me avise" in m, "e o 'se precisar mudar, me avise'")
    checar(_limpa(m), "sem '{', '[' nem 'None'", m)

    # 🔴 O PAR: sem a confirmação LIDA do portal, NUNCA "Agendei".
    nao = PP.mensagem_do_desfecho({**DESFECHO_AGENDADO, "agendamento": {
        **AGENDAMENTO, "confirmado_pelo_portal": False}})
    checar("Agendei" not in nao and "Não considere agendado" in nao,
           "CONTROLE: confirmado_pelo_portal False => nada de 'Agendei'", nao)
    checar("16:00" not in nao, "e o horario NAO confirmado nem aparece", nao)
    faltando = PP.mensagem_do_desfecho({**DESFECHO_AGENDADO, "agendamento": {
        "loja": "Loja Exemplo Centro", "data": "22/09/2026", "horario": "16:00",
        "permanencia": None, "referencia": None, "confirmado_pelo_portal": True}})
    checar(_limpa(faltando) and "Ponto de referência" not in faltando,
           "dado ausente nao vira linha vazia nem 'None'", faltando)


def g8_a_agenda_com_horarios() -> None:
    print("\n[G8-agenda] por loja, os horarios por dia — no teto, e texto limpo")
    m = PP.mensagem_do_desfecho(DESFECHO_AGENDA, COM)
    checar("1) Loja Exemplo Centro" in m and "2) Loja Exemplo Norte" in m,
           "lojas NUMERADAS", m)
    checar("25/09: 08:00, 08:30, 09:00, 09:30, 10:00, 10:30" in m and "11:00" not in m,
           "no maximo 6 horarios por dia", m)
    checar("26/09: 14:00" in m and "27/09: 15:00" in m and "28/09" not in m,
           "no maximo 3 dias por loja", m)
    trecho_2 = m.split("2) Loja Exemplo Norte")[1].split("Me diga")[0] \
        if "2) Loja Exemplo Norte" in m else "?"
    checar("25/09:" not in trecho_2 and "10:00" not in trecho_2,
           "da 2a loja (so lixo: dict, None, 'depois', dia 'xx') NENHUM horario e inventado",
           trecho_2)
    checar(_limpa(m), "🔴 G8: o lixo (dict, None, 'depois') NAO chega ao segurado", m)
    checar("Me diga o número da loja, o dia e o horário que eu agendo para você." in m,
           "COM continuacao: 'eu agendo para voce'", m[-300:])
    checar("Quem confirma o horário com a loja é a nossa equipe" not in m,
           "COM continuacao: sem o 'a equipe confirma'", m[-300:])

    sem = PP.mensagem_do_desfecho(DESFECHO_AGENDA, SEM)
    checar("Quem confirma o horário com a loja é a nossa equipe" in sem
           and "Não considere agendado" in sem,
           "🔴 SEM continuacao: a versao honesta de hoje (a equipe confirma)", sem[-300:])
    checar("eu agendo para você" not in sem, "e NAO promete que o robo agenda", sem[-300:])
    checar(PP.mensagem_do_desfecho(DESFECHO_AGENDA) == sem,
           "sem o bloco `continuacao` = o mesmo que SEM (o padrao e o honesto)")
    checar("eu agendo" not in PP.mensagem_do_desfecho(DESFECHO_AGENDA, {"possivel": "true"}),
           "'possivel': 'true' em TEXTO nao e prova")


def g8_as_paradas_com_e_sem_continuacao() -> None:
    print("\n[G8-paradas] 'me responde que eu continuo' SO com a prova")
    for stage in PP.ESTAGIOS_QUE_O_SEGURADO_RESPONDE:
        sem = PP.texto_da_parada(stage, False)
        com = PP.texto_da_parada(stage, True)
        if not sem:
            checar(False, f"'{stage}' tem texto", stage)
            continue
        checar("equipe" in sem[0] and "continuo" not in sem[0],
               f"'{stage}' SEM prova: a equipe assume, nada de 'continuo'", sem[0])
        checar("continuo o seu pedido" in com[0] and PP._A_EQUIPE_ASSUME not in com[0],
               f"'{stage}' COM prova: 'me responde que eu continuo'", com[0])
        checar(_limpa(com[0]) and _limpa(sem[0]), f"'{stage}': texto limpo")
    for stage in PP.ESTAGIOS_TECNICOS:
        com = PP.texto_da_parada(stage, True)
        checar(com and "tentando de novo" in com[0],
               f"tecnico '{stage}' COM prova: 'ja estou tentando de novo'",
               com[0] if com else None)
    checar(PP.texto_da_parada("maybe_committed", True) == PP.texto_da_parada("maybe_committed"),
           "CONTROLE: maybe_committed NUNCA vira 'tento de novo' (reconciliacao, nao retry)")


def g8_as_paradas_novas() -> None:
    print("\n[G8-novas] sessao_expirada, horario_indisponivel, cancelado, nao confirmado")
    for stage in ("sessao_expirada", "sessao_indisponivel", "horario_indisponivel",
                  "atendimento_cancelado", "agendamento_nao_confirmado", "decidir_vistoria"):
        par = PP.texto_da_parada(stage)
        checar(bool(par) and len(par[0]) > 40 and len(par[1]) > 40 and _limpa(par[0]),
               f"'{stage}': texto ao segurado e dossie a equipe", par)
    exp = PP.texto_da_parada("sessao_expirada")[0]
    checar("continua valendo" in exp and "equipe" in exp and "Área do Segurado" in exp,
           "sessao_expirada: pedido valido + equipe conclui + Area do Segurado", exp)
    checar("continuo" not in exp and "eu agendo" not in exp,
           "e NAO promete o que o robo nao faz depois do 401", exp)
    nc = PP.texto_da_parada("agendamento_nao_confirmado")[0]
    checar("não vou repetir" in nc and "Não considere agendado" in nc,
           "agendamento_nao_confirmado: NAO repete e nao da como agendado", nc)

    # horario_indisponivel entrega as opções DE AGORA, pela format_result.
    job = {"status": "needs_human", "evidence": {
        "stage": "horario_indisponivel", "desfecho": DESFECHO_AGENDA,
        "continuacao": COM}}
    txt = PP.format_result(job)
    checar("acabou de ser ocupado" in txt and "1) Loja Exemplo Centro" in txt
           and "25/09: 08:00" in txt, "horario_indisponivel: as opcoes atuais vao junto", txt[:500])
    checar("escolha_agenda" in txt, "e o agente aprende como mandar a escolha de volta")


def g8_vistoria_opcional() -> None:
    print("\n[G8-vistoria] link x loja, com e sem continuacao")
    for tipo in ("vistoria_opcional", "decidir_vistoria"):
        com = PP.mensagem_do_desfecho({"tipo": tipo, "codigo_atendimento": "66666666"},
                                      {"possivel": True, "acao_esperada": "vistoria"})
        sem = PP.mensagem_do_desfecho({"tipo": tipo, "codigo_atendimento": "66666666"})
        checar("link no celular" in com and "levar o carro numa loja" in com
               and "continuo" in com, f"'{tipo}' COM: pergunta link x loja e continua", com)
        checar("continuo" not in sem and "equipe" in sem,
               f"'{tipo}' SEM: pergunta, e a equipe registra", sem)
        checar(_limpa(com) and _limpa(sem), f"'{tipo}': texto limpo")
    checar(PP.resumo_da_tela_desconhecida({"desfecho": {"tipo": "agendado",
                                                        "titulo_portal": "x"}}) is None,
           "'agendado' e desfecho CONHECIDO: nao vai para a fila de aprendizado")


if __name__ == "__main__":
    print("=" * 72)
    print("G8 — as mensagens da continuacao")
    print("=" * 72)
    g8_o_agendado_e_exato()
    g8_a_agenda_com_horarios()
    g8_as_paradas_com_e_sem_continuacao()
    g8_as_paradas_novas()
    g8_vistoria_opcional()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
