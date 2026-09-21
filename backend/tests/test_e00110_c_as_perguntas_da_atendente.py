# -*- coding: utf-8 -*-
"""G8 — tudo o que a atendente humana pergunta cabe num slot do produto.

SPEC-EXTRA-001.10 P1-3/P1-4.

## 📊 A CONTAGEM, feita por este executor em 20/09/2026

Comando: `python -c` com `zipfile` sobre `word/document.xml` do .docx de intake.

```
64 parágrafos · 8 blocos de peça · 53 ocorrências · 22 SLOTS distintos
24 linhas de pergunta = 23 perguntas distintas + a PLACA (que vem da apólice)
```

📊 **Como os três números se reconciliam** (CLAUDE.md §12.1):

```
22  slots do produto           a resposta mora em 22 campos
+1  'vidro fixo' × 'sobe e desce'   duas linhas do roteiro, UM slot
+1  a placa                    o roteiro pede; o produto NÃO pergunta (§8.3 do mapa)
--
24  linhas de pergunta  ⇒  23 perguntas distintas ao segurado, mais a placa
```

O **23** da proposta é este mesmo número por outro caminho. O **20** do
diagnóstico não contava a placa nem separava fixo × sobe-e-desce. 🔴 A contagem
deste executor vence (SPEC §6 G8), e o gate passou a medi-la a cada rodada em
vez de guardar um número escrito à mão.

## 🔴 Por que o teste lê o .docx em tempo de execução

O arquivo é INTAKE — ele não é versionado (`docs/intake/` fica fora do
repositório de código). Congelar a lista aqui dentro faria o guarda provar uma
cópia de 20/09 para sempre, e o dia em que a atendente acrescentasse uma
pergunta ninguém saberia. Sem o arquivo, o teste **pula e diz por quê** — um
guarda que mente sobre ter rodado é pior que um guarda ausente.

## 🔴 E quem responde é o MOTOR (CLAUDE.md §9.4)

Nada aqui olha para `_ESPECIFICAS_POR_IDENTIDADE` com um regex. Cada pergunta do
roteiro é conferida chamando `o_que_falta` / `especificas_da_peca` com o texto
da peça — que é o caminho que o produto percorre de verdade.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services import perguntas_do_portal_de_vidros as P  # noqa: E402

PASS = FAIL = 0

DOCX = os.path.join(
    RAIZ, "..", "docs", "intake", "materiais", "portal-vidros",
    "PERGUNTAS QUE HUMANO FAZ PARA PORTAL DE VIDROS.docx")


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:300] if extra else ""))


def _dobrar(texto: str) -> str:
    cru = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join("".join(c if c.isalnum() else " " for c in cru).lower().split())


def paragrafos_do_docx(caminho: str) -> list:
    """Os parágrafos, na ordem. Sem python-docx: zipfile + o XML, que sempre há."""
    with zipfile.ZipFile(caminho) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    saida = []
    for bloco in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        texto = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", bloco, re.S))
        texto = (texto.replace("&amp;", "&").replace("&lt;", "<")
                 .replace("&gt;", ">").replace("&quot;", '"'))
        saida.append(texto.strip())
    return saida


# --------------------------------------------------------------------------
# O MAPA: o que o roteiro pergunta -> em que SLOT do produto a resposta mora
# --------------------------------------------------------------------------
# ⚠️ A chave é um FRAGMENTO dobrado (sem acento, minúsculo). Fragmento, e não a
# frase inteira, porque o .docx junta duas perguntas no mesmo parágrafo cinco
# vezes — e porque a atendente reescreve a mesma pergunta com palavras
# ligeiramente diferentes em blocos diferentes.
#
# `None` = a resposta NÃO vem do segurado (sai da apólice/InfoCap).
MAPA = {
    "placa": None,                                  # 📊 vem da InfoCap (§8.3 do mapa)
    "data da ocorrencia": P.DATA_DO_DANO,
    "ocorreu em rodovia ou area urbana": P.ONDE_OCORREU,
    "relato de como ocorreu": P.COMO_OCORREU,
    "como ocorreu": P.COMO_OCORREU,
    "informar a cidade para troca": P.CIDADE_PARA_O_SERVICO,
    "cidade para realizacao dos servicos": P.CIDADE_PARA_O_SERVICO,
    "cidade para troca": P.CIDADE_PARA_O_SERVICO,
    "posicao da trinca": P.POSICAO_DO_TRINCADO,
    "vidro tem sensor de chuva": P.SENSOR_DE_CHUVA,
    "possui faixa degrade": P.FAIXA_DEGRADE,
    "trinca esta maior ou menor": P.TAMANHO_DO_TRINCADO,
    "sensor de direcao mudanca de faixa": P.SENSOR_DE_DIRECAO_OU_FAIXA,
    "capa tem pintura": P.CAPA_PINTADA_OU_FOSCA,
    "lado danificado": P.LADO_MOTORISTA_OU_CARONA,
    "informar lado direito carona esquerdo motorista": P.LADO_MOTORISTA_OU_CARONA,
    "vidro lado direito carona ou esquerdo motorista": P.LADO_MOTORISTA_OU_CARONA,
    "tem pisca no retrovisor": P.RETROVISOR_TEM_PISCA,
    "regulagem e manual ou eletrica": P.REGULAGEM_DO_RETROVISOR,
    "capa ainda esta na peca": P.CAPA_AINDA_NA_PECA,
    "bipartida": P.LANTERNA_BIPARTIDA_ONDE,
    "vidro tem pelicula": P.PELICULA,
    "informar se tem pelicula": P.PELICULA,
    "vidro porta dianteira ou traseira": P.PORTA_DIANTEIRA_OU_TRASEIRA,
    "informar se e vidro fixo": P.VIDRO_FIXO_OU_SOBE_DESCE,
    "informar se e vidro sobe e desce": P.VIDRO_FIXO_OU_SOBE_DESCE,
    "para choque dianteiro ou traseiro": P.PARA_CHOQUE_DIANTEIRO_OU_TRASEIRO,
    "quais sao as pecas": P.PECAS_LATARIA,
    "danos deverao ser do mesmo evento": P.LATARIA_MESMO_EVENTO,
    "desembacador termico": P.VIGIA_DESEMBACADOR_TERMICO,
}

#: Os cabeçalhos de bloco -> o texto de peça que o produto recebe do segurado.
#: ⚠️ Casamento EXATO (o parágrafo inteiro), senão "Para brisa" casaria dentro
#: de "Reparo em para choque".
FAMILIAS = {
    "para brisa": "para-brisa",
    "troca de retrovisor": "retrovisor",
    "troca de lanterna": "lanterna",
    "troca de farol": "farol",
    "vidros de portas": "vidro de porta",
    "reparo em para choque": "para-choque",
    "reparo lataria pintura pequenos reparos": "lataria",
    "vidro traseiro vigia": "vigia",
}

#: O que NÃO é pergunta: saudação, observação de negócio, opção de resposta e
#: as duas linhas de recado de quem mandou o arquivo.
NAO_E_PERGUNTA = (
    "esse documento foi passado", "nos ja devemos ter", "link de vistoria",
    "me chamo", "seguem as perguntas", "troca de pecas individuais",
    "a seguradora que indica a loja", "as pecas nao sao trocadas",
    "mantem a estabilidade do veiculo", "nao sendo possivel juntar danos",
    "possibilidade reparo sem precisar trocar",
)


def _pula(motivo: str) -> None:
    print("\n" + "=" * 72)
    print("  PULADO — " + motivo)
    print("  Este guarda le o .docx de INTAKE, que nao e versionado.")
    print("  Sem o arquivo ele NAO afirma nada: um guarda que mente sobre ter")
    print("  rodado e pior que um guarda ausente.")
    print("=" * 72)
    sys.exit(0)


def g8_cada_pergunta_do_roteiro_cabe_num_slot() -> None:
    print("\n[G8] cada pergunta do roteiro da atendente casa com um slot")

    paragrafos = paragrafos_do_docx(DOCX)
    checar(len(paragrafos) >= 50,
           f"o .docx foi lido ({len(paragrafos)} paragrafos)", len(paragrafos))

    familia_corrente = ""
    por_familia = {}     # familia -> {slot, ...}
    perguntas_vistas = 0
    slots_vistos = set()
    fragmentos_usados = set()
    sobraram = []

    for bruto in paragrafos:
        dobrado = _dobrar(bruto)
        if not dobrado:
            continue
        if dobrado in FAMILIAS:
            familia_corrente = FAMILIAS[dobrado]
            por_familia.setdefault(familia_corrente, set())
            continue
        # ⚠️ Os fragmentos do MAPA vêm PRIMEIRO. O .docx gruda pergunta em
        # observação cinco vezes ("Obs: os danos deverão ser do mesmo evento…"),
        # e descartar a linha pela observação apagaria a pergunta junto.
        achou_algo = False
        for fragmento, slot in MAPA.items():
            if fragmento in dobrado:
                achou_algo = True
                perguntas_vistas += 1
                fragmentos_usados.add(fragmento)
                if slot:
                    slots_vistos.add(slot)
                dobrado = " ".join(dobrado.replace(fragmento, " ").split())
                if slot and familia_corrente:
                    por_familia.setdefault(familia_corrente, set()).add(slot)
        if achou_algo:
            continue
        if any(ig in dobrado for ig in NAO_E_PERGUNTA):
            continue   # saudação, recado de quem mandou o arquivo, opção de resposta
        # 🔴 O QUE SOBROU é o guarda de verdade: se restou texto e nenhum
        # fragmento o explicou, a atendente pergunta algo que o produto não
        # sabe coletar — e o segurado descobriria isso dentro do portal.
        if len(dobrado) > 12:
            sobraram.append(bruto)

    checar(not sobraram,
           "NENHUMA pergunta do roteiro ficou sem slot",
           " | ".join(sobraram[:5]))

    checar(not (set(MAPA) - fragmentos_usados),
           "e TODO fragmento do mapa foi exercido pelo arquivo de verdade",
           f"nunca casaram: {sorted(set(MAPA) - fragmentos_usados)} — um mapa com "
           "entrada morta afirma cobertura que nao existe")

    # 📊 A CONTAGEM DESTE EXECUTOR, medida aqui e reproduzível a cada rodada.
    # Ela vence os "20"/"23" citados (SPEC §6 G8) e explica os dois:
    #
    #   22 SLOTS distintos (a resposta mora em 22 campos do produto)
    #   +1  'vidro fixo' e 'vidro sobe e desce' sao DUAS linhas do roteiro e UM slot
    #   +1  a PLACA, que o roteiro pede e o produto NAO pergunta (sai da apolice)
    #   ---
    #   24 linhas de pergunta · 23 perguntas DISTINTAS ao segurado + a placa
    #
    # O "23" da proposta e este mesmo numero por outro caminho; o "20" do
    # diagnostico nao contava a placa nem separava fixo/sobe-desce.
    checar(len(slots_vistos) == 22,
           f"📊 {len(slots_vistos)} slots distintos casaram com o roteiro",
           sorted(slots_vistos))
    print(f"     📊 CONTAGEM DESTE EXECUTOR (20/09/2026): {len(paragrafos)} paragrafos · "
          f"8 blocos · {len(slots_vistos)} slots · {perguntas_vistas} ocorrencias · "
          f"24 linhas de pergunta = 23 distintas + a placa (que vem da apolice)")

    # ------------------------------------------------------------------
    # 🔴 E AGORA O MOTOR. Nada acima provou que o produto PERGUNTA isso —
    # provou que existe uma constante com esse nome. Aqui o texto da peça
    # entra em `o_que_falta` / `especificas_da_peca`, que é o caminho real.
    # ------------------------------------------------------------------
    print("\n[G8-motor] e o MOTOR devolve esses mesmos slots para cada familia")
    for familia, slots in sorted(por_familia.items()):
        if not slots:
            continue
        do_motor = {p.campo for p in P.o_que_falta(familia, {})}
        do_motor |= {p.campo for p in P.especificas_da_peca(familia)}
        faltando = sorted(slots - do_motor)
        checar(not faltando,
               f"'{familia}': o motor cobra os {len(slots)} slots do roteiro",
               f"nao cobrados: {faltando} · motor devolveu {sorted(do_motor)}")

    # 🔴 CONTROLE DO CONTROLE: o motor tem de conseguir NÃO devolver. Se ele
    # devolvesse todos os slots do produto para qualquer peça, o bloco acima
    # passaria sem provar nada sobre família nenhuma.
    do_farol = {p.campo for p in P.especificas_da_peca("farol")}
    do_parabrisa = {p.campo for p in P.especificas_da_peca("para-brisa")}
    checar(do_farol != do_parabrisa and not (do_parabrisa <= do_farol),
           "CONTROLE: familias diferentes dao perguntas DIFERENTES",
           f"farol={sorted(do_farol)} parabrisa={sorted(do_parabrisa)}")
    checar(P.PELICULA not in do_parabrisa,
           "CONTROLE: pelicula NAO e perguntada a quem quebrou o para-brisa",
           "perguntar de pelicula a quem quebrou o para-brisa e ruido")


def g8_o_destino_de_cada_resposta_esta_declarado() -> None:
    """Catálogo × questionário × reparo — e o que ainda não foi visto numa tela."""
    print("\n[G8-destino] para onde vai cada resposta")

    validos = (P.DESTINO_CATALOGO, P.DESTINO_QUESTIONARIO, P.DESTINO_REPARO)
    todas = list(P.universais())
    for perguntas in P.catalogo_de_familias().values():
        todas.extend(perguntas)
    checar(all(p.destino in validos for p in todas),
           f"as {len(todas)} perguntas do catalogo tem destino declarado",
           str([(p.campo, p.destino) for p in todas if p.destino not in validos]))

    catalogo = [p.campo for p in todas if p.destino == P.DESTINO_CATALOGO]
    checar(len(catalogo) >= 8,
           f"📊 {len(catalogo)} perguntas sao de CATALOGO (escolhem o item coberto)",
           str(catalogo))

    reparo = [p for p in todas if p.destino == P.DESTINO_REPARO]
    checar(len(reparo) == 1 and reparo[0].campo == P.ACEITA_REPARO,
           "e o REPARO e um destino so dele (vira PUT alterar-reparo)",
           str([p.campo for p in reparo]))

    # 🔴 O que ainda NÃO foi visto numa tela tem de estar marcado. 📊 A captura
    # de 20/09 trouxe TRES perguntas de para-brisa e nao perguntou chuva nem
    # degrade: elas valem (escolhem o vidro) e nao vao ao questionario.
    nao_confirmadas = {p.campo for p in todas if not p.confirmada}
    for campo in (P.SENSOR_DE_CHUVA, P.FAIXA_DEGRADE):
        checar(campo in nao_confirmadas,
               f"'{campo}' esta marcada NAO-CONFIRMADA (nenhuma tela a exibiu)",
               "afirmar que o portal a pergunta seria inventar")
    for campo in (P.POSICAO_DO_TRINCADO, P.TAMANHO_DO_TRINCADO,
                  P.SENSOR_DE_DIRECAO_OU_FAIXA):
        checar(campo not in nao_confirmadas,
               f"CONTROLE: '{campo}' e MEDIDA (perguntas 5, 8 e 140 de 20/09/2026)",
               "se tudo fosse nao-confirmado, a marca nao distinguiria nada")


def g8_as_familias_novas_nao_travam_o_que_nao_devem() -> None:
    """Perguntar mais não pode significar travar mais — exceto onde é preciso."""
    print("\n[G8-trava] o que passou a TRAVAR, e o que so e coletado")

    from app.agents.tools import portal_params as PP

    trava = set(PP.TRANSPORTAVEIS)
    checar(P.CIDADE_PARA_O_SERVICO in trava,
           "a cidade do servico TRAVA (P0-5)")
    checar(P.ACEITA_REPARO in trava,
           "a decisao do reparo TRAVA (P0-6/N-2) — o portal para depois do numero")
    checar(P.PECAS_LATARIA in trava,
           "a lista de pecas da lataria TRAVA (P1-5) — ela vai no PATCH")

    # 🔴 E o resto NÃO trava. Travar numa pergunta de catálogo faria o agente
    # perguntar "a capa tem pisca?" e recusar o acionamento de quem não sabe.
    for campo in (P.CAPA_PINTADA_OU_FOSCA, P.RETROVISOR_TEM_PISCA,
                  P.REGULAGEM_DO_RETROVISOR, P.CAPA_AINDA_NA_PECA,
                  P.LANTERNA_BIPARTIDA_ONDE, P.SENSOR_DE_CHUVA, P.FAIXA_DEGRADE,
                  P.VIDRO_FIXO_OU_SOBE_DESCE, P.VIGIA_DESEMBACADOR_TERMICO,
                  P.LATARIA_MESMO_EVENTO, P.PARA_CHOQUE_DIANTEIRO_OU_TRASEIRO):
        checar(campo not in trava, f"'{campo}' e COLETADO mas NAO trava",
               "travar numa pergunta de catalogo recusaria quem nao sabe responder")

    # E a prova de comportamento, não de lista: o reparo só é cobrado de quem
    # quebrou o para-brisa.
    faltam_parabrisa = {p.campo for p in P.o_que_falta("para-brisa", {})}
    faltam_retrovisor = {p.campo for p in P.o_que_falta("retrovisor", {})}
    checar(P.ACEITA_REPARO in faltam_parabrisa,
           "o reparo e cobrado de quem quebrou o PARA-BRISA")
    checar(P.ACEITA_REPARO not in faltam_retrovisor,
           "CONTROLE: e NAO e cobrado de quem quebrou o retrovisor",
           "perguntar de reparo de vidro a quem quebrou o espelho e ruido")
    faltam_lataria = {p.campo for p in P.o_que_falta("lataria", {})}
    checar(P.PECAS_LATARIA in faltam_lataria and P.PECAS_LATARIA not in faltam_parabrisa,
           "e a lista de pecas so e cobrada na LATARIA",
           f"lataria={sorted(faltam_lataria)}")


def g8_o_vocabulario_unico_continua_mandando() -> None:
    """🔴 ATUALIZADO em 20/09/2026 — P-E00110-C-01 (CLAUDE.md §9.3).

    O FATO que este bloco guardava MUDOU, e mudou porque foi consertado: 📊 até
    aqui `identidade_peca("lataria")` e `identidade_peca("para-choque")`
    devolviam conjunto VAZIO, e por isso existia uma tabela local em
    `perguntas_do_portal_de_vidros` para falar onde o vocabulário ficava mudo.

    As duas famílias entraram em `_PECAS` e **a tabela local morreu**. A lição
    não morreu com ela: o que se testa continua sendo *"existe UM vocabulário"*
    — agora provando que é ele quem responde pelas duas famílias novas, e que a
    ambiguidade continua sendo ambiguidade.
    """
    print("\n[G8-precedencia] ha UM vocabulario, e ele nomeia as duas familias novas")

    from portal_worker.journeys.vidros_lanternas import identidade_peca

    # Tudo o que o vocabulário único nomeia continua vindo DELE.
    for texto in ("para-brisa", "vidro de porta", "retrovisor", "farol",
                  "lanterna", "vigia", "teto"):
        do_vocabulario = sorted(identidade_peca(texto))
        checar(do_vocabulario and P.familia_da_peca(texto) == do_vocabulario[0],
               f"'{texto}': quem decide e o vocabulario unico ({do_vocabulario})",
               P.familia_da_peca(texto))

    # E as duas famílias novas vêm do MESMO lugar que todas as outras.
    for texto, familia in (("para-choque", "para_choque"), ("lataria", "lataria"),
                           ("preciso reparar a funilaria", "lataria"),
                           ("amassei a porta e o paralama", "lataria")):
        checar(sorted(identidade_peca(texto)) == [familia],
               f"'{texto}': o vocabulario unico responde '{familia}'",
               sorted(identidade_peca(texto)))
        checar(P.familia_da_peca(texto) == familia,
               f"'{texto}' vira '{familia}', e pelo vocabulario unico",
               P.familia_da_peca(texto))

    # 🔴 O par que prova que a lataria não atropelou a vidraçaria: a MESMA
    # palavra "porta", com e sem a palavra "vidro", dá famílias opostas.
    checar(P.familia_da_peca("quebrou o vidro da porta") == "lateral",
           "CONTROLE: 'quebrou o VIDRO da porta' continua sendo vidro lateral",
           P.familia_da_peca("quebrou o vidro da porta"))

    # E a ambiguidade continua sendo ambiguidade.
    checar(P.familia_da_peca("a luz quebrou") == "",
           "CONTROLE: 'a luz quebrou' continua AMBIGUA (farol x lanterna)",
           "um vocabulario que desempata sozinho escolhe a peca errada calado")
    checar(P.familia_da_peca("quebrou o vidro") == "",
           "CONTROLE: 'quebrou o vidro' continua nao nomeando peca")


def g8_toda_pergunta_MEDIDA_do_portal_tem_slot_cobrado_antes() -> None:
    """🔴 O que o portal PERGUNTA tem de estar coletado ANTES da fronteira A.

    A razão é a mais cara do produto: **não existe journey de continuação.** O
    `token_autorizacao` vive só em memória e `safe_to_retry_open` é `False`
    depois do `POST /atendimentos` — então uma pergunta do questionário que
    falte não é "pergunta ao segurado e chama de novo": é um atendimento
    terminado à mão, dentro do portal, com o protocolo já emitido.

    📊 As perguntas que os 4 HAR de 20/09/2026 mostraram, por família:

        parabrisa  P5   SR.(A), PODERIA INFORMAR A POSICAO DO TRINCADO ?
                   P8   O TRINCADO ESTÁ MAIOR OU MENOR QUE 10 CM?
                   P140 O VEICULO POSSUI SENSOR DE DIREÇÃO/MUDANÇA DE FAIXA?
        lateral    P4   O VIDRO DANIFICADO TEM PELÍCULA DE CONTROLE SOLAR?
                   P39  O VIDRO DANIFICADO É DA PORTA DIANTEIRA OU TRASEIRA?
                   P35  QUAL O LADO DO ITEM DANIFICADO?
        lanterna   P35  QUAL O LADO DO ITEM DANIFICADO?
        lataria    (nenhuma — 📊 zero chamadas a /questionarios na captura)
    """
    print("\n[G8-questionario] toda pergunta MEDIDA tem slot, e o slot TRAVA")

    from app.agents.tools.portal_params import trava_o_pedido

    MEDIDAS = {
        "parabrisa": (("P5", "posicao_do_trincado"),
                      ("P8", "tamanho_do_trincado"),
                      ("P140", "sensor_de_direcao_ou_faixa")),
        "lateral": (("P4", "pelicula"),
                    ("P39", "porta_dianteira_ou_traseira"),
                    ("P35", "lado_motorista_ou_carona")),
        "lanterna": (("P35", "lado_motorista_ou_carona"),),
        "lataria": (),
    }
    for familia, pares in MEDIDAS.items():
        campos = {p.campo: p for p in P.catalogo_de_familias().get(familia, ())}
        for codigo, slot in pares:
            p = campos.get(slot)
            checar(p is not None,
                   f"{familia}/{codigo}: existe o slot `{slot}`", sorted(campos))
            if p is None:
                continue
            checar(p.confirmada is True,
                   f"{familia}/{codigo}: o slot esta CONFIRMADO (foi visto numa tela)")
            checar(p.de_quem == P.DO_SEGURADO,
                   f"{familia}/{codigo}: e a resposta e do SEGURADO")
            checar(trava_o_pedido(p),
                   f"{familia}/{codigo}: e ele TRAVA o pedido antes da fronteira A",
                   "sem travar, a falta dele vira atendimento terminado a mao")
    # 📊 A lataria não tem questionário — e o guarda prova que isso é medido, e
    # não esquecimento: nenhuma pergunta de questionário na família.
    do_questionario = [p.campo for p in P.catalogo_de_familias().get("lataria", ())
                       if p.destino == P.DESTINO_QUESTIONARIO]
    checar(not do_questionario,
           "lataria: NENHUMA pergunta de questionario (📊 zero /questionarios na captura)",
           do_questionario)

    # 🔴 E o par que impede a régua de virar "cobra tudo": o que NENHUMA captura
    # confirmou continua sendo coletado SEM travar.
    nao_confirmadas = [(f, p.campo) for f, ps in P.catalogo_de_familias().items()
                       for p in ps if not p.confirmada and p.de_quem == P.DO_SEGURADO]
    checar(nao_confirmadas and all(not trava_o_pedido(p)
                                   for f, ps in P.catalogo_de_familias().items()
                                   for p in ps
                                   if not p.confirmada and p.de_quem == P.DO_SEGURADO),
           f"CONTROLE: as {len(nao_confirmadas)} perguntas NAO confirmadas nao travam",
           nao_confirmadas)

    # E as perguntas do portal que NÃO têm slot nenhum: o inventário honesto.
    # 📊 Nas 4 capturas, todas as perguntas feitas têm slot. A família `vigia`
    # tem slots e nenhuma captura — é o inverso, e está declarado.
    vigia = [p.campo for p in P.catalogo_de_familias().get("vigia", ())]
    checar(vigia and all(not p.confirmada
                         for p in P.catalogo_de_familias().get("vigia", ())),
           "vigia: tem perguntas, e NENHUMA confirmada (nenhuma captura dela)",
           vigia)


if __name__ == "__main__":
    print("=" * 72)
    print("G8 — o roteiro da atendente humana cabe no produto")
    print("=" * 72)
    if not os.path.exists(DOCX):
        _pula(f"arquivo nao encontrado: {os.path.normpath(DOCX)}")
    g8_cada_pergunta_do_roteiro_cabe_num_slot()
    g8_o_destino_de_cada_resposta_esta_declarado()
    g8_as_familias_novas_nao_travam_o_que_nao_devem()
    g8_o_vocabulario_unico_continua_mandando()
    g8_toda_pergunta_MEDIDA_do_portal_tem_slot_cobrado_antes()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
