/* Shared timing for catalogue cards and the product gallery. */
window.createGalleryHoverPreview = ({ count, initialIndex, show, isManual }) => {
    let timer = null;
    let generation = 0;
    const cancel = () => {
        generation += 1;
        if (timer !== null) clearTimeout(timer);
        timer = null;
    };
    const start = (event) => {
        if (event.pointerType === 'touch' || isManual() || count < 2) return;
        cancel();
        const run = generation;
        const offsets = count >= 3 ? [1, 2, 0] : [1, 0];
        const advance = async (step) => {
            timer = null;
            if (run !== generation || isManual()) return;
            await show((initialIndex + offsets[step]) % count);
            if (run !== generation || isManual()) return;
            // Each loaded preview stays visible for the same 1.25 seconds.
            if (step + 1 < offsets.length) timer = setTimeout(() => advance(step + 1), 1250);
        };
        timer = setTimeout(() => advance(0), 900);
    };
    const stop = () => {
        cancel();
        if (!isManual()) show(initialIndex);
    };
    return { start, stop, cancel };
};
