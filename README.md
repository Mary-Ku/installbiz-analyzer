# InstallBiz Analyzer

**InstallBiz Analyzer** - сервис загрузки и анализа текстовых файлов.

Для запуска приложения используйте команду:
```bash
docker compose up --build
```

Локальный `.env` не нужен: все настройки заданы в `docker-compose.yml`.
Миграции накатываются автоматически при старте контейнера приложения.
Сервис будет доступен на `http://localhost:8000`.

Остановка приложения:
```bash
docker compose down
```
