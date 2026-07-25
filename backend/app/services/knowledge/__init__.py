"""Corpus de conhecimento — SPEC-057 Bloco H.

Condicao geral e o mesmo documento para todas as corretoras. Le-se uma vez, no
nivel da plataforma, e todas consultam de graca pelo conhecimento global que ja
existe.
"""

from .insurance_corpus import InsuranceCorpusService, classificar, extrair_susep

__all__ = ["InsuranceCorpusService", "classificar", "extrair_susep"]
