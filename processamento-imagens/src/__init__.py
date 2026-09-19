"""Módulo de Processamento de Imagens e Sinais do Nature Code.

Análise morfológica de folhas por processamento digital clássico de imagens.

Este pacote é **totalmente independente** do módulo de Inteligência Artificial do
projeto: não importa nada de ``script/ia/``, não fala com o Ollama e não usa modelo
de aprendizado de máquina de espécie alguma. Todo o processamento é determinístico —
a mesma entrada, com os mesmos parâmetros, produz sempre a mesma saída.

A regra é verificada automaticamente por ``tests/test_isolamento.py``.

Estado atual: Fase 3 — apenas validação de entrada e pré-processamento.
"""

__version__ = "0.1.0"
