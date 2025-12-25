const rowsPerPage = 15; // Количество строк на странице
const tableData = {}; // Хранилище данных для таблиц (пагинация и поиск)
const activeFilters = {
    online: 'all',
    employee: 'all',
    date_from: null,
    date_to: null,
    location: null,
};

// Инициализация таблиц
document.addEventListener('DOMContentLoaded', function () {
    const tables = ['wifi_clients', 'employees', 'blacklist'];

    tables.forEach(tableId => {
        tableData[tableId] = { currentPage: 1, searchQuery: '' };
        setupSearch(tableId);
    });
    setupFilters();
});

function changePageTo(tableId, pageNumber) {
    tableData[tableId].currentPage = pageNumber;
    loadTableData(tableId);
}

function loadWifiData() {
    const tableId = 'wifi_clients';
    const { currentPage, searchQuery } = tableData[tableId];
    let url = '/admin/tables/wifi_clients';
    let url_query = [`page=${currentPage}`, `rows_per_page=${rowsPerPage}`];

    // Filters
    if (searchQuery.length >= 3) {
        url_query.push(`search=${encodeURIComponent(searchQuery)}`);
    }

    if (activeFilters.online && activeFilters.online !== 'all') {
        url_query.push(`online=${activeFilters.online}`);
    }

    if (activeFilters.employee && activeFilters.employee !== 'all') {
        url_query.push(`employee=${activeFilters.employee}`);
    }

    if (activeFilters.date_from) {
        url_query.push(`date_from=${activeFilters.date_from}`);
    }

    if (activeFilters.date_to) {
        url_query.push(`date_to=${activeFilters.date_to}`);
    }

    if (activeFilters.location) {
        url_query.push(`location=${encodeURIComponent(activeFilters.location)}`);
    }

    // Compile Query
    if (url_query.length > 0) {
        url += `?${url_query.join('&')}`
    }

    fetch(url)
        .then(response => response.json())
        .then(data => { 
            updateTable(tableId, data.data);
            updateFoundCounter(tableId, data.total_rows);
            updatePagination(
                tableId, 
                data.current_page, 
                Math.ceil(data.total_rows / rowsPerPage)
            );
         })
        .catch(error => console.error('Error loading table data:', error));
}

// Функция для загрузки данных с сервера
function loadTableData(tableId) {
    if (tableId === 'wifi_clients'){
        loadWifiData();
    } else {
        const { currentPage, searchQuery } = tableData[tableId];
        let url = `/admin/tables/${tableId}`;
        let url_query = [`page=${currentPage}`, `rows_per_page=${rowsPerPage}`];

        // Filters
        if (searchQuery.length >= 3) {
            url_query.push(`search=${encodeURIComponent(searchQuery)}`);
        }

        // Compile Query
        if (url_query.length > 0) {
            url += `?${url_query.join('&')}`
        }

        fetch(url)
            .then(response => response.json())
            .then(data => { 
                updateTable(tableId, data.data);
                updateFoundCounter(tableId, data.total_rows);
                updatePagination(
                    tableId, 
                    data.current_page, 
                    Math.ceil(data.total_rows / rowsPerPage)
                );
            })
            .catch(error => console.error('Error loading table data:', error));
    }
}

function updateFoundCounter(tableId, totalRows) {
    const pageBody = document.getElementById(tableId);
    const foundCounterSpan = pageBody.querySelector('.found-count');
    foundCounterSpan.innerHTML = getTranslate('html.admin.panel.tables.found_counter', { count: totalRows });
}

// Функция для обновления таблицы
function updateTable(tableId, rows) {
    const tableBody = document.getElementById(`${tableId}_body`);
    const addRowButton = tableBody.querySelector('.add_row_button'); // Сохраняем строку с кнопкой добавления

    tableBody.innerHTML = ''; // Очищаем таблицу

    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = generateRowHTML(tableId, row);
        tableBody.appendChild(tr);
    });

    if (addRowButton) {
        tableBody.appendChild(addRowButton); // Возвращаем строку с кнопкой добавления
    }
}

// Генерация HTML для строки таблицы
function generateRowHTML(tableId, row) {
    if (tableId === 'wifi_clients') {
        // Определяем формат даты на основе userLanguage
        const formattedExpiration = new Date(row.expiration).toLocaleDateString(userLanguage, {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });

        return `
            <td>${row.mac}</td>
            <td>${formattedExpiration}</td>
            <td>${row.employee ? `${row.employee.lastname} ${row.employee.name}` : getTranslate('buttons.no') }</td>
            <td>+${row.phone}</td>
            <td>${row.online ? getTranslate('buttons.yes') : getTranslate('buttons.no')}</td>
            <td>${row.last_location}</td>
            <td>${row.last_ipv4_address}</td>
            <td class="column-controls">
                <button class="btn btn-edit btn-controls" onclick="deauthRow(this)">${getTranslate('buttons.deauth')}</button>
                <button class="btn btn-delete btn-controls" onclick="blockRow(this)">${getTranslate('buttons.block')}</button>
            </td>
        `;
    } else if (tableId === 'employees') {
        return `
            <td data-id>${row.id}</td>
            <td data-lastname>${row.lastname}</td>
            <td data-name>${row.name}</td>
            <td data-phones class="column-phones">
                <ul>${row.phones.map(phone => `<li>+${phone}</li>`).join('')}</ul>
            </td>
            <td class="column-controls">
                <button class="btn btn-edit btn-controls" onclick="editRow(this, 'employees')">${getTranslate('buttons.edit')}</button>
                <button class="btn btn-delete btn-controls" onclick="deleteRow(this, 'employees')">${getTranslate('buttons.delete')}</button>
            </td>
        `;
    } else if (tableId === 'blacklist') {
        return `
            <td class="blocked-phone">+${row}</td>
            <td class="column-controls">
                <button class="btn btn-delete btn-controls" onclick="deleteRow(this, 'blacklist')">${getTranslate('buttons.delete')}</button>
            </td>
        `;
    }
    return '';
}

// Функция для обновления пагинации
function updatePagination(tableId, currentPage, totalPages) {
    const pagination = document.querySelector(`#${tableId} .pagination`);

    const paginationContainer = pagination.querySelector('.page_numbers');
    const prevButton = pagination.querySelector('.btn-prev');
    const nextButton = pagination.querySelector('.btn-next');
    const pageInfo = pagination.querySelector('.page_info');
    pageInfo.textContent = getTranslate(
        'html.admin.panel.tables.page_counter', 
        { current_page: currentPage, total_pages: totalPages }
    );

    if (totalPages <= 1) {
        pagination.style.display = 'none';
    } else {
        pagination.style.display = '';
        // Очистка текущих кнопок пагинации
        paginationContainer.innerHTML = '';
        // Генерация кнопок страниц
        const createPageButton = (page) => {
            const button = document.createElement('button');
            button.className = 'btn btn-number';
            if (page === currentPage) {
                button.classList.add('active');
            }
            button.textContent = page;
            button.onclick = () => changePageTo(tableId, page);
            return button;
        };

        // Видимость кнопок Вперед\Назад
        if (currentPage == 1) {
            prevButton.style.visibility = 'hidden'
        } else {
            prevButton.style.visibility = ''
        }
        if (currentPage == totalPages) {
            nextButton.style.visibility = 'hidden'
        } else {
            nextButton.style.visibility = ''
        }

        // Добавление первой страницы
        if (currentPage > 3) {
            paginationContainer.appendChild(createPageButton(1));
            if (currentPage > 4) {
                const dots = document.createElement('span');
                dots.textContent = '...';
                paginationContainer.appendChild(dots);
            }
        }

        // Добавление кнопок для текущей страницы и соседних
        for (let page = Math.max(1, currentPage - 2); page <= Math.min(totalPages, currentPage + 4); page++) {
            paginationContainer.appendChild(createPageButton(page));
        }

        // Добавление последней страницы
        if (currentPage < totalPages - 3) {
            if (currentPage < totalPages - 4) {
                const dots = document.createElement('span');
                dots.textContent = '...';
                paginationContainer.appendChild(dots);
            }
            paginationContainer.appendChild(createPageButton(totalPages));
        }
    }
}

// Функция для изменения страницы
function changePage(tableId, direction) {
    const { currentPage } = tableData[tableId];
    const newPage = currentPage + direction;

    if (newPage < 1) return;

    tableData[tableId].currentPage = newPage;
    loadTableData(tableId);
}

// Функция для поиска
function setupSearch(tableId) {
    const searchInput = document.getElementById(`${tableId}_search`);
    searchInput.addEventListener('input', () => {
        tableData[tableId].searchQuery = searchInput.value;
        tableData[tableId].currentPage = 1; // Сброс на первую страницу
        loadTableData(tableId);
    });
}

function addRowModal(button, type) {
    const modal = document.getElementById('addRowModal')

    // Генерация HTML формы для модального окна
    const templates = {
        employees: `
            <form class="form form-modal" id="addRowForm">
                <input class="input modal-input" type="text" name="lastname" placeholder="${getTranslate('placeholders.lastname')}" required>
                <input class="input modal-input" type="text" name="name" placeholder="${getTranslate('placeholders.firstname')}" required>
                <label>
                    ${getTranslate('html.admin.panel.edit.phones_label')}:
                    <ul id="phoneList">
                        <li>
                            <input class="input modal-input" type="tel" name="phone" data-tel-input placeholder="${getTranslate('placeholders.phone')}" required>
                        </li>
                    </ul>
                    <button type="button" class="btn btn-add-phone" onclick="addPhoneField(this, true)">${getTranslate('buttons.add_phone')}</button>
                </label>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-save" data-close-button>${getTranslate('buttons.save')}</button>
                    <button type="button" class="btn btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
                </div>
            </form>
        `,
        blacklist: `
            <form class="form form-modal" id="addRowForm">
                <input class="input modal-input" type="tel" name="phone" data-tel-input placeholder="${getTranslate('placeholders.phone')}" required>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-save" data-close-button>${getTranslate('buttons.save')}</button>
                    <button type="button" class="btn btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
                </div>
            </form>
        `
    };

    triggerModalHtml(modal, getTranslate(`html.admin.panel.edit.title.${type}`), templates[type] || '<p>Invalid type</p>');

    // Добавляем обработчики событий после вставки строки
    const phoneInputs = modal.querySelectorAll('input[data-tel-input]');
    for (var phoneInput of phoneInputs) {
        detectPhoneInput(phoneInput)
    }

    // Обработчик отправки формы
    const form = modal.querySelector('#addRowForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = {};

        // Преобразуем данные формы в объект
        formData.forEach((value, key) => {
            if (key === 'phone') {
                // Заменяем префикс +7 или 8 на 7 и удаляем все нецифровые символы
                let phone = value.replace(/\D/g, '').replace(/^(\+?7|8)/, '7');
                if (type === 'employees') {
                    data[key] = data[key] || [];
                    data[key].push(phone);
                } else {
                    data[key] = phone;
                }
            } else {
                data[key] = value.trim();
            }
        });

        // Отправляем запрос на сервер
        fetch(`/admin/tables/${type}/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    loadTableData(type); // Обновляем таблицу
                } else {
                    alert(`Error: ${result.error.description}`);
                }
            })
            .catch(error => console.error('Error:', error));
    });
}

// Функция для удаления строки
function deleteRow(button, type) {
    const row = button.closest('tr');

    if (row.dataset.new === "true") {
        row.remove();
        return;
    }

    const data = {};

    if (type === 'employees') {
        const idInput = row.querySelector('input[name="id"]');
        let originalValue = row.querySelector('td[data-id]').textContent.trim();
        if (idInput) {
            originalValue = idInput.dataset.originalValue || '';
        }
        data['id'] = Number(originalValue);
    } else if (type === 'blacklist') {
        let phone = row.querySelector('td').textContent.trim();
        phone = phone.replace(/\D/g, '').replace(/^(\+?7|8)/, '7');
        data['phone'] = phone;
    }


    fetch(`/admin/tables/${type}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            row.remove();
        } else {
            const modal = document.querySelector("#errorModal");
            triggerModal(modal, getTranslate('errors.admin.modals.delete'), getTranslate('errors.admin.modals.header') + result.error.description);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Функция для сохранения строки
function saveRow(button, type) {
    const row = button.closest('tr');
    const inputs = row.querySelectorAll('input');
    const data = {};
    let hasChanges = false;
    let hasEmptyFields = false;

    inputs.forEach(input => {
        const currentValue = input.value.trim();
        if (!currentValue) {
            hasEmptyFields = true;
        }
    });

    if (hasEmptyFields) {
        const modal = document.querySelector("#errorModal");
        triggerModal(modal, 'Error', getTranslate('errors.must_be_filled'));
        return;
    }

    inputs.forEach(input => {
        const key = input.getAttribute('name');
        const currentValue = input.value.trim();
        const originalValue = input.dataset.originalValue || '';

        if (currentValue !== originalValue) {
            hasChanges = true;
        }

        if (key === 'phone') {
            // Заменяем префикс +7 или 8 на 7 и удаляем все нецифровые символы
            let phone = currentValue.replace(/\D/g, '').replace(/^(\+?7|8)/, '7');
            if (type === 'employees') {
                data[key] = data[key] || [];
                data[key].push(phone);
            } else {
                data[key] = phone;
            }
        } else {
            data[key] = input.name === 'id' ? Number(currentValue) : currentValue;
        }
    });

    if (!hasChanges) {
        convertInputsToCells(inputs, data, type, row, button);
        delete row.dataset.new;
        return;
    }

    fetch(`/admin/tables/${type}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            convertInputsToCells(inputs, data, type, row, button, result.new_id || null);
            delete row.dataset.new;
        } else {
            const modal = document.querySelector("#errorModal");
            triggerModal(modal, getTranslate('errors.admin.modals.save'), getTranslate('errors.admin.modals.header') + result.error.description);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Функция для редактирования строки
function editRow(button, type) {
    const row = button.closest('tr');
    const cells = row.querySelectorAll('td');

    cells.forEach(cell => {
        if (cell.hasAttribute('data-id')) {
            createHiddenInput(cell, 'id');
        } else if (cell.hasAttribute('data-lastname') || cell.hasAttribute('data-name')) {
            createTextInput(cell, cell.hasAttribute('data-lastname') ? 'lastname' : 'name');
        } else if (cell.hasAttribute('data-value')) {
            createTextInput(cell, cell.hasAttribute('data-value'));
        } else if (cell.hasAttribute('data-phones')) {
            editPhoneList(cell);
        }
    });

    updateControlButtons(row, type);
}

// Функция для деавторизации клиента
function deauthRow(button) {
    const row = button.closest('tr');
    const macAddress = row.querySelector('td:first-child').textContent.trim();

    if (!macAddress) {
        const modal = document.querySelector("#errorModal");
        triggerModal(modal, 'Error', getTranslate('errors.admin.tables.mac_is_missing'));
        return;
    }

    fetch(`/admin/hotspot/deauth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mac: macAddress })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadTableData('wifi_clients'); // Обновляем таблицу
        } else {
            const modal = document.querySelector("#errorModal");
            triggerModal(modal, getTranslate('errors.admin.modals.deauth'), getTranslate('errors.admin.modals.header') + result.error.description); 
        }
    })
    .catch(error => console.error('Error:', error));
}

// Функция для блокировки клиента
function blockRow(button) {
    const row = button.closest('tr');
    const macAddress = row.querySelector('td:first-child').textContent.trim();

    if (!macAddress) {
        const modal = document.querySelector("#errorModal");
        triggerModal(modal, 'Error', getTranslate('errors.admin.tables.mac_is_missing'));
        return;
    }

    fetch(`/admin/hotspot/block`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mac: macAddress })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadTableData('wifi_clients'); // Обновляем таблицу
            loadTableData('blacklist'); // Обновляем таблицу
        } else {
            const modal = document.querySelector("#errorModal");
            triggerModal(modal, getTranslate('errors.admin.modals.block'), getTranslate('errors.admin.modals.header') + result.error.description);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Функция для создания скрытого инпута
function createHiddenInput(cell, name) {
    const text = cell.textContent.trim();
    const input = document.createElement('input');
    input.type = 'hidden';
    input.value = text;
    input.name = name;
    input.setAttribute('data-original-value', text);
    cell.appendChild(input);
}

// Функция для создания текстового инпута
function createTextInput(cell, name) {
    const text = cell.textContent.trim();
    const input = document.createElement('input');
    input.type = 'text';
    input.classList = 'table-input';
    input.value = text;
    input.name = name;
    input.setAttribute('data-original-value', text);
    cell.innerHTML = '';
    cell.appendChild(input);
}

// Функция для редактирования списка телефонов
function editPhoneList(cell) {
    const ul = cell.querySelector('ul');
    const phones = Array.from(ul.querySelectorAll('li')).map(li => li.textContent.trim());
    ul.innerHTML = '';

    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'phones-count';
    hiddenInput.value = phones.length;
    hiddenInput.setAttribute('data-original-value', phones.length);
    ul.appendChild(hiddenInput);

    phones.forEach(phone => {
        const li = document.createElement('li');
        const input = document.createElement('input');
        input.type = 'tel';
        input.name = 'phone';
        input.classList = 'table-input';
        input.value = phone;
        input.setAttribute('data-original-value', phone);
        detectPhoneInput(input)

        const deleteButton = createDeleteButton(li, ul);
        li.appendChild(input);
        li.appendChild(deleteButton);
        ul.appendChild(li);
    });

    const addPhoneButton = document.createElement('button');
    addPhoneButton.type = 'button';
    addPhoneButton.className = 'btn btn-add-phone';
    addPhoneButton.textContent = getTranslate('buttons.add_phone');
    addPhoneButton.onclick = () => addPhoneField(addPhoneButton);
    cell.appendChild(addPhoneButton);
}

// Функция для создания кнопки удаления
function createDeleteButton(li, ul) {
    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.textContent = 'x';
    deleteButton.classList = 'btn btn-delete btn-controls';
    deleteButton.onclick = () => {
        li.remove();
        const phonesCountInput = ul.querySelector('input[name="phones-count"]');
        if (phonesCountInput) {
            phonesCountInput.value = Math.max(0, parseInt(phonesCountInput.value, 10) - 1);
        }
    };
    return deleteButton;
}

// Функция для обновления кнопок управления
function updateControlButtons(row, type) {
    const controlsTd = row.querySelector('.column-controls');
    if (controlsTd) {
        controlsTd.innerHTML = '';
        const saveButton = document.createElement('button');
        saveButton.className = 'btn btn-save btn-controls';
        saveButton.textContent = getTranslate('buttons.save');
        saveButton.onclick = () => saveRow(saveButton, type);
        controlsTd.appendChild(saveButton);

        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-delete btn-controls';
        deleteButton.textContent = getTranslate('buttons.delete');
        deleteButton.onclick = () => deleteRow(deleteButton, type);
        controlsTd.appendChild(deleteButton);
    }
}

// Функция для добавления поля телефона
function addPhoneField(button, isModal=false) {
    const ul = button.previousElementSibling;
    const li = document.createElement('li');
    const newInput = document.createElement('input');
    newInput.type = 'tel';
    newInput.name = 'phone';
    newInput.placeholder = getTranslate('placeholders.phone');
    if (isModal) {
        newInput.classList = 'input modal-input';
    } else {
        newInput.classList = 'input table-input';
    }
    detectPhoneInput(newInput)

    const deleteButton = createDeleteButton(li, ul);
    li.appendChild(newInput);
    li.appendChild(deleteButton);
    ul.appendChild(li);

    const phonesCountInput = button.parentElement.querySelector('input[name="phones-count"]');
    if (phonesCountInput) {
        phonesCountInput.value = parseInt(phonesCountInput.value, 10) + 1;
    }
    
}

// Функция для преобразования инпутов в ячейки
function convertInputsToCells(inputs, data, type, row, button, new_id) {
    if (type === 'employees') {
        inputs.forEach(input => {
            if (input.type !== 'hidden' || input.name === 'id') {
                const td = input.closest('td');
                if (td) {
                    if (input.name === 'id' && input.value === '#') {
                        td.textContent = String(new_id);
                    } else if (input.name === 'phone') {
                        const ul = document.createElement('ul');
                        data['phone'].forEach(phone => {
                            const li = document.createElement('li');
                            li.textContent = "+"+phone;
                            ul.appendChild(li);
                        });
                        td.innerHTML = '';
                        td.appendChild(ul);
                    } else {
                        td.textContent = input.value;
                    }
                }
            }
        });
    
        const controlsTd = row.querySelector('.column-controls');
        if (controlsTd) {
            const editButton = document.createElement('button');
            editButton.className = 'btn btn-edit btn-controls';
            editButton.textContent = getTranslate('buttons.edit');
            editButton.onclick = () => editRow(editButton, type);
            controlsTd.insertBefore(editButton, controlsTd.firstChild);
        }
    } else if (type === 'blacklist') {
        inputs.forEach(input => {
            if (input.type !== 'hidden') {
                const td = input.closest('td');
                if (td) {
                    td.textContent = "+"+data['phone'];
                }
            }
        });
    }
    
    button.remove();
}

function setupFilters() {
    // Трехпозиционные переключатели Online / Employee
    document.querySelectorAll('.tri-toggle').forEach(toggle => {
        const target = toggle.dataset.target;

        toggle.querySelectorAll('.tri-option').forEach(opt => {
            opt.addEventListener('click', () => {
                activeFilters[target] = opt.dataset.value;
                reloadWifiTable();
            });
        });
    });

    // Выбор локации
    const locationSelect = document.querySelector('.filter-select');
    if (locationSelect) {
        locationSelect.addEventListener('change', () => {
            activeFilters.location =
                locationSelect.value === 'None' ? null : locationSelect.value;
            reloadWifiTable();
        });
    }

    // Дата (дельта)
    const dateInputStart = document.getElementById('wifi_clients_daterange_start');
    const dateInputStop = document.getElementById('wifi_clients_daterange_stop');
    if (dateInputStart && dateInputStop) {
        dateInputStart.addEventListener('change', () => {
            if (dateInputStart) {
                activeFilters.date_from = dateInputStart.value;
            } else {
                activeFilters.date_to = null;
            }
            reloadWifiTable();
        });
        dateInputStop.addEventListener('change', () => {
            if (dateInputStop) {
                activeFilters.date_to = dateInputStop.value;
            } else {
                activeFilters.date_to = null;
            }
            reloadWifiTable();
        });
    }
}

// Перезагрузка всех таблиц
function reloadWifiTable() {
    tableData['wifi_clients'].currentPage = 1;
    loadWifiData();
}