document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-filter-form]');
    if (!form) return;
    const groups = [...form.querySelectorAll('.catalog-filter-group')];
    const updateCounts = () => groups.forEach(group => {
        const count = group.querySelectorAll('input:checked').length + [...group.querySelectorAll('[data-price-number]')].filter(input => input.value !== '').length;
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
    form.addEventListener('input', updateCounts);
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

// Numeric fields submit the price bounds; sliders are an optional editing aid.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-filter-form]');
    if (!form) return;
    const minimum = form.querySelector('[data-price-number="min"]');
    const maximum = form.querySelector('[data-price-number="max"]');
    if (!minimum || !maximum) return;
    const rail = form.querySelector('.price-range-sliders');
    const sliders = [...form.querySelectorAll('[data-price-range]')];
    const paintRange = () => {
        const [lower, upper] = sliders;
        const ceiling = Math.max(...sliders.map(slider => Number(slider.max)));
        sliders.forEach(slider => { slider.max = ceiling; });
        rail.style.setProperty('--range-start', `${Number(lower.value) / ceiling * 100}%`);
        rail.style.setProperty('--range-end', `${Number(upper.value) / ceiling * 100}%`);
        // Keep either thumb reachable when the handles meet at an endpoint.
        lower.style.zIndex = Number(lower.value) === ceiling ? '2' : '1';
    };
    form.querySelector('[data-price-clear]').addEventListener('click', () => {
        minimum.value = '';
        maximum.value = '';
        form.requestSubmit();
    });
    form.querySelectorAll('[data-price-range]').forEach(slider => {
        const input = form.querySelector(`[data-price-number="${slider.dataset.priceRange}"]`);
        slider.addEventListener('input', () => {
            input.value = slider.value;
            if (minimum.value && maximum.value && Number(minimum.value) > Number(maximum.value)) {
                const other = input === minimum ? maximum : minimum;
                other.value = input.value;
                form.querySelector(`[data-price-range="${other.dataset.priceNumber}"]`).value = input.value;
            }
            input.dispatchEvent(new Event('input', { bubbles: true }));
            paintRange();
        });
        input.addEventListener('input', () => {
            if (input.value !== '') slider.max = Math.max(Number(slider.max), Number(input.value));
            slider.value = input.value || (slider.dataset.priceRange === 'min' ? slider.min : slider.max);
            paintRange();
        });
    });
    paintRange();
});
