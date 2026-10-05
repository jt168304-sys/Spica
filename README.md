# Spica

Assistente virtual para Android, feita em Python com Kivy/KivyMD. Funciona como app normal e também como uma bolha flutuante com expressões, que fica por cima de outros apps e escuta e responde mesmo com o app minimizado.

**Versão atual: 1.1**

## O que ela faz

- **Conversa por texto ou voz**, usando `openai/gpt-oss-120b` (Groq) como motor de IA.
- **Pesquisa na web**: a própria IA decide quando pesquisar, usando a pesquisa embutida do Groq (`browser_search`), e cita a fonte pelo nome. Se a pesquisa nativa falhar, usa ferramentas locais como reserva.
- **Ferramentas**: clima atual e previsão de 3 dias (Open-Meteo) e calculadora exata.
- **Entende imagens**: você manda uma foto e ela analisa e responde (modelo de visão da Qwen via Groq).
- **Escuta contínua fora do app**: com a bolha ativa, o app é minimizado e a Spica continua ouvindo (testado no Android 14).
- **Fala em voz alta**, com o motor de texto para voz nativo do Android.
- **Bolha flutuante com expressões**: a IA se classifica em um de 6 humores (neutro, feliz, surpresa, confusa, triste, chocada) e a expressão muda sozinha. Dá para arrastar a bolha, e um toque abre o menu de falar, mutar ou fechar.
- Sabe a data e a hora reais do aparelho a cada resposta.
- Tema claro/escuro nas configurações.

## Como funciona por baixo dos panos

O app inteiro é Python, sem Java/Kotlin escrito à mão. O acesso às APIs nativas do Android (overlay, TTS, WakeLock, AudioRecord, seletor de imagens) é feito via [pyjnius](https://github.com/kivy/pyjnius).

### Escuta em segundo plano (Android 14)

No Android 12+, o reconhecimento de voz do Google entrega silêncio quando o app não está visível. A solução tem 4 partes:

1. **Foreground service com tipo `microphone`**: o serviço (`service.py`) é declarado no manifesto com `foregroundServiceType="microphone"`. O p4a 2024.01.21 não gera esse atributo, então o workflow clona o p4a e aplica o `patch_p4a_manifest.py` antes do build (`p4a.source_dir = ./p4a-local`).
2. **AudioRecord + Whisper**: o áudio é capturado no processo do serviço e transcrito pelo Whisper do Groq (`mic_recorder.py`, `voice_service.py`, `listen_ipc.py`).
3. **Bolha de sobreposição** (`SYSTEM_ALERT_WINDOW`), que mantém o processo com prioridade alta.
4. **Isenção de otimização de bateria** e `moveTaskToBack` para minimizar o app sem fechá-lo (`src/utils/keepalive.py`).

O diagnóstico completo está em `docs/android14-escuta-continua.md`.

### Pesquisa e ferramentas

- **Modo principal**: `browser_search` do Groq (roda nos servidores deles) + `clima` e `calcular` locais.
- **Modo reserva**: `buscar_web` (DuckDuckGo) e `ler_pagina`, executadas no aparelho. O DuckDuckGo costuma bloquear o app, por isso não é o modo principal.
- Se tudo falhar, a Spica avisa que não conseguiu pesquisar, em vez de inventar.

### Estrutura

```
main.py                        Activity (UI), inicialização e captura de erros
service.py                     Foreground service (escuta e bolha em segundo plano)
buildozer.spec                 Configuração de build
patch_p4a_manifest.py          Insere foregroundServiceType=microphone no manifesto do p4a
extra_manifest.xml             Bloco <queries> exigido desde o Android 11

src/
├── core/app_manager.py        App principal: tema, telas, permissões
├── ui/
│   ├── image_handler.py       Seletor de imagem (câmera/galeria)
│   └── screens/               chat_screen.py, settings_screen.py
├── services/
│   ├── groq_service.py        API do Groq (texto, visão), tool calling e humor
│   ├── ferramentas.py         buscar_web, ler_pagina, clima, calcular
│   ├── web_search.py          Busca DuckDuckGo (modo reserva)
│   ├── mood_service.py        Lê assets/expressoes/humor.json e extrai [HUMOR:xxx]
│   ├── voice_service.py       Reconhecimento de voz (SpeechRecognizer / Whisper)
│   ├── mic_recorder.py        Captura de áudio PCM (AudioRecord)
│   ├── listen_ipc.py          Pedido de escuta entre a Activity e o serviço
│   ├── fg_service.py          Foreground service (tipo microphone)
│   ├── tts_service.py         Texto para voz nativo
│   ├── overlay.py             Bolha flutuante
│   └── web_service.py         Scraper antigo, sem uso (pode ser removido)
├── utils/                     logger, service_log, permissions, thread_safe, keepalive
└── config/settings.py         Configurações persistentes (JSON local)

assets/
├── expressoes/                PNGs por humor (boca aberta/fechada) + humor.json
└── live2d/                    Modelo Live2D (em pausa, previsto para a 1.2)
```

## Build

O APK é gerado pelo GitHub Actions (`.github/workflows/build.yml`), com Buildozer e python-for-android. Basta dar push na `main` ou disparar manualmente pela aba Actions. O build **depende do passo que prepara o p4a** (veja acima), então não rode o `buildozer` local sem ele.

## Configuração

A Spica precisa de uma chave de API do Groq (gratuita):

1. Crie uma conta em [console.groq.com](https://console.groq.com).
2. Gere uma API Key.
3. No app: Configurações → cole a chave.

Para a bolha, libere a permissão "Exibir sobre outros apps" (o app leva você à tela certa). Na primeira ativação, ele também pede a isenção de otimização de bateria.

## Requisitos

- Testada no Android 10 e no Android 14 (Moto G24). `minapi = 24`.
- Internet (a IA roda na nuvem).

## Limitações conhecidas

- **Sem corretor de texto no chat**: o campo do Kivy não lida bem com teclado preditivo. Previsto para a 1.3, com campo nativo do Android.
- A pesquisa na web pode não achar canais ou pessoas muito pequenos.

## Roadmap

- **1.0**: versão bruta (chat, visão, voz e bolha).
- **1.1**: ajustes finos, suporte ao Android 14 e pesquisa na web.
- **1.2**: design novo (paleta baseada no modelo) e modelo V-tuber Live2D.
- **1.3**: ajustes finos.
