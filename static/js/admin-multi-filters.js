document.querySelectorAll('[data-multi-filter]').forEach((filter) => {
    const summary = filter.querySelector('[data-selection-summary]');
    const emptyLabel = summary.dataset.emptyLabel;
    const update = () => {
        const selected = [...filter.querySelectorAll('input[type="checkbox"]:checked')];
        summary.textContent = selected.length ? selected.map(input => input.closest('label').querySelector('span').textContent).join(', ') : emptyLabel;
        summary.title = summary.textContent;
    };
    filter.addEventListener('change', update);
    filter.addEventListener('toggle', () => {
        if (filter.open) {
            document.querySelectorAll('[data-multi-filter]').forEach((other) => {
                if (other !== filter) other.open = false;
            });
            filter.querySelector('[data-option-search]').focus();
        }
    });
    filter.querySelector('[data-option-search]').addEventListener('input', (event) => {
        const term = event.target.value.trim().toLocaleLowerCase();
        const rows = [...filter.querySelectorAll('[data-option-row]')];
        rows.forEach((row) => { row.hidden = !row.textContent.toLocaleLowerCase().includes(term); });
        filter.querySelector('[data-no-options]').hidden = rows.some((row) => !row.hidden);
    });
    filter.querySelector('[data-option-search]').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') event.preventDefault();
    });
    filter.querySelector('[data-clear-selection]').addEventListener('click', () => {
        filter.querySelectorAll('input[type="checkbox"]').forEach((input) => { input.checked = false; });
        update();
    });
    filter.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            filter.open = false;
            filter.querySelector('summary').focus();
        }
    });
});
document.addEventListener('click', (event) => {
    document.querySelectorAll('[data-multi-filter][open]').forEach((filter) => {
        if (!filter.contains(event.target)) filter.open = false;
    });
});

document.querySelectorAll('[data-remove-filter]').forEach((button) => {
    button.addEventListener('click', () => {
        const form = button.closest('form');
        form.querySelectorAll('input[type="checkbox"]').forEach((input) => {
            if (input.name === button.dataset.removeFilter && input.value === button.dataset.removeValue) input.checked = false;
        });
        form.requestSubmit();
    });
});
