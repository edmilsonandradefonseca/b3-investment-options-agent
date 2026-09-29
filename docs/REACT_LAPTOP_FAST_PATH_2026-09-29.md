# React V1.1 — validação rápida no laptop

Branch: `feat/react-functional-v1-laptop`. Base funcional: `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md` em `3b9c0f2`.

## Caminho mais curto

No servidor Ubuntu, atualize o código e reinicie o serviço B3 que serve `b3_agent.server:app`:

```bash
cd /opt/b3-investment-options-agent
git fetch origin
git switch feat/react-functional-v1-laptop
git pull --ff-only origin feat/react-functional-v1-laptop
./.venv/bin/python -m pip install -e .
sudo systemctl restart b3-runtime.service
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/portfolio/current
```

O instalador do runtime configura `B3_API_HOST=127.0.0.1` por padrão. Para acessar a API pelo laptop, altere **somente** `B3_API_HOST` para o IP LAN do Ubuntu em `/etc/b3-runtime.env` (por exemplo, `192.168.1.20`), reinicie `b3-runtime.service` e teste `http://IP_DO_UBUNTU:8000/health` do laptop. Restrinja o acesso à rede local no firewall. Não coloque tokens no frontend. Os endpoints de carteira e capital exigem este novo backend; apontar a interface para a versão antiga deixa essas áreas indisponíveis.

No laptop Windows, com Node.js instalado, execute no PowerShell:

```powershell
git clone -b feat/react-functional-v1-laptop https://github.com/edmilsonandradefonseca/b3-investment-options-agent.git
cd b3-investment-options-agent/frontend
npm ci
npm run dev
```

Abra `http://localhost:5173` e, em **Configurar backend**, informe `http://IP_DO_UBUNTU:8000`. Primeiro valide a conexão, carregue o Excel BTG e confira ações/opções; depois salve capital e envie uma nota PDF pequena. A API deve estar acessível na rede do laptop, e CORS permite o endereço local de desenvolvimento.

## Estado funcional

- Cinco áreas e Copilot persistente; seleção de posição informa o ticker ao Copilot.
- Carteira BTG validada e lida do servidor; notas PDF em até 100 arquivos com resultado por arquivo, ou um ZIP usando o endpoint atual; capital BTG persistido em SQLite.
- Opções abertas e transações disponíveis; consultas de oportunidades, Strategy Lab e mercado usam `/orchestrate`; análise de ativo usa `/analysis/live/{ticker}` e `/research/news/{ticker}`.
- Resultado econômico, dividendos, histórico realizado de opções, ranking determinístico, preço histórico com indicadores, fundamentos e research institucional dependem de novos contratos canônicos. Essas áreas exibem indisponibilidade explícita.
- O processamento do ZIP atual é síncrono. Lotes grandes devem ser validados em seguida com jobs assíncronos e progresso por arquivo.

Para gerar o aplicativo Windows posteriormente, use `npm run windows:build` no Windows com a cadeia Rust/Tauri configurada. O navegador local acelera a validação funcional antes do instalador.
