# storage.py — Banco de dados chave-valor persistido em JSON, compartilhado
# de verdade entre a Activity e o service.py (processo separado)
import json
import os
from src.utils.logger import WindLogger


class Storage:
    def __init__(self):
        self.logger = WindLogger()
        # Caminho ABSOLUTO, ancorado na raiz do projeto. Antes era relativo
        # ("data/storage.json"), dependente do diretório de trabalho atual —
        # como o service.py roda num processo separado e pode ter um cwd
        # diferente da Activity, isso podia fazer os dois escreverem em DOIS
        # ARQUIVOS DIFERENTES, cada um com sua própria versão parcial do
        # histórico. É bem provável que fosse a causa raiz da Spica parecer
        # "recapitular" a conversa do zero ao alternar entre chat e bolha.
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.pasta_dados = os.path.join(base_dir, "data")
        self.ARQUIVO = os.path.join(self.pasta_dados, "storage.json")
        os.makedirs(self.pasta_dados, exist_ok=True)
        self._dados = {}
        self._carregar()

    def _carregar(self):
        if os.path.exists(self.ARQUIVO):
            try:
                with open(self.ARQUIVO, "r", encoding="utf-8") as f:
                    self._dados = json.load(f)
            except Exception as e:
                self.logger.error(f"[Storage] Falha ao carregar {self.ARQUIVO}: {e}")

    def get(self, chave, padrao=None):
        # Relê do disco a cada chamada — funciona como um cache compartilhado
        # de verdade entre os dois processos (Activity/service.py), em vez de
        # manter uma cópia em memória que pode ficar desatualizada se o OUTRO
        # processo tiver escrito algo novo enquanto este ficou parado.
        self._carregar()
        return self._dados.get(chave, padrao)

    def set(self, chave, valor):
        self._carregar()  # reincorpora o que o outro processo já salvou antes de sobrescrever
        self._dados[chave] = valor
        self._flush()

    def delete(self, chave):
        self._carregar()
        self._dados.pop(chave, None)
        self._flush()

    def _flush(self):
        try:
            with open(self.ARQUIVO, "w", encoding="utf-8") as f:
                json.dump(self._dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"[Storage] Falha ao salvar {self.ARQUIVO}: {e}")

    def close(self):
        self._flush()
