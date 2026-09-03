"""O motor de métrica — SPEC-094 BLOCO D. ⛔ **Aqui não existe provider.**

🔴 A mutação **M1** é estática e está no guarda: nenhum nome de campo, de rota
ou de marca de sistema de gestão pode aparecer nesta pasta — **nem em
comentário**. Um nome de campo escrito num comentário é a semente do `if` que
vem depois: primeiro alguém documenta a exceção, depois alguém a implementa.

Por isso as próprias medições citadas aqui dentro falam em "a fonte piloto", "a
rota de produção" e "a rota de vencimentos". Não é pudor: é que o motor de
métrica **de fato** não precisa saber, e escrever como se não soubesse é o que
mantém a fronteira de pé.

Importar este pacote registra as 16 definições da v1.
"""
from app.comercial.metricas.registry import (  # noqa: F401
    METRICAS,
    MetricDefinition,
    calcular,
    comparar,
    definicao,
    registrar,
    todas,
)

# ⚠️ As definições NÃO são importadas aqui: `registry.py` as carrega por
# INJEÇÃO ao ser importado (ver `_carregar_definicoes`). Import duplo aqui
# registraria duas vezes — e, pior, criaria uma segunda cópia do registry para
# quem carrega `registry.py` por caminho.
