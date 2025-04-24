document.addEventListener('DOMContentLoaded', function() {
    const openModalButtons = document.querySelectorAll('[data-modal-target]');
    const closeModalButtons = document.querySelectorAll('[data-close-button]');
    const overlay = document.getElementById('modal-overlay');

    openModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = document.querySelector(button.dataset.modalTarget);
            openModal(modal, overlay);
        });
    });

    closeModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.modal');
            closeModal(modal, overlay);
        });
    });

    overlay.addEventListener('click', () => {
        const modals = document.querySelectorAll('.modal.active');
        modals.forEach(modal => {
            closeModal(modal, overlay);
        });
    });

    function openModal(modal) {
        if (modal == null) return;
        modal.classList.add('active');
        overlay.style.display = 'flex';
    }
});


function closeModal(modal, overlay) {
    if (modal == null) return;
    modal.classList.remove('active');
    overlay.style.display = 'none';
}


function triggerModal(modal, title, content) {
    if (modal == null) return;
    modal.classList.add('active');
    const overlay = document.getElementById('modal-overlay');
    overlay.style.display = 'flex';
    // Найдите элемент с классом .modal-title и установите его textContent
    const modalTitle = modal.querySelector('.modal-title');
    if (modalTitle) {
        modalTitle.textContent = title;
    }

    // Найдите элемент с классом .modal-content и установите его textContent
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.textContent = content;
    }
}

function triggerModalHtml(modal, title, content) {
    if (modal == null) return;
    modal.classList.add('active');
    const overlay = document.getElementById('modal-overlay');
    overlay.style.display = 'flex';
    // Найдите элемент с классом .modal-title и установите его textContent
    const modalTitle = modal.querySelector('.modal-title');
    if (modalTitle) {
        modalTitle.textContent = title;
    }

    // Найдите элемент с классом .modal-content и установите его textContent
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.innerHTML = content;
    }

    const closeModalButtons = modalContent.querySelectorAll('[data-close-button]');
    closeModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.modal');
            closeModal(modal, overlay);
        });
    });
}