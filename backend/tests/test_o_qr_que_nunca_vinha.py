"""O QR que nunca vinha, e o canal que voltava mudo.

A HISTÓRIA
==========
Uma atendente da Resulta passou DIAS tentando parear o WhatsApp. A tela
alternava entre duas frases, com um código de suporte diferente a cada tentativa:

    "O serviço de conexão está indisponível no momento."      (provider_unavailable)
    "A configuração do canal precisa de ajuste pelo suporte." (configuration_error)

Não havia suporte a chamar: o suporte é o próprio sistema. Três diagnósticos e
dois consertos depois, o QR continuava sem aparecer.

📊 A auditoria de 06/08/2026 mediu o provedor com linha de controle (CLAUDE.md
§9.2) e achou QUATRO defeitos, não um. Cada `teste_` aqui guarda um deles.

    RODADA          jid       POST /connect    GET /qr
    A (controle)    ausente   200              200 + PNG
    B (Resulta)     presente  200              400 "no QR code available"

Um fator variado, um resultado invertido. E a mensagem do provedor era um pedido
de paciência que nós traduzíamos como "chame o suporte".

E o defeito mais caro não era o QR: o reconector religava os canais **sem
webhook**, e a captura das duas corretoras estava parada há 42 h e 67 h com o
painel dizendo "Conectado".

COMO ESTE ARQUIVO PROVA
=======================
Funções puras, sem rede e sem banco. Cada guarda tem CONTROLE — a rodada que
prova que o teste CONSEGUE reprovar (CLAUDE.md §9.3): um guarda que não tem como
falhar não guarda nada.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar(caminho_relativo: str, nome: str):
    """Carrega um módulo pelo arquivo, sem passar pelo pacote `app.services`.

    O `__init__` daquele pacote puxa `openai`, que não existe na máquina de
    teste. O que está sob teste aqui é decisão pura — ela não precisa do pacote.
    """
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, caminho_relativo)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _fonte(caminho_relativo: str) -> str:
    with open(os.path.join(RAIZ, caminho_relativo), encoding="utf-8") as arquivo:
        return arquivo.read()


# ---------------------------------------------------------------------------
def teste_o_pedido_de_espera_nao_e_um_pedido_de_socorro():
    print("\n[1] 400 'no QR code available' é ESPERE, não é 'chame o suporte'")
    orq = _carregar_orquestrador()

    checar(
        orq.qr_ainda_nao_disponivel(
            400, '{"error":"no QR code available. Please wait a moment and try again"}'),
        "a resposta LITERAL do provedor é lida como espera",
        "📊 medida em 06/08/2026 contra a instância da Resulta")

    checar(orq.qr_ainda_nao_disponivel(400, "NO QR CODE AVAILABLE. please wait"),
           "e a leitura não depende de caixa alta/baixa")

    # CONTROLE — sem estas três, a função diria "espere" para tudo, e um canal
    # realmente quebrado ficaria em polling eterno até o TTL. O guarda tem de
    # conseguir reprovar.
    checar(not orq.qr_ainda_nao_disponivel(400, '{"error":"instance not found"}'),
           "CONTROLE — outro 400 continua sendo erro de verdade")
    checar(not orq.qr_ainda_nao_disponivel(401, "no qr code available"),
           "CONTROLE — 401 não vira espera nem com a mensagem certa")
    checar(not orq.qr_ainda_nao_disponivel(500, "no qr code available"),
           "CONTROLE — 500 continua sendo provedor fora")

    # E o efeito no produto: 400 deixou de ser terminal no `_refresh`.
    fonte = _fonte("backend/app/services/whatsapp/pairing_orchestrator.py")
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
    checar("if qr_response.status_code >= 400 and not aguardando_qr:" in comandos,
           "o `_refresh` só levanta quando NÃO é o pedido de espera")


def teste_instancia_que_ja_existe_nao_e_provedor_fora_do_ar():
    print("\n[2] create devolve 500 'already exists' — e isso não é indisponibilidade")
    orq = _carregar_orquestrador()

    checar(orq.instancia_ja_existe(500, '{"error":"instance already exists"}'),
           "500 + 'already exists' é reconhecido",
           "📊 resposta medida do POST /instance/create com nome repetido")
    checar(orq.instancia_ja_existe(
               500, 'duplicate key value violates unique constraint "uni_instances_token"'),
           "500 + token duplicado também",
           "📊 a outra forma medida na mesma bateria")
    checar(orq.instancia_ja_existe(409, "") and orq.instancia_ja_existe(422, ""),
           "409/422 seguem aceitos — upstream pode passar a usá-los")

    # CONTROLE — o defeito era tratar 500 como categoria. Se qualquer 500 virasse
    # "já existe", um provedor em pânico seria lido como instância duplicada e o
    # pareamento seguiria em cima de um banco fora do ar.
    checar(not orq.instancia_ja_existe(500, '{"error":"database is down"}'),
           "CONTROLE — 500 genuíno continua sendo falha")
    checar(not orq.instancia_ja_existe(200, "already exists"),
           "CONTROLE — 200 nunca é recusa, mesmo com a mensagem dentro")


def teste_religar_um_canal_sem_dizer_para_onde_entregar_e_proibido():
    print("\n[3] O connect que apagava a entrega do canal")
    seg = _carregar("backend/app/services/whatsapp/channel_security.py",
                    "_teste_channel_security")

    corpo = seg.corpo_do_connect("https://api.exemplo/api/v1/webhook/evolution-go/tok")
    checar(corpo.get("webhookUrl", "").endswith("/tok"),
           "o corpo leva a URL de entrega")
    checar("HISTORY_SYNC" in corpo.get("subscribe", []),
           "e assina HISTORY_SYNC — sem ele o Espelho não recebe o histórico")
    checar(set(corpo.get("subscribe", [])) == set(seg.EVENTOS_DO_CANAL),
           "a lista vem de EVENTOS_DO_CANAL, não de uma cópia local")

    # CONTROLE — o defeito real: `{"immediate": True}` sem webhookUrl. O Go grava
    # `Webhook=""` por cima e o canal volta MUDO. Tem de ser impossível montar.
    try:
        seg.corpo_do_connect("")
        vazio_recusado = False
    except ValueError:
        vazio_recusado = True
    checar(vazio_recusado,
           "CONTROLE — corpo sem URL é RECUSADO, não montado em silêncio",
           "📊 era assim que 3 das 4 instâncias ficaram com webhook=''")

    # E os quatro chamadores usam o mesmo corpo — a divergência era o defeito.
    for caminho, quem in (
        ("backend/app/services/whatsapp/pairing_orchestrator.py", "orquestrador"),
        ("backend/app/services/whatsapp/channel_state.py", "reconector"),
        ("backend/app/api/whatsapp_channel.py", "canal da corretora"),
        ("backend/app/api/admin_atlas.py", "onboarding do Atlas"),
    ):
        fonte = _fonte(caminho)
        comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
        checar("corpo_do_connect(" in comandos,
               f"o {quem} usa o corpo único")
        checar('"subscribe": [' not in comandos,
               f"CONTROLE — e o {quem} NÃO monta uma lista própria")


def teste_o_reconector_rotaciona_em_vez_de_apagar():
    print("\n[4] O reconector grava a credencial ANTES de religar")
    fonte = _fonte("backend/app/services/whatsapp/channel_state.py")
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("json=corpo_do_connect(" in comandos,
           "religa com o corpo completo")
    checar('json={"immediate": True}' not in comandos,
           "CONTROLE — o corpo que apagava o webhook não existe mais",
           "📊 era ele que zerava Webhook e Events em produção")
    checar("_gravar_credencial_de_webhook" in comandos,
           "o hash do webhook novo é gravado")
    checar("if not await _gravar_credencial_de_webhook" in comandos,
           "CONTROLE — e a falha em gravar IMPEDE a religação",
           "entregar para uma porta que recusa é trocar mudo por surdo")
    checar('PUBLIC_BACKEND_URL' in comandos and "return None" in comandos,
           "sem endereço público, não religa de propósito")
    checar('.eq("company_id"' in comandos,
           "a gravação filtra por corretora (CLAUDE.md §7)",
           "service role ignora RLS — o filtro é o único guarda")


def teste_a_linha_que_ja_tem_dono_diz_quem_e():
    print("\n[5] Sessão registrada: religa e mostra o número, em vez de pedir QR")
    fonte = _fonte("backend/app/services/whatsapp/pairing_orchestrator.py")
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("_sessao_registrada" in comandos,
           "o orquestrador pergunta ao provedor se a linha já tem jid")
    checar('r.get("name") or "") == instance' in comandos,
           "e a pergunta é feita ao /instance/all, que é o estado DURÁVEL",
           "/instance/status lê a memória do processo e mente após restart")
    checar("if jid_registrado:" in comandos,
           "com jid, o fluxo NÃO segue para o QR")

    orq = _carregar_orquestrador()
    checar("paired_phone" in orq._PUBLIC_FIELDS,
           "o telefone pareado chega à tela",
           "pedido do Founder em 06/08/2026")

    # CONTROLE — e chega MASCARADO. É a linha de trabalho de uma pessoa real.
    numero = _carregar("backend/app/services/whatsapp/numero_pareado.py",
                       "_teste_numero_pareado")
    mascarado = numero.mascarar(numero.telefone_e164("554788087463:26@s.whatsapp.net"))
    checar("88087463" not in mascarado,
           "CONTROLE — o número não trafega cru (CLAUDE.md §13.3)",
           f"vira {mascarado}")
    checar(mascarado.startswith("5547"),
           "mas quem já conhece a linha a reconhece",
           mascarado)


def teste_existe_saida_para_trocar_de_numero():
    print("\n[6] A porta que não existia: soltar a linha do telefone antigo")
    fonte = _fonte("backend/app/services/whatsapp/pairing_orchestrator.py")
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("async def liberar_para_novo_numero" in comandos,
           "existe caminho para trocar o número pareado",
           "📊 nada no Evolution Go limpa o jid — sem isto, exige console")
    checar("self._instance_name(company_id, purpose), integration, lembrada" in comandos,
           "o NOME vem de identidade_da_instancia, não do chamador",
           "observer_number = _digits(nome) — é metade da chave de dedup")
    checar("await self._provider_create(client, instance, instance_token)" in comandos,
           "recria com o mesmo nome e o mesmo token")
    checar('"ja_estava_sem_numero"' in comandos,
           "CONTROLE — é idempotente: dois cliques não apagam duas vezes")
    checar('"sem_instancia_registrada"' in comandos,
           "CONTROLE — quem nunca pareou não sofre um delete inventado")

    rota = _fonte("backend/app/api/whatsapp_channel.py")
    checar("pairing/liberar-numero" in rota, "e a tela tem por onde chamar")

    # CONTROLE que mais importa: NADA chama isso sozinho. Um reconector que
    # liberasse a linha derrubaria a corretora que está funcionando.
    estado = _fonte("backend/app/services/whatsapp/channel_state.py")
    checar("liberar_para_novo_numero" not in estado,
           "CONTROLE — o heartbeat NUNCA libera linha nenhuma",
           "automatizar isto derrubaria quem está pareado e funcionando")


def _carregar_orquestrador():
    """O orquestrador puxa `app.core.*` no topo; aqui só interessam as puras."""
    if "_teste_orquestrador" in sys.modules:
        return sys.modules["_teste_orquestrador"]
    for nome, atributos in (
        ("app.services.whatsapp.integration_secrets",
         {"prepare_integration_for_runtime": lambda r: r,
          "decrypt_integration_secret": lambda v: v}),
    ):
        if nome not in sys.modules:
            modulo = types.ModuleType(nome)
            for chave, valor in atributos.items():
                setattr(modulo, chave, valor)
            sys.modules[nome] = modulo
    return _carregar("backend/app/services/whatsapp/pairing_orchestrator.py",
                     "_teste_orquestrador")


def main() -> int:
    print("=" * 70)
    print("O QR QUE NUNCA VINHA — os quatro defeitos do pareamento")
    print("=" * 70)
    teste_o_pedido_de_espera_nao_e_um_pedido_de_socorro()
    teste_instancia_que_ja_existe_nao_e_provedor_fora_do_ar()
    teste_religar_um_canal_sem_dizer_para_onde_entregar_e_proibido()
    teste_o_reconector_rotaciona_em_vez_de_apagar()
    teste_a_linha_que_ja_tem_dono_diz_quem_e()
    teste_existe_saida_para_trocar_de_numero()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for problema in _PROBLEMAS:
            print(f"  - {problema}")
        return 1
    print("TUDO VERDE — o pedido de espera não é mais um pedido de socorro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
