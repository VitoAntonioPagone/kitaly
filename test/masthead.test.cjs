const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup({ scrollY = 0, reduced = false, publicPage = true } = {}) {
    const frames = new Map(), events = {}, values = [];
    let sequence = 0;
    const motion = { matches: reduced, addEventListener: (type, fn) => { events.motion = fn; } };
    const window = { scrollY, matchMedia: () => motion,
        addEventListener: (type, fn) => { events[type] = fn; } };
    const masthead = { style: { setProperty: (key, value) => values.push(Number(value)) },
        classList: { toggle() {} } };
    vm.runInNewContext(fs.readFileSync('static/js/masthead.js', 'utf8'), {
        window, document: { querySelector: () => publicPage ? masthead : null },
        requestAnimationFrame: fn => { const id = ++sequence; frames.set(id, fn); return id; },
        cancelAnimationFrame: id => frames.delete(id),
    });
    const tick = time => {
        const pending = [...frames.values()]; frames.clear();
        pending.forEach(fn => fn(time));
    };
    return { window, events, frames, values, motion, tick };
}

test('coarse scroll steps ease across frames and settle at the final size', () => {
    const s = setup();
    s.window.scrollY = 240;
    s.events.scroll(); s.events.scroll();
    assert.equal(s.frames.size, 1);
    s.tick(0);
    assert.ok(s.values.at(-1) > 0 && s.values.at(-1) < .25);
    for (let time = 16; time < 1500; time += 16) s.tick(time);
    assert.equal(s.values.at(-1), 1);
    assert.equal(s.frames.size, 0);
    assert.ok(s.values.every((value, index) => !index || value >= s.values[index - 1]));
});

test('reversing scroll smoothly restores the expanded logo', () => {
    const s = setup({ scrollY: 240 });
    s.window.scrollY = 0; s.events.scroll(); s.tick(0);
    assert.ok(s.values.at(-1) > .75 && s.values.at(-1) < 1);
    for (let time = 16; time < 1500; time += 16) s.tick(time);
    assert.equal(s.values.at(-1), 0);
});

test('reduced motion and page restoration apply the current scroll position immediately', () => {
    const s = setup({ reduced: true });
    s.window.scrollY = 240; s.events.scroll(); s.tick(0);
    assert.equal(s.values.at(-1), 1); assert.equal(s.frames.size, 0);
    s.window.scrollY = 120; s.events.pageshow();
    assert.equal(s.values.at(-1), .5);
});

test('admin pages do not install the public masthead animation', () => {
    const s = setup({ publicPage: false });
    assert.equal(s.values.length, 0); assert.equal(Object.keys(s.events).length, 0);
});
