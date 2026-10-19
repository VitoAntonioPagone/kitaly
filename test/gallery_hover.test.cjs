const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(count = 3, initialIndex = 0, showOverride) {
    let now = 0, sequence = 0, manual = false;
    const tasks = new Map(), shown = [];
    const context = { window: {},
        setTimeout: (fn, delay) => { const id = ++sequence; tasks.set(id, {fn, at:now + delay}); return id; },
        clearTimeout: id => tasks.delete(id),
    };
    vm.runInNewContext(fs.readFileSync('static/js/gallery-hover.js', 'utf8'), context);
    const hover = context.window.createGalleryHoverPreview({ count, initialIndex,
        show: index => { shown.push({index, at:now}); return showOverride?.(index); },
        isManual: () => manual,
    });
    const advance = async delay => {
        const until = now + delay;
        while (true) {
            const next = [...tasks].sort((a,b) => a[1].at-b[1].at).find(([,t])=>t.at <= until);
            if (!next) break;
            now = next[1].at; tasks.delete(next[0]); next[1].fn();
            await Promise.resolve(); await Promise.resolve();
        }
        now = until;
    };
    return {hover, shown, advance, manual: value => {manual = value;}, pending:()=>tasks.size};
}

test('three photos preview 2, 3, 2 at equal intervals and stop', async () => {
    const s = setup(); s.hover.start({pointerType:'mouse'});
    await s.advance(899); assert.equal(s.shown.length,0);
    await s.advance(1); await s.advance(1250); await s.advance(1250); await s.advance(10000);
    assert.deepEqual(s.shown,[{index:1,at:900},{index:2,at:2150},{index:1,at:3400}]);
    assert.equal(s.pending(),0);
});
test('two photos retain their original hover and return behaviour', async () => {
    const s=setup(2);s.hover.start({pointerType:'mouse'});await s.advance(3000);
    assert.deepEqual(s.shown.map(s=>s.index),[1,0]);
});
test('leaving restores the cover and cancels future previews', async () => {
    const s=setup();s.hover.start({pointerType:'mouse'});await s.advance(900);
    s.hover.stop();await s.advance(10000);assert.deepEqual(s.shown.map(s=>s.index),[1,0]);
});
test('manual navigation and touch prevent automatic previews', async () => {
    const s=setup();s.hover.start({pointerType:'touch'});await s.advance(3000);assert.equal(s.shown.length,0);
    s.manual(true);s.hover.start({pointerType:'mouse'});s.hover.stop();await s.advance(3000);assert.equal(s.shown.length,0);
});
test('initial cover index is respected and a single photo stays still', async () => {
    const s=setup(3,2);s.hover.start({pointerType:'mouse'});await s.advance(3400);
    assert.deepEqual(s.shown.map(s=>s.index),[0,1,0]);
    const single=setup(1);single.hover.start({pointerType:'mouse'});await single.advance(5000);assert.equal(single.shown.length,0);
});
test('next delay begins only after the requested photo has loaded', async () => {
    let finish;
    const s=setup(3,0,()=>new Promise(resolve=>{finish=resolve;}));
    s.hover.start({pointerType:'mouse'});await s.advance(900);await s.advance(3000);
    assert.equal(s.shown.length,1);finish();await Promise.resolve();await Promise.resolve();
    await s.advance(1249);assert.equal(s.shown.length,1);await s.advance(1);assert.equal(s.shown[1].index,2);
});
test('cancelling while a photo loads prevents the following timer', async () => {
    let finish;const s=setup(3,0,()=>new Promise(resolve=>{finish=resolve;}));
    s.hover.start({pointerType:'mouse'});await s.advance(900);s.hover.cancel();finish();
    await Promise.resolve();await Promise.resolve();await s.advance(10000);assert.equal(s.shown.length,1);
});
