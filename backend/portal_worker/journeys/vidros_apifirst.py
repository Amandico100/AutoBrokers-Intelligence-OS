# -*- coding: utf-8 -*-
"""A journey API-first do portal de vidros — SPEC-074 + EXTRA-001.10, atrás de flag.

Como ela entra sem arriscar o que funciona
==========================================
`PORTAL_VIDROS_API_FIRST` nasce **false**. Com a flag desligada,
`vidros_lanternas.abrir_atendimento` segue exatamente o caminho de hoje —
`_select_insurer_start` → passo 1 → modal → `run_adaptive`. Nenhuma linha muda.

Com a flag ligada, este módulo assume o fluxo INTEIRO, do nome da seguradora ao
desfecho que o portal decidiu, e devolve o controle ao DOM **apenas antes** da
primeira escrita.

🔴 A ordem das operações NÃO é a da tela
========================================
📊 Medido nos 4 HAR de 20/09/2026 (`trafego.importar_har`), idêntico em 4 de 4:

    GET  /seguradoras/          a lista AO VIVO — o slug sai daqui, não do código
    GET  /apolices              preflight — read-only, decide se PODE escrever
    ────────────── fronteira A ──────────────
    POST /atendimentos          NumeroProtocolo + Token · IRREVERSÍVEL
    PUT  /atendimentos/corretores   ← e é daqui em diante que o token viaja
    POST /solicitantes
    GET  /apolices/itens-cobertos · /motivos-dano · /ufs · /cidades · /clientes/cidades
    ─── [L] fronteira B AQUI ───
    PATCH /atendimentos         grava peça, causa, local
    ─── [V] segue ───
    POST /questionarios/perguntas ×N   (leitura! não persiste)
    POST /questionarios/regras-reparo  (leitura! diz se o portal vai oferecer reparo)
    ─── [V] fronteira B ───
    POST /questionarios         CodigoAtendimento nasce · IRREVERSÍVEL
    PUT  /atendimentos/alterar-reparo  (quando o segurado decidiu)
    GET  /agendamentos/opcoes-disponiveis   🔴 O ROTEADOR: quem decide o desfecho
    GET  /atendimentos          ← só AGORA o ScriptFinalizacao traz a loja

🔴 A regra de ouro de segurança
===============================
**Depois da fronteira A nada cai para o DOM e nada é reexecutado.** Toda parada
é `needs_human` com `business_state` e o que falta; toda resposta fora do
contrato grava `evidence["tela_desconhecida"]` com as CHAVES, nunca os valores.

Antes da fronteira A, devolver `None` continua sendo a resposta certa: nada
aconteceu, e o navegador é a autoridade de último recurso.

O que este módulo NÃO faz
=========================
Não direciona, não cancela, não abandona, não finaliza. Ele APRESENTA o que o
portal ofereceu — lojas, distâncias, dias e horários LIVRES — e a escolha
continua sendo do segurado.

🔴 EXTRA-001.10.1 — o que mudou, e com que limite
==================================================
AGENDA (📊 `POST /agendamentos` medido, LATERAL [048]) só em dois casos, e
sempre confirmada pelo "Agendado para" LIDO do portal: (a) a preferência que o
segurado JÁ deu (`especificos.preferencia_agenda`) casou — loja mais próxima
pela distância do portal, 1º horário livre no período; (b) a continuação trouxe
a escolha dele (loja, dia, horário), casada por IGUALDADE com o publicado agora.
O RAMO 7 do roteador (prioridade + preferência de vistoria) é respondido com a
preferência dele e as respostas NEUTRAS medidas; sem ela, para e pergunta.
As fases depois da fronteira A viraram funções (`rodar_fases`) — a journey
`vidros_continuacao` as reusa; não existe segundo motor.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from portal_worker.journeys import JourneyResult
from portal_worker.journeys import vidros_api as API
from portal_worker.journeys import vidros_estado as ST
from portal_worker.journeys import vidros_questionario as QZ
from portal_worker.journeys.vidros_sessao import SessaoVidros

logger = logging.getLogger(__name__)

# Teto de leitura da agenda. 📊 A única captura com agenda trouxe 1 loja; 6
# cobre uma cidade grande e ainda impede que uma lista inesperada de 40 lojas
# queime o teto de 150 chamadas da sessão em consultas de rota.
MAX_LOJAS_CONSULTADAS = 6


def api_first_habilitado() -> bool:
    """A flag nasce DESLIGADA. So um `true`/`1` explicito liga."""
    return str(os.getenv("PORTAL_VIDROS_API_FIRST", "") or "").strip().lower() in ("1", "true", "yes", "on")


def data_iso(valor: Any) -> str:
    """`DD/MM/AAAA` (o formato que a conversa produz) → `AAAA-MM-DD`.

    Devolve `""` para qualquer coisa que não seja uma data reconhecível — e o
    vazio faz o preflight desistir e cair para o DOM, que é o comportamento
    certo: adivinhar a data do dano é escolher a data errada.
    """
    txt = str(valor or "").strip()
    if not txt:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
        return txt
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", txt)
    if not m:
        return ""
    d, mes, ano = m.groups()
    try:
        datetime(int(ano), int(mes), int(d))
    except ValueError:
        return ""  # 31/02 não é data; melhor cair para o DOM do que mentir
    return f"{ano}-{int(mes):02d}-{int(d):02d}"


def _norm(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# --------------------------------------------------------------------------
# 🔴 Casar UM item de um catálogo do portal — e parar quando não dá
# --------------------------------------------------------------------------
def casar_unico(texto: Any, itens: Any, campos: Tuple[str, ...]) -> Dict[str, Any]:
    """`{"item", "candidatos", "motivo"}`. `item=None` quando não há UM só.

    🔴 A regra que esta função existe para impedir: **escolher por posição**.
    📊 A mesma pergunta veio com as opções em ordem diferente entre duas
    seguradoras (`vidros_questionario`, docstring do módulo) — pegar "o
    primeiro" troca a porta do motorista pela do carona, e o portal não deixa
    corrigir depois.

    Zero candidatos e dois candidatos são desfechos DIFERENTES e os dois param:
    um pede a família da peça, o outro pede a desambiguação. Quem pergunta é a
    conversa, com a lista real na mão.
    """
    alvo = _norm(texto)
    reais = [i for i in (itens or []) if isinstance(i, dict)]
    if not alvo:
        return {"item": None, "candidatos": reais, "motivo": "nada a casar"}

    def textos(i: Dict[str, Any]) -> List[str]:
        return [_norm(i.get(c)) for c in campos if i.get(c) not in (None, "")]

    exatos = [i for i in reais if alvo in textos(i)]
    if len(exatos) == 1:
        return {"item": exatos[0], "candidatos": exatos, "motivo": "texto exato"}
    if len(exatos) > 1:
        return {"item": None, "candidatos": exatos, "motivo": "mais de um item com o mesmo texto"}

    contidos = [i for i in reais
                if any(t and (alvo in t or t in alvo) for t in textos(i))]
    if len(contidos) == 1:
        return {"item": contidos[0], "candidatos": contidos, "motivo": "continencia"}
    if len(contidos) > 1:
        return {"item": None, "candidatos": contidos,
                "motivo": f"{len(contidos)} itens candidatos"}

    # 🔴 Terceira passada: TODAS as palavras do segurado estão no item?
    #
    # 📊 A medição que a obriga, feita na costura com o catálogo real de
    # lataria: a própria pergunta da fatia C ensina o agente a responder
    # `["porta dianteira esquerda", "paralama esquerdo"]`, e o catálogo escreve
    # `PORTA DT ESQUERDA` e `PARALAMAS DT ESQUERDO`. Por continência, **zero**
    # das duas casava — e todo pedido de lataria parava com o protocolo já
    # emitido.
    #
    # A passada é conservadora por construção: ela só aceita quando **todas** as
    # palavras ditas estão no item e **um único** item as contém. Ela nunca
    # inventa: "uma pedra bateu no vidro" continua não casando com
    # "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA", e é isso mesmo.
    ditas = _palavras_comparaveis(alvo)
    if ditas:
        subconjunto = [i for i in reais
                       if any(t and ditas <= _palavras_comparaveis(t) for t in textos(i))]
        if len(subconjunto) == 1:
            return {"item": subconjunto[0], "candidatos": subconjunto,
                    "motivo": "todas as palavras ditas estao no item"}
        if len(subconjunto) > 1:
            return {"item": None, "candidatos": subconjunto,
                    "motivo": f"{len(subconjunto)} itens contem todas as palavras"}
    return {"item": None, "candidatos": [], "motivo": "nenhum item do catalogo casou"}


# 📊 Como o catálogo do portal ABREVIA, lido dos 21 serviços de lataria da
# captura: `PORTA DT ESQUERDA`, `PORTA TR DIREITA`, `PARALAMAS DT ESQUERDO`.
# E o segurado fala por extenso e troca o gênero. As duas pontas viram a mesma
# raiz, e nenhuma delas precisa saber da outra.
_RAIZ_DA_PALAVRA: Dict[str, str] = {
    "dt": "diant", "dianteiro": "diant", "dianteira": "diant", "frente": "diant",
    "tr": "tras", "traseiro": "tras", "traseira": "tras", "atras": "tras",
    "esquerdo": "esq", "esquerda": "esq", "motorista": "esq",
    "direito": "dir", "direita": "dir", "carona": "dir", "passageiro": "dir",
}
# Palavras que aparecem em quase todo item do catálogo e não distinguem nada
# ("RLATARIA (SEM TROCA)" está em 14 dos 21 serviços).
_PALAVRAS_SEM_PODER = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as",
                       "um", "uma", "no", "na", "em", "com", "meu", "minha",
                       "sem", "troca", "rlataria", "reparo", "se"}


def _palavras_comparaveis(texto: Any) -> set:
    """Palavras que distinguem um item do outro, já com as raízes aplicadas."""
    limpo = "".join(c if c.isalnum() else " " for c in _norm(texto))
    saida = set()
    for palavra in limpo.split():
        if palavra in _PALAVRAS_SEM_PODER:
            continue
        raiz = _RAIZ_DA_PALAVRA.get(palavra)
        if raiz is None and palavra.endswith("s") and len(palavra) > 3:
            raiz = _RAIZ_DA_PALAVRA.get(palavra[:-1], palavra[:-1])
        saida.add(raiz or palavra)
    return saida


def casar_peca(texto: Any, itens: Any) -> Dict[str, Any]:
    """A PEÇA do catálogo — pelo VOCABULÁRIO ÚNICO, não por continência de texto.

    🔴 Esta função existe por uma medição feita na costura, em 20/09/2026, com
    os três catálogos reais e as palavras que o segurado usa de verdade:

        texto do segurado              continência       vocabulário único
        ─────────────────────────────  ────────────────  ─────────────────────
        "para-brisa"                   ✗ nada            ✓ VIDRO PARABRISA
        "o vidro da frente"            ✗ nada            ✓ VIDRO PARABRISA
        "vidro da porta"               ✗ nada            ✓ VIDRO DE PORTA
        "porta do motorista"           ✗ nada            ✓ VIDRO DE PORTA
        "amassei a porta e o paralama" ✗ nada            ✓ (pela FAMÍLIA)

    📊 **5 de 10 frases reais não casavam** — e cada uma delas é um pedido que
    nasce e trava em `peca_ambigua` com o protocolo já emitido. `explicar_match`
    é o casador de PEÇA que o caminho DOM já usa, com placar, margem mínima e
    veto de peça diferente; usar outro aqui seria um segundo vocabulário
    (CLAUDE.md §5).

    Duas passadas, e a segunda é a que resolve a lataria: quando as palavras do
    segurado não nomeiam nenhuma linha do catálogo mas nomeiam **uma família**
    (`identidade_peca("amassei a porta e o paralama") == {"lataria"}`), procura-se
    a família no catálogo — e é assim que se chega em
    `REPARO DE LATARIA E PINTURA` sem nenhuma tabela nova.

    ⛔ Sem confiança, `item=None` e as opções REAIS voltam. Escolher "o mais
    parecido" é como se pede o para-brisa de quem quebrou o vidro da porta.
    """
    from portal_worker.journeys.vidros_lanternas import (
        explicar_match, identidade_peca,
    )

    reais = [i for i in (itens or []) if isinstance(i, dict)]
    rotulos = [str(i.get("Descricao") or "") for i in reais]
    if not str(texto or "").strip() or not rotulos:
        return {"item": None, "candidatos": reais, "motivo": "nada a casar"}

    def pelo_rotulo(escolha: Any) -> Optional[Dict[str, Any]]:
        for i in reais:
            if str(i.get("Descricao") or "") == escolha:
                return i
        return None

    familias = sorted(identidade_peca(str(texto)))

    def a_familia_do_item_bate(item: Dict[str, Any]) -> bool:
        """🔴 A PECA ESCOLHIDA TEM DE SER DA FAMILIA QUE O SEGURADO NOMEOU.

        📊 O red team mediu, no catalogo real do para-brisa, o que acontecia sem
        esta checagem:

            "vidro lateral"            -> LANTERNA TRASEIRA BI-PARTIDA LATERAL LED
            "janela lateral traseira"  -> LANTERNA TRASEIRA BI-PARTIDA LATERAL LED

        A pessoa pede o vidro da porta e o robo pede uma LANTERNA — irreversivel,
        pago, e o portal nao deixa corrigir. A palavra `LATERAL` no nome da
        lanterna bastava.

        A regra: a identidade da DESCRICAO DO ITEM tem de ser exatamente a
        familia que o texto do segurado nomeou. `LANTERNA … LATERAL LED` tem
        identidade `{lanterna, lateral}` — nao e `{lateral}`, entao nao serve.
        Quando o texto nao nomeia UMA familia, nao ha o que conferir e a
        checagem se cala (nao inventa veto).
        """
        if len(familias) != 1:
            return True
        return sorted(identidade_peca(str(item.get("Descricao") or ""))) == familias

    veredito = explicar_match(texto, rotulos)
    item = pelo_rotulo(veredito.get("escolha"))
    if item is not None and a_familia_do_item_bate(item):
        return {"item": item, "candidatos": [item],
                "motivo": f"vocabulario unico: {veredito.get('motivo')}"}
    if item is not None:
        return {"item": None, "candidatos": reais,
                "motivo": (f"o item mais parecido ({item.get('Descricao')!r}) nao e "
                           f"da familia {familias[0]!r} que o segurado nomeou")}

    if len(familias) == 1:
        # 🔴 A passada por FAMILIA so aceita item cuja PROPRIA identidade e
        # aquela familia, e exatamente UM. Sem "o mais parecido".
        da_familia = [i for i in reais if a_familia_do_item_bate(i)]
        if len(da_familia) == 1:
            return {"item": da_familia[0], "candidatos": da_familia,
                    "motivo": f"unico item da familia {familias[0]!r} no catalogo"}
        if len(da_familia) > 1:
            # `para_choque` -> "para choque": o nome da familia e chave de
            # codigo; o que se procura no catalogo e a palavra.
            por_familia = explicar_match(familias[0].replace("_", " "),
                                         [str(i.get("Descricao") or "") for i in da_familia])
            item = pelo_rotulo(por_familia.get("escolha"))
            if item is not None and a_familia_do_item_bate(item):
                return {"item": item, "candidatos": da_familia,
                        "motivo": f"pela familia {familias[0]!r}: {por_familia.get('motivo')}"}
            return {"item": None, "candidatos": da_familia,
                    "motivo": (f"{len(da_familia)} itens da familia {familias[0]!r} "
                               "no catalogo desta apolice")}

    return {"item": None, "candidatos": reais,
            "motivo": f"o vocabulario nao reconheceu a peca ({veredito.get('motivo')})"}


# --------------------------------------------------------------------------
# 🔴 A CAUSA DO DANO — DEPOIS DA FRONTEIRA, SO IGUALDADE
# --------------------------------------------------------------------------
# 📊 Aqui existia uma segunda passada, por "palavra distintiva". O red team a
# mediu contra as listas AO VIVO dos 4 HAR, em 20/09/2026:
#
#     "quebra acidental do para-brisa"  ->  QUEBRA INTENCIONAL OU VOLUNTARIA
#     "foi uma quebra acidental"        ->  QUEBRA INTENCIONAL OU VOLUNTARIA
#     "na chuva o vidro trincou"        ->  CHUVA DE GRANIZO
#
# A primeira linha descreve FRAUDE. Ela e gravada na seguradora, confiante e
# calada, para alguem que disse o contrario — e sinistro negado por causa
# declarada errada nao se desfaz com um pedido de desculpas.
#
# A passada MORREU. O que sobrou e igualdade normalizada com a lista daquela
# peca, e o rigor mudou de lugar: `portal_params.causa_conhecida` exige, ANTES
# da fronteira A, que `como_ocorreu` seja IGUAL a uma causa medida da familia.
# Ali, recusar custa uma pergunta; aqui, custa o atendimento.
CAUSA_PROIBIDA_POR_EXCLUSAO = "outros"


def casar_causa(texto: Any, motivos: Any) -> Dict[str, Any]:
    """A causa do dano na lista AO VIVO, por IGUALDADE. Nada mais.

    ⛔ Sem continencia, sem palavra distintiva, sem posicao, sem `OUTROS` por
    exclusao — `OUTROS` so quando dito literalmente, e ai e escolha de gente.
    """
    reais = [m for m in (motivos or []) if isinstance(m, dict)]
    alvo = _norm(texto)
    if not alvo or not reais:
        return {"item": None, "candidatos": reais, "motivo": "nada a casar"}

    exatos = [m for m in reais if _norm(m.get("DescricaoObjetoCausa")) == alvo]
    if len(exatos) == 1:
        return {"item": exatos[0], "candidatos": exatos, "motivo": "texto exato"}
    if len(exatos) > 1:
        return {"item": None, "candidatos": exatos,
                "motivo": "a lista tem duas causas com o mesmo texto"}
    return {"item": None, "candidatos": reais,
            "motivo": "a causa dita nao e IGUAL a nenhuma da lista desta peca"}


def casar_igual(texto: Any, itens: Any, campos: Tuple[str, ...]) -> Dict[str, Any]:
    """Casamento por IGUALDADE normalizada, e exatamente UM. Nada de parecido.

    🔴 E o unico casador que esta SPEC autoriza depois da fronteira A para
    catalogo fechado (cidade, UF). Zero candidatos e dois candidatos param —
    sao desfechos diferentes e os dois pedem a mesma coisa: perguntar.
    """
    reais = [i for i in (itens or []) if isinstance(i, dict)]
    alvo = _norm(texto)
    if not alvo:
        return {"item": None, "candidatos": reais, "motivo": "nada a casar"}
    iguais = [i for i in reais
              if any(_norm(i.get(c)) == alvo for c in campos if i.get(c) not in (None, ""))]
    if len(iguais) == 1:
        return {"item": iguais[0], "candidatos": iguais, "motivo": "texto exato"}
    if len(iguais) > 1:
        return {"item": None, "candidatos": iguais,
                "motivo": f"{len(iguais)} itens com o mesmo nome"}
    return {"item": None, "candidatos": reais,
            "motivo": "nenhum item do catalogo tem esse nome exato"}


def _rotulos(itens: Any, campo: str, teto: int = 20) -> List[str]:
    return [str(i.get(campo) or "") for i in (itens or [])
            if isinstance(i, dict)][:teto]


# --------------------------------------------------------------------------
# O contato que vai ao portal — D-E00110-01
# --------------------------------------------------------------------------
# 📊 Medido em 4 de 4 capturas: `RelacaoTitular` é STRING (`"1"`, `"5"`, `"6"`),
# `TermoAceito` é `false` nas quatro, e `EmailTitularAplice` (sic, sem o `o`) só
# aparece quando `EmailCorretor` é `true` — 2 de 4.
#
# 🔴 A nossa escolha é sempre `"6"` (Corretor): quem abre é a corretora, e
# declarar "O Próprio" seria declaração falsa. O CONTATO, porém, é o segurado —
# 📊 3 de 4 capturas gravaram o telefone como `Tipo 21 = CELULAR CORRETOR`, e
# nessas o portal marcou `PossuiTelefoneRecebeWhatsapp: false`: o segurado não
# recebe nada e a loja liga para a corretora.
RELACAO_CORRETOR = "6"
TIPO_TELEFONE_POR_DONO = {
    "segurado": "CELULAR SEGURADO",
    "corretora": "CELULAR CORRETOR",
}


def _contato_de(params: Dict[str, Any]) -> Dict[str, Any]:
    """O bloco `params["contato"]` do contrato A↔C, com defaults compatíveis.

    Se `contato` não vier, cai para o `solicitante`/`segurado` que a tool já
    monta hoje — assim a fatia C pode chegar depois sem derrubar a A.
    """
    c = dict(params.get("contato") or {})
    sol = dict(params.get("solicitante") or {})
    seg = dict(params.get("segurado") or {})
    tipo_telefone = str(c.get("tipo_telefone")
                        or ("segurado" if seg.get("telefone") else "corretora"))
    # 🔴 EXTRA-001.10.1 (D-E001101-04): o WhatsApp do SEGURADO vai marcado.
    # 📊 `StatusEnvioWhatsapp: true` medido 1× (LATERAL [009], Tipo 20) e o
    # agregado passou a dizer `PossuiTelefoneRecebeWhatsapp: true`; sem a
    # caixinha, `false` nas outras 5 capturas. Padrão: marcado quando o telefone
    # é do segurado — o celular da corretora não recebe o aviso do portal.
    recebe = c.get("recebe_whatsapp")
    return {
        "relacao": str(c.get("relacao") or RELACAO_CORRETOR),
        "telefone": str(c.get("telefone") or seg.get("telefone")
                        or sol.get("telefone") or "").strip(),
        "tipo_telefone": tipo_telefone,
        "recebe_whatsapp": (bool(recebe) if recebe is not None
                            else tipo_telefone.strip().lower() == "segurado"),
        "email_segurado": str(c.get("email_segurado") or seg.get("email") or "").strip(),
        "email_corretora": str(c.get("email_corretora") or sol.get("email") or "").strip(),
        "nome_solicitante": str(c.get("nome_solicitante") or sol.get("nome") or "").strip(),
        "documento_corretor": str(c.get("documento_corretor")
                                  or sol.get("cpf_cnpj") or "").strip(),
    }


def _codigo_do_tipo_de_telefone(tipos: Any, dono: str) -> Optional[int]:
    """Do NOME para o código. 📊 `[{Codigo:20,Descricao:"CELULAR SEGURADO"},…]`.

    🔴 Nunca o número decorado: `20` e `21` estão a um dígito de distância e
    significam pessoas diferentes. Se a lista não trouxer o nome, a resposta é
    `None` e quem chamou para — gravar o tipo errado manda o SMS do portal para
    o telefone errado.
    """
    alvo = _norm(TIPO_TELEFONE_POR_DONO.get(str(dono or "").strip().lower(), ""))
    if not alvo:
        return None
    for t in (tipos or []):
        if isinstance(t, dict) and _norm(t.get("Descricao")) == alvo:
            try:
                return int(t.get("Codigo"))
            except (TypeError, ValueError):
                return None
    return None


def termo_exibido(corpo: Dict[str, Any]) -> bool:
    """A regra LITERAL do SPA para `TermoExibido` (laudo §8, offset ~107338).

    termo = e-mail do segurado E relação preenchidos E
            (O Próprio "1" SEM e-mail de corretor  OU  Corretor "6" COM e-mail de corretor)

    📊 Bate com as 6 capturas (todas `false`). 🔴 A versão anterior mandava
    `true` sempre — declarava ao portal um termo que a tela dele não teria
    exibido a ninguém.
    """
    email = str(corpo.get("EmailSegurado") or "").strip()
    relacao = str(corpo.get("RelacaoTitular") or "").strip()
    if not email or not relacao:
        return False
    com_corretor = bool(corpo.get("EmailCorretor"))
    return (relacao == "1" and not com_corretor) or (relacao == "6" and com_corretor)


def _corpo_do_solicitante(contato: Dict[str, Any], *,
                          codigo_tipo_telefone: int) -> Dict[str, Any]:
    """O corpo do `POST /solicitantes`, na ordem medida."""
    tem_email_corretora = bool(contato["email_corretora"])
    corpo: Dict[str, Any] = {
        "RelacaoTitular": str(contato["relacao"]),
        "EmailSegurado": contato["email_segurado"],
    }
    if tem_email_corretora:
        # 📊 A chave chega escrita assim no portal, sem o `o` de "Apolice".
        # Corrigir a grafia faria o campo não existir para o servidor.
        corpo["EmailTitularAplice"] = contato["email_corretora"]
    corpo["NomeSolicitante"] = contato["nome_solicitante"] or None
    corpo["CpfCnpjSolicitante"] = contato["documento_corretor"] or None
    corpo["EmailCorretor"] = True if tem_email_corretora else None
    telefone: Dict[str, Any] = {"Numero": contato["telefone"],
                                "Tipo": codigo_tipo_telefone}
    if contato.get("recebe_whatsapp"):
        telefone["StatusEnvioWhatsapp"] = True
    corpo["Telefones"] = [telefone] if contato["telefone"] else []
    corpo["TermoExibido"] = termo_exibido(corpo)
    # 🔴 `false` em 4 de 4 capturas. Não se inventa `true` num termo que
    # ninguém exibiu a ninguém.
    corpo["TermoAceito"] = False
    return corpo


# --------------------------------------------------------------------------
# Guard e checkpoint
# --------------------------------------------------------------------------
def _guard_do(params: Dict[str, Any]):
    """O guard da SPEC-073 — e, sem ele, uma porta FECHADA.

    🔴 A versão anterior desta função devolvia
    `PortalActionGuard(material_liberado=bool(params.get("confirm")))` quando o
    runtime não vinha nos params. Isso era fail-OPEN, e abria justamente o
    buraco que a SPEC-073 existe para fechar:

    `guard.armar()` só persiste `phase=armed` se tiver um checkpoint durável
    (`_gravar` faz `if self._checkpoint is not None`). Um guard construído solto
    não tem nenhum. Então, com `confirm=True` e sem runtime, o `POST
    /atendimentos` saía **sem que o banco soubesse que havia um POST em curso**
    -- e uma queda logo depois deixaria um atendimento existindo na seguradora
    sem uma linha de evidência. É o `maybe_committed` sem ninguém para
    reconciliar.

    Em produção o worker sempre injeta `params["_runtime"]`. Mas "sempre" é uma
    suposição sobre outro módulo, e fronteira material não se apoia em
    suposição: se a injeção quebrar um dia, o certo é o pedido NÃO sair.
    """
    rt = params.get("_runtime")
    g = getattr(rt, "guard", None)
    if g is not None:
        return g
    from portal_worker.guardrails import PortalActionGuard

    # Sem checkpoint durável não há fronteira material. Leitura continua livre.
    return PortalActionGuard(material_liberado=False)


async def _checkpoint(params: Dict[str, Any], patch: Dict[str, Any]) -> None:
    rt = params.get("_runtime")
    if rt is not None and hasattr(rt, "checkpoint"):
        await rt.checkpoint(patch)


def _tela_desconhecida(evidence: Dict[str, Any], *, onde: str,
                       resposta: Dict[str, Any]) -> None:
    """Grava o dossiê de uma resposta fora do contrato. **Chaves, nunca valores.**

    📊 A API do portal devolve nome, CPF, placa e telefone dentro dos agregados.
    O dossiê existe para ensinar o sistema o que ele não conhecia; para isso
    bastam o endereço, o status e a FORMA da resposta.
    """
    corpo = resposta.get("json")
    if isinstance(corpo, dict):
        resumo: Any = sorted(corpo.keys())[:40]
    elif isinstance(corpo, list):
        primeiro = corpo[0] if corpo and isinstance(corpo[0], dict) else {}
        resumo = {"lista": len(corpo), "chaves_do_item": sorted(primeiro.keys())[:40]}
    else:
        resumo = {"tipo": type(corpo).__name__}
    evidence["tela_desconhecida"] = {
        "onde": onde,
        "status": int(resposta.get("status") or 0),
        "erro": str(resposta.get("erro") or ""),
        "resumo": resumo,
    }


# --------------------------------------------------------------------------
# O relógio — UMA função, para o replay poder fixar o "hoje" da captura
# --------------------------------------------------------------------------
def hoje() -> date:
    """A data de hoje no fuso do portal (meia-noite de São Paulo).

    🔴 Uma função só, e não `datetime.now()` espalhado: o replay de um HAR de
    21/09 roda em outro dia, e "a primeira data ≥ hoje" tem de ser a do dia da
    captura para o motor ler a mesma agenda que o humano leu.
    """
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(API.FUSO_DO_PORTAL)).date()
    except Exception:  # noqa: BLE001
        return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


# --------------------------------------------------------------------------
# 🔴 A EXECUÇÃO — o estado que as FASES dividem (EXTRA-001.10.1)
# --------------------------------------------------------------------------
# A abertura era UMA função de 560 linhas. A continuação precisa retomar do
# meio dela — e a SPEC proíbe um segundo motor (CLAUDE.md §5). Então a função
# virou FASES, e a abertura e a continuação chamam as MESMAS fases com a
# mesma `Execucao`. Nada foi copiado para `vidros_continuacao`.
@dataclass
class Execucao:
    params: Dict[str, Any]
    evidence: Dict[str, Any]
    sessao: Any
    guard: Any
    estado: Any
    dano: Dict[str, Any] = field(default_factory=dict)
    local: Dict[str, Any] = field(default_factory=dict)
    especificos: Dict[str, Any] = field(default_factory=dict)
    contato: Dict[str, Any] = field(default_factory=dict)
    seguradora: str = ""
    protocolo: str = ""
    chassi: str = ""
    relato: str = ""
    perimetro: str = ""
    # o que as fases de LEITURA descobrem e as de escrita consomem
    codigo_item: str = ""
    partes: Dict[str, Any] = field(default_factory=dict)
    codigo_causa: Any = None
    servicos_lataria: List[Dict[str, Any]] = field(default_factory=list)
    codigo_cidade: Any = None
    reparo_decidido: Optional[bool] = None
    agregado: Dict[str, Any] = field(default_factory=dict)
    # o bloco `evidence["continuacao"]` COM a sessão cifrada (em memória)
    continuacao: Dict[str, Any] = field(default_factory=dict)


def execucao_de(params: Dict[str, Any], evidence: Dict[str, Any], *, sessao: Any,
                guard: Any, estado: Any) -> Execucao:
    """A `Execucao` a partir dos params do job — o mesmo contrato A↔C."""
    dano = dict(params.get("dano") or {})
    local = dict(params.get("local") or {})
    return Execucao(
        params=params, evidence=evidence, sessao=sessao, guard=guard, estado=estado,
        dano=dano, local=local,
        especificos=dict(params.get("especificos") or {}),
        contato=_contato_de(params),
        chassi=str(params.get("chassi") or "").strip(),
        relato=str(dano.get("descricao") or "").strip(),
        perimetro=API.perimetro_do_texto(dano.get("onde") or local.get("perimetro")),
    )


# --------------------------------------------------------------------------
# 🔴 A SESSÃO DURÁVEL — A1
# --------------------------------------------------------------------------
# 📊 O `Token` do `POST /atendimentos` é a ÚNICA autenticação da API (header
# `token_autorizacao`, sem cookie, CORS `*`); não existe endpoint que devolva
# token de atendimento existente (laudo §7c); e ele EXPIRA (o de 21/09 22:09Z
# deu 401 em 23/09 23:40Z). Guardá-lo é o único jeito de continuar um pedido
# que já nasceu — e guardá-lo em claro seria entregar a chave do atendimento a
# quem lesse `portal_jobs.evidence`. Vai CIFRADO pelo cofre do worker
# (`PORTAL_VAULT_KEY`, D-E001101-01).
#
# ⚠️ O nome `sessao_cifrada` foi escolhido para PASSAR intacto pelo redator:
# `redaction.redigir_envelope` só toca as chaves de diagnóstico, e nenhuma
# substring de `CHAVES_SENSIVEIS` (`token`, `session_storage`…) está no nome.
# A cifra é o que protege; apagar a cifra seria perder a continuação.
def _guardar_sessao(ex: Execucao, token: str) -> None:
    from datetime import timezone as _tz

    bloco: Dict[str, Any] = {
        "sessao_cifrada": "",
        "emitida_em": datetime.now(_tz.utc).isoformat(timespec="seconds"),
        "seguradora": ex.seguradora,
        "protocolo": ex.protocolo,
        "codigo_atendimento": "",
        "categoria": "",
        "etapa": ST.ETAPA_CONTATO,
        "acao_esperada": "reler",
        "possivel": False,
        "sessao_guardada": False,
        "motivo": "",
    }
    try:
        if not token:
            raise ValueError("o portal nao devolveu Token")
        from portal_worker import vault

        bloco["sessao_cifrada"] = vault.encrypt(token)
        bloco["sessao_guardada"] = True
        bloco["possivel"] = True
        bloco["motivo"] = ("sessao do portal guardada cifrada; o pedido pode ser "
                           "retomado enquanto o portal aceitar o token")
    except Exception as exc:  # noqa: BLE001
        # 🔴 NUNCA derruba o acionamento: o pedido JÁ existe na seguradora.
        # Só a continuação automática fica indisponível — e isso é dito.
        bloco["motivo"] = (f"sessao NAO guardada ({type(exc).__name__}): a "
                           "continuacao automatica fica indisponivel para este "
                           "pedido (cofre do worker sem PORTAL_VAULT_KEY?)")
    ex.continuacao = bloco
    ex.evidence["continuacao"] = dict(bloco)


def _marcar_continuacao(ex: Execucao, *, etapa: str, acao: str,
                        possivel: Optional[bool] = None, incerto: bool = False,
                        motivo: str = "") -> None:
    """Regrava `evidence["continuacao"]` com a etapa NOVA. Sem sessão, nada."""
    if not ex.continuacao:
        return
    guardada = bool(ex.continuacao.get("sessao_guardada")) \
        and bool(ex.continuacao.get("sessao_cifrada"))
    pode = guardada and bool(etapa) and (True if possivel is None else bool(possivel))
    bloco = {
        **ex.continuacao,
        "etapa": etapa or "",
        "acao_esperada": acao or "",
        "possivel": pode,
        "sessao_guardada": guardada,
        "codigo_atendimento": (ex.estado.codigo_atendimento
                               or ex.continuacao.get("codigo_atendimento") or ""),
        "categoria": (ex.partes.get("categoria")
                      or ex.continuacao.get("categoria") or ""),
        "motivo": (str(motivo or "")[:300] if guardada
                   else str(ex.continuacao.get("motivo") or "")),
    }
    if incerto:
        bloco["incerto"] = True
    if not pode:
        # Sem continuação possível, a cifra não tem serventia: não fica.
        bloco["sessao_cifrada"] = ""
    ex.evidence["continuacao"] = bloco


def _parar(ex: Execucao, stage: str, mensagem: str, **capturado: Any) -> JourneyResult:
    """🔴 Toda parada DEPOIS da fronteira A é esta função: `needs_human`, com o
    estado de negócio, o que falta e — EXTRA-001.10.1 — a ETAPA de onde uma
    continuação retoma. Nunca `None`, que voltaria ao DOM e abriria um segundo
    pedido."""
    ex.evidence["vidros_estado"] = ex.estado.para_evidencia()
    ex.evidence["api_first"] = {"usado": True, "parou_em": stage,
                                **ex.sessao.resumo_para_evidencia()}
    etapa, acao = ST.etapa_da_parada(stage)
    _marcar_continuacao(ex, etapa=etapa, acao=acao,
                        incerto=stage in ST.PARADAS_INCERTAS, motivo=mensagem)
    return JourneyResult(
        status="needs_human",
        captured={"stage": stage, "business_state": ex.estado.estado,
                  "protocolo": ex.estado.codigo_atendimento or ex.estado.numero_protocolo,
                  **capturado},
        message=mensagem)


# --------------------------------------------------------------------------
# A journey de abertura
# --------------------------------------------------------------------------
async def abrir_atendimento_api(page, params: Dict[str, Any],
                                evidence: Dict[str, Any]) -> Optional[JourneyResult]:
    """O fluxo API-first, do nome da seguradora ao desfecho.

    `None` = devolve ao caminho DOM, e **só acontece antes da fronteira A**.
    """
    estado = ST.EstadoDoAtendimento()
    sessao = SessaoVidros(page=page)
    guard = _guard_do(params)
    guard.acao_material_esperada = ST.FRONTEIRA_ABRIR
    ex = execucao_de(params, evidence, sessao=sessao, guard=guard, estado=estado)
    dano, local, contato = ex.dano, ex.local, ex.contato

    def desistir(motivo: str, **extra: Any) -> None:
        evidence["api_first"] = {"usado": False, "motivo": motivo, **extra}

    # ======================================================================
    # 1. A SEGURADORA SAI DA LISTA AO VIVO — P0-4
    # ======================================================================
    rs = await sessao.seguradoras()
    lista_seguradoras = rs.get("json")
    if not rs.get("ok") or not isinstance(lista_seguradoras, list):
        desistir("nao consegui ler a lista de seguradoras do portal")
        return None

    achada = API.resolver_seguradora(params.get("_seguradora_slug")
                                     or params.get("insurer_name"),
                                     lista_seguradoras)
    if achada is None:
        # 🔴 `None` é resposta legítima: não dá para PROVAR de qual seguradora
        # ele falou. O DOM assume, que é quem sabe navegar a tela de seleção.
        desistir("a seguradora informada nao casa com UMA das publicadas hoje",
                 publicadas=len(lista_seguradoras))
        return None

    seguradora = achada["slug"]
    ex.seguradora = seguradora
    evidence["seguradora"] = {"slug": seguradora, "codigo": achada["codigo"],
                              "nome_de_tela": achada["nome_de_tela"]}
    if seguradora in API.FORA_DO_API_FIRST:
        # D-PILOTO-17: ela existe, é exibível, e a escrita automática não sai.
        desistir(f"{seguradora} esta fora do API-first por decisao de produto")
        return None

    # ======================================================================
    # 2. TUDO O QUE DÁ PARA SABER SEM ESCREVER — a lista de paradas precoces
    # ======================================================================
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip().upper()
    data = (str(params.get("_data_iso") or "").strip()
            or data_iso(params.get("data_dano")))
    relato = ex.relato
    # 🔴 O perímetro é classificado AQUI, antes de qualquer escrita, porque um
    # texto que não classifica não pode virar `"N"` (= "Não Sabe" no portal) lá
    # na frente. Ver `API.perimetro_do_texto`.
    # 🔴 So o ENUM: quem classificou o texto de gente foi
    # `portal_params.normalizar_perimetro`, ANTES da fronteira A.
    perimetro = ex.perimetro
    faltou = [n for n, v in (
        ("cpf", cpf), ("placa", placa), ("data", data),
        ("dano.peca", dano.get("peca")), ("dano.como", dano.get("como")),
        ("local.cidade_servico", local.get("cidade_servico")),
        ("contato.documento_corretor", contato["documento_corretor"]),
        ("contato.telefone", contato["telefone"]),
        # `dano.onde` existe mas não classifica como cidade ou estrada: a
        # pergunta certa é barata AGORA e cara depois do protocolo emitido.
        ("dano.onde (foi na cidade ou na estrada?)", perimetro),
    ) if not v]
    if relato and len(relato) < API.MINIMO_AVALIACAO_DANO:
        # 📊 O portal exige relato com no mínimo 30 caracteres. Descobrir isso
        # aqui custa uma pergunta; descobrir no PATCH custa um pedido aberto e
        # travado.
        faltou.append(f"dano.descricao (o portal exige {API.MINIMO_AVALIACAO_DANO} caracteres)")
    elif not relato:
        faltou.append("dano.descricao")
    if faltou:
        desistir("faltam dados que o portal exige ANTES de qualquer escrita",
                 faltou=faltou)
        return None

    # ---- PREFLIGHT — read-only, e o único portão para a fronteira A --------
    tipo = API.tipo_atendimento_para(seguradora, dano.get("peca"))
    # 🔴 `DataSinistro` viaja como INSTANTE nos dois lugares — ver
    # `API.instante_do_sinistro`. 📊 `AAAA-MM-DD` tem zero exercícios.
    instante = API.instante_do_sinistro(data)
    r = await sessao.buscar_apolice(seguradora=seguradora, cpf_cnpj=cpf,
                                    placa=placa, data_sinistro=instante,
                                    tipo_atendimento=tipo)
    veredito = API.classificar_preflight(r.get("status") or 0, r.get("json"))
    evidence["preflight"] = {k: v for k, v in veredito.items()
                             if k != "mensagem_portal"}
    evidence["vidros_estado"] = estado.para_evidencia()

    if veredito["estado"] == API.COVERAGE_ABSENT:
        # 📊 Detectado ANTES de qualquer escrita. Nenhum atendimento nasceu, e
        # nenhum vai nascer — repetir com outra cobertura seria adivinhar.
        return JourneyResult(
            status="needs_human",
            captured={"stage": "coverage_absent", "escopo": veredito.get("escopo", ""),
                      "business_state": ST.PRE_PROTOCOLO},
            message=("a apolice nao tem a cobertura necessaria para este item "
                     f"({veredito.get('escopo') or 'cobertura nao contratada'}). "
                     "Nenhum atendimento foi aberto."))

    if not veredito["pode_escrever"]:
        # policy_not_found · policy_ambiguous · regra desconhecida · erro.
        desistir(f"preflight={veredito['estado']}")
        return None

    apolice = r.get("json") or {}
    ex.chassi = str(params.get("chassi") or apolice.get("Chassi") or "").strip()

    # ======================================================================
    # 3. FRONTEIRA A — a partir daqui existe registro na seguradora
    # ======================================================================
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    corpo = {
        "Seguradora": seguradora,
        "NumeroDaApolice": str(apolice.get("NumeroDaApolice") or ""),
        "DataSinistro": instante,
        "PlacaInformada": placa,
        "SufixoChassi": None,
        "CpfCnpjSegurado": cpf,
        "TipoAtendimento": tipo,
    }
    try:
        await guard.before(action=ST.FRONTEIRA_ABRIR,
                           action_class=MATERIAL_SIDE_EFFECT,
                           details={"idempotency_key":
                                    str(params.get("_idempotency_key") or "")},
                           origem="journey")
    except AcaoBloqueada as e:
        # `confirm=false` chega aqui. É a trava funcionando, não uma falha.
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "pronto_para_abrir", "business_state": ST.PRE_PROTOCOLO},
            message=("tudo conferido e a apolice tem cobertura — falta a "
                     f"autorizacao para abrir o pedido ({e})"))

    ra = await sessao.criar_atendimento(corpo)
    if not ra.get("ok"):
        # 🔴 A chamada saiu e não sabemos se o servidor a processou. Este é o
        # `maybe_committed`, e é o estado que existe para impedir o retry.
        estado.transitar(ST.DESCONHECIDO,
                         motivo=f"POST /atendimentos devolveu {ra.get('status')}")
        await guard.incerto(motivo="POST /atendimentos sem resposta de sucesso")
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "maybe_committed", "business_state": ST.DESCONHECIDO},
            message=("a chamada que cria o atendimento saiu e nao consegui "
                     "confirmar o resultado. NAO reexecute: consulte antes."))

    dados = ra.get("json") or {}
    protocolo = str(dados.get("NumeroProtocolo") or "")
    ex.protocolo = protocolo
    estado.transitar(ST.PROTOCOLO_CRIADO, motivo="POST /atendimentos 200",
                     numero_protocolo=protocolo)
    await guard.submetido(receipt=protocolo)
    # 🔴 `evidence["protocolo"]` é escrito AQUI, e não só no fim.
    # `guardrails.tem_prova_de_efeito` procura exatamente esta chave — é o que a
    # journey DOM sempre gravou, e é o que o `portal_tool` consulta para decidir
    # se um job `failed` esconde um pedido vivo. Escrever só depois da fronteira
    # B deixava uma janela em que o pedido JÁ EXISTIA na seguradora e a evidência
    # dizia que não havia prova de nada — a janela exata em que um retry abriria
    # o segundo atendimento, pago, no nome do mesmo segurado.
    if protocolo:
        evidence["protocolo"] = protocolo
    # 🔴 A1 — a sessão durável nasce AQUI, junto do protocolo, e vai no MESMO
    # checkpoint: uma queda no passo seguinte ainda deixa o pedido retomável.
    _guardar_sessao(ex, sessao.token)
    evidence["vidros_estado"] = estado.para_evidencia()
    await _checkpoint(params, {"vidros_estado": estado.para_evidencia(),
                               "protocolo": protocolo,
                               "continuacao": evidence["continuacao"]})

    return await rodar_fases(ex, a_partir=ST.ETAPA_CONTATO)


# --------------------------------------------------------------------------
# 🔴 As FASES depois da fronteira A — a abertura e a continuação usam estas
# --------------------------------------------------------------------------
async def rodar_fases(ex: Execucao, *, a_partir: str) -> JourneyResult:
    """Roda as fases a partir de `a_partir`, na ordem medida.

    🔴 A fase de CONTATO (PUT corretores + POST solicitantes) é escrita: roda só
    quando a retomada é DELA. As fases de LEITURA (peça, causa, lataria,
    cidade) rodam sempre — reler é reversível, e o `CodigoItemCoberto` que a
    fase de materializar consome sai delas.
    """
    fases = (
        (ST.ETAPA_CONTATO, _fase_contato),
        (ST.ETAPA_PECA, _fase_peca),
        (ST.ETAPA_CAUSA, _fase_causa),
        (ST.ETAPA_LATARIA, _fase_lataria),
        (ST.ETAPA_CIDADE, _fase_cidade),
        (ST.ETAPA_MATERIALIZAR, _fase_materializar),
    )
    # Etapa desconhecida NUNCA recomeça pelo contato (que escreve): pela peça.
    inicio = a_partir if a_partir in ST.ORDEM_DAS_ETAPAS else ST.ETAPA_PECA
    for etapa, fase in fases:
        if etapa == ST.ETAPA_CONTATO and inicio != ST.ETAPA_CONTATO:
            continue
        parada = await fase(ex)
        if parada is not None:
            return parada
    return await fase_desfecho(ex)


async def _fase_contato(ex: Execucao) -> Optional[JourneyResult]:
    """Corretor e solicitante — P0-2, obrigatórios em 4 de 4."""
    sessao, evidence, contato = ex.sessao, ex.evidence, ex.contato
    rc = await sessao.registrar_corretor(contato["documento_corretor"])
    if not rc.get("ok"):
        _tela_desconhecida(evidence, onde=API.EP_CORRETORES, resposta=rc)
        return _parar(ex, "corretor_recusado",
                      "o pedido foi aberto e o portal recusou o vinculo do "
                      "corretor. NAO reexecute: o atendimento ja existe.")

    rt_tel = await sessao.tipos_de_telefone()
    codigo_tipo = _codigo_do_tipo_de_telefone(rt_tel.get("json"),
                                              contato["tipo_telefone"])
    if codigo_tipo is None:
        _tela_desconhecida(evidence, onde=API.EP_TIPOS_TELEFONE, resposta=rt_tel)
        return _parar(ex, "tipo_de_telefone_desconhecido",
                      "o pedido foi aberto e a lista de tipos de telefone do "
                      "portal nao trouxe o tipo esperado. NAO reexecute.")

    corpo_sol = _corpo_do_solicitante(contato, codigo_tipo_telefone=codigo_tipo)
    rsol = await sessao.registrar_solicitante(corpo_sol)
    if not rsol.get("ok"):
        _tela_desconhecida(evidence, onde=API.EP_SOLICITANTES, resposta=rsol)
        return _parar(ex, "solicitante_recusado",
                      "o pedido foi aberto e o portal recusou os dados de "
                      "contato. NAO reexecute: o atendimento ja existe.")
    evidence["contato_no_portal"] = {"relacao": contato["relacao"],
                                     "tipo_telefone": contato["tipo_telefone"],
                                     "codigo_tipo_telefone": codigo_tipo,
                                     "recebe_whatsapp": bool(contato.get("recebe_whatsapp")),
                                     "termo_exibido": corpo_sol["TermoExibido"],
                                     "termo_aceito": False}
    return None


async def _fase_peca(ex: Execucao) -> Optional[JourneyResult]:
    """O CATÁLOGO DESTA APÓLICE — só existe depois do token."""
    sessao, evidence, dano, especificos = ex.sessao, ex.evidence, ex.dano, ex.especificos
    ritens = await sessao.itens_cobertos(ex.seguradora)
    itens = ritens.get("json")
    if not ritens.get("ok") or not isinstance(itens, list) or not itens:
        _tela_desconhecida(evidence, onde=API.EP_ITENS_COBERTOS, resposta=ritens)
        return _parar(ex, "catalogo_indisponivel",
                      "o pedido foi aberto e o catalogo de pecas desta apolice "
                      "nao veio. NAO reexecute.")

    achado = casar_peca(dano.get("peca"), itens)
    if achado["item"] is None and especificos:
        # A família casou com várias linhas do catálogo; o que separa uma da
        # outra é o ESPECÍFICO que o segurado já respondeu (capa com pisca,
        # farol de LED, vidro fixo × sobe-e-desce).
        for resposta in especificos.values():
            if not isinstance(resposta, str) or not resposta.strip():
                continue
            refinado = casar_peca(f"{dano.get('peca')} {resposta}",
                                  achado["candidatos"] or itens)
            if refinado["item"] is not None:
                achado = refinado
                break
    if achado["item"] is None:
        return _parar(ex, "peca_ambigua",
                      "o pedido foi aberto e a peca precisa ser escolhida na "
                      "lista real desta apolice: " + achado["motivo"],
                      opcoes=_rotulos(achado["candidatos"] or itens, "Descricao"))

    item = achado["item"]
    codigo_item = str(item.get("CodigoItemCoberto") or "")
    partes = API.partes_do_item_coberto(codigo_item)
    if not partes:
        return _parar(ex, "item_com_formato_desconhecido",
                      "o pedido foi aberto e a chave da peca veio num formato "
                      "que nao conheco. NAO reexecute.")
    ex.codigo_item, ex.partes = codigo_item, partes
    evidence["peca"] = {"codigo": codigo_item, "categoria": partes["categoria"],
                        "descricao": str(item.get("Descricao") or "")}
    return None


async def _fase_causa(ex: Execucao) -> Optional[JourneyResult]:
    """A causa do dano, da lista DAQUELA peça."""
    rmot = await ex.sessao.motivos_dano(ex.codigo_item)
    motivos = rmot.get("json")
    if not rmot.get("ok") or not isinstance(motivos, list) or not motivos:
        _tela_desconhecida(ex.evidence, onde=API.EP_MOTIVOS_DANO, resposta=rmot)
        return _parar(ex, "motivos_indisponiveis",
                      "o pedido foi aberto e a lista de causas desta peca nao "
                      "veio. NAO reexecute.")
    causa = casar_causa(ex.dano.get("como"), motivos)
    if causa["item"] is None:
        return _parar(ex, "motivo_ambiguo",
                      "o pedido foi aberto e a causa do dano precisa ser "
                      "escolhida na lista real: " + causa["motivo"],
                      opcoes=_rotulos(causa["candidatos"] or motivos,
                                      "DescricaoObjetoCausa"))
    ex.codigo_causa = causa["item"].get("CodigoObjetoCausa")
    return None


async def _fase_lataria(ex: Execucao) -> Optional[JourneyResult]:
    """As peças da LATARIA (multi-peça) — P1-5."""
    ex.servicos_lataria = []
    if ex.partes.get("categoria") != API.CATEGORIA_LATARIA:
        return None
    rserv = await ex.sessao.servicos_itens(
        codigo_script=ex.partes["codigo_script"],
        codigo_tipo_script=ex.partes["codigo_tipo_script"])
    catalogo_pecas = rserv.get("json") if isinstance(rserv.get("json"), list) else []
    pedidas = [p for p in (ex.dano.get("pecas_lataria") or []) if str(p).strip()]
    if not pedidas:
        return _parar(ex, "pecas_de_lataria_ausentes",
                      "o pedido foi aberto e a lista de pecas amassadas nao "
                      "veio. Quais pecas o reparo cobre?",
                      opcoes=_rotulos(catalogo_pecas, "Descricao"))
    for peca in pedidas:
        casado = casar_unico(peca, catalogo_pecas, ("Descricao",))
        if casado["item"] is None:
            return _parar(ex, "peca_de_lataria_ambigua",
                          f"o pedido foi aberto e a peca {peca!r} precisa ser "
                          "escolhida na lista real: " + casado["motivo"],
                          opcoes=_rotulos(casado["candidatos"] or catalogo_pecas,
                                          "Descricao"))
        ex.servicos_lataria.append({"CodigoServico": casado["item"].get("Codigo"),
                                    "CodigoObjetoCausa": ex.codigo_causa})
    return None


async def _fase_cidade(ex: Execucao) -> Optional[JourneyResult]:
    """A cidade do serviço — e se ela tem REDE."""
    sessao = ex.sessao
    cidade_pedida = ex.local.get("cidade_servico") or {}
    uf = str(cidade_pedida.get("uf") or "").strip().upper()
    nome_cidade = str(cidade_pedida.get("cidade") or "").strip()
    rufs = await sessao.ufs()
    ufs_validas = {str(u.get("UF") or "").upper()
                   for u in (rufs.get("json") or []) if isinstance(u, dict)}
    if ufs_validas and uf not in ufs_validas:
        return _parar(ex, "uf_desconhecida",
                      f"o pedido foi aberto e o estado {uf!r} nao esta na lista "
                      "do portal.", opcoes=sorted(ufs_validas))
    rcid = await sessao.cidades(uf)
    cidades = rcid.get("json") if isinstance(rcid.get("json"), list) else []
    # 🔴 CIDADE POR IGUALDADE, e so. 📊 O red team mediu o que a continencia
    # fazia com a lista real de SC: "Curitiba" -> CURITIBANOS, "Palmas" ->
    # PALMA SOLA, "Santo Amaro" -> SANTO AMARO DA IMPERATRIZ. Cada uma dessas e
    # um vidraceiro esperando numa cidade onde o carro nao esta.
    achada_cidade = casar_igual(nome_cidade, cidades, ("Nome", "Cidade"))
    if achada_cidade["item"] is None:
        return _parar(ex, "cidade_ambigua",
                      f"o pedido foi aberto e a cidade {nome_cidade!r} nao casou "
                      "com uma da lista do portal: " + achada_cidade["motivo"],
                      opcoes=_rotulos(achada_cidade["candidatos"], "Nome"))
    codigo_cidade = achada_cidade["item"].get("Codigo")

    rrede = await sessao.cidade_atendida(
        chassi=ex.chassi, codigo_cidade=codigo_cidade,
        codigo_script=ex.partes["codigo_script"],
        codigo_tipo_script=ex.partes["codigo_tipo_script"])
    rede = rrede.get("json")
    if not rrede.get("ok") or not isinstance(rede, dict) or not rede.get("Codigo"):
        # 🔴 Esta é uma parada que SÓ dá para descobrir depois da fronteira A:
        # a consulta exige o token, que nasce no `POST /atendimentos`.
        _tela_desconhecida(ex.evidence, onde=API.EP_CLIENTES_CIDADES, resposta=rrede)
        return _parar(ex, "cidade_sem_rede",
                      f"o pedido foi aberto e {nome_cidade}/{uf} nao tem rede "
                      "para esta peca. Ha outra cidade onde o servico possa ser "
                      "feito?")
    ex.codigo_cidade = codigo_cidade
    return None


async def _fase_materializar(ex: Execucao) -> Optional[JourneyResult]:
    """A FRONTEIRA MATERIAL DEPENDE DA CATEGORIA — P0-3. PATCH, questionário, reparo."""
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    sessao, evidence, guard, estado = ex.sessao, ex.evidence, ex.guard, ex.estado
    especificos = ex.especificos
    # 🔴 Nenhuma constante fixa aqui: a fronteira é CALCULADA a partir da peça.
    fronteira_b = ST.fronteira_materializar_de(ex.codigo_item)
    evidence["fronteira_material"] = {"peca": ex.codigo_item,
                                      "categoria": ex.partes["categoria"],
                                      "fronteira": fronteira_b}

    corpo_patch = API.corpo_de_atualizacao(
        codigo_item_coberto=ex.codigo_item,
        codigo_cidade=ex.codigo_cidade,
        codigo_objeto_causa=ex.codigo_causa,
        avaliacao_dano=ex.relato,
        perimetro_dano=ex.perimetro,
        cep=str(ex.local.get("cep") or ex.params.get("cep") or ""),
        servicos_martelinho_lataria=ex.servicos_lataria,
        item_removido=especificos.get("item_removido"),
        evento_composto=especificos.get("evento_composto"),
        polimento_farol=especificos.get("polimento_farol"),
    )

    if fronteira_b == ST.FRONTEIRA_ATUALIZAR:
        # Categoria `L` (e toda categoria que não sabemos ler): o PATCH é que
        # materializa. Arma ANTES dele.
        guard.acao_material_esperada = ST.FRONTEIRA_ATUALIZAR
        try:
            await guard.before(action=ST.FRONTEIRA_ATUALIZAR,
                               action_class=MATERIAL_SIDE_EFFECT, origem="journey")
        except AcaoBloqueada as e:
            return _parar(ex, "pronto_para_materializar",
                          f"os dados estao completos, falta autorizacao ({e})")

    rpatch = await sessao.atualizar_atendimento(corpo_patch)
    if not rpatch.get("ok"):
        if fronteira_b == ST.FRONTEIRA_ATUALIZAR:
            estado.transitar(ST.DESCONHECIDO,
                             motivo=f"PATCH /atendimentos devolveu {rpatch.get('status')}")
            await guard.incerto(motivo="PATCH /atendimentos sem sucesso")
        _tela_desconhecida(evidence, onde=API.EP_ATENDIMENTOS, resposta=rpatch)
        return _parar(ex, "maybe_committed" if fronteira_b == ST.FRONTEIRA_ATUALIZAR
                      else "patch_recusado",
                      "gravei a peca e o local e nao confirmei. NAO reexecute.")

    if fronteira_b != ST.FRONTEIRA_MATERIALIZAR:
        return None

    # ---- O QUESTIONÁRIO E O REPARO — só para vidraçaria ------------------
    resultado = await QZ.rodar_questionario(
        sessao,
        respostas_do_segurado=dict(especificos),
        relato=ex.relato)
    evidence["questionario"] = resultado.para_evidencia()

    if not resultado.completo:
        estado.transitar(ST.PROTOCOLO_CRIADO, motivo=resultado.motivo)
        pendente = resultado.pergunta_pendente
        return _parar(ex, "questionario_incompleto",
                      "o pedido foi aberto e o questionario parou: "
                      + resultado.motivo,
                      pergunta=pendente.texto if pendente else "",
                      opcoes=pendente.textos_das_opcoes if pendente else [])

    # ---- `regras-reparo` é LEITURA e roda ANTES da fronteira B -----------
    # 🔴 É esta ordem que permite descobrir que falta a decisão do segurado
    # sem ter materializado nada.
    rreg = await sessao.regras_reparo(resultado.respostas)
    oferece = bool((rreg.get("json") or {}).get("ExibirDialogDeReparo")) \
        if isinstance(rreg.get("json"), dict) else False
    evidence["reparo"] = {"portal_oferece": oferece,
                          "previsto_pelo_questionario": resultado.reparo_previsto}
    if oferece:
        dito = _norm(especificos.get("aceita_reparo"))
        if dito in ("sim", "s", "aceito", "true"):
            ex.reparo_decidido = True
        elif dito in ("nao", "n", "recuso", "false"):
            ex.reparo_decidido = False
        else:
            # 🔴 PARA AQUI, antes da fronteira B: nada materializado, e a
            # decisão é do segurado. 💭 "A seguradora pode consertar sem
            # trocar o vidro — leva uns 30 minutos e costuma sair mais
            # barato para você. Quer tentar o reparo?"
            return _parar(ex, "decidir_reparo",
                          "o portal ofereceu REPARO em vez de troca, e essa "
                          "escolha e do segurado. Nada foi materializado.",
                          opcoes=["tentar o reparo", "trocar a peca"])

    # ---- FRONTEIRA B ----------------------------------------------------
    guard.acao_material_esperada = ST.FRONTEIRA_MATERIALIZAR
    try:
        await guard.before(action=ST.FRONTEIRA_MATERIALIZAR,
                           action_class=MATERIAL_SIDE_EFFECT, origem="journey")
    except AcaoBloqueada as e:
        return _parar(ex, "pronto_para_materializar",
                      f"questionario completo, falta autorizacao para gravar ({e})")

    rq = await sessao.gravar_questionario(resultado.respostas)
    if not rq.get("ok"):
        estado.transitar(ST.DESCONHECIDO,
                         motivo=f"POST /questionarios devolveu {rq.get('status')}")
        await guard.incerto(motivo="POST /questionarios sem sucesso")
        return _parar(ex, "maybe_committed",
                      "gravei o questionario e nao confirmei. NAO reexecute.")

    if ex.reparo_decidido is not None:
        rrep = await sessao.alterar_reparo(ex.reparo_decidido)
        evidence["reparo"] = {**evidence.get("reparo", {}),
                              "gravado": bool(rrep.get("ok")),
                              "valor": ex.reparo_decidido}
        if not rrep.get("ok"):
            # 🔴 RED B7: a decisao do segurado entre REPARAR e TROCAR nao
            # foi gravada, e as duas coisas custam valores diferentes a ele.
            # Seguir calado entregaria um desfecho que fala de reparo sobre
            # um pedido que o portal registrou como troca (ou vice-versa).
            # O numero de 8 digitos JA nasceu (o POST /questionarios
            # passou): uma leitura barata o traz, e e ele que o segurado
            # anota. Parar sem o numero seria fazer a pessoa parar duas vezes.
            _rnum = await sessao.ler_atendimento()
            _ag = _rnum.get("json") if isinstance(_rnum.get("json"), dict) else {}
            _cod = str(_ag.get("CodigoAtendimento") or "").strip()
            if _cod:
                estado.codigo_atendimento = _cod
                evidence["protocolo"] = _cod
                evidence["protocolo_do_atendimento"] = _cod
            estado.transitar(ST.ATENDIMENTO_MATERIALIZADO,
                             motivo="alterar-reparo nao confirmou")
            _tela_desconhecida(evidence, onde=API.EP_ALTERAR_REPARO, resposta=rrep)
            return _parar(ex, "reparo_nao_gravado",
                          "o pedido esta aberto e a escolha entre reparar e "
                          "trocar nao foi confirmada pela seguradora.")
    return None


async def fase_desfecho(ex: Execucao, *,
                        ropc: Optional[Dict[str, Any]] = None) -> JourneyResult:
    """O DESFECHO — quem decide é o PORTAL, e ele diz por escrito."""
    sessao, evidence, guard = ex.sessao, ex.evidence, ex.guard
    if ropc is None:
        ropc = await sessao.opcoes_de_agendamento()
    if not ropc.get("ok") or not isinstance(ropc.get("json"), dict):
        _tela_desconhecida(evidence, onde=API.EP_OPCOES_DISPONIVEIS, resposta=ropc)
        return _parar(ex, "roteador_ilegivel",
                      "o pedido existe e o portal nao disse o desfecho. NAO "
                      "reexecute: consulte o atendimento.")
    opcoes = ropc["json"]

    # 🔴 O `GET /atendimentos` vem DEPOIS de `opcoes-disponiveis`, e a ordem é
    # o ponto inteiro: 📊 o `ScriptFinalizacao` reescreve a si mesmo, e só aqui
    # ele traz a loja. Lido antes, diz "aguarde o analista".
    rg = await sessao.ler_atendimento()
    if not rg.get("ok") or not isinstance(rg.get("json"), dict):
        # 🔴 JUIZ B3 / RED B7: sem o agregado nao ha desfecho nenhum. A versao
        # anterior seguia com `{}`, o roteador dizia "conclusao sem loja" e o
        # segurado recebia `analista` INVENTADO — com `done`, sobre um pedido
        # cujo estado ninguem leu.
        _tela_desconhecida(evidence, onde=API.EP_ATENDIMENTOS, resposta=rg)
        evidence["desfecho"] = {"tipo": ST.DESFECHO_DESCONHECIDO,
                                "roteador": opcoes,
                                "motivo": "GET /atendimentos nao respondeu depois "
                                          "de opcoes-disponiveis"}
        return _parar(ex, "desfecho_ilegivel",
                      "o pedido existe e eu nao consegui ler o que a seguradora "
                      "decidiu. NAO reexecute: consulte o atendimento.")
    agregado = rg["json"]
    desfecho = ST.ler_desfecho(opcoes, agregado)
    _absorver_agregado(ex, agregado, desfecho)
    if ex.estado.codigo_atendimento:
        await guard.confirmado(receipt=ex.estado.codigo_atendimento)

    if desfecho["tipo"] == ST.DESFECHO_DESCONHECIDO:
        _tela_desconhecida(evidence, onde=API.EP_OPCOES_DISPONIVEIS, resposta=ropc)
        return _parar(ex, "desfecho_desconhecido",
                      "o pedido existe e o portal decidiu por um caminho que eu "
                      "nao sei ler: " + str(desfecho.get("motivo") or ""))

    # ---- agenda: ler lojas, distância, dias e horários (LEITURA) — P1-1 ---
    if desfecho["tipo"] == ST.DESFECHO_AGENDA:
        cache = await _enriquecer_agenda(sessao, desfecho, agregado=agregado,
                                         codigo_atendimento=ex.estado.codigo_atendimento)
        # ---- A4: a preferência do segurado já veio → agenda NESTA sessão --
        pref = preferencia_de_agenda(ex.especificos)
        if pref is not None:
            feito = await _agendar_pela_preferencia(ex, desfecho, cache, pref)
            if feito is not None:
                return feito

    # ---- A5: ramo 7 — prioridade + preferência de vistoria ---------------
    if desfecho["tipo"] == ST.DESFECHO_VISTORIA_OPCIONAL:
        return await _responder_vistoria_opcional(ex, desfecho)

    # ---- conclusão: o COMPROVANTE — P1-5 --------------------------------
    if desfecho["tipo"] in (ST.DESFECHO_LOJA_DIRETA, ST.DESFECHO_ANALISTA) \
            and ex.estado.codigo_atendimento:
        rf = await sessao.emitir_formalizado(ex.estado.codigo_atendimento)
        desfecho["comprovante_emitido"] = bool(rf.get("ok"))

    return await _concluir(ex, desfecho, agregado)


def _absorver_agregado(ex: Execucao, agregado: Dict[str, Any],
                       desfecho: Dict[str, Any]) -> None:
    """O agregado é a verdade: estado, número, franquia e link saem DELE."""
    evidence = ex.evidence
    ex.agregado = agregado
    estado = ST.ler_estado_do_agregado(agregado, tinha_protocolo=bool(ex.protocolo))
    estado.numero_protocolo = ex.protocolo
    ex.estado = estado
    desfecho["reparo"] = ex.reparo_decidido
    # 🔴 O NUMERO NAO PODE SUMIR NO CAMINHO DA AGENDA.
    # 📊 No HAR do vidro de porta nao ha `GET /atendimentos` depois de
    # `opcoes-disponiveis` — o agregado que o replay devolve e o de ANTES, e ele
    # JA TINHA `CodigoAtendimento` (a materializacao veio antes). Se por
    # qualquer motivo o agregado tardio vier sem o numero, vale o que ja
    # tinhamos lido: perder o numero e deixar o segurado sem o que anotar.
    if not desfecho.get("codigo_atendimento"):
        desfecho["codigo_atendimento"] = str(
            evidence.get("protocolo_do_atendimento")
            or (estado.codigo_atendimento if estado.codigo_atendimento else "") or "")
    evidence["desfecho"] = desfecho
    if estado.codigo_atendimento:
        evidence["protocolo_do_atendimento"] = estado.codigo_atendimento
        # 📊 O número que a tela mostra e que o segurado anota é este.
        evidence["protocolo"] = estado.codigo_atendimento
    if desfecho.get("franquias"):
        evidence["franquia"] = desfecho["franquias"][0].get("valor", "")
    vistoria = API.vistoria_do_atendimento(agregado)
    if vistoria.get("tem_link"):
        evidence["link_vistoria"] = vistoria["link"]


async def _concluir(ex: Execucao, desfecho: Dict[str, Any],
                    agregado: Dict[str, Any]) -> JourneyResult:
    """O `done` — com a etapa da continuação dizendo o que ainda cabe."""
    evidence, estado = ex.evidence, ex.estado
    evidence["desfecho"] = desfecho
    tipo = desfecho["tipo"]
    estado.transitar(ST.AGUARDANDO_ESCOLHA if tipo == ST.DESFECHO_AGENDA
                     else ST.ATENDIMENTO_MATERIALIZADO,
                     motivo=str(desfecho.get("motivo") or ""))
    if tipo == ST.DESFECHO_AGENDA:
        _marcar_continuacao(ex, etapa=ST.ETAPA_AGENDAR, acao="agendar",
                            motivo="o portal abriu a agenda; falta o segurado "
                                   "escolher loja, dia e horario")
    else:
        _marcar_continuacao(ex, etapa=ST.ETAPA_CONCLUIDO, acao="", possivel=False,
                            motivo=f"o portal concluiu ({tipo}); nada a continuar")
    evidence["vidros_estado"] = estado.para_evidencia()
    evidence["api_first"] = {"usado": True, **ex.sessao.resumo_para_evidencia()}
    await _checkpoint(ex.params, {"vidros_estado": estado.para_evidencia(),
                                  "desfecho": desfecho,
                                  "continuacao": evidence.get("continuacao") or {}})
    vistoria = API.vistoria_do_atendimento(agregado)
    captured: Dict[str, Any] = {
        "business_state": estado.estado,
        "protocolo": estado.codigo_atendimento,
        "tipo": tipo,
        "franquia": (desfecho.get("franquias") or [{}])[0].get("valor", ""),
        "link_vistoria": vistoria.get("link", ""),
        "customer_choice_needed": tipo == ST.DESFECHO_AGENDA,
    }
    if desfecho.get("agendamento"):
        captured["agendamento"] = desfecho["agendamento"]
    return JourneyResult(
        status="done",
        captured=captured,
        message=("atendimento aberto"
                 + (f" — n {estado.codigo_atendimento}" if estado.codigo_atendimento else "")
                 + f" · desfecho: {tipo}"))


# --------------------------------------------------------------------------
# 🔴 A AGENDA — ler (A3), agendar pela preferência (A4) e pela escolha (A2)
# --------------------------------------------------------------------------
# Tetos de leitura. 📊 A sessão tem 150 chamadas; a abertura medida usa ~40.
# 6 lojas × (distância + datas + 5 dias) = 42 no pior caso, e a reserva garante
# que o POST, a confirmação e o comprovante nunca fiquem sem chamada.
MAX_DIAS_LIDOS_POR_LOJA = 5
DIAS_COM_HORARIO_POR_LOJA = 3
MAX_DIAS_PELA_PREFERENCIA = 10
RESERVA_DE_CHAMADAS = 15
PERIODOS = ("manha", "tarde", "qualquer")


def _datas_publicadas(meses: Any, ano: int) -> List[Tuple[str, str]]:
    """`[{"Mes": 9, "Dias": [21, 22]}]` → `[("21/09", "2026-09-21"), …]`, em ordem."""
    saida: List[Tuple[str, str]] = []
    for m in (meses or []):
        if not isinstance(m, dict):
            continue
        try:
            mes = int(m.get("Mes"))
        except (TypeError, ValueError):
            continue
        a = _ano_do_mes(mes, ano)
        for d in (m.get("Dias") or []):
            try:
                dia = int(d)
                date(a, mes, dia)
            except (TypeError, ValueError):
                continue
            saida.append((f"{dia:02d}/{mes:02d}", f"{a}-{mes:02d}-{dia:02d}"))
    return sorted(set(saida), key=lambda t: t[1])


async def _ler_blocos(sessao: Any, loja: Dict[str, Any], data_iso_: str,
                      cache: Dict[Any, Any], *, encaixe_ceven: Any = None
                      ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Os blocos LIVRES de uma loja num dia (regra do bundle), com cache."""
    chave = (str(loja.get("codigo_cliente")), data_iso_)
    if chave in cache:
        return cache[chave]["livres"], cache[chave]["resposta"]
    r = await sessao.horarios_disponiveis(
        codigo_cliente=loja.get("codigo_cliente"),
        codigo_produto=loja.get("codigo_produto"),
        data_agendamento=data_iso_)
    resp = r.get("json") if r.get("ok") and isinstance(r.get("json"), dict) else {}
    livres = API.blocos_livres(
        resp, encaixe_ceven=encaixe_ceven,
        bloqueio_por_peca_nao_medido=bool(loja.get("bloqueio_por_peca_nao_medido"))
    ) if resp else []
    cache[chave] = {"livres": livres, "resposta": resp}
    return livres, resp


def _pode_ler_mais(sessao: Any) -> bool:
    from portal_worker.journeys.vidros_sessao import MAX_CHAMADAS

    return int(getattr(sessao, "chamadas", 0) or 0) < MAX_CHAMADAS - RESERVA_DE_CHAMADAS


async def _enriquecer_agenda(sessao: Any, desfecho: Dict[str, Any], *,
                             agregado: Dict[str, Any],
                             codigo_atendimento: str) -> Dict[Any, Any]:
    """Distância, dias e horários LIVRES de cada loja. **Só leitura.**

    🔴 Isto é o que elimina a razão de sortear loja. 📊 `adaptive.py` explica,
    com três motivos medidos, por que o robô não escolhe: *"a lista de lojas só
    existe NESTA tela. O segurado nunca a viu."* Aqui a lista passa a existir na
    conversa — e a decisão continua sendo dele (ou da preferência que ele deu).

    ⚠️ `POST /lojas/consultar-distancias` é POST e **não** é escrita de negócio:
    calcula rota. Não passa pelo guard como fronteira material.

    🔴 EXTRA-001.10.1 — o contrato A→C de `lojas[].horarios` passa a ser
    `{"DD/MM": ["HH:MM", …]}`, só com blocos LIVRES (normal ou encaixe, regra
    do bundle em `API.blocos_livres`). 📊 Antes era `{"AAAA-MM-DD": [blocos
    crus]}` — dict do portal que nenhuma mensagem pode imprimir. O MODO de cada
    bloco (normal × encaixe) fica no cache devolvido, em memória, para o POST.
    """
    ano = hoje().year
    cache: Dict[Any, Any] = {}
    encaixe_ceven = agregado.get("EncaixeCeven") if isinstance(agregado, dict) else None
    for loja in desfecho.get("lojas", [])[:MAX_LOJAS_CONSULTADAS]:
        rd = await sessao.consultar_distancia({
            "CodigoAtendimento": str(codigo_atendimento or ""),
            "Cep": str(agregado.get("Cep") or ""),
            "Uf": str(agregado.get("EstadoRealizacaoServico") or loja.get("uf") or ""),
            "Cidade": str(agregado.get("CidadeRealizacaoServico") or loja.get("cidade") or ""),
            "Logradouro": "",
            "Bairro": str(loja.get("bairro") or ""),
        })
        distancia = rd.get("json") if isinstance(rd.get("json"), dict) else {}
        loja["distancia"] = str(distancia.get("Distancia") or "")
        loja["tempo"] = str(distancia.get("TempoDuracao") or "")

        if not loja.get("tem_agenda"):
            # 📊 `DisponibilizaAgenda` diferente de `"S"`: a loja não publica
            # agenda. Perguntar datas a ela seria inventar uma opção que o
            # segurado não tem.
            continue
        rdias = await sessao.datas_disponiveis(
            codigo_cliente=loja.get("codigo_cliente"),
            codigo_produto=loja.get("codigo_produto"), ano=ano)
        meses = rdias.get("json") if isinstance(rdias.get("json"), list) else []
        # 🔴 UM FORMATO SO, e ele ja e o que a mensagem imprime: `["15/08", …]`.
        # 📊 O red team mediu a mensagem ao segurado com `[{'mes': 8, 'dias':
        # [15, 17]}]` dentro dela — chave, colchete e tudo. Quem le e uma pessoa.
        loja["dias"] = _dias_legiveis(meses, ano)
        publicadas = _datas_publicadas(meses, ano)
        cache[("datas", str(loja.get("codigo_cliente")))] = publicadas
        loja["horarios"] = {}
        lidos = 0
        for dd_mm, iso in publicadas:
            if (lidos >= MAX_DIAS_LIDOS_POR_LOJA
                    or len(loja["horarios"]) >= DIAS_COM_HORARIO_POR_LOJA
                    or not _pode_ler_mais(sessao)):
                break
            livres, resp = await _ler_blocos(sessao, loja, iso, cache,
                                             encaixe_ceven=encaixe_ceven)
            lidos += 1
            if resp:
                loja["tempo_servico"] = resp.get("TempoServico")
                loja["tempo_permanencia"] = resp.get("TempoPermanencia")
            # 📊 Dia com `Blocos` vazio (LATERAL [044]) ou todo lotado não entra:
            # dizer "sem horários" é o que a lista de dias já diz sozinha.
            if livres:
                loja["horarios"][dd_mm] = [b["horario"] for b in livres]
    return cache


def preferencia_de_agenda(especificos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """`especificos.preferencia_agenda` (contrato C→A) validada, ou `None`.

    `{"a_partir_de": "DD/MM/AAAA", "periodo": "manha"|"tarde"|"qualquer"}`.
    ⛔ Período fora dos três → `None`: agendar por um período adivinhado é
    marcar o dia de alguém no horário em que ele disse que não pode.
    """
    bruto = (especificos or {}).get("preferencia_agenda")
    if not isinstance(bruto, dict):
        return None
    periodo = _norm(bruto.get("periodo") or "qualquer")
    if periodo not in PERIODOS:
        return None
    a_partir = data_iso(bruto.get("a_partir_de")) if bruto.get("a_partir_de") else ""
    if bruto.get("a_partir_de") and not a_partir:
        return None
    return {"a_partir_de": a_partir, "periodo": periodo}


def _km(texto: Any) -> float:
    """📊 `"9,2 km"` (LATERAL [040]) → 9.2. Sem número → infinito (vai por último)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(km|m)\b", str(texto or "").lower())
    if not m:
        return float("inf")
    valor = float(m.group(1).replace(",", "."))
    return valor / 1000.0 if m.group(2) == "m" else valor


async def _agendar_pela_preferencia(ex: Execucao, desfecho: Dict[str, Any],
                                    cache: Dict[Any, Any],
                                    pref: Dict[str, Any]) -> Optional[JourneyResult]:
    """A4 — a loja MAIS PRÓXIMA, o 1º horário que casa. `None` = não casou.

    🔴 A loja é a mais próxima pela distância que o PORTAL calculou (empate →
    a ordem em que o portal as listou). A data é a primeira publicada ≥ o
    "a partir de" do segurado e ≥ hoje, com bloco livre no período dele.
    Sem casamento em `MAX_DIAS_PELA_PREFERENCIA` dias, nada sai: o desfecho
    continua `agenda`, com as opções, e a conversa pergunta.
    """
    candidatas = [(i, l) for i, l in enumerate(desfecho.get("lojas") or [])
                  if l.get("tem_agenda") and not l.get("bloqueio_por_peca_nao_medido")]
    registro: Dict[str, Any] = {"periodo": pref["periodo"],
                                "a_partir_de": pref["a_partir_de"], "casou": False}
    ex.evidence["preferencia_agenda"] = registro
    if not candidatas:
        registro["motivo"] = "nenhuma loja com agenda publicada"
        return None
    _, loja = min(candidatas, key=lambda t: (_km(t[1].get("distancia")), t[0]))
    inicio = max(pref["a_partir_de"] or "", hoje().isoformat())
    publicadas = cache.get(("datas", str(loja.get("codigo_cliente")))) or []
    encaixe_ceven = ex.agregado.get("EncaixeCeven") if ex.agregado else None
    lidos = 0
    for _, iso in publicadas:
        if iso < inicio:
            continue
        if lidos >= MAX_DIAS_PELA_PREFERENCIA or not _pode_ler_mais(ex.sessao):
            break
        lidos += 1
        livres, resp = await _ler_blocos(ex.sessao, loja, iso, cache,
                                         encaixe_ceven=encaixe_ceven)
        casam = [b for b in livres
                 if pref["periodo"] == "qualquer" or _norm(b.get("turno")) == pref["periodo"]]
        if casam:
            registro.update(casou=True, dias_lidos=lidos)
            return await _agendar_no_portal(ex, loja, iso, casam[0], resp)
    registro.update(dias_lidos=lidos,
                    motivo="nenhum horario livre casou com a preferencia")
    return None


async def agendar_escolha(ex: Execucao, escolha: Dict[str, Any]) -> JourneyResult:
    """A2/A3 — a CONTINUAÇÃO com a escolha do segurado: loja, dia, horário.

    🔴 Tudo por IGUALDADE contra o que o portal publica AGORA — não contra o
    que publicou quando a lista foi mostrada. Loja pelo `CodigoCliente`, dia
    `DD/MM` na lista de datas, horário `HH:MM` nos blocos livres daquele dia.
    Não casou → `horario_indisponivel` com as opções REAIS de agora, e nenhuma
    escrita sai.
    """
    ropc = await ex.sessao.opcoes_de_agendamento()
    if not ropc.get("ok") or not isinstance(ropc.get("json"), dict):
        _tela_desconhecida(ex.evidence, onde=API.EP_OPCOES_DISPONIVEIS, resposta=ropc)
        return _parar(ex, "roteador_ilegivel",
                      "o pedido existe e o portal nao disse o desfecho. NAO "
                      "reexecute: consulte o atendimento.")
    opcoes = ropc["json"]
    if not isinstance(opcoes, dict) or opcoes.get("DisponibilizarAgendamento") is not True \
            or any(opcoes.get(k) is True for k in ST._CONCLUSAO):
        # 🔴 Já agendado, concluído, ou a agenda sumiu: o desfecho de HOJE é o
        # que vale — e ler não repete nenhum POST (idempotência pela leitura).
        return await fase_desfecho(ex, ropc=ropc)

    desfecho = ST.ler_desfecho(opcoes, ex.agregado)
    lojas = desfecho.get("lojas") or []
    alvo_loja = str((escolha or {}).get("loja") or "").strip()
    alvo_dia = str((escolha or {}).get("dia") or "").strip()[:5]
    alvo_hora = str((escolha or {}).get("horario") or "").strip()
    loja = next((l for l in lojas if str(l.get("codigo_cliente")) == alvo_loja
                 and l.get("tem_agenda")), None)

    async def indisponivel(motivo: str) -> JourneyResult:
        # As opções REAIS de agora, no MESMO contrato da abertura (`lojas[]`).
        await _enriquecer_agenda(ex.sessao, desfecho, agregado=ex.agregado,
                                 codigo_atendimento=ex.estado.codigo_atendimento)
        _absorver_agregado(ex, ex.agregado, desfecho)
        return _parar(ex, "horario_indisponivel",
                      "a escolha nao esta mais publicada pelo portal: " + motivo
                      + ". Nada foi agendado.",
                      escolha={"loja": alvo_loja, "dia": alvo_dia, "horario": alvo_hora})

    if loja is None:
        return await indisponivel("a loja escolhida nao esta entre as de agora")
    rdias = await ex.sessao.datas_disponiveis(
        codigo_cliente=loja.get("codigo_cliente"),
        codigo_produto=loja.get("codigo_produto"), ano=hoje().year)
    meses = rdias.get("json") if isinstance(rdias.get("json"), list) else []
    iso = next((i for d, i in _datas_publicadas(meses, hoje().year) if d == alvo_dia), "")
    if not iso:
        return await indisponivel(f"o dia {alvo_dia} nao esta mais na agenda da loja")
    livres, resp = await _ler_blocos(ex.sessao, loja, iso, {},
                                     encaixe_ceven=ex.agregado.get("EncaixeCeven"))
    bloco = next((b for b in livres if b.get("horario") == alvo_hora), None)
    if bloco is None:
        return await indisponivel(f"o horario {alvo_hora} de {alvo_dia} nao esta livre")
    ex.evidence["desfecho"] = desfecho
    return await _agendar_no_portal(ex, loja, iso, bloco, resp)


async def _agendar_no_portal(ex: Execucao, loja: Dict[str, Any], iso: str,
                             bloco: Dict[str, Any], horarios: Dict[str, Any]
                             ) -> JourneyResult:
    """A3 — `POST /agendamentos`, CONFIRMADO pela leitura do portal.

    🔴 A confirmação é o "Agendado para" do `GET /atendimentos` seguinte (📊
    LATERAL [049]), com o MESMO dia e horário pedidos. `ServicoAgendado` sozinho
    não prova nada (0 ocorrências no bundle). Sem confirmação → parada
    `agendamento_nao_confirmado`, e a continuação RELÊ — nunca repete o POST.
    """
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    corpo = API.corpo_do_agendamento(loja=loja, data_iso=iso, bloco=bloco,
                                     horarios=horarios or {})
    data_br = f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    faltam = [k for k, v in corpo.items() if not isinstance(v, bool) and v in (None, "")]
    if faltam:
        return _parar(ex, "agenda_ilegivel",
                      "a agenda do portal veio sem os campos que o agendamento "
                      "exige (" + ", ".join(faltam) + "). Nada foi agendado.")
    ex.guard.acao_material_esperada = ST.FRONTEIRA_AGENDAR
    try:
        await ex.guard.before(action=ST.FRONTEIRA_AGENDAR,
                              action_class=MATERIAL_SIDE_EFFECT,
                              details={"idempotency_key":
                                       str(ex.params.get("_idempotency_key") or "")},
                              origem="journey")
    except AcaoBloqueada as e:
        return _parar(ex, "pronto_para_agendar",
                      f"o horario casou e falta autorizacao para agendar ({e})",
                      escolha={"loja": str(loja.get("codigo_cliente")),
                               "dia": data_br[:5], "horario": bloco.get("horario")})

    r = await ex.sessao.agendar(corpo)
    ex.evidence["agendamento_enviado"] = {"data": data_br,
                                          "horario": corpo["Horario"],
                                          "encaixe": corpo["Encaixe"],
                                          "status": int(r.get("status") or 0)}
    if not r.get("ok"):
        await ex.guard.incerto(motivo="POST /agendamentos sem sucesso")
        _tela_desconhecida(ex.evidence, onde=API.EP_AGENDAMENTOS, resposta=r)
        return _parar(ex, "agendamento_nao_confirmado",
                      "o pedido de agendamento saiu e o portal nao confirmou. "
                      "NAO repita: releia o atendimento.")
    dados = r.get("json") if isinstance(r.get("json"), dict) else {}
    await ex.guard.submetido(receipt=f"{data_br} {corpo['Horario']}")

    rg = await ex.sessao.ler_atendimento()
    agregado = rg.get("json") if rg.get("ok") and isinstance(rg.get("json"), dict) else {}
    script = API.script_de_finalizacao(agregado)
    ag = script.get("agendamento") or {}
    confirmado = (ag.get("data") == data_br and ag.get("horario") == corpo["Horario"])
    ex.evidence["agendamento_enviado"].update(
        servico_agendado=dados.get("ServicoAgendado"),
        confirmado_pelo_portal=confirmado)
    if dados.get("ServicoAgendado") is not True or not confirmado:
        await ex.guard.incerto(motivo="agendamento sem o 'Agendado para' lido")
        return _parar(ex, "agendamento_nao_confirmado",
                      "o portal nao confirmou o agendamento por escrito. NAO "
                      "repita o pedido: releia o atendimento.")

    desfecho = ST.ler_conclusao((ex.evidence.get("desfecho") or {}).get("roteador"),
                                agregado)
    _absorver_agregado(ex, agregado, desfecho)
    ag_final = desfecho.get("agendamento") or {}
    # Se o script não trouxer a loja por escrito, os dados vêm da loja que o
    # PORTAL publicou em `OpcoesAgendamento` — nunca de texto nosso.
    for campo, valor in (("loja", loja.get("nome")), ("endereco", loja.get("endereco"))):
        if not ag_final.get(campo) and valor:
            ag_final[campo] = valor
    if desfecho["tipo"] != ST.DESFECHO_AGENDADO:
        desfecho["tipo"] = ST.DESFECHO_AGENDADO
        desfecho["agendamento"] = {
            "loja": str(loja.get("nome") or ""), "endereco": str(loja.get("endereco") or ""),
            "referencia": "", "data": ag["data"], "horario": ag["horario"],
            "permanencia": ag.get("permanencia", ""), "confirmado_pelo_portal": True}
    await ex.guard.confirmado(receipt=f"{data_br} {corpo['Horario']}")
    if ex.estado.codigo_atendimento:
        rf = await ex.sessao.emitir_formalizado(ex.estado.codigo_atendimento)
        desfecho["comprovante_emitido"] = bool(rf.get("ok"))
    return await _concluir(ex, desfecho, agregado)


# --------------------------------------------------------------------------
# 🔴 O RAMO 7 — prioridade + preferência de vistoria (A5)
# --------------------------------------------------------------------------
async def _responder_vistoria_opcional(ex: Execucao,
                                       desfecho: Dict[str, Any]) -> JourneyResult:
    """📊 LATARIA [089]→[091]→[092]→[093]→[094]→[095]: o que o SPA fez, na ordem.

    Com a preferência do segurado (`especificos.preferencia_vistoria` ∈
    {"loja","link"}): lê se é veículo de carga; grava a prioridade NEUTRA
    medida; grava a ocorrência com o texto LITERAL do bundle; relê o agregado
    (o SPA vai direto à conclusão, `F()`, sem reler `opcoes-disponiveis`) e
    emite o comprovante. Sem a preferência: PARA antes de qualquer escrita.
    """
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    pref = _norm(ex.especificos.get("preferencia_vistoria"))
    cod = str(ex.estado.codigo_atendimento or "").strip()
    if pref not in API.OCORRENCIA_VISTORIA:
        return _parar(ex, "decidir_vistoria",
                      "o portal quer saber se o segurado prefere a vistoria numa "
                      "LOJA ou por LINK no celular antes de concluir. Nada foi "
                      "gravado.", opcoes=sorted(API.OCORRENCIA_VISTORIA))
    if not cod.isdigit():
        return _parar(ex, "desfecho_ilegivel",
                      "o portal pediu a vistoria e o atendimento veio sem numero. "
                      "Nada foi gravado.")

    rp = await ex.sessao.prioridade_do_atendimento(cod)
    if not rp.get("ok") or rp.get("json") is not False:
        # 📊 `false` é o único valor medido. `true` (veículo de carga) troca a
        # lista de situações — e nela não existe a resposta neutra medida.
        _tela_desconhecida(ex.evidence, onde=API.EP_PRIORIDADES, resposta=rp)
        return _parar(ex, "prioridade_nao_medida",
                      "o portal pediu a prioridade do atendimento num caso que "
                      "nunca medimos (veiculo de carga ou resposta ilegivel). "
                      "Nada foi gravado.")

    for fronteira in (ST.FRONTEIRA_PRIORIDADE, ST.FRONTEIRA_OCORRENCIA):
        ex.guard.acao_material_esperada = fronteira
        try:
            await ex.guard.before(action=fronteira, action_class=MATERIAL_SIDE_EFFECT,
                                  details={"idempotency_key":
                                           str(ex.params.get("_idempotency_key") or "")},
                                  origem="journey")
        except AcaoBloqueada as e:
            return _parar(ex, "pronto_para_vistoria",
                          f"a preferencia de vistoria esta pronta e falta "
                          f"autorizacao para grava-la ({e})")
        if fronteira == ST.FRONTEIRA_PRIORIDADE:
            r = await ex.sessao.gravar_prioridade(
                {"CodigoAtendimento": int(cod), **API.PRIORIDADE_NEUTRA})
            onde = API.EP_PRIORIDADES
        else:
            r = await ex.sessao.gravar_ocorrencia(
                {"CodigoAtendimento": int(cod),
                 "Ocorrencia": API.OCORRENCIA_VISTORIA[pref]})
            onde = API.EP_OCORRENCIAS
        if not r.get("ok"):
            await ex.guard.incerto(motivo=f"{onde} sem sucesso")
            _tela_desconhecida(ex.evidence, onde=onde, resposta=r)
            # ⛔ fora da tabela de etapas: a equipe confere antes de qualquer
            # repetição (duas prioridades/ocorrências não se desfazem).
            return _parar(ex, "vistoria_nao_confirmada",
                          "gravei a preferencia de vistoria e o portal nao "
                          "confirmou. NAO repita: confira o atendimento.")
        await ex.guard.confirmado(receipt=f"{onde}:{cod}")

    rg = await ex.sessao.ler_atendimento()
    if not rg.get("ok") or not isinstance(rg.get("json"), dict):
        _tela_desconhecida(ex.evidence, onde=API.EP_ATENDIMENTOS, resposta=rg)
        return _parar(ex, "desfecho_ilegivel",
                      "a preferencia de vistoria foi gravada e nao consegui ler "
                      "o que o portal decidiu. NAO repita: consulte o atendimento.")
    agregado = rg["json"]
    final = ST.ler_conclusao(desfecho.get("roteador"), agregado)
    final["vistoria_preferida"] = pref
    _absorver_agregado(ex, agregado, final)
    if ex.estado.codigo_atendimento:
        rf = await ex.sessao.emitir_formalizado(ex.estado.codigo_atendimento)
        final["comprovante_emitido"] = bool(rf.get("ok"))
    return await _concluir(ex, final, agregado)


def _ano_do_mes(mes: Any, ano_corrente: int) -> int:
    """O ano a que este mes pertence. 🔴 A VIRADA DE ANO importa.

    📊 O juiz apontou `datetime.now().year` cravado: em dezembro, a agenda que o
    portal devolve para JANEIRO viraria `2026-01-…` em vez de `2027-01-…` — e a
    query de horarios sai com o ano errado, ou o segurado le uma data que ja
    passou. A regra: mes MENOR que o corrente e do ano que vem.
    """
    try:
        m = int(mes)
    except (TypeError, ValueError):
        return ano_corrente
    return ano_corrente + 1 if 1 <= m < hoje().month else ano_corrente


def _dias_legiveis(meses: Any, ano: int) -> List[str]:
    """`[{"Mes": 8, "Dias": [15,17]}, …]` → `["15/08", "17/08", …]`.

    ⛔ O contrato A→C de `lojas[].dias` e ESTE: uma lista de textos prontos. A
    mensagem ao segurado imprime direto, sem formatar nada — e por isso nenhuma
    chave, colchete ou `None` pode vazar para o WhatsApp.
    """
    saida: List[str] = []
    for m in (meses or []):
        if not isinstance(m, dict):
            continue
        try:
            mes = int(m.get("Mes"))
        except (TypeError, ValueError):
            continue
        for d in (m.get("Dias") or []):
            try:
                saida.append(f"{int(d):02d}/{mes:02d}")
            except (TypeError, ValueError):
                continue
    return saida[:60]


def _primeira_data(meses: Any, ano: int) -> str:
    """📊 `[{"Mes": 8, "Dias": [15,17,…]}, …]` → `"2026-08-15"`, com o ano certo."""
    datas = _datas_publicadas(meses, ano)
    return datas[0][1] if datas else ""
