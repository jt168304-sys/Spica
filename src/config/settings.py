# settings.py — Configuracoes persistentes salvas em JSON
import json, os
from typing import Any
from src.utils.logger import WindLogger


class Settings:
    ARQUIVO = "data/settings.json"
    PADROES = {"theme_mode": "Dark", "voice_activation": False,
               "api_key": "", "nome_usuario": "Usuario", "idioma_voz": "pt-BR"}

    def __init__(self):
        self.logger = WindLogger()
        self._dados = dict(self.PADROES)
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.ARQUIVO):
            try:
                with open(self.ARQUIVO, "r", encoding="utf-8") as f:
                    self._dados.update(json.load(f))
            except:
                pass

    def get(self, chave: str, padrao: Any = None) -> Any:
        return self._dados.get(chave, padrao)

    def set(self, chave: str, valor: Any):
        self._dados[chave] = valor
        self.save()

    def save(self):
        try:
            with open(self.ARQUIVO, "w", encoding="utf-8") as f:
                json.dump(self._dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Erro ao salvar config: {e}")
