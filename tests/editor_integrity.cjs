const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/web/static/app.js', 'utf8');
function evaluate(ctx, start, end) {
  vm.runInContext(source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))), ctx);
}
function environment() {
  const applied = [];
  const ctx = {
    FormData,
    state: {video:{path:'A.mp4', filename:'A.mp4'}, activePackage:{path:'A'}, track:{segments:[{id:1,start:0,end:1,text:'原文'}]}},
    el: {
      alignScriptTextarea:{value:'原詞'},
      rawSubtitleTextarea:{value:'全文草稿'},
      checkAutoProofread:{checked:false},
      selectLlmEngine:{value:'local'},
      selectScriptMode:{value:'reference'},
      btnAiTranscribe:{}
    },
    addLog(){},
    subtitleFingerprint(){return JSON.stringify(ctx.state.track.segments)},
    setSubtitleTrack(track){applied.push(track)},
  };
  vm.createContext(ctx);
  evaluate(ctx, 'let subtitleRequestId =', 'function initAiButtons()');
  evaluate(ctx, 'function formatEditorText(', 'function setSubtitleTrack(');
  return {ctx, applied};
}
(async () => {
  const {ctx} = environment();
  const cues = [{text:'第一句上半\n第一句下半'}, {text:''}, {text:'  尾句\n'}];
  assert.deepEqual(Array.from(ctx.parseEditorText(ctx.formatEditorText(cues), 3)), cues.map(s=>s.text));
  assert.deepEqual(Array.from(ctx.parseEditorText('第一句\n\n第三句',3)), ['第一句','','第三句']);
  for (const value of ['一\n二\n三','一','[#1]\n一\n[#2]\n二']) {
    assert.throws(()=>ctx.parseEditorText(value,2));
  }
  for (const change of ['package','edit','reload','new_request','script','draft','unchanged']) {
    const {ctx:c,applied}=environment();
    let release;
    c.fetch=()=>new Promise(resolve=>{release=resolve});
    const pending=c.runAiTranscribe();
    if(change==='package') {c.state.activePackage={path:'B'};c.state.video.path='B.mp4';}
    if(change==='edit') c.state.track.segments[0].text='手動新內容';
    if(change==='reload') c.state.track=JSON.parse(JSON.stringify(c.state.track));
    if(change==='new_request') c.captureSubtitleRequest();
    if(change==='script') c.el.alignScriptTextarea.value='修改原詞';
    if(change==='draft') c.el.rawSubtitleTextarea.value='未套用的全文草稿';
    release({json:async()=>({status:'success',track:{segments:[{text:'舊辨識結果'}]}})});
    await pending;
    assert.equal(applied.length, change==='unchanged'?1:0, change);
    if(change==='edit') assert.equal(c.state.track.segments[0].text,'手動新內容');
  }
  console.log('Stale results rejected; multiline and empty cues survive text editing.');
})().catch(error=>{console.error(error);process.exitCode=1});
