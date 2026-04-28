# Document Processing System

API REST para processamento assíncrono de documentos de texto com monitoramento em tempo real.

## Sobre o Projeto

O sistema permite carregar arquivos `.txt`, processá-los em lote e extrair métricas de conteúdo. Tudo de forma assíncrona e não bloqueante. Cada processo tem um ciclo de vida completo com controle de estado, e os resultados são atualizados incrementalmente conforme os arquivos são analisados.

A ideia central foi manter a arquitetura simples e funcional, mantendo a simplicidade. O processamento roda em background via `BackgroundTasks` do FastAPI, e o banco de dados serve tanto para persistência quanto para coordenação de estado entre o worker e a API.

---

## Funcionalidades

- Processamento assíncrono de múltiplos arquivos `.txt`
- Extração de métricas por arquivo e agregadas: palavras, linhas, caracteres, palavras mais frequentes e resumo de conteúdo
- Controle completo do ciclo de vida: iniciar, pausar, retomar, parar
- Resultados incrementais — atualizados a cada arquivo processado
- Atualizações em tempo real via WebSocket
- Interface web para monitoramento
- Persistência de estados e resultados no PostgreSQL

### Estados do Processo

| Estado | Descrição |
|---|---|
| `RUNNING` | Processamento em andamento |
| `PAUSED` | Pausado temporariamente |
| `COMPLETED` | Finalizado com sucesso |
| `FAILED` | Encerrado com erro |
| `STOPPED` | Interrompido manualmente |

---

## Tecnologias

- **Python 3.12**
- **FastAPI** — framework web e WebSocket
- **SQLAlchemy** — ORM
- **PostgreSQL** — banco de dados
- **Alembic** — migrações
- **Docker + Docker Compose** — ambiente de execução

---

## Como Rodar

### Pré-requisitos

- Docker
- Docker Compose

### Subindo o ambiente

```bash
git clone <repo-url>
cd <repo>
docker compose up --build
```

A API estará disponível em `http://localhost:8000/process`.  
A interface web pode ser acessada em `http://localhost:8000`.

### Rodando as migrações manualmente (opcional)

As migrações rodam automaticamente na inicialização. Caso precise rodar manualmente:

```bash
docker compose exec app alembic upgrade head
```

---

## Dados de Teste

A pasta `data/input/` contém 10 arquivos `.txt` com textos clássicos da literatura e filosofia, cada um com mais de 500 palavras:

- Pride and Prejudice
- Moby Dick
- Frankenstein
- Huckleberry Finn
- A Tale of Two Cities
- The Republic (Plato)
- Federalist No. 10
- Gettysburg Address + Second Inaugural
- On the Origin of Species
- The Wealth of Nations

Para popular o banco com esses arquivos via script:

```bash
docker compose exec app python scripts/seed_files.py
```

---

## Testes

```bash
docker compose exec app pytest tests/ -v
```

Os testes cobrem os principais fluxos: iniciar processo, verificar status, listar processos, parar, e validar resultados após conclusão.

---

## Endpoints Principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/process/start` | Inicia um novo processo |
| GET | `/process/status/{id}` | Consulta o estado atual |
| GET | `/process/results/{id}` | Retorna os resultados |
| POST | `/process/stop/{id}` | Para o processo |
| POST | `/process/pause/{id}` | Pausa o processo |
| POST | `/process/resume/{id}` | Retoma o processo |
| GET | `/process/list` | Lista todos os processos |
| WS | `/process/ws/{id}` | Atualizações em tempo real |

Documentação completa dos endpoints em [`API_DOCS.md`](./API_DOCS.md).

---

## Decisões Técnicas

**Por que não usar o Celery?**  
O Celery é uma ferramenta de workers distribuídos muito eficiente. Contudo, um sistema de processamento local não precisa de tanto. O `BackgroundTasks` do FastAPI é suficiente e elimina a complexidade de configurar um broker externo como Redis ou RabbitMQ.

**Por que resultados incrementais?**  
Isso permite que o cliente acompanhe o progresso via WebSocket ou polling sem precisar esperar o processamento completo.

**Migrações com Alembic**  
Toda alteração de schema é versionada. O histórico de migrações reflete a evolução do modelo de dados ao longo do desenvolvimento.

---

## Estrutura do Projeto

```
.
├── app/
│   ├── api.py              # Endpoints e WebSocket
│   ├── worker.py           # Lógica de processamento assíncrono
│   ├── processor.py        # Extração de métricas de texto
│   ├── crud.py             # Operações no banco de dados
│   ├── models.py           # Modelos SQLAlchemy
│   ├── schemas.py          # Schemas Pydantic
│   ├── database.py         # Configuração da sessão
│   ├── websocket_manager.py
│   ├── main.py
│   ├── static/
│   └── templates/
├── alembic/
├── data/input/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── API_DOCS.md
└── requirements.txt
```
