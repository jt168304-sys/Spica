# storage.py — Banco de dados chave-valor persistido em JSON
import json, os
from src.utils.logger import WindLogger


class Storage:
    ARQUIVO = "data/storage.json"

    def __init__(self):
        self.logger = WindLogger()
        self._dados = {}
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.ARQUIVO):
            try:
                with open(self.ARQUIVO, "r", encoding="utf-8") as f:
                    self._dados = json.load(f)
            except: pass

    def get(self, chave, padrao=None): return self._dados.get(chave, padrao)

    def set(self, chave, valor):
        self._dados[chave] = valor
        self._flush()

    def delete(self, chave):
        self._dados.pop(chave, None)
        self._flush()

    def _flush(self):
        with open(self.ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(self._dados, f, ensure_ascii=False, indent=2)

    def close(self): self._flush()
