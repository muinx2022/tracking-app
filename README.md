# tracking-app

Simple Django tracking dashboard with embeddable `tracker.js`, owner-scoped `/user` analytics UI, and Docker deployment support.

## Local dev

```powershell
.\run_dev.ps1
```

Open:

- `http://127.0.0.1:8777/user/login/`
- `http://127.0.0.1:8777/user/dashboard/`

## Docker deploy

1. Copy `.env.example` to `.env`
2. Set:

```env
USE_SQLITE=0
DEBUG=False
ALLOWED_HOSTS=tracking.trekky.net,127.0.0.1,localhost
DB_NAME=tracking
DB_USER=tracking
DB_PASSWORD=tracking
DB_HOST=db
DB_PORT=5432
```

3. Start:

```bash
docker compose up -d --build
```

App runs on port `8777`.
