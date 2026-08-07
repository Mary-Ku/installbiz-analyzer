// Кнопка запуска скачивания и индикатор прогресса (polling раз в 1.5 сек,
// только пока процесс идёт)

const downloadBtn = document.getElementById('download-btn');
const statusEl = document.getElementById('download-status');

const POLL_INTERVAL_MS = 1500;

let pollTimer = null;

// Запускает периодический опрос статуса, если он ещё не идёт
function startPolling() {
    if (pollTimer === null) {
        pollTimer = setInterval(pollStatus, POLL_INTERVAL_MS);
    }
}

// Останавливает периодический опрос статуса
function stopPolling() {
    clearInterval(pollTimer);
    pollTimer = null;
}

// Форматирует дату
function formatNskTime(isoString) {
    return new Date(isoString).toLocaleTimeString('ru-RU', {
        timeZone: 'Asia/Novosibirsk',
    });
}

// Отображает текущий статус и количество файлов в базе
function renderStatus(status) {
    statusEl.classList.toggle('running', status.is_running);

    const filesInDbText = ` Файлов в базе: ${status.files_in_db}.`;

    if (status.is_running) {
        const startedAt = formatNskTime(status.started_at);
        statusEl.textContent =
            `Старт в ${startedAt} по НСК. ` +
            `Получено ${status.received_names} названий, ` +
            `скачано ${status.downloaded_files} из ${status.received_names}.` +
            filesInDbText;
        return;
    }

    statusEl.textContent = (status.message || 'Скачивание не запущено.') + filesInDbText;
}

// Узнаёт эндпоинт статуса, останавливает polling по завершении процесса
async function pollStatus() {
    try {
        const response = await fetch('/api/download/status');
        const status = await response.json();
        renderStatus(status);
        if (!status.is_running) {
            stopPolling();
        }
        return status;
    } catch (error) {
        statusEl.textContent = 'Не удалось получить статус скачивания';
        stopPolling();
        return null;
    }
}

// Запускает скачивание по клику на кнопку
downloadBtn.addEventListener('click', async () => {
    downloadBtn.disabled = true;
    try {
        const response = await fetch('/api/download/start', { method: 'POST' });
        if (response.status === 409) {
            statusEl.textContent = 'Скачивание уже выполняется';
        }
    } finally {
        downloadBtn.disabled = false;
    }

    const status = await pollStatus();
    if (status && status.is_running) {
        startPolling();
    }
});

// При загрузке страницы проверяем статус один раз:
// если скачивание уже идёт (страницу открыли/обновили на ходу), включаем polling
(async () => {
    const status = await pollStatus();
    if (status && status.is_running) {
        startPolling();
    }
})();
