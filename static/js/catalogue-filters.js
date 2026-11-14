document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-filter-form]');
    const drawer = document.getElementById('catalog-filters-panel');
    if (!form || !drawer) return;
    const triggers = [document.getElementById('catalog-filters-toggle'), document.getElementById('header-filters')].filter(Boolean);
    const closeButton = drawer.querySelector('[data-close-filters]');
    const apply = form.querySelector('[data-apply-filters]');
    const total = form.querySelector('[data-filter-result-count]');
    const reset = form.querySelector('[data-reset-filters]');
    const groups = [...form.querySelectorAll('details.catalog-filter-group')];
    const controls = [...form.querySelectorAll('input[name]')].filter(input => input.type !== 'hidden' || input.hasAttribute('data-price-number'));
    const leagueInputs = controls.filter(input => input.name === 'campionato');
    const teamOptions = [...form.querySelectorAll('[data-team-leagues]')].map(button => ({
        button,
        input: document.getElementById(button.dataset.filterTarget),
        leagues: JSON.parse(button.dataset.teamLeagues),
    }));
    const noTeams = form.querySelector('[data-no-teams]');
    const italian = document.documentElement.lang === 'it';
    let opener = null;
    let timer = null;
    let controller = null;
    let revision = 0;

    function close() {
        drawer.hidden = true;
        groups.forEach(group => { group.open = false; });
        triggers.forEach(button => button.setAttribute('aria-expanded', 'false'));
        opener?.focus({preventScroll: true});
    }
    function open(trigger) {
        if (!drawer.hidden) { close(); return; }
        opener = trigger;
        drawer.hidden = false;
        triggers.forEach(button => button.setAttribute('aria-expanded', 'true'));
        if (trigger.id === 'header-filters') {
            const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            document.getElementById('catalogue-toolbar').scrollIntoView({behavior: reduceMotion ? 'instant' : 'smooth'});
            closeButton?.focus({preventScroll: true});
        }
    }
    triggers.forEach(button => button.addEventListener('click', () => open(button)));
    closeButton.addEventListener('click', () => close());
    document.addEventListener('click', event => {
        groups.forEach(group => {
            if (group.open && !group.contains(event.target)) {
                group.open = false;
            }
        });
    });
    drawer.addEventListener('keydown', event => {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        const group = event.target.closest('details.catalog-filter-group[open]');
        if (!group) { close(); return; }
        group.open = false;
        group.querySelector('summary').focus();
    });
    groups.forEach(group => group.addEventListener('toggle', () => {
        if (group.open) groups.forEach(other => { if (other !== group) other.open = false; });
    }));

    function syncTeams(clearUnavailable = false) {
        const leagues = leagueInputs.filter(input => input.checked).map(input => input.value);
        teamOptions.forEach(({button, input, leagues: teamLeagues}) => {
            button.hidden = leagues.length > 0 && !leagues.some(league => teamLeagues.includes(league));
            if (button.hidden && clearUnavailable) input.checked = false;
        });
        noTeams.hidden = teamOptions.some(({button}) => !button.hidden);
    }

    function sync() {
        form.querySelectorAll('[data-filter-toggle]').forEach(button => {
            const input = document.getElementById(button.dataset.filterTarget);
            button.setAttribute('aria-pressed', String(input.checked));
        });
        groups.forEach(group => {
            const selected = [...group.querySelectorAll('input:checked')].map(input => {
                const button = form.querySelector(`[data-filter-target="${input.id}"]`);
                return button ? button.textContent.trim() : input.value;
            });
            const label = group.querySelector('summary > span');
            let description = label.querySelector('.stock-filter-selection');
            if (!description) {
                description = document.createElement('small');
                description.className = 'stock-filter-selection';
                label.append(description);
            }
            description.textContent = selected.length ? selected.join(', ') : (italian ? 'Tutti' : 'All');
            group.toggleAttribute('data-selected', selected.length > 0);
        });
        reset.disabled = !controls.some(input => input.type === 'checkbox' ? input.checked : input.value.trim());
    }

    function preview() {
        sync();
        clearTimeout(timer);
        controller?.abort();
        const current = ++revision;
        total.textContent = '…';
        timer = setTimeout(async () => {
            controller = new AbortController();
            const query = new URLSearchParams(new FormData(form));
            try {
                const response = await fetch(`${form.action}?${query}`, {
                    headers: {'X-Kitaly-Filter-Preview': '1'}, signal: controller.signal,
                });
                if (!response.ok) throw new Error('Preview unavailable');
                const data = await response.json();
                if (current === revision) total.textContent = String(data.total);
            } catch (error) {
                if (current === revision && error.name !== 'AbortError') total.textContent = '';
            }
        }, 180);
    }
    form.querySelectorAll('[data-filter-toggle]').forEach(button => button.addEventListener('click', () => {
        const input = document.getElementById(button.dataset.filterTarget);
        input.checked = !input.checked;
        input.dispatchEvent(new Event('change', {bubbles: true}));
    }));
    form.addEventListener('input', preview);
    form.addEventListener('change', event => {
        if (event.target.name === 'campionato') syncTeams(true);
        preview();
    });
    reset.addEventListener('click', () => {
        controls.forEach(input => { if (input.type === 'checkbox') input.checked = false; else input.value = ''; });
        syncTeams();
        syncRange();
        preview();
    });
    const minimum = form.querySelector('[data-price-number="min"]');
    const maximum = form.querySelector('[data-price-number="max"]');
    const sliders = [...form.querySelectorAll('[data-price-range]')];
    const rail = form.querySelector('.price-range-sliders');
    function syncRange() {
        const ceiling = Math.max(...sliders.map(slider => Number(slider.max)), Number(minimum.value), Number(maximum.value));
        sliders.forEach(slider => {
            slider.max = ceiling;
            const input = slider.dataset.priceRange === 'min' ? minimum : maximum;
            slider.value = input.value || (slider.dataset.priceRange === 'min' ? '0' : String(ceiling));
        });
        rail.style.setProperty('--range-start', `${Number(sliders[0].value) / ceiling * 100}%`);
        rail.style.setProperty('--range-end', `${Number(sliders[1].value) / ceiling * 100}%`);
        form.querySelector('[data-price-output="min"]').textContent = `${rail.dataset.priceSymbol}${sliders[0].value}`;
        form.querySelector('[data-price-output="max"]').textContent = `${rail.dataset.priceSymbol}${sliders[1].value}`;
        sliders[0].style.zIndex = Number(sliders[0].value) === ceiling ? '2' : '1';
    }
    sliders.forEach(slider => slider.addEventListener('input', () => {
        const input = slider.dataset.priceRange === 'min' ? minimum : maximum;
        input.value = slider.value;
        if (minimum.value && maximum.value && Number(minimum.value) > Number(maximum.value)) {
            (input === minimum ? maximum : minimum).value = input.value;
        }
        syncRange();
    }));
    [minimum, maximum].forEach(input => input.addEventListener('input', syncRange));
    apply.disabled = false;
    syncRange();
    syncTeams();
    sync();
});
