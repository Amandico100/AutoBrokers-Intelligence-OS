"""Auxiliary & Routine Factory — SPEC-058.

Transforma "queria que alguem fizesse X" no padrao de trabalho CERTO, em vez de
criar um Agent para tudo.
"""

from .factory import AuxiliaryFactory, classificar_padrao, fingerprint, redigir

__all__ = ["AuxiliaryFactory", "classificar_padrao", "fingerprint", "redigir"]
