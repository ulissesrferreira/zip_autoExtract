# ⚡ ZipAutoExtract

**ZipAutoExtract** é um utilitário leve e automatizado para Windows que roda em segundo plano (na área de notificação/systray) e extrai de forma imediata qualquer arquivo `.zip` assim que ele chega na sua pasta **Downloads**, sem nenhuma intervenção manual.

---

## ✨ Recursos Principais

- **📥 Extração Imediata**: Monitora a pasta Downloads em tempo real e extrai novos arquivos ZIP assim que o download é concluído pelo navegador (trata renomeações de `.crdownload` e `.part`).
- **🛡️ Tratamento de Bloqueio**: Espera inteligentemente o navegador terminar de gravar o arquivo antes de tentar extraí-lo, evitando arquivos corrompidos.
- **📁 Organização Inteligente**: Cria subpastas nomeadas a partir do arquivo ZIP (ex: `Downloads/projeto.zip` -> `Downloads/projeto/`). Se o nome da pasta colidir, cria novas pastas sequenciais (ex: `projeto (1)`, `projeto (2)`), evitando perda ou sobreposição de dados.
- **🔔 Notificações Nativas**: Exibe um balão de notificação nativo do Windows ao finalizar a extração ou em caso de erro.
- **⚙️ Controle pelo Menu da Bandeja (System Tray)**:
  - **Pausar/Retomar**: Pause a extração automática com um clique.
  - **Ações pós-extração**: Escolha se deseja manter o ZIP original (padrão), enviá-lo para a Lixeira, excluí-lo permanentemente ou movê-lo para uma pasta de backup (`Downloads/Zip_Backup`).
  - **Histórico Recente**: Exibe os últimos 5 arquivos extraídos; clique em qualquer um para abrir a pasta correspondente no Explorer.
  - **Inicialização Automática**: Registre ou remova o extrator para iniciar com o Windows de forma nativa.
- **🔒 Instância Única**: Previne que múltiplas cópias do programa rodem ao mesmo tempo.

---

## ⚙️ Pré-requisitos

- **Python 3.10+** (com `pip` adicionado ao PATH do Windows).

---

## 🚀 Instalação e Execução

1. Abra a pasta do projeto `ZipAutoExtract` no terminal ou Explorer.
2. Execute o arquivo:
   ```bash
   install.bat
   ```
   *Isso instalará as dependências (`watchdog`, `pystray`, `Pillow`, `send2trash`) de forma silenciosa e iniciará o extrator em segundo plano.*

---

## 📁 Estrutura do Projeto

```text
ZipAutoExtract/
├── assets/         # Recursos visuais (ícone do aplicativo)
├── config.json     # Configurações do usuário (gerado automaticamente)
├── extractor.log   # Log de eventos e extrações (gerado automaticamente)
├── install.bat     # Instalador automático de dependências
├── monitor.pyw     # Código fonte principal (sem janela de terminal)
├── README.md       # Este arquivo de documentação
└── requirements.txt# Lista de dependências Python
```

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: [Python](https://www.python.org/)
- **Monitoramento**: [Watchdog](https://pypi.org/project/watchdog/)
- **Tray Icon**: [Pystray](https://pypi.org/project/pystray/)
- **Processamento de Imagem**: [Pillow (PIL)](https://python-pillow.org/)
- **Envio para Lixeira**: [Send2Trash](https://pypi.org/project/Send2Trash/)
