Spica — Assistente Virtual Android

> **Assistente virtual inteligente com bolha flutuante, desenvolvido em Python + KivyMD**

---

## O que é a Spica?

A **Spica** é uma assistente virtual para Android feito 100% em Python.
Funciona com uma bolha flutuante que
fica sempre visível na tela e pode ser tocada para abrir o painel principal.

### Funcionalidades

| Função | Status |
|---|---|
| 🌬️ Bolha flutuante arrastável | ✅ Pronto |
| 💬 Chat com comandos por texto | ✅ Pronto |
| 📝 Criar e gerenciar notas | ✅ Pronto |
| 🧮 Calculadora inteligente | ✅ Pronto |
| 🌙 Modo escuro/claro | ✅ Pronto |
| 🎙️ Reconhecimento de voz | ✅ Pronto |
| ⚙️ Configurações salvas | ✅ Pronto |
| 🤖 Chat com IA (Groq/Gemini) |  Em breve |
| ⏰ Alarmes e lembretes |  Em breve |
| 🌐 Tradução de texto |  Em breve |

---

## 📁 Estrutura do Projeto

```
WindIA/
├── main.py                     ← Ponto de entrada (execute este!)
├── buildozer.spec              ← Configuração para gerar APK
├── requirements.txt            ← Dependências Python
│
├── assets/
│   ├── images/                 ← Ícones, splash screen
│   └── sounds/                 ← Sons de notificação
│
├── src/
│   ├── core/
│   │   └── app_manager.py      ← Coração do app (tema, telas, ciclo de vida)
│   │
│   ├── ui/
│   │   ├── bubble.py           ← A bolha flutuante (widget principal!)
│   │   ├── main_screen.py      ← Tela base
│   │   └── screens/
│   │       ├── home_screen.py     ← Tela inicial com atalhos
│   │       ├── chat_screen.py     ← Chat com WindIA
│   │       ├── notes_screen.py    ← Gerenciador de notas
│   │       └── settings_screen.py ← Configurações
│   │
│   ├── services/
│   │   └── voice_service.py    ← Reconhecimento de voz (microfone)
│   │
│   ├── modules/
│   │   ├── commands.py         ← Processador central de comandos
│   │   ├── notes.py            ← Lógica de notas
│   │   └── calculator.py       ← Calculadora inteligente
│   │
│   ├── utils/
│   │   ├── logger.py           ← Sistema de logs
│   │   └── permissions.py      ← Permissões Android
│   │
│   ├── database/
│   │   └── storage.py          ← Banco de dados JSON local
│   │
│   └── config/
│       └── settings.py         ← Configurações persistentes
│
├── data/                       ← Criado automaticamente ao rodar
│   ├── notas.json
│   ├── settings.json
│   ├── storage.json
│   └── wind.log
│
└── docs/
    └── tutorial_instalacao.md
```

---

##  Como Executar

### No PC (Windows / Linux / Mac)

```bash
# 1. Clone ou baixe o projeto

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute
python main.py
```

### No Celular com Pydroid 3

1. Instale o **Pydroid 3** na Play Store
2. Abra o Pydroid 3 → vá em **Pip** → instale: `kivy`, `kivymd`
3. Abra o arquivo `main.py` e execute

### No Celular com Termux

```bash
pkg install python
pip install kivy kivymd
python main.py
```

---

##  Gerar APK com Buildozer

> Requer Linux ou WSL no Windows

```bash
# Instalar Buildozer
pip install buildozer

# Na pasta do projeto:
buildozer android debug

# O APK ficará em:
# bin/WindIA-1.0-armeabi-v7a-debug.apk
```

---

## Comandos Disponíveis

| Exemplo | O que faz |
|---|---|
| `Anota que preciso comprar leite` | Cria uma nota |
| `Calcule 10 + 5 × 3` | Realiza o cálculo |
| `Que horas são?` | Mostra a hora atual |
| `Qual a data de hoje?` | Mostra a data |
| `Me conta uma piada` | Conta uma piada |
| `Ajuda` | Lista todos os comandos |

---

##  Configurar API de IA (Opcional)

Para habilitar respostas mais inteligentes:

1. Crie uma conta em [console.groq.com](https://console.groq.com) (gratuito)
2. Gere uma API Key
3. No app: **Configurações → API Key → Cole a chave**

---

##  Licença

Incondicionalmente privada kashira.

---

*Spica — Feita com Python e KivyMD*
