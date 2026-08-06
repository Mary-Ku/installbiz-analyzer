# InstallBiz Analyzer

## Создание БД и накатывание миграций

Запустить Postgres, создать локальную бд и накатить миграции:
```bash
# запуск контейнера postgres
docker run --rm --name installbiz_analyzer -v $(pwd)/_postgres:/var/lib/postgresql/data -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:17

# создание БД installbiz_analyzer
docker exec -it installbiz_analyzer createdb -U postgres installbiz_analyzer

# накатить миграции
uv run alembic upgrade head
```

Для работы с базой данных локально с psql используйте команду:
```bash
psql -h localhost -p 5432 -U postgres -d installbiz_analyzer
```

## Проверка проекта

### Mypy

Запустить проверку MyPy можно одной из следующих команд:

```bash
uv run env PYTHONPATH=$(pwd) mypy .
```
или
```bash
mypy .
```

### Ruff

```bash
uv run env PYTHONPATH=$(pwd) ruff check .
```
или
```bash
ruff check .
```
