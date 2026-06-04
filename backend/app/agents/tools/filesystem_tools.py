"""
Filesystem Tools — LangChain BaseTool classes for File System Search
====================================================================

4 tools que permitem ao sub-agente navegar um documento markdown completo:
- FilesystemOutlineTool: estrutura de seções
- FilesystemReadTool: leitura de seções/linhas
- FilesystemSearchTool: busca textual (regex in-memory)
- FilesystemMetadataTool: metadados do documento

Todas seguem o mesmo pattern de KnowledgeBaseTool:
- company_id fixo no construtor
- agent_id injetado em runtime pelo tool_node
- Delegam para FilesystemSearchService

PRD: PRD-FileSystemSearch-AgentSmithV6.md
"""

import json
import logging
from typing import Any, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ...services.filesystem_search_service import (
    FilesystemSearchService,
    get_filesystem_search_service,
)

logger = logging.getLogger(__name__)


# ===== INPUT SCHEMAS =====


class FilesystemOutlineInput(BaseModel):
    """Nenhum input necessário — agent_id injetado pelo tool_node."""

    pass


class FilesystemReadInput(BaseModel):
    section: Optional[str] = Field(
        None, description="ID da seção do outline (ex: '3.2')"
    )
    start_line: Optional[int] = Field(
        None, description="Linha de início para leitura direta"
    )
    end_line: Optional[int] = Field(
        None, description="Linha de fim para leitura direta"
    )
    # Se nenhum parâmetro: retorna documento inteiro (se < 30K tokens)


class FilesystemSearchInput(BaseModel):
    query: str = Field(
        ..., description="Texto ou palavras-chave para buscar no documento"
    )
    max_results: int = Field(10, description="Máximo de resultados", ge=1, le=50)


class FilesystemMetadataInput(BaseModel):
    """Nenhum input necessário — agent_id injetado pelo tool_node."""

    pass


# ===== TOOLS =====


class FilesystemOutlineTool(BaseTool):
    """
    Retorna a estrutura de seções/headers do documento vinculado a este agente.
    Use como primeira ação para entender a organização do documento antes de buscar.
    """

    name: str = "filesystem_get_outline"
    description: str = (
        "Retorna a estrutura de seções/headers do documento vinculado a este agente. "
        "Use como primeira ação para entender a organização do documento antes de buscar. "
        "Não requer parâmetros."
    )
    args_schema: Type[BaseModel] = FilesystemOutlineInput

    # Configuração injetada
    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = company_id

    def _run(self, agent_id: Optional[str] = None, **kwargs) -> str:
        """agent_id injetado pelo tool_node, mesmo pattern de knowledge_base_search."""
        try:
            logger.info(
                f"[FS Outline] Buscando outline | company={self.company_id} | agent={agent_id}"
            )
            service = get_filesystem_search_service()
            result = service.get_outline(
                company_id=self.company_id, agent_id=agent_id
            )
            logger.info(
                f"[FS Outline] ✅ {result['total_sections']} seções, {result['total_tokens']} tokens"
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[FS Outline] ❌ Erro: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    async def _arun(self, agent_id: Optional[str] = None, **kwargs) -> str:
        return self._run(agent_id=agent_id, **kwargs)


class FilesystemReadTool(BaseTool):
    """
    Lê uma seção específica ou range de linhas do documento.
    Use o ID da seção retornado por filesystem_get_outline, ou especifique start_line/end_line.
    Sem parâmetros retorna o documento inteiro se ele couber em 30K tokens.
    """

    name: str = "filesystem_read_section"
    description: str = (
        "Lê uma seção específica ou range de linhas do documento. "
        "Use o ID da seção retornado por filesystem_get_outline, ou especifique start_line/end_line. "
        "Sem parâmetros retorna o documento inteiro se ele couber em 30K tokens."
    )
    args_schema: Type[BaseModel] = FilesystemReadInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = company_id

    def _run(
        self,
        section: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        try:
            logger.info(
                f"[FS Read] section={section} lines={start_line}-{end_line} | "
                f"company={self.company_id} | agent={agent_id}"
            )
            service = get_filesystem_search_service()
            result = service.read_section(
                company_id=self.company_id,
                agent_id=agent_id,
                section=section,
                start_line=start_line,
                end_line=end_line,
            )
            logger.info(
                f"[FS Read] ✅ {result['token_count']} tokens | "
                f"truncated={result['truncated']}"
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[FS Read] ❌ Erro: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    async def _arun(
        self,
        section: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        return self._run(
            section=section,
            start_line=start_line,
            end_line=end_line,
            agent_id=agent_id,
            **kwargs,
        )


class FilesystemSearchTool(BaseTool):
    """
    Busca textual no documento completo. Funciona como Ctrl+F inteligente.
    Retorna trechos com contexto ao redor de cada match e indica a seção/linha.
    """

    name: str = "filesystem_search"
    description: str = (
        "Busca textual no documento completo. Funciona como Ctrl+F inteligente. "
        "Retorna trechos com contexto ao redor de cada match e indica a seção/linha. "
        "Use para localizar informações antes de ler seções completas."
    )
    args_schema: Type[BaseModel] = FilesystemSearchInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = company_id

    def _run(
        self,
        query: str,
        max_results: int = 10,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        try:
            logger.info(
                f"[FS Search] query='{query}' max={max_results} | "
                f"company={self.company_id} | agent={agent_id}"
            )
            service = get_filesystem_search_service()
            result = service.search(
                company_id=self.company_id,
                agent_id=agent_id,
                query=query,
                max_results=max_results,
            )
            logger.info(
                f"[FS Search] ✅ {result['total_matches']} matches para '{query}'"
            )
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[FS Search] ❌ Erro: {e}", exc_info=True)
            return json.dumps({"error": str(e), "query": query, "matches": []})

    async def _arun(
        self,
        query: str,
        max_results: int = 10,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        return self._run(
            query=query, max_results=max_results, agent_id=agent_id, **kwargs
        )


class FilesystemMetadataTool(BaseTool):
    """
    Retorna metadados do documento (título, tamanho, tipo, data de upload)
    sem ler o conteúdo. Use para contextualizar antes de decidir a estratégia de busca.
    """

    name: str = "filesystem_get_metadata"
    description: str = (
        "Retorna metadados do documento (título, tamanho em tokens, número de seções, "
        "data de upload) sem ler o conteúdo. "
        "Use para contextualizar antes de decidir a estratégia de busca."
    )
    args_schema: Type[BaseModel] = FilesystemMetadataInput

    company_id: str = ""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, **kwargs):
        super().__init__(**kwargs)
        self.company_id = company_id

    def _run(self, agent_id: Optional[str] = None, **kwargs) -> str:
        try:
            logger.info(
                f"[FS Metadata] company={self.company_id} | agent={agent_id}"
            )
            service = get_filesystem_search_service()
            result = service.get_metadata(
                company_id=self.company_id, agent_id=agent_id
            )
            logger.info(f"[FS Metadata] ✅ {result['title']}")
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[FS Metadata] ❌ Erro: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    async def _arun(self, agent_id: Optional[str] = None, **kwargs) -> str:
        return self._run(agent_id=agent_id, **kwargs)


# ===== FACTORY =====


class FilesystemToolFactory:
    """
    Factory para criar tools de File System Search.
    Segue o mesmo pattern de MCPToolFactory.create_tools_for_agent().
    """

    @staticmethod
    def create_tools_for_agent(company_id: str) -> List[BaseTool]:
        """
        Cria as 4 tools de filesystem para um sub-agente.
        Chamada em subagent_tool.py quando retrieval_mode = 'filesystem'.

        Args:
            company_id: ID da empresa (multi-tenant isolation)

        Returns:
            Lista de 4 BaseTool instances
        """
        tools = [
            FilesystemOutlineTool(company_id=company_id),
            FilesystemReadTool(company_id=company_id),
            FilesystemSearchTool(company_id=company_id),
            FilesystemMetadataTool(company_id=company_id),
        ]

        logger.info(
            f"[FilesystemToolFactory] ✅ Criadas {len(tools)} tools para company={company_id}"
        )

        return tools
