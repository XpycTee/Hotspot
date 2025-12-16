document.querySelectorAll('.tri-toggle').forEach(toggle => {
    const options = Array.from(toggle.querySelectorAll('.tri-option'));

    options.forEach((opt, index) => {
        opt.addEventListener('click', e => {
            e.stopPropagation();
            const state = index + 1;
            toggle.setAttribute('data-state', state);
            const val = opt.dataset.value;
            console.log(toggle.dataset.target + ' = ' + val);
        });
    });
});

// Toggle filters visibility
const toggleBtn = document.querySelector('.filters-toggle-btn');
const filtersBody = document.querySelector('.filters-body');

if (toggleBtn && filtersBody) {
    toggleBtn.addEventListener('click', () => {
        const expanded = toggleBtn.getAttribute('aria-expanded') === 'true';
        toggleBtn.setAttribute('aria-expanded', String(!expanded));
        toggleBtn.textContent = !expanded ? getTranslate('html.admin.buttons.filters_close') : getTranslate('html.admin.buttons.filters_open');
        filtersBody.hidden = expanded;
    });
}