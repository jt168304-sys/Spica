# web_service.py — O "Navegador" autônomo da Spica
from duckduckgo_search import DDGS

class WebService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def pesquisar(self, termo, max_resultados=3):
        """
        Faz uma busca silenciosa na web e retorna um texto resumido com os achados.
        """
        print(f"[Spica/Web] 🌐 Buscando na internet por: '{termo}'...")
        try:
            with DDGS() as ddgs:
                resultados = list(ddgs.text(termo, region='br-tz', max_results=max_resultados))
                
                if not resultados:
                    return "Nenhuma informação relevante encontrada na web."

                # Formata os resultados para injetar no cérebro da Groq
                contexto_web = "Resultados da pesquisa na Web:\n"
                for res in resultados:
                    contexto_web += f"- {res.get('title', '')}: {res.get('body', '')}\n"
                
                print("[Spica/Web] ✅ Busca concluída com sucesso!")
                return contexto_web
                
        except Exception as e:
            print(f"[Spica/Web] ❌ Erro ao buscar na web: {e}")
            return f"Erro na pesquisa web: {e}"
