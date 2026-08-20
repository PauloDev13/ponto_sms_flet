# desktop — Módulo LEGADO (descontinuado)

> **AVISO DE DEPRECIAÇÃO**: esta pasta contém a **aplicação desktop legada** em Flet/PyInstaller.
> A aplicação principal do projeto é a **versão web** (`backend/app` + `frontend`).
> Este módulo é mantido **estritamente para compatibilidade legada** e não recebe mais
> novas funcionalidades nem testes automatizados.

## Por que este módulo existe ainda?

Historicamente o ponto eletrônico rodava como um aplicativo desktop (Flet + PyInstaller)
instalado em estações Windows. A refatoração para o monorepo web (FastAPI + HTML/CSS/JS)
transferiu toda a lógica de scraping, geração de planilhas/PDFs e manipulação de sessão
para `backend/`, desacoplada de qualquer UI.

O código desta pasta é mantido apenas para:

- Execução isolada em circunstâncias excepcionais (`python -m desktop.main`).
- Referência histórica dos seletores do portal e do fluxo original.

## O que NÃO fazer

- **Não importe** qualquer módulo de `desktop/` a partir de `backend/` — os dois
  mundos são independentes (verificado por CI/revisão de código).
- **Não acrescente** novas funcionalidades aqui. Alterações funcionais devem ir para
  `backend/app` + `backend/core`.
- **Não dependa** desta pasta em testes automatizados da suíte `tests/`.

## Estrutura legada

```
desktop/
  main.py          # ponto de entrada Flet (emite DeprecationWarning ao executar)
  models/          # PageManager, SplashScreen
  utils/           # validação, máscaras, share_model
  controls/        # componentes de interface (Flet)
  config/          # config_env.py (leitura do .env legado)
  services/        # authenticate_service, data/, compress/divide_pdf_file
  requirements.txt # dependências do desktop (flet, etc.) — NÃO usar no backend
```

A execução isolada emitirá um `DeprecationWarning` no terminal. Para novos
desenvolvedores, consulte `backend/` (web) e a documentação de deploy em `docs/`.