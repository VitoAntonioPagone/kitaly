(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const setExpanded = (control, expanded) => {
        if (control) control.setAttribute('aria-expanded', String(expanded));
    };

    const searchToggle = document.querySelector('[data-search-toggle]');
    const headerSearch = document.getElementById('header-search');
    if (searchToggle && headerSearch) {
        searchToggle.addEventListener('click', () => {
            const willOpen = headerSearch.hidden;
            headerSearch.hidden = !willOpen;
            setExpanded(searchToggle, willOpen);
            if (willOpen) {
                window.setTimeout(() => headerSearch.querySelector('input')?.focus(), reduceMotion ? 0 : 80);
            }
        });
    }

    const menuToggle = document.querySelector('[data-menu-toggle]');
    const mobileMenu = document.getElementById('mobile-menu');
    if (menuToggle && mobileMenu) {
        menuToggle.addEventListener('click', () => {
            const willOpen = mobileMenu.hidden;
            mobileMenu.hidden = !willOpen;
            setExpanded(menuToggle, willOpen);
        });
        mobileMenu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
            mobileMenu.hidden = true;
            setExpanded(menuToggle, false);
        }));
    }

    const header = document.querySelector('.archive-header');
    if (header) {
        const updateHeaderHeight = () => document.documentElement.style.setProperty('--header-height', `${header.offsetHeight}px`);
        new ResizeObserver(updateHeaderHeight).observe(header);
        updateHeaderHeight();
    }
    const filterDrawer = document.getElementById('archive-filters');
    const filterOpens = Array.from(document.querySelectorAll('[data-filter-drawer-toggle]'));
    const filterClose = document.querySelector('[data-filter-drawer-close]');
    const narrowScreen = window.matchMedia('(max-width: 900px)');
    let lastFilterTrigger = null;
    const backdrop = document.createElement('div');
    backdrop.className = 'filter-backdrop';
    backdrop.hidden = true;
    document.body.appendChild(backdrop);
    const closeFilterDrawer = (restoreFocus = true) => {
        filterDrawer?.classList.remove('is-open');
        filterDrawer?.removeAttribute('role');
        filterDrawer?.removeAttribute('aria-modal');
        filterOpens.forEach(control => setExpanded(control, false));
        backdrop.hidden = true;
        document.body.style.removeProperty('overflow');
        if (filterDrawer && narrowScreen.matches) filterDrawer.inert = true;
        if (restoreFocus) lastFilterTrigger?.focus();
    };
    const syncFilterLayout = () => {
        closeFilterDrawer(false);
        if (filterDrawer) filterDrawer.inert = narrowScreen.matches;
        filterOpens.forEach(control => setExpanded(control, !narrowScreen.matches));
    };
    if (filterDrawer) {
        syncFilterLayout();
        narrowScreen.addEventListener('change', syncFilterLayout);
        filterOpens.forEach(control => control.addEventListener('click', () => {
            if (!narrowScreen.matches) {
                filterDrawer.scrollIntoView({ behavior: reduceMotion ? 'instant' : 'smooth', block: 'start' });
                filterDrawer.querySelector('input[type="search"]')?.focus({ preventScroll: true });
                return;
            }
            lastFilterTrigger = control;
            if (filterDrawer.classList.contains('is-open')) { closeFilterDrawer(); return; }
            filterDrawer.inert = false;
            filterDrawer.classList.add('is-open');
            filterDrawer.setAttribute('role', 'dialog');
            filterDrawer.setAttribute('aria-modal', 'true');
            filterOpens.forEach(button => setExpanded(button, true));
            backdrop.hidden = false;
            document.body.style.overflow = 'hidden';
            filterClose?.focus();
        }));
        filterClose?.addEventListener('click', () => closeFilterDrawer());
        backdrop.addEventListener('click', () => closeFilterDrawer());
        filterDrawer.addEventListener('keydown', event => {
            if (event.key !== 'Tab' || !filterDrawer.classList.contains('is-open')) return;
            const focusable = Array.from(filterDrawer.querySelectorAll('button, input, summary, a[href], select')).filter(el => el.getClientRects().length && !el.disabled && el.type !== 'hidden');
            const first = focusable[0], last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
            if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        });
        const groups = Array.from(filterDrawer.querySelectorAll('details'));
        groups.forEach(group => group.addEventListener('toggle', () => {
            if (!group.open || narrowScreen.matches) return;
            groups.forEach(other => { if (other !== group) other.open = false; });
            const options = group.querySelector('.filter-group__options');
            const alignRight = group.getBoundingClientRect().left + 260 > window.innerWidth - 16;
            options.style.left = alignRight ? 'auto' : '-1px';
            options.style.right = alignRight ? '-1px' : 'auto';
        }));
        document.addEventListener('click', event => {
            if (!filterDrawer.contains(event.target)) groups.forEach(group => { group.open = false; });
        });
    }

    document.querySelectorAll('[data-gallery]').forEach((gallery) => {
        const images = Array.from(gallery.querySelectorAll('[data-gallery-image]'));
        const dots = Array.from(gallery.querySelectorAll('[data-gallery-dot]'));
        if (images.length < 2) return;

        let index = Math.max(0, images.findIndex((image) => image.classList.contains('is-active')));
        let firstTimer = null;
        let secondTimer = null;
        let touchStart = 0;

        const show = (nextIndex) => {
            index = (nextIndex + images.length) % images.length;
            images.forEach((image, imageIndex) => image.classList.toggle('is-active', imageIndex === index));
            dots.forEach((dot, dotIndex) => dot.classList.toggle('is-active', dotIndex === index));
        };
        const clearTimers = () => {
            window.clearTimeout(firstTimer);
            window.clearTimeout(secondTimer);
        };

        gallery.addEventListener('mouseenter', () => {
            if (reduceMotion || !window.matchMedia('(hover:hover)').matches) return;
            clearTimers();
            firstTimer = window.setTimeout(() => {
                show(index + 1);
                secondTimer = window.setTimeout(() => show(0), 1150);
            }, 650);
        });
        gallery.addEventListener('mouseleave', () => { clearTimers(); show(0); });
        gallery.addEventListener('touchstart', (event) => { touchStart = event.touches[0]?.clientX || 0; }, { passive: true });
        gallery.addEventListener('touchend', (event) => {
            const end = event.changedTouches[0]?.clientX || touchStart;
            if (Math.abs(end - touchStart) > 38) show(index + (end < touchStart ? 1 : -1));
        }, { passive: true });
    });

    const mainImage = document.querySelector('[data-product-main-image]');
    const thumbnails = Array.from(document.querySelectorAll('[data-product-thumbnail]'));
    if (mainImage && thumbnails.length) {
        thumbnails.forEach((thumbnail) => thumbnail.addEventListener('click', () => {
            const src = thumbnail.dataset.imageSrc;
            if (!src || src === mainImage.src) return;
            mainImage.style.opacity = '0';
            window.setTimeout(() => {
                mainImage.src = src;
                mainImage.style.opacity = '1';
            }, reduceMotion ? 0 : 160);
            thumbnails.forEach((item) => item.classList.toggle('is-active', item === thumbnail));
        }));
    }

    const lightbox = document.querySelector('[data-image-lightbox]');
    const lightboxImage = document.querySelector('[data-image-lightbox-image]');
    const closeLightbox = () => {
        if (!lightbox) return;
        lightbox.hidden = true;
        document.body.style.removeProperty('overflow');
    };
    document.querySelector('[data-product-zoom]')?.addEventListener('click', () => {
        if (!lightbox || !lightboxImage || !mainImage) return;
        lightboxImage.src = mainImage.src;
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
        lightbox.querySelector('[data-image-lightbox-close]')?.focus();
    });
    document.querySelector('[data-image-lightbox-close]')?.addEventListener('click', closeLightbox);
    lightbox?.addEventListener('click', (event) => { if (event.target === lightbox) closeLightbox(); });

    const playerModal = document.querySelector('[data-player-info-modal]');
    const closePlayerModal = () => {
        if (!playerModal) return;
        playerModal.hidden = true;
        document.body.style.removeProperty('overflow');
    };
    document.querySelector('[data-player-info-open]')?.addEventListener('click', () => {
        if (!playerModal) return;
        playerModal.hidden = false;
        document.body.style.overflow = 'hidden';
        playerModal.querySelector('.archive-modal__dialog > button')?.focus();
    });
    document.querySelectorAll('[data-player-info-close]').forEach((control) => control.addEventListener('click', closePlayerModal));

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        if (lightbox && !lightbox.hidden) closeLightbox();
        if (playerModal && !playerModal.hidden) closePlayerModal();
        if (filterDrawer?.classList.contains('is-open')) closeFilterDrawer();
        filterDrawer?.querySelectorAll('details[open]').forEach(group => { group.open = false; });
        if (mobileMenu && !mobileMenu.hidden) { mobileMenu.hidden = true; setExpanded(menuToggle, false); menuToggle?.focus(); }
        if (headerSearch && !headerSearch.hidden) {
            headerSearch.hidden = true;
            setExpanded(searchToggle, false);
            searchToggle?.focus();
        }
    });
})();
