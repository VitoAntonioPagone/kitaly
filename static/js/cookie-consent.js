(() => {
    const banner = document.getElementById('cookie-banner');
    if (!banner) return;
    const dialog = document.getElementById('cookie-dialog');
    const launcher = document.getElementById('cookie-launcher');
    const form = document.getElementById('cookie-consent-form');
    const checkbox = document.getElementById('cookie-appearance');
    const readChoice = () => document.cookie.split(';').map(v => v.trim()).find(v => /^appearance_preferences=v1:(on|off)$/.test(v));
    const open = () => {
        checkbox.checked = readChoice() === 'appearance_preferences=v1:on';
        dialog.showModal();
    };
    banner.hidden = Boolean(readChoice());
    launcher.hidden = false;
    launcher.addEventListener('click', open);
    document.querySelectorAll('[data-customize]').forEach(button => button.addEventListener('click', open));
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    let saving = false;
    async function save(choice) {
        if (saving) return;
        saving = true;
        const buttons = [...document.querySelectorAll('#cookie-dialog button, #cookie-banner button')];
        buttons.forEach(button => button.disabled = true);
        try {
            const data = new FormData(form);
            data.set('appearance_preferences', choice);
            const response = await fetch(form.action, { method: 'POST', body: data, credentials: 'same-origin' });
            if (!response.ok || !readChoice()) throw new Error('Consent not saved');
            try {
                if (choice === 'off') localStorage.removeItem('theme');
                else localStorage.setItem('theme', document.documentElement.dataset.theme || 'light');
            } catch (_) { /* Cookie choice still applies if localStorage is unavailable. */ }
            window.location.reload();
        } catch (_) {
            const italian = document.documentElement.lang === 'it';
            const status = document.getElementById('cookie-status');
            status.textContent = italian ? 'Impossibile salvare. Riprova o apri Preferenze cookie nel footer.' : 'Could not save. Please retry or open Cookie preferences in the footer.';
            // Keep errors visible even while the modal is open.
            if (dialog.open) dialog.querySelector('form').prepend(status);
            saving = false;
            buttons.forEach(button => button.disabled = false);
        }
    }
    document.querySelectorAll('[data-consent]').forEach(button => button.addEventListener('click', () => save(button.dataset.consent)));
    form.addEventListener('submit', event => { event.preventDefault(); save(checkbox.checked ? 'on' : 'off'); });
})();
