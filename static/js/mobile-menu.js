(() => {
    const trigger = document.getElementById('mobile-menu-trigger');
    const menu = document.getElementById('mobile-menu');
    if (!trigger || !menu) return;
    const close = menu.querySelector('[data-close-mobile-menu]');
    const playerIssueFeature = menu.querySelector('[data-player-issue-shirts]');
    const playerIssueImg = playerIssueFeature ? playerIssueFeature.querySelector('.wide-menu__image img') : null;
    let playerIssuePool = [];
    if (playerIssueFeature) {
        try {
            const parsed = JSON.parse(playerIssueFeature.dataset.playerIssueShirts || '[]');
            if (Array.isArray(parsed)) playerIssuePool = parsed.filter(item => item && item.src);
        } catch (error) {
            playerIssuePool = [];
        }
    }
    const pickRandomPlayerIssue = () => {
        if (!playerIssueImg || playerIssuePool.length === 0) return;
        const currentSrc = playerIssueImg.getAttribute('src');
        const candidates = playerIssuePool.length > 1
            ? playerIssuePool.filter(item => item.src !== currentSrc)
            : playerIssuePool;
        const pool = candidates.length > 0 ? candidates : playerIssuePool;
        const chosen = pool[Math.floor(Math.random() * pool.length)];
        if (!chosen) return;
        playerIssueImg.loading = 'eager';
        playerIssueImg.src = chosen.src;
        if (chosen.alt) playerIssueImg.alt = chosen.alt;
    };
    trigger.addEventListener('click', () => {
        if (menu.open) return;
        pickRandomPlayerIssue();
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
})();
