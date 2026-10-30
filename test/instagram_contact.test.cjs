const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(clipboard) {
    let handler;
    const shown = [], status = { textContent: '' };
    const window = { location: { href: '/shirt/140' }, open: () => { throw Error('Must not open a synthetic tab'); } };
    const link = { dataset: { instagramMessage: 'Question about shirt 140' }, href: 'https://ig.me/m/kitaly' };
    const event = { button: 0, target: { closest: () => link },
        preventDefault: () => { throw Error('Must preserve native link navigation'); } };
    vm.runInNewContext(fs.readFileSync('static/js/instagram-contact.js', 'utf8'), {
        document: { addEventListener: (type, fn) => { handler = fn; }, querySelector: () => status },
        navigator: { clipboard }, window, showInstagramMessage: text => shown.push(text),
    });
    return { click: () => handler(event), event, shown, status, window, link };
}

test('copies the shirt message without preventing the real link or navigating the source page', async () => {
    const copied = [];
    const s = setup({ writeText: async text => copied.push(text) });
    s.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(copied, ['Question about shirt 140']);
    assert.deepEqual(s.shown, copied);
    assert.equal(s.window.location.href, '/shirt/140');
    assert.match(s.status.textContent, /Copied/);
});

test('unavailable or denied clipboard still leaves native navigation and source page intact', async () => {
    for (const clipboard of [undefined, { writeText: () => Promise.reject(Error('Denied')) },
        { writeText: () => { throw Error('Unavailable'); } }]) {
        const s = setup(clipboard);
        s.click();
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(s.shown.length, 1);
        assert.equal(s.window.location.href, '/shirt/140');
        assert.match(s.status.textContent, /Copy message/);
    }
});

test('modified clicks, cancelled clicks and ordinary links retain browser behaviour', () => {
    for (const property of ['metaKey', 'ctrlKey', 'shiftKey', 'altKey', 'defaultPrevented']) {
        const s = setup(); s.event[property] = true; s.click();
        assert.equal(s.shown.length, 0);
    }
    const middle = setup(); middle.event.button = 1; middle.click();
    assert.equal(middle.shown.length, 0);
    const ordinary = setup(); ordinary.event.target.closest = () => null; ordinary.click();
    assert.equal(ordinary.shown.length, 0);
});
