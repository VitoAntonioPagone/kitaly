// Let the real link open Instagram; never create an empty tab or replace this page.
document.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[data-instagram-message]');
    const message = link?.dataset.instagramMessage;
    if (!message) return;

    // This is supplementary to the link's native target="_blank" behaviour.
    showInstagramMessage(message);
    const updateStatus = text => {
        const status = document.querySelector('[data-instagram-message-status]');
        if (status) status.textContent = text;
    };
    const fallback = () => updateStatus('Use Copy message, then paste it in Instagram.');
    if (!navigator.clipboard?.writeText) {
        fallback();
        return;
    }
    try {
        Promise.resolve(navigator.clipboard.writeText(message)).then(
            () => updateStatus('Copied. Paste it in Instagram to send.'),
            fallback,
        );
    } catch (error) {
        fallback();
    }
});
