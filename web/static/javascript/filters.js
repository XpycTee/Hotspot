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