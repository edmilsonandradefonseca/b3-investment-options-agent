# React V1.1 — validação rápida no laptop

Branch: `feat/react-functional-v1-laptop`. Base funcional: `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md` em `3b9c0f2`.

## Onde cada parte roda

| Máquina | Responsabilidade |
|---|---|
| Windows | React no navegador durante a validação; posteriormente, aplicativo Tauri instalado. |
| Ubuntu | Backend B3 já existente, acessado pelo Windows na porta 8000. |

**Os comandos do Ubuntu abaixo não instalam nem executam o React.** Eles atualizam a API existente uma vez porque esta versão acrescentou `GET /portfolio/current` e `GET/POST /capital-profile`. Sem essa atualização, o frontend abre no Windows, mas carteira atual e capital ficam indisponíveis. As importações e as análises que já existiam continuam usando as rotas antigas.

## 1. Executar o frontend no Windows

No PowerShell, com Node.js instalado:

```powershell
git clone -b feat/react-functional-v1-laptop https://github.com/edmilsonandradefonseca/b3-investment-options-agent.git
cd b3-investment-options-agent/frontend
npm ci
npm run dev
```

Abra `http://localhost:5173`. Em **Configurar backend**, informe `http://IP_DO_UBUNTU:8000` e teste a conexão. O React é servido no Windows; todas as consultas financeiras são enviadas à API do Ubuntu.

## 2. Atualizar somente a API no Ubuntu (uma vez)

Faça esta etapa para habilitar a leitura do snapshot BTG e a persistência do capital. Confirme primeiro que a árvore em `/opt/b3-investment-options-agent` está limpa (`git status --short`); preserve alterações locais antes de trocar de branch.

```bash
cd /opt/b3-investment-options-agent
git status --short
git fetch origin
git switch feat/react-functional-v1-laptop
git pull --ff-only origin feat/react-functional-v1-laptop
./.venv/bin/python -m pip install -e .
sudo systemctl restart b3-runtime.service
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/portfolio/current
```

O `curl` com `127.0.0.1` acima testa **apenas a API dentro do Ubuntu**. Para o Windows alcançá-la, confira o endereço de escuta em `/etc/b3-runtime.env`: `B3_API_HOST` deve ser o IP LAN do Ubuntu (por exemplo, `192.168.1.20`), não `127.0.0.1`. Reinicie o serviço após ajustar essa variável e teste `http://IP_DO_UBUNTU:8000/health` no Windows. Permita a porta 8000 somente na rede local. Não coloque tokens no frontend.

Depois, no Windows, carregue o Excel BTG, confira ações e opções, salve o capital e envie uma nota PDF pequena.

## Estado funcional

- Cinco áreas e Copilot persistente; seleção de posição informa o ticker ao Copilot.
- Carteira BTG validada e lida do servidor; notas PDF em até 100 arquivos com resultado por arquivo, ou um ZIP usando o endpoint atual; capital BTG persistido em SQLite.
- Opções abertas e transações disponíveis; consultas de oportunidades, Strategy Lab e mercado usam `/orchestrate`; análise de ativo usa `/analysis/live/{ticker}` e `/research/news/{ticker}`.
- Resultado econômico, dividendos, histórico realizado de opções, ranking determinístico, preço histórico com indicadores, fundamentos e research institucional dependem de novos contratos canônicos. Essas áreas exibem indisponibilidade explícita.
- O processamento do ZIP atual é síncrono. Lotes grandes devem ser validados em seguida com jobs assíncronos e progresso por arquivo.

Para gerar o aplicativo Windows posteriormente, use `npm run windows:build` no Windows com a cadeia Rust/Tauri configurada. O navegador local acelera a validação funcional antes do instalador.
