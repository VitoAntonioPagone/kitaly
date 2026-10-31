(() => {
    const trigger = document.getElementById('mobile-menu-trigger');
    const menu = document.getElementById('mobile-menu');
    if (!trigger || !menu) return;
    const viewport = window.matchMedia('(max-width: 640px)');
    const close = menu.querySelector('[data-close-mobile-menu]');
    const choices = [...menu.querySelectorAll('[data-mobile-theme]')];
    const syncTheme = () => {
        const current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        choices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mobileTheme === current)));
    };
    trigger.addEventListener('click', () => {
        if (!viewport.matches || menu.open) return;
        syncTheme();
        menu.showModal();
        trigger.setAttribute('aria-expanded', 'true');
        close.focus();
    });
    close.addEventListener('click', () => menu.close());
    menu.addEventListener('close', () => {
        trigger.setAttribute('aria-expanded', 'false');
        if (viewport.matches) trigger.focus();
        else document.querySelector('#main-nav .kitaly-logo')?.focus();
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
    viewport.addEventListener('change', event => { if (!event.matches && menu.open) menu.close(); });
    new MutationObserver(syncTheme).observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
    syncTheme();
})();

(() => {
    const stockTrigger = document.getElementById('stock-submenu-trigger');
    const stockSubmenu = document.getElementById('stock-submenu');
    const nav = document.getElementById('main-nav');
    if (!stockTrigger || !stockSubmenu) return;

    const setOpen = (open) => {
        stockSubmenu.hidden = !open;
        stockTrigger.setAttribute('aria-expanded', String(open));
    };

    stockTrigger.addEventListener('click', (event) => {
        event.stopPropagation();
        setOpen(stockSubmenu.hidden);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !stockSubmenu.hidden) {
            setOpen(false);
            stockTrigger.focus();
        }
    });

    document.addEventListener('click', (event) => {
        if (!stockSubmenu.hidden && nav && !nav.contains(event.target)) {
            setOpen(false);
        }
    });
})();
