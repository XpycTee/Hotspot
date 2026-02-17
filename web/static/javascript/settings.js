// Функция для загрузки данных с сервера
function loadSettingsData(settingId) {
    let url = `/admin/settings/${settingId}/get`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                updateSettingsPage(settingId, result.data);
            } else {
                alert(`Error: ${result.error.description}`);
            }
        })
        .catch(error => console.error('Error loading table data:', error));
}

function updateRadiusPage(settings) {
    const radiusBody = document.getElementById('radius_body');
    const addRowButton = radiusBody.querySelector('.add_row_button'); // Сохраняем строку с кнопкой добавления
    radiusBody.innerHTML = ''; // Очищаем таблицу

    Object.values(settings).forEach(host => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
        <td data-address>${host.address}</td>
        <td data-name>${host.name}</td>
        <td data-authport>${host.authport}</td>
        <td data-acctport>${host.acctport}</td>
        <td data-coaport>${host.coaport}</td>
        <td class="column-controls">
            <button class="btn btn-edit btn-controls" onclick="editHostModal(this)">${getTranslate('buttons.edit')}</button>
            <button class="btn btn-delete btn-controls" onclick="deleteHostRow(this)">${getTranslate('buttons.delete')}</button>
        </td>
        `
        radiusBody.appendChild(tr);
    });
    radiusBody.appendChild(addRowButton); // Возвращаем строку с кнопкой добавления
}

function updateUsersPage(settings) {
    const usersBody = document.getElementById('users_body');
    const addRowButton = usersBody.querySelector('.add_row_button'); // Сохраняем строку с кнопкой добавления
    usersBody.innerHTML = ''; // Очищаем таблицу

    Object.values(settings).forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
        <td data-username>${user.username}</td>
        <td data-group>${user.group}</td>
        <td class="column-controls">
            <button class="btn btn-edit btn-controls" onclick="editUserModal(this)">${getTranslate('buttons.edit')}</button>
            <button class="btn btn-edit btn-controls" onclick="editUserPasswordModal(this)">${getTranslate('buttons.change_password')}</button>
            <button class="btn btn-delete btn-controls" onclick="deleteUserRow(this)">${getTranslate('buttons.delete')}</button>
        </td>
        `
        usersBody.appendChild(tr);
    });
    usersBody.appendChild(addRowButton); // Возвращаем строку с кнопкой добавления
}

// Функция для обновления таблицы
function updateSettingsPage(settingId, settings) {
    if (settingId === 'radius') {
        updateRadiusPage(settings);
    } else if (settingId === 'users') {
        updateUsersPage(settings);
    }
}

function showModal(title, template, settingId, action) {
    const modal = document.getElementById('addRowModal')
    const overlay = document.getElementById('modal-overlay');

    triggerModalHtml(modal, title, template);

    // Обработчик отправки формы
    const form = modal.querySelector('#addRowForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = {};

        // Преобразуем данные формы в объект
        formData.forEach((value, key) => {
            data[key] = value.trim();
        });

        // Отправляем запрос на сервер
        fetch(`/admin/settings/${settingId}/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                closeModal(modal, overlay)
                loadSettingsData(settingId); // Обновляем таблицу
            } else {
                alert(`Error: ${result.error.description}`);
            }
        })
        .catch(error => console.error('Error:', error));
    });
}

function addNewHostModal() {
    const tittle = getTranslate(`html.admin.settings.radius.add_title`);
    const template = `
        <form class="form form-modal" id="addRowForm">
            <label for="address">${getTranslate('html.admin.settings.radius.address')}</label>
            <input class="input modal-input" type="text" name="address" placeholder="${getTranslate('html.admin.settings.radius.address')}" required>
            <label for="name">${getTranslate('html.admin.settings.radius.name')}</label>
            <input class="input modal-input" type="text" name="name" placeholder="${getTranslate('html.admin.settings.radius.name')}" required>
            <label for="secret">${getTranslate('html.admin.settings.radius.secret')}</label>
            <input class="input modal-input" type="password" name="secret" placeholder="${getTranslate('html.admin.settings.radius.secret')}" required>
            <label for="authport">${getTranslate('html.admin.settings.radius.authport')}</label>
            <input class="input modal-input" type="text" name="authport" value="1812" placeholder="${getTranslate('html.admin.settings.radius.authport')}" required>
            <label for="acctport">${getTranslate('html.admin.settings.radius.acctport')}</label>
            <input class="input modal-input" type="text" name="acctport" value="1813" placeholder="${getTranslate('html.admin.settings.radius.acctport')}" required>
            <label for="coaport">${getTranslate('html.admin.settings.radius.coaport')}</label>
            <input class="input modal-input" type="text" name="coaport" value="3799" placeholder="${getTranslate('html.admin.settings.radius.coaport')}" required>

            <div class="modal-footer">
                <button type="submit" class="btn btn-controls btn-save">${getTranslate('buttons.save')}</button>
                <button type="button" class="btn btn-controls btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
            </div>
        </form>
    `
    showModal(tittle, template, 'radius', 'add');
}

function editHostModal(button) {
    const tittle = getTranslate(`html.admin.settings.radius.edit_title`);
    const row = button.closest('tr');
    const address = row.querySelector('td[data-address]').textContent;
    const hostName = row.querySelector('td[data-name]').textContent;
    const authPort = row.querySelector('td[data-authport]').textContent;
    const acctPort = row.querySelector('td[data-acctport]').textContent;
    const coaPort = row.querySelector('td[data-coaport]').textContent;

    const template = `
        <form class="form form-modal" id="addRowForm">
            <input type="hidden" name="host" value="${address}">
            <label for="address">${getTranslate('html.admin.settings.radius.address')}</label>
            <input class="input modal-input" type="text" name="address" placeholder="${getTranslate('html.admin.settings.radius.address')}" value="${address}" required>
            <label for="name">${getTranslate('html.admin.settings.radius.name')}</label>
            <input class="input modal-input" type="text" name="name" placeholder="${getTranslate('html.admin.settings.radius.name')}" value="${hostName}" required>
            <label for="secret">${getTranslate('html.admin.settings.radius.secret')}</label>
            <input class="input modal-input" type="password" name="secret" placeholder="${getTranslate('html.admin.settings.radius.secret')}">
            <label for="authport">${getTranslate('html.admin.settings.radius.authport')}</label>
            <input class="input modal-input" type="text" name="authport" placeholder="${getTranslate('html.admin.settings.radius.authport')}" value="${authPort}" required>
            <label for="acctport">${getTranslate('html.admin.settings.radius.acctport')}</label>
            <input class="input modal-input" type="text" name="acctport" placeholder="${getTranslate('html.admin.settings.radius.acctport')}" value="${acctPort}" required>
            <label for="coaport">${getTranslate('html.admin.settings.radius.coaport')}</label>
            <input class="input modal-input" type="text" name="coaport" placeholder="${getTranslate('html.admin.settings.radius.coaport')}" value="${coaPort}" required>

            <div class="modal-footer">
                <button type="submit" class="btn btn-controls btn-save">${getTranslate('buttons.save')}</button>
                <button type="button" class="btn btn-controls btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
            </div>
        </form>
    `
    showModal(tittle, template, 'radius', 'update');
}

function deleteHostRow(button) {
    const row = button.closest('tr');
    const address = row.querySelector('td[data-address]').textContent;

    const data = {
        host: address.trim()
    };

    // Отправляем запрос на сервер
    fetch(`/admin/settings/radius/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadSettingsData('radius'); // Обновляем таблицу
        } else {
            alert(`Error: ${result.error.description}`);
        }
    })
    .catch(error => console.error('Error:', error));
}

function addNewUserModal() {
    const tittle = getTranslate(`html.admin.settings.users.add_title`);
    const template = `
        <form class="form form-modal" id="addRowForm">
            <label for="username">${getTranslate('placeholders.login')}</label>
            <input class="input modal-input" type="text" name="username" placeholder="${getTranslate('placeholders.login')}" required>
            <label for="password">${getTranslate('placeholders.password')}</label>
            <input class="input modal-input" type="password" name="password" placeholder="${getTranslate('placeholders.password')}" required>
            <label for="password_confirm">${getTranslate('placeholders.password_confirm')}</label>
            <input class="input modal-input" type="password" name="password_confirm" placeholder="${getTranslate('placeholders.password_confirm')}" required>
            <label for="group">${getTranslate('html.admin.settings.users.group')}</label>
            <select class="input modal-input" name="group" required>
                <option value="">-- Выберите группу --</option>
                <option value="read">read</option>
                <option value="write">write</option>
                <option value="full">full</option>
            </select>

            <div class="modal-footer">
                <button type="submit" class="btn btn-controls btn-save">${getTranslate('buttons.save')}</button>
                <button type="button" class="btn btn-controls btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
            </div>
        </form>
    `
    showModal(tittle, template, 'users', 'add');
}

function editUserModal(button) {
    const row = button.closest('tr');
    const username = row.querySelector('td[data-username]').textContent;
    const group = row.querySelector('td[data-group]').textContent.trim();

    const template = `
        <form class="form form-modal" id="addRowForm">
            <input type="hidden" name="username" value="${username}">
            <label for="group">${getTranslate('html.admin.settings.users.group')}</label>
            <select class="input modal-input" name="group" required>
                <option value="read" ${group === 'read' ? 'selected' : ''}>read</option>
                <option value="write" ${group === 'write' ? 'selected' : ''}>write</option>
                <option value="full" ${group === 'full' ? 'selected' : ''}>full</option>
            </select>

            <div class="modal-footer">
                <button type="submit" class="btn btn-controls btn-save">${getTranslate('buttons.save')}</button>
                <button type="button" class="btn btn-controls btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
            </div>
        </form>
    `
    const tittle = getTranslate(`html.admin.settings.users.edit_title`, {'username': username});
    showModal(tittle, template, 'users', 'update');
}

function editUserPasswordModal(button) {
    const row = button.closest('tr');
    const username = row.querySelector('td[data-username]').textContent;

    const template = `
        <form class="form form-modal" id="addRowForm">
            <input type="hidden" name="username" value="${username}">
            <label for="confirm">${getTranslate('placeholders.confirm')}</label>
            <input class="input modal-input" type="password" name="confirm" placeholder="${getTranslate('placeholders.confirm')}" required>
            <label for="password">${getTranslate('placeholders.password_new')}</label>
            <input class="input modal-input" type="password" name="password" placeholder="${getTranslate('placeholders.password_new', {'username': username})}" required>
            <label for="password_confirm">${getTranslate('placeholders.password_confirm')}</label>
            <input class="input modal-input" type="password" name="password_confirm" placeholder="${getTranslate('placeholders.password_confirm')}" required>

            <div class="modal-footer">
                <button type="submit" class="btn btn-controls btn-save">${getTranslate('buttons.save')}</button>
                <button type="button" class="btn btn-controls btn-modal-close" data-close-button>${getTranslate('buttons.cancel')}</button>
            </div>
        </form>
    `
    const tittle = getTranslate(`html.admin.settings.users.edit_title`, {'username': username});
    showModal(tittle, template, 'users', 'change_password');
}

function deleteUserRow(button) {
    const row = button.closest('tr');
    const username = row.querySelector('td[data-username]').textContent;

    const data = {
        username: username.trim()
    };

    // Отправляем запрос на сервер
    fetch(`/admin/settings/users/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            loadSettingsData('users'); // Обновляем таблицу
        } else {
            alert(`Error: ${result.error.description}`);
        }
    })
    .catch(error => console.error('Error:', error));
}

let hideTimer = null;

document.addEventListener('DOMContentLoaded', function () {
    const statusEl = document.getElementById('status');
    
    if (statusEl) {
        statusEl.style.transition = 'opacity 0.6s ease';
        statusEl.style.opacity = '0';
    }
});

function showStatus(msg, ok) {
    const statusEl = document.getElementById('status');
    
    if (!statusEl) return;

    if (hideTimer) {
        clearTimeout(hideTimer);
        hideTimer = null;
    }

    statusEl.textContent = msg;
    statusEl.style.color = ok ? 'green' : 'crimson';
    statusEl.style.opacity = '1';

    hideTimer = setTimeout(() => {
        statusEl.style.opacity = '0';
    }, 5000); // 5 seconds
}

function toggleEnabled(item) {
    const id = item.dataset.id;
    const header = item.querySelector('.settings-item-header');
    const enabledCheckbox = item.querySelector('input[name="enabled_' + id + '"]');

    if (enabledCheckbox.checked) {
        header.classList.remove('settings-item-disabled');
    } else {
        header.classList.add('settings-item-disabled');
    }
}

function toggleAccordion(item) {
    const body = item.querySelector('.settings-item-body');

    const isOpen = body.style.height && body.style.height !== '0px';

    if (isOpen) {
        body.style.height = body.scrollHeight + 'px';
        requestAnimationFrame(() => {
            body.style.height = '0px';
        });
    } else {
        body.style.height = body.scrollHeight + 'px';

        body.addEventListener('transitionend', function handler() {
            body.style.height = 'auto';
            body.removeEventListener('transitionend', handler);
        });
    }
}