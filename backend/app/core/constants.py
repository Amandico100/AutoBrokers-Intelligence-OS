"""
Constantes centralizadas do AutoBrokers V2.

Todas as configurações hardcoded ficam aqui para fácil manutenção.
"""

# =============================================================================
# MEMORY SERVICE
# =============================================================================

# Máximo de fatos armazenados por usuário (evita crescimento infinito)
MEMORY_MAX_FACTS_PER_USER = 8

# Máximo de caracteres por fato (trunca fatos muito longos)
MEMORY_MAX_CHARS_PER_FACT = 150

# Fatos incluídos no contexto do prompt
MEMORY_CONTEXT_MAX_FACTS = 10

# Resumos de sessão incluídos no contexto
MEMORY_CONTEXT_MAX_SUMMARIES = 3

# Pendências incluídas no contexto
MEMORY_CONTEXT_MAX_PENDING_ITEMS = 5

# Truncamento do texto de resumo no contexto
MEMORY_SUMMARY_PREVIEW_MAX_CHARS = 200

# Fatos do usuário incluídos no prompt de summary
MEMORY_SUMMARY_USER_FACTS_LIMIT = 5


# =============================================================================
# AGENT / LLM
# =============================================================================

# Janela de contexto: últimas N mensagens enviadas ao LLM
AGENT_CONTEXT_WINDOW_SIZE = 15


# =============================================================================
# UPLOAD
# =============================================================================

# Tamanho máximo de arquivo para upload (5MB)
UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# Buckets permitidos para upload
UPLOAD_ALLOWED_BUCKETS = ["chat-media", "attachments", "avatars"]

# =============================================================================
# DEFAULT SETTINGS (Fallback)
# =============================================================================
DEFAULT_MEMORY_SETTINGS = {
    "web_summarization_mode": "session_end",
    "web_message_threshold": 20,
    "web_inactivity_timeout_min": 30,
    "whatsapp_summarization_mode": "message_count",
    "whatsapp_sliding_window_size": 50,
    "whatsapp_time_interval_hours": 24,
    "whatsapp_message_threshold": 50,
    "extract_user_profile": True,
    "extract_session_summary": True,
    # 🔴 A MEMORIA NAO PODE RODAR NO MODELO MAIS FRACO DA CASA.
    #
    # E ela que decide QUAIS FATOS do usuario sobrevivem a conversa, e o que
    # ela guarda alimenta todo atendimento seguinte. Erro aqui nao parece erro:
    # parece agente que esqueceu, ou que lembrou errado.
    #
    # 📊 07/08/2026: 148 chamadas em 30 dias, US$ 0,0162 no total. Subir de
    # `gpt-4o-mini` para Haiku 4.5 custa centavos por mes e melhora a extracao
    # de fato — a melhor relacao ganho/custo do sistema inteiro.
    #
    # Haiku e nao Sonnet/Opus de proposito: extrair fato de um texto curto e
    # tarefa mecanica de alto volume. Modelo caro aqui seria pagar raciocinio
    # para uma tarefa que nao raciocina.
    "memory_llm_model": "claude-haiku-4-5-20251001",
    "debounce_seconds": 10,
}
