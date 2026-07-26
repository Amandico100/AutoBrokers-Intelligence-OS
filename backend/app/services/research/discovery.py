"""Descoberta de empresas e análise de concorrentes. SPEC-060 §19 e §20.

A linha que este módulo não atravessa
-------------------------------------
§19.4 e §4.5 são categóricas: **não se raspa a interface do Google Maps**, não
se coleta e-mail pessoal de funcionário, não se enriquece com base vazada e
**não se envia mensagem nenhuma daqui**.

A pesquisa entrega uma LISTA. Contato é outra ação, com consentimento, policy,
aprovação e opt-out (§19.5) — e vive em outra Skill. Misturar as duas é o que
transforma uma ferramenta de prospecção em uma máquina de spam, e é por isso
que a fronteira está no código e não numa recomendação de uso.

Score de fit explicável
-----------------------
§19.6 lista o que pode entrar (segmento, região, site, sinais de operação) e o
que **nunca** entra: renda presumida de pessoa, raça, saúde, religião ou
qualquer proxy disso. O score aqui é uma soma de critérios declarados, e cada
ponto vem com o motivo — um número sem motivo é discriminação sem auditoria.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# §19.6 — critérios permitidos, com peso declarado.
CRITERIOS = {
    "tem_site": (20, "tem site próprio — sinal de operação estabelecida"),
    "tem_telefone": (15, "tem telefone comercial publicado"),
    "operando": (20, "o negócio consta como em operação"),
    "segmento_alvo": (25, "o segmento combina com o perfil procurado"),
    "endereco_na_regiao": (20, "fica na região pedida"),
}

# Segmentos com necessidade clara de seguro empresarial. A lista é de
# CATEGORIA de negócio, nunca de pessoa.
SEGMENTOS_COM_AFINIDADE = {
    "transporte": ("logistic", "transport", "moving", "trucking", "courier",
                   "freight", "storage"),
    "construcao": ("construction", "contractor", "roofing", "electrician",
                   "plumber", "building"),
    "saude": ("clinic", "dentist", "medical", "hospital", "veterinary",
              "physiotherap", "laborator"),
    "alimentacao": ("restaurant", "bakery", "cafe", "food", "catering", "bar"),
    "comercio": ("store", "shop", "supermarket", "wholesaler", "retail"),
    "industria": ("factory", "manufactur", "industrial", "plant"),
    "servicos": ("agency", "consult", "accounting", "law", "school",
                 "gym", "salon", "repair"),
    "hotelaria": ("hotel", "hostel", "lodging", "motel", "resort"),
}


@dataclass
class Empresa:
    """Uma empresa encontrada. Só campos comerciais — §19.3."""

    nome: str
    place_id: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    site: Optional[str] = None
    categorias: list[str] = field(default_factory=list)
    categoria_principal: Optional[str] = None
    status: Optional[str] = None
    segmento: Optional[str] = None
    fit_score: int = 0
    motivos_do_fit: list[str] = field(default_factory=list)
    fonte: str = "google_places"
    attribution: str = ""

    def chave_de_dedupe(self) -> str:
        """§38.7 — dedupe por place ID, domínio e telefone, nessa ordem."""
        from .urls import dominio

        if self.place_id:
            return f"place:{self.place_id}"
        if self.site:
            host = dominio(self.site)
            if host:
                return f"site:{host}"
        if self.telefone:
            digitos = "".join(c for c in self.telefone if c.isdigit())
            if len(digitos) >= 10:
                return f"tel:{digitos[-10:]}"
        return f"nome:{' '.join(self.nome.lower().split())}"

    def como_linha(self) -> dict:
        return {
            "empresa": self.nome, "categoria": self.categoria_principal or "",
            "segmento": self.segmento or "", "endereco": self.endereco or "",
            "telefone": self.telefone or "", "site": self.site or "",
            "situacao": self.status or "", "fit": self.fit_score,
            "por_que": "; ".join(self.motivos_do_fit),
            "fonte": self.fonte, "attribution": self.attribution,
        }


def classificar_segmento(categorias: list[str],
                         principal: Optional[str] = None) -> Optional[str]:
    """Segmento a partir das categorias do provider. Puro."""
    alvo = " ".join([*(categorias or []), principal or ""]).lower()
    if not alvo.strip():
        return None
    for segmento, pistas in SEGMENTOS_COM_AFINIDADE.items():
        if any(p in alvo for p in pistas):
            return segmento
    return None


def calcular_fit(empresa: Empresa, *, segmento_alvo: Optional[str] = None,
                 regiao: Optional[str] = None) -> tuple[int, list[str]]:
    """Score 0–100 com o motivo de cada ponto. Puro — §19.6.

    Devolver os motivos junto não é cortesia: é o que permite ao corretor
    discordar do score, e ao Admin auditar que nenhum critério proibido entrou.
    """
    pontos = 0
    motivos: list[str] = []

    if empresa.site:
        p, m = CRITERIOS["tem_site"]
        pontos += p
        motivos.append(m)
    if empresa.telefone:
        p, m = CRITERIOS["tem_telefone"]
        pontos += p
        motivos.append(m)
    if (empresa.status or "").upper() in ("OPERATIONAL", "ATIVO", ""):
        if empresa.status:
            p, m = CRITERIOS["operando"]
            pontos += p
            motivos.append(m)
    if segmento_alvo and empresa.segmento == segmento_alvo:
        p, m = CRITERIOS["segmento_alvo"]
        pontos += p
        motivos.append(m)
    elif empresa.segmento:
        pontos += 10
        motivos.append(f"segmento identificado: {empresa.segmento}")
    if regiao and empresa.endereco and regiao.lower() in empresa.endereco.lower():
        p, m = CRITERIOS["endereco_na_regiao"]
        pontos += p
        motivos.append(m)

    return min(100, pontos), motivos


def deduplicar(empresas: list[Empresa]) -> list[Empresa]:
    """Uma empresa, uma linha — §38.7. Preserva a de maior fit."""
    melhor: dict[str, Empresa] = {}
    ordem: list[str] = []
    for e in empresas:
        chave = e.chave_de_dedupe()
        atual = melhor.get(chave)
        if atual is None:
            melhor[chave] = e
            ordem.append(chave)
        elif e.fit_score > atual.fit_score:
            melhor[chave] = e
    return [melhor[c] for c in ordem]


class BusinessDiscovery:
    def __init__(self, supabase_client: Any, *, company_id: str,
                 work_run_id: Optional[str] = None):
        self.raw = supabase_client
        self.company_id = company_id
        self.work_run_id = work_run_id

    async def descobrir(self, *, segmento: str, regiao: str,
                        limite: int = 50,
                        enriquecer: bool = True) -> dict:
        """Busca empresas pela API licenciada e enriquece com o site público."""
        from .provider_router import ProviderRouter
        from .providers import MOTIVO_HUMANO, SEM_CHAVE

        router = ProviderRouter(self.raw, company_id=self.company_id,
                                work_run_id=self.work_run_id)
        places = router.providers.get("google_places")
        limitacoes: list[str] = []

        if places is None or not places.disponivel():
            # §19.4 proíbe o contorno. Sem a API licenciada, a resposta é que
            # não dá — nunca raspar o Maps.
            return {
                "ok": False, "empresas": [],
                "erro": "provider_de_lugares_indisponivel",
                "limitacoes": [
                    "A descoberta de empresas depende de uma API licenciada de "
                    "lugares, que não está configurada nesta instalação. Não "
                    "existe caminho alternativo: raspar a interface de mapas é "
                    "proibido pelos termos e pela nossa política."],
                "mensagem_humana": (
                    "Ainda não consigo montar lista de empresas — falta ativar "
                    "o serviço licenciado de busca de lugares."),
            }

        encontradas: list[Empresa] = []
        alvo = classificar_segmento([segmento], segmento)

        # A API devolve no máximo 20 por chamada; consultas variadas cobrem
        # mais sem repetir a mesma paginação.
        consultas = [f"{segmento} em {regiao}",
                     f"empresas de {segmento} {regiao}",
                     f"{segmento} {regiao} comercial"]
        for consulta in consultas:
            if len(encontradas) >= limite:
                break
            r = await places.buscar_empresas(consulta, limite=20)
            if not r.ok:
                if r.sem_credito:
                    limitacoes.append(
                        "A cota da busca de lugares foi atingida — a lista "
                        "está incompleta.")
                    break
                continue
            for f in r.fontes:
                m = f.metadata or {}
                e = Empresa(
                    nome=f.titulo or "(sem nome)",
                    place_id=m.get("place_id"), endereco=m.get("endereco"),
                    telefone=m.get("telefone"), site=m.get("site") or None,
                    categorias=list(m.get("categorias") or []),
                    categoria_principal=m.get("categoria_principal"),
                    status=m.get("status"),
                    attribution=m.get("attribution") or "")
                e.segmento = classificar_segmento(e.categorias,
                                                  e.categoria_principal)
                e.fit_score, e.motivos_do_fit = calcular_fit(
                    e, segmento_alvo=alvo, regiao=regiao)
                encontradas.append(e)

        unicas = deduplicar(encontradas)[:limite]

        if enriquecer:
            enriquecidas, limites_extra = await self._enriquecer(router, unicas)
            unicas = enriquecidas
            limitacoes.extend(limites_extra)

        unicas.sort(key=lambda e: -e.fit_score)
        return {
            "ok": True,
            "empresas": [e.como_linha() for e in unicas],
            "total": len(unicas),
            "segmento": segmento, "regiao": regiao,
            "limitacoes": limitacoes,
            "aviso": ("Esta é uma lista para prospecção EMPRESARIAL. Nenhuma "
                      "mensagem foi enviada — o contato é uma ação separada, "
                      "com registro e opção de descadastro."),
            "attribution": "Dados de lugares fornecidos pelo Google",
        }

    async def _enriquecer(self, router: Any,
                          empresas: list[Empresa]) -> tuple[list[Empresa], list[str]]:
        """Lê o site público para confirmar operação. §19.2.

        Só o site declarado pela própria empresa no cadastro do provider, e só
        para confirmar que existe e do que trata. Nada de varrer o site atrás
        de nome de funcionário.
        """
        limitacoes: list[str] = []
        sem_credito = False
        lidos = 0
        for e in empresas:
            if not e.site or lidos >= 15 or sem_credito:
                continue
            a = await router.ler(e.site, exigir_conteudo=False)
            lidos += 1
            if a.ok and a.saneado and len(a.saneado.texto) > 200:
                e.fit_score = min(100, e.fit_score + 5)
                e.motivos_do_fit.append("site ativo e com conteúdo")
            elif a.limitacao and ("crédito" in a.limitacao or "credito" in a.limitacao):
                sem_credito = True
                limitacoes.append(
                    "A confirmação dos sites ficou incompleta: o provedor de "
                    "leitura está sem crédito. A lista continua válida — o que "
                    "falta é a checagem extra de cada site.")
        return empresas, limitacoes


# ---------------------------------------------------------------------------
# Concorrentes — §20
# ---------------------------------------------------------------------------

# §20.2 — critérios iguais para todos, declarados antes de olhar qualquer um.
CRITERIOS_DE_COMPARACAO = (
    ("site_ativo", "Tem site no ar"),
    ("produtos_declarados", "Diz quais produtos oferece"),
    ("contato_visivel", "Telefone ou endereço visível"),
    ("conteudo_proprio", "Publica conteúdo próprio"),
    ("presenca_local", "Menciona a região onde atua"),
    ("dados_estruturados", "Site preparado para busca e assistentes"),
)


@dataclass
class Concorrente:
    nome: str
    site: Optional[str] = None
    criterios: dict = field(default_factory=dict)
    observacoes: list[str] = field(default_factory=list)
    fontes: list[str] = field(default_factory=list)

    @property
    def pontuacao(self) -> int:
        return sum(1 for v in self.criterios.values() if v)

    def como_linha(self) -> dict:
        return {"concorrente": self.nome, "site": self.site or "",
                **{chave: ("sim" if self.criterios.get(chave) else "não")
                   for chave, _ in CRITERIOS_DE_COMPARACAO},
                "pontos": self.pontuacao,
                "fontes": len(self.fontes)}


def montar_matriz(concorrentes: list[Concorrente]) -> dict:
    """Matriz comparativa com rubrica — §20.2 e §20.3.

    Sem rubrica não há nota: §20.2 proíbe "nenhuma nota sem rubrica". Aqui a
    rubrica são os seis critérios verificáveis, e a pontuação é a contagem —
    não uma opinião sobre quem é melhor.
    """
    return {
        "criterios": [{"chave": c, "rotulo": r} for c, r in CRITERIOS_DE_COMPARACAO],
        "linhas": [c.como_linha() for c in
                   sorted(concorrentes, key=lambda x: -x.pontuacao)],
        "metodologia": (
            "Todos os concorrentes foram avaliados pelos mesmos seis critérios "
            "verificáveis no site público, na mesma data. A pontuação é a "
            "contagem de critérios atendidos — não é uma nota de qualidade, e "
            "não diz nada sobre carteira, faturamento ou atendimento."),
        "limitacoes": [
            "A comparação usa apenas o que está publicado no site de cada um. "
            "Declaração própria não foi tratada como evidência independente."],
    }
