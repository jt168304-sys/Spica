# src/utils/thread_safe.py — Utilitários para thread safety e async
"""
Módulo para gerenciar operações assíncronas e threading com segurança.
Evita race conditions e garante UI updates seguras.
"""

import threading
from typing import Callable, Any, Optional
from functools import wraps
from kivy.clock import Clock
from src.utils.logger import WindLogger

logger = WindLogger()


def safe_ui_update(func: Callable) -> Callable:
    """
    Decorador que garante que updates de UI aconteçam na thread principal.
    
    Uso:
        @safe_ui_update
        def atualizar_label(self, texto):
            self.label.text = texto
    
    Isso garante que a operação seja executada na UI Thread.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        def _execute():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Erro em update UI: {e}")
        
        # Se já está na UI thread, executar diretamente
        if threading.current_thread().name == "MainThread":
            return _execute()
        else:
            # Caso contrário, agendar via Clock
            Clock.schedule_once(lambda dt: _execute(), 0)
    
    return wrapper


def safe_async(callback: Callable[[Any], None], timeout: float = 30.0) -> Callable:
    """
    Decorador para executar função em thread separada com callback seguro.
    
    Uso:
        @safe_async(callback=self._processar_resultado)
        def buscar_dados():
            return requests.get("...")
    
    O resultado será passado para callback de forma segura (na UI thread).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            def _execute():
                try:
                    resultado = func(*args, **kwargs)
                    # Executar callback de forma segura na UI thread
                    Clock.schedule_once(lambda dt: callback(resultado), 0)
                except Exception as e:
                    logger.error(f"Erro em async execute: {e}")
                    Clock.schedule_once(lambda dt: callback(None), 0)
            
            # Executar em thread separada
            thread = threading.Thread(target=_execute, daemon=True)
            thread.start()
        
        return wrapper
    
    return decorator


class ThreadPool:
    """
    Pool de threads simples para gerenciar múltiplas operações concorrentes.
    Evita criar muitas threads desnecessárias.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.active_threads: dict = {}
        self._lock = threading.Lock()
    
    def submit(self, name: str, func: Callable, *args, callback: Optional[Callable] = None, **kwargs):
        """
        Submete tarefa para executor em thread.
        
        Args:
            name: Nome único da tarefa
            func: Função a executar
            args: Argumentos posicionais
            callback: Função chamada com resultado (segura em UI thread)
            kwargs: Argumentos nomeados
        """
        # Evitar duplicatas
        with self._lock:
            if name in self.active_threads and self.active_threads[name].is_alive():
                logger.warning(f"Tarefa {name} já está em execução")
                return
        
        def _execute():
            try:
                resultado = func(*args, **kwargs)
                if callback:
                    Clock.schedule_once(lambda dt: callback(resultado), 0)
                logger.debug(f"Tarefa {name} concluída")
            except Exception as e:
                logger.error(f"Erro em tarefa {name}: {e}")
                if callback:
                    Clock.schedule_once(lambda dt: callback(None), 0)
            finally:
                # Remover da lista de ativas
                with self._lock:
                    if name in self.active_threads:
                        del self.active_threads[name]
        
        thread = threading.Thread(target=_execute, daemon=True, name=f"pool-{name}")
        
        with self._lock:
            self.active_threads[name] = thread
        
        thread.start()
    
    def wait_all(self, timeout: float = 30.0) -> bool:
        """Aguardar que todas as tarefas terminem."""
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            with self._lock:
                if not self.active_threads:
                    return True
            
            time.sleep(0.1)
        
        logger.warning(f"Timeout esperando tarefas (timeout={timeout}s)")
        return False


# Singleton de thread pool global
_global_pool: Optional[ThreadPool] = None


def get_thread_pool() -> ThreadPool:
    """Retorna instância global de ThreadPool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = ThreadPool(max_workers=4)
    return _global_pool


# Exemplo de uso:
# from src.utils.thread_safe import safe_ui_update, get_thread_pool
#
# @safe_ui_update
# def atualizar_label(self, texto):
#     self.label.text = texto
#
# def processar_requisicao():
#     resposta = requests.get("...")
#     return resposta.text
#
# pool = get_thread_pool()
# pool.submit(
#     "minha_tarefa",
#     processar_requisicao,
#     callback=lambda resultado: atualizar_label(self, resultado)
# )
