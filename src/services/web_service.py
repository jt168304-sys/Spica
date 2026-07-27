# web_service.py — O "Navegador" autônomo e leve da Spica
import re
import urllib.parse

class WebService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def pesquisar(self, termo, max_resultados=3):
        """
        Faz uma busca HTTP direta no DuckDuckGo (versão HTML leve) sem bibliotecas C/C++.
        """
        print(f"[Spica/Web] 🌐 Buscando na internet por: '{termo}'...")
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(termo)}"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                return "Não foi possível conectar ao motor de busca."

            # Extrai títulos e trechos (snippets) do HTML retornado usando Regex
            html = resp.text
            titulos = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</span>', html, re.DOTALL)

            resultados = []
            for t, s in zip(titulos, snippets):
                # Limpa tags HTML remanescentes e entidades do texto
                t_limpo = re.sub(r'<[^>]+>', '', t).strip()
                s_limpo = re.sub(r'<[^>]+>', '', s).strip()
                if t_limpo and s_limpo:
                    resultados.append(f"- {t_limpo}: {s_limpo}")
                if len(resultados) >= max_resultados:
                    break

            if not resultados:
                return "Nenhuma informação relevante encontrada na web."

            contexto_web = "Resultados da pesquisa na Web:\n" + "\n".join(resultados)
            print("[Spica/Web] ✅ Busca concluída com sucesso!")
            return contexto_web

        except Exception as e:
            print(f"[Spica/Web] ❌ Erro ao buscar na web: {e}")
            return f"Erro na pesquisa web: {e}"
