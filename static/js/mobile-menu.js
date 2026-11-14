(() => {
    const trigger = document.getElementById('mobile-menu-trigger');
    const menu = document.getElementById('mobile-menu');
    if (!trigger || !menu) return;
    const close = menu.querySelector('[data-close-mobile-menu]');
    const choices = [...menu.querySelectorAll('[data-mobile-theme]')];
    const syncTheme = () => {
        const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        choices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mobileTheme === current)));
    };
    trigger.addEventListener('click', () => {
        if (menu.open) return;
        syncTheme();
        menu.showModal();
        trigger.setAttribute('aria-expanded', 'true');
        close.focus();
    });
    close.addEventListener('click', () => menu.close());
    menu.querySelector('.mobile-menu__pages').addEventListener('click', event => {
        if (event.target.closest('a')) menu.close();
    });
    menu.addEventListener('close', () => {
        trigger.setAttribute('aria-expanded', 'false');
        trigger.focus({preventScroll: true});
    });
    menu.addEventListener('click', event => {
        if (event.target !== menu) return;
        const bounds = menu.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) menu.close();
    });
    choices.forEach(button => button.addEventListener('click', () => {
        window.KitalyThemeManager.applyTheme(button.dataset.mobileTheme, {persist: true, animate: false});
        syncTheme();
    }));
    new MutationObserver(syncTheme).observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
    syncTheme();
})();
