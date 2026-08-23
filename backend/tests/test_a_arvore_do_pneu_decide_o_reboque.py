# -*- coding: utf-8 -*-
"""🔴 O ESCOPO SEGUIA O NOME DO SUBSERVIÇO — SPEC-084.1, ONDA F.

📊 23/08/2026. Duas seguradoras, o mesmo defeito, e ele é invisível para quem
lê só o nome da rota:

```
zurich × auto × guincho   "Mais de 1 pneu está danificado?"        ÓRFÃ
zurich × auto × guincho   "Possui estepe, macaco e chave de rodas?" ÓRFÃ
porto × residencial       "qual é o nome de quem estará na residência?" ÓRFÃ ×2
porto × residencial       "posso te ligar em qualquer um deles?"    ÓRFÃ
```

🔴 **A árvore do PNEU é quem decide se o serviço é borracheiro ou REBOQUE.** A
sessão real da zurich que chega ao número da assistência 71791336 percorre essa
árvore inteira — e tem de percorrer. Escopar os passos só em `pneu` deixava-os
mudos na rota por onde eles realmente chegam.

⚠️ E na Porto residencial o filtro era uma lista **de AUTO** enquanto a própria
`notes` do passo contava as três telas residenciais: *"auto 6/6 · residencial
3/3"*. Documento a contar uma coisa e código a filtrar outra (§9.3).

🔴 **E a mesma frase, duas renderizações**: *"posso te ligar em qualquer um
deles?"* vem NUMERADA no corredor de auto e como LISTA no residencial. Mandar
`"1"` numa lista é apertar uma tecla que não existe — a mesma família do
`pane_detalhe` da ONDA C.

Este arquivo chama o MOTOR (§9.4). As telas são copiadas do corpus versionado.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import importlib.util as _ilu  # noqa: E402


def _mod(nome, arquivo):
    sp = _ilu.spec_from_file_location(
        nome, os.path.join(RAIZ, "app", "services", arquivo))
    m = _ilu.module_from_spec(sp)
    sys.modules[nome] = m
    sp.loader.exec_module(m)
    return m


CP = _mod("app.services.corridor_playbooks", "corridor_playbooks.py")
IDS = _mod("app.services.insurer_dispatch_service", "insurer_dispatch_service.py")

OK = FAIL = 0
Q = chr(10)


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


# ── telas REAIS, copiadas do corpus ────────────────────────────────────────
Z_MAIS_DE_UM = ("Mais de 1 pneu está danificado?" + Q + Q + "*1* - Sim" + Q +
                "*2* - Não")
Z_ESTEPE = ("Possui estepe, macaco e chave de rodas?" + Q + Q + "*1* - Sim" +
            Q + "*2* - Não")
Z_ESCOPO = ("Aqui você vai *acionar a assistência 24h,* que atende reboque, "
            "socorro mecânico, chaveiro, pane seca ou troca de pneu.")
Z_TELEFONES = ("Para acompanhar o status da Assistência 24h, entre em contato "
               "pelos telefones: *Atendimento nacional:* 0800 729 1400")
P_NOME_RESID = ("Nesse caso, qual é o nome de quem estará na residência?" + Q +
                Q + "Lembrando que é necessário ter mais de 18 anos de idade "
                "para acompanhar o serviço.")
P_LIGAR_LISTA = ("Se for necessário, posso te ligar em qualquer um deles?" + Q +
                 "Sim" + Q + "Não, apenas no primeiro" + Q +
                 "Apenas no segundo" + Q + "Nenhum dos dois")
P_GARANTIA = ("Esse serviço agendado tem direito a uma garantia de *90 dias* "
              "corridos.")
P_PECA = ("Se o prestador precisar de alguma peça, você tem até *20 dias "
          "corridos* para comprá-la e agendar o retorno do serviço.")
P_ALTERAR = ("Gostaria de alterar alguma informação?" + Q +
             "Não, está tudo correto" + Q + "Localização" + Q +
             "Quem estará no local" + Q + "Sair e não agendar" + Q + "Voltar")

CASO = {
    "titular_cpf": "11122233344", "veiculo_placa": "ABC1D23",
    "titular_nome": "Cliente", "local_atual": "Rua X, 100, Florianópolis, SC",
    "local_destino": "Oficina Y, São José, SC",
    "problema_descricao": "furei o pneu e o carro não anda", "quando": "agora",
    "telefone_contato": "48999998888", "pessoa_no_local": "Cliente",
    "endereco_numero": "100", "periodo_preferido": "manhã",
}


def sessao(ref, subservico, **extra):
    slots = dict(CASO)
    slots.update(extra)
    return IDS.new_dispatch_session(case_id="f-t", company_id="co",
                                    playbook_ref=ref, subservice=subservico,
                                    slots=slots)


def responder(s, tela):
    antes = len([t for t in s.get("transcript") or []
                 if t.get("direction") == "out"])
    s = IDS.handle_insurer_message(s, tela)
    saidas = [t.get("text") for t in s.get("transcript") or []
              if t.get("direction") == "out"]
    return s, (saidas[antes:] or [None])[-1]


print("=" * 74)
print("[1] 🔴 zurich/auto/guincho PERCORRE a árvore do pneu — e tem de percorrer")
print("=" * 74)

for tela, rotulo in ((Z_MAIS_DE_UM, "mais de 1 pneu danificado"),
                     (Z_ESTEPE, "possui estepe, macaco e chave de rodas")):
    s = IDS.start_dispatch(sessao("zurich-auto-whatsapp@v1", "guincho",
                                  pneus_danificados_opcao="2",
                                  estepe_opcao="1"))
    s, r = responder(s, tela)
    certo(r is not None,
          f"🔴 zurich/auto/guincho responde: {rotulo}", f"respondeu {r!r}")

# 🔴 CONTROLE: e a rota de PNEU continua vendo as mesmas telas — o widen
#    acrescentou, não mudou de dono.
certo(CP.match_ura_step(CP.get_playbook("zurich-auto-whatsapp@v1"), Z_ESTEPE,
                        subservice="pneu") is not None,
      "🔴 CONTROLE: a rota de PNEU continua vendo a tela do estepe")
# 🔴 CONTROLE 2: e uma rota que NÃO percorre essa árvore continua sem ver.
certo(CP.match_ura_step(CP.get_playbook("zurich-auto-whatsapp@v1"), Z_ESTEPE,
                        subservice="vidros") is None,
      "🔴 CONTROLE: `vidros` continua sem ver a tela do estepe — o escopo "
      "cresceu onde a URA leva, não em todo lugar")

s = IDS.start_dispatch(sessao("zurich-auto-whatsapp@v1", "guincho"))
s, r = responder(s, Z_ESCOPO)
certo(r is None, "🔴 e o texto de ESCOPO da zurich é aviso — o corredor não "
      "responde por cima dele", f"respondeu {r!r}")

print()
print("=" * 74)
print("[2] 🔴 porto/residencial: quem espera na RESIDÊNCIA também tem nome")
print("=" * 74)

s2 = IDS.start_dispatch(sessao("porto-residencial-whatsapp@v1", "encanador"))
s2, r2 = responder(s2, P_NOME_RESID)
certo(r2 == "Cliente",
      "🔴 porto/residencial/encanador responde o NOME de quem espera — a lista "
      "de escopo era só de auto enquanto a `notes` contava as residenciais",
      f"respondeu {r2!r}")

s3 = IDS.start_dispatch(sessao("porto-residencial-whatsapp@v1", "encanador"))
s3, r3 = responder(s3, P_LIGAR_LISTA)
certo(r3 == "Sim",
      "🔴 e responde a LISTA com o RÓTULO — no corredor de auto a MESMA frase "
      "vem numerada, e ali `1` é a resposta certa", f"respondeu {r3!r}")

# 🔴 CONTROLE: a versão NUMERADA da mesma frase, no corredor de AUTO,
#    continua respondendo o NÚMERO. Se as duas respondessem igual, uma estaria
#    errada.
P_LIGAR_NUM = ("Se for necessário, posso te ligar em qualquer um deles?" + Q +
               "*1* - Sim" + Q + "*2* - Não, apenas no primeiro" + Q +
               "*3* - Apenas no segundo")
s4 = IDS.start_dispatch(sessao("porto-auto-whatsapp@v1", "tecnico"))
s4, r4 = responder(s4, P_LIGAR_NUM)
certo(r4 == "1",
      "🔴 CONTROLE: a versão NUMERADA, no corredor de auto, responde o NÚMERO",
      f"respondeu {r4!r}")

print()
print("=" * 74)
print("[3] 🔴 P1 — o FREIO da porto residencial não armava em UMA tela sequer")
print("=" * 74)

pb_pr = CP.get_playbook("porto-residencial-whatsapp@v1")
certo(CP.detect_finalize_anchor(pb_pr, P_ALTERAR) is not None,
      "🔴 a tela que CONFIRMA a solicitação arma o freio",
      f"detect_finalize_anchor devolveu "
      f"{CP.detect_finalize_anchor(pb_pr, P_ALTERAR)!r}")

# 🔴 CONTROLE: e a tela de GARANTIA, que é aviso, NÃO arma. Um freio que arma
#    em tudo para o produto inteiro.
certo(CP.detect_finalize_anchor(pb_pr, P_GARANTIA) is None
      and CP.detect_finalize_anchor(pb_pr, P_PECA) is None,
      "🔴 CONTROLE: telas de AVISO (garantia, peça) NÃO armam o freio")

# 🔴 CONTROLE 2: e o `finalize_abort_reply` deste playbook é uma opção DESTA
#    tela — era a intenção escrita que faltava a âncora.
certo(str(pb_pr.get("finalize_abort_reply") or "") in P_ALTERAR,
      "🔴 CONTROLE: o `finalize_abort_reply` é, literalmente, uma opção da "
      "tela que agora arma o freio",
      f"{pb_pr.get('finalize_abort_reply')!r}")

print()
print("=" * 74)
print("[4] E as regras que o segurado precisa ouvir estão escritas")
print("=" * 74)

for ref, sv, trecho in (
        ("porto-residencial-whatsapp@v1", "encanador",
         "pressurização"),
        ("porto-residencial-whatsapp@v1", "chaveiro",
         "instalação de fechaduras"),
        ("zurich-auto-whatsapp@v1", "guincho", "acionar o seguro")):
    sub = (CP.get_playbook(ref).get("subservices") or {}).get(sv) or {}
    texto = " ".join(sub.get("regras_para_o_cliente") or [])
    certo(trecho in texto, f"🔴 {ref.split('-')[0]}/{sv}: a EXCLUSÃO está "
          f"escrita ({trecho!r})", f"{texto[:80]!r}")

print()
print("=" * 74)
print("[5] 🔴 BRADESCO: a tela que separa guincho de bateria vem DEPOIS")
print("=" * 74)
print("     (as 4 rotas eram SEM_CORPUS por um desempate que ninguem lia)")

B_MENU = ("Entendi, mas pra eu te ajudar, preciso entender qual o problema com "
          "o seu carro:" + Q + "*1* - Pane ( _ex. bateria, motor, cambio_ )" +
          Q + "*2* - Acidente" + Q + "*3* - Problemas com pneus")
B_DESEMPATE = ("Ok! Preciso confirmar alguns dados pra enviar o melhor "
               "servico, ta? Me conta o que aconteceu:" + Q +
               "*1* - O veiculo estava estacionado e nao liga" + Q +
               "*2* - O veiculo estava andando e parou de funcionar")
B_CONFIRMA = ("So vamos confirmar as informacoes" + Q + Q +
              "Origem: *Estrada X, Florianopolis - SC*" + Q + Q +
              "Destino do veiculo: *Rua Y, Sao Jose - SC*" + Q +
              "Posso confirmar a abertura da assistencia?")

# 🔴 A tela de confirmacao ARMA O FREIO -- e e por isso que responde-la e
#    seguro: em LIVE ela so e respondida depois da aprovacao humana.
pb_bd = CP.get_playbook("bradesco-auto-whatsapp@v1")
certo(CP.detect_finalize_anchor(pb_bd, B_CONFIRMA) is not None,
      "🔴 bradesco: a tela que confirma a abertura ARMA o freio",
      str(CP.detect_finalize_anchor(pb_bd, B_CONFIRMA)))

sb = IDS.start_dispatch(sessao("bradesco-auto-whatsapp@v1", "guincho"))
sb, rb = responder(sb, B_CONFIRMA)
certo(rb == "Sim",
      "🔴 e o corredor SABE responde-la depois de aprovada -- sem o passo, "
      "a tela conhecida caia no cerebro na hora mais cara da conversa",
      f"respondeu {rb!r}")

# 🔴 CONTROLE: o desempate e o que separa as duas rotas, e ele e uma tela
#    POSTERIOR. O menu anterior (tecla 1 = Pane) NAO decide -- e e por isso que
#    a tabela o mapeia para None de proposito.
import importlib.util as _ilu2
_spec = _ilu2.spec_from_file_location(
    "padroes_de_servico", os.path.join(RAIZ, "scripts", "padroes_de_servico.py"))
PS = _ilu2.module_from_spec(_spec)
sys.modules["padroes_de_servico"] = PS
_spec.loader.exec_module(PS)
PS.ligar_resolvedor(CP.canonical_subservice)

def _classifica(resposta_desempate):
    pares = [("in", CP._norm(B_MENU)), ("out", "1"),
             ("in", CP._norm(B_DESEMPATE)), ("out", resposta_desempate)]
    return PS.servico_da_sessao("bradesco", pares, pb_bd)

certo(_classifica("2")[0] == "guincho",
      "🔴 CONTROLE: 'estava andando e parou' -> GUINCHO",
      str(_classifica("2")))
certo(_classifica("1")[0] == "bateria",
      "🔴 CONTROLE: 'estava estacionado e nao liga' -> BATERIA — a MESMA "
      "tecla `1` do menu anterior, e desfechos diferentes",
      str(_classifica("1")))

# 🔴 CONTROLE DO CONTROLE: sem a tela de desempate, a tecla `1` do menu
#    continua NAO decidindo. Se decidisse, o desempate seria decorativo.
certo(PS.servico_da_sessao(
        "bradesco", [("in", CP._norm(B_MENU)), ("out", "1")], pb_bd)[0] is None,
      "🔴 CONTROLE: sem a tela posterior, a tecla `1` continua sem decidir")

print()
print("=" * 74)
print("[6] 🔴 TOKIO: o numero do turno 3 e do CHAT, nao do chamado")
print("=" * 74)

T_CPF = "Olá, Fulano - Corretora X! Digite o CPF/CNPJ do titular do Seguro."
T_TICKET = "Seu protocolo de atendimento é 68977599"
T_MENU = ("Clique no botão abaixo para acessar o menu de serviços do *Seguro "
          "Automóvel* 🚙")
T_LINK = ("Clique no link abaixo para solicitar ou acompanhar *ASSISTÊNCIA "
          "AUTOMÓVEL 24H E GUINCHO:* (Guincho, chaveiro, pane e pneu furado)")
T_ALGO_MAIS = ("Posso te ajudar em algo mais?" + Q + "Botão 1: Outro serviço" +
               Q + "Botão 2: Menu inicial" + Q + "Botão 3: Encerrar")

pb_tk = CP.get_playbook("tokio-auto-whatsapp@v1")

# 🔴 O QUE ESTE GUARDA PROTEGE, e vale mais que os pontos: a tokio manda um
#    numero no turno 3, ANTES de qualquer escolha de servico. Ele e o protocolo
#    do CHAT. Se `extract_capture_anchors` o colhesse como `protocol`, o
#    corredor encerraria dizendo "assistencia aberta, protocolo 68977599"
#    enquanto NADA foi aberto -- e o segurado ligaria com um numero que nao
#    existe.
certo(not (CP.extract_capture_anchors(pb_tk, T_TICKET) or {}).get("protocol"),
      "🔴 tokio: o numero do turno 3 NAO e colhido como protocolo",
      str(CP.extract_capture_anchors(pb_tk, T_TICKET)))

# 🔴 CONTROLE: e o mecanismo de captura FUNCIONA -- noutra seguradora, o
#    numero de verdade e colhido. Sem esta metade, um `protocol` sempre vazio
#    passaria igual.
certo((CP.extract_capture_anchors(
        CP.get_playbook("allianz-auto-whatsapp@v1"),
        "Protocolo: *52440449* Você receberá um link por SMS") or {}
       ).get("protocol") == "52440449",
      "🔴 CONTROLE: e o protocolo de VERDADE, noutra seguradora, e colhido")

for tela, rotulo in ((T_CPF, "pede o CPF/CNPJ"),
                     (T_MENU, "o menu de servicos do seguro auto"),
                     (T_ALGO_MAIS, "posso te ajudar em algo mais")):
    st = IDS.start_dispatch(sessao("tokio-auto-whatsapp@v1", "guincho"))
    st, rt = responder(st, tela)
    certo(rt is not None, f"🔴 tokio/auto/guincho responde: {rotulo}",
          f"respondeu {rt!r}")

st = IDS.start_dispatch(sessao("tokio-auto-whatsapp@v1", "guincho"))
st, rt = responder(st, T_LINK)
certo(rt is None,
      "🔴 e fica CALADO no link -- ele e o DESFECHO da tokio "
      "(`OUTCOME_ENCAMINHA`), nao uma pergunta", f"respondeu {rt!r}")

print()
print("=" * 74)
print("[7] PORTO residencial: o eletrodomestico em TRES paginas de menu")
print("=" * 74)

PE = [
    ("O que você precisa?" + Q + "Eletrodoméstico" + Q +
     "Reparo de produtos de linha branca" + Q + "Encanador" + Q + "Voltar",
     "o menu de servico da residencia"),
    ("O que você precisa?" + Q + "Conserto ou reparo" + Q +
     "Conversão de gás" + Q + "Contratar instalação" + Q + "Não encontrei",
     "conserto x conversao de gas x instalacao"),
    ("O conserto ou reparo é para o quê?" + Q + "Máquina de lavar roupa" + Q +
     "Lava e seca" + Q + "Secadora" + Q + "Mais opções",
     "a pagina 1 do menu de aparelhos"),
    ("O conserto ou reparo é para o quê?" + Q + "Geladeira expositora" + Q +
     "Geladeira" + Q + "Geladeira side by side" + Q + "Mais opções",
     "a pagina 2 do menu de aparelhos"),
]
for tela, rotulo in PE:
    sp2 = IDS.start_dispatch(sessao(
        "porto-residencial-whatsapp@v1", "eletrodomesticos",
        problema_descricao="a geladeira parou de gelar",
        eletrodomestico_opcao="Geladeira",
        # ⚠️ Os slots que o corredor da porto usa nesta arvore. Sem eles quem
        #    responderia e o cerebro (`fallback_adaptive`), que nao roda aqui --
        #    e o que este guarda mede e que o corredor SABE a tela e responde o
        #    que o caso diz. O caminho do cerebro tem guarda proprio.
        servico_texto="Eletrodoméstico",
        eletrodomestico_rotulo="Geladeira"))
    sp2, rp2 = responder(sp2, tela)
    certo(rp2 is not None,
          f"🔴 porto/residencial/eletrodomesticos responde: {rotulo}",
          f"respondeu {rp2!r}")

# 🔴 CONTROLE: e esta rota NAO recebe `regras_para_o_cliente` de proposito.
#    A unica sessao dela abandona no terceiro submenu, sem protocolo, e a unica
#    frase do corpus que casaria a regua e um aviso de mascaramento -- que nao e
#    regra ao cliente. Preencher com ela seria ganhar 3 pontos enganando a regua.
_sub_pe = (CP.get_playbook("porto-residencial-whatsapp@v1")
           .get("subservices") or {}).get("eletrodomesticos") or {}
certo(not _sub_pe.get("regras_para_o_cliente"),
      "🔴 CONTROLE: e esta rota segue SEM `regras_para_o_cliente` -- a "
      "unica sessao dela abandona antes de qualquer regra de cobertura",
      str(_sub_pe.get("regras_para_o_cliente"))[:60])

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
