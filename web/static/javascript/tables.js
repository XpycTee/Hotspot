const rowsPerPage = 15;
const tableData = {};
const activeFilters = {
    online: 'all',
    employee: 'all',
    date_from: null,
    date_to: null,
    location: null,
};

function hasTable(tableId) {
    return Boolean(document.getElementById(tableId));
}

function getCurrentPagePath() {
    return window.location.pathname;
}

function updatePageQuery(tableId) {
    const state = tableData[tableId];
    if (!state) {
        return;
    }

    const params = new URLSearchParams();
    if (state.currentPage > 1) {
        params.set('page', String(state.currentPage));
    }
    if (state.searchQuery) {
        params.set('search', state.searchQuery);
    }

    if (activeFilters.online && activeFilters.online !== 'all') {
        params.set('online', activeFilters.online);
    }
    if (activeFilters.employee && activeFilters.employee !== 'all') {
        params.set('employee', activeFilters.employee);
    }
    if (activeFilters.date_from) {
        params.set('date_from', activeFilters.date_from);
    }
    if (activeFilters.date_to) {
        params.set('date_to', activeFilters.date_to);
    }
    if (activeFilters.location) {
        params.set('location', activeFilters.location);
    }

    const query = params.toString();
    const nextUrl = query ? `${getCurrentPagePath()}?${query}` : getCurrentPagePath();
    window.history.replaceState({}, '', nextUrl);
}

function hydrateStateFromUrl(tableId) {
    const params = new URLSearchParams(window.location.search);
    const pageRaw = parseInt(params.get('page') || '1', 10);
    tableData[tableId].currentPage = Number.isNaN(pageRaw) ? 1 : Math.max(pageRaw, 1);
    tableData[tableId].searchQuery = params.get('search') || '';

    const searchInput = document.getElementById(`${tableId}_search`);
    if (searchInput) {
        searchInput.value = tableData[tableId].searchQuery;
    }

    activeFilters.online = params.get('online') || 'all';
    activeFilters.employee = params.get('employee') || 'all';
    activeFilters.date_from = params.get('date_from') || null;
    activeFilters.date_to = params.get('date_to') || null;
    activeFilters.location = params.get('location') || null;

    const dateStart = document.getElementById('wifi_clients_daterange_start');
    const dateStop = document.getElementById('wifi_clients_daterange_stop');
    const location = document.getElementById('wifi_clients_last_location');

    if (dateStart) {
        dateStart.value = activeFilters.date_from || '';
    }
    if (dateStop) {
        dateStop.value = activeFilters.date_to || '';
    }
    if (location) {
        location.value = activeFilters.location || 'all';
    }
}

function initPanelTable(tableId) {
    if (tableId !== 'wifi_clients' || !hasTable('wifi_clients')) {
        return;
    }

    tableData.wifi_clients = { currentPage: 1, searchQuery: '' };
    hydrateStateFromUrl('wifi_clients');
    setupSearch('wifi_clients');
    setupFilters();
    loadWifiData();
}

document.addEventListener('DOMContentLoaded', function () {
    if (window.__PANEL_TABLE__) {
        initPanelTable(window.__PANEL_TABLE__);
    }
});

function changePageTo(tableId, pageNumber) {
    if (!tableData[tableId]) {
        return;
    }

    tableData[tableId].currentPage = pageNumber;
    updatePageQuery(tableId);
    loadWifiData();
}

function loadWifiData() {
    const tableId = 'wifi_clients';
    if (!tableData[tableId] || !hasTable(tableId)) {
        return;
    }

    const { currentPage, searchQuery } = tableData[tableId];
    let url = '/admin/tables/wifi_clients';
    const urlQuery = [`page=${currentPage}`, `rows_per_page=${rowsPerPage}`];

    if (searchQuery.length >= 3) {
        urlQuery.push(`search=${encodeURIComponent(searchQuery)}`);
    }
    if (activeFilters.online && activeFilters.online !== 'all') {
        urlQuery.push(`online=${activeFilters.online}`);
    }
    if (activeFilters.employee && activeFilters.employee !== 'all') {
        urlQuery.push(`employee=${activeFilters.employee}`);
    }
    if (activeFilters.date_from) {
        urlQuery.push(`date_from=${activeFilters.date_from}`);
    }
    if (activeFilters.date_to) {
        urlQuery.push(`date_to=${activeFilters.date_to}`);
    }
    if (activeFilters.location) {
        urlQuery.push(`location=${encodeURIComponent(activeFilters.location)}`);
    }

    if (urlQuery.length > 0) {
        url += `?${urlQuery.join('&')}`;
    }

    updatePageQuery(tableId);

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

function updateFoundCounter(tableId, totalRows) {
    const pageBody = document.getElementById(tableId);
    if (!pageBody) {
        return;
    }

    const foundCounterSpan = pageBody.querySelector('.found-count');
    if (!foundCounterSpan) {
        return;
    }

    foundCounterSpan.innerHTML = getTranslate('html.admin.panel.found_counter', { count: totalRows });
}

function updateTable(tableId, rows) {
    const tableBody = document.getElementById(`${tableId}_body`);
    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = '';

    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = generateRowHTML(row);
        tableBody.appendChild(tr);
    });
}

function generateRowHTML(row) {
    const formattedExpiration = new Date(row.expiration).toLocaleDateString(userLanguage, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    });
    const canManageWifiActions = window.__CAN_MANAGE_WIFI_ACTIONS__ === true;
    const controlsCell = canManageWifiActions ? `
        <td class="column-controls">
            <button class="btn btn-edit btn-controls" onclick="deauthRow(this)">${getTranslate('buttons.deauth')}</button>
            <button class="btn btn-delete btn-controls" onclick="blockRow(this)">${getTranslate('buttons.block')}</button>
        </td>
    ` : '';

    return `
        <td>${row.mac}</td>
        <td>${formattedExpiration}</td>
        <td>${row.employee ? `${row.employee.lastname} ${row.employee.name}` : getTranslate('buttons.no')}</td>
        <td>+${row.phone}</td>
        <td>${row.online ? getTranslate('buttons.yes') : getTranslate('buttons.no')}</td>
        <td>${row.last_location}</td>
        <td>${row.last_ipv4_address}</td>
        ${controlsCell}
    `;
}

function updatePagination(tableId, currentPage, totalPages) {
    const pagination = document.querySelector(`#${tableId} .pagination`);
    if (!pagination) {
        return;
    }

    const paginationContainer = pagination.querySelector('.page_numbers');
    const prevButton = pagination.querySelector('.btn-prev');
    const nextButton = pagination.querySelector('.btn-next');
    const pageInfo = pagination.querySelector('.page_info');

    pageInfo.textContent = getTranslate('html.admin.panel.page_counter', {
        current_page: currentPage,
        total_pages: totalPages,
    });

    if (totalPages <= 1) {
        pagination.style.display = 'none';
        return;
    }

    pagination.style.display = '';
    paginationContainer.innerHTML = '';

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

    prevButton.style.visibility = currentPage === 1 ? 'hidden' : '';
    nextButton.style.visibility = currentPage === totalPages ? 'hidden' : '';

    if (currentPage > 3) {
        paginationContainer.appendChild(createPageButton(1));
        if (currentPage > 4) {
            const dots = document.createElement('span');
            dots.textContent = '...';
            paginationContainer.appendChild(dots);
        }
    }

    for (let page = Math.max(1, currentPage - 2); page <= Math.min(totalPages, currentPage + 4); page += 1) {
        paginationContainer.appendChild(createPageButton(page));
    }

    if (currentPage < totalPages - 3) {
        if (currentPage < totalPages - 4) {
            const dots = document.createElement('span');
            dots.textContent = '...';
            paginationContainer.appendChild(dots);
        }
        paginationContainer.appendChild(createPageButton(totalPages));
    }
}

function changePage(tableId, direction) {
    if (!tableData[tableId]) {
        return;
    }

    const newPage = tableData[tableId].currentPage + direction;
    if (newPage < 1) {
        return;
    }

    tableData[tableId].currentPage = newPage;
    updatePageQuery(tableId);
    loadWifiData();
}

function setupSearch(tableId) {
    const searchInput = document.getElementById(`${tableId}_search`);
    if (!searchInput) {
        return;
    }

    searchInput.addEventListener('input', () => {
        tableData[tableId].searchQuery = searchInput.value;
        tableData[tableId].currentPage = 1;
        updatePageQuery(tableId);
        loadWifiData();
    });
}

function deauthRow(button) {
    const row = button.closest('tr');
    const macAddress = row.querySelector('td:first-child').textContent.trim();

    if (!macAddress) {
        const modal = document.querySelector('#errorModal');
        triggerModal(modal, 'Error', getTranslate('errors.admin.tables.mac_is_missing'));
        return;
    }

    fetch('/admin/hotspot/deauth', {
        method: 'POST',
        headers: adminJsonHeaders(),
        body: JSON.stringify({ mac: macAddress }),
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                loadWifiData();
                return;
            }

            const modal = document.querySelector('#errorModal');
            triggerModal(
                modal,
                getTranslate('errors.admin.modals.deauth'),
                getTranslate('errors.admin.modals.header') + result.error.description
            );
        })
        .catch(error => console.error('Error:', error));
}

function blockRow(button) {
    const row = button.closest('tr');
    const macAddress = row.querySelector('td:first-child').textContent.trim();

    if (!macAddress) {
        const modal = document.querySelector('#errorModal');
        triggerModal(modal, 'Error', getTranslate('errors.admin.tables.mac_is_missing'));
        return;
    }

    fetch('/admin/hotspot/block', {
        method: 'POST',
        headers: adminJsonHeaders(),
        body: JSON.stringify({ mac: macAddress }),
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                loadWifiData();
                return;
            }

            const modal = document.querySelector('#errorModal');
            triggerModal(
                modal,
                getTranslate('errors.admin.modals.block'),
                getTranslate('errors.admin.modals.header') + result.error.description
            );
        })
        .catch(error => console.error('Error:', error));
}

function setupFilters() {
    if (!hasTable('wifi_clients')) {
        return;
    }

    document.querySelectorAll('.select-toggle').forEach(toggle => {
        const target = toggle.dataset.target;

        toggle.querySelectorAll('.select-option').forEach(opt => {
            opt.addEventListener('click', () => {
                activeFilters[target] = opt.dataset.value;
                reloadWifiTable();
            });
        });
    });

    const locationSelect = document.querySelector('.filter-select');
    if (locationSelect) {
        locationSelect.addEventListener('change', () => {
            activeFilters.location = locationSelect.value === 'all' ? null : locationSelect.value;
            reloadWifiTable();
        });
    }

    const dateInputStart = document.getElementById('wifi_clients_daterange_start');
    const dateInputStop = document.getElementById('wifi_clients_daterange_stop');
    if (dateInputStart && dateInputStop) {
        dateInputStart.addEventListener('change', () => {
            activeFilters.date_from = dateInputStart.value || null;
            reloadWifiTable();
        });
        dateInputStop.addEventListener('change', () => {
            activeFilters.date_to = dateInputStop.value || null;
            reloadWifiTable();
        });
    }
}

function reloadWifiTable() {
    if (!tableData.wifi_clients) {
        return;
    }

    tableData.wifi_clients.currentPage = 1;
    updatePageQuery('wifi_clients');
    loadWifiData();
}
