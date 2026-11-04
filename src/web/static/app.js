// AutoSubtitle AI Studio - Frontend Application Logic

const state = {
  video: {
    filename: "",
    url: "",
    path: "",
    duration: 0,
    width: 1920,
    height: 1080
  },
  track: {
    version: "1.0.0",
    source_file: "",
    duration: 0,
    language: "zh",
    segments: []
  },
  selectedSegmentIndex: 0,
  style: {
    font_name: "Noto Sans CJK TC",
    font_size: 36,
    primary_color: "#FFFFFF",
    outline_color: "#000000",
    outline_width: 2.5,
    shadow_color: "#000000",
    shadow_offset: 2.0,
    bold: true,
    italic: false,
    letter_spacing: 1.0,
    orientation: "horizontal", // "horizontal" | "vertical"
    vertical_align: "bottom",   // "top" | "middle" | "bottom"
    horizontal_align: "center", // "left" | "center" | "right"
    padding_top: 50,
    padding_bottom: 60,
    padding_left: 40,
    padding_right: 40,
    pos_x: null,
    pos_y: null
  }
};

// DOM 元素引用
const el = {
  video: document.getElementById("main-video"),
  placeholder: document.getElementById("video-placeholder"),
  leftPanel: document.getElementById("left-video-panel"),
  dragDropOverlay: document.getElementById("drag-drop-overlay"),
  overlayContainer: document.getElementById("subtitle-overlay-container"),
  overlay: document.getElementById("subtitle-overlay"),
  scrubber: document.getElementById("video-scrubber"),
  btnPlayPause: document.getElementById("btn-play-pause"),
  iconPlay: document.getElementById("icon-play"),
  iconPause: document.getElementById("icon-pause"),
  timeCurrent: document.getElementById("time-current"),
  timeDuration: document.getElementById("time-duration"),
  volumeSlider: document.getElementById("volume-slider"),
  playbackSpeed: document.getElementById("playback-speed"),
  videoFilename: document.getElementById("video-filename"),
  videoResolutionPill: document.getElementById("video-resolution-pill"),
  mediaBadge: document.getElementById("active-media-badge"),
  segmentCountBadge: document.getElementById("segment-count-badge"),
  logBox: document.getElementById("process-log-box"),

  // Tab 1: 資產管理
  timelineReadyBanner: document.getElementById("timeline-ready-banner"),
  bannerSegCount: document.getElementById("banner-seg-count"),
  inputUploadFiles: document.getElementById("input-upload-files"),
  assetLibraryContainer: document.getElementById("asset-library-container"),
  btnRefreshAssets: document.getElementById("btn-refresh-assets"),
  btnAiTranscribe: document.getElementById("btn-ai-transcribe"),
  btnAiAlign: document.getElementById("btn-ai-align"),
  btnAiProofread: document.getElementById("btn-ai-proofread"),

  // Tab 2: 字幕編輯
  btnAddSegment: document.getElementById("btn-add-segment"),
  btnClearSubtitles: document.getElementById("btn-clear-subtitles"),
  segmentListContainer: document.getElementById("segment-list-container"),
  rawTextContainer: document.getElementById("raw-text-container"),
  rawSubtitleTextarea: document.getElementById("raw-subtitle-textarea"),
  btnApplyRawText: document.getElementById("btn-apply-raw-text"),
  btnViewList: document.getElementById("btn-view-list"),
  btnViewRaw: document.getElementById("btn-view-raw"),
  editorSegCount: document.getElementById("editor-seg-count"),

  // Tab 3: 樣式與位置
  selectSubtitleLine: document.getElementById("select-subtitle-line"),
  selectedSubBadge: document.getElementById("selected-sub-badge"),
  btnOrientH: document.getElementById("btn-orient-h"),
  btnOrientV: document.getElementById("btn-orient-v"),
  sliderPosX: document.getElementById("slider-pos-x"),
  sliderPosY: document.getElementById("slider-pos-y"),
  valPosX: document.getElementById("val-pos-x"),
  valPosY: document.getElementById("val-pos-y"),
  inputPadTop: document.getElementById("input-pad-top"),
  inputPadRight: document.getElementById("input-pad-right"),
  inputPadBottom: document.getElementById("input-pad-bottom"),
  inputPadLeft: document.getElementById("input-pad-left"),
  selectFontName: document.getElementById("select-font-name"),
  sliderFontSize: document.getElementById("slider-font-size"),
  valFontSize: document.getElementById("val-font-size"),
  pickerPrimaryColor: document.getElementById("picker-primary-color"),
  labelPrimaryColor: document.getElementById("label-primary-color"),
  pickerOutlineColor: document.getElementById("picker-outline-color"),
  labelOutlineColor: document.getElementById("label-outline-color"),
  sliderOutlineWidth: document.getElementById("slider-outline-width"),
  valOutlineWidth: document.getElementById("val-outline-width"),
  pickerShadowColor: document.getElementById("picker-shadow-color"),
  labelShadowColor: document.getElementById("label-shadow-color"),
  sliderShadowOffset: document.getElementById("slider-shadow-offset"),
  valShadowOffset: document.getElementById("val-shadow-offset"),
  checkBold: document.getElementById("check-bold"),
  checkItalic: document.getElementById("check-italic"),
  cssLiveCode: document.getElementById("css-live-code"),
  btnCopyCss: document.getElementById("btn-copy-css"),

  // Presets
  presetYoutube: document.getElementById("preset-youtube"),
  presetTiktok: document.getElementById("preset-tiktok"),
  presetClassic: document.getElementById("preset-classic"),
  presetMinimal: document.getElementById("preset-minimal"),

  // Tab 4: 預覽與匯出
  summaryTotalLines: document.getElementById("summary-total-lines"),
  summaryDuration: document.getElementById("summary-duration"),
  btnExportSrt: document.getElementById("btn-export-srt"),
  btnExportVtt: document.getElementById("btn-export-vtt"),
  btnExportJson: document.getElementById("btn-export-json"),
  btnStartBurn: document.getElementById("btn-start-burn"),
  burnResultBox: document.getElementById("burn-result-box"),
  linkDownloadBurned: document.getElementById("link-download-burned"),
  btnPreviewBurned: document.getElementById("btn-preview-burned"),
};

// 輔助日誌輸出
function addLog(msg, type = "info") {
  const time = new Date().toLocaleTimeString();
  const colorClass = type === "error" ? "text-red-400 font-semibold" : (type === "success" ? "text-emerald-400 font-semibold" : "text-zinc-300");
  const div = document.createElement("div");
  div.className = colorClass;
  div.textContent = `[${time}] ${msg}`;
  el.logBox.appendChild(div);
  el.logBox.scrollTop = el.logBox.scrollHeight;
}

// 格式化秒數為 mm:ss.ms
function formatTime(sec) {
  if (isNaN(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 100);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
}

// ---------------- 1. 影音播放器事件 ----------------
function initPlayer() {
  const v = el.video;

  // 播放 / 暫停按鈕
  el.btnPlayPause.addEventListener("click", () => {
    if (v.paused) v.play();
    else v.pause();
  });

  v.addEventListener("play", () => {
    el.iconPlay.classList.add("hidden");
    el.iconPause.classList.remove("hidden");
  });

  v.addEventListener("pause", () => {
    el.iconPlay.classList.remove("hidden");
    el.iconPause.classList.add("hidden");
  });

  // 時間與進度條更新
  v.addEventListener("timeupdate", () => {
    el.timeCurrent.textContent = formatTime(v.currentTime);
    if (v.duration) {
      el.scrubber.value = (v.currentTime / v.duration) * 100;
    }
    updateSubtitleOverlayOnTime(v.currentTime);
  });

  v.addEventListener("loadedmetadata", () => {
    el.timeDuration.textContent = formatTime(v.duration);
    state.video.duration = v.duration;
    state.video.width = v.videoWidth || 1920;
    state.video.height = v.videoHeight || 1080;

    // 計算原生長寬比與標籤
    const ratio = state.video.width / state.video.height;
    let ratioDesc = "";
    if (Math.abs(ratio - (16/9)) < 0.05) ratioDesc = " (16:9 橫式)";
    else if (Math.abs(ratio - (9/16)) < 0.05) ratioDesc = " (9:16 直式)";
    else if (Math.abs(ratio - (4/3)) < 0.05) ratioDesc = " (4:3)";
    else if (Math.abs(ratio - 1.0) < 0.05) ratioDesc = " (1:1 正方)";
    else if (ratio < 0.9) ratioDesc = " (直式)";
    else ratioDesc = " (橫式)";

    el.videoResolutionPill.textContent = `${state.video.width}x${state.video.height}${ratioDesc}`;
    el.videoResolutionPill.classList.remove("hidden");
    el.placeholder.classList.add("hidden");
    updateSummary();

    // 重新計算字型與座標縮放比，確保預覽與實體影片原樣 100% 貼合
    applySubtitleStyleToOverlay();
  });

  // 監聽視窗或影片尺寸變更，即時維持等比錨定
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(() => {
      applySubtitleStyleToOverlay();
    });
    ro.observe(el.video);
  } else {
    window.addEventListener("resize", () => {
      applySubtitleStyleToOverlay();
    });
  }

  // 進度拖曳
  el.scrubber.addEventListener("input", (e) => {
    if (v.duration) {
      v.currentTime = (e.target.value / 100) * v.duration;
    }
  });

  // 快進快退
  document.getElementById("btn-seek-backward").addEventListener("click", () => { v.currentTime = Math.max(0, v.currentTime - 3); });
  document.getElementById("btn-seek-forward").addEventListener("click", () => { v.currentTime = Math.min(v.duration, v.currentTime + 3); });

  // 音量與倍速
  el.volumeSlider.addEventListener("input", (e) => { v.volume = parseFloat(e.target.value); });
  el.playbackSpeed.addEventListener("change", (e) => { v.playbackRate = parseFloat(e.target.value); });

  // 全螢幕
  document.getElementById("btn-fullscreen").addEventListener("click", () => {
    if (!document.fullscreenElement) {
      el.video.parentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  });
}

// 取得預覽畫面相對於影片原生實體解析度的縮放比例
function getPreviewScale() {
  const v = el.video;
  if (!v || !v.videoHeight || !v.clientHeight) return 1.0;
  return v.clientHeight / v.videoHeight;
}

// ---------------- 2. 即時字幕覆蓋層渲染 (CSS Box Model) ----------------
function applySubtitleStyleToOverlay() {
  const s = state.style;
  const overlay = el.overlay;
  const container = el.overlayContainer;
  const scale = getPreviewScale();

  // 1. 盒模型對齊
  if (s.vertical_align === "top") container.style.alignItems = "flex-start";
  else if (s.vertical_align === "middle") container.style.alignItems = "center";
  else container.style.alignItems = "flex-end";

  if (s.horizontal_align === "left") container.style.justifyContent = "flex-start";
  else if (s.horizontal_align === "right") container.style.justifyContent = "flex-end";
  else container.style.justifyContent = "center";

  // 等比縮放內距 (Padding) 邊界，確保在任何解析度下與影片邊緣距離一致
  const padTop = Math.round(s.padding_top * scale);
  const padRight = Math.round(s.padding_right * scale);
  const padBottom = Math.round(s.padding_bottom * scale);
  const padLeft = Math.round(s.padding_left * scale);

  container.style.paddingTop = `${padTop}px`;
  container.style.paddingRight = `${padRight}px`;
  container.style.paddingBottom = `${padBottom}px`;
  container.style.paddingLeft = `${padLeft}px`;

  // 2. 文字外觀與特效 (依據影片原生解析度等比縮放)
  const fontSize = Math.max(10, Math.round(s.font_size * scale));
  const outlineWidth = Math.max(0.5, (s.outline_width * scale).toFixed(1));
  const shadowDist = (s.shadow_offset * scale).toFixed(1);

  overlay.style.fontFamily = `"${s.font_name}", sans-serif`;
  overlay.style.fontSize = `${fontSize}px`;
  overlay.style.color = s.primary_color;
  overlay.style.fontWeight = s.bold ? "bold" : "normal";
  overlay.style.fontStyle = s.italic ? "italic" : "normal";
  overlay.style.letterSpacing = `${(s.letter_spacing * scale).toFixed(1)}px`;

  // 描邊字
  overlay.style.webkitTextStroke = `${outlineWidth}px ${s.outline_color}`;

  // 陰影字
  overlay.style.textShadow = `${shadowDist}px ${shadowDist}px ${shadowDist * 1.5}px ${s.shadow_color}`;

  // 直排 / 橫排
  if (s.orientation === "vertical") {
    overlay.style.writingMode = "vertical-rl";
    overlay.style.textAlign = s.vertical_align === "top" ? "start" : (s.vertical_align === "bottom" ? "end" : "center");
  } else {
    overlay.style.writingMode = "horizontal-tb";
    overlay.style.textAlign = s.horizontal_align;
  }

  updateCssCodeBox();
}

function updateCssCodeBox() {
  const s = state.style;
  const writingMode = s.orientation === "vertical" ? "vertical-rl" : "horizontal-tb";
  const css = `/* Subtitle Web CSS Preset */
font-family: '${s.font_name}', sans-serif;
font-size: ${s.font_size}px;
color: ${s.primary_color};
font-weight: ${s.bold ? 'bold' : 'normal'};
font-style: ${s.italic ? 'italic' : 'normal'};
-webkit-text-stroke: ${s.outline_width}px ${s.outline_color};
text-shadow: ${s.shadow_offset}px ${s.shadow_offset}px ${(s.shadow_offset*1.5).toFixed(1)}px ${s.shadow_color};
writing-mode: ${writingMode};
text-align: ${s.horizontal_align};
vertical-align: ${s.vertical_align};
padding: ${s.padding_top}px ${s.padding_right}px ${s.padding_bottom}px ${s.padding_left}px;
letter-spacing: ${s.letter_spacing}px;`;

  el.cssLiveCode.value = css;
}

// 根據時間戳更新字幕
function updateSubtitleOverlayOnTime(currentTime) {
  if (!state.track.segments || state.track.segments.length === 0) {
    el.overlay.textContent = "";
    return;
  }

  const activeSeg = state.track.segments.find(seg => currentTime >= seg.start && currentTime <= seg.end);

  if (activeSeg) {
    renderOverlayText(activeSeg.text);
    highlightActiveSegmentInList(activeSeg.id);
  } else {
    if (el.video.paused && state.selectedSegmentIndex >= 0 && state.track.segments[state.selectedSegmentIndex]) {
      renderOverlayText(state.track.segments[state.selectedSegmentIndex].text);
    } else {
      el.overlay.textContent = "";
    }
  }
}

function renderOverlayText(text) {
  el.overlay.textContent = text;
}

// ---------------- 3. Tab 切換 ----------------
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.tab;

      document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.remove("border-blue-500", "text-blue-400", "font-semibold", "bg-zinc-800/40");
        b.classList.add("border-transparent", "text-zinc-400");
      });
      btn.classList.add("border-blue-500", "text-blue-400", "font-semibold", "bg-zinc-800/40");
      btn.classList.remove("border-transparent", "text-zinc-400");

      document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.add("hidden"));
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.remove("hidden");

      if (targetId === "tab-style") {
        updateSubtitleSelectDropdown();
        applySubtitleStyleToOverlay();
      }
    });
  });
}

// ---------------- 4. Tab 1: 資產媒體庫 (Asset Library) 與全域拖放 ----------------
async function loadAssetLibrary() {
  const container = el.assetLibraryContainer;
  container.innerHTML = `<div class="text-xs text-zinc-500 py-3 text-center">正在讀取資產庫...</div>`;

  try {
    const res = await fetch("/api/assets");
    const data = await res.json();
    const assets = data.assets || [];

    if (!assets.length) {
      container.innerHTML = `<div class="text-xs text-zinc-500 py-4 text-center">資產庫目前為空，請拖入或上傳檔案</div>`;
      return;
    }

    container.innerHTML = "";
    assets.forEach(asset => {
      const isUpload = asset.folder === "uploads";
      const card = document.createElement("div");
      card.className = "flex items-center justify-between p-2 bg-zinc-900/80 hover:bg-zinc-800/90 rounded border border-zinc-800 text-xs transition";

      // 類型圖示
      let icon = "📄";
      if (asset.type === "video") icon = "🎬";
      else if (asset.type === "subtitle") icon = "📝";
      else if (asset.type === "audio") icon = "🎵";

      const badgeColor = isUpload ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-zinc-700/30 text-zinc-400 border-zinc-700/50";
      const sourceTag = isUpload ? "已上傳" : "內建模擬";

      card.innerHTML = `
        <div class="flex items-center gap-2 overflow-hidden flex-1 mr-2">
          <span class="text-base">${icon}</span>
          <div class="truncate">
            <div class="font-medium text-zinc-200 truncate flex items-center gap-1.5">
              <span>${asset.name}</span>
              <span class="text-[9px] px-1.5 py-0.2 rounded border ${badgeColor}">${sourceTag}</span>
            </div>
            <div class="text-[10px] text-zinc-500 font-mono">${asset.size_mb} MB • ${asset.type.toUpperCase()}</div>
          </div>
        </div>

        <div class="flex items-center gap-1 shrink-0">
          ${asset.type === "video" ? `
            <button class="btn-load-this-video px-2 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded text-[11px] transition">
              ▶ 載入影片
            </button>
            ${asset.paired_subtitle ? `
              <button class="btn-load-paired-all px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-[11px] transition" title="同時載入影片與同名字幕">
                ⚡ 同步載入
              </button>
            ` : ''}
          ` : ''}

          ${asset.type === "subtitle" ? `
            <button class="btn-load-this-sub px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-[11px] transition">
              📝 載入時間軸
            </button>
          ` : ''}

          ${isUpload ? `
            <button class="btn-delete-asset px-1.5 py-1 text-zinc-500 hover:text-red-400 rounded text-[11px]" title="刪除檔案">✕</button>
          ` : ''}
        </div>
      `;

      // 載入影片
      const btnVideo = card.querySelector(".btn-load-this-video");
      if (btnVideo) {
        btnVideo.addEventListener("click", () => {
          loadVideoAsset(asset);
        });
      }

      // 載入成對影片與字幕
      const btnPaired = card.querySelector(".btn-load-paired-all");
      if (btnPaired && asset.paired_subtitle) {
        btnPaired.addEventListener("click", async () => {
          loadVideoAsset(asset);
          await loadSubtitleAsset(asset.paired_subtitle);
          addLog(`⚡ 已同步載入 ${asset.name} 及其成對時間軸字幕！`, "success");
        });
      }

      // 載入字幕
      const btnSub = card.querySelector(".btn-load-this-sub");
      if (btnSub) {
        btnSub.addEventListener("click", () => {
          loadSubtitleAsset(asset);
        });
      }

      // 刪除資產
      const btnDel = card.querySelector(".btn-delete-asset");
      if (btnDel) {
        btnDel.addEventListener("click", async () => {
          if (confirm(`確定要從伺服器刪除 ${asset.name} 嗎？`)) {
            await fetch(`/api/assets/${encodeURIComponent(asset.name)}`, { method: "DELETE" });
            addLog(`已刪除資產: ${asset.name}`, "info");
            loadAssetLibrary();
          }
        });
      }

      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = `<div class="text-xs text-red-400 py-3 text-center">讀取資產庫失敗: ${err.message}</div>`;
  }
}

function loadVideoAsset(asset) {
  state.video.filename = asset.name;
  state.video.url = asset.url;
  state.video.path = asset.absolute_path;
  el.video.src = asset.url;
  el.videoFilename.textContent = asset.name;
  el.mediaBadge.textContent = asset.name;
  el.placeholder.classList.add("hidden");
  addLog(`已成功載入影片: ${asset.name}`, "success");
}

async function loadSubtitleAsset(asset) {
  try {
    const res = await fetch(asset.url);
    const content = await res.text();
    parseAndSetSrt(content, asset.name);
    addLog(`✔ 現成時間軸字幕已直接載入: ${asset.name} (共 ${state.track.segments.length} 句)`, "success");
  } catch (err) {
    addLog(`載入字幕失敗: ${err.message}`, "error");
  }
}

// ---------------- 5. 檔案上傳與全域拖放 (Drag & Drop) ----------------
async function handleBatchFileUpload(files) {
  if (!files || !files.length) return;

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  addLog(`正在上傳 ${files.length} 個檔案至資產庫...`);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (data.status === "success") {
      addLog(`✔ 上傳成功: 共儲存 ${data.uploaded.length} 個檔案`, "success");

      // 1. 若有上傳影片，立即載入最新影片至播放器
      if (data.videos && data.videos.length > 0) {
        const v = data.videos[0];
        loadVideoAsset({
          name: v.name,
          url: v.url,
          absolute_path: v.absolute_path
        });
      }

      // 2. 【關鍵功能】若上傳包含 SRT / VTT 字幕，直接載入時間軸！
      if (data.tracks && data.tracks.length > 0) {
        const t = data.tracks[0];
        setSubtitleTrack(t.track);
        addLog(`🎉 偵測到現成時間軸字幕 (${t.filename})！已直接載入時間軸 (共 ${t.track.segments.length} 句)，無需重複 AI 辨識！`, "success");

        // 自動定位播放器至第 1 句字幕
        if (t.track.segments.length > 0) {
          el.video.currentTime = t.track.segments[0].start;
          renderOverlayText(t.track.segments[0].text);
        }
      }

      // 刷新資產庫
      loadAssetLibrary();
    } else {
      throw new Error(data.detail || "上傳失敗");
    }
  } catch (err) {
    addLog(`上傳失敗: ${err.message}`, "error");
  }
}

function initUniversalDragAndDrop() {
  const panel = el.leftPanel;
  const overlay = el.dragDropOverlay;

  // 阻止瀏覽器預設開啟行為
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    window.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  // 拖入時高亮
  window.addEventListener('dragover', (e) => {
    overlay.classList.remove('hidden');
  });

  overlay.addEventListener('dragleave', (e) => {
    overlay.classList.add('hidden');
  });

  window.addEventListener('drop', (e) => {
    overlay.classList.add('hidden');
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      handleBatchFileUpload(dt.files);
    }
  });

  // 點擊上傳按鈕事件 (多選)
  el.inputUploadFiles.addEventListener("change", (e) => {
    handleBatchFileUpload(e.target.files);
  });

  // 重新整理資產庫
  el.btnRefreshAssets.addEventListener("click", () => {
    loadAssetLibrary();
    addLog("已重新整理資產庫", "info");
  });
}

// ---------------- 6. AI 功能按鈕 ----------------
function initAiButtons() {
  // AI 自動辨識
  el.btnAiTranscribe.addEventListener("click", async () => {
    const media = state.video.path;
    if (!media) {
      addLog("請先載入或上傳影片後再執行辨識", "error");
      return;
    }

    addLog(`【AI 辨識】正在以 Whisper 辨識 ${state.video.filename}...`);
    el.btnAiTranscribe.disabled = true;
    el.btnAiTranscribe.textContent = "⏳ Whisper 語音辨識中...";

    const formData = new FormData();
    formData.append("media_path", media);
    formData.append("model", "small");
    formData.append("device", "cuda");
    formData.append("prompt", "繁體中文");

    try {
      const res = await fetch("/api/ai/transcribe", { method: "POST", body: formData });
      const data = await res.json();
      if (data.status === "success") {
        setSubtitleTrack(data.track);
        addLog(`【AI 辨識完成】生成 ${data.track.segments.length} 句字幕`, "success");
      } else {
        throw new Error(data.detail || "辨識失敗");
      }
    } catch (err) {
      addLog(`辨識失敗: ${err.message}`, "error");
    } finally {
      el.btnAiTranscribe.disabled = false;
      el.btnAiTranscribe.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>【AI 本地辨識】使用 Whisper 從影片提取音軌並自動切分`;
    }
  });

  // 有稿強制對齊
  el.btnAiAlign.addEventListener("click", async () => {
    const media = state.video.path;
    if (!media) {
      addLog("請先載入影片後再執行對齊", "error");
      return;
    }
    const script = sessionStorage.getItem("current_script_text") || "inputclip/audio-org.txt";
    addLog(`【有稿對齊】正在將原稿與音軌強制對齊...`);
    el.btnAiAlign.disabled = true;

    try {
      const res = await fetch("/api/ai/align", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ media_path: media, script_path: script })
      });
      const data = await res.json();
      if (data.status === "success") {
        setSubtitleTrack(data.track);
        addLog(`【有稿對齊成功】生成 ${data.track.segments.length} 句 100% 原稿時間軸字幕！`, "success");
      } else {
        throw new Error(data.detail || "對齊失敗");
      }
    } catch (err) {
      addLog(`對齊失敗: ${err.message}`, "error");
    } finally {
      el.btnAiAlign.disabled = false;
    }
  });

  // 無稿 Edge LLM 校對
  el.btnAiProofread.addEventListener("click", async () => {
    if (!state.track.segments.length) {
      addLog("請先載入或生成字幕後再執行校對", "error");
      return;
    }
    addLog(`【Edge LLM 校對】啟動本地 Qwen2.5 進行錯別字校正...`);
    el.btnAiProofread.disabled = true;

    try {
      const res = await fetch("/api/ai/proofread", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track: state.track, batch_size: 8 })
      });
      const data = await res.json();
      if (data.status === "success") {
        setSubtitleTrack(data.track);
        addLog(`【校對完成】字幕已自動修正同音字與標點！`, "success");
      } else {
        throw new Error(data.detail || "校對失敗");
      }
    } catch (err) {
      addLog(`校對失敗: ${err.message}`, "error");
    } finally {
      el.btnAiProofread.disabled = false;
    }
  });
}

// 簡易 SRT 解析器 (客戶端備援)
function parseAndSetSrt(srtContent, sourceName = "manual") {
  const blocks = srtContent.trim().split(/\r?\n\s*\r?\n/);
  const segments = [];

  blocks.forEach((block, idx) => {
    const lines = block.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    if (lines.length >= 2) {
      let timeLineIdx = -1;
      let sId = idx + 1;
      for (let i = 0; i < Math.min(3, lines.length); i++) {
        if (lines[i].includes("-->")) {
          timeLineIdx = i;
          break;
        }
      }

      if (timeLineIdx !== -1) {
        if (timeLineIdx > 0 && !isNaN(parseInt(lines[0], 10))) {
          sId = parseInt(lines[0], 10);
        }
        const timeMatch = lines[timeLineIdx].match(/(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)/);
        if (timeMatch) {
          const parseT = (str) => {
            str = str.replace(',', '.');
            const [h, m, s] = str.split(':');
            return parseFloat(h) * 3600 + parseFloat(m) * 60 + parseFloat(s);
          };
          const start = parseT(timeMatch[1]);
          const end = parseT(timeMatch[2]);
          const text = lines.slice(timeLineIdx + 1).join(" ");
          segments.push({ id: sId, start, end, text, words: [] });
        }
      }
    }
  });

  setSubtitleTrack({
    version: "1.0.0",
    source_file: sourceName,
    duration: segments.length ? segments[segments.length - 1].end : 0,
    language: "zh",
    segments: segments
  });
}

// ---------------- 7. Tab 2: 字幕管理編輯器 ----------------
function setSubtitleTrack(track) {
  state.track = track;
  el.segmentCountBadge.textContent = `${track.segments.length} 句字幕`;
  el.editorSegCount.textContent = track.segments.length;
  renderSegmentList();
  updateSubtitleSelectDropdown();
  updateSummary();

  // 顯示時間軸就緒提示
  if (track.segments.length > 0) {
    el.timelineReadyBanner.classList.remove("hidden");
    el.bannerSegCount.textContent = track.segments.length;
    state.selectedSegmentIndex = 0;
  } else {
    el.timelineReadyBanner.classList.add("hidden");
  }
}

function renderSegmentList() {
  const container = el.segmentListContainer;
  container.innerHTML = "";

  if (!state.track.segments.length) {
    container.innerHTML = `<div class="text-center py-10 text-xs text-zinc-500">尚無字幕資料，可直接拖入 SRT 或至【資產管理】載入</div>`;
    return;
  }

  el.rawSubtitleTextarea.value = state.track.segments.map(s => s.text).join("\n");

  state.track.segments.forEach((seg, idx) => {
    const card = document.createElement("div");
    card.id = `seg-card-${seg.id}`;
    card.className = "p-2.5 bg-zinc-950/70 border border-zinc-800 rounded-lg hover:border-zinc-700 transition flex flex-col gap-1.5 text-xs";

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono text-[10px]">#${seg.id}</span>
          <span class="font-mono text-zinc-400 text-[11px]">${seg.start.toFixed(2)}s ➔ ${seg.end.toFixed(2)}s</span>
        </div>
        <div class="flex items-center gap-1">
          <button class="btn-play-seg px-1.5 py-0.5 bg-zinc-800 hover:bg-zinc-700 text-blue-400 rounded text-[11px]" title="定位播放此段">▶ 試聽</button>
          <button class="btn-del-seg px-1.5 py-0.5 hover:bg-red-950/40 text-red-400 rounded text-[11px]" title="刪除此句">✕</button>
        </div>
      </div>
      <input type="text" class="seg-text-input w-full bg-zinc-900 border border-zinc-800/80 rounded px-2 py-1 text-zinc-200 text-xs focus:outline-none focus:border-blue-500" value="${seg.text}">
    `;

    card.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") {
        selectAndJumpToSegment(idx);
      }
    });

    card.querySelector(".btn-play-seg").addEventListener("click", () => {
      selectAndJumpToSegment(idx);
      el.video.currentTime = seg.start;
      el.video.play();
    });

    card.querySelector(".seg-text-input").addEventListener("input", (e) => {
      seg.text = e.target.value;
      if (state.selectedSegmentIndex === idx) {
        renderOverlayText(seg.text);
      }
    });

    card.querySelector(".btn-del-seg").addEventListener("click", () => {
      state.track.segments.splice(idx, 1);
      renderSegmentList();
      updateSubtitleSelectDropdown();
      updateSummary();
    });

    container.appendChild(card);
  });
}

function highlightActiveSegmentInList(segId) {
  document.querySelectorAll("#segment-list-container > div").forEach(c => c.classList.remove("border-blue-500", "bg-blue-950/20"));
  const activeCard = document.getElementById(`seg-card-${segId}`);
  if (activeCard) {
    activeCard.classList.add("border-blue-500", "bg-blue-950/20");
  }
}

function selectAndJumpToSegment(index) {
  state.selectedSegmentIndex = index;
  const seg = state.track.segments[index];
  if (seg) {
    el.video.currentTime = seg.start;
    renderOverlayText(seg.text);
    highlightActiveSegmentInList(seg.id);
    el.selectedSubBadge.textContent = `目前選擇: 第 ${seg.id} 句 (${seg.start.toFixed(2)}s)`;
    el.selectSubtitleLine.value = String(index);
  }
}

function initEditorViewToggle() {
  el.btnViewList.addEventListener("click", () => {
    el.segmentListContainer.classList.remove("hidden");
    el.rawTextContainer.classList.add("hidden");
    el.btnViewList.className = "text-blue-400 font-semibold underline";
    el.btnViewRaw.className = "text-zinc-500 hover:text-zinc-300";
  });

  el.btnViewRaw.addEventListener("click", () => {
    el.segmentListContainer.classList.add("hidden");
    el.rawTextContainer.classList.remove("hidden");
    el.btnViewRaw.className = "text-blue-400 font-semibold underline";
    el.btnViewList.className = "text-zinc-500 hover:text-zinc-300";
  });

  el.btnApplyRawText.addEventListener("click", () => {
    const lines = el.rawSubtitleTextarea.value.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length === state.track.segments.length) {
      lines.forEach((l, i) => { state.track.segments[i].text = l; });
      renderSegmentList();
      addLog("全文文字已更新至時間軸！", "success");
    } else {
      addLog(`行數 (${lines.length}) 與現有時間軸 (${state.track.segments.length}) 不一致，建議在資產管理重新斷句`, "error");
    }
  });

  el.btnAddSegment.addEventListener("click", () => {
    const curTime = el.video.currentTime || 0;
    const newId = state.track.segments.length + 1;
    state.track.segments.push({
      id: newId,
      start: curTime,
      end: curTime + 2.5,
      text: "新字幕文字",
      words: []
    });
    renderSegmentList();
    updateSubtitleSelectDropdown();
    addLog(`新增字幕段 #${newId}`, "info");
  });

  el.btnClearSubtitles.addEventListener("click", () => {
    if (confirm("確定要清空所有字幕嗎？")) {
      setSubtitleTrack({ ...state.track, segments: [] });
      addLog("已清空字幕", "info");
    }
  });
}

// ---------------- 8. Tab 3: 字幕樣式與逐行選擇控件 ----------------
function updateSubtitleSelectDropdown() {
  const sel = el.selectSubtitleLine;
  sel.innerHTML = "";

  if (!state.track.segments.length) {
    sel.innerHTML = `<option value="0">尚無字幕</option>`;
    return;
  }

  state.track.segments.forEach((seg, idx) => {
    const opt = document.createElement("option");
    opt.value = String(idx);
    opt.textContent = `#${seg.id} [${formatTime(seg.start)}]: ${seg.text}`;
    if (idx === state.selectedSegmentIndex) opt.selected = true;
    sel.appendChild(opt);
  });
}

function initStyleEditor() {
  el.selectSubtitleLine.addEventListener("change", (e) => {
    const idx = parseInt(e.target.value, 10);
    selectAndJumpToSegment(idx);
  });

  el.btnOrientH.addEventListener("click", () => {
    state.style.orientation = "horizontal";
    el.btnOrientH.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
    el.btnOrientV.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
    applySubtitleStyleToOverlay();
  });

  el.btnOrientV.addEventListener("click", () => {
    state.style.orientation = "vertical";
    el.btnOrientV.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
    el.btnOrientH.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
    applySubtitleStyleToOverlay();
  });

  document.querySelectorAll(".grid-align-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".grid-align-btn").forEach(b => {
        b.classList.remove("bg-blue-600", "text-white");
        b.classList.add("bg-zinc-800");
      });
      btn.classList.add("bg-blue-600", "text-white");
      btn.classList.remove("bg-zinc-800");

      state.style.vertical_align = btn.dataset.valign;
      state.style.horizontal_align = btn.dataset.halign;
      applySubtitleStyleToOverlay();
    });
  });

  el.sliderPosX.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    if (val < 33) {
      state.style.horizontal_align = "left";
      state.style.padding_left = Math.max(10, val * 4);
      el.valPosX.textContent = `靠左 (${state.style.padding_left}px)`;
    } else if (val > 66) {
      state.style.horizontal_align = "right";
      state.style.padding_right = Math.max(10, (100 - val) * 4);
      el.valPosX.textContent = `靠右 (${state.style.padding_right}px)`;
    } else {
      state.style.horizontal_align = "center";
      el.valPosX.textContent = "水平置中";
    }
    applySubtitleStyleToOverlay();
  });

  el.sliderPosY.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    if (val < 33) {
      state.style.vertical_align = "bottom";
      state.style.padding_bottom = Math.max(20, val * 5);
      el.valPosY.textContent = `靠底 (${state.style.padding_bottom}px)`;
    } else if (val > 66) {
      state.style.vertical_align = "top";
      state.style.padding_top = Math.max(20, (100 - val) * 5);
      el.valPosY.textContent = `齊頭頂部 (${state.style.padding_top}px)`;
    } else {
      state.style.vertical_align = "middle";
      el.valPosY.textContent = "垂直置中";
    }
    applySubtitleStyleToOverlay();
  });

  el.inputPadTop.addEventListener("input", (e) => { state.style.padding_top = parseInt(e.target.value, 10) || 0; applySubtitleStyleToOverlay(); });
  el.inputPadRight.addEventListener("input", (e) => { state.style.padding_right = parseInt(e.target.value, 10) || 0; applySubtitleStyleToOverlay(); });
  el.inputPadBottom.addEventListener("input", (e) => { state.style.padding_bottom = parseInt(e.target.value, 10) || 0; applySubtitleStyleToOverlay(); });
  el.inputPadLeft.addEventListener("input", (e) => { state.style.padding_left = parseInt(e.target.value, 10) || 0; applySubtitleStyleToOverlay(); });

  el.selectFontName.addEventListener("change", (e) => { state.style.font_name = e.target.value; applySubtitleStyleToOverlay(); });
  el.sliderFontSize.addEventListener("input", (e) => {
    state.style.font_size = parseInt(e.target.value, 10);
    el.valFontSize.textContent = `${state.style.font_size}px`;
    applySubtitleStyleToOverlay();
  });

  el.pickerPrimaryColor.addEventListener("input", (e) => {
    state.style.primary_color = e.target.value.toUpperCase();
    el.labelPrimaryColor.textContent = state.style.primary_color;
    applySubtitleStyleToOverlay();
  });

  el.checkBold.addEventListener("change", (e) => { state.style.bold = e.target.checked; applySubtitleStyleToOverlay(); });
  el.checkItalic.addEventListener("change", (e) => { state.style.italic = e.target.checked; applySubtitleStyleToOverlay(); });

  el.pickerOutlineColor.addEventListener("input", (e) => {
    state.style.outline_color = e.target.value.toUpperCase();
    el.labelOutlineColor.textContent = state.style.outline_color;
    applySubtitleStyleToOverlay();
  });
  el.sliderOutlineWidth.addEventListener("input", (e) => {
    state.style.outline_width = parseFloat(e.target.value);
    el.valOutlineWidth.textContent = `${state.style.outline_width}px`;
    applySubtitleStyleToOverlay();
  });

  el.pickerShadowColor.addEventListener("input", (e) => {
    state.style.shadow_color = e.target.value.toUpperCase();
    el.labelShadowColor.textContent = state.style.shadow_color;
    applySubtitleStyleToOverlay();
  });
  el.sliderShadowOffset.addEventListener("input", (e) => {
    state.style.shadow_offset = parseFloat(e.target.value);
    el.valShadowOffset.textContent = `${state.style.shadow_offset}px`;
    applySubtitleStyleToOverlay();
  });

  el.btnCopyCss.addEventListener("click", () => {
    navigator.clipboard.writeText(el.cssLiveCode.value);
    el.btnCopyCss.textContent = "已複製 ✔";
    setTimeout(() => { el.btnCopyCss.textContent = "複製 CSS"; }, 1500);
  });

  el.cssLiveCode.addEventListener("change", async (e) => {
    try {
      const res = await fetch("/api/style/parse-css", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ css: e.target.value })
      });
      const data = await res.json();
      if (data.status === "success") {
        Object.assign(state.style, data.style);
        syncStateToControls();
        applySubtitleStyleToOverlay();
        addLog("已由自訂 CSS 更新樣式參數", "info");
      }
    } catch (err) {
      addLog(`CSS 解析錯誤: ${err.message}`, "error");
    }
  });

  initPresets();
}

function syncStateToControls() {
  const s = state.style;
  el.sliderFontSize.value = s.font_size;
  el.valFontSize.textContent = `${s.font_size}px`;
  el.pickerPrimaryColor.value = s.primary_color;
  el.labelPrimaryColor.textContent = s.primary_color;
  el.pickerOutlineColor.value = s.outline_color;
  el.labelOutlineColor.textContent = s.outline_color;
  el.sliderOutlineWidth.value = s.outline_width;
  el.valOutlineWidth.textContent = `${s.outline_width}px`;
  el.pickerShadowColor.value = s.shadow_color;
  el.labelShadowColor.textContent = s.shadow_color;
  el.sliderShadowOffset.value = s.shadow_offset;
  el.valShadowOffset.textContent = `${s.shadow_offset}px`;
  el.checkBold.checked = s.bold;
  el.checkItalic.checked = s.italic;
  el.inputPadTop.value = s.padding_top;
  el.inputPadRight.value = s.padding_right;
  el.inputPadBottom.value = s.padding_bottom;
  el.inputPadLeft.value = s.padding_left;

  if (s.orientation === "vertical") {
    el.btnOrientV.click();
  } else {
    el.btnOrientH.click();
  }
}

function initPresets() {
  el.presetYoutube.addEventListener("click", () => {
    Object.assign(state.style, {
      font_size: 38,
      primary_color: "#FFD700",
      outline_color: "#000000",
      outline_width: 3.2,
      shadow_color: "#000000",
      shadow_offset: 2.5,
      bold: true,
      orientation: "horizontal",
      vertical_align: "bottom",
      horizontal_align: "center",
      padding_bottom: 60
    });
    syncStateToControls();
    applySubtitleStyleToOverlay();
  });

  el.presetTiktok.addEventListener("click", () => {
    Object.assign(state.style, {
      font_size: 34,
      primary_color: "#FFFFFF",
      outline_color: "#111111",
      outline_width: 2.5,
      shadow_color: "#000000",
      shadow_offset: 2.0,
      bold: true,
      orientation: "vertical",
      vertical_align: "top",
      horizontal_align: "right",
      padding_top: 60,
      padding_right: 60
    });
    syncStateToControls();
    applySubtitleStyleToOverlay();
  });

  el.presetClassic.addEventListener("click", () => {
    Object.assign(state.style, {
      font_size: 32,
      primary_color: "#FFFFFF",
      outline_color: "#000000",
      outline_width: 2.0,
      shadow_color: "#000000",
      shadow_offset: 1.5,
      bold: true,
      orientation: "horizontal",
      vertical_align: "bottom",
      horizontal_align: "center",
      padding_bottom: 50
    });
    syncStateToControls();
    applySubtitleStyleToOverlay();
  });

  el.presetMinimal.addEventListener("click", () => {
    Object.assign(state.style, {
      font_size: 30,
      primary_color: "#E2E8F0",
      outline_color: "#0F172A",
      outline_width: 1.5,
      shadow_color: "#000000",
      shadow_offset: 1.0,
      bold: false,
      orientation: "horizontal",
      vertical_align: "bottom",
      horizontal_align: "center",
      padding_bottom: 45
    });
    syncStateToControls();
    applySubtitleStyleToOverlay();
  });
}

// ---------------- 9. Tab 4: 預覽與匯出 ----------------
function updateSummary() {
  el.summaryTotalLines.textContent = `${state.track.segments.length} 句`;
  el.summaryDuration.textContent = `${state.video.duration.toFixed(2)} 秒`;
}

function initExport() {
  function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  el.btnExportSrt.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    let srt = "";
    state.track.segments.forEach((seg, i) => {
      const formatSrtTime = (t) => {
        const sec = Math.max(0, t);
        const hrs = Math.floor(sec / 3600);
        const mins = Math.floor((sec % 3600) / 60);
        const secs = Math.floor(sec % 60);
        const ms = Math.floor((sec % 1) * 1000);
        return `${String(hrs).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')},${String(ms).padStart(3,'0')}`;
      };
      srt += `${i + 1}\n${formatSrtTime(seg.start)} --> ${formatSrtTime(seg.end)}\n${seg.text}\n\n`;
    });
    downloadTextFile(srt, "subtitles.srt");
    addLog("已匯出 subtitles.srt", "success");
  });

  el.btnExportVtt.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    let vtt = "WEBVTT\n\n";
    state.track.segments.forEach((seg, i) => {
      const formatVttTime = (t) => {
        const sec = Math.max(0, t);
        const hrs = Math.floor(sec / 3600);
        const mins = Math.floor((sec % 3600) / 60);
        const secs = Math.floor(sec % 60);
        const ms = Math.floor((sec % 1) * 1000);
        return `${String(hrs).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}.${String(ms).padStart(3,'0')}`;
      };
      vtt += `${i + 1}\n${formatVttTime(seg.start)} --> ${formatVttTime(seg.end)}\n${seg.text}\n\n`;
    });
    downloadTextFile(vtt, "subtitles.vtt");
    addLog("已匯出 subtitles.vtt", "success");
  });

  el.btnExportJson.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    downloadTextFile(JSON.stringify(state.track, null, 2), "subtitles.json");
    addLog("已匯出 subtitles.json", "success");
  });

  el.btnStartBurn.addEventListener("click", async () => {
    const videoPath = state.video.path;
    if (!videoPath) {
      addLog("請先載入或上傳影片後再執行壓制", "error");
      return;
    }
    if (!state.track.segments.length) {
      addLog("請先載入或生成字幕後再執行壓制", "error");
      return;
    }

    addLog(`【影音壓制】啟動 NVIDIA NVENC 壓制燒錄影片至 ${videoPath}...`);
    el.btnStartBurn.disabled = true;
    el.btnStartBurn.textContent = "⏳ GPU 硬體編碼壓制中...";
    el.burnResultBox.classList.add("hidden");

    try {
      const res = await fetch("/api/burn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: videoPath,
          track: state.track,
          style: state.style
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        addLog(`【壓制成功】已產出燒錄影片: ${data.filename}`, "success");
        el.burnResultBox.classList.remove("hidden");
        el.linkDownloadBurned.href = data.url;
        el.btnPreviewBurned.onclick = () => {
          el.video.src = data.url;
          el.video.play();
          addLog("已切換播放器至壓制後影片", "info");
        };
        // 壓制完成後刷新資產庫
        loadAssetLibrary();
      } else {
        throw new Error(data.detail || "壓制失敗");
      }
    } catch (err) {
      addLog(`壓制失敗: ${err.message}`, "error");
    } finally {
      el.btnStartBurn.disabled = false;
      el.btnStartBurn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>開始壓制燒錄影片`;
    }
  });
}

// ---------------- 應用程式啟動入口 ----------------
window.addEventListener("DOMContentLoaded", async () => {
  initPlayer();
  initTabs();
  initUniversalDragAndDrop();
  initAiButtons();
  initEditorViewToggle();
  initStyleEditor();
  initExport();
  applySubtitleStyleToOverlay();

  // 1. 讀取並渲染資產庫
  await loadAssetLibrary();

  // 2. 如果資產庫中已經有使用者上傳的影片 (例如 director-film.mp4)，自動載入！
  try {
    const res = await fetch("/api/assets");
    const data = await res.json();
    const assets = data.assets || [];

    const userVideo = assets.find(a => a.folder === "uploads" && a.type === "video");
    if (userVideo) {
      loadVideoAsset(userVideo);
      addLog(`已自動載入您先前上傳的影片: ${userVideo.name}`, "info");

      // 若有成對字幕，也直接自動載入！
      if (userVideo.paired_subtitle) {
        await loadSubtitleAsset(userVideo.paired_subtitle);
      }
    }
  } catch (e) {
    console.error("Auto load check failed:", e);
  }

  addLog("AutoSubtitle AI Studio 系統初始化完成！", "success");
});
