const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('src/web/static/app.js', 'utf8');
const payload = '<img src=x onerror=alert(1)>';
class Element {
  constructor() { this.children = []; this.nodes = new Map(); this.style = {}; }
  set innerHTML(value) { this.html = value; }
  get innerHTML() { return this.html; }
  appendChild(node) { this.children.push(node); }
  querySelector(selector) {
    if (!['.asset-name', '.font-label', '.font-description'].includes(selector)) return null;
    if (!this.nodes.has(selector)) this.nodes.set(selector, new Element());
    return this.nodes.get(selector);
  }
}
const assets = new Element();
const fonts = new Element();
const context = {
  document: { createElement: () => new Element() },
  el: { assetLibraryContainer: assets, fontCatalogList: fonts },
  state: {
    assets: [{ name: payload + '.txt', type: 'text', size_mb: 1, line_count: 1, is_sample: false }],
    showSamples: true, assetFilter: 'all', video: {}, track: {}, style: {},
  },
};
function evaluate(start, end) {
  const offset = source.indexOf(start);
  vm.runInNewContext(source.slice(offset, source.indexOf(end, offset)), context);
}
evaluate('function renderFilteredAssetLibrary()', '\nasync function selectScriptAssetForAlignment');
evaluate('function renderFontManagerCatalog(', '\nfunction applyFontCatalogData');
context.renderFilteredAssetLibrary();
const card = assets.children[0];
assert(!card.innerHTML.includes(payload));
assert.equal(card.querySelector('.asset-name').textContent, payload + '.txt');
context.renderFontManagerCatalog({ installed: [{
  category: 'custom', filename: 'test.ttf', family: payload + '"; color: red;', display_name: payload, size_mb: 1,
}] });
const row = fonts.children[0];
assert(!row.innerHTML.includes(payload));
assert.equal(row.querySelector('.font-label').textContent, payload);
console.log('Untrusted asset and font names remain text nodes.');
