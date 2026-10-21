/* Ease scroll updates between frames, including coarse mouse-wheel steps. */
(() => {
    const masthead = document.querySelector('body.public-storefront #main-nav');
    if (!masthead) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const targetProgress = () => {
        const position = Math.min(1, Math.max(0, window.scrollY / 240));
        return position * position * (3 - 2 * position);
    };
    let progress = targetProgress();
    let frame = null;
    let previousTime = null;

    const render = () => {
        masthead.style.setProperty('--masthead-progress', progress.toFixed(5));
        masthead.classList.toggle('scrolled', window.scrollY > 20);
    };
    const animate = (time) => {
        frame = null;
        const target = targetProgress();
        const elapsed = previousTime === null ? 1000 / 60 : Math.min(time - previousTime, 64);
        previousTime = time;
        progress = reducedMotion.matches ? target : progress + (target - progress) * (1 - Math.exp(-elapsed / 90));
        if (Math.abs(target - progress) < .0001) progress = target;
        render();
        if (progress !== target) frame = requestAnimationFrame(animate);
        else previousTime = null;
    };
    const schedule = () => {
        if (frame === null) frame = requestAnimationFrame(animate);
    };
    const restore = () => {
        if (frame !== null) cancelAnimationFrame(frame);
        frame = null;
        previousTime = null;
        progress = targetProgress();
        render();
    };

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('pageshow', restore);
    reducedMotion.addEventListener('change', restore);
    render();
})();
