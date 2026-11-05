const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/web/static/app.js', 'utf8');
const emptyTrack = () => ({source_file:'', segments:[], duration:0, language:'zh'});
const packageInfo = path => ({path, name:path, media:{name:path+'.mp4', stem:path, url:'/uploads/'+path+'/'+path+'.mp4', absolute_path:'/uploads/'+path+'/'+path+'.mp4'}, subtitle:path==='A'?{name:'A.srt'}:null});
function environment() {
  const calls = [];
  const storage = new Map();
  const element = () => ({value:'',textContent:'', classList:{add(){},remove(){}}, pause(){},load(){},removeAttribute(){}});
  const context = {
    state:{track:emptyTrack(),activePackage:null,packages:[packageInfo('A'),packageInfo('B')],video:{}, packageLoading:false, packageBusy:false, savedSubtitle:'[]',savedScript:'',style:{}},
    el:Object.fromEntries(['video','videoFilename','mediaBadge','placeholder','videoCenterPlayBadge','alignScriptTextarea','packageSaveStatus','segmentCountBadge','editorSegCount','waveformBarWrapper'].map(key=>[key,element()])),
    localStorage:{setItem(k,v){storage.set(k,v)},removeItem(k){storage.delete(k)}},
    setTimeout(fn){ context.timer=fn;return 1; },clearTimeout(){context.timer=null;},
    showBusyOverlay(){},hideBusyOverlay(){},addLog(){},renderFilteredAssetLibrary(){},
    renderSegmentList(){},updateSubtitleSelectDropdown(){},updateSummary(){},updateWorkspaceSlots(){},drawWaveformTimeline(){},updateSubtitleOverlayOnTime(){},
    async fetch(url,options) {
      const payload=JSON.parse(options.body);calls.push({url,payload});
      if(url==='/api/packages/open') return {ok:true,async json(){return {
        package:packageInfo(payload.path), script_text:payload.path==='A'?'A原詞':'',
        track:payload.path==='A'?{source_file:'A.srt',segments:[{id:1,start:.123,end:1.456,text:'A字幕'}],duration:2}:emptyTrack()
      }}};
      if(url==='/api/packages/save') return {ok:true,async json(){return {package:packageInfo(payload.path)}}};
      throw new Error('Unexpected route '+url);
    },
  };
  vm.createContext(context);
  function evaluate(start,end) {
    const offset=source.indexOf(start);assert(offset>=0,start);
    const stop=source.indexOf(end,offset);assert(stop>offset,end);
    vm.runInContext(source.slice(offset,stop),context);
  }
  evaluate('function saveSessionToStorage()', '// 更新頂部');
  evaluate('function subtitleFingerprint()', 'async function loadAssetLibrary()');
  evaluate('function loadVideoAsset(', '// ---------------- 5.');
  evaluate('function normalizeTrackSegments()', 'function renderSegmentList()');
  return {context,calls,storage};
}
(async()=>{
  const {context:c,calls}=environment();
  await c.openPackage('A');
  assert.equal(c.state.track.segments[0].start,.123);
  assert.equal(c.state.track.segments[0].end,1.456);
  assert.equal(c.el.alignScriptTextarea.value,'A原詞');
  assert.equal(calls.filter(call=>call.url.endsWith('/save')).length,0,'opening must not rewrite the SRT');
  c.state.style.color='red';c.saveSessionToStorage();
  assert.equal(c.timer,null,'style changes must not create disk metadata or rewrite the SRT');
  c.state.track.segments[0].text='編輯到一半';c.saveSessionToStorage();
  assert(c.timer,'editing schedules a disk save');
  await c.openPackage('B');
  const saveIndex=calls.findIndex(call=>call.url.endsWith('/save'));
  const openIndex=calls.findIndex(call=>call.url.endsWith('/open')&&call.payload.path==='B');
  assert(saveIndex>=0&&saveIndex<openIndex,'save A before opening B');
  assert.equal(calls[saveIndex].payload.path,'A');
  assert.equal(calls[saveIndex].payload.track.segments[0].text,'編輯到一半');
  assert.equal(c.state.track.segments.length,0,'a package without SRT clears the previous track');
  assert.equal(c.el.alignScriptTextarea.value,'','a package without lyrics clears the previous lyrics');

  const failure=environment();
  await failure.context.openPackage('A');
  failure.context.state.track.segments[0].text='unsaved';
  const originalFetch=failure.context.fetch;
  failure.context.fetch=async(url,options)=>url.endsWith('/save')?{ok:false,async json(){return {detail:'disk full'}}}:originalFetch(url,options);
  await failure.context.openPackage('B');
  assert.equal(failure.context.state.activePackage.path,'A');
  assert.equal(failure.context.state.track.segments[0].text,'unsaved');
  assert(failure.context.packageHasChanges());

  const concurrent=environment();
  const q=concurrent.context;
  await q.openPackage('A');
  q.state.track.segments[0].text='first';
  const baseFetch=q.fetch;
  let release;
  let count=0;
  const saves=[];
  q.fetch=async(url,options)=>{
    if(url.endsWith('/save')) {
      saves.push(JSON.parse(options.body));
      if(count++===0) await new Promise(resolve=>{release=resolve;});
    }
    return baseFetch(url,options);
  };
  const pending=q.saveActivePackage();
  q.state.track.segments[0].text='latest';
  release();await pending;
  assert.equal(saves.length,2);
  assert.equal(saves[1].track.segments[0].text,'latest','edits during a save must be persisted next');
  assert(!q.packageHasChanges());
  console.log('Package open, autosave, switching, failed-save protection and in-flight edits passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
