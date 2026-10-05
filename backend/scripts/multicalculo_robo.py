# -*- coding: utf-8 -*-
"""Os robôs do multicálculo — o comando do Founder (SPEC-129-B U6, T-120).

O código mora em `portal_worker/multicalculo/comando_robo.py` (a imagem do portal-worker só tem esse pacote: o
comando roda onde o robô roda). Este arquivo é a porta de entrada no backend.

    cd backend && python scripts/multicalculo_robo.py --help
    no contêiner do portal-worker:  python -m portal_worker.multicalculo.comando_robo --help
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from portal_worker.multicalculo.comando_robo import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
