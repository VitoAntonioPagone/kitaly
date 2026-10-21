document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-filter-form]');
    if (!form) return;
    const groups = [...form.querySelectorAll('.catalog-filter-group')];
    const updateCounts = () => groups.forEach(group => {
        const count = group.querySelectorAll('input:checked').length;
        group.toggleAttribute('data-selected', count > 0);
        const summaryLabel = group.querySelector('summary > span');
        if (summaryLabel) summaryLabel.dataset.count = String(count);
    });
    groups.forEach(group => {
        group.addEventListener('toggle', () => {
            if (!group.open) return;
            groups.forEach(other => { if (other !== group) other.open = false; });
            const panel = group.querySelector(':scope > div');
            panel.style.left = '0';
            panel.style.right = 'auto';
            if (panel.getBoundingClientRect().right > window.innerWidth - 16) {
                panel.style.left = 'auto';
                panel.style.right = '0';
            }
        });
    });
    form.addEventListener('click', updateCounts);
    form.addEventListener('change', updateCounts);
    document.addEventListener('click', event => groups.forEach(group => {
        if (!group.contains(event.target)) group.open = false;
    }));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') groups.forEach(group => {
            if (group.open) { group.open = false; group.querySelector('summary').focus(); }
        });
    });
    updateCounts();
});
