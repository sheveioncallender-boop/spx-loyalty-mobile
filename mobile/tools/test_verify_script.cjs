/* Run with node --test tools/test_verify_script.cjs. No browser or network. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '../odoo/spx_loyalty_mobile/static/src/account/verify.js'), 'utf8');

function page({ visibility = 'visible', prerendering = false, failure = false } = {}) {
    const listeners = {};
    const status = { hidden: true }, button = { hidden: false };
    let submitCount = 0, cleanHistory = 0;
    const form = {
        addEventListener: (name, fn) => { listeners['form:' + name] = fn; },
        querySelector: () => button,
        requestSubmit: () => {
            if (failure) throw Error('Submission unavailable');
            listeners['form:submit']?.();
            submitCount++;
        },
    };
    const document = {
        visibilityState: visibility, prerendering,
        getElementById: id => id === 'verify-email-form' ? form : id === 'verification-status' ? status : null,
        addEventListener: (name, fn) => { listeners[name] = fn; },
    };
    const window = {
        history: { replaceState: (_, __, url) => {
            assert.equal(url, '/spx/mobile/account/verify'); cleanHistory++;
        } },
        location: { pathname: '/spx/mobile/account/verify' },
        requestAnimationFrame: fn => { listeners.frame = fn; },
    };
    vm.runInNewContext(script, { document, window });
    return { listeners, document, status, button, submitCount: () => submitCount, cleanHistory: () => cleanHistory };
}

test('visible email page submits once and cleans token from history', () => {
    const p = page();
    p.listeners.frame(); p.listeners.visibilitychange(); p.listeners.prerenderingchange();
    assert.equal(p.submitCount(), 1);
    assert.equal(p.cleanHistory(), 1);
    assert.equal(p.status.hidden, false);
});
test('hidden/prerendered page waits until opened', () => {
    const p = page({ visibility: 'hidden', prerendering: true });
    p.listeners.frame(); assert.equal(p.submitCount(), 0);
    p.document.visibilityState = 'visible';
    p.listeners.visibilitychange(); assert.equal(p.submitCount(), 0);
    p.document.prerendering = false;
    p.listeners.prerenderingchange(); assert.equal(p.submitCount(), 1);
});
test('manual fallback submission prevents a second automatic submission', () => {
    const p = page();
    p.listeners['form:submit']();
    p.listeners.frame();
    assert.equal(p.submitCount(), 0);
});
test('failed automatic submission keeps the fallback button available', () => {
    const p = page({ failure: true });
    p.listeners.frame();
    assert.equal(p.submitCount(), 0);
    assert.equal(p.button.hidden, false);
    assert.equal(p.status.hidden, true);
});

test('mobile success page opens the app and retains a user-tappable link', () => {
    const app = { href: 'jennys://account/verified?code=example' };
    const window = { location: { href: '' }, setTimeout: fn => fn() };
    vm.runInNewContext(script, { document: { getElementById: id => id === 'open-jennys-app' ? app : null },
        navigator: { userAgent: 'Android' }, window });
    assert.equal(window.location.href, app.href);
});
test('desktop verification leaves the app button available without automatic launch', () => {
    const app = { href: 'jennys://account/verified?code=example' };
    const window = { location: { href: '' }, setTimeout: () => assert.fail('Desktop must not auto-launch') };
    vm.runInNewContext(script, { document: { getElementById: () => app },
        navigator: { userAgent: 'Windows' }, window });
    assert.equal(window.location.href, '');
});


test('reset form never auto-submits and blocks repeated password submissions', () => {
    const listeners = {}, button = {textContent: 'Save new password', disabled: false};
    const form = {querySelector: () => button, addEventListener: (n,f) => listeners[n] = f};
    const window = {addEventListener: (n,f) => listeners[n] = f};
    vm.runInNewContext(script, {document: {getElementById: id => id === 'reset-password-form' ? form : null}, window});
    assert.equal(button.disabled, false);
    let blocked = 0;
    const event = {preventDefault: () => blocked++};
    listeners.submit(event);
    assert.equal(button.disabled, true);
    assert.equal(button.textContent, 'Saving your password…');
    listeners.submit(event);
    assert.equal(blocked, 1);
    listeners.pageshow();
    assert.equal(button.disabled, false);
    assert.equal(button.textContent, 'Save new password');
});
