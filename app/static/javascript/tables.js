// Функция для добавления строки в таблицу
function addRow(button, type) {
    const tableBody = button.closest('table').querySelector('tbody');
    const addButtonRow = button.closest('tr');
    const newRow = document.createElement('tr');
    newRow.dataset.new = "true";

    const templates = {
        employee: `
            <td data-id><input type="hidden" name="id" value="#">#</td>
            <td data-lastname><input class="table-input" type="text" name="lastname" placeholder="Lastname"></td>
            <td data-name><input class="table-input" type="text" name="name" placeholder="Name"></td>
            <td data-phones>
                <ul>
                    <li><input class="table-input" type="tel" name="phone" data-tel-input placeholder="Phone"></li>
                </ul>
                <button type="button" class="btn btn-add-phone">+ phone</button>
            </td>
            <td class="column-controls">
                <button class="btn btn-save btn-controls">Save</button>
                <button class="btn btn-delete btn-controls">Delete</button>
            </td>
        `,
        blacklist: `
            <td><input class="table-input" type="tel" data-tel-input name="phone" placeholder="Phone"></td>
            <td class="column-controls">
                <button class="btn btn-save btn-controls">Save</button>
                <button class="btn btn-delete btn-controls">Delete</button>
            </td>
        `
    };

    newRow.innerHTML = templates[type] || '';
    tableBody.insertBefore(newRow, addButtonRow);

    // Добавляем обработчики событий после вставки строки
    const phoneInputs = newRow.querySelectorAll('input[data-tel-input]');
    for (var phoneInput of phoneInputs) {
        detectPhoneInput(phoneInput)
    }

    addEventListeners(newRow, type);
}

// Функция для добавления обработчиков событий
function addEventListeners(row, type) {
    const addPhoneButton = row.querySelector('.btn-add-phone');
    const saveButton = row.querySelector('.btn-save');
    const deleteButton = row.querySelector('.btn-delete');

    if (addPhoneButton) {
        addPhoneButton.addEventListener('click', () => addPhoneField(addPhoneButton));
    }
    if (saveButton) {
        saveButton.addEventListener('click', () => saveRow(saveButton, type));
    }
    if (deleteButton) {
        deleteButton.addEventListener('click', () => deleteRow(deleteButton, type));
    }
}

// Функция для удаления строки
function deleteRow(button, type) {
    const row = button.closest('tr');

    if (row.dataset.new === "true") {
        row.remove();
        return;
    }

    const data = collectRowData(row, type, false);

    fetch(`/admin/delete/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            row.remove();
        } else {
            alert('Error saving data\nError message:\n'+result.error);
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
        alert('All fields must be filled');
        return;
    }

    inputs.forEach(input => {
        const key = input.getAttribute('name');
        const currentValue = input.value.trim();
        const originalValue = input.dataset.originalValue || '';

        if (currentValue !== originalValue) {
            hasChanges = true;
        }

        if (key === 'phone' && type !== 'blacklist') {
            data[key] = data[key] || [];
            data[key].push(currentValue);
        } else {
            data[key] = input.name === 'id' ? Number(currentValue) : currentValue;
        }
    });

    if (!hasChanges) {
        convertInputsToCells(inputs, data, type, row, button);
        delete row.dataset.new;
        return;
    }

    fetch(`/admin/save/${type}`, {
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
            alert('Error saving data\nError message:\n'+result.error);
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
        } else if (cell.hasAttribute('data-phones')) {
            editPhoneList(cell);
        }
    });

    updateControlButtons(row, type);
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
    addPhoneButton.textContent = '+ phone';
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

// Функция для добавления поля телефона
function addPhoneField(button) {
    const ul = button.previousElementSibling;
    const li = document.createElement('li');
    const newInput = document.createElement('input');
    newInput.type = 'tel';
    newInput.name = 'phone';
    newInput.placeholder = 'Phone';
    newInput.classList = 'table-input';
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
    if (type === 'employee') {
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
    
        const controlsTd = row.querySelector('.column-controls');
        if (controlsTd) {
            const editButton = document.createElement('button');
            editButton.className = 'btn btn-edit btn-controls';
            editButton.textContent = 'Edit';
            editButton.onclick = () => editRow(editButton, type);
            controlsTd.insertBefore(editButton, controlsTd.firstChild);
        }
    } else if (type === 'blacklist') {
        inputs.forEach(input => {
            if (input.type !== 'hidden') {
                const td = input.closest('td');
                if (td) {
                    td.textContent = input.value;
                }
            }
        });
    }
    
    button.remove();
}

// Функция для сбора данных строки
function collectRowData(row, type, isEditing) {
    const data = {};
    const inputs = row.querySelectorAll('input');

    if (inputs.length > 0) {
        inputs.forEach(input => {
            const key = input.getAttribute('name');
            const originalValue = input.dataset.originalValue || '';
            if (key === 'phone' && type !== 'blacklist') {
                data[key] = data[key] || [];
                data[key].push(originalValue);
            } else {
                data[key] = originalValue;
            }
        });
    } else {
        if (type === 'employee') {
            data['lastname'] = row.querySelector('td[data-lastname]').textContent.trim();
            data['name'] = row.querySelector('td[data-name]').textContent.trim();
        } else if (type === 'blacklist') {
            data['phone'] = row.querySelector('td').textContent.trim();
        }
    }

    return data;
}