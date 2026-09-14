/* Complete an opened email link with Odoo's session-bound CSRF form.
 * GET/HEAD only render a page; they never activate a user. */
(() => {
    'use strict';
    const app = document.getElementById('open-jennys-app');
    if (app) {
        // Browsers may require the user's tap; the same button remains usable.
        if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            window.setTimeout(() => { window.location.href = app.href; }, 350);
        }
        return;
    }
    const reset = document.getElementById('reset-password-form');
    if (reset) {
        let saving = false;
        const button = reset.querySelector('button');
        const label = button?.textContent;
        reset.addEventListener('submit', (event) => {
            if (saving) { event.preventDefault(); return; }
            saving = true;
            if (button) { button.disabled = true; button.textContent = 'Saving your password…'; }
        });
        // Restore controls if the user returns via the browser's back cache.
        window.addEventListener('pageshow', () => {
            saving = false;
            if (button) { button.disabled = false; button.textContent = label; }
        });
        // Recovery is never submitted automatically, including by email previews.
        return;
    }
    const form = document.getElementById('verify-email-form');
    if (!form) return;
    let submitting = false;
    form.addEventListener('submit', () => { submitting = true; });
    function verify() {
        if (submitting || document.prerendering || document.visibilityState !== 'visible') return;
        submitting = true;
        const status = document.getElementById('verification-status');
        const button = form.querySelector('button');
        if (status) status.hidden = false;
        // Remove the bearer token from this history entry. Its value stays in
        // the POST form, and the page's no-referrer policy also protects it.
        try { window.history.replaceState(null, '', window.location.pathname); } catch (_) { /* continue */ }
        try {
            form.requestSubmit();
            if (button) button.hidden = true;
        } catch (_) {
            submitting = false;
            if (status) status.hidden = true;
            if (button) button.hidden = false;
        }
    }
    document.addEventListener('visibilitychange', verify);
    document.addEventListener('prerenderingchange', verify);
    window.requestAnimationFrame(verify);
})();
