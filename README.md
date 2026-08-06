# InstallBiz Analyzer

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
