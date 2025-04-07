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
                <div class="phones-container">
                    <input type="text" name="phones" placeholder="Phone">
                </div>
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
    const container = button.previousElementSibling;
    const newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.name = 'phones';
    newInput.placeholder = 'Phone';
    container.appendChild(newInput);
}

// Общая функция для сохранения строки
function saveRow(button, type) {
    const row = button.closest('tr');
    const inputs = row.querySelectorAll('input');
    const data = {};

    inputs.forEach(input => {
        const key = input.getAttribute('name');
        if (key === 'phones') {
            data[key] = data[key] || [];
            data[key].push(input.value);
        } else {
            data[key] = input.value;
        }
    });

    const url = `/admin/save/${type}`;

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            inputs.forEach(input => {
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
            cell.innerHTML = '';
            cell.appendChild(input);
        } else if (cell.hasAttribute('data-phones')) {
            const ul = cell.querySelector('ul');
            const phones = Array.from(ul.querySelectorAll('li')).map(li => li.textContent.trim());
            cell.innerHTML = '<div class="phones-container"></div>';
            const container = cell.querySelector('.phones-container');
            phones.forEach(phone => {
                const input = document.createElement('input');
                input.type = 'text';
                input.name = 'phones';
                input.value = phone;
                container.appendChild(input);
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