# settings.py — Configuracoes persistentes salvas em JSON
import json
import os
from typing import Any
from src.utils.logger import WindLogger


class Settings:
    PADROES = {"theme_mode": "Dark", "voice_activation": False,
               "api_key": "", "nome_usuario": "Usuario", "idioma_voz": "pt-BR"}

    def __init__(self):
        self.logger = WindLogger()
        # Caminho ABSOLUTO — mesmo problema/correção do storage.py: caminho
        # relativo dependia do diretório de trabalho, que pode diferir entre
        # a Activity e o service.py (processo separado).
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.pasta_dados = os.path.join(base_dir, "data")
        self.ARQUIVO = os.path.join(self.pasta_dados, "settings.json")
        os.makedirs(self.pasta_dados, exist_ok=True)
        self._dados = dict(self.PADROES)
        self._carregar()

    def _carregar(self):
        if os.path.exists(self.ARQUIVO):
            try:
                with open(self.ARQUIVO, "r", encoding="utf-8") as f:
                    self._dados.update(json.load(f))
            except Exception as e:
                self.logger.error(f"[Settings] Falha ao carregar {self.ARQUIVO}: {e}")

    def get(self, chave: str, padrao: Any = None) -> Any:
        self._carregar()
        return self._dados.get(chave, padrao)

    def set(self, chave: str, valor: Any):
        self._carregar()
        self._dados[chave] = valor
        self.save()

    def save(self):
        try:
            with open(self.ARQUIVO, "w", encoding="utf-8") as f:
                json.dump(self._dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Erro ao salvar config: {e}")
