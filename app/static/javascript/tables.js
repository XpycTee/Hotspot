// Общая функция для добавления строки в таблицу
function addRow(button, type) {
    const tableBody = button.closest('table').querySelector('tbody');
    const addButtonRow = button.closest('tr');
    const newRow = document.createElement('tr');

    if (type === 'employee') {
        newRow.innerHTML = `
            <td data-lastname><input type="text" name="lastname" placeholder="Lastname"></td>
            <td data-name><input type="text" name="name" placeholder="Name"></td>
            <td data-phones>
                <ul>
                    <li><input type="text" name="phones" placeholder="Phone"></li>
                </ul>
                <button type="button" class="btn btn-add-phone" onclick="addPhoneField(this)">+ phone</button>
            </td>
            <td class="column-controls">
                <button class="btn btn-save btn-controls" onclick="saveRow(this, 'employee')">Save</button>
                <button class="btn btn-delete btn-controls" onclick="deleteRow(this, 'employee')">Delete</button>
            </td>
        `;
    } else if (type === 'blacklist') {
        newRow.innerHTML = `
            <td><input type="text" name="phone" placeholder="Phone"></td>
            <td class="column-controls">
                <button class="btn btn-save btn-controls" onclick="saveRow(this, 'blacklist')">Save</button>
                <button class="btn btn-delete btn-controls" onclick="deleteRow(this, 'blacklist')">Delete</button>
            </td>
        `;
    }

    tableBody.insertBefore(newRow, addButtonRow);
}

function addPhoneField(button) {
    const ul = button.previousElementSibling;

    // Создаём новый элемент списка с полем ввода
    const li = document.createElement('li');
    const newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.name = 'phones';
    newInput.placeholder = 'Phone';

    // Создаём кнопку удаления
    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.classList = 'btn btn-delete btn-controls'
    deleteButton.textContent = 'x';
    deleteButton.onclick = () => {
        li.remove();
        // Найдите input с именем phones-count и уменьшите его значение на 1
        const phonesCountInput = button.parentElement.querySelector('input[name="phones-count"]');
        if (phonesCountInput) {
            phonesCountInput.value = Math.max(0, parseInt(phonesCountInput.value, 10) - 1);
        }
    };

    li.appendChild(newInput);
    li.appendChild(deleteButton);
    ul.appendChild(li);

    // Найдите input с именем phones-count и увеличьте его значение на 1
    const phonesCountInput = button.parentElement.querySelector('input[name="phones-count"]');
    if (phonesCountInput) {
        phonesCountInput.value = parseInt(phonesCountInput.value, 10) + 1;
    }
}

function convertInputsToCells(inputs, data, type, row, button) {
    inputs.forEach(input => {
        if (input.type !== 'hidden') {
            const td = input.closest('td');
            if (td) {
                if (input.name === 'phones') {
                    const ul = document.createElement('ul');
                    data['phones'].forEach(phone => {
                        const li = document.createElement('li');
                        li.textContent = phone;
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
    button.remove();
    const controlsTd = row.querySelector('.column-controls');
    if (type === 'employee') {
        if (controlsTd) {
            const editButton = document.createElement('button');
            editButton.className = 'btn btn-edit btn-controls';
            editButton.textContent = 'Edit';
            editButton.onclick = () => editRow(editButton, type);
            controlsTd.insertBefore(editButton, controlsTd.firstChild);
        }
    }
}

// Общая функция для сохранения строки
function saveRow(button, type) {
    const row = button.closest('tr');
    const inputs = row.querySelectorAll('input');
    const data = {};
    let hasChanges = false;
    let hasEmptyFields = false;

    // Проверка на пустые поля
    inputs.forEach(input => {
        const currentValue = input.value.trim();
        if (!currentValue) {
            hasEmptyFields = true;
        }
    });

    if (hasEmptyFields) {
        alert('All fields must be filled');
        return;
    }

    inputs.forEach(input => {
        const key = input.getAttribute('name');
        const currentValue = input.value.trim();

        // Проверка на изменения
        const originalValue = input.dataset.originalValue || '';
        if (currentValue !== originalValue) {
            hasChanges = true;
        }

        if (key === 'phones') {
            data[key] = data[key] || [];
            data[key].push(currentValue);
        } else {
            if (input.type !== 'hidden') {
                data[key] = currentValue;
            }
        }
    });

    // Если изменений нет, не отправляем запрос
    if (!hasChanges) {
        convertInputsToCells(inputs, data, type, row, button);
        return;
    }

    const url = `/admin/save/${type}`;

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            convertInputsToCells(inputs, data, type, row, button);
        } else {
            alert('Error saving data');
        }
    })
    .catch(error => console.error('Error:', error));
}

// Общая функция для редактирования строки
function editRow(button, type) {
    const row = button.closest('tr');
    const cells = row.querySelectorAll('td');

    cells.forEach(cell => {
        if (cell.hasAttribute('data-lastname') || cell.hasAttribute('data-name')) {
            const text = cell.textContent.trim();
            const input = document.createElement('input');
            input.type = 'text';
            input.value = text;
            input.name = cell.hasAttribute('data-lastname') ? 'lastname' : 'name';
            input.setAttribute('data-original-value', text);
            cell.innerHTML = '';
            cell.appendChild(input);
        } else if (cell.hasAttribute('data-phones')) {
            // Извлекаем текущие значения телефонов из списка
            const ul = cell.querySelector('ul');
            const phones = Array.from(ul.querySelectorAll('li')).map(li => li.textContent.trim());

            // Очищаем списка
            ul.innerHTML = '';

            // Создаем невидимый инпут с атрибутом data-original-phones-count
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'phones-count';
            hiddenInput.value = phones.length;
            hiddenInput.setAttribute('data-original-value', phones.length);
            ul.appendChild(hiddenInput);

            // Добавляем в список элементы с полями ввода
            phones.forEach(phone => {
                const li = document.createElement('li');
                const input = document.createElement('input');
                input.type = 'text';
                input.name = 'phones';
                input.value = phone;
                input.setAttribute('data-original-value', phone);

                // Создаём кнопку удаления
                const deleteButton = document.createElement('button');
                deleteButton.type = 'button';
                deleteButton.textContent = 'x';
                deleteButton.classList = 'btn btn-delete btn-controls'
                deleteButton.onclick = () => {
                    li.remove();
                    // Найдите input с именем phones-count и уменьшите его значение на 1
                    const phonesCountInput = ul.querySelector('input[name="phones-count"]');
                    if (phonesCountInput) {
                        phonesCountInput.value = Math.max(0, parseInt(phonesCountInput.value, 10) - 1);
                    }
                };
                li.appendChild(input);
                li.appendChild(deleteButton);
                ul.appendChild(li);
            });

            const addPhoneButton = document.createElement('button');
            addPhoneButton.type = 'button';
            addPhoneButton.className = 'btn btn-add-phone';
            addPhoneButton.textContent = '+ phone';
            addPhoneButton.onclick = () => addPhoneField(addPhoneButton);
            cell.appendChild(addPhoneButton);
        }
    });

    const controlsTd = row.querySelector('.column-controls');
    if (controlsTd) {
        controlsTd.innerHTML = '';
        const saveButton = document.createElement('button');
        saveButton.className = 'btn btn-save btn-controls';
        saveButton.textContent = 'Save';
        saveButton.onclick = () => saveRow(saveButton, type);
        controlsTd.appendChild(saveButton);

        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-delete btn-controls';
        deleteButton.textContent = 'Delete';
        deleteButton.onclick = () => deleteRow(deleteButton, type);
        controlsTd.appendChild(deleteButton);
    }
}

// Общая функция для удаления строки
function deleteRow(button, type) {
    const row = button.closest('tr');
    const data = {};
    const url = `/admin/delete/${type}`;

    if (type === 'employee') {
        data['lastname'] = row.querySelector('td[data-lastname]').textContent.trim();
        data['name'] = row.querySelector('td[data-name]').textContent.trim();
    } else if (type === 'blacklist') {
        data['phone'] = row.querySelector('td').textContent.trim();
    }

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            row.remove();
        } else {
            alert('Error deleting data');
        }
    })
    .catch(error => console.error('Error:', error));
}