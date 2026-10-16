"""SPEC-131-B · G2 — a API da aba Renovações (o lugar onde o comercial confere e envia).

    GET  /api/renovacoes?company_id=&user_id=&escopo=minhas|todas&estado=&ramo=&de=&ate=&seguradora=
         + cabeçalho `x-busca` (nome ou CPF/CNPJ — 🔴 NUNCA na query string: a query vai ao log de acesso)
    GET  /api/renovacoes/{id}?company_id=&user_id=                o detalhe + a linha do tempo + "Abrir no Agger"
    POST /api/renovacoes/{id}/apresentacao   {company_id, user_id}          → {token, url} · estado `apresentada`
    POST /api/renovacoes/{id}/envio          {company_id, user_id, via?}    → {texto, texto_curto, link, wa_me_url?,
                                                                               sem_telefone}
         `texto` = a mensagem COMPLETA (≤ 700, a do "Copiar a mensagem") · `texto_curto` = a que vai DENTRO do
         `wa_me_url` (a completa se couber em 500; senão a curta da G4). 🔴 O link enviado é SEMPRE o `proposta_ref`
         gravado (dois cliques ao mesmo tempo mandam o MESMO link).
    POST /api/renovacoes/{id}/respostas-de-vida {company_id, user_id, fumante?, renda_mensal?, esporte_radical?,
                                                 profissao_texto?}  → {estado, frase}
         SPEC-129-D · conserto K2 (red team B3): o que o CLIENTE respondeu (o comercial digita) a uma renovação de VIDA
         `pendente(falta_dado)` — um evento com `dados.respostas_de_vida` (o ÚNICO lugar com os valores) e `pronta`
         para a próxima madrugada (que LÊ a última resposta). ⛔ Os valores nunca vão a log nem à linha do tempo.

🔴 Chave interna (o proxy Next é quem fala com isto); `company_id` e `user_id` vêm da SESSÃO no proxy, nunca do
   navegador. TODA leitura passa pelo repositório da 131-A (`RepositorioDeRenovacoes`, filtro `company_id` + a segunda
   trava) e as leituras do multicálculo levam `solicitante_company_id` (CLAUDE.md §7 — o backend é service role).
🔴 O estado só muda pela MÁQUINA (`RepositorioDeRenovacoes.transicionar`) e só por estas três ações: publicar a
   apresentação (`calculada → apresentada`), abrir o envio (`apresentada → enviada`) e registrar as respostas de vida do
   cliente (`pendente → pronta`). Nenhuma rota recebe um estado
   ou uma coluna de destino — arrastar um card não existe (mutação 4 da SPEC; o corpo com chave desconhecida é 400).
⛔ NENHUMA mensagem sai daqui: o envio devolve um `wa.me` que o NAVEGADOR de quem clicou abre (o WhatsApp do aparelho
   dele). O telefone do cliente é lido NA HORA na InfoCap da corretora (`/documento` → `codcli` → `/cliente`, sem
   cache) e só existe dentro do `wa_me_url` da resposta: nunca vai a log, a evento, a linha do banco (mutação 5).
⛔ Nome do cliente só o curto; documento só mascarado (o que a 131-A já grava). Nenhum nome de corretora (§13.9).
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.portal import _require_internal_key
from app.services.multicalculo import renovacao as R

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/renovacoes", tags=["Renovações"])

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: o que o corpo de um POST pode trazer — qualquer outra chave (um `estado`, uma `coluna`) é recusada: a tela não move
#: card nenhum, ela só pede as duas ações que a máquina conhece
CHAVES_DO_POST = frozenset({"company_id", "user_id", "via"})
VIAS_DO_ENVIO = ("whatsapp", "copiar")
ESCOPOS = ("minhas", "todas")
#: SPEC-129-D · conserto K2 — o corpo das respostas de vida (nenhuma outra chave: nunca um estado, nunca uma coluna)
CHAVES_DAS_RESPOSTAS = frozenset({"company_id", "user_id", "fumante", "renda_mensal", "esporte_radical",
                                  "profissao_texto"})
#: 💭 um teto de sanidade para a renda digitada (um zero a mais não vira declaração ao Agger)
RENDA_MENSAL_MAXIMA = 10_000_000
TAMANHO_DA_PROFISSAO = (2, 120)
#: a pergunta NA TELA por campo que o cliente responde (a voz de quem conversa com o cliente — juiz B1)
PERGUNTA_NA_TELA: Dict[str, str] = {
    "vida.fumante": "O cliente fuma?",
    "vida.renda_mensal": "Qual a renda mensal do cliente?",
    "vida.esporte_radical": "Pratica esporte radical? Qual?",
    "segurado.profissao_texto": "Qual a profissão do cliente?",
}
FRASE_DO_ESPORTE_NA_TELA = ("O cliente pratica esporte radical e o Agger pede QUAL esporte: o aplicativo ainda não "
                            "escolhe o esporte — cote esta vida direto no Agger.")
#: os avisos do pedido de vida (códigos de `pedido.AVISO_*`) em português — o corretor confere antes de cotar
AVISO_NA_TELA: Dict[str, str] = {
    "coberturas_de_vida_nao_mapeadas": "Algumas coberturas da apólice não foram reconhecidas — confira antes de cotar.",
    "capital_de_morte_ambiguo": "A apólice tem dois capitais de morte diferentes — confira qual vale.",
    "coberturas_do_cadastro": "O capital veio do cadastro da InfoCap, não do PDF da apólice — confira.",
    "coberturas_nao_conferidas": "A leitura do PDF da apólice não fechou — confira as coberturas.",
    "documento_nao_e_a_apolice": "O PDF anexado não parece ser a apólice — confira.",
}
AVISO_GENERICO_NA_TELA = "Confira a apólice antes de cotar."
AVISO_DAS_RESPOSTAS = "Estas respostas são do cliente: confirme com ele."

#: B1 do BLOCO 0 (não medido nos aparelhos): o texto que vai DENTRO do link ≤ 500 caracteres; a mensagem inteira vai
#: no "Copiar a mensagem", que fica SEMPRE ao lado (RT-B2: `texto` = a inteira, `texto_curto` = a do link)
LIMITE_DO_TEXTO_NO_LINK = 500
#: J-B1: a busca (nome ou CPF/CNPJ) chega neste CABEÇALHO — a query string vai ao log de acesso do uvicorn e à URL
CABECALHO_DA_BUSCA = "x-busca"
TAMANHO_MAXIMO_DA_BUSCA = 80
#: a lista padrão: o que vence de 30 dias atrás em diante (a renovação vencida há mais tempo não é mais trabalho)
DIAS_PARA_TRAS_PADRAO = 30
#: os estados que a tela mostra — `substituida` é a linha velha de um endosso (a nova está na lista)
ESTADOS_VISIVEIS: Tuple[str, ...] = tuple(e for e in R.ESTADOS_LIGADOS + R.ESTADOS_RESERVADOS if e != "substituida")
#: o que se pode apresentar/enviar (a renovação já calculada)
ESTADOS_ENVIAVEIS: Tuple[str, ...] = ("calculada", "apresentada", "enviada")

# ---------------------------------------------------------------------------------------------------------------------
# O vocabulário da tela (a voz de quem trabalha, não a do banco)
# ---------------------------------------------------------------------------------------------------------------------
#: a COLUNA do quadro de cada estado (SPEC §4 · laudo de design §5). As quatro últimas a tela esconde até alguém chegar
#: lá; `substituida` não aparece. A coluna é DERIVADA do estado — nunca o contrário (sem arrastar).
COLUNA_DO_ESTADO: Dict[str, str] = {
    "listada": "vai_calcular", "pronta": "vai_calcular", "pendente": "vai_calcular", "calculando": "vai_calcular",
    "aguardando_agger": "vai_calcular", "falhou": "vai_calcular",
    "calculada": "calculada", "apresentada": "calculada",
    "enviada": "enviada", "vista": "enviada",
    "em_negociacao": "em_negociacao", "recalculo": "em_negociacao",
    "aceita": "fechada", "emissao_pendente": "fechada",
    "emitida": "emitida", "registrada": "emitida",
    "recusada": "perdida", "perdida": "perdida",
}
ROTULO_DO_ESTADO: Dict[str, str] = {
    "listada": "Na lista da madrugada", "pronta": "Vai calcular", "pendente": "Pendente",
    "calculando": "Calculando", "aguardando_agger": "Esperando o Agger", "falhou": "Não calculou",
    "calculada": "Calculada", "apresentada": "Apresentação pronta", "enviada": "Enviada", "vista": "Vista pelo cliente",
    "em_negociacao": "Em negociação", "recalculo": "Recalculando", "aceita": "Fechada", "emissao_pendente": "Emitindo",
    "emitida": "Emitida", "registrada": "Registrada", "recusada": "Recusada", "perdida": "Perdida",
    "substituida": "Substituída",
}
#: as opções da renovação na ordem da página (a "Sua renovação" em 1º — nunca "a melhor das N")
ORDEM_DAS_OPCOES: Tuple[str, ...] = ("anterior", "franquia_reduzida", "completa_mais", "padrao")
ROTULO_DA_OPCAO: Dict[str, str] = {"anterior": "Sua renovação", "franquia_reduzida": "Franquia menor",
                                   "completa_mais": "Mais completa", "padrao": "Cálculo padrão"}
ROTULO_DO_STATUS_DO_CALCULO: Dict[str, str] = {
    "na_fila": "na fila", "disparando": "começando", "calculando": "calculando", "fechado": "pronto",
    "falhou": "não calculou", "incerto": "confira no Agger", "cancelado": "cancelado", "expirado": "expirou",
}
#: os atalhos do topo da aba (cada um é um filtro; o número é a contagem do que ele mostra)
ATALHOS: Tuple[str, ...] = ("para_enviar_hoje", "precisa_de_voce", "vence_esta_semana", "enviadas")
#: o que ainda é TRABALHO (a renovação que não fechou nem se perdeu)
COLUNAS_EM_ABERTO: Tuple[str, ...] = ("vai_calcular", "calculada", "enviada", "em_negociacao")


def _db() -> Any:
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def _hoje() -> date:
    """O dia de HOJE no fuso do Brasil (a renovação vence num dia do calendário de quem trabalha)."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(R.FUSO_PADRAO)).date()


def _uuid(valor: Any, nome: str) -> str:
    texto = str(valor or "").strip().lower()
    if not _UUID.match(texto):
        raise HTTPException(status_code=400, detail=f"{nome} precisa ser um uuid")
    return texto


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).lower()


def _num(v: Any) -> Optional[float]:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


# ---------------------------------------------------------------------------------------------------------------------
# As peças puras (o teste as chama direto)
# ---------------------------------------------------------------------------------------------------------------------
def rotulo_do_ramo(sigla: Any) -> Optional[str]:
    """`AUTO` → "Auto", `RESI` → "Residencial"… pelo agrupamento que o produto já tem (`familia_de_ramo`); a sigla
    desconhecida volta como veio (nunca se inventa um ramo)."""
    s = str(sigla or "").strip()
    if not s:
        return None
    try:
        from app.providers.policy_data_provider import NOME_DA_FAMILIA, familia_de_ramo

        fam = familia_de_ramo(s)
        nome = NOME_DA_FAMILIA.get(fam or "")
        if nome:
            return nome[:1].upper() + nome[1:]
    except Exception:  # noqa: BLE001
        pass
    return s.upper()


def precisa_de_voce(item: Mapping[str, Any]) -> bool:
    """O SELO (não é coluna): pendente ou falhou (o motivo diz por quê), ou sem ninguém da corretora para cuidar."""
    estado = str(item.get("estado") or "")
    if estado in ("pendente", "falhou"):
        return True
    em_aberto = COLUNA_DO_ESTADO.get(estado) in COLUNAS_EM_ABERTO
    return em_aberto and not item.get("dono_user_id") and not item.get("responsavel_user_id")


def link_do_agger(ramo_agger: Any, negocio_ref: Any) -> Optional[str]:
    """BLOCO 0 B4: `…/cotacao/<ramo>/resultados/<negocio_ref>` (a rota que o app do Agger declara). ⚠️ Que ele abre com a
    pessoa já logada não foi provado por clique — a tela diz "se pedir login, entre e volte"."""
    ref = str(negocio_ref or "").strip()
    if not ref:
        return None
    try:
        from portal_worker.multicalculo.agger_sessao import URL_BASE_AGGER
        from portal_worker.multicalculo.contrato import NOME_DO_RAMO
    except Exception:  # noqa: BLE001
        return None
    try:
        nome = NOME_DO_RAMO.get(int(ramo_agger))
    except (TypeError, ValueError):
        nome = None
    if not nome:
        return None
    return f"{URL_BASE_AGGER.rstrip('/')}/cotacao/{nome}/resultados/{quote(ref, safe='')}"


def resumo_dos_calculos(calculos: Sequence[Mapping[str, Any]], ofertas: Sequence[Mapping[str, Any]],
                        *, ramo_agger: Any = None) -> List[Dict[str, Any]]:
    """Os cálculos da renovação resumidos POR OPÇÃO, na ordem da página: o menor preço, quantas seguradoras deram
    preço, o estado do cálculo em palavras e o link direto ao Agger. `ajuste` (recálculo da negociação) fica de fora."""
    por_opcao: Dict[str, List[Mapping[str, Any]]] = {}
    for c in calculos:
        opcao = str(c.get("opcao") or "")
        if opcao and opcao != "ajuste":
            por_opcao.setdefault(opcao, []).append(c)
    ordem = [o for o in ORDEM_DAS_OPCOES if o in por_opcao] + sorted(o for o in por_opcao if o not in ORDEM_DAS_OPCOES)
    saida: List[Dict[str, Any]] = []
    for opcao in ordem:
        calc = sorted(por_opcao[opcao], key=lambda c: str(c.get("criado_em") or ""))[-1]   # o mais recente vale
        cid = str(calc.get("id") or "")
        validas = [o for o in ofertas if str(o.get("calculo_id") or "") == cid and _num(o.get("premio_total"))]
        menor = min(validas, key=lambda o: float(o["premio_total"])) if validas else None
        status = str(calc.get("status") or "")
        saida.append({
            "opcao": opcao,
            "rotulo": ROTULO_DA_OPCAO.get(opcao, opcao.replace("_", " ").capitalize()),
            "status": status,
            "status_rotulo": ROTULO_DO_STATUS_DO_CALCULO.get(status, status.replace("_", " ")),
            "menor_preco": round(float(menor["premio_total"]), 2) if menor else None,
            "seguradora_do_menor": (str(menor.get("seguradora") or "").strip() or None) if menor else None,
            "franquia_do_menor": _num(menor.get("franquia_valor")) if menor else None,
            "seguradoras": len({str(o.get("seguradora") or "").strip().lower() for o in validas}),
            "agger_url": link_do_agger(ramo_agger, calc.get("negocio_ref")),
        })
    return saida


def item_da_tela(linha: Mapping[str, Any], *, calculos: Sequence[Mapping[str, Any]] = (),
                 ofertas: Sequence[Mapping[str, Any]] = (), nomes: Optional[Mapping[str, str]] = None,
                 hoje: Optional[date] = None, dados_do_motivo: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Uma linha de `renovacoes` na forma da tela. Só o que a 131-A já grava: nome CURTO, documento MASCARADO.
    `dados_do_motivo` (os do evento que deixou o item no estado de agora) refinam a frase de vida (conserto K2)."""
    hoje = hoje or _hoje()
    nomes = nomes or {}
    estado = str(linha.get("estado") or "")
    fim = R.data_de(linha.get("fimvig"))
    dias = (fim - hoje).days if fim else None
    resumo = resumo_dos_calculos(calculos, ofertas, ramo_agger=linha.get("ramo_agger"))
    principal = next((c for c in resumo if c["menor_preco"]), None)
    atual = _num(linha.get("premio_atual"))
    novo = principal["menor_preco"] if principal else None
    variacao = round((novo - atual) / atual * 100, 1) if (novo and atual) else None
    resp_id = str(linha.get("responsavel_user_id") or linha.get("dono_user_id") or "").lower() or None
    coluna = COLUNA_DO_ESTADO.get(estado)
    motivo = linha.get("motivo")
    item = {
        "id": str(linha.get("id")),
        "cliente": linha.get("cliente_nome_curto") or None,
        "documento": linha.get("documento_mascarado") or None,
        "ramo": linha.get("ramo_sigla") or None,
        "ramo_rotulo": rotulo_do_ramo(linha.get("ramo_sigla")),
        "vence_em": fim.isoformat() if fim else None,
        "dias_para_vencer": dias,
        "seguradora_atual": linha.get("seguradora_atual") or None,
        "seguradora_nova": principal["seguradora_do_menor"] if principal else None,
        "premio_atual": atual,
        "premio_novo": novo,
        "variacao_pct": variacao,
        "responsavel": ({"user_id": resp_id, "nome": nomes.get(resp_id) or "Alguém da equipe"} if resp_id else None),
        "dono_user_id": (str(linha.get("dono_user_id")).lower() if linha.get("dono_user_id") else None),
        "estado": estado,
        "estado_rotulo": ROTULO_DO_ESTADO.get(estado, estado.replace("_", " ")),
        "coluna": coluna,
        "precisa_de_voce": precisa_de_voce(linha),
        "motivo": motivo or None,
        "motivo_frase": R.frase_do_motivo(motivo, dados_do_motivo) if motivo else None,
        "calculos": resumo,
        "pode_enviar": estado in ESTADOS_ENVIAVEIS,
        "atualizado_em": linha.get("atualizado_em"),
        "versao": linha.get("versao"),
    }
    atalhos = []
    if estado in ("calculada", "apresentada"):
        atalhos.append("para_enviar_hoje")
    if item["precisa_de_voce"]:
        atalhos.append("precisa_de_voce")
    if dias is not None and 0 <= dias <= 7 and coluna in COLUNAS_EM_ABERTO:
        atalhos.append("vence_esta_semana")
    if coluna == "enviada":
        atalhos.append("enviadas")
    item["atalhos"] = atalhos
    return item


def e_vida(linha: Mapping[str, Any]) -> bool:
    """A renovação é de VIDA INDIVIDUAL (ramo 91)? Pelo ramo do pedido, ou pela sigla da lista pela MESMA régua da
    madrugada (`pedido._ramo_do_agger` — com a chave da vida desligada, ela não é vida para o produto)."""
    from types import SimpleNamespace

    from app.services.multicalculo import pedido as P

    try:
        if int(linha.get("ramo_agger") or 0) == P.RAMO_VIDA:
            return True
    except (TypeError, ValueError):
        pass
    sigla = str(linha.get("ramo_sigla") or "").strip()
    if not sigla:
        return False
    try:
        return P._ramo_do_agger(SimpleNamespace(ramo=sigla)) == P.RAMO_VIDA
    except Exception:  # noqa: BLE001 — ramo que o produto não cota não é vida aqui
        return False


def dados_do_estado(eventos: Sequence[Mapping[str, Any]], estado: Any) -> Dict[str, Any]:
    """Os `dados` do evento MAIS RECENTE que levou o item ao estado de agora (eventos em ordem crescente). {} se não há."""
    for ev in reversed(list(eventos)):
        if str(ev.get("para") or "") == str(estado or ""):
            d = ev.get("dados")
            return dict(d) if isinstance(d, Mapping) else {}
    return {}


def campos_a_responder(linha: Mapping[str, Any], dados: Mapping[str, Any]) -> List[str]:
    """Os NOMES das respostas que o cliente ainda deve (fumante, renda_mensal, esporte_radical, profissao_texto), na
    ordem do formulário — só numa renovação de VIDA `pendente(falta_dado)`. [] = não há o que responder."""
    if str(linha.get("estado")) != "pendente" or str(linha.get("motivo")) != "falta_dado" or not e_vida(linha):
        return []
    faltando = {str(f) for f in (dados.get("faltando") or ())}
    return [nome for campo, nome in R.CAMPOS_DA_RESPOSTA_DE_VIDA.items() if campo in faltando]


def contexto_de_vida(linha: Mapping[str, Any], eventos: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """🔴 Juiz B1: o que a madrugada perguntou CHEGA à tela — as perguntas em português, os avisos do pedido de vida e o
    formulário das respostas. Só numa renovação de VIDA; o auto e o RE não ganham chave nenhuma. ⛔ Nenhum valor de
    resposta sai daqui (só SE já foi respondido)."""
    if not e_vida(linha):
        return {}
    from app.services.multicalculo import madrugada as M
    from app.services.multicalculo import pedido as P

    estado = str(linha.get("estado") or "")
    dados = dados_do_estado(eventos, estado)
    perguntas: List[str] = []

    def juntar(texto: Any) -> None:
        t = str(texto or "").strip()
        if t and t not in perguntas:
            perguntas.append(t)

    if estado in ("pendente", "falhou"):
        ditas = [str(p) for p in (dados.get("perguntas") or ())]
        qual_esporte = M.PERGUNTA_DO_ESPORTE_RADICAL in ditas
        for f in (str(x) for x in (dados.get("faltando") or ())):
            if qual_esporte and f == "vida.esporte_radical":
                juntar(FRASE_DO_ESPORTE_NA_TELA)
            else:
                juntar(PERGUNTA_NA_TELA.get(f) or P.PERGUNTA_DE_VIDA.get(f))
        if any(str(c).startswith("vida_por_ramo.") for c in (dados.get("configurar") or ())):
            juntar(R.FRASE_DA_COMISSAO_DE_VIDA[:1].upper() + R.FRASE_DA_COMISSAO_DE_VIDA[1:] + ".")
        conhecidas = set(P.PERGUNTA_DE_VIDA.values()) | {M.PERGUNTA_DO_ESPORTE_RADICAL}
        for p in ditas:
            if p not in conhecidas and "comissão de vida" not in p:
                juntar(p)
    avisos: List[str] = []
    for codigo in (dados.get("avisos") or ()):
        texto = AVISO_NA_TELA.get(str(codigo), AVISO_GENERICO_NA_TELA)
        if texto not in avisos:
            avisos.append(texto)
    campos = campos_a_responder(linha, dados)
    return {"perguntas": perguntas, "avisos": avisos,
            "respostas_de_vida": ({"campos": campos, "aviso": AVISO_DAS_RESPOSTAS,
                                   "ja_respondido": bool(R.ultima_resposta_de_vida(eventos))} if campos else None)}


def proximo_passo(item: Mapping[str, Any], linha: Mapping[str, Any]) -> str:
    """O que fazer agora com esta renovação, numa frase (o cabeçalho do detalhe)."""
    estado = str(item.get("estado") or "")
    if estado in ("pendente", "falhou"):
        return f"Precisa de você: {item.get('motivo_frase') or 'confira no Agger'}."
    if estado in ("listada", "pronta"):
        quando = R.data_de(linha.get("calcular_em"))
        return (f"Vai calcular na madrugada de {quando.strftime('%d/%m')}." if quando
                else "Vai calcular numa das próximas madrugadas.")
    if estado in ("calculando", "aguardando_agger"):
        return "Calculando no Agger agora. Fica pronto antes das 7h."
    if estado == "calculada":
        return "Confira os cálculos e envie ao cliente pelo WhatsApp."
    if estado == "apresentada":
        return "A apresentação está pronta: envie ao cliente pelo WhatsApp."
    if estado in ("enviada", "vista"):
        return "Enviada. Agora é esperar a resposta do cliente."
    return str(item.get("estado_rotulo") or "")


def numero_de_whatsapp(cliente: Mapping[str, Any]) -> Optional[str]:
    """O número do PRÓPRIO cliente (`/cliente`) em dígitos E.164 do Brasil (`55` + DDD + número), o CELULAR primeiro.
    🔴 RT-B3: as MESMAS fontes do leitor canônico (`infocap_connector._client_phone`): `telefone` e `telefones[]` — NUNCA
    `contatos[]` (pode ser o contador, um parente: outra pessoa receberia o nome, o vencimento e o link do cliente).
    🔴 A regra do número é a ÚNICA do produto (`perfil_do_membro.e164_do_brasil`, = o CHECK do banco): um número de
    OUTRO país nunca vira brasileiro. Nada válido → None (a tela oferece só o "Copiar"). ⛔ Quem chama nunca loga."""
    from app.services.perfil_do_membro import e164_do_brasil

    candidatos: List[str] = []

    def juntar(v: Any) -> None:
        if isinstance(v, Mapping):
            numero = v.get("numero")
            if numero:
                candidatos.append(f"{v.get('ddd') or ''}{numero}")
        elif isinstance(v, (str, int)) and not isinstance(v, bool):
            candidatos.append(str(v))

    juntar(cliente.get("telefone"))
    lista = cliente.get("telefones")
    for v in (lista if isinstance(lista, list) else []):
        juntar(v)
    validos: List[str] = []
    for bruto in candidatos:
        e164 = e164_do_brasil(bruto)
        if e164 and e164[1:] not in validos:
            validos.append(e164[1:])
    celular = next((d for d in validos if len(d) == 13 and d[4] == "9"), None)
    return celular or (validos[0] if validos else None)


def url_do_wa_me(numero: str, texto: str) -> str:
    return f"https://wa.me/{numero}?text={quote(texto, safe='')}"


# ---------------------------------------------------------------------------------------------------------------------
# As leituras (sempre da corretora da sessão)
# ---------------------------------------------------------------------------------------------------------------------
def _em_lotes(ids: Sequence[str], n: int = 50) -> Iterable[List[str]]:
    for i in range(0, len(ids), n):
        yield list(ids[i:i + n])


def calculos_e_ofertas(db: Any, cid: str, pedido_ids: Iterable[str]) -> Tuple[Dict[str, List[Dict[str, Any]]],
                                                                                  Dict[str, List[Dict[str, Any]]]]:
    """Os cálculos e as ofertas dos pedidos da renovação, POR PEDIDO, filtrados pelo SOLICITANTE (a corretora da sessão)
    no banco e de novo aqui. Lidos em lotes e paginados (o PostgREST corta em 1000 linhas)."""
    from app.leitura_completa import ler_paginado
    from app.services.multicalculo.repositorio import CALCULOS, OFERTAS

    ids = sorted({str(p).lower() for p in pedido_ids if p})
    calcs: Dict[str, List[Dict[str, Any]]] = {}
    ofs: Dict[str, List[Dict[str, Any]]] = {}
    for lote in _em_lotes(ids):
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(CALCULOS).select("id, pedido_id, solicitante_company_id, opcao, status, "
                                                        "negocio_ref, versao, criado_em")
            .in_("pedido_id", lote).eq("solicitante_company_id", cid),
            chave_unica="id", rotulo="renovacoes.calculos")
        for c in linhas:
            if str(c.get("solicitante_company_id") or "").lower() == cid:
                calcs.setdefault(str(c.get("pedido_id")).lower(), []).append(c)
        linhas, _ = ler_paginado(
            lambda lote=lote: db.table(OFERTAS).select("id, calculo_id, pedido_id, solicitante_company_id, seguradora, "
                                                       "premio_total, franquia_valor")
            .in_("pedido_id", lote).eq("solicitante_company_id", cid),
            chave_unica="id", rotulo="renovacoes.ofertas")
        for o in linhas:
            if str(o.get("solicitante_company_id") or "").lower() == cid:
                ofs.setdefault(str(o.get("pedido_id")).lower(), []).append(o)
    return calcs, ofs


def _nomes_da_equipe(db: Any, cid: str) -> Dict[str, str]:
    try:
        from app.services.sistema_de_gestao import dono as DONO

        return {m["user_id"]: m["nome"] for m in DONO.membros_ativos(db, cid)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] equipe ilegível: %s", type(exc).__name__)
        return {}


def aplicativo_ligado(db: Any, cid: str) -> bool:
    """A corretora tem o aplicativo de Renovação LIGADO (a madrugada só roda assim — 131-A)?"""
    try:
        linhas = list(getattr(db.table("tenant_auxiliaries").select("company_id, slug, status")
                              .eq("company_id", cid).eq("slug", "renovacao").limit(1).execute(), "data", None) or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] estado do aplicativo ilegível: %s", type(exc).__name__)
        return False
    return any(str(x.get("company_id", "")).lower() == cid and x.get("status") == "active" for x in linhas)


def quem_eu_cubro_hoje(db: Any, cid: str, uid: str, hoje: date) -> frozenset:
    """J-P6: as pessoas desta corretora cuja ausência ATIVA hoje tem a mim como substituto (o leitor do perfil)."""
    try:
        from app.services.perfil_do_membro import quem_eu_cubro_hoje as ler

        return frozenset(ler(db, cid, uid, hoje=hoje))
    except Exception as exc:  # noqa: BLE001 — sem a tabela de ausências, "Minhas" é só o que é meu
        logger.info("[RENOVACOES] ausências ilegíveis para 'Minhas': %s", type(exc).__name__)
        return frozenset()


def busca_do_cabecalho(valor: Optional[str]) -> Optional[str]:
    """J-B1: o texto da busca vem no cabeçalho `x-busca` (nunca na query, que vai ao log de acesso). Aceita o texto
    percent-encoded (`encodeURIComponent`) ou cru; os bytes UTF-8 que o Starlette leu como latin-1 voltam a ser texto.
    ⛔ Nunca é logado. Vazio → None."""
    texto = str(valor or "")
    if not texto.strip():
        return None
    try:
        texto = texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    if "%" in texto:
        from urllib.parse import unquote

        texto = unquote(texto)
    texto = texto.strip()[:TAMANHO_MAXIMO_DA_BUSCA]
    return texto or None


def _casa_busca(linha: Mapping[str, Any], q: str) -> bool:
    texto = _sem_acento(q.strip())
    if not texto:
        return True
    digitos = re.sub(r"\D", "", q)
    if len(digitos) in (11, 14):   # o CPF/CNPJ inteiro: compara pelo HMAC (o banco nunca teve o documento em claro)
        try:
            return R.hmac_do_documento(digitos) == linha.get("documento_hmac")
        except Exception:  # noqa: BLE001 — sem a chave do HMAC, a busca por documento não casa nada (fail-closed)
            return False
    return texto in _sem_acento(str(linha.get("cliente_nome_curto") or ""))


def _filtrar(linhas: List[Dict[str, Any]], *, uid: str, escopo: str, estado: Optional[str], ramo: Optional[str],
             de: Optional[str], ate: Optional[str], seguradora: Optional[str], q: Optional[str],
             cobertos: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """`cobertos` (J-P6, D-131-08): as pessoas que EU cubro numa ausência ATIVA hoje — as renovações delas entram em
    "Minhas" (o aviso já vem para mim; a lista precisa mostrar o trabalho)."""
    saida = []
    meus = {uid, *(str(c).lower() for c in cobertos)}
    estados = {e.strip() for e in (estado or "").split(",") if e.strip()}
    ramo_alvo = _sem_acento(ramo or "")
    seg_alvo = _sem_acento(seguradora or "")
    for x in linhas:
        if escopo == "minhas" and not meus & {str(x.get("dono_user_id") or "").lower(),
                                              str(x.get("responsavel_user_id") or "").lower()}:
            continue
        if estados and str(x.get("estado")) not in estados and COLUNA_DO_ESTADO.get(str(x.get("estado"))) not in estados:
            continue
        if ramo_alvo and ramo_alvo not in (_sem_acento(str(x.get("ramo_sigla") or "")),
                                           _sem_acento(rotulo_do_ramo(x.get("ramo_sigla")) or "")):
            continue
        if seg_alvo and _sem_acento(str(x.get("seguradora_atual") or "")) != seg_alvo:
            continue
        fim = str(R.data_de(x.get("fimvig")) or "")
        if de and fim < de:
            continue
        if ate and fim > ate:
            continue
        if q and not _casa_busca(x, q):
            continue
        saida.append(x)
    return saida


def montar_lista(db: Any, cid: str, uid: str, *, escopo: str = "minhas", estado: Optional[str] = None,
                 ramo: Optional[str] = None, de: Optional[str] = None, ate: Optional[str] = None,
                 seguradora: Optional[str] = None, q: Optional[str] = None) -> Dict[str, Any]:
    hoje = _hoje()
    if not de and not ate:
        de = (hoje - timedelta(days=DIAS_PARA_TRAS_PADRAO)).isoformat()
    repo = R.RepositorioDeRenovacoes(db)
    todas = repo.listar(cid, estados=ESTADOS_VISIVEIS)
    cobertos = quem_eu_cubro_hoje(db, cid, uid, hoje) if escopo == "minhas" else frozenset()
    do_escopo = _filtrar(todas, uid=uid, escopo=escopo, estado=None, ramo=None, de=None, ate=None, seguradora=None,
                         q=None, cobertos=cobertos)
    linhas = _filtrar(do_escopo, uid=uid, escopo=escopo, estado=estado, ramo=ramo, de=de, ate=ate,
                      seguradora=seguradora, q=q, cobertos=cobertos)
    calcs, ofs = calculos_e_ofertas(db, cid, [x.get("pedido_id") for x in linhas])
    nomes = _nomes_da_equipe(db, cid)
    itens = []
    for x in linhas:
        pid = str(x.get("pedido_id") or "").lower()
        dados = None
        if x.get("estado") in ("pendente", "falhou") and x.get("motivo") in ("falta_dado", "porta_recusou") \
                and e_vida(x):
            # conserto K2: só a vida pendente lê os eventos (poucas) — a frase diz "faltam respostas do cliente"
            dados = dados_do_estado(repo.eventos(cid, str(x["id"])), x.get("estado"))
        itens.append(item_da_tela(x, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), nomes=nomes, hoje=hoje,
                                  dados_do_motivo=dados))
    itens.sort(key=lambda i: (i["vence_em"] or "9999", _sem_acento(i["cliente"] or "")))
    ramos: Dict[str, str] = {}
    for x in do_escopo:
        if x.get("ramo_sigla"):
            ramos.setdefault(str(x["ramo_sigla"]), rotulo_do_ramo(x["ramo_sigla"]) or str(x["ramo_sigla"]))
    return {
        "itens": itens,
        "total": len(itens),
        "contagens": {a: sum(1 for i in itens if a in i["atalhos"]) for a in ATALHOS},
        "escopo": escopo,
        "eu": uid,
        "hoje": hoje.isoformat(),
        "ligado": aplicativo_ligado(db, cid),
        "tem_alguma": bool(todas),
        "seguradoras": sorted({str(x["seguradora_atual"]) for x in do_escopo if x.get("seguradora_atual")},
                              key=_sem_acento),
        "ramos": [{"id": k, "rotulo": v} for k, v in sorted(ramos.items(), key=lambda kv: _sem_acento(kv[1]))],
    }


def _por_de_evento(por: Any, nomes: Mapping[str, str]) -> str:
    p = str(por or "").strip().lower()
    if p in nomes:
        return nomes[p]
    return "Alguém da equipe" if _UUID.match(p) else "O aplicativo"


def _frase_do_evento(ev: Mapping[str, Any], quem: str) -> str:
    para = str(ev.get("para") or "")
    motivo = ev.get("motivo")
    dados = ev.get("dados") if isinstance(ev.get("dados"), Mapping) else {}
    if dados.get("evento") == R.EVENTO_RESPOSTAS_DE_VIDA:
        # ⛔ só QUEM registrou — os valores (fumante, renda) nunca aparecem na linha do tempo (LGPD art. 11)
        return (f"{quem} registrou as respostas do cliente: vai calcular na próxima madrugada" if para == "pronta"
                else f"{quem} registrou as respostas do cliente")
    if para == "enviada" or motivo == "aberto_para_envio":
        via = (ev.get("dados") or {}).get("via") if isinstance(ev.get("dados"), Mapping) else None
        return (f"{quem} copiou a mensagem para enviar" if via == "copiar"
                else f"{quem} abriu o WhatsApp para enviar")
    if para == "apresentada":
        return f"{quem} preparou a apresentação"
    if para in ("pendente", "falhou"):
        return (f"{ROTULO_DO_ESTADO[para]}: {R.frase_do_motivo(motivo, dados)}" if motivo
                else ROTULO_DO_ESTADO[para])
    if para == "listada":
        return "Entrou na lista da madrugada"
    return ROTULO_DO_ESTADO.get(para, para.replace("_", " "))


def montar_detalhe(db: Any, cid: str, uid: str, rid: str) -> Dict[str, Any]:
    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)
    pid = str(linha.get("pedido_id") or "").lower()
    calcs, ofs = calculos_e_ofertas(db, cid, [pid] if pid else [])
    nomes = _nomes_da_equipe(db, cid)
    evs = repo.eventos(cid, rid)
    item = item_da_tela(linha, calculos=calcs.get(pid, []), ofertas=ofs.get(pid, []), nomes=nomes,
                        dados_do_motivo=dados_do_estado(evs, linha.get("estado")))
    eventos = []
    for ev in evs:
        quem = _por_de_evento(ev.get("por"), nomes)
        eventos.append({"quando": ev.get("criado_em"), "para": ev.get("para"), "frase": _frase_do_evento(ev, quem)})
    agger = next((c["agger_url"] for c in item["calculos"] if c.get("agger_url")), None)
    return {**item, "eventos": list(reversed(eventos)), "proximo_passo": proximo_passo(item, linha),
            "agger_url": agger, "eu": uid, **contexto_de_vida(linha, evs)}


# ---------------------------------------------------------------------------------------------------------------------
# As bordas: a apresentação e a mensagem (G4, pelo contrato) e a InfoCap da corretora
# ---------------------------------------------------------------------------------------------------------------------
async def _chamar(fn: Any, *args: Any, **kwargs: Any) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    r = await asyncio.to_thread(fn, *args, **kwargs)
    return await r if inspect.isawaitable(r) else r


def quem_clica(db: Any, cid: str, uid: str) -> Dict[str, Any]:
    """A `pessoa` do contrato da G4: {user_id, primeiro_nome} de QUEM clicou — o nome só se ela é membro DESTA
    corretora (`proposta.pessoa_de`, filtro company_id). Sem nome legível, só o id (a mensagem sai sem "Aqui é…")."""
    from app.services.multicalculo import proposta as P

    try:
        return dict(P.pessoa_de(db, cid, uid))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RENOVACOES] nome de quem clicou ilegível: %s", type(exc).__name__)
        return {"user_id": uid}


def _erro_da_publicacao(exc: Exception) -> Optional[HTTPException]:
    from app.services.multicalculo import proposta as P

    if isinstance(exc, P.PropostaImpossivel):
        return HTTPException(status_code=409, detail="Ainda não dá para montar a apresentação desta renovação: "
                                                     "falta um cálculo com preço. Confira no Agger.")
    if isinstance(exc, P.LinkSemEndereco):
        return HTTPException(status_code=503, detail="O endereço público do painel não está configurado: o link "
                                                     "da apresentação não teria para onde apontar.")
    return None


async def publicar(db: Any, cid: str, rid: str, pessoa: Mapping[str, Any]) -> Dict[str, Any]:
    """`proposta.publicar_renovacao(company_id, renovacao_id, *, pessoa, db) -> {token, url, artifact_id, versao,
    validade_ate, modelo}` (contrato da SPEC §5, G4) — ASYNC, com o MESMO banco da sessão. Ela NÃO muda o estado
    (quem faz `apresentada` é esta API)."""
    from app.services.multicalculo import proposta as P

    try:
        r = await _chamar(P.publicar_renovacao, cid, rid, pessoa=dict(pessoa), db=db)
    except Exception as exc:  # noqa: BLE001
        http = _erro_da_publicacao(exc)
        if http is None:
            raise
        raise http
    if not isinstance(r, Mapping) or not r.get("url"):
        raise HTTPException(status_code=502, detail="Não consegui preparar a apresentação agora. Tente de novo.")
    return dict(r)


#: um link que vence antes disto não é reaproveitado no envio (o cliente abriria um link morto)
FOLGA_DO_LINK_REAPROVEITADO = timedelta(days=2)


def ultima_apresentacao(db: Any, cid: str, linha: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """A apresentação JÁ publicada desta renovação (`proposta_ref` = o token do `/r/`), para o envio mandar o MESMO
    link que o comercial conferiu — sem versão nova a cada clique. Só vale se o link é DESTA corretora, não foi
    revogado, não vence nos próximos dias, a versão é uma página de RENOVAÇÃO (`modelo["renovacao"]`) e 🔴 RT-B1:
    QUEM ATENDE na página é quem atenderia AGORA (`proposta.quem_atende_mudou` — o dono ainda ATIVO, com o MESMO número
    confirmado; senão a corretora com o mesmo número). Qualquer dúvida → None (quem chama republica). Devolve {token,
    url, versao, artifact_id, modelo}."""
    token = str(linha.get("proposta_ref") or "").strip()
    if not token or linha.get("estado") not in ("apresentada", "enviada"):
        return None
    try:
        from app.services.multicalculo import proposta as P

        shares = list(getattr(db.table("artifact_shares")
                              .select("company_id, artifact_id, artifact_version_id, expires_at, revoked_at")
                              .eq("token", token).eq("company_id", cid).limit(1).execute(), "data", None) or [])
        s = next((x for x in shares if str(x.get("company_id") or "").lower() == cid), None)
        if s is None or s.get("revoked_at"):
            return None
        vence = datetime.fromisoformat(str(s.get("expires_at")).replace("Z", "+00:00"))
        if vence <= datetime.now(vence.tzinfo) + FOLGA_DO_LINK_REAPROVEITADO:
            return None
        versoes = list(getattr(db.table("artifact_versions").select("id, company_id, version, payload")
                               .eq("id", s["artifact_version_id"]).eq("company_id", cid).limit(1).execute(),
                               "data", None) or [])
        v = next((x for x in versoes if str(x.get("company_id") or "").lower() == cid), None)
        modelo = (v or {}).get("payload")
        if not isinstance(modelo, Mapping) or not isinstance(modelo.get("renovacao"), Mapping) \
                or not modelo.get("opcoes"):
            return None
        if P.quem_atende_mudou(db, cid, linha, modelo):
            # o dono saiu, apagou ou trocou o número (ou passou a ter um): a página velha mandaria o cliente ao
            # WhatsApp errado — republica com o "quem atende" de agora
            logger.info("[RENOVACOES] quem atende mudou desde a apresentação: republica")
            return None
        return {"token": token, "url": f"{P._base_do_link(None)}/r/{token}", "versao": int(v.get("version") or 1),
                "artifact_id": str(s.get("artifact_id")), "modelo": dict(modelo)}
    except Exception as exc:  # noqa: BLE001 — na dúvida, republica (nunca um link morto ao cliente)
        logger.info("[RENOVACOES] a apresentação anterior não serve: %s", type(exc).__name__)
        return None


def _config_da_renovacao(db: Any, cid: str) -> Optional[Mapping[str, Any]]:
    try:
        from app.services.multicalculo import config as CFG

        return CFG.carregar(cid, db=db, servico="renovacao")
    except Exception as exc:  # noqa: BLE001 — a mensagem usa o padrão do produto
        logger.info("[RENOVACOES] config ilegível para a mensagem: %s", type(exc).__name__)
        return None


async def mensagem(db: Any, cid: str, renovacao: Mapping[str, Any], proposta: Mapping[str, Any],
                   pessoa: Mapping[str, Any]) -> Dict[str, Any]:
    """`mensagem.mensagem_de_renovacao(renovacao, {url, modelo}, *, pessoa={primeiro_nome}) -> {texto, texto_curto,
    link}` (G4). ⛔ Nunca recebe o telefone: o `wa.me/<cliente>` é esta API que monta, na hora."""
    from app.services.multicalculo import mensagem as MSG

    kw: Dict[str, Any] = {"pessoa": {"primeiro_nome": pessoa.get("primeiro_nome")}}
    cfg = await asyncio.to_thread(_config_da_renovacao, db, cid)
    if cfg is not None:
        kw["config"] = cfg
    try:
        r = await _chamar(MSG.mensagem_de_renovacao, dict(renovacao),
                          {"url": proposta.get("url"), "modelo": proposta.get("modelo") or {}}, **kw)
    except ValueError as exc:
        logger.warning("[RENOVACOES] mensagem impossível: %s", type(exc).__name__)
        raise HTTPException(status_code=409, detail="Não consegui montar a mensagem: a apresentação não tem opção "
                                                    "com preço.")
    if not isinstance(r, Mapping) or not str(r.get("texto") or "").strip():
        raise HTTPException(status_code=502, detail="Não consegui montar a mensagem agora. Tente de novo.")
    return dict(r)


def textos_do_envio(msg: Mapping[str, Any]) -> Dict[str, Any]:
    """🔴 RT-B2 (contrato com a tela): dois campos, cada um com o seu papel —
    `texto`       = a mensagem COMPLETA (≤ 700 — as opções, as parcelas, "hoje você paga…", a assinatura): o "Copiar a
                    mensagem" e o caso "sem telefone" usam ESTA;
    `texto_curto` = a que vai DENTRO do `wa_me_url`: a completa quando cabe em 500 (B1 do BLOCO 0), senão a curta da G4.
    `link`        = o `/r/` da apresentação (está nas duas)."""
    completo = str(msg["texto"])
    curto = str(msg.get("texto_curto") or "").strip()
    no_link = completo if (len(completo) <= LIMITE_DO_TEXTO_NO_LINK or not curto) else curto
    return {"texto": completo, "texto_curto": no_link, "link": msg.get("link")}


async def abrir_fonte(db: Any, cid: str) -> Any:
    """A InfoCap DESTA corretora pelo caminho canônico (`dono.abrir_fonte`, nunca por nome — §13.9)."""
    from app.services.sistema_de_gestao import dono as DONO

    return await DONO.abrir_fonte(db, cid)


async def telefone_do_cliente(db: Any, cid: str, renovacao: Mapping[str, Any]) -> Optional[str]:
    """O WhatsApp do cliente, lido AGORA: `/documento` (o `codcli` da apólice) → `/cliente` (o cadastro, SEM cache —
    `cliente_cru` não guarda no Redis). Volta só para quem chamou; nunca é logado nem gravado. Falhou → None."""
    try:
        fonte = await abrir_fonte(db, cid)
        codfil, nosnum = R.codfil_de(renovacao.get("codfil")), R.nosnum_de(renovacao.get("nosnum"))
        doc = await asyncio.to_thread(fonte.documento_cru, codfil, nosnum)
        codcli = (doc or {}).get("codcli")
        if not codcli:
            return None
        cliente = await asyncio.to_thread(fonte.cliente_cru, codfil, codcli)
        return numero_de_whatsapp(cliente or {})
    except Exception as exc:  # noqa: BLE001 — ⛔ só o TIPO do erro: a mensagem de uma exceção pode carregar o dado
        logger.warning("[RENOVACOES] telefone do cliente ilegível agora: %s", type(exc).__name__)
        return None


# ---------------------------------------------------------------------------------------------------------------------
# As escritas — SÓ pela máquina da 131-A
# ---------------------------------------------------------------------------------------------------------------------
def _erro_da_maquina(exc: Exception) -> HTTPException:
    if isinstance(exc, R.NaoEncontrada):
        return HTTPException(status_code=404, detail="Esta renovação não existe nesta corretora.")
    if isinstance(exc, R.ConcorrenciaPerdida):
        return HTTPException(status_code=409, detail="Outra pessoa mexeu nesta renovação agora. Abra de novo.")
    return HTTPException(status_code=409, detail="Esta renovação mudou de estado. Abra de novo para ver como está.")


#: quantas vezes a referência é refeita quando outra pessoa mexeu na mesma renovação ao mesmo tempo
TENTATIVAS_DA_REFERENCIA = 3


def _trocar_referencia(db: Any, cid: str, linha: Mapping[str, Any], token: str) -> Dict[str, Any]:
    """RT-P2: a apresentação foi REPUBLICADA (o link velho vencia, ou quem atende mudou) numa renovação já
    `apresentada`/`enviada`: a referência passa a ser o link NOVO. Não é transição (o estado fica); CAS pela `versao`
    e pelo `estado`, como a máquina — perdeu a corrida → `ConcorrenciaPerdida`."""
    versao = int(linha.get("versao") or 1)
    patch = {"proposta_ref": token, "versao": versao + 1, "atualizado_em": R.RepositorioDeRenovacoes(db)._agora()}
    tabela = getattr(db, "client", db).table(R.TABELA)
    linhas = list(getattr(tabela.update(patch).eq("id", linha["id"]).eq("company_id", cid)
                          .eq("estado", linha.get("estado")).eq("versao", versao).execute(), "data", None) or [])
    nova = next((x for x in linhas if str(x.get("company_id", "")).lower() == cid), None)
    if nova is None:
        raise R.ConcorrenciaPerdida("a renovação mudou enquanto a referência da apresentação era trocada")
    return nova


def fixar_referencia(db: Any, cid: str, rid: str, uid: str,
                     proposta: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """🔴 RT-P1/P2: a referência GRAVADA (`proposta_ref`) é SEMPRE o link que sai — um link só por renovação.
    `calculada → apresentada` com o token (pela máquina, CAS). Já apresentada/enviada com OUTRO token: se o gravado
    ainda VALE (`ultima_apresentacao` — outro clique ao mesmo tempo gravou o dele), ele é ADOTADO e é o que vai; se não
    vale mais (vencendo, quem atende mudou), a referência passa a ser o novo (CAS). Perdeu a corrida → relê e decide
    de novo. Devolve (linha, proposta) — a proposta pode não ser a que entrou (a página órfã nunca é enviada)."""
    repo = R.RepositorioDeRenovacoes(db)
    atual = dict(proposta)
    for _ in range(TENTATIVAS_DA_REFERENCIA):
        linha = repo.por_id(cid, rid)
        token = str(atual.get("token") or "")
        estado = linha.get("estado")
        try:
            if estado == "calculada":
                return repo.transicionar(cid, rid, "apresentada", por=uid, campos={"proposta_ref": token}), atual
            if estado not in ("apresentada", "enviada"):
                raise R.TransicaoInvalida(f"{estado}: não se apresenta")
            if linha.get("proposta_ref") == token:
                return linha, atual
            gravada = ultima_apresentacao(db, cid, linha)
            if gravada is not None:
                return linha, gravada      # o link gravado vale: é ELE que vai
            return _trocar_referencia(db, cid, linha, token), atual
        except R.ConcorrenciaPerdida:
            continue
    raise R.ConcorrenciaPerdida("a renovação mudou de novo durante o envio")


def _apresentar(db: Any, cid: str, rid: str, uid: str, token: Optional[str]) -> Dict[str, Any]:
    """Compatível com a G5: a referência fixada para `token` (ver `fixar_referencia`)."""
    return fixar_referencia(db, cid, rid, uid, {"token": token})[0]


def _registrar_envio(db: Any, cid: str, rid: str, uid: str, *, via: str, proposta: Mapping[str, Any]) -> Dict[str, Any]:
    """O evento `aberto_para_envio` (quem, versão, por onde — ⛔ SEM telefone) e `apresentada → enviada`. Uma renovação
    já enviada que se abre de novo ganha só o evento (a máquina não tem `enviada → enviada`)."""
    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)
    dados = {"evento": "aberto_para_envio", "via": via, "por_user_id": uid, "versao": linha.get("versao"),
             "proposta_versao": proposta.get("versao")}
    if linha.get("estado") == "enviada":
        repo._evento(cid, rid, "enviada", "enviada", uid, "aberto_para_envio", dados)   # a escrita da própria máquina
        return linha
    try:
        return repo.transicionar(cid, rid, "enviada", por=uid, motivo="aberto_para_envio", dados=dados)
    except R.ConcorrenciaPerdida:
        # RT-P1: o outro clique levou a `enviada` no mesmo instante (com o MESMO link — `fixar_referencia`): o meu
        # envio vira só o evento; qualquer outra mudança sobe como 409
        linha = repo.por_id(cid, rid)
        if linha.get("estado") != "enviada":
            raise
        repo._evento(cid, rid, "enviada", "enviada", uid, "aberto_para_envio", dados)
        return linha


def respostas_do_corpo(corpo: Mapping[str, Any]) -> Dict[str, Any]:
    """As respostas de vida do corpo, conferidas UMA a UMA (tipo e faixa). Nenhuma resposta, ou uma fora do tipo → 400.
    ⛔ Nunca um valor padrão: o que não veio fica de fora (e o item continua pedindo). ⛔ A mensagem nunca leva valor."""
    saida: Dict[str, Any] = {}
    for campo in ("fumante", "esporte_radical"):
        if campo in corpo and corpo[campo] is not None:
            if not isinstance(corpo[campo], bool):
                raise HTTPException(status_code=400, detail=f"{campo}: responda sim ou não")
            saida[campo] = corpo[campo]
    if corpo.get("renda_mensal") is not None:
        renda = corpo["renda_mensal"]
        if isinstance(renda, bool) or not isinstance(renda, (int, float)) or renda != renda \
                or not 0 <= renda <= RENDA_MENSAL_MAXIMA:
            raise HTTPException(status_code=400, detail="renda_mensal: um valor em reais, de 0 até "
                                                        f"{RENDA_MENSAL_MAXIMA:,}".replace(",", "."))
        saida["renda_mensal"] = round(float(renda), 2)
    if corpo.get("profissao_texto") is not None:
        prof = corpo["profissao_texto"]
        texto = " ".join(prof.split()) if isinstance(prof, str) else ""
        if not TAMANHO_DA_PROFISSAO[0] <= len(texto) <= TAMANHO_DA_PROFISSAO[1]:
            raise HTTPException(status_code=400, detail="profissao_texto: escreva a profissão do cliente "
                                                        f"(de {TAMANHO_DA_PROFISSAO[0]} a {TAMANHO_DA_PROFISSAO[1]} letras)")
        saida["profissao_texto"] = texto
    if not saida:
        raise HTTPException(status_code=400, detail="nenhuma resposta do cliente veio no pedido")
    return saida


def registrar_respostas_de_vida(db: Any, cid: str, rid: str, uid: str, respostas: Mapping[str, Any]) -> Dict[str, Any]:
    """🔴 Red team B3: a resposta do CLIENTE a uma renovação de VIDA `pendente(falta_dado)`, pela MÁQUINA (CAS):
    `pendente → pronta` com o evento `respostas_de_vida` (os valores moram SÓ ali — a madrugada lê a última). O que já
    tinha sido respondido antes vale junto (a resposta nova só completa/corrige). Esporte radical "sim" → o item FICA
    pendente com a pergunta "qual esporte" (o Agger exige o esporte; o pedido não tem o campo — nunca um palpite).
    Outra corretora → `NaoEncontrada` (404). Não é vida / não espera resposta → 409. Falta resposta pedida → 422."""
    from app.services.multicalculo import madrugada as M

    repo = R.RepositorioDeRenovacoes(db)
    linha = repo.por_id(cid, rid)                       # 🔴 filtro company_id: o id de outra corretora "não existe"
    if not e_vida(linha):
        raise HTTPException(status_code=409, detail="Esta renovação não é de vida individual.")
    eventos = repo.eventos(cid, rid)
    campos = campos_a_responder(linha, dados_do_estado(eventos, linha.get("estado")))
    if not campos:
        raise HTTPException(status_code=409, detail="Esta renovação não está esperando respostas do cliente. "
                                                    "Abra de novo para ver como está.")
    juntas = {**R.ultima_resposta_de_vida(eventos), **dict(respostas)}
    faltam = [c for c in campos if juntas.get(c) is None]
    if faltam:
        nomes = {"fumante": "se fuma", "renda_mensal": "a renda mensal", "esporte_radical": "o esporte radical",
                 "profissao_texto": "a profissão"}
        raise HTTPException(status_code=422, detail="Falta responder: " + ", ".join(nomes[c] for c in faltam) + ".")
    dados = {"evento": R.EVENTO_RESPOSTAS_DE_VIDA, "por_user_id": uid, "respostas_de_vida": juntas}
    if juntas.get("esporte_radical") is True:
        return repo.transicionar(cid, rid, "pendente", por=uid, motivo="falta_dado",
                                 dados={**dados, **M.pendencia_do_esporte_radical()})
    return repo.transicionar(cid, rid, "pronta", por=uid, dados=dados)


async def _corpo(request: Request) -> Dict[str, Any]:
    try:
        corpo = await request.json()
    except Exception:  # noqa: BLE001
        corpo = {}
    if not isinstance(corpo, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    estranhas = set(corpo) - CHAVES_DO_POST
    if estranhas:
        # ⛔ mutação 4: nenhuma rota recebe um estado ou uma coluna de destino
        raise HTTPException(status_code=400, detail="campos que esta ação não recebe: " + ", ".join(sorted(estranhas)))
    return corpo


# ---------------------------------------------------------------------------------------------------------------------
# As rotas
# ---------------------------------------------------------------------------------------------------------------------
@router.get("")
async def listar_renovacoes(
    company_id: str,
    user_id: str,
    escopo: str = "minhas",
    estado: Optional[str] = None,
    ramo: Optional[str] = None,
    de: Optional[str] = None,
    ate: Optional[str] = None,
    seguradora: Optional[str] = None,
    x_busca: Optional[str] = Header(default=None, alias=CABECALHO_DA_BUSCA),
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """🔴 J-B1: a busca (nome ou CPF/CNPJ) é SÓ o cabeçalho `x-busca`. Um `?q=` na query não é lido (não filtra, não
    é logado por esta rota) — a query string inteira vai ao log de acesso do uvicorn, o documento não pode ir junto."""
    _require_internal_key(x_key)
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    if escopo not in ESCOPOS:
        raise HTTPException(status_code=400, detail="escopo é minhas ou todas")
    for nome, valor in (("de", de), ("ate", ate)):
        if valor and not _DATA.match(valor):
            raise HTTPException(status_code=400, detail=f"{nome} é uma data AAAA-MM-DD")
    try:
        return await asyncio.to_thread(montar_lista, _db(), cid, uid, escopo=escopo, estado=estado, ramo=ramo, de=de,
                                       ate=ate, seguradora=seguradora, q=busca_do_cabecalho(x_busca))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[RENOVACOES] lista falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui carregar as renovações agora.")


@router.get("/{renovacao_id}")
async def detalhe_da_renovacao(
    renovacao_id: str,
    company_id: str,
    user_id: str,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    cid, uid = _uuid(company_id, "company_id"), _uuid(user_id, "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    try:
        return await asyncio.to_thread(montar_detalhe, _db(), cid, uid, rid)
    except R.NaoEncontrada as exc:
        raise _erro_da_maquina(exc)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("[RENOVACOES] detalhe falhou: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Não consegui abrir esta renovação agora.")


@router.post("/{renovacao_id}/apresentacao")
async def apresentar_renovacao(
    renovacao_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = _uuid(corpo.get("company_id"), "company_id"), _uuid(corpo.get("user_id"), "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    db = _db()
    try:
        linha = await asyncio.to_thread(R.RepositorioDeRenovacoes(db).por_id, cid, rid)
        if linha.get("estado") not in ESTADOS_ENVIAVEIS:
            raise HTTPException(status_code=409, detail="Esta renovação ainda não foi calculada.")
        proposta = await asyncio.to_thread(ultima_apresentacao, db, cid, linha)
        if proposta is None:
            pessoa = await asyncio.to_thread(quem_clica, db, cid, uid)
            proposta = await publicar(db, cid, rid, pessoa)
        linha, proposta = await asyncio.to_thread(fixar_referencia, db, cid, rid, uid, proposta)
    except (R.NaoEncontrada, R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        raise _erro_da_maquina(exc)
    return {"token": proposta.get("token"), "url": proposta.get("url"), "versao": proposta.get("versao"),
            "estado": linha.get("estado")}


@router.post("/{renovacao_id}/envio")
async def enviar_renovacao(
    renovacao_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """Prepara o envio: a apresentação publicada, a mensagem pronta e — por WhatsApp — o `wa.me` do cliente. Quem
    ENVIA é a pessoa, no aparelho dela. `via=copiar` (o botão "Copiar a mensagem") não lê telefone nenhum."""
    _require_internal_key(x_key)
    corpo = await _corpo(request)
    cid, uid = _uuid(corpo.get("company_id"), "company_id"), _uuid(corpo.get("user_id"), "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    via = str(corpo.get("via") or "whatsapp")
    if via not in VIAS_DO_ENVIO:
        raise HTTPException(status_code=400, detail="via é whatsapp ou copiar")
    db = _db()
    try:
        linha = await asyncio.to_thread(R.RepositorioDeRenovacoes(db).por_id, cid, rid)
        if linha.get("estado") not in ESTADOS_ENVIAVEIS:
            raise HTTPException(status_code=409, detail="Esta renovação ainda não foi calculada.")
        pessoa = await asyncio.to_thread(quem_clica, db, cid, uid)
        # a ÚLTIMA apresentação publicada (o link que o comercial conferiu); sem ela, ou vencendo, publica agora
        proposta = await asyncio.to_thread(ultima_apresentacao, db, cid, linha)
        if proposta is None:
            proposta = await publicar(db, cid, rid, pessoa)
        # 🔴 RT-P1/P2: o link que sai é o GRAVADO (outro clique ao mesmo tempo → o link dele, um só)
        linha, proposta = await asyncio.to_thread(fixar_referencia, db, cid, rid, uid, proposta)
        msg = await mensagem(db, cid, linha, proposta, pessoa)
        resposta: Dict[str, Any] = textos_do_envio(msg)
        if via == "whatsapp":
            numero = await telefone_do_cliente(db, cid, linha)
            if not numero:
                # sem telefone: nada foi aberto — a pessoa copia a mensagem (e o "copiar" registra o envio)
                return {**resposta, "sem_telefone": True, "estado": linha.get("estado")}
            resposta["wa_me_url"] = url_do_wa_me(numero, resposta["texto_curto"])
        linha = await asyncio.to_thread(_registrar_envio, db, cid, rid, uid, via=via, proposta=proposta)
    except (R.NaoEncontrada, R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        raise _erro_da_maquina(exc)
    return {**resposta, "sem_telefone": False if via == "whatsapp" else None, "estado": linha.get("estado")}


@router.post("/{renovacao_id}/respostas-de-vida")
async def responder_vida(
    renovacao_id: str,
    request: Request,
    x_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """SPEC-129-D · conserto K2 (red team B3): as respostas do cliente (fumante, renda mensal, esporte radical e — quando
    o Agger não achou — a profissão) a uma renovação de VIDA pendente. `company_id`/`user_id` vêm da SESSÃO (o proxy).
    ⛔ Nenhum valor vai a log; nada é enviado a ninguém; nenhum cálculo começa aqui (a próxima madrugada calcula)."""
    _require_internal_key(x_key)
    try:
        corpo = await request.json()
    except Exception:  # noqa: BLE001
        corpo = {}
    if not isinstance(corpo, dict):
        raise HTTPException(status_code=400, detail="corpo inválido")
    estranhas = set(corpo) - CHAVES_DAS_RESPOSTAS
    if estranhas:
        raise HTTPException(status_code=400, detail="campos que esta ação não recebe: " + ", ".join(sorted(estranhas)))
    cid, uid = _uuid(corpo.get("company_id"), "company_id"), _uuid(corpo.get("user_id"), "user_id")
    rid = _uuid(renovacao_id, "renovacao_id")
    respostas = respostas_do_corpo(corpo)
    try:
        linha = await asyncio.to_thread(registrar_respostas_de_vida, _db(), cid, rid, uid, respostas)
    except (R.NaoEncontrada, R.ConcorrenciaPerdida, R.TransicaoInvalida) as exc:
        raise _erro_da_maquina(exc)
    estado = str(linha.get("estado") or "")
    frase = ("Respostas registradas. A vida entra no cálculo da próxima madrugada." if estado == "pronta"
             else FRASE_DO_ESPORTE_NA_TELA)
    return {"estado": estado, "frase": frase}
