const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(cookie) {
    const calls = [], classes = new Set();
    const document = {cookie, readyState: 'loading', addEventListener() {},
        documentElement: {dataset: {}, style: {}, classList: {
            add: key => classes.add(key), remove: key => classes.delete(key),
            toggle: (key, on) => on ? classes.add(key) : classes.delete(key),
        }}};
    const window = {};
    vm.runInNewContext(fs.readFileSync('static/js/theme-manager.js', 'utf8'), {
        document, window, localStorage: {getItem: key => { calls.push(['read',key]); return 'dark'; },
            setItem: (key,value) => calls.push(['write',key,value])},
    });
    return {manager: window.KitalyThemeManager, calls, document};
}

test('objecting to appearance storage stops reads and writes while theme controls still work', () => {
    const {manager,calls,document} = setup('appearance_preferences=off');
    assert.equal(manager.getSavedTheme(), null);
    manager.applyTheme('dark', {animate:false});
    assert.deepEqual(calls, []);
    assert.equal(document.documentElement.dataset.theme, 'dark');
});

test('appearance preferences remain available when enabled', () => {
    const {manager,calls} = setup('appearance_preferences=on');
    assert.equal(manager.getSavedTheme(), 'dark');
    manager.applyTheme('light', {animate:false});
    assert.deepEqual(calls, [['read','theme'], ['write','theme','light']]);
});
