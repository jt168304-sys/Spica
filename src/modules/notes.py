# notes.py — CRUD de notas salvas em JSON local
import json, os, datetime
from typing import List, Dict, Optional
from src.utils.logger import WindLogger


class NotesManager:
    _instancia: Optional["NotesManager"] = None
    ARQUIVO = "data/notas.json"

    @classmethod
    def get_instance(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.logger = WindLogger()
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.ARQUIVO):
            self._salvar([])
            self.logger.info("Arquivo de notas criado.")

    def _carregar(self) -> List[Dict]:
        try:
            with open(self.ARQUIVO, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _salvar(self, notas: List[Dict]):
        with open(self.ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(notas, f, ensure_ascii=False, indent=2)

    def criar(self, titulo: str, conteudo: str) -> Dict:
        notas = self._carregar()
        nova = {"id": self._novo_id(notas), "titulo": titulo, "conteudo": conteudo,
                "criado_em": datetime.datetime.now().isoformat()}
        notas.append(nova)
        self._salvar(notas)
        return nova

    def listar_todas(self) -> List[Dict]:
        return sorted(self._carregar(), key=lambda n: n.get("criado_em", ""), reverse=True)

    def atualizar(self, nota_id: int, titulo: str, conteudo: str) -> bool:
        notas = self._carregar()
        for n in notas:
            if n.get("id") == nota_id:
                n.update({"titulo": titulo, "conteudo": conteudo,
                          "editado_em": datetime.datetime.now().isoformat()})
                self._salvar(notas)
                return True
        return False

    def deletar(self, nota_id: int) -> bool:
        notas = self._carregar()
        filtradas = [n for n in notas if n.get("id") != nota_id]
        if len(filtradas) < len(notas):
            self._salvar(filtradas)
            return True
        return False

    def _novo_id(self, notas) -> int:
        return max((n.get("id", 0) for n in notas), default=0) + 1
