# logger.py — Log em arquivo e terminal
import logging
import os


class WindLogger:
    _ok = False

    def __init__(self, nome="WindIA"):
        if not WindLogger._ok:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            pasta_dados = os.path.join(base_dir, "data")
            os.makedirs(pasta_dados, exist_ok=True)
            logging.basicConfig(
                level=logging.INFO,
                format="[%(asctime)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
                handlers=[logging.FileHandler(os.path.join(pasta_dados, "wind.log"), encoding="utf-8"),
                          logging.StreamHandler()]
            )
            WindLogger._ok = True
        self._log = logging.getLogger(nome)

    def info(self, m):    self._log.info(m)
    def warning(self, m): self._log.warning(m)
    def error(self, m):   self._log.error(m)
