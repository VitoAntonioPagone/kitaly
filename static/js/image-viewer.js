document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.getElementById('image-viewer');
    const trigger = document.getElementById('open-image-viewer');
    if (!dialog || !trigger) return;
    const main = document.getElementById('main-image');
    const photo = document.getElementById('image-viewer-photo');
    const counter = document.getElementById('image-viewer-count');
    const thumbnails = [...document.querySelectorAll('[data-image-src]')];
    const fullSources = thumbnails.length ? thumbnails.map(t => t.dataset.fullImageSrc || t.dataset.imageSrc) : [main.dataset.fullImageSrc || main.getAttribute('src')];
    const sources = thumbnails.length ? thumbnails.map(t => t.dataset.imageSrc) : [main.getAttribute('src')];
    let current = 0;
    let previousOverflow = '';
    let photoRequest = 0;
    const show = index => {
        current = (index + sources.length) % sources.length;
        const request = ++photoRequest;
        // Show the lightweight detail photo first, then upgrade to the original.
        const preview = new Image();
        preview.src = sources[current];
        const originalSource = fullSources[current];
        preview.decode().then(() => {
            if (request !== photoRequest) return;
            photo.src = preview.src;
            counter.textContent = `${current + 1} / ${sources.length}`;
            const original = new Image();
            original.src = originalSource;
            original.decode().then(() => {
                if (request === photoRequest) photo.src = original.src;
            }).catch(() => {});
        }).catch(() => {});
    };
    dialog.querySelectorAll('[data-viewer-step]').forEach(button => {
        button.hidden = sources.length < 2;
        button.addEventListener('click', () => show(current + Number(button.dataset.viewerStep)));
    });
    trigger.addEventListener('click', () => {
        if (typeof clearItemGalleryHoverTimers === 'function') clearItemGalleryHoverTimers();
        show(Math.max(0, sources.indexOf(main.getAttribute('src'))));
        previousOverflow = document.documentElement.style.overflow;
        document.documentElement.style.overflow = 'hidden';
        dialog.showModal();
    });
    dialog.querySelector('[data-viewer-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => {
        photoRequest += 1;
        document.documentElement.style.overflow = previousOverflow;
        trigger.focus({ preventScroll: true });
    });
    dialog.addEventListener('keydown', event => {
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
            event.preventDefault();
            show(current + (event.key === 'ArrowRight' ? 1 : -1));
        }
    });
    let touchStart = null;
    photo.addEventListener('touchstart', event => {
        touchStart = event.touches.length === 1 ? {x: event.touches[0].clientX, y: event.touches[0].clientY} : null;
    }, {passive: true});
    photo.addEventListener('touchend', event => {
        if (!touchStart || !event.changedTouches.length) return;
        const dx = event.changedTouches[0].clientX - touchStart.x;
        const dy = event.changedTouches[0].clientY - touchStart.y;
        if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) show(current + (dx < 0 ? 1 : -1));
        touchStart = null;
    }, {passive: true});
});
