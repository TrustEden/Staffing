# Alembic Migrations

Run `alembic init migrations` from `backend/` to scaffold migrations. The directory is pre-created so git tracks it; update `alembic.ini` to point at `backend/app/database.py` engine or use `backend/config.py`.

Example:
```bash
cd backend
alembic init ../migrations
```

After scaffolding, generate migrations with:
```bash
alembic revision --autogenerate -m "create core tables"
```
