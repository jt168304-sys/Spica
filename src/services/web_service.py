# web_service.py — O "Navegador" autônomo e leve da Spica
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
        Faz uma busca HTTP leve usando endpoints JSON do DuckDuckGo.
        """
        print(f"[Spica/Web] 🌐 Buscando na internet por: '{termo}'...")
        try:
            import requests

            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            }

            # Tenta via API Instant Answer JSON em português
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(termo)}&format=json&no_html=1&kl=br-pt"
            resp = requests.get(url, headers=headers, timeout=8)

            resultados = []

            if resp.status_code == 200:
                data = resp.json()

                # Pega resposta direta se houver
                if data.get("AbstractText"):
                    resultados.append(f"- Resumo: {data.get('AbstractText')}")

                # Pega tópicos relacionados
                related = data.get("RelatedTopics", [])
                for item in related:
                    if isinstance(item, dict) and "Text" in item:
                        resultados.append(f"- {item['Text']}")
                    if len(resultados) >= max_resultados:
                        break

            # Fallback para busca HTML lite se a API principal não retornar tópicos suficientes
            if not resultados:
                url_lite = f"https://lite.duckduckgo.com/lite/"
                payload = {"q": termo, "kl": "br-pt"}
                resp_lite = requests.post(url_lite, data=payload, headers=headers, timeout=8)

                if resp_lite.status_code == 200:
                    import re
                    snippets = re.findall(r'<td class="result-snippet">(.*?)</td>', resp_lite.text, re.DOTALL)
                    for snip in snippets[:max_resultados]:
                        snip_limpo = re.sub(r'<[^>]+>', '', snip).strip()
                        if snip_limpo:
                            resultados.append(f"- {snip_limpo}")

            if not resultados:
                return "Nenhuma informação relevante encontrada na web."

            contexto_web = "Resultados da pesquisa na Web:\n" + "\n".join(resultados)
            print("[Spica/Web] ✅ Busca concluída com sucesso!")
            return contexto_web

        except Exception as e:
            print(f"[Spica/Web] ❌ Erro ao buscar na web: {e}")
            return f"Erro na pesquisa web: {e}"
