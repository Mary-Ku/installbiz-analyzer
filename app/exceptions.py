"""Содержит классы исключений приложения InstallBiz Analyzer."""


class NoDownloadProgressError(Exception):
    """Внешний API не возвращает содержимое запрошенных файлов."""


class RequestFailedError(Exception):
    """Запрос к внешнему API завершился ошибкой."""

    def __init__(self, status_code: int, retry_after: float = 0.0) -> None:
        """Сохраняет статус ответа и время паузы в секундах до повтора запроса."""
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f'Запрос к внешнему API завершился ошибкой ({status_code}).')
