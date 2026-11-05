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
  assets: [],
  assetFilter: "video", // "video" | "subtitle" | "text" | "all"
  showSamples: false,
  selectedSegmentIndex: 0,
  waveformPeaks: [],
  autoPauseAt: null,
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
  videoStage: document.getElementById("video-stage"),
  btnScaleFit: document.getElementById("btn-scale-fit"),
  btnScaleCompact: document.getElementById("btn-scale-compact"),
  btnScaleLarge: document.getElementById("btn-scale-large"),
  placeholder: document.getElementById("video-placeholder"),
  videoCenterPlayBadge: document.getElementById("video-center-play-badge"),
  videoBufferingSpinner: document.getElementById("video-buffering-spinner"),
  leftPanel: document.getElementById("left-video-panel"),
  dragDropOverlay: document.getElementById("drag-drop-overlay"),
  overlayContainer: document.getElementById("subtitle-overlay-container"),
  overlay: document.getElementById("subtitle-overlay"),
  waveformBarWrapper: document.getElementById("waveform-bar-wrapper"),
  waveformCanvas: document.getElementById("waveform-canvas"),
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

  // Tab 1: 掛載槽、分類資產庫與 AI 模式
  slotCardVideo: document.getElementById("slot-card-video"),
  slotVideoStatus: document.getElementById("slot-video-status"),
  slotVideoName: document.getElementById("slot-video-name"),
  slotVideoMeta: document.getElementById("slot-video-meta"),
  slotCardSub: document.getElementById("slot-card-sub"),
  slotSubStatus: document.getElementById("slot-sub-status"),
  slotSubName: document.getElementById("slot-sub-name"),
  slotSubMeta: document.getElementById("slot-sub-meta"),
  timelineReadyBanner: document.getElementById("timeline-ready-banner"),
  bannerSegCount: document.getElementById("banner-seg-count"),
  inputUploadFiles: document.getElementById("input-upload-files"),
  toggleShowSamples: document.getElementById("toggle-show-samples"),
  countFilterVideo: document.getElementById("count-filter-video"),
  countFilterSubtitle: document.getElementById("count-filter-subtitle"),
  countFilterText: document.getElementById("count-filter-text"),
  assetLibraryContainer: document.getElementById("asset-library-container"),
  btnRefreshAssets: document.getElementById("btn-refresh-assets"),
  btnModeUnscripted: document.getElementById("btn-mode-unscripted"),
  btnModeScripted: document.getElementById("btn-mode-scripted"),
  panelAiUnscripted: document.getElementById("panel-ai-unscripted"),
  panelAiScripted: document.getElementById("panel-ai-scripted"),
  checkAutoProofread: document.getElementById("check-auto-proofread"),
  selectWhisperModel: document.getElementById("select-whisper-model"),
  selectScriptAsset: document.getElementById("select-script-asset"),
  alignScriptTextarea: document.getElementById("align-script-textarea"),
  btnAiTranscribe: document.getElementById("btn-ai-transcribe"),
  btnAiAlign: document.getElementById("btn-ai-align"),
  btnAiProofread: document.getElementById("btn-ai-proofread"),
  btnGotoBreakpointFlow: document.getElementById("btn-goto-breakpoint-flow"),

  // Tab 2: 斷點校對與字幕編輯
  selectBreakpointMode: document.getElementById("select-breakpoint-mode"),
  btnAnalyzeBreakpoints: document.getElementById("btn-analyze-breakpoints"),
  checkLockedOnlyEmpty: document.getElementById("check-locked-only-empty"),
  checkLockedProofread: document.getElementById("check-locked-proofread"),
  btnTranscribeLocked: document.getElementById("btn-transcribe-locked"),
  btnSetInPoint: document.getElementById("btn-set-in-point"),
  btnSetOutPoint: document.getElementById("btn-set-out-point"),
  btnSplitAtPlayhead: document.getElementById("btn-split-at-playhead"),
  btnAddSegment: document.getElementById("btn-add-segment"),
  btnMergeSegments: document.getElementById("btn-merge-segments"),
  btnSplitByPunct: document.getElementById("btn-split-by-punct"),
  btnOffsetMinus: document.getElementById("btn-offset-minus"),
  btnOffsetPlus: document.getElementById("btn-offset-plus"),
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
  btnToggleFontManager: document.getElementById("btn-toggle-font-manager"),
  fontManagerPanel: document.getElementById("font-manager-panel"),
  installedFontCountBadge: document.getElementById("installed-font-count-badge"),
  inputUploadFont: document.getElementById("input-upload-font"),
  fontCatalogList: document.getElementById("font-catalog-list"),
  inputFontUrl: document.getElementById("input-font-url"),
  btnInstallFontUrl: document.getElementById("btn-install-font-url"),
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

  // 核心播放 / 暫停切換器 (具備自動靜音備援與例外保護)
  function togglePlayPause() {
    state.autoPauseAt = null;
    if (!v.src && state.video.url) {
      v.src = state.video.url;
      v.load();
    }
    if (v.paused) {
      const p = v.play();
      if (p !== undefined) {
        p.catch(err => {
          console.warn("Playback error:", err);
          if (err.name === "NotAllowedError") {
            addLog("瀏覽器限制有聲自動播放，已先以靜音啟動播放，可隨時調整音量！", "warn");
            v.muted = true;
            v.play().catch(e => addLog(`播放失敗: ${e.message}`, "error"));
          } else {
            addLog(`播放異常 (${err.name}): ${err.message}`, "error");
          }
        });
      }
    } else {
      v.pause();
    }
  }

  // 播放 / 暫停按鈕
  el.btnPlayPause.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePlayPause();
  });

  // 點擊影片舞台直接播放/暫停
  if (el.videoStage) {
    el.videoStage.addEventListener("click", (e) => {
      // 若佔位提示尚未隱藏，不攔截點擊
      if (el.placeholder && !el.placeholder.classList.contains("hidden")) return;
      togglePlayPause();
    });

    // 雙擊畫面切換全螢幕
    el.videoStage.addEventListener("dblclick", () => {
      if (!document.fullscreenElement) {
        el.videoStage.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  v.addEventListener("play", () => {
    el.iconPlay.classList.add("hidden");
    el.iconPause.classList.remove("hidden");
    if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.add("hidden");
  });

  v.addEventListener("pause", () => {
    el.iconPlay.classList.remove("hidden");
    el.iconPause.classList.add("hidden");
    if (el.videoCenterPlayBadge && (!el.placeholder || el.placeholder.classList.contains("hidden"))) {
      el.videoCenterPlayBadge.classList.remove("hidden");
    }
  });

  v.addEventListener("waiting", () => {
    if (el.videoBufferingSpinner) el.videoBufferingSpinner.classList.remove("hidden");
  });

  v.addEventListener("playing", () => {
    if (el.videoBufferingSpinner) el.videoBufferingSpinner.classList.add("hidden");
  });

  v.addEventListener("canplay", () => {
    if (el.videoBufferingSpinner) el.videoBufferingSpinner.classList.add("hidden");
  });

  v.addEventListener("error", () => {
    const err = v.error;
    let msg = "影片解碼或傳輸錯誤";
    if (err) {
      if (err.code === 1) msg = "加載中止 (MEDIA_ERR_ABORTED)";
      else if (err.code === 2) msg = "網路中斷 (MEDIA_ERR_NETWORK)";
      else if (err.code === 3) msg = "解碼失敗 (MEDIA_ERR_DECODE)";
      else if (err.code === 4) msg = "格式不支援或無效來源 (MEDIA_ERR_SRC_NOT_SUPPORTED)";
    }
    addLog(`【播放器錯誤】${msg} (${v.src})`, "error");
  });

  // 時間與進度條更新 (含聽頭/聽尾自動停頓與波形游標重繪)
  v.addEventListener("timeupdate", () => {
    if (state.autoPauseAt !== null && v.currentTime >= state.autoPauseAt) {
      v.pause();
      state.autoPauseAt = null;
    }
    el.timeCurrent.textContent = formatTime(v.currentTime);
    if (v.duration) {
      el.scrubber.value = (v.currentTime / v.duration) * 100;
    }
    updateSubtitleOverlayOnTime(v.currentTime);
    drawWaveformTimeline();
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

    // 若為直式短影音（寬度小於 600px，如 448x768 等小解析度），自適應縮減預設字級與邊距，防止字體過大爆框
    if (state.video.width < 600 && state.style.font_size > 26) {
      state.style.font_size = 22;
      el.sliderFontSize.value = 22;
      el.valFontSize.textContent = "22px";
      state.style.padding_left = 16;
      state.style.padding_right = 16;
      el.inputPadLeft.value = 16;
      el.inputPadRight.value = 16;
    }

    updateSummary();
    updateWorkspaceSlots();

    // 重新計算字型與座標縮放比，確保預覽與實體影片原樣 100% 貼合
    applySubtitleStyleToOverlay();
  });

  // 全域鍵盤快捷鍵 (Space 播放/暫停，左右鍵快進退，[ 設起點，] 設終點，S 游標處切開)
  window.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || e.target.isContentEditable) {
      return;
    }
    if (e.code === "Space") {
      e.preventDefault();
      state.autoPauseAt = null;
      if (v.paused) v.play();
      else v.pause();
    } else if (e.code === "ArrowLeft" || e.key === "j" || e.key === "J") {
      e.preventDefault();
      state.autoPauseAt = null;
      v.currentTime = Math.max(0, v.currentTime - 3);
    } else if (e.code === "ArrowRight" || e.key === "l" || e.key === "L") {
      e.preventDefault();
      state.autoPauseAt = null;
      v.currentTime = Math.min(v.duration || 0, v.currentTime + 3);
    } else if (e.key === "[") {
      e.preventDefault();
      setInPointAtPlayhead();
    } else if (e.key === "]") {
      e.preventDefault();
      setOutPointAtPlayhead();
    } else if (e.key === "s" || e.key === "S") {
      e.preventDefault();
      splitSegmentAtPlayhead();
    }
  });

  // 點擊聲學波形條定位播放並選取對應 #Index 段落
  if (el.waveformCanvas) {
    el.waveformCanvas.addEventListener("click", (e) => {
      const rect = el.waveformCanvas.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / Math.max(1, rect.width)));
      const dur = v.duration || state.track.duration || 0;
      if (dur > 0) {
        const targetTime = ratio * dur;
        state.autoPauseAt = null;
        v.currentTime = targetTime;
        const foundIdx = state.track.segments.findIndex(s => targetTime >= s.start && targetTime <= s.end);
        if (foundIdx !== -1) {
          state.selectedSegmentIndex = foundIdx;
          const seg = state.track.segments[foundIdx];
          highlightActiveSegmentInList(seg.id);
          const cardEl = document.getElementById(`seg-card-${seg.id}`);
          if (cardEl) cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
        drawWaveformTimeline();
      }
    });
  }

  // 畫面大小切換 (Fit, Compact, Large)
  function setPreviewSize(mode) {
    if (!el.btnScaleFit) return;
    el.btnScaleFit.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";
    el.btnScaleCompact.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";
    el.btnScaleLarge.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";
    
    el.videoStage.classList.remove("max-h-full", "max-h-[300px]", "max-h-[560px]");
    el.video.classList.remove("max-h-full", "max-h-[300px]", "max-h-[560px]");

    if (mode === "compact") {
      el.btnScaleCompact.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
      el.videoStage.classList.add("max-h-[300px]");
      el.video.classList.add("max-h-[300px]");
    } else if (mode === "large") {
      el.btnScaleLarge.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
      el.videoStage.classList.add("max-h-[560px]");
      el.video.classList.add("max-h-[560px]");
    } else {
      el.btnScaleFit.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
      el.videoStage.classList.add("max-h-full");
      el.video.classList.add("max-h-full");
    }

    setTimeout(() => {
      applySubtitleStyleToOverlay();
    }, 50);
  }

  if (el.btnScaleFit) el.btnScaleFit.addEventListener("click", () => setPreviewSize("fit"));
  if (el.btnScaleCompact) el.btnScaleCompact.addEventListener("click", () => setPreviewSize("compact"));
  if (el.btnScaleLarge) el.btnScaleLarge.addEventListener("click", () => setPreviewSize("large"));

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
  saveSessionToStorage();
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
    const activeIdx = state.track.segments.indexOf(activeSeg);
    if (activeIdx !== -1) state.selectedSegmentIndex = activeIdx;
    renderOverlayText(activeSeg.text || `[#${activeSeg.id} 斷點區間]`);
    highlightActiveSegmentInList(activeSeg.id);
  } else {
    if (el.video.paused && state.selectedSegmentIndex >= 0 && state.track.segments[state.selectedSegmentIndex]) {
      const selSeg = state.track.segments[state.selectedSegmentIndex];
      renderOverlayText(selSeg.text || "");
    } else {
      el.overlay.textContent = "";
    }
  }
}

function renderOverlayText(text) {
  el.overlay.textContent = text;
}

// 本地暫存機制 (防止重新整理遺失進度)
function saveSessionToStorage() {
  try {
    localStorage.setItem("autosub_style_v1", JSON.stringify(state.style));
    if (state.track && state.track.segments && state.track.segments.length > 0) {
      localStorage.setItem("autosub_track_v1", JSON.stringify(state.track));
    }
  } catch (e) {
    // ignore storage quota errors
  }
}

// 更新頂部「當前工作台掛載看板 (Active Workspace Slots)」
function updateWorkspaceSlots() {
  // 1. 影片槽狀態
  if (state.video.filename) {
    el.slotCardVideo.className = "p-2.5 rounded-lg bg-blue-950/20 border border-blue-500/40 flex flex-col justify-between gap-1.5 transition";
    el.slotVideoStatus.className = "px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-medium";
    el.slotVideoStatus.textContent = "● 使用中";
    el.slotVideoName.textContent = state.video.filename;
    el.slotVideoName.className = "text-xs font-semibold text-blue-200 truncate";
    const durStr = state.video.duration ? ` • ${state.video.duration.toFixed(1)}s` : "";
    el.slotVideoMeta.textContent = `${state.video.width}x${state.video.height}${durStr}`;
  } else {
    el.slotCardVideo.className = "p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 flex flex-col justify-between gap-1.5 transition";
    el.slotVideoStatus.className = "px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 text-[10px]";
    el.slotVideoStatus.textContent = "未載入";
    el.slotVideoName.textContent = "請從下方選擇或拖入影片";
    el.slotVideoName.className = "text-xs font-semibold text-zinc-400 truncate";
    el.slotVideoMeta.textContent = "支援 MP4 / MOV / WebM";
  }

  // 2. 字幕槽狀態
  const segCount = (state.track && state.track.segments) ? state.track.segments.length : 0;
  if (segCount > 0) {
    el.slotCardSub.className = "p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-500/40 flex flex-col justify-between gap-1.5 transition";
    el.slotSubStatus.className = "px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-medium";
    el.slotSubStatus.textContent = "● 已掛載";
    el.slotSubName.textContent = state.track.source_file || "已生成之字幕時間軸";
    el.slotSubName.className = "text-xs font-semibold text-emerald-200 truncate";
    el.slotSubMeta.textContent = `共 ${segCount} 句時間軸字幕`;
    el.timelineReadyBanner.classList.remove("hidden");
    el.bannerSegCount.textContent = segCount;
  } else {
    el.slotCardSub.className = "p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 flex flex-col justify-between gap-1.5 transition";
    el.slotSubStatus.className = "px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 text-[10px]";
    el.slotSubStatus.textContent = "尚無字幕";
    el.slotSubName.textContent = "可載入 SRT 或由步驟 3 生成";
    el.slotSubName.className = "text-xs font-semibold text-zinc-400 truncate";
    el.slotSubMeta.textContent = "0 句字幕";
    el.timelineReadyBanner.classList.add("hidden");
  }
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

// ---------------- 4. Tab 1: 分類資產媒體庫 (Categorized Asset Library) ----------------
async function loadAssetLibrary() {
  const container = el.assetLibraryContainer;
  container.innerHTML = `<div class="text-xs text-zinc-500 py-3 text-center">正在讀取資產庫...</div>`;

  try {
    const res = await fetch("/api/assets");
    const data = await res.json();
    state.assets = data.assets || [];

    // 若使用者尚未上傳任何檔案，自動開啟「顯示內建範例」避免空白
    const hasUploaded = state.assets.some(a => !a.is_sample);
    if (!hasUploaded && !state.showSamples) {
      state.showSamples = true;
      if (el.toggleShowSamples) el.toggleShowSamples.checked = true;
    }

    updateScriptSelectDropdown();
    renderFilteredAssetLibrary();
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-red-400 py-3 text-center">讀取資產庫失敗: ${err.message}</div>`;
  }
}

function updateScriptSelectDropdown() {
  if (!el.selectScriptAsset) return;
  const currentVal = el.selectScriptAsset.value;
  el.selectScriptAsset.innerHTML = `<option value="">-- 直接在下方貼上歌詞/原稿文字 --</option>`;

  const textAssets = state.assets.filter(a => a.type === "text");
  textAssets.forEach(a => {
    const opt = document.createElement("option");
    opt.value = a.absolute_path;
    opt.dataset.url = a.url;
    const tag = a.is_sample ? "[範例] " : "";
    const lineInfo = a.line_count ? ` (${a.line_count} 行)` : "";
    opt.textContent = `${tag}${a.name}${lineInfo}`;
    el.selectScriptAsset.appendChild(opt);
  });

  if (currentVal) {
    el.selectScriptAsset.value = currentVal;
  }
}

function renderFilteredAssetLibrary() {
  const container = el.assetLibraryContainer;
  const visibleAssets = state.assets.filter(a => state.showSamples || !a.is_sample);

  // 更新各分類數量徽章
  const vCount = visibleAssets.filter(a => a.type === "video").length;
  const sCount = visibleAssets.filter(a => a.type === "subtitle").length;
  const tCount = visibleAssets.filter(a => a.type === "text").length;
  if (el.countFilterVideo) el.countFilterVideo.textContent = vCount;
  if (el.countFilterSubtitle) el.countFilterSubtitle.textContent = sCount;
  if (el.countFilterText) el.countFilterText.textContent = tCount;

  const filtered = state.assetFilter === "all"
    ? visibleAssets
    : visibleAssets.filter(a => a.type === state.assetFilter);

  container.innerHTML = "";

  if (!filtered.length) {
    const hiddenSampleCount = state.assets.filter(a => a.is_sample && (state.assetFilter === "all" || a.type === state.assetFilter)).length;
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "text-xs text-zinc-500 py-4 text-center space-y-2";
    emptyDiv.innerHTML = `<div>此分類目前沒有您上傳的檔案</div>`;
    if (!state.showSamples && hiddenSampleCount > 0) {
      const btnShow = document.createElement("button");
      btnShow.className = "px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-blue-400 rounded text-[11px] transition";
      btnShow.textContent = `點此顯示 ${hiddenSampleCount} 個內建範例檔`;
      btnShow.addEventListener("click", () => {
        state.showSamples = true;
        if (el.toggleShowSamples) el.toggleShowSamples.checked = true;
        renderFilteredAssetLibrary();
      });
      emptyDiv.appendChild(btnShow);
    }
    container.appendChild(emptyDiv);
    return;
  }

  filtered.forEach(asset => {
    const isUpload = !asset.is_sample;
    const isActiveVideo = (asset.type === "video" && state.video.filename === asset.name);
    const isActiveSub = (asset.type === "subtitle" && state.track.source_file === asset.name && state.track.segments.length > 0);
    const isActive = isActiveVideo || isActiveSub;

    const card = document.createElement("div");
    card.className = isActive
      ? "flex items-center justify-between p-2 bg-blue-950/30 border border-blue-500/50 rounded-lg text-xs transition"
      : "flex items-center justify-between p-2 bg-zinc-900/80 hover:bg-zinc-800/90 rounded-lg border border-zinc-800 text-xs transition";

    let icon = "📄";
    if (asset.type === "video") icon = "🎬";
    else if (asset.type === "subtitle") icon = "📝";
    else if (asset.type === "audio") icon = "🎵";

    const badgeColor = isUpload
      ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
      : "bg-zinc-700/30 text-zinc-400 border-zinc-700/50";
    const sourceTag = isUpload ? "已上傳" : "範例";

    let metaDetail = `${asset.size_mb} MB`;
    if (asset.type === "subtitle" && asset.segment_count !== undefined) {
      metaDetail = `${asset.segment_count} 句字幕 • ${asset.name.split('.').pop().toUpperCase()}`;
    } else if (asset.type === "text" && asset.line_count !== undefined) {
      metaDetail = `${asset.line_count} 行原稿 • TXT`;
    }

    card.innerHTML = `
      <div class="flex items-center gap-2 overflow-hidden flex-1 mr-2">
        <span class="text-base shrink-0">${icon}</span>
        <div class="truncate">
          <div class="font-medium text-zinc-200 truncate flex items-center gap-1.5">
            <span class="truncate">${asset.name}</span>
            <span class="text-[9px] px-1.5 py-0.2 rounded border shrink-0 ${badgeColor}">${sourceTag}</span>
            ${isActive ? `<span class="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold shrink-0">● 使用中</span>` : ''}
          </div>
          <div class="text-[10px] text-zinc-500 font-mono">${metaDetail}</div>
        </div>
      </div>

      <div class="flex items-center gap-1 shrink-0">
        ${asset.type === "video" ? `
          <button class="btn-load-this-video px-2 py-1 ${isActiveVideo ? 'bg-blue-600 text-white' : 'bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30'} rounded text-[11px] transition">
            ${isActiveVideo ? '✓ 已載入' : '▶ 載入影片'}
          </button>
          ${asset.paired_subtitle ? `
            <button class="btn-load-paired-all px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-[11px] transition" title="同時載入影片與同名字幕">
              ⚡ 影片+字幕
            </button>
          ` : ''}
        ` : ''}

        ${asset.type === "subtitle" ? `
          <button class="btn-load-this-sub px-2 py-1 ${isActiveSub ? 'bg-emerald-600 text-white' : 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30'} rounded text-[11px] transition">
            ${isActiveSub ? '✓ 已掛載' : '📝 載入時間軸'}
          </button>
        ` : ''}

        ${asset.type === "text" ? `
          <button class="btn-use-this-script px-2 py-1 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded text-[11px] transition">
            🎯 選為對齊原稿
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

    // 選為對齊原稿 (.txt)
    const btnScript = card.querySelector(".btn-use-this-script");
    if (btnScript) {
      btnScript.addEventListener("click", async () => {
        await selectScriptAssetForAlignment(asset);
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
}

async function selectScriptAssetForAlignment(asset) {
  try {
    const res = await fetch(asset.url);
    const text = await res.text();
    if (el.btnModeScripted) el.btnModeScripted.click();
    if (el.selectScriptAsset) el.selectScriptAsset.value = asset.absolute_path;
    if (el.alignScriptTextarea) el.alignScriptTextarea.value = text;
    addLog(`📄 已載入原稿「${asset.name}」至步驟 3 有稿對齊區`, "success");
  } catch (err) {
    addLog(`讀取原稿失敗: ${err.message}`, "error");
  }
}

function loadVideoAsset(asset) {
  state.video.filename = asset.name;
  state.video.url = asset.url;
  state.video.path = asset.absolute_path;
  el.video.src = asset.url;
  try {
    el.video.load();
  } catch (e) {
    console.warn("Video load call error:", e);
  }
  el.videoFilename.textContent = asset.name;
  el.mediaBadge.textContent = asset.name;
  el.placeholder.classList.add("hidden");
  if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.remove("hidden");
  updateWorkspaceSlots();
  renderFilteredAssetLibrary();
  addLog(`已載入影片: ${asset.name}`, "success");
}

async function loadSubtitleAsset(asset) {
  try {
    const res = await fetch(asset.url);
    const content = await res.text();
    if (asset.name.toLowerCase().endsWith(".json")) {
      const trackData = JSON.parse(content);
      trackData.source_file = asset.name;
      setSubtitleTrack(trackData);
    } else {
      parseAndSetSrt(content, asset.name);
    }
    renderFilteredAssetLibrary();
    addLog(`✔ 現成時間軸字幕已掛載: ${asset.name} (共 ${state.track.segments.length} 句)`, "success");
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

      // 1. 若有上傳影片，立即載入最新影片至播放器並切到影片分類
      if (data.videos && data.videos.length > 0) {
        const v = data.videos[0];
        state.assetFilter = "video";
        loadVideoAsset({
          name: v.name,
          url: v.url,
          absolute_path: v.absolute_path
        });
      }

      // 2. 若上傳包含 SRT / VTT 字幕，直接掛載時間軸！
      if (data.tracks && data.tracks.length > 0) {
        const t = data.tracks[0];
        t.track.source_file = t.filename;
        setSubtitleTrack(t.track);
        addLog(`🎉 偵測到現成時間軸字幕 (${t.filename})！已直接掛載 (共 ${t.track.segments.length} 句)，無需重複 AI 辨識！`, "success");

        if (t.track.segments.length > 0) {
          el.video.currentTime = t.track.segments[0].start;
          renderOverlayText(t.track.segments[0].text);
        }
      }

      // 3. 若上傳包含 TXT 原稿，自動填入有稿對齊區
      if (data.scripts && data.scripts.length > 0) {
        const s = data.scripts[0];
        if (el.btnModeScripted) el.btnModeScripted.click();
        if (el.alignScriptTextarea) el.alignScriptTextarea.value = s.content;
        addLog(`📄 偵測到原稿檔案 (${s.filename})，已自動載入至「有稿對齊」區！`, "success");
      }

      // 4. 若上傳包含 TTF / OTF / TTC / WOFF2 字型檔，自動載入字型並套用！
      if (data.fonts && data.fonts.length > 0) {
        await loadFontCatalog();
        const f = data.fonts[0];
        selectAndApplyFont(f.family, f.display_name);
        addLog(`🔤 已成功安裝並套用字型：${f.display_name} (${f.family})`, "success");
      }

      // 刷新資產庫
      await loadAssetLibrary();
    } else {
      throw new Error(data.detail || "上傳失敗");
    }
  } catch (err) {
    addLog(`上傳失敗: ${err.message}`, "error");
  }
}

function initUniversalDragAndDrop() {
  const overlay = el.dragDropOverlay;

  // 阻止瀏覽器預設開啟行為
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    window.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  window.addEventListener('dragover', () => {
    overlay.classList.remove('hidden');
  });

  overlay.addEventListener('dragleave', () => {
    overlay.classList.add('hidden');
  });

  window.addEventListener('drop', (e) => {
    overlay.classList.add('hidden');
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      handleBatchFileUpload(dt.files);
    }
  });

  el.inputUploadFiles.addEventListener("change", (e) => {
    handleBatchFileUpload(e.target.files);
  });

  el.btnRefreshAssets.addEventListener("click", () => {
    loadAssetLibrary();
    addLog("已重新整理資產庫", "info");
  });

  // 資產分類切換按鈕
  document.querySelectorAll(".asset-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.assetFilter = btn.dataset.assetFilter;
      document.querySelectorAll(".asset-filter-btn").forEach(b => {
        b.className = "asset-filter-btn flex-1 py-1 px-2 rounded text-zinc-400 hover:text-zinc-200 transition";
      });
      btn.className = "asset-filter-btn flex-1 py-1 px-2 rounded bg-blue-600 text-white font-medium transition";
      renderFilteredAssetLibrary();
    });
  });

  // 顯示內建範例開關
  if (el.toggleShowSamples) {
    el.toggleShowSamples.addEventListener("change", (e) => {
      state.showSamples = e.target.checked;
      renderFilteredAssetLibrary();
    });
  }
}

// ---------------- 6. AI 功能按鈕與模式切換 ----------------
function initAiButtons() {
  // 模式切換：無稿辨識 vs 有稿對齊
  if (el.btnModeUnscripted && el.btnModeScripted) {
    el.btnModeUnscripted.addEventListener("click", () => {
      el.panelAiUnscripted.classList.remove("hidden");
      el.panelAiScripted.classList.add("hidden");
      el.btnModeUnscripted.className = "flex-1 py-1.5 px-2 rounded bg-purple-600/30 text-purple-300 border border-purple-500/40 font-medium transition";
      el.btnModeScripted.className = "flex-1 py-1.5 px-2 rounded text-zinc-400 hover:text-zinc-200 transition";
    });

    el.btnModeScripted.addEventListener("click", () => {
      el.panelAiScripted.classList.remove("hidden");
      el.panelAiUnscripted.classList.add("hidden");
      el.btnModeScripted.className = "flex-1 py-1.5 px-2 rounded bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 font-medium transition";
      el.btnModeUnscripted.className = "flex-1 py-1.5 px-2 rounded text-zinc-400 hover:text-zinc-200 transition";
    });
  }

  // 當從下拉選單選擇原稿檔時，自動載入內容預覽
  if (el.selectScriptAsset) {
    el.selectScriptAsset.addEventListener("change", async (e) => {
      const opt = e.target.selectedOptions[0];
      if (opt && opt.dataset.url) {
        try {
          const res = await fetch(opt.dataset.url);
          el.alignScriptTextarea.value = await res.text();
        } catch (err) {
          console.error(err);
        }
      }
    });
  }

  // AI 自動產生字幕 (單一入口：自動依據是否有填寫原詞智慧雙分流)
  if (el.btnAiTranscribe) {
    el.btnAiTranscribe.addEventListener("click", async () => {
      const media = state.video.path;
      if (!media) {
        addLog("請先在上方選擇或上傳影片後再執行產生字幕", "error");
        return;
      }

      const modelSize = el.selectWhisperModel ? el.selectWhisperModel.value : "large-v3-turbo";
      const autoProofread = el.checkAutoProofread ? el.checkAutoProofread.checked : true;
      const scriptText = el.alignScriptTextarea ? el.alignScriptTextarea.value.trim() : "";

      if (scriptText) {
        addLog(`【AI 產生字幕】檢測到參考原詞（${scriptText.split('\n').filter(Boolean).length} 行），以 Whisper (${modelSize}) 擷取字級時間軸，並由 Qwen2.5 比對原詞 100% 精準校對...`);
      } else {
        addLog(`【AI 產生字幕】無稿模式，正在以 Whisper (${modelSize}) 辨識${autoProofread ? ' 並由 Qwen2.5 自動盲校錯字' : ''}...`);
      }

      el.btnAiTranscribe.disabled = true;
      el.btnAiTranscribe.textContent = scriptText 
        ? "⏳ Whisper 辨識與 Qwen2.5 原詞對照校對中..." 
        : (autoProofread ? "⏳ Whisper 辨識與 Qwen2.5 校對中..." : "⏳ Whisper 語音辨識中...");

      const formData = new FormData();
      formData.append("media_path", media);
      formData.append("model", modelSize);
      formData.append("device", "cuda");
      formData.append("prompt", "繁體中文");
      formData.append("auto_proofread", String(autoProofread));
      if (scriptText) {
        formData.append("script_text", scriptText);
      }

      try {
        const res = await fetch("/api/ai/transcribe", { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
          data.track.source_file = `${state.video.filename.replace(/\.[^.]+$/, '')}.ai.srt`;
          setSubtitleTrack(data.track);
          if (data.has_reference) {
            addLog(`【AI 產生字幕成功】已生成 ${data.track.segments.length} 句字幕（已成功參照原稿完成 100% 正字校對）！`, "success");
          } else {
            addLog(`【AI 辨識完成】已生成 ${data.track.segments.length} 句時間軸字幕！`, "success");
          }
        } else {
          throw new Error(data.detail || "辨識失敗");
        }
      } catch (err) {
        addLog(`辨識失敗: ${err.message}`, "error");
      } finally {
        el.btnAiTranscribe.disabled = false;
        el.btnAiTranscribe.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"/></svg>🎙️ 開始 AI 產生字幕 (自動判定原詞)`;
      }
    });
  }

  // 有稿強制對齊 (備用相容)
  if (el.btnAiAlign) {
    el.btnAiAlign.addEventListener("click", async () => {
      const media = state.video.path;
      if (!media) {
        addLog("請先載入影片後再執行對齊", "error");
        return;
      }

      const scriptText = el.alignScriptTextarea ? el.alignScriptTextarea.value.trim() : "";
      const scriptPath = el.selectScriptAsset ? el.selectScriptAsset.value : "";

      if (!scriptText && !scriptPath) {
        addLog("請先選擇原稿 .txt 檔案或在文字框貼上歌詞/原稿內容", "error");
        return;
      }

      addLog(`【有稿對齊】正在將原稿與 ${state.video.filename} 音軌強制對齊...`);
      el.btnAiAlign.disabled = true;
      el.btnAiAlign.textContent = "⏳ 音軌特徵提取與動態規劃對齊中...";

      try {
        const payload = { media_path: media };
        if (scriptText) payload.script_text = scriptText;
        if (scriptPath) payload.script_path = scriptPath;

        const res = await fetch("/api/ai/align", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
          data.track.source_file = `${state.video.filename.replace(/\.[^.]+$/, '')}.aligned.srt`;
          setSubtitleTrack(data.track);
          addLog(`【有稿對齊成功】生成 ${data.track.segments.length} 句 100% 原稿時間軸字幕！`, "success");
        } else {
          throw new Error(data.detail || "對齊失敗");
        }
      } catch (err) {
        addLog(`對齊失敗: ${err.message}`, "error");
      } finally {
        el.btnAiAlign.disabled = false;
        el.btnAiAlign.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>開始原稿與音軌 100% 強制對齊`;
      }
    });
  }

  // Edge LLM 校對 (自動依據是否有填寫原詞決定「有稿精準校對」或「無稿盲校」)
  if (el.btnAiProofread) {
    el.btnAiProofread.addEventListener("click", async () => {
      if (!state.track.segments.length) {
        addLog("請先載入或生成字幕後再執行校對", "error");
        return;
      }
      const scriptText = el.alignScriptTextarea ? el.alignScriptTextarea.value.trim() : "";
      if (scriptText) {
        addLog(`【Qwen2.5 校對】正在參照上方原稿歌詞進行精準錯字校正...`);
      } else {
        addLog(`【Qwen2.5 校對】啟動本地 Qwen2.5 進行上下文盲校...`);
      }
      el.btnAiProofread.disabled = true;
      el.btnAiProofread.textContent = "⏳ 校對中...";

      try {
        const payload = { track: state.track, batch_size: 8 };
        if (scriptText) {
          payload.script_text = scriptText;
        }
        const res = await fetch("/api/ai/proofread", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
          setSubtitleTrack(data.track);
          if (data.has_reference) {
            addLog(`【校對完成】已依據原稿歌詞 100% 還原正確正字！`, "success");
          } else {
            addLog(`【校對完成】字幕已自動修正同音字與標點！`, "success");
          }
        } else {
          throw new Error(data.detail || "校對失敗");
        }
      } catch (err) {
        addLog(`校對失敗: ${err.message}`, "error");
      } finally {
        el.btnAiProofread.disabled = false;
        el.btnAiProofread.textContent = "✨ 校對目前字幕";
      }
    });
  }
}

// 強健 SRT / VTT 解析器 (客戶端)
function parseAndSetSrt(srtContent, sourceName = "manual.srt") {
  const clean = srtContent.replace(/^\uFEFF/, "").replace(/^WEBVTT[^\n]*\n+/i, "").trim();
  const blocks = clean.split(/\r?\n\s*\r?\n/);
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

// ---------------- 7. Tab 2: 斷點校對與字幕管理編輯器 ----------------
function drawWaveformTimeline() {
  if (!el.waveformCanvas || !el.waveformBarWrapper) return;
  if ((!state.waveformPeaks || !state.waveformPeaks.length) && (!state.track.segments || !state.track.segments.length)) {
    return;
  }

  el.waveformBarWrapper.classList.remove("hidden");
  const canvas = el.waveformCanvas;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 480;
  const h = canvas.clientHeight || 36;
  if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
  }

  const ctx = canvas.getContext("2d");
  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const totalDur = el.video.duration || state.track.duration || 1;

  // 1. 繪製 #Index 段落底色區塊
  if (state.track.segments && state.track.segments.length > 0) {
    state.track.segments.forEach((seg, idx) => {
      const x1 = (seg.start / totalDur) * w;
      const x2 = Math.max(x1 + 2, (seg.end / totalDur) * w);
      const isSel = (idx === state.selectedSegmentIndex);

      ctx.fillStyle = isSel ? "rgba(37, 99, 235, 0.32)" : "rgba(16, 185, 129, 0.13)";
      ctx.fillRect(x1, 0, x2 - x1, h);

      ctx.strokeStyle = isSel ? "rgba(96, 165, 250, 0.9)" : "rgba(52, 211, 153, 0.45)";
      ctx.lineWidth = isSel ? 1.5 : 1;
      ctx.strokeRect(x1 + 0.5, 0.5, Math.max(1, x2 - x1 - 1), h - 1);
    });
  }

  // 2. 繪製聲學能量峰值柱狀圖
  if (state.waveformPeaks && state.waveformPeaks.length > 0) {
    const peaks = state.waveformPeaks;
    const n = peaks.length;
    const barW = w / n;
    ctx.fillStyle = "rgba(148, 163, 184, 0.55)";
    for (let i = 0; i < n; i++) {
      const val = peaks[i];
      const bh = Math.max(2, val * (h - 6));
      const x = i * barW;
      const y = h - bh;
      ctx.fillRect(x, y, Math.max(1, barW - 0.5), bh);
    }
  }

  // 3. 繪製目前播放時間紅線游標
  const curX = ((el.video.currentTime || 0) / totalDur) * w;
  ctx.strokeStyle = "#f43f5e";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(curX, 0);
  ctx.lineTo(curX, h);
  ctx.stroke();

  ctx.restore();
}

function auditionWindow(startSec, endSec) {
  const s = Math.max(0, startSec);
  const e = Math.max(s + 0.25, endSec);
  state.autoPauseAt = e;
  el.video.currentTime = s;
  el.video.play();
}

function normalizeTrackSegments() {
  if (!state.track || !state.track.segments) return;
  state.track.segments.sort((a, b) => a.start - b.start);
  state.track.segments.forEach((seg, i) => {
    seg.id = i + 1;
    seg.start = Math.max(0, Number(seg.start.toFixed(2)));
    seg.end = Math.max(seg.start + 0.1, Number(seg.end.toFixed(2)));
    if (!seg.expected_chars) {
      seg.expected_chars = Math.max(2, Math.min(22, Math.round((seg.end - seg.start) * 3.3)));
    }
  });
}

function setSubtitleTrack(track) {
  state.track = track;
  normalizeTrackSegments();
  el.segmentCountBadge.textContent = `${track.segments.length} 句字幕`;
  el.editorSegCount.textContent = track.segments.length;
  renderSegmentList();
  updateSubtitleSelectDropdown();
  updateSummary();
  updateWorkspaceSlots();
  renderFilteredAssetLibrary();
  drawWaveformTimeline();
  saveSessionToStorage();

  if (track.segments.length > 0) {
    state.selectedSegmentIndex = Math.min(state.selectedSegmentIndex, track.segments.length - 1);
  }
}

function renderSegmentList() {
  const container = el.segmentListContainer;
  container.innerHTML = "";

  if (!state.track.segments.length) {
    container.innerHTML = `<div class="text-center py-10 text-xs text-zinc-500">請點擊上方【🔍 分析音訊斷點】自動抓出每句開頭結尾，或拖入現成 SRT</div>`;
    el.rawSubtitleTextarea.value = "";
    return;
  }

  el.rawSubtitleTextarea.value = state.track.segments.map(s => s.text).join("\n");

  state.track.segments.forEach((seg, idx) => {
    const card = document.createElement("div");
    card.id = `seg-card-${seg.id}`;
    const isSelected = (idx === state.selectedSegmentIndex);
    card.className = isSelected
      ? "p-2.5 bg-blue-950/25 border border-blue-500 rounded-lg transition flex flex-col gap-1.5 text-xs"
      : "p-2.5 bg-zinc-950/70 border border-zinc-800 rounded-lg hover:border-zinc-700 transition flex flex-col gap-1.5 text-xs";

    const dur = Math.max(0.1, seg.end - seg.start);
    const expChars = seg.expected_chars || Math.max(2, Math.round(dur * 3.3));
    const curLen = (seg.text || "").trim().length;
    const capBadgeText = curLen > 0
      ? `${dur.toFixed(1)}s • 已填 ${curLen} 字 (建議~${expChars}字)`
      : `${dur.toFixed(1)}s • 建議約 ${expChars} 字`;
    const capBadgeColor = (curLen > expChars + 6)
      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
      : (curLen > 0 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" : "text-cyan-300 bg-cyan-500/10 border-cyan-500/20");

    const topRow = document.createElement("div");
    topRow.className = "flex items-center justify-between gap-1.5 flex-wrap";

    topRow.innerHTML = `
      <div class="flex items-center gap-1">
        <span class="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-200 font-semibold font-mono text-[10px]">#${seg.id}</span>
        <input type="number" step="0.05" min="0" class="seg-start-input w-16 bg-zinc-900 border border-zinc-800 rounded px-1 py-0.5 font-mono text-[11px] text-zinc-200 text-center focus:outline-none focus:border-blue-500" title="起點秒數 (支援滾輪微調)">
        <span class="text-zinc-600 text-[10px]">➔</span>
        <input type="number" step="0.05" min="0" class="seg-end-input w-16 bg-zinc-900 border border-zinc-800 rounded px-1 py-0.5 font-mono text-[11px] text-zinc-200 text-center focus:outline-none focus:border-blue-500" title="終點秒數 (支援滾輪微調)">
        <span class="seg-cap-badge px-1.5 py-0.5 rounded border font-mono text-[10px] ${capBadgeColor}">${capBadgeText}</span>
      </div>
      <div class="flex items-center gap-1">
        <button class="btn-audition-head px-1.5 py-0.5 bg-zinc-800 hover:bg-cyan-900/50 text-cyan-300 border border-zinc-700/80 rounded text-[10px] transition" title="只聽開頭 0.9 秒，確認起點有沒有切太早或太晚">🎧 聽頭</button>
        <button class="btn-audition-tail px-1.5 py-0.5 bg-zinc-800 hover:bg-amber-900/50 text-amber-300 border border-zinc-700/80 rounded text-[10px] transition" title="只聽結尾最後 0.9 秒，確認拖音有沒有被切斷">🎧 聽尾</button>
        <button class="btn-play-seg px-1.5 py-0.5 bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/30 rounded text-[10px] transition" title="完整試聽此段並在結尾自動暫停">▶ 整段</button>
        <button class="btn-del-seg px-1.5 py-0.5 hover:bg-red-950/40 text-zinc-500 hover:text-red-400 rounded text-[10px]" title="刪除此段">✕</button>
      </div>
    `;

    const startInput = topRow.querySelector(".seg-start-input");
    const endInput = topRow.querySelector(".seg-end-input");
    const capBadge = topRow.querySelector(".seg-cap-badge");
    startInput.value = seg.start.toFixed(2);
    endInput.value = seg.end.toFixed(2);

    function refreshCapBadge() {
      const d = Math.max(0.1, seg.end - seg.start);
      seg.expected_chars = Math.max(2, Math.min(22, Math.round(d * 3.3)));
      const cLen = (seg.text || "").trim().length;
      capBadge.textContent = cLen > 0
        ? `${d.toFixed(1)}s • 已填 ${cLen} 字 (建議~${seg.expected_chars}字)`
        : `${d.toFixed(1)}s • 建議約 ${seg.expected_chars} 字`;
      drawWaveformTimeline();
    }

    startInput.addEventListener("change", (e) => {
      const val = parseFloat(e.target.value);
      if (!isNaN(val) && val >= 0) {
        seg.start = Number(val.toFixed(2));
        if (seg.end <= seg.start) seg.end = Number((seg.start + 0.4).toFixed(2));
        endInput.value = seg.end.toFixed(2);
        refreshCapBadge();
        updateSubtitleSelectDropdown();
        saveSessionToStorage();
      }
    });

    endInput.addEventListener("change", (e) => {
      const val = parseFloat(e.target.value);
      if (!isNaN(val) && val > seg.start) {
        seg.end = Number(val.toFixed(2));
        refreshCapBadge();
        updateSubtitleSelectDropdown();
        saveSessionToStorage();
      }
    });

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.className = "seg-text-input w-full bg-zinc-900 border border-zinc-800/80 rounded px-2 py-1 text-zinc-200 text-xs focus:outline-none focus:border-blue-500 placeholder:text-zinc-600";
    textInput.placeholder = `[#${seg.id} 待填字幕 — 可直接手打 (Enter 跳下一段)，或校對完時間軸後點上方「填入 AI 字幕」]`;
    textInput.value = seg.text || "";

    card.appendChild(topRow);
    card.appendChild(textInput);

    card.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") {
        selectAndJumpToSegment(idx);
      }
    });

    textInput.addEventListener("focus", () => {
      state.selectedSegmentIndex = idx;
      highlightActiveSegmentInList(seg.id);
      drawWaveformTimeline();
    });

    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const nextIdx = idx + 1;
        if (nextIdx < state.track.segments.length) {
          const nextSeg = state.track.segments[nextIdx];
          selectAndJumpToSegment(nextIdx);
          auditionWindow(nextSeg.start, nextSeg.end);
          const nextCard = document.getElementById(`seg-card-${nextSeg.id}`);
          if (nextCard) {
            const nextInp = nextCard.querySelector(".seg-text-input");
            if (nextInp) nextInp.focus();
          }
        }
      }
    });

    textInput.addEventListener("input", (e) => {
      seg.text = e.target.value;
      el.rawSubtitleTextarea.value = state.track.segments.map(s => s.text).join("\n");
      refreshCapBadge();
      if (state.selectedSegmentIndex === idx) {
        renderOverlayText(seg.text);
      }
      saveSessionToStorage();
    });

    // 🎧 聽頭 (只播開頭 0.95 秒)
    topRow.querySelector(".btn-audition-head").addEventListener("click", () => {
      state.selectedSegmentIndex = idx;
      highlightActiveSegmentInList(seg.id);
      renderOverlayText(seg.text || `[#${seg.id} 聽開頭]`);
      auditionWindow(seg.start, Math.min(seg.end, seg.start + 0.95));
    });

    // 🎧 聽尾 (只播結尾前 0.95 秒到結束)
    topRow.querySelector(".btn-audition-tail").addEventListener("click", () => {
      state.selectedSegmentIndex = idx;
      highlightActiveSegmentInList(seg.id);
      renderOverlayText(seg.text || `[#${seg.id} 聽結尾]`);
      auditionWindow(Math.max(seg.start, seg.end - 0.95), seg.end);
    });

    // ▶ 整段試聽 (播到該段結束自動暫停)
    topRow.querySelector(".btn-play-seg").addEventListener("click", () => {
      state.selectedSegmentIndex = idx;
      highlightActiveSegmentInList(seg.id);
      renderOverlayText(seg.text || `[#${seg.id} 試聽中]`);
      auditionWindow(seg.start, seg.end);
    });

    topRow.querySelector(".btn-del-seg").addEventListener("click", () => {
      state.track.segments.splice(idx, 1);
      setSubtitleTrack(state.track);
    });

    container.appendChild(card);
  });
}

function highlightActiveSegmentInList(segId) {
  document.querySelectorAll("#segment-list-container > div").forEach(c => {
    c.classList.remove("border-blue-500", "bg-blue-950/20");
    c.classList.add("border-zinc-800", "bg-zinc-950/70");
  });
  const activeCard = document.getElementById(`seg-card-${segId}`);
  if (activeCard) {
    activeCard.classList.remove("border-zinc-800", "bg-zinc-950/70");
    activeCard.classList.add("border-blue-500", "bg-blue-950/20");
  }
}

function selectAndJumpToSegment(index) {
  state.selectedSegmentIndex = index;
  const seg = state.track.segments[index];
  if (seg) {
    state.autoPauseAt = null;
    el.video.currentTime = seg.start;
    renderOverlayText(seg.text);
    highlightActiveSegmentInList(seg.id);
    el.selectedSubBadge.textContent = `目前選擇: 第 ${seg.id} 句 (${seg.start.toFixed(2)}s)`;
    el.selectSubtitleLine.value = String(index);
    drawWaveformTimeline();
  }
}

// 【拍點快修 1】設目前播放點為選取段的「起點 (In)」
function setInPointAtPlayhead() {
  const segs = state.track.segments;
  const idx = state.selectedSegmentIndex;
  if (!segs.length || idx < 0 || idx >= segs.length) {
    addLog("請先選取一個 #Index 段落後再設起點", "error");
    return;
  }
  const cur = segs[idx];
  const t = Number((el.video.currentTime || 0).toFixed(2));
  if (t >= cur.end - 0.15) {
    cur.end = Number((t + 1.5).toFixed(2));
  }
  cur.start = t;
  // 若與前一段重疊，自動收斂前一段的終點
  if (idx > 0 && segs[idx - 1].end > t) {
    segs[idx - 1].end = t;
  }
  setSubtitleTrack(state.track);
  auditionWindow(cur.start, Math.min(cur.end, cur.start + 0.9));
  addLog(`✔ 已將 #${cur.id} 起點設為 ${t.toFixed(2)}s (並自動試聽開頭)`, "success");
}

// 【拍點快修 2】設目前播放點為選取段的「終點 (Out)」
function setOutPointAtPlayhead() {
  const segs = state.track.segments;
  const idx = state.selectedSegmentIndex;
  if (!segs.length || idx < 0 || idx >= segs.length) {
    addLog("請先選取一個 #Index 段落後再設終點", "error");
    return;
  }
  const cur = segs[idx];
  const t = Number((el.video.currentTime || 0).toFixed(2));
  if (t <= cur.start + 0.15) {
    addLog(`終點 (${t}s) 必須大於該段起點 (${cur.start}s)`, "error");
    return;
  }
  cur.end = t;
  // 若與下一段重疊，自動往後推下一段的起點
  if (idx + 1 < segs.length && segs[idx + 1].start < t) {
    segs[idx + 1].start = t;
    if (segs[idx + 1].end <= t) segs[idx + 1].end = Number((t + 1.2).toFixed(2));
  }
  setSubtitleTrack(state.track);
  auditionWindow(Math.max(cur.start, cur.end - 0.9), cur.end);
  addLog(`✔ 已將 #${cur.id} 終點設為 ${t.toFixed(2)}s (並自動試聽結尾)`, "success");
}

// 【拍點快修 3】在目前播放游標處切開為兩段 (自動吸附聲學波谷)
async function splitSegmentAtPlayhead() {
  const segs = state.track.segments;
  if (!segs.length) {
    addLog("目前尚無時間軸段落可供切分", "error");
    return;
  }
  let playTime = Number((el.video.currentTime || 0).toFixed(2));

  // 優先尋找包含目前播放時間的段落，否則使用目前選取的段落
  let targetIdx = segs.findIndex(s => playTime > s.start + 0.15 && playTime < s.end - 0.15);
  if (targetIdx === -1) {
    const sel = segs[state.selectedSegmentIndex];
    if (sel && playTime > sel.start + 0.15 && playTime < sel.end - 0.15) {
      targetIdx = state.selectedSegmentIndex;
    } else if (sel && (sel.end - sel.start) >= 0.8) {
      targetIdx = state.selectedSegmentIndex;
      playTime = Number(((sel.start + sel.end) / 2).toFixed(2));
    }
  }

  if (targetIdx === -1) {
    addLog("請先將播放游標停在要切開的段落中間後再按「✂️ 游標處切開」", "error");
    return;
  }

  const cur = segs[targetIdx];
  // 呼叫後端吸附附近 ±0.18s 的聲學能量波谷
  if (state.video.path) {
    try {
      const res = await fetch("/api/audio/snap-split", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ media_path: state.video.path, time_sec: playTime })
      });
      const data = await res.json();
      if (data.status === "success" && data.snapped_time > cur.start + 0.2 && data.snapped_time < cur.end - 0.2) {
        playTime = data.snapped_time;
      }
    } catch (e) {
      // ignore snap fallback
    }
  }

  const origEnd = cur.end;
  const origText = (cur.text || "").trim();
  let text1 = origText;
  let text2 = "";
  if (origText.length >= 4) {
    const ratio = (playTime - cur.start) / Math.max(0.2, origEnd - cur.start);
    const cutIdx = Math.max(1, Math.min(origText.length - 1, Math.round(origText.length * ratio)));
    text1 = origText.slice(0, cutIdx).trim();
    text2 = origText.slice(cutIdx).trim();
  }

  cur.end = playTime;
  cur.text = text1;
  cur.expected_chars = Math.max(2, Math.round((cur.end - cur.start) * 3.3));

  const newSeg = {
    id: cur.id + 1,
    start: playTime,
    end: origEnd,
    text: text2,
    expected_chars: Math.max(2, Math.round((origEnd - playTime) * 3.3)),
    words: []
  };

  segs.splice(targetIdx + 1, 0, newSeg);
  state.selectedSegmentIndex = targetIdx + 1;
  setSubtitleTrack(state.track);
  auditionWindow(newSeg.start, Math.min(newSeg.end, newSeg.start + 1.0));
  addLog(`✂️ 已於聲學波谷 ${playTime.toFixed(2)}s 處切開為 #${targetIdx + 1} 與 #${targetIdx + 2}！`, "success");
}

// 【階段 1】執行極速音訊斷點分析 (建立 #1 ~ #N 時間軸索引)
async function runBreakpointAnalysis() {
  const media = state.video.path;
  if (!media) {
    addLog("請先載入或上傳影片後再執行音訊斷點分析", "error");
    return;
  }

  const hasTypedText = state.track.segments.some(s => (s.text || "").trim().length > 0);
  if (hasTypedText) {
    if (!confirm("重新分析音訊斷點將會建立全新的空白時間軸索引 (#1 ~ #N)，確定要覆蓋目前的字幕嗎？")) {
      return;
    }
  }

  const mode = el.selectBreakpointMode ? el.selectBreakpointMode.value : "balanced";
  const modeLabel = mode === "dense" ? "密集歌詞/快歌" : (mode === "slow" ? "慢歌拖音" : "一般標準");
  addLog(`【階段 1：音訊斷點分析】正在以「${modeLabel}」模式掃描 ${state.video.filename} 的發聲區間與換氣波谷...`);

  if (el.btnAnalyzeBreakpoints) {
    el.btnAnalyzeBreakpoints.disabled = true;
    el.btnAnalyzeBreakpoints.textContent = "⏳ 掃描聲學斷點中...";
  }

  try {
    const res = await fetch("/api/audio/breakpoints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_path: media, mode })
    });
    const data = await res.json();
    if (data.status === "success") {
      state.waveformPeaks = data.waveform_peaks || [];
      state.selectedSegmentIndex = 0;
      setSubtitleTrack(data.track);
      // 自動切換至 Tab 2 方便使用者立即聽頭尾校對
      const tab2Btn = document.querySelector('[data-tab="tab-editor"]');
      if (tab2Btn) tab2Btn.click();
      addLog(`✔ 斷點分析完成！共抓出 ${data.segment_count} 個發聲段落 (#1 ~ #${data.segment_count})。請用「🎧 聽頭 / 聽尾」確認斷點，確認無誤後即可手打、貼詞或點「🎙️ 依目前時間軸填入 AI 字幕」！`, "success");
    } else {
      throw new Error(data.detail || "斷點分析失敗");
    }
  } catch (err) {
    addLog(`斷點分析失敗: ${err.message}`, "error");
  } finally {
    if (el.btnAnalyzeBreakpoints) {
      el.btnAnalyzeBreakpoints.disabled = false;
      el.btnAnalyzeBreakpoints.innerHTML = `<span>🔍 分析音訊斷點 (建立時間軸)</span>`;
    }
  }
}

// 【階段 3】依目前鎖定時間軸執行受控 Whisper 填空
async function runLockedTimelineTranscribe() {
  const media = state.video.path;
  if (!media) {
    addLog("請先載入影片後再執行填字", "error");
    return;
  }
  if (!state.track.segments || !state.track.segments.length) {
    addLog("請先點選左側「🔍 分析音訊斷點」建立時間軸段落後，再執行填字！", "error");
    return;
  }

  const onlyEmpty = el.checkLockedOnlyEmpty ? el.checkLockedOnlyEmpty.checked : false;
  const autoProofread = el.checkLockedProofread ? el.checkLockedProofread.checked : false;
  const modelSize = el.selectWhisperModel ? el.selectWhisperModel.value : "large-v3-turbo";

  addLog(`【階段 3：鎖定時間軸填字】正在嚴格依照您校對好的 ${state.track.segments.length} 個時間段執行受控 Whisper 填字 (絕不改動起訖時間)...`);
  if (el.btnTranscribeLocked) {
    el.btnTranscribeLocked.disabled = true;
    el.btnTranscribeLocked.textContent = "⏳ 按鎖定時間軸逐段辨識中...";
  }

  try {
    const res = await fetch("/api/ai/transcribe-segments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        media_path: media,
        track: state.track,
        model: modelSize,
        device: "cuda",
        prompt: "繁體中文",
        only_empty: onlyEmpty,
        auto_proofread: autoProofread
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      setSubtitleTrack(data.track);
      addLog(`🎉 已依鎖定時間軸完成 ${data.track.segments.length} 段字幕填入！時間軸起訖點 100% 保持不變！`, "success");
    } else {
      throw new Error(data.detail || "填字失敗");
    }
  } catch (err) {
    addLog(`鎖定時間軸填字失敗: ${err.message}`, "error");
  } finally {
    if (el.btnTranscribeLocked) {
      el.btnTranscribeLocked.disabled = false;
      el.btnTranscribeLocked.innerHTML = `<span>🎙️ 依目前時間軸填入 AI 字幕</span>`;
    }
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

  // 1:1 將多行文字依序填入目前鎖定的 #1 ~ #N 時間軸
  el.btnApplyRawText.addEventListener("click", () => {
    const lines = el.rawSubtitleTextarea.value.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const segs = state.track.segments;
    if (!segs.length) {
      addLog("目前尚無時間軸段落，請先執行「🔍 分析音訊斷點」建立時間軸！", "error");
      return;
    }
    const fillCount = Math.min(lines.length, segs.length);
    for (let i = 0; i < fillCount; i++) {
      segs[i].text = lines[i];
    }
    setSubtitleTrack(state.track);
    el.btnViewList.click();
    if (lines.length === segs.length) {
      addLog(`✔ 已將 ${lines.length} 行文字 1:1 完美填入 #1 ~ #${segs.length} 時間軸！`, "success");
    } else {
      addLog(`✔ 已將前 ${fillCount} 行文字依序填入時間軸 (文字共 ${lines.length} 行，時間軸共 ${segs.length} 段)`, "info");
    }
  });

  // 綁定斷點分析、鎖定時間軸填字與拍點快修按鈕
  if (el.btnAnalyzeBreakpoints) {
    el.btnAnalyzeBreakpoints.addEventListener("click", runBreakpointAnalysis);
  }
  if (el.btnGotoBreakpointFlow) {
    el.btnGotoBreakpointFlow.addEventListener("click", runBreakpointAnalysis);
  }
  if (el.btnTranscribeLocked) {
    el.btnTranscribeLocked.addEventListener("click", runLockedTimelineTranscribe);
  }
  if (el.btnSetInPoint) {
    el.btnSetInPoint.addEventListener("click", setInPointAtPlayhead);
  }
  if (el.btnSetOutPoint) {
    el.btnSetOutPoint.addEventListener("click", setOutPointAtPlayhead);
  }
  if (el.btnSplitAtPlayhead) {
    el.btnSplitAtPlayhead.addEventListener("click", splitSegmentAtPlayhead);
  }

  // 1. 新增字幕段
  el.btnAddSegment.addEventListener("click", () => {
    const curTime = Number((el.video.currentTime || 0).toFixed(2));
    state.track.segments.push({
      id: state.track.segments.length + 1,
      start: curTime,
      end: Number((curTime + 2.5).toFixed(2)),
      text: "新字幕文字",
      words: []
    });
    setSubtitleTrack(state.track);
    addLog(`已於 ${curTime}s 處新增字幕段`, "info");
  });

  // 2. 合併下一句
  if (el.btnMergeSegments) {
    el.btnMergeSegments.addEventListener("click", () => {
      const idx = state.selectedSegmentIndex;
      const segs = state.track.segments;
      if (!segs.length || idx < 0 || idx >= segs.length - 1) {
        addLog("請先點選一句字幕（且其後方需有下一句）以進行合併", "error");
        return;
      }
      const cur = segs[idx];
      const next = segs[idx + 1];
      cur.end = next.end;
      cur.text = `${cur.text} ${next.text}`.trim();
      segs.splice(idx + 1, 1);
      setSubtitleTrack(state.track);
      addLog(`已將第 #${idx + 1} 句與下一句合併`, "success");
    });
  }

  // 3. 依標點拆句
  if (el.btnSplitByPunct) {
    el.btnSplitByPunct.addEventListener("click", () => {
      const idx = state.selectedSegmentIndex;
      const segs = state.track.segments;
      if (!segs.length || idx < 0 || idx >= segs.length) {
        addLog("請先點選要拆分的字幕句", "error");
        return;
      }
      const cur = segs[idx];
      const text = cur.text.trim();
      // 尋找中間附近的標點或空格
      const match = text.slice(1, -1).match(/[，。！？；、,.!?;:\s]+/);
      let splitPos = -1;
      if (match && match.index !== undefined) {
        splitPos = match.index + 1 + match[0].length;
      } else if (text.length >= 6) {
        splitPos = Math.floor(text.length / 2);
      }

      if (splitPos === -1) {
        addLog("此句字數過短，無法拆分", "error");
        return;
      }

      const part1 = text.slice(0, splitPos).trim();
      const part2 = text.slice(splitPos).trim();
      const ratio = part1.length / Math.max(1, text.length);
      const midTime = Number((cur.start + (cur.end - cur.start) * ratio).toFixed(2));

      const newSeg = {
        id: cur.id + 1,
        start: midTime,
        end: cur.end,
        text: part2,
        words: []
      };
      cur.end = midTime;
      cur.text = part1;
      segs.splice(idx + 1, 0, newSeg);
      setSubtitleTrack(state.track);
      addLog(`已將字幕拆分為「${part1}」與「${part2}」`, "success");
    });
  }

  // 4. 全體時間軸平移 (-0.5s / +0.5s)
  function shiftAllTimestamps(deltaSec) {
    if (!state.track.segments.length) return;
    state.track.segments.forEach(seg => {
      seg.start = Math.max(0, Number((seg.start + deltaSec).toFixed(2)));
      seg.end = Math.max(seg.start + 0.2, Number((seg.end + deltaSec).toFixed(2)));
    });
    setSubtitleTrack(state.track);
    updateSubtitleOverlayOnTime(el.video.currentTime);
    addLog(`已將全體字幕時間軸平移 ${deltaSec > 0 ? '+' : ''}${deltaSec} 秒`, "info");
  }

  if (el.btnOffsetMinus) el.btnOffsetMinus.addEventListener("click", () => shiftAllTimestamps(-0.5));
  if (el.btnOffsetPlus) el.btnOffsetPlus.addEventListener("click", () => shiftAllTimestamps(0.5));

  // 5. 清空字幕
  el.btnClearSubtitles.addEventListener("click", () => {
    if (confirm("確定要清空目前時間軸上的所有字幕嗎？")) {
      localStorage.removeItem("autosub_track_v1");
      setSubtitleTrack({ ...state.track, source_file: "", segments: [] });
      addLog("已清空字幕時間軸", "info");
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
  initFontManager();
}

// ---------------- 8.5 字型安裝與動態 @font-face 管理 ----------------
function injectDynamicFontFaces(installedFonts) {
  let styleEl = document.getElementById("dynamic-custom-fonts");
  if (!styleEl) {
    styleEl = document.createElement("style");
    styleEl.id = "dynamic-custom-fonts";
    document.head.appendChild(styleEl);
  }

  const rules = [];
  installedFonts.forEach(f => {
    if (f.url && f.family) {
      rules.push(`
@font-face {
  font-family: '${f.family.replace(/'/g, "\\'")}';
  src: url('${f.url}');
  font-display: swap;
}`);
      // 嘗試透過 FontFace API 立即預載入至瀏覽器畫面
      if (window.FontFace) {
        try {
          const ff = new FontFace(f.family, `url("${f.url}")`);
          ff.load().then(loaded => {
            document.fonts.add(loaded);
            applySubtitleStyleToOverlay();
          }).catch(() => {});
        } catch (e) {
          // ignore
        }
      }
    }
  });
  styleEl.textContent = rules.join("\n");
}

function populateFontSelectDropdown(installedFonts) {
  if (!el.selectFontName) return;
  const currentFont = state.style.font_name || "Noto Sans CJK TC";
  el.selectFontName.innerHTML = "";

  const customList = installedFonts.filter(f => f.category === "custom");
  const builtinList = installedFonts.filter(f => f.category !== "custom");

  if (customList.length > 0) {
    const grpCustom = document.createElement("optgroup");
    grpCustom.label = `★ 已安裝自訂字型 (${customList.length})`;
    customList.forEach(f => {
      const opt = document.createElement("option");
      opt.value = f.family;
      opt.textContent = `★ ${f.display_name}`;
      if (f.family === currentFont) opt.selected = true;
      grpCustom.appendChild(opt);
    });
    el.selectFontName.appendChild(grpCustom);
  }

  const grpBuiltin = document.createElement("optgroup");
  grpBuiltin.label = "系統內建字型";
  builtinList.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f.family;
    opt.textContent = f.display_name;
    if (f.family === currentFont) opt.selected = true;
    grpBuiltin.appendChild(opt);
  });
  el.selectFontName.appendChild(grpBuiltin);

  if (el.installedFontCountBadge) {
    el.installedFontCountBadge.textContent = customList.length > 0
      ? `已安裝 ${customList.length} 款自訂字型`
      : `目前僅系統字型`;
  }
}

function selectAndApplyFont(familyName, displayName) {
  state.style.font_name = familyName;
  if (el.selectFontName) {
    el.selectFontName.value = familyName;
  }
  applySubtitleStyleToOverlay();
  if (displayName) {
    addLog(`🔤 已切換字幕字型為：${displayName} (${familyName})`, "info");
  }
}

function renderFontManagerCatalog(catalog) {
  if (!el.fontCatalogList) return;
  el.fontCatalogList.innerHTML = "";

  const allItems = [
    ...(catalog.presets || []).map(p => ({ ...p, sourceType: "preset" })),
    ...(catalog.windows_fonts || []).map(w => ({ ...w, sourceType: "windows" }))
  ];

  // 也找出使用者自己上傳但不在 presets 清單中的自訂字型
  const presetFilenames = new Set(allItems.map(x => x.filename));
  const userUploadedCustom = (catalog.installed || []).filter(
    f => f.category === "custom" && !presetFilenames.has(f.filename)
  );

  userUploadedCustom.forEach(u => {
    allItems.unshift({
      id: u.id,
      family: u.family,
      display_name: u.display_name,
      filename: u.filename,
      description: `使用者上傳字型檔 (${u.size_mb} MB)`,
      installed: true,
      sourceType: "uploaded"
    });
  });

  allItems.forEach(item => {
    const row = document.createElement("div");
    const isCurrent = (state.style.font_name === item.family && item.installed);
    row.className = isCurrent
      ? "flex items-center justify-between p-2 rounded bg-indigo-950/40 border border-indigo-500/50 transition"
      : "flex items-center justify-between p-2 rounded bg-zinc-950/80 border border-zinc-800/90 hover:border-zinc-700 transition";

    const tagHtml = item.sourceType === "windows"
      ? `<span class="text-[9px] px-1 py-0.2 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">本機 Windows</span>`
      : (item.sourceType === "uploaded"
        ? `<span class="text-[9px] px-1 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">手動上傳</span>`
        : `<span class="text-[9px] px-1 py-0.2 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">開源商用</span>`);

    row.innerHTML = `
      <div class="overflow-hidden pr-2 flex-1">
        <div class="font-medium text-zinc-200 flex items-center gap-1.5 truncate">
          <span class="truncate" style="${item.installed ? `font-family: '${item.family}', sans-serif;` : ''}">${item.display_name}</span>
          ${tagHtml}
        </div>
        <div class="text-[10px] text-zinc-500 truncate">${item.description || item.family}</div>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        ${item.installed ? `
          <button class="btn-use-font px-2 py-1 ${isCurrent ? 'bg-indigo-600 text-white' : 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'} rounded text-[11px] transition">
            ${isCurrent ? '✓ 使用中' : '套用此字型'}
          </button>
          <button class="btn-del-font px-1.5 py-1 text-zinc-500 hover:text-red-400 rounded text-[11px]" title="移除此字型">✕</button>
        ` : `
          <button class="btn-install-preset-font px-2.5 py-1 bg-indigo-600/25 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/40 rounded text-[11px] font-medium transition">
            ${item.sourceType === 'windows' ? '📥 一鍵匯入' : '⬇ 一鍵安裝'}
          </button>
        `}
      </div>
    `;

    const btnInstall = row.querySelector(".btn-install-preset-font");
    if (btnInstall) {
      btnInstall.addEventListener("click", async () => {
        btnInstall.disabled = true;
        btnInstall.textContent = "⏳ 安裝中...";
        addLog(`正在安裝字型「${item.display_name}」...`);
        try {
          const res = await fetch("/api/fonts/install", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ preset_id: item.id })
          });
          const data = await res.json();
          if (data.status === "success") {
            applyFontCatalogData(data.catalog);
            selectAndApplyFont(data.font.family, data.font.display_name);
            addLog(`✔ 字型「${item.display_name}」安裝完成並已立即套用！`, "success");
          } else {
            throw new Error(data.detail || "安裝失敗");
          }
        } catch (err) {
          addLog(`字型安裝失敗: ${err.message}`, "error");
          btnInstall.disabled = false;
          btnInstall.textContent = "重試安裝";
        }
      });
    }

    const btnUse = row.querySelector(".btn-use-font");
    if (btnUse) {
      btnUse.addEventListener("click", () => {
        selectAndApplyFont(item.family, item.display_name);
        renderFontManagerCatalog(catalog);
      });
    }

    const btnDel = row.querySelector(".btn-del-font");
    if (btnDel && item.filename) {
      btnDel.addEventListener("click", async () => {
        if (!confirm(`確定要移除字型「${item.display_name}」(${item.filename}) 嗎？`)) return;
        try {
          const res = await fetch(`/api/fonts/${encodeURIComponent(item.filename)}`, { method: "DELETE" });
          const data = await res.json();
          if (data.status === "success") {
            if (state.style.font_name === item.family) {
              state.style.font_name = "Noto Sans CJK TC";
            }
            applyFontCatalogData(data.catalog);
            applySubtitleStyleToOverlay();
            addLog(`已移除字型: ${item.display_name}`, "info");
          }
        } catch (err) {
          addLog(`移除字型失敗: ${err.message}`, "error");
        }
      });
    }

    el.fontCatalogList.appendChild(row);
  });
}

function applyFontCatalogData(catalog) {
  if (!catalog) return;
  injectDynamicFontFaces(catalog.installed || []);
  populateFontSelectDropdown(catalog.installed || []);
  renderFontManagerCatalog(catalog);
}

async function loadFontCatalog() {
  try {
    const res = await fetch("/api/fonts");
    const catalog = await res.json();
    applyFontCatalogData(catalog);
  } catch (err) {
    console.error("Failed to load font catalog:", err);
  }
}

function initFontManager() {
  if (el.btnToggleFontManager && el.fontManagerPanel) {
    el.btnToggleFontManager.addEventListener("click", () => {
      const isHidden = el.fontManagerPanel.classList.contains("hidden");
      if (isHidden) {
        el.fontManagerPanel.classList.remove("hidden");
        loadFontCatalog();
      } else {
        el.fontManagerPanel.classList.add("hidden");
      }
    });
  }

  // 上傳本機 .ttf / .otf / .ttc 字型檔
  if (el.inputUploadFont) {
    el.inputUploadFont.addEventListener("change", async (e) => {
      const files = e.target.files;
      if (!files || !files.length) return;
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
      addLog(`正在上傳並解析 ${files.length} 個字型檔案...`);
      try {
        const res = await fetch("/api/fonts/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success" && data.installed && data.installed.length > 0) {
          applyFontCatalogData(data.catalog);
          const first = data.installed[0];
          selectAndApplyFont(first.family, first.display_name);
          addLog(`✔ 成功安裝並套用字型：${first.display_name} (Family: ${first.family})`, "success");
        } else {
          throw new Error(data.detail || "上傳字型失敗");
        }
      } catch (err) {
        addLog(`上傳字型失敗: ${err.message}`, "error");
      } finally {
        el.inputUploadFont.value = "";
      }
    });
  }

  // 從遠端 URL 下載安裝字型
  if (el.btnInstallFontUrl && el.inputFontUrl) {
    el.btnInstallFontUrl.addEventListener("click", async () => {
      const url = el.inputFontUrl.value.trim();
      if (!url) {
        addLog("請先輸入 .ttf 或 .otf 字型下載網址", "error");
        return;
      }
      el.btnInstallFontUrl.disabled = true;
      el.btnInstallFontUrl.textContent = "下載中...";
      addLog(`正在從網址下載字型: ${url}...`);
      try {
        const res = await fetch("/api/fonts/install", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (data.status === "success") {
          el.inputFontUrl.value = "";
          applyFontCatalogData(data.catalog);
          selectAndApplyFont(data.font.family, data.font.display_name);
          addLog(`✔ 網址字型安裝成功：${data.font.display_name} (${data.font.family})`, "success");
        } else {
          throw new Error(data.detail || "下載安裝失敗");
        }
      } catch (err) {
        addLog(`網址安裝字型失敗: ${err.message}`, "error");
      } finally {
        el.btnInstallFontUrl.disabled = false;
        el.btnInstallFontUrl.textContent = "網址安裝";
      }
    });
  }
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

function getExportStem() {
  if (state.video && state.video.filename) {
    return state.video.filename.replace(/\.[^.]+$/, "");
  }
  if (state.track && state.track.source_file) {
    return state.track.source_file.replace(/\.[^.]+$/, "");
  }
  return "subtitles";
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
    const outName = `${getExportStem()}.srt`;
    downloadTextFile(srt, outName);
    addLog(`已匯出 ${outName}`, "success");
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
    const outName = `${getExportStem()}.vtt`;
    downloadTextFile(vtt, outName);
    addLog(`已匯出 ${outName}`, "success");
  });

  el.btnExportJson.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    const outName = `${getExportStem()}.json`;
    downloadTextFile(JSON.stringify(state.track, null, 2), outName);
    addLog(`已匯出 ${outName}`, "success");
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
  // 0. 嘗試還原上次儲存的樣式
  try {
    const savedStyle = localStorage.getItem("autosub_style_v1");
    if (savedStyle) {
      Object.assign(state.style, JSON.parse(savedStyle));
    }
  } catch (e) {
    // ignore
  }

  initPlayer();
  initTabs();
  initUniversalDragAndDrop();
  initAiButtons();
  initEditorViewToggle();
  initStyleEditor();
  initExport();
  syncStateToControls();
  applySubtitleStyleToOverlay();

  // 1. 讀取並渲染字型庫與資產庫
  await loadFontCatalog();
  await loadAssetLibrary();

  // 2. 自動載入使用者最新上傳的影片與配對字幕（或還原暫存字幕）
  try {
    const userVideo = state.assets.find(a => !a.is_sample && a.type === "video");
    if (userVideo) {
      loadVideoAsset(userVideo);
      if (userVideo.paired_subtitle) {
        await loadSubtitleAsset(userVideo.paired_subtitle);
      } else {
        const savedTrack = localStorage.getItem("autosub_track_v1");
        if (savedTrack) {
          const parsed = JSON.parse(savedTrack);
          if (parsed && parsed.segments && parsed.segments.length > 0) {
            setSubtitleTrack(parsed);
          }
        }
      }
    }
  } catch (e) {
    console.error("Auto load check failed:", e);
  }

  updateWorkspaceSlots();
  addLog("AutoSubtitle AI Studio 系統初始化完成！(快捷鍵: Space 播放/暫停)", "success");
});
