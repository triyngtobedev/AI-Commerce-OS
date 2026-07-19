# Volume persistente no Railway

Sem volume, o SQLite (`pipeline_jobs.db`) e os vídeos gerados em `output/` são perdidos a cada deploy ou restart do container.

## Como configurar

### 1. No Railway Dashboard

1. Abra seu projeto → selecione o serviço `ai-commerce-os`
2. Vá em **Settings → Volumes → Add Volume**
3. Configure:
   - **Mount path:** `/app/persistent`
   - **Size:** mínimo 5 GB (vídeos ocupam espaço)
4. Clique em **Save** — o serviço será reiniciado automaticamente

### 2. Variáveis de ambiente (opcional — o entrypoint já define defaults)

Se quiser customizar os caminhos, adicione em **Variables**:

```
DATABASE_PATH=/app/persistent/database/pipeline_jobs.db
OUTPUT_DIR=/app/persistent/output
REPORTS_DIR=/app/persistent/reports
```

### 3. Verificar

Após o redeploy, acesse:

```
GET /api/v1/health
```

O campo `persistent_storage` deve aparecer como `true` quando o volume estiver montado corretamente.

## Estrutura do volume

```
/app/persistent/
├── database/
│   └── pipeline_jobs.db    ← jobs e callbacks do n8n
├── output/
│   ├── video_final.mp4     ← vídeos gerados
│   └── ...
└── reports/
    └── relatorio_YYYY-MM-DD.md
```

## Alternativa: armazenamento externo (recomendado para produção)

Para não depender de volume Railway, considere migrar para:

- **Cloudflare R2** (gratuito até 10 GB) — para `output/` e `reports/`
- **PlanetScale ou Supabase** — para substituir o SQLite por PostgreSQL

O `api/services/job_store.py` usa SQLite via `DATABASE_PATH` — trocar a URL de conexão é suficiente para migrar para Postgres.
