import sys

# O CrewAI loga emojis (ex.: 🚀, 📋) no console. No Windows, o codepage padrão
# do terminal (cp1252/cp437) não sabe codificar esses caracteres e cada log
# vira um "UnicodeEncodeError" silencioso (capturado internamente pelo
# CrewAIEventsBus, mas polui a saída). Força stdout/stderr para UTF-8 assim
# que qualquer coisa deste pacote é importada.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
