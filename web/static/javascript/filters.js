document.querySelectorAll('.tri-toggle').forEach(toggle => {
    const options = Array.from(toggle.querySelectorAll('.tri-option'));
    const slider = toggle.querySelector('.tri-slider');
    const n = options.length || 1;

    // set slider width based on number of options
    if (slider) {
        slider.style.width = `calc((100% - 8px) / ${n})`;
    }

    // helper to set visual state and optional target input
    const setState = (index) => {
        const state = index + 1;
        toggle.setAttribute('data-state', state);
        if (slider) {
            slider.style.left = `calc((100% - 8px) * ${index} / ${n} + 4px)`;
        }
        const opt = options[index];
        if (opt) {
            const val = opt.dataset.value;
            const target = toggle.dataset.target;
            if (target) {
                // prefer element with id=target, fallback to input[name=target]
                const hidden = document.getElementById(target) || document.querySelector(`input[name="${target}"]`);
                if (hidden) hidden.value = val;
                if (hidden) hidden.dispatchEvent(new Event('input', { bubbles: true }));
            }
            console.log((toggle.dataset.target || '(no-target)') + ' = ' + val);
        }
    };

    // expose a control method to allow external code to set state programmatically
    toggle._setState = setState;

    // initialize from existing data-state attribute (1-based)
    const initialState = parseInt(toggle.getAttribute('data-state') || '1', 10) - 1;
    const initIndex = Math.max(0, Math.min(n - 1, isNaN(initialState) ? 0 : initialState));
    setState(initIndex);

    // attach click handlers
    options.forEach((opt, index) => {
        opt.addEventListener('click', e => {
            e.stopPropagation();
            setState(index);
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
        toggleBtn.textContent = !expanded ? getTranslate('buttons.filters_close') : getTranslate('buttons.filters_open');
        filtersBody.hidden = expanded;
    });
}