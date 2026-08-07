// Страница файлов: таблица с сортировкой, пагинацией, выбором и расчётами

const tbody = document.getElementById('files-tbody');
const pageInfo = document.getElementById('page-info');
const selectionInfo = document.getElementById('selection-info');
const totalInfo = document.getElementById('total-info');
const statsContainer = document.getElementById('stats-container');
const statsDialog = document.getElementById('stats-dialog');

const PER_PAGE = 20;
const DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

let page = 1;
let totalPages = 1;
let totalFiles = 0;
let order = 'desc';
// Выбранные id файлов; при allSelected=true выбраны все, кроме excludedIds
let selectedIds = new Set();
let allSelected = false;
let excludedIds = new Set();
// id файлов на текущей странице
let pageFileIds = [];

// Форматирует дату из ISO-строки в дату и время по НСК
function formatNskDateTime(isoString) {
    return new Date(isoString).toLocaleString('ru-RU', {
        timeZone: 'Asia/Novosibirsk',
    });
}

// Экранирует строку для вставки в HTML (имена файлов приходят из внешнего API)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Загружает и отображает текущую страницу файлов
async function loadFiles() {
    const response = await fetch(
        `/api/files?page=${page}&per_page=${PER_PAGE}&order=${order}`,
    );
    const data = await response.json();

    totalPages = Math.max(1, Math.ceil(data.total / PER_PAGE));
    totalFiles = data.total;
    pageFileIds = data.files.map((file) => file.id);

    if (data.files.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="3" class="empty-cell">' +
            'Файлов пока нет — нажмите «Загрузить данные»</td></tr>';
    } else {
        tbody.innerHTML = data.files
            .map((file) => {
                const isChecked = allSelected
                    ? !excludedIds.has(file.id)
                    : selectedIds.has(file.id);
                return (
                    `<tr>` +
                    `<td><input type="checkbox" class="file-checkbox" ` +
                    `data-id="${file.id}" ${isChecked ? 'checked' : ''} /></td>` +
                    `<td>${escapeHtml(file.name)}</td>` +
                    `<td>${formatNskDateTime(file.downloaded_at)}</td>` +
                    `</tr>`
                );
            })
            .join('');
    }

    pageInfo.textContent = `Страница ${page} из ${totalPages}`;
    totalInfo.textContent = `Всего файлов: ${data.total}`;
    document.getElementById('prev-page-btn').disabled = page <= 1;
    document.getElementById('next-page-btn').disabled = page >= totalPages;

    updateSelectionInfo();
}

// Показывает, сколько файлов выбрано
function updateSelectionInfo() {
    const selectedCount = allSelected
        ? totalFiles - excludedIds.size
        : selectedIds.size;
    selectionInfo.textContent = `Выбрано файлов: ${selectedCount}`;
}

// Точечный выбор файла чекбоксом
tbody.addEventListener('change', (event) => {
    const checkbox = event.target.closest('.file-checkbox');
    if (!checkbox) {
        return;
    }
    const fileId = Number(checkbox.dataset.id);
    if (allSelected) {
        // При выборе «все файлы» запоминаем снятые галочки как исключения
        if (checkbox.checked) {
            excludedIds.delete(fileId);
        } else {
            excludedIds.add(fileId);
        }
    } else if (checkbox.checked) {
        selectedIds.add(fileId);
    } else {
        selectedIds.delete(fileId);
    }
    updateSelectionInfo();
});

// Выбор всех файлов в базе
document.getElementById('select-all-btn').addEventListener('click', () => {
    allSelected = true;
    selectedIds.clear();
    excludedIds.clear();
    loadFiles();
});

// Сброс выбора
document.getElementById('reset-selection-btn').addEventListener('click', () => {
    allSelected = false;
    selectedIds.clear();
    excludedIds.clear();
    loadFiles();
});

// Переключение сортировки по времени скачивания
document.getElementById('sort-btn').addEventListener('click', (event) => {
    order = order === 'desc' ? 'asc' : 'desc';
    event.target.textContent =
        order === 'desc' ? 'Сортировка: сначала новые' : 'Сортировка: сначала старые';
    page = 1;
    loadFiles();
});

// Пагинация
document.getElementById('prev-page-btn').addEventListener('click', () => {
    if (page > 1) {
        page -= 1;
        loadFiles();
    }
});
document.getElementById('next-page-btn').addEventListener('click', () => {
    if (page < totalPages) {
        page += 1;
        loadFiles();
    }
});

// Расчёт статистики по выбранным файлам, результат — во всплывающем окне
document.getElementById('calc-btn').addEventListener('click', async () => {
    if (!allSelected && selectedIds.size === 0) {
        statsContainer.innerHTML =
            '<p class="stats-error">Выберите файлы для расчёта.</p>';
        statsDialog.showModal();
        return;
    }

    const response = await fetch('/api/stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            file_ids: allSelected ? null : [...selectedIds],
            exclude_ids: [...excludedIds],
        }),
    });
    renderStats(await response.json());
    statsDialog.showModal();
});

// Закрытие окна со статистикой: кнопкой или кликом по фону
document.getElementById('stats-close-btn').addEventListener('click', () => {
    statsDialog.close();
});
statsDialog.addEventListener('click', (event) => {
    if (event.target === statsDialog) {
        statsDialog.close();
    }
});

// Отображает таблицу статистики: строки — файлы и итог, столбцы — цифры 0-9
function renderStats(stats) {
    const headerCells = DIGITS.map((digit) => `<th>${digit}</th>`).join('');
    const fileRows = stats.files
        .map((fileStats) => {
            const cells = DIGITS.map((digit) => `<td>${fileStats.counts[digit]}</td>`).join('');
            return `<tr><td>${escapeHtml(fileStats.file_name)}</td>${cells}</tr>`;
        })
        .join('');
    const totalCells = DIGITS.map((digit) => `<td>${stats.total[digit]}</td>`).join('');

    statsContainer.innerHTML =
        `<h3>Статистика по цифрам</h3>` +
        `<div class="stats-table-wrapper"><table>` +
        `<thead><tr><th>Файл</th>${headerCells}</tr></thead>` +
        `<tbody>` +
        `<tr class="stats-total-row"><td>Итого</td>${totalCells}</tr>` +
        fileRows +
        `</tbody></table></div>`;
}

loadFiles();
