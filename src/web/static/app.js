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
  packages: [],
  activePackage: null,
  packageLoading: false,
  packageBusy: false,
  savedSubtitle: "[]",
  savedScript: "",
  selectedSegmentIndex: 0,
  waveformPeaks: [],
  autoPauseAt: null,
  activeTab: "tab-assets",
  previewScaleMode: "fit",
  styleCustomized: false,
  justDraggedSubtitle: false,
  style: {
    font_name: "Noto Sans CJK TC",
    font_size: 36,
    primary_color: "#FFFFFF",
    outline_color: "#000000",
    outline_width: 2.5,
    outline_enabled: true,
    shadow_color: "#000000",
    shadow_offset: 2.0,
    bold: true,
    italic: false,
    letter_spacing: 1.0,
    opacity: 1.0,
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
  videoViewport: document.getElementById("video-viewport"),
  videoStage: document.getElementById("video-stage"),
  btnScaleFit: document.getElementById("btn-scale-fit"),
  btnScaleCompact: document.getElementById("btn-scale-compact"),
  btnScaleLarge: document.getElementById("btn-scale-large"),
  placeholder: document.getElementById("video-placeholder"),
  audioOnlyBackdrop: document.getElementById("audio-only-backdrop"),
  audioOnlyTrackName: document.getElementById("audio-only-track-name"),
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
  inputUploadFolder: document.getElementById("input-upload-folder"),
  packageSaveStatus: document.getElementById("package-save-status"),
  btnSavePackage: document.getElementById("btn-save-package"),
  btnDeletePackage: document.getElementById("btn-delete-package"),
  btnUpscaleActiveVideo: document.getElementById("btn-upscale-active-video"),
  modalUpscale: document.getElementById("modal-upscale"),
  btnCloseUpscaleModal: document.getElementById("btn-close-upscale-modal"),
  btnCancelUpscale: document.getElementById("btn-cancel-upscale"),
  btnConfirmUpscale: document.getElementById("btn-confirm-upscale"),
  upscaleTargetName: document.getElementById("upscale-target-name"),
  upscaleTargetMeta: document.getElementById("upscale-target-meta"),
  upscaleFramesInfo: document.getElementById("upscale-frames-info"),
  upscaleTimeEst: document.getElementById("upscale-time-est"),
  upscaleWarningBox: document.getElementById("upscale-warning-box"),
  upscaleWarningText: document.getElementById("upscale-warning-text"),
  selectUpscaleModel: document.getElementById("select-upscale-model"),
  upscalePreviewPkgName: document.getElementById("upscale-preview-pkg-name"),
  assetLibraryContainer: document.getElementById("asset-library-container"),
  btnRefreshAssets: document.getElementById("btn-refresh-assets"),
  btnModeUnscripted: document.getElementById("btn-mode-unscripted"),
  btnModeScripted: document.getElementById("btn-mode-scripted"),
  panelAiUnscripted: document.getElementById("panel-ai-unscripted"),
  panelAiScripted: document.getElementById("panel-ai-scripted"),
  checkAutoProofread: document.getElementById("check-auto-proofread"),
  selectLlmEngine: document.getElementById("select-llm-engine"),
  selectScriptMode: document.getElementById("select-script-mode"),
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
  selectLockedLlmEngine: document.getElementById("select-locked-llm-engine"),
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
  inputStylePreviewText: document.getElementById("input-style-preview-text"),
  btnResetPosition: document.getElementById("btn-reset-position"),
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
  sliderOpacity: document.getElementById("slider-opacity"),
  valOpacity: document.getElementById("val-opacity"),
  checkOutlineEnabled: document.getElementById("check-outline-enabled"),
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
  btnExportOpenshot: document.getElementById("btn-export-openshot"),
  btnExportJson: document.getElementById("btn-export-json"),
  burnVideoCard: document.getElementById("burn-video-card"),
  audioOnlyExportNotice: document.getElementById("audio-only-export-notice"),
  selectBurnRenderMode: document.getElementById("select-burn-render-mode"),
  btnStartBurn: document.getElementById("btn-start-burn"),
  burnResultBox: document.getElementById("burn-result-box"),
  linkDownloadBurned: document.getElementById("link-download-burned"),
  btnPreviewBurned: document.getElementById("btn-preview-burned"),
};

// 輔助日誌輸出
// ---------------- 長時間處理遮罩 (半透明覆蓋整頁) ----------------
let _busyTimer = null;
let _busyCancelHandler = null;

function showBusyOverlay(text = "處理中...", options = {}) {
  const ov = document.getElementById("busy-overlay");
  if (!ov) return;
  const txt = document.getElementById("busy-overlay-text");
  const elapsed = document.getElementById("busy-overlay-elapsed");
  const progressContainer = document.getElementById("busy-overlay-progress-container");
  const progressBar = document.getElementById("busy-overlay-progress-bar");
  const frameCount = document.getElementById("busy-overlay-frame-count");
  const percentText = document.getElementById("busy-overlay-percent");
  const etaWrapper = document.getElementById("busy-overlay-eta-wrapper");
  const etaText = document.getElementById("busy-overlay-eta");
  const detailText = document.getElementById("busy-overlay-detail");
  const btnCancel = document.getElementById("btn-cancel-busy-task");

  if (txt) txt.textContent = text;

  if (options.showProgress) {
    if (progressContainer) progressContainer.classList.remove("hidden");
    if (progressBar) progressBar.style.width = "0%";
    if (frameCount) frameCount.textContent = "0 / 0 幀";
    if (percentText) percentText.textContent = "0%";
    if (etaWrapper) etaWrapper.classList.remove("hidden");
    if (etaText) etaText.textContent = "計算中...";
    if (detailText) {
      detailText.textContent = "";
      detailText.classList.remove("hidden");
    }
  } else {
    if (progressContainer) progressContainer.classList.add("hidden");
    if (etaWrapper) etaWrapper.classList.add("hidden");
    if (detailText) detailText.classList.add("hidden");
  }

  if (btnCancel) {
    if (options.onCancel) {
      btnCancel.classList.remove("hidden");
      _busyCancelHandler = options.onCancel;
      btnCancel.onclick = () => {
        if (_busyCancelHandler) _busyCancelHandler();
      };
    } else {
      btnCancel.classList.add("hidden");
      btnCancel.onclick = null;
      _busyCancelHandler = null;
    }
  }

  const t0 = Date.now();
  const tick = () => {
    const s = Math.floor((Date.now() - t0) / 1000);
    if (elapsed) elapsed.textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };
  tick();
  clearInterval(_busyTimer);
  _busyTimer = setInterval(tick, 1000);
  ov.classList.remove("hidden");
  ov.classList.add("flex");
}

function updateBusyProgress(data = {}) {
  const progressBar = document.getElementById("busy-overlay-progress-bar");
  const frameCount = document.getElementById("busy-overlay-frame-count");
  const percentText = document.getElementById("busy-overlay-percent");
  const etaText = document.getElementById("busy-overlay-eta");
  const detailText = document.getElementById("busy-overlay-detail");
  const txt = document.getElementById("busy-overlay-text");

  const pct = Math.max(0, Math.min(100, data.percent || 0));
  if (progressBar) progressBar.style.width = `${pct}%`;
  if (percentText) percentText.textContent = `${pct}%`;
  if (frameCount && data.total_frames !== undefined) {
    frameCount.textContent = `${data.current_frame || 0} / ${data.total_frames} 幀`;
  }
  if (etaText && data.eta_text) {
    etaText.textContent = data.eta_text;
  }
  if (detailText && data.message) {
    detailText.textContent = data.message;
  }
  if (txt && data.stage_text) {
    txt.textContent = data.stage_text;
  }
}

function hideBusyOverlay() {
  const ov = document.getElementById("busy-overlay");
  clearInterval(_busyTimer);
  _busyTimer = null;
  _busyCancelHandler = null;
  const btnCancel = document.getElementById("btn-cancel-busy-task");
  if (btnCancel) {
    btnCancel.classList.add("hidden");
    btnCancel.onclick = null;
  }
  const progressContainer = document.getElementById("busy-overlay-progress-container");
  if (progressContainer) progressContainer.classList.add("hidden");
  const etaWrapper = document.getElementById("busy-overlay-eta-wrapper");
  if (etaWrapper) etaWrapper.classList.add("hidden");
  const detailText = document.getElementById("busy-overlay-detail");
  if (detailText) detailText.classList.add("hidden");

  if (!ov) return;
  ov.classList.add("hidden");
  ov.classList.remove("flex");
}

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
      // 若剛完成拖曳字幕，或點擊在字幕覆蓋層上，不觸發影片播放切換
      if (state.justDraggedSubtitle) return;
      if (e.target === el.overlay || (el.overlay && el.overlay.contains(e.target))) return;
      // 若佔位提示尚未隱藏，不攔截點擊
      if (el.placeholder && !el.placeholder.classList.contains("hidden")) return;
      togglePlayPause();
    });

    // 雙擊畫面切換全螢幕
    el.videoStage.addEventListener("dblclick", (e) => {
      if (e.target === el.overlay || (el.overlay && el.overlay.contains(e.target))) return;
      if (!document.fullscreenElement) {
        el.videoStage.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  // 高精度 60FPS 字幕同步渲染迴圈 (播放中即時比對起訖時間，段落結束毫秒級清空消失)
  let _subSyncRaf = null;
  function startSubtitleSyncLoop() {
    if (_subSyncRaf) cancelAnimationFrame(_subSyncRaf);
    function tick() {
      if (v && !v.paused && !v.ended) {
        updateSubtitleOverlayOnTime(v.currentTime);
        _subSyncRaf = requestAnimationFrame(tick);
      } else {
        _subSyncRaf = null;
      }
    }
    _subSyncRaf = requestAnimationFrame(tick);
  }

  function stopSubtitleSyncLoop() {
    if (_subSyncRaf) {
      cancelAnimationFrame(_subSyncRaf);
      _subSyncRaf = null;
    }
  }

  v.addEventListener("play", () => {
    el.iconPlay.classList.add("hidden");
    el.iconPause.classList.remove("hidden");
    if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.add("hidden");
    startSubtitleSyncLoop();
  });

  v.addEventListener("playing", () => {
    if (el.videoBufferingSpinner) el.videoBufferingSpinner.classList.add("hidden");
    startSubtitleSyncLoop();
  });

  v.addEventListener("pause", () => {
    stopSubtitleSyncLoop();
    el.iconPlay.classList.remove("hidden");
    el.iconPause.classList.add("hidden");
    if (el.videoCenterPlayBadge && state.activeTab !== "tab-style" && (!el.placeholder || el.placeholder.classList.contains("hidden"))) {
      el.videoCenterPlayBadge.classList.remove("hidden");
    }
    updateSubtitleOverlayOnTime(v.currentTime);
  });

  v.addEventListener("ended", () => {
    stopSubtitleSyncLoop();
    updateSubtitleOverlayOnTime(v.currentTime);
  });

  v.addEventListener("seeked", () => {
    updateSubtitleOverlayOnTime(v.currentTime);
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
    const isAudioOnly = state.video.isAudioOnly || !v.videoWidth || !v.videoHeight;
    state.video.isAudioOnly = isAudioOnly;
    state.video.duration = v.duration;
    state.video.width = v.videoWidth || 1920;
    state.video.height = v.videoHeight || 1080;
    if (el.audioOnlyBackdrop) {
      el.audioOnlyBackdrop.classList.toggle("hidden", !isAudioOnly);
    }

    // 計算原生長寬比與標籤
    const ratio = state.video.width / state.video.height;
    let ratioDesc = "";
    if (Math.abs(ratio - (16/9)) < 0.05) ratioDesc = " (16:9 橫式)";
    else if (Math.abs(ratio - (9/16)) < 0.05) ratioDesc = " (9:16 直式)";
    else if (Math.abs(ratio - (4/3)) < 0.05) ratioDesc = " (4:3)";
    else if (Math.abs(ratio - 1.0) < 0.05) ratioDesc = " (1:1 正方)";
    else if (ratio < 0.9) ratioDesc = " (直式)";
    else ratioDesc = " (橫式)";

    el.videoResolutionPill.textContent = isAudioOnly
      ? `🎵 純音訊 · 畫布 ${state.video.width}x${state.video.height}`
      : `${state.video.width}x${state.video.height}${ratioDesc}`;
    el.videoResolutionPill.classList.remove("hidden");
    el.placeholder.classList.add("hidden");

    // 自適應調整預設字級與邊距：若使用者尚未手動修改樣式，依據影片原生解析度比例自適應縮放，防止不同解析度下字級失衡
    if (!state.styleCustomized) {
      const minDim = Math.min(state.video.width || 1920, state.video.height || 1080);
      const refScale = Math.max(0.48, Math.min(1.5, minDim / 1080));
      state.style.font_size = Math.round(36 * refScale);
      state.style.padding_left = Math.max(16, Math.round(40 * (state.video.width / 1920)));
      state.style.padding_right = Math.max(16, Math.round(40 * (state.video.width / 1920)));
      state.style.padding_bottom = Math.max(20, Math.round(60 * (state.video.height / 1080)));
      state.style.padding_top = Math.max(20, Math.round(50 * (state.video.height / 1080)));
      syncStateToControls();
    }

    updateSummary();
    updateWorkspaceSlots();
    syncVideoStageDimensions();

    // 重新計算字型與座標縮放比，確保預覽與實體影片原樣 100% 貼合
    applySubtitleStyleToOverlay();
    updateSubtitleOverlayOnTime(v.currentTime || 0);
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
      updateSubtitleOverlayOnTime(v.currentTime);
    } else if (e.code === "ArrowRight" || e.key === "l" || e.key === "L") {
      e.preventDefault();
      state.autoPauseAt = null;
      v.currentTime = Math.min(v.duration || 0, v.currentTime + 3);
      updateSubtitleOverlayOnTime(v.currentTime);
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
        updateSubtitleOverlayOnTime(targetTime);
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
    state.previewScaleMode = mode;
    if (!el.btnScaleFit) return;
    el.btnScaleFit.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";
    el.btnScaleCompact.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";
    el.btnScaleLarge.className = "px-2 py-0.5 rounded text-zinc-400 hover:text-white transition";

    if (mode === "compact") {
      el.btnScaleCompact.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
    } else if (mode === "large") {
      el.btnScaleLarge.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
    } else {
      el.btnScaleFit.className = "px-2 py-0.5 rounded bg-blue-600 text-white font-medium transition";
    }

    syncVideoStageDimensions();
    setTimeout(() => {
      syncVideoStageDimensions();
      applySubtitleStyleToOverlay();
    }, 30);
  }

  if (el.btnScaleFit) el.btnScaleFit.addEventListener("click", () => setPreviewSize("fit"));
  if (el.btnScaleCompact) el.btnScaleCompact.addEventListener("click", () => setPreviewSize("compact"));
  if (el.btnScaleLarge) el.btnScaleLarge.addEventListener("click", () => setPreviewSize("large"));

  // 監聽視窗或影片容器尺寸變更，即時維持等比錨定
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(() => {
      syncVideoStageDimensions();
      applySubtitleStyleToOverlay();
    });
    if (el.videoViewport) ro.observe(el.videoViewport);
    if (el.video) ro.observe(el.video);
  } else {
    window.addEventListener("resize", () => {
      syncVideoStageDimensions();
      applySubtitleStyleToOverlay();
    });
  }

  // 進度拖曳
  el.scrubber.addEventListener("input", (e) => {
    if (v.duration) {
      v.currentTime = (e.target.value / 100) * v.duration;
      updateSubtitleOverlayOnTime(v.currentTime);
    }
  });

  // 快進快退
  document.getElementById("btn-seek-backward").addEventListener("click", () => {
    v.currentTime = Math.max(0, v.currentTime - 3);
    updateSubtitleOverlayOnTime(v.currentTime);
  });
  document.getElementById("btn-seek-forward").addEventListener("click", () => {
    v.currentTime = Math.min(v.duration, v.currentTime + 3);
    updateSubtitleOverlayOnTime(v.currentTime);
  });

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

// 精準計算並同步 #video-stage 與 #main-video 寬高 (完美支援 9:16 直式與 16:9 橫式，防止 CSS max-h-full 爆框裁切)
function syncVideoStageDimensions() {
  const vp = el.videoViewport;
  const v = el.video;
  const stage = el.videoStage;
  if (!vp || !v || !stage) return;

  // 若尚未載入任何影片，清除固定寬高讓 placeholder 正常展示
  if (!state.video.filename && !v.videoWidth) {
    stage.style.width = "";
    stage.style.height = "";
    v.style.width = "";
    v.style.height = "";
    return;
  }

  const vidW = v.videoWidth || state.video.width || 1920;
  const vidH = v.videoHeight || state.video.height || 1080;

  const availW = Math.max(180, vp.clientWidth - 24);
  let availH = Math.max(180, vp.clientHeight - 24);

  if (state.previewScaleMode === "compact") {
    availH = Math.min(availH, 300);
  } else if (state.previewScaleMode === "large") {
    availH = Math.min(availH, 560);
  }

  const scale = Math.min(availW / vidW, availH / vidH);
  const stageW = Math.max(120, Math.floor(vidW * scale));
  const stageH = Math.max(90, Math.floor(vidH * scale));

  stage.style.width = `${stageW}px`;
  stage.style.height = `${stageH}px`;
  v.style.width = `${stageW}px`;
  v.style.height = `${stageH}px`;
}

// 取得預覽畫面相對於影片原生實體解析度的縮放比例
function getPreviewScale() {
  const v = el.video;
  const vidH = (v && v.videoHeight) || state.video.height || 1080;
  const clientH = (el.videoStage && el.videoStage.clientHeight) || (v && v.clientHeight) || 0;
  if (!vidH || !clientH) return 1.0;
  return clientH / vidH;
}

// ---------------- 2. 即時字幕覆蓋層渲染 (CSS Box Model) ----------------
function applySubtitleStyleToOverlay() {
  syncVideoStageDimensions();
  const s = state.style;
  const overlay = el.overlay;
  const container = el.overlayContainer;
  if (!overlay || !container) return;
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

  // 2. 文字外觀與特效 (依據影片原生解析度等比縮放，支援亞像素平滑渲染)
  const fontSize = Math.max(6, Number((s.font_size * scale).toFixed(1)));
  const outlineWidth = Math.max(0.0, (s.outline_width * scale)).toFixed(1);
  const shadowDist = (s.shadow_offset * scale).toFixed(1);

  overlay.style.fontFamily = `"${s.font_name}", sans-serif`;
  overlay.style.fontSize = `${fontSize}px`;
  // 字幕框左右內距 = 影片原生 4px 等比縮放 (與後端 ASS 燒錄計算一致，避免預覽與硬字幕位置偏移)
  overlay.style.paddingLeft = `${(4 * scale).toFixed(2)}px`;
  overlay.style.paddingRight = `${(4 * scale).toFixed(2)}px`;
  overlay.style.lineHeight = "1.5";
  overlay.style.color = s.primary_color;
  overlay.style.fontWeight = s.bold ? "bold" : "normal";
  overlay.style.fontStyle = s.italic ? "italic" : "normal";
  overlay.style.letterSpacing = `${(s.letter_spacing * scale).toFixed(1)}px`;
  overlay.style.opacity = s.opacity !== undefined ? s.opacity : 1.0;

  // 描邊字 (外側向外生長 + 獨立開關)
  const isOutlineOn = s.outline_enabled !== false && Number(outlineWidth) > 0;
  if (isOutlineOn) {
    // 透過 paint-order: stroke fill 確保字形 fill 繪製在 stroke 上方，讓描邊完全只往外側生長，不侵蝕內部字體
    const strokeDiameter = (Number(outlineWidth) * 2).toFixed(1);
    overlay.style.webkitTextStroke = `${strokeDiameter}px ${s.outline_color}`;
    overlay.style.paintOrder = "stroke fill";
    overlay.style.webkitPaintOrder = "stroke fill";
  } else {
    overlay.style.webkitTextStroke = "0px transparent";
    overlay.style.paintOrder = "normal";
    overlay.style.webkitPaintOrder = "normal";
  }

  // 陰影字
  overlay.style.textShadow = Number(shadowDist) > 0
    ? `${shadowDist}px ${shadowDist}px ${(shadowDist * 1.5).toFixed(1)}px ${s.shadow_color}`
    : "none";

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
  if (!el.cssLiveCode) return;
  const s = state.style;
  const writingMode = s.orientation === "vertical" ? "vertical-rl" : "horizontal-tb";
  const isOutlineOn = s.outline_enabled !== false && s.outline_width > 0;
  const strokeCss = isOutlineOn
    ? `-webkit-text-stroke: ${(s.outline_width * 2).toFixed(1)}px ${s.outline_color};\npaint-order: stroke fill;`
    : `-webkit-text-stroke: 0px transparent;`;

  const css = `/* Subtitle Web CSS Preset */
font-family: '${s.font_name}', sans-serif;
font-size: ${s.font_size}px;
color: ${s.primary_color};
font-weight: ${s.bold ? 'bold' : 'normal'};
font-style: ${s.italic ? 'italic' : 'normal'};
${strokeCss}
text-shadow: ${s.shadow_offset}px ${s.shadow_offset}px ${(s.shadow_offset*1.5).toFixed(1)}px ${s.shadow_color};
opacity: ${s.opacity !== undefined ? s.opacity : 1.0};
writing-mode: ${writingMode};
text-align: ${s.horizontal_align};
vertical-align: ${s.vertical_align};
padding: ${s.padding_top}px ${s.padding_right}px ${s.padding_bottom}px ${s.padding_left}px;
letter-spacing: ${s.letter_spacing}px;`;

  el.cssLiveCode.value = css;
}

// 確保在「3. 樣式與位置」調整樣式時，畫面上能即時預覽外觀效果
function ensureSubtitlePreviewVisible() {
  if (!el.overlay) return;
  const segs = (state.track && state.track.segments) ? state.track.segments : [];
  if (segs.length > 0) {
    if (state.selectedSegmentIndex < 0 || state.selectedSegmentIndex >= segs.length) {
      state.selectedSegmentIndex = 0;
    }
    const curTime = el.video ? (el.video.currentTime || 0) : 0;
    const activeSeg = segs.find(seg => curTime >= seg.start && curTime <= seg.end);

    if (activeSeg) {
      renderOverlayText(activeSeg.text || `[#${activeSeg.id}]`);
      if (el.selectedSubBadge) {
        el.selectedSubBadge.textContent = `目前選擇: 第 ${activeSeg.id} 句 (${activeSeg.start.toFixed(2)}s)`;
      }
    } else {
      // 若當前時間不在任何字幕時間軸區間內：
      // 僅在使用者處於【3. 樣式與位置】頁籤且影片為【暫停狀態】（手動調整樣式滑桿）時顯示所選字幕供外觀微調
      if (state.activeTab === "tab-style" && (el.video ? el.video.paused : true)) {
        const targetSeg = segs[state.selectedSegmentIndex] || segs[0];
        const fallbackText = (el.inputStylePreviewText && el.inputStylePreviewText.value.trim())
          ? el.inputStylePreviewText.value.trim()
          : "字幕樣式與位置即時預覽 Sample";
        const textToShow = (targetSeg && targetSeg.text && targetSeg.text.trim())
          ? targetSeg.text
          : `[#${targetSeg ? targetSeg.id : 1}] ${fallbackText}`;
        renderOverlayText(textToShow);
        if (el.selectedSubBadge && targetSeg) {
          el.selectedSubBadge.textContent = `樣式預覽: 第 ${targetSeg.id} 句 (${targetSeg.start.toFixed(2)}s)`;
        }
      } else {
        // 其餘情況（播放中、或非樣式頁籤），不在時間軸內一律消失！
        renderOverlayText("");
      }
    }
  } else {
    if (state.activeTab === "tab-style") {
      const sampleText = (el.inputStylePreviewText && el.inputStylePreviewText.value.trim())
        ? el.inputStylePreviewText.value.trim()
        : "字幕樣式與位置即時預覽 Sample";
      renderOverlayText(sampleText);
    } else {
      renderOverlayText("");
    }
  }
}

// 根據時間戳更新字幕 (關鍵修正：不在時間軸內的字幕必須立即消失！)
function updateSubtitleOverlayOnTime(currentTime) {
  const segs = (state.track && state.track.segments) ? state.track.segments : [];
  if (segs.length === 0) {
    renderOverlayText("");
    return;
  }

  // 嚴格判定當前時間是否落入字幕區間 [seg.start, seg.end]
  const activeSeg = segs.find(seg => currentTime >= seg.start && currentTime <= seg.end);

  if (activeSeg) {
    const activeIdx = segs.indexOf(activeSeg);
    if (activeIdx !== -1) state.selectedSegmentIndex = activeIdx;
    renderOverlayText(activeSeg.text || `[#${activeSeg.id} 斷點區間]`);
    highlightActiveSegmentInList(activeSeg.id);
    if (el.selectSubtitleLine && state.activeTab === "tab-style") {
      el.selectSubtitleLine.value = String(state.selectedSegmentIndex);
    }
  } else {
    // 當前時間點不在任何字幕區間內，字幕必須立即消失！
    renderOverlayText("");
    highlightActiveSegmentInList(null);
  }
}

function renderOverlayText(text) {
  if (el.overlay) {
    const str = (text !== null && text !== undefined)
      ? String(text).replace(/<br\s*\/?>/gi, "\n").replace(/\\N/g, "\n")
      : "";
    el.overlay.textContent = str;
    el.overlay.style.whiteSpace = "pre-wrap";
    if (!str.trim()) {
      el.overlay.style.display = "none";
    } else {
      el.overlay.style.display = "";
    }
  }
}

function saveSessionToStorage() {
  try {
    localStorage.setItem("autosub_style_v1", JSON.stringify(state.style));
  } catch (error) {
    // Browser storage is optional; the SRT is saved on disk.
  }
  schedulePackageSave();
}

// 更新頂部「當前工作台掛載看板 (Active Workspace Slots)」
function updateWorkspaceSlots() {
  // 1. 影音來源槽狀態
  if (state.video.filename) {
    const audioOnly = !!state.video.isAudioOnly;
    if (el.btnUpscaleActiveVideo) el.btnUpscaleActiveVideo.classList.toggle("hidden", audioOnly);
    if (el.burnVideoCard) el.burnVideoCard.classList.toggle("hidden", audioOnly);
    if (el.audioOnlyExportNotice) el.audioOnlyExportNotice.classList.toggle("hidden", !audioOnly);
    el.slotCardVideo.className = "p-2.5 rounded-lg bg-blue-950/20 border border-blue-500/40 flex flex-col justify-between gap-1.5 transition";
    el.slotVideoStatus.className = "px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-medium";
    el.slotVideoStatus.textContent = "● 使用中";
    el.slotVideoName.textContent = state.video.filename;
    el.slotVideoName.className = "text-xs font-semibold text-blue-200 truncate";
    const durStr = state.video.duration ? ` • ${state.video.duration.toFixed(1)}s` : "";
    el.slotVideoMeta.textContent = state.video.isAudioOnly
      ? `🎵 純音訊模式${durStr}`
      : `${state.video.width}x${state.video.height}${durStr}`;
  } else {
    if (el.btnUpscaleActiveVideo) el.btnUpscaleActiveVideo.classList.add("hidden");
    if (el.burnVideoCard) el.burnVideoCard.classList.remove("hidden");
    if (el.audioOnlyExportNotice) el.audioOnlyExportNotice.classList.add("hidden");
    el.slotCardVideo.className = "p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 flex flex-col justify-between gap-1.5 transition";
    el.slotVideoStatus.className = "px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 text-[10px]";
    el.slotVideoStatus.textContent = "未載入";
    el.slotVideoName.textContent = "請從下方選擇或拖入影片 / 音檔";
    el.slotVideoName.className = "text-xs font-semibold text-zinc-400 truncate";
    el.slotVideoMeta.textContent = "支援 MP4 / MOV / WAV / MP3";
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
      state.activeTab = targetId;

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
        // 在樣式與位置頁籤中隱藏中央大播放鈕，避免遮擋置中字幕與干擾滑鼠拖曳
        if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.add("hidden");
        updateSubtitleSelectDropdown();
        syncStateToControls();
        applySubtitleStyleToOverlay();
        ensureSubtitlePreviewVisible();
      } else {
        if (el.video && el.video.paused && el.videoCenterPlayBadge && (!el.placeholder || el.placeholder.classList.contains("hidden"))) {
          el.videoCenterPlayBadge.classList.remove("hidden");
        }
        // 切換離開樣式頁籤時，立即校準時間軸狀態：若不在時間軸內立即消失
        updateSubtitleOverlayOnTime(el.video ? el.video.currentTime : 0);
      }
    });
  });
}

// ---------------- 4. Tab 1: 分類資產媒體庫 (Categorized Asset Library) ----------------
function subtitleFingerprint() {
  return JSON.stringify(state.track.segments.map(segment => [segment.start, segment.end, segment.text]));
}

function packageHasChanges() {
  return !!state.activePackage && !state.packageLoading && (
    subtitleFingerprint() !== state.savedSubtitle || el.alignScriptTextarea.value !== state.savedScript
  );
}

function setPackageSaveStatus(text, failed = false) {
  if (el.packageSaveStatus) {
    el.packageSaveStatus.textContent = text;
    el.packageSaveStatus.className = failed ? "text-xs text-red-400" : "text-xs text-zinc-400";
  }
  if (el.btnDeletePackage) {
    if (state.activePackage) {
      el.btnDeletePackage.classList.remove("hidden");
    } else {
      el.btnDeletePackage.classList.add("hidden");
    }
  }
}

let packageSaveTimer = null;
let packageSavePromise = null;

async function saveActivePackage() {
  clearTimeout(packageSaveTimer);
  if (packageSavePromise) return packageSavePromise;
  packageSavePromise = (async () => {
    while (packageHasChanges()) {
      const current = state.activePackage;
      const subtitle = subtitleFingerprint();
      const script = el.alignScriptTextarea.value;
      const payload = { path: current.path };
      if (subtitle !== state.savedSubtitle) payload.track = state.track;
      if (script !== state.savedScript) payload.script_text = script;
      setPackageSaveStatus("正在儲存至資產包…");
      const response = await fetch("/api/packages/save", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "儲存失敗");
      state.savedSubtitle = subtitle;
      state.savedScript = script;
      state.activePackage = data.package;
      state.packages = state.packages.map(item => item.path === current.path ? data.package : item);
      state.track.source_file = data.package.subtitle ? data.package.subtitle.name : state.track.source_file;
      renderFilteredAssetLibrary();
    }
    if (state.activePackage) setPackageSaveStatus("已儲存至資產包");
  })();
  try {
    await packageSavePromise;
  } catch (error) {
    setPackageSaveStatus("儲存失敗，請重試", true);
    throw error;
  } finally {
    packageSavePromise = null;
  }
}

function schedulePackageSave() {
  if (!packageHasChanges()) return;
  setPackageSaveStatus("尚有變更，等待儲存…");
  clearTimeout(packageSaveTimer);
  packageSaveTimer = setTimeout(() => {
    saveActivePackage().catch(error => addLog(`資產包儲存失敗：${error.message}`, "error"));
  }, 600);
}

async function openPackage(path) {
  if (state.packageBusy) return;
  state.packageBusy = true;
  showBusyOverlay("正在開啟資產包…");
  try {
    await saveActivePackage();
    const response = await fetch("/api/packages/open", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "開啟失敗");
    state.packageLoading = true;
    state.activePackage = data.package;
    state.waveformPeaks = [];
    state.selectedSegmentIndex = 0;
    state.autoPauseAt = null;
    el.video.pause();
    loadVideoAsset(data.package.media);
    el.alignScriptTextarea.value = data.script_text;
    if (data.script_text && el.btnModeScripted) el.btnModeScripted.click();
    if (!data.script_text && el.btnModeUnscripted) el.btnModeUnscripted.click();
    setSubtitleTrack(data.track);
    state.savedSubtitle = subtitleFingerprint();
    state.savedScript = data.script_text;
    try { localStorage.setItem("autosub_package_v1", data.package.path); } catch (error) {}
    setPackageSaveStatus(data.package.subtitle ? "已載入包內 SRT" : "尚無 SRT，編輯後自動建立");
    renderFilteredAssetLibrary();
    addLog(`已開啟資產包「${data.package.name}」，影片、原稿與字幕已同步載入`, "success");
  } catch (error) {
    addLog(`開啟資產包失敗：${error.message}`, "error");
  } finally {
    state.packageLoading = false;
    state.packageBusy = false;
    hideBusyOverlay();
  }
}

function clearPackageWorkspace() {
  state.packageLoading = true;
  state.activePackage = null;
  state.waveformPeaks = [];
  state.video = { filename: "", path: "", url: "", duration: 0, width: 1920, height: 1080, isAudioOnly: false };
  el.video.pause();
  el.video.removeAttribute("src");
  el.video.load();
  el.videoFilename.textContent = "未載入影音";
  el.mediaBadge.textContent = "未載入影音";
  el.placeholder.classList.remove("hidden");
  if (el.audioOnlyBackdrop) el.audioOnlyBackdrop.classList.add("hidden");
  if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.add("hidden");
  el.alignScriptTextarea.value = "";
  setSubtitleTrack({ source_file: "", segments: [], duration: 0, language: "zh" });
  try { localStorage.removeItem("autosub_package_v1"); } catch (error) {}
  setPackageSaveStatus("未開啟資產包");
  state.packageLoading = false;
}

async function managePackage(action, item) {
  if (state.packageBusy) return;
  let destination = item.path;
  if (action === "delete") {
    if (!confirm(`確定要永久刪除「${item.name || item.path}」資產包及其中的影片、原詞與 SRT？此操作無法復原。`)) return;
  } else {
    const value = prompt(action === "rename" ? "資產包的新名稱" : "資產庫內的目標路徑，例如：客戶A/訪談", action === "rename" ? item.name : item.path);
    if (!value || !value.trim()) return;
    if (action === "rename") {
      if (/[\\/]/.test(value)) { addLog("名稱不能包含路徑分隔符號，請使用移動功能", "error"); return; }
      const parent = item.path.includes("/") ? item.path.slice(0, item.path.lastIndexOf("/") + 1) : "";
      destination = parent + value.trim();
    } else destination = value.trim();
  }
  state.packageBusy = true;
  showBusyOverlay(action === "delete" ? "正在刪除資產包…" : "正在更新資產包…");
  let reopen = null;
  try {
    if (action !== "delete") {
      await saveActivePackage();
    } else if (state.activePackage && state.activePackage.path === item.path) {
      clearPackageWorkspace();
    }
    const response = await fetch(action === "delete" ? `/api/packages?path=${encodeURIComponent(item.path)}` : "/api/packages/move", {
      method: action === "delete" ? "DELETE" : "POST",
      headers: { "Content-Type": "application/json" },
      ...(action === "delete" ? {} : { body: JSON.stringify({ path: item.path, destination }) })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "操作失敗");
    if (state.activePackage && state.activePackage.path === item.path) {
      if (action === "delete") clearPackageWorkspace();
      else reopen = data.package.path;
    }
    await loadAssetLibrary();
    if (action === "delete") {
      addLog(`已成功刪除資產包「${item.name || item.path}」`, "success");
    }
  } catch (error) {
    addLog(`資產包操作失敗：${error.message}`, "error");
  } finally {
    state.packageBusy = false;
    hideBusyOverlay();
  }
  if (reopen) await openPackage(reopen);
}

async function loadAssetLibrary() {
  try {
    const response = await fetch("/api/assets");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "讀取失敗");
    state.packages = data.packages || [];
    renderFilteredAssetLibrary();
  } catch (error) {
    el.assetLibraryContainer.textContent = `讀取資產包失敗：${error.message}`;
  }
}

function renderFilteredAssetLibrary() {
  const container = el.assetLibraryContainer;
  container.innerHTML = "";
  if (!state.packages.length) {
    const empty = document.createElement("div");
    empty.className = "text-xs text-zinc-500 py-4 text-center";
    empty.textContent = "選取影片、SRT 與原稿建立資產包，或匯入已整理好的資料夾";
    container.appendChild(empty);
    return;
  }
  state.packages.forEach(item => {
    const card = document.createElement("div");
    const active = state.activePackage && state.activePackage.path === item.path;
    card.className = `p-3 rounded-lg border space-y-2 ${active ? 'bg-blue-950/30 border-blue-500/60' : 'bg-zinc-900 border-zinc-800'}`;
    card.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <span class="package-name font-medium text-xs text-zinc-200 truncate"></span>
        <button class="package-open px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded">${active ? '重新載入' : '開啟資產包'}</button>
      </div>
      <div class="package-files text-[11px] text-zinc-400 break-all whitespace-pre-line"></div>
      <div class="flex gap-3 text-[11px] text-zinc-500">
        <button class="package-rename hover:text-zinc-200 transition">重新命名</button>
        <button class="package-move hover:text-zinc-200 transition">移動</button>
        <button class="package-upscale text-violet-400 hover:text-violet-300 transition">✨ AI 放大</button>
        <button class="package-delete text-red-400/80 hover:text-red-400 transition">🗑️ 刪除資產</button>
      </div>`;
    if (item.error) {
      card.textContent = `📁 ${item.path}：${item.error}`;
      container.appendChild(card);
      return;
    }
    const isAudioPkg = item.media && (item.media.type === "audio" || /\.(wav|mp3|m4a|aac|flac|ogg)$/i.test(item.media.name || ""));
    card.querySelector(".package-name").textContent = `📁 ${item.path}${active ? ' · 使用中' : ''}`;
    card.querySelector(".package-files").textContent = [
      `${isAudioPkg ? '🎵' : '🎬'} ${item.media.name}`,
      item.subtitle ? `📝 ${item.subtitle.name} · ${item.subtitle.segment_count || 0} 句` : "📝 尚無 SRT",
      item.script ? `📄 ${item.script.name}` : "📄 尚無原詞（選填）"
    ].join("\n");
    card.querySelector(".package-open").addEventListener("click", () => openPackage(item.path));
    const upscaleBtn = card.querySelector(".package-upscale");
    if (upscaleBtn) {
      if (isAudioPkg) {
        upscaleBtn.classList.add("hidden");
      } else {
        upscaleBtn.addEventListener("click", () => openUpscaleModal({
          package_path: item.path,
          media_name: item.media ? item.media.name : item.path,
          target_name: `資產包: ${item.path}`,
          meta_info: item.media ? `原始影片: ${item.media.name} (${item.media.size_mb || 0} MB)` : "準備就緒"
        }));
      }
    }
    for (const action of ["rename", "move", "delete"]) {
      card.querySelector(`.package-${action}`).addEventListener("click", () => managePackage(action, item));
    }
    container.appendChild(card);
  });
}

function loadVideoAsset(asset) {
  const isAudioOnly = (asset.type === "audio") || /\.(wav|mp3|m4a|aac|flac|ogg)$/i.test(asset.name || "");
  state.video.filename = asset.name;
  state.video.url = asset.url;
  state.video.path = asset.absolute_path;
  state.video.isAudioOnly = isAudioOnly;
  el.video.src = asset.url;
  el.video.load();
  el.videoFilename.textContent = asset.name;
  el.mediaBadge.textContent = `${isAudioOnly ? '🎵 ' : ''}${asset.name}`;
  el.placeholder.classList.add("hidden");
  if (el.audioOnlyBackdrop) el.audioOnlyBackdrop.classList.toggle("hidden", !isAudioOnly);
  if (el.audioOnlyTrackName) el.audioOnlyTrackName.textContent = asset.name;
  if (el.videoCenterPlayBadge) el.videoCenterPlayBadge.classList.remove("hidden");
  updateWorkspaceSlots();
}

// ---------------- 5. 檔案上傳與全域拖放 (Drag & Drop) ----------------
async function handleBatchFileUpload(files) {
  if (!files || !files.length || state.packageBusy) return;
  state.packageBusy = true;
  showBusyOverlay("正在匯入資產包…");
  let openPath = null;
  try {
    await saveActivePackage();
    const formData = new FormData();
    const createsPackage = Array.from(files).some(file => /\.(mp4|mov|mkv|webm|avi|flv|wav|mp3|m4a|aac|flac|ogg)$/i.test(file.name));
    if (!createsPackage && state.activePackage) formData.append("package_path", state.activePackage.path);
    for (const file of files) formData.append("files", file, file.webkitRelativePath || file.name);
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "匯入失敗");
    await loadAssetLibrary();
    if (data.packages.length) openPath = data.packages[0].path;
    if (data.fonts.length) {
      await loadFontCatalog();
      selectAndApplyFont(data.fonts[0].family, data.fonts[0].display_name);
    }
    addLog(`已匯入 ${data.packages.length} 個資產包`, "success");
  } catch (error) {
    addLog(`匯入失敗：${error.message}`, "error");
  } finally {
    state.packageBusy = false;
    hideBusyOverlay();
    el.inputUploadFiles.value = "";
    if (el.inputUploadFolder) el.inputUploadFolder.value = "";
  }
  if (openPath) await openPackage(openPath);
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

  el.inputUploadFiles.addEventListener("change", event => handleBatchFileUpload(event.target.files));
  el.inputUploadFolder.addEventListener("change", event => handleBatchFileUpload(event.target.files));
  el.btnRefreshAssets.addEventListener("click", loadAssetLibrary);
  el.btnSavePackage.addEventListener("click", () => saveActivePackage().catch(error => addLog(error.message, "error")));
  if (el.btnDeletePackage) {
    el.btnDeletePackage.addEventListener("click", () => {
      if (state.activePackage) {
        managePackage("delete", state.activePackage);
      }
    });
  }
  el.alignScriptTextarea.addEventListener("input", schedulePackageSave);
  window.addEventListener("beforeunload", event => {
    if (packageHasChanges()) { event.preventDefault(); event.returnValue = ""; }
  });
  window.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      saveActivePackage().catch(error => addLog(error.message, "error"));
    }
  });
}

// ---------------- 6. AI 功能按鈕與模式切換 ----------------
let subtitleRequestId = 0;
function captureSubtitleRequest() {
  return {
    id: ++subtitleRequestId, track: state.track, media: state.video.path,
    packagePath: state.activePackage?.path, content: subtitleFingerprint(),
    script: el.alignScriptTextarea.value, editorText: el.rawSubtitleTextarea.value
  };
}

function canApplySubtitleResult(request) {
  if (request.id !== subtitleRequestId || request.track !== state.track ||
      request.media !== state.video.path || request.packagePath !== state.activePackage?.path ||
      request.content !== subtitleFingerprint() || request.script !== el.alignScriptTextarea.value ||
      request.editorText !== el.rawSubtitleTextarea.value || state.packageBusy) {
    addLog("工作區已變更，已略過過期結果，保留目前字幕。", "info");
    return false;
  }
  return true;
}

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

  // 雙向即時連動：Tab 1 大腦引擎 <-> Tab 2 鎖定填字校對引擎
  const syncLlmEngine = (val) => {
    if (el.selectLlmEngine) el.selectLlmEngine.value = val;
    if (el.selectLockedLlmEngine) el.selectLockedLlmEngine.value = val;
    try { localStorage.setItem("autosub_llm_engine", val); } catch (e) {}
  };

  if (el.selectLlmEngine) {
    el.selectLlmEngine.addEventListener("change", (e) => syncLlmEngine(e.target.value));
  }
  if (el.selectLockedLlmEngine) {
    el.selectLockedLlmEngine.addEventListener("change", (e) => syncLlmEngine(e.target.value));
  }

  // 雙向即時連動：Tab 1 校對開關 <-> Tab 2 鎖定填字校對開關
  const syncProofreadCheck = (checked) => {
    if (el.checkAutoProofread) el.checkAutoProofread.checked = checked;
    if (el.checkLockedProofread) el.checkLockedProofread.checked = checked;
    try { localStorage.setItem("autosub_auto_proofread", checked ? "1" : "0"); } catch (e) {}
  };

  if (el.checkAutoProofread) {
    el.checkAutoProofread.addEventListener("change", (e) => syncProofreadCheck(e.target.checked));
  }
  if (el.checkLockedProofread) {
    el.checkLockedProofread.addEventListener("change", (e) => syncProofreadCheck(e.target.checked));
  }

  // 還原上次儲存的 LLM 偏好設定
  try {
    const savedEngine = localStorage.getItem("autosub_llm_engine");
    if (savedEngine) syncLlmEngine(savedEngine);
    const savedProof = localStorage.getItem("autosub_auto_proofread");
    if (savedProof !== null) syncProofreadCheck(savedProof === "1");
  } catch (e) {}

  // AI 自動產生字幕 (單一入口：自動依據是否有填寫原詞智慧雙分流)
  if (el.btnAiTranscribe) {
    el.btnAiTranscribe.addEventListener("click", async () => {
      const media = state.video.path;
      if (!media) {
        addLog("請先在上方選擇或上傳影片後再執行產生字幕", "error");
        return;
      }

      const autoProofread = el.checkAutoProofread ? el.checkAutoProofread.checked : true;
      const llmProvider = el.selectLlmEngine ? el.selectLlmEngine.value : "local";
      const scriptText = el.alignScriptTextarea ? el.alignScriptTextarea.value.trim() : "";
      const scriptMode = el.selectScriptMode.value;

      if (scriptText) {
        const brainName = llmProvider === "local" ? "本地 Qwen2.5 (離線)" : "雲端 LLM API (.env)";
        const auditDescription = autoProofread ? `決策大腦: ${brainName}` : "AI 審核已關閉，保留 Whisper 時間結果";
        const modeName = scriptMode === "reference" ? "歌詞參考，可重複引用" : "完整逐句稿，固定順序";
        addLog(`【AI 產生字幕】${modeName}（${scriptText.split('\n').filter(Boolean).length} 行），啟動原生 Whisper (large-v3-turbo，原生)＋Luna 歌詞字幕管線 (${auditDescription})...`);
      } else {
        const brainName = llmProvider === "local" ? "本地 Qwen2.5" : "雲端 LLM API";
        addLog(`【AI 產生字幕】無稿模式，正在以 Whisper (large-v3-turbo，原生) 辨識${autoProofread ? ` 並由 ${brainName} 自動盲校錯字` : ''}...`);
      }

      el.btnAiTranscribe.disabled = true;
      el.btnAiTranscribe.textContent = scriptText 
        ? "⏳ 歌詞強制對齊與時間軸審核管線執行中..." 
        : (autoProofread ? "⏳ Whisper 語音辨識與錯字校對中..." : "⏳ Whisper 語音辨識中...");
      showBusyOverlay(scriptText
        ? "歌詞強制對齊與時間軸審核中，請稍候..."
        : "Whisper 語音辨識中，請稍候...");

      const formData = new FormData();
      formData.append("media_path", media);
      formData.append("device", "cuda");
      formData.append("prompt", "繁體中文");
      formData.append("auto_proofread", String(autoProofread));
      formData.append("llm_provider", llmProvider);
      if (scriptText) {
        formData.append("script_text", scriptText);
        formData.append("script_mode", scriptMode);
      }

      const request = captureSubtitleRequest();
      try {
        const res = await fetch("/api/ai/transcribe", { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
          if (!canApplySubtitleResult(request)) return;
          data.track.source_file = `${state.video.filename.replace(/\.[^.]+$/, '')}.ai.srt`;
          setSubtitleTrack(data.track);
          if (data.proofread_warning) {
            addLog(`字幕已保留，LLM 審核尚未全部完成：${data.proofread_warning}`, "error");
          } else if (data.has_reference) {
            addLog(`已生成 ${data.track.segments.length} 句字幕，診斷報告已儲存於 output/，請確認待複核項目。`, "success");
          } else {
            addLog(`【AI 辨識完成】已生成 ${data.track.segments.length} 句時間軸字幕！`, "success");
          }
        } else {
          throw new Error(data.detail || "辨識失敗");
        }
      } catch (err) {
        addLog(`辨識失敗: ${err.message}`, "error");
      } finally {
        hideBusyOverlay();
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
      const llmProvider = el.selectLlmEngine ? el.selectLlmEngine.value : "local";

      if (!scriptText) {
        addLog("請先選擇原稿 .txt 檔案或在文字框貼上歌詞/原稿內容", "error");
        return;
      }

      addLog(`【有稿對齊】啟動 Luna 管線將原稿與 ${state.video.filename} 強制對齊...`);
      el.btnAiAlign.disabled = true;
      el.btnAiAlign.textContent = "⏳ 強制對齊與時間軸審核中...";
      showBusyOverlay("歌詞強制對齊與時間軸審核中，請稍候...");

      const request = captureSubtitleRequest();
      try {
        const payload = { media_path: media, llm_provider: llmProvider };
        if (scriptText) payload.script_text = scriptText;

        const res = await fetch("/api/ai/align", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "success") {
          if (!canApplySubtitleResult(request)) return;
          data.track.source_file = `${state.video.filename.replace(/\.[^.]+$/, '')}.aligned.srt`;
          setSubtitleTrack(data.track);
          addLog(`【有稿對齊成功】生成 ${data.track.segments.length} 句 100% 原稿時間軸字幕（已輸出交付檔案）！`, "success");
        } else {
          throw new Error(data.detail || "對齊失敗");
        }
      } catch (err) {
        addLog(`對齊失敗: ${err.message}`, "error");
      } finally {
        hideBusyOverlay();
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
        addLog(`【字幕校對】正在參照上方原稿歌詞進行精準錯字校正...`);
      } else {
        addLog(`【字幕校對】使用所選 LLM 進行上下文盲校...`);
      }
      el.btnAiProofread.disabled = true;
      el.btnAiProofread.textContent = "⏳ 校對中...";

      const request = captureSubtitleRequest();
      try {
        const payload = { track: state.track, batch_size: 25, llm_provider: el.selectLlmEngine ? el.selectLlmEngine.value : "local" };
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
          if (!canApplySubtitleResult(request)) return;
          setSubtitleTrack(data.track);
          if (data.proofread_warning) {
            addLog(data.proofread_warning, "error");
          } else if (data.has_reference) {
            addLog("已完成參考原詞校對，請確認結果。", "success");
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
// ---------------- 7. Tab 2: 斷點校對與字幕管理編輯器 ----------------
function drawWaveformTimeline() {
  if (!el.waveformCanvas || !el.waveformBarWrapper) return;
  if ((!state.waveformPeaks || !state.waveformPeaks.length) && (!state.track.segments || !state.track.segments.length)) {
    el.waveformBarWrapper.classList.add("hidden");
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
    seg.start = Math.max(0, Number(seg.start));
    seg.end = Math.max(seg.start + 0.001, Number(seg.end));
    if (!seg.expected_chars) {
      seg.expected_chars = Math.max(2, Math.min(22, Math.round((seg.end - seg.start) * 3.3)));
    }
  });
}

function formatEditorText(segments) {
  return segments.map((segment, index) => `[#${index + 1}]\n${segment.text}`).join("\n\n");
}

function parseEditorText(value, count) {
  const text = value.replace(/\r\n/g, "\n");
  const markers = [...text.matchAll(/^\[#(\d+)\]\n/gm)];
  if (markers.length) {
    if (markers.length !== count || markers[0].index !== 0 || markers.some((m, i) => Number(m[1]) !== i + 1 || (i > 0 && text.slice(m.index - 2, m.index) !== "\n\n"))) {
      throw new Error("請保留每段的 [#序號]，段數與順序須和時間軸一致。");
    }
    return markers.map((marker, i) => {
      const end = i + 1 < markers.length ? markers[i + 1].index - 2 : text.length;
      return text.slice(marker.index + marker[0].length, end);
    });
  }
  const lines = text.split("\n");
  if (lines.length === count + 1 && lines.at(-1) === "") lines.pop();
  if (lines.length !== count) throw new Error(`文字共 ${lines.length} 段，時間軸共 ${count} 段；請調整後再套用。`);
  return lines;
}

function setSubtitleTrack(track) {
  if (state.activePackage) {
    track.source_file = state.activePackage.subtitle ? state.activePackage.subtitle.name : state.activePackage.media.stem + ".srt";
  }
  state.track = track;
  normalizeTrackSegments();
  el.segmentCountBadge.textContent = `${track.segments.length} 句字幕`;
  el.editorSegCount.textContent = track.segments.length;

  if (track.segments.length > 0) {
    state.selectedSegmentIndex = Math.max(0, Math.min(state.selectedSegmentIndex, track.segments.length - 1));
  } else {
    state.selectedSegmentIndex = 0;
  }

  renderSegmentList();
  updateSubtitleSelectDropdown();
  updateSummary();
  updateWorkspaceSlots();
  renderFilteredAssetLibrary();
  drawWaveformTimeline();
  updateSubtitleOverlayOnTime(el.video ? (el.video.currentTime || 0) : 0);
  saveSessionToStorage();
}

function renderSegmentList() {
  const container = el.segmentListContainer;
  container.innerHTML = "";

  if (!state.track.segments.length) {
    container.innerHTML = `<div class="text-center py-10 text-xs text-zinc-500">請點擊上方【🔍 分析音訊斷點】自動抓出每句開頭結尾，或拖入現成 SRT</div>`;
    el.rawSubtitleTextarea.value = "";
    return;
  }

  el.rawSubtitleTextarea.value = formatEditorText(state.track.segments);

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

    const textInput = document.createElement("textarea");
    const lineCount = (seg.text || "").split(/\n|<br\s*\/?>/i).length;
    textInput.rows = Math.min(4, Math.max(1, lineCount));
    textInput.className = "seg-text-input w-full bg-zinc-900 border border-zinc-800/80 rounded px-2 py-1 text-zinc-200 text-xs focus:outline-none focus:border-blue-500 placeholder:text-zinc-600 resize-y font-sans";
    textInput.placeholder = `[#${seg.id} 待填字幕 — Enter跳下一段, Shift+Enter換行, 亦支援<br>]`;
    textInput.value = seg.text || "";

    function autoResizeInput(target) {
      target.style.height = 'auto';
      target.style.height = `${target.scrollHeight}px`;
    }

    card.appendChild(topRow);
    card.appendChild(textInput);

    card.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON" && e.target.tagName !== "TEXTAREA") {
        selectAndJumpToSegment(idx);
      }
    });

    textInput.addEventListener("focus", () => {
      state.selectedSegmentIndex = idx;
      highlightActiveSegmentInList(seg.id);
      drawWaveformTimeline();
    });

    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
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
      autoResizeInput(e.target);
      el.rawSubtitleTextarea.value = formatEditorText(state.track.segments);
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
    // 定位至該段起點後 +0.05s，確保浮點數不會落在 start 之前而被 timeupdate 清除
    const targetSec = Math.min(seg.end, seg.start + 0.05);
    if (el.video && !isNaN(targetSec)) {
      try {
        el.video.currentTime = targetSec;
      } catch (e) {
        // ignore seek before metadata
      }
    }
    const textToShow = (seg.text && seg.text.trim()) ? seg.text : `[#${seg.id} 字幕樣式預覽]`;
    renderOverlayText(textToShow);
    if (el.inputStylePreviewText && seg.text && seg.text.trim()) {
      el.inputStylePreviewText.value = seg.text;
      el.inputStylePreviewText.style.height = 'auto';
      el.inputStylePreviewText.style.height = `${el.inputStylePreviewText.scrollHeight}px`;
    }
    highlightActiveSegmentInList(seg.id);
    if (el.selectedSubBadge) {
      el.selectedSubBadge.textContent = `目前選擇: 第 ${seg.id} 句 (${seg.start.toFixed(2)}s)`;
    }
    if (el.selectSubtitleLine) {
      el.selectSubtitleLine.value = String(index);
    }
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
  const request = captureSubtitleRequest();
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

  if (!canApplySubtitleResult(request)) return;
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

  const request = captureSubtitleRequest();
  try {
    const res = await fetch("/api/audio/breakpoints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_path: media, mode })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (!canApplySubtitleResult(request)) return;
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
  const llmProvider = el.selectLockedLlmEngine ? el.selectLockedLlmEngine.value : (el.selectLlmEngine ? el.selectLlmEngine.value : "local");
  const brainName = llmProvider === "local" ? "本地 Qwen2.5 (離線)" : "雲端 LLM API (.env)";
  const proofText = autoProofread ? `AI校對: ${brainName}` : "無校對";

  addLog(`【階段 3：鎖定時間軸填字】正在依照您校對好的 ${state.track.segments.length} 個時間段執行受控 Whisper 填字 (${proofText}，起訖時間100%鎖定)...`, "info");
  
  if (el.btnTranscribeLocked) {
    el.btnTranscribeLocked.disabled = true;
    el.btnTranscribeLocked.textContent = "⏳ 按鎖定時間軸逐段辨識中...";
  }

  if (typeof showBusyOverlay === "function") {
    showBusyOverlay(`🎙️ 正在依鎖定時間軸逐段填入 AI 字幕... (${state.track.segments.length} 段 · ${proofText})`);
  }

  const request = captureSubtitleRequest();
  try {
    const res = await fetch("/api/ai/transcribe-segments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        media_path: media,
        track: state.track,
        device: "cuda",
        prompt: "繁體中文",
        only_empty: onlyEmpty,
        auto_proofread: autoProofread,
        llm_provider: llmProvider
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (!canApplySubtitleResult(request)) return;
      setSubtitleTrack(data.track);
      addLog(data.proofread_warning || `✔ 已依鎖定時間軸完成 ${data.track.segments.length} 段字幕填入！`, data.proofread_warning ? "error" : "success");
    } else {
      throw new Error(data.detail || "填字失敗");
    }
  } catch (err) {
    addLog(`❌ 鎖定時間軸填字失敗: ${err.message}`, "error");
    if (typeof alert === "function") alert(`鎖定時間軸填字失敗: ${err.message}`);
  } finally {
    if (typeof hideBusyOverlay === "function") hideBusyOverlay();
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
    const segs = state.track.segments;
    if (!segs.length) {
      addLog("目前尚無時間軸段落，請先執行「🔍 分析音訊斷點」建立時間軸！", "error");
      return;
    }
    let lines;
    try { lines = parseEditorText(el.rawSubtitleTextarea.value, segs.length); }
    catch (error) { addLog(error.message, "error"); return; }
    for (let i = 0; i < segs.length; i++) {
      segs[i].text = lines[i];
    }
    setSubtitleTrack(state.track);
    el.btnViewList.click();
    addLog(`已更新 ${lines.length} 段文字，保留時間軸。`, "success");
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
      setSubtitleTrack({ ...state.track, source_file: "", segments: [] });
      addLog("已清空字幕時間軸", "info");
    }
  });
}

// ---------------- 8. Tab 3: 字幕樣式與逐行選擇控件 ----------------
function updateSubtitleSelectDropdown() {
  const sel = el.selectSubtitleLine;
  if (!sel) return;
  sel.innerHTML = "";

  if (!state.track.segments || !state.track.segments.length) {
    sel.innerHTML = `<option value="0">尚無字幕 (顯示預設範例文字)</option>`;
    return;
  }

  state.track.segments.forEach((seg, idx) => {
    const opt = document.createElement("option");
    opt.value = String(idx);
    const labelText = (seg.text && seg.text.trim()) ? seg.text.replace(/\n|<br\s*\/?>/gi, " ") : "[待填字幕斷點]";
    opt.textContent = `#${seg.id} [${formatTime(seg.start)}]: ${labelText}`;
    if (idx === state.selectedSegmentIndex) opt.selected = true;
    sel.appendChild(opt);
  });
}

// 依據 X 百分比 (0=最左, 50=置中, 100=最右) 無死角平滑計算盒模型水平對齊與邊距
function applySliderPositionX(pctX) {
  state.styleCustomized = true;
  const val = Math.max(0, Math.min(100, Math.round(pctX)));
  const vidW = state.video.width || 1920;
  const minPad = Math.max(10, Math.round(vidW * 0.025));

  if (state.style.orientation === "vertical") {
    state.style.horizontal_align = "right";
    state.style.padding_right = Math.round(((100 - val) / 100) * (vidW * 0.86));
    state.style.padding_left = minPad;
    if (el.valPosX) el.valPosX.textContent = `距右 ${state.style.padding_right}px (${val}%)`;
  } else {
    if (state.style.horizontal_align === "left") {
      state.style.padding_left = Math.round((val / 100) * (vidW * 0.80));
      state.style.padding_right = minPad;
      if (el.valPosX) el.valPosX.textContent = `靠左 距左 ${state.style.padding_left}px (${val}%)`;
    } else if (state.style.horizontal_align === "right") {
      state.style.padding_right = Math.round(((100 - val) / 100) * (vidW * 0.80));
      state.style.padding_left = minPad;
      if (el.valPosX) el.valPosX.textContent = `靠右 距右 ${state.style.padding_right}px (${val}%)`;
    } else {
      // 水平置中模式下，藉由左右非對稱內距平滑偏移中心點 (0~100 全程無死角，且與 FFmpeg ASS MarginL/MarginR 完全一致)
      if (Math.abs(val - 50) <= 1) {
        state.style.padding_left = minPad;
        state.style.padding_right = minPad;
        if (el.valPosX) el.valPosX.textContent = `水平置中 (50%)`;
      } else if (val < 50) {
        state.style.padding_left = minPad;
        state.style.padding_right = minPad + Math.round(((50 - val) / 50) * (vidW * 0.78));
        if (el.valPosX) el.valPosX.textContent = `偏左 ${val}% (右距 ${state.style.padding_right}px)`;
      } else {
        state.style.padding_right = minPad;
        state.style.padding_left = minPad + Math.round(((val - 50) / 50) * (vidW * 0.78));
        if (el.valPosX) el.valPosX.textContent = `偏右 ${val}% (左距 ${state.style.padding_left}px)`;
      }
    }
  }

  if (el.sliderPosX) el.sliderPosX.value = val;
  if (el.inputPadLeft) el.inputPadLeft.value = state.style.padding_left;
  if (el.inputPadRight) el.inputPadRight.value = state.style.padding_right;
  updateGridButtonsHighlight();
  applySubtitleStyleToOverlay();
  ensureSubtitlePreviewVisible();
}

// 依據 Y 百分比 (0=最底, 50=正中, 100=最頂) 無死角平滑計算盒模型垂直對齊與邊距
function applySliderPositionY(pctY) {
  state.styleCustomized = true;
  const val = Math.max(0, Math.min(100, Math.round(pctY)));
  const vidH = state.video.height || 1080;
  const minPad = Math.max(10, Math.round(vidH * 0.025));

  if (state.style.orientation === "vertical") {
    state.style.vertical_align = "top";
    state.style.padding_top = Math.round(((100 - val) / 100) * (vidH * 0.75));
    state.style.padding_bottom = minPad;
    if (el.valPosY) el.valPosY.textContent = `距頂 ${state.style.padding_top}px (${val}%)`;
  } else {
    if (state.style.vertical_align === "top") {
      state.style.padding_top = Math.round(((100 - val) / 100) * (vidH * 0.85));
      state.style.padding_bottom = minPad;
      if (el.valPosY) el.valPosY.textContent = `距頂 ${state.style.padding_top}px (${val}%)`;
    } else {
      // 以 bottom 為基準，從 0% (貼底) 到 100% (頂部) 全程平滑無死角移動，且與 FFmpeg ASS MarginV 100% 對應
      state.style.vertical_align = "bottom";
      state.style.padding_bottom = Math.round((val / 100) * (vidH * 0.86));
      state.style.padding_top = minPad;
      if (el.valPosY) el.valPosY.textContent = `距底 ${state.style.padding_bottom}px (${val}%)`;
    }
  }

  if (el.sliderPosY) el.sliderPosY.value = val;
  if (el.inputPadTop) el.inputPadTop.value = state.style.padding_top;
  if (el.inputPadBottom) el.inputPadBottom.value = state.style.padding_bottom;
  updateGridButtonsHighlight();
  applySubtitleStyleToOverlay();
  ensureSubtitlePreviewVisible();
}

function updateGridButtonsHighlight() {
  const s = state.style;
  document.querySelectorAll(".grid-align-btn").forEach(b => {
    if (b.dataset.valign === s.vertical_align && b.dataset.halign === s.horizontal_align) {
      b.classList.add("bg-blue-600", "text-white");
      b.classList.remove("bg-zinc-800");
    } else {
      b.classList.remove("bg-blue-600", "text-white");
      b.classList.add("bg-zinc-800");
    }
  });
}

// 支援直接在左側影片預覽畫布上按住字幕拖曳位置
function initOverlayDirectDrag() {
  const overlay = el.overlay;
  if (!overlay) return;

  let isDragging = false;
  let startClientX = 0;
  let startClientY = 0;
  let startPctX = 50;
  let startPctY = 10;

  overlay.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 && e.pointerType === "mouse") return;
    e.stopPropagation();
    e.preventDefault();
    isDragging = true;
    state.justDraggedSubtitle = true;
    startClientX = e.clientX;
    startClientY = e.clientY;
    startPctX = el.sliderPosX ? (parseFloat(el.sliderPosX.value) || 50) : 50;
    startPctY = el.sliderPosY ? (parseFloat(el.sliderPosY.value) || 10) : 10;

    overlay.classList.add("ring-2", "ring-blue-400", "bg-blue-500/20");
    try {
      overlay.setPointerCapture(e.pointerId);
    } catch (err) {
      // ignore
    }
  });

  overlay.addEventListener("pointermove", (e) => {
    if (!isDragging) return;
    e.stopPropagation();
    e.preventDefault();
    const stageW = Math.max(120, (el.videoStage && el.videoStage.clientWidth) || 360);
    const stageH = Math.max(120, (el.videoStage && el.videoStage.clientHeight) || 360);

    const dx = e.clientX - startClientX;
    const dy = e.clientY - startClientY;

    const newPctX = Math.max(0, Math.min(100, Math.round(startPctX + (dx / stageW) * 100)));
    const newPctY = Math.max(0, Math.min(100, Math.round(startPctY - (dy / stageH) * 100)));

    applySliderPositionX(newPctX);
    applySliderPositionY(newPctY);
  });

  const endDrag = (e) => {
    if (!isDragging) return;
    isDragging = false;
    overlay.classList.remove("ring-2", "ring-blue-400", "bg-blue-500/20");
    try {
      if (e && e.pointerId !== undefined) overlay.releasePointerCapture(e.pointerId);
    } catch (err) {
      // ignore
    }
    setTimeout(() => {
      state.justDraggedSubtitle = false;
    }, 180);
  };

  overlay.addEventListener("pointerup", endDrag);
  overlay.addEventListener("pointercancel", endDrag);
}

function initStyleEditor() {
  if (el.selectSubtitleLine) {
    el.selectSubtitleLine.addEventListener("change", (e) => {
      const idx = parseInt(e.target.value, 10);
      if (state.track.segments && state.track.segments[idx]) {
        selectAndJumpToSegment(idx);
      } else {
        ensureSubtitlePreviewVisible();
      }
    });
  }

  if (el.inputStylePreviewText) {
    const adjustHeight = () => {
      el.inputStylePreviewText.style.height = 'auto';
      el.inputStylePreviewText.style.height = `${el.inputStylePreviewText.scrollHeight}px`;
    };
    el.inputStylePreviewText.addEventListener("input", (e) => {
      adjustHeight();
      const txt = e.target.value;
      renderOverlayText(txt || "字幕樣式與位置即時預覽 Sample");
      // 若目前已選取某句字幕，也可同步更新該句預覽
      if (state.track.segments && state.track.segments[state.selectedSegmentIndex]) {
        state.track.segments[state.selectedSegmentIndex].text = txt;
        updateSubtitleSelectDropdown();
        renderSegmentList();
        saveSessionToStorage();
      }
    });
  }

  if (el.btnResetPosition) {
    el.btnResetPosition.addEventListener("click", () => {
      state.styleCustomized = true;
      const vidH = state.video.height || 1080;
      const vidW = state.video.width || 1920;
      state.style.orientation = "horizontal";
      state.style.vertical_align = "bottom";
      state.style.horizontal_align = "center";
      state.style.padding_bottom = Math.round(vidH * 0.06);
      state.style.padding_top = Math.round(vidH * 0.04);
      state.style.padding_left = Math.round(vidW * 0.04);
      state.style.padding_right = Math.round(vidW * 0.04);
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
      addLog("已重設字幕為預設底部置中位置", "info");
    });
  }

  if (el.btnOrientH) {
    el.btnOrientH.addEventListener("click", () => {
      state.styleCustomized = true;
      const changed = state.style.orientation !== "horizontal";
      state.style.orientation = "horizontal";
      if (changed) {
        const vidW = state.video.width || 1920;
        const vidH = state.video.height || 1080;
        state.style.vertical_align = "bottom";
        state.style.horizontal_align = "center";
        state.style.padding_bottom = Math.round(vidH * 0.06);
        state.style.padding_top = Math.round(vidH * 0.04);
        state.style.padding_left = Math.round(vidW * 0.04);
        state.style.padding_right = Math.round(vidW * 0.04);
      }
      el.btnOrientH.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
      if (el.btnOrientV) el.btnOrientV.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.btnOrientV) {
    el.btnOrientV.addEventListener("click", () => {
      state.styleCustomized = true;
      const changed = state.style.orientation !== "vertical";
      state.style.orientation = "vertical";
      if (changed) {
        const vidW = state.video.width || 1920;
        const vidH = state.video.height || 1080;
        state.style.vertical_align = "top";
        state.style.horizontal_align = "right";
        state.style.padding_top = Math.round(vidH * 0.06);
        state.style.padding_right = Math.round(vidW * 0.05);
        state.style.padding_left = Math.round(vidW * 0.03);
        state.style.padding_bottom = Math.round(vidH * 0.04);
      }
      el.btnOrientV.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
      if (el.btnOrientH) el.btnOrientH.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  document.querySelectorAll(".grid-align-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.styleCustomized = true;
      const valign = btn.dataset.valign;
      const halign = btn.dataset.halign;
      const vidW = state.video.width || 1920;
      const vidH = state.video.height || 1080;
      const padH = Math.max(16, Math.round(vidW * 0.045));
      const padV = Math.max(24, Math.round(vidH * 0.06));

      state.style.vertical_align = valign;
      state.style.horizontal_align = halign;

      if (valign === "top") {
        state.style.padding_top = padV;
        state.style.padding_bottom = 16;
      } else if (valign === "middle") {
        state.style.padding_top = 0;
        state.style.padding_bottom = 0;
      } else {
        state.style.padding_bottom = padV;
        state.style.padding_top = 16;
      }

      if (halign === "left") {
        state.style.padding_left = padH;
        state.style.padding_right = 16;
      } else if (halign === "right") {
        state.style.padding_right = padH;
        state.style.padding_left = 16;
      } else {
        state.style.padding_left = 16;
        state.style.padding_right = 16;
      }

      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  });

  if (el.sliderPosX) {
    el.sliderPosX.addEventListener("input", (e) => {
      applySliderPositionX(parseFloat(e.target.value));
    });
  }

  if (el.sliderPosY) {
    el.sliderPosY.addEventListener("input", (e) => {
      applySliderPositionY(parseFloat(e.target.value));
    });
  }

  if (el.inputPadTop) {
    el.inputPadTop.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.padding_top = Math.max(0, parseInt(e.target.value, 10) || 0);
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.inputPadRight) {
    el.inputPadRight.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.padding_right = Math.max(0, parseInt(e.target.value, 10) || 0);
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.inputPadBottom) {
    el.inputPadBottom.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.padding_bottom = Math.max(0, parseInt(e.target.value, 10) || 0);
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.inputPadLeft) {
    el.inputPadLeft.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.padding_left = Math.max(0, parseInt(e.target.value, 10) || 0);
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.selectFontName) {
    el.selectFontName.addEventListener("change", (e) => {
      state.styleCustomized = true;
      state.style.font_name = e.target.value;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.sliderFontSize) {
    el.sliderFontSize.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.font_size = parseInt(e.target.value, 10);
      if (el.valFontSize) el.valFontSize.textContent = `${state.style.font_size}px`;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.pickerPrimaryColor) {
    el.pickerPrimaryColor.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.primary_color = e.target.value.toUpperCase();
      if (el.labelPrimaryColor) el.labelPrimaryColor.textContent = state.style.primary_color;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.checkBold) {
    el.checkBold.addEventListener("change", (e) => {
      state.styleCustomized = true;
      state.style.bold = e.target.checked;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.checkItalic) {
    el.checkItalic.addEventListener("change", (e) => {
      state.styleCustomized = true;
      state.style.italic = e.target.checked;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.sliderOpacity) {
    el.sliderOpacity.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.opacity = parseFloat(e.target.value);
      if (el.valOpacity) el.valOpacity.textContent = `${Math.round(state.style.opacity * 100)}%`;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.checkOutlineEnabled) {
    el.checkOutlineEnabled.addEventListener("change", (e) => {
      state.styleCustomized = true;
      state.style.outline_enabled = e.target.checked;
      const wContainer = document.getElementById("outline-width-container");
      const cContainer = document.getElementById("outline-color-container");
      if (wContainer) wContainer.style.opacity = e.target.checked ? "1" : "0.35";
      if (cContainer) cContainer.style.opacity = e.target.checked ? "1" : "0.35";
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.pickerOutlineColor) {
    el.pickerOutlineColor.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.outline_color = e.target.value.toUpperCase();
      if (el.labelOutlineColor) el.labelOutlineColor.textContent = state.style.outline_color;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.sliderOutlineWidth) {
    el.sliderOutlineWidth.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.outline_width = parseFloat(e.target.value);
      if (el.valOutlineWidth) el.valOutlineWidth.textContent = `${state.style.outline_width}px`;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.pickerShadowColor) {
    el.pickerShadowColor.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.shadow_color = e.target.value.toUpperCase();
      if (el.labelShadowColor) el.labelShadowColor.textContent = state.style.shadow_color;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }
  if (el.sliderShadowOffset) {
    el.sliderShadowOffset.addEventListener("input", (e) => {
      state.styleCustomized = true;
      state.style.shadow_offset = parseFloat(e.target.value);
      if (el.valShadowOffset) el.valShadowOffset.textContent = `${state.style.shadow_offset}px`;
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
    });
  }

  if (el.btnCopyCss) {
    el.btnCopyCss.addEventListener("click", () => {
      navigator.clipboard.writeText(el.cssLiveCode.value);
      el.btnCopyCss.textContent = "已複製 ✔";
      setTimeout(() => { el.btnCopyCss.textContent = "複製 CSS"; }, 1500);
    });
  }

  if (el.cssLiveCode) {
    el.cssLiveCode.addEventListener("change", async (e) => {
      try {
        const res = await fetch("/api/style/parse-css", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ css: e.target.value })
        });
        const data = await res.json();
        if (data.status === "success") {
          state.styleCustomized = true;
          Object.assign(state.style, data.style);
          syncStateToControls();
          applySubtitleStyleToOverlay();
          ensureSubtitlePreviewVisible();
          addLog("已由自訂 CSS 更新樣式參數", "info");
        }
      } catch (err) {
        addLog(`CSS 解析錯誤: ${err.message}`, "error");
      }
    });
  }

  initPresets();
  initFontManager();
  initOverlayDirectDrag();
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
  font-family: ${JSON.stringify(f.family)};
  src: url(${JSON.stringify(f.url)});
  font-display: swap;
}`);
      // 嘗試透過 FontFace API 立即預載入至瀏覽器畫面
      if (window.FontFace) {
        try {
          const ff = new FontFace(f.family, `url(${JSON.stringify(f.url)})`);
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
          <span class="truncate font-label"></span>
          ${tagHtml}
        </div>
        <div class="text-[10px] text-zinc-500 truncate font-description"></div>
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

    const label = row.querySelector(".font-label");
    label.textContent = item.display_name;
    if (item.installed) label.style.fontFamily = JSON.stringify(item.family) + ", sans-serif";
    row.querySelector(".font-description").textContent = item.description || item.family;

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
  if (el.sliderFontSize) el.sliderFontSize.value = s.font_size;
  if (el.valFontSize) el.valFontSize.textContent = `${s.font_size}px`;
  if (el.pickerPrimaryColor) el.pickerPrimaryColor.value = s.primary_color;
  if (el.labelPrimaryColor) el.labelPrimaryColor.textContent = s.primary_color;
  const curOpacity = s.opacity !== undefined ? s.opacity : 1.0;
  if (el.sliderOpacity) el.sliderOpacity.value = curOpacity;
  if (el.valOpacity) el.valOpacity.textContent = `${Math.round(curOpacity * 100)}%`;
  const isOutlineOn = s.outline_enabled !== false && Number(s.outline_width) > 0;
  if (el.checkOutlineEnabled) el.checkOutlineEnabled.checked = isOutlineOn;
  const wContainer = document.getElementById("outline-width-container");
  const cContainer = document.getElementById("outline-color-container");
  if (wContainer) wContainer.style.opacity = isOutlineOn ? "1" : "0.35";
  if (cContainer) cContainer.style.opacity = isOutlineOn ? "1" : "0.35";

  if (el.pickerOutlineColor) el.pickerOutlineColor.value = s.outline_color;
  if (el.labelOutlineColor) el.labelOutlineColor.textContent = s.outline_color;
  if (el.sliderOutlineWidth) el.sliderOutlineWidth.value = s.outline_width;
  if (el.valOutlineWidth) el.valOutlineWidth.textContent = `${s.outline_width}px`;
  if (el.pickerShadowColor) el.pickerShadowColor.value = s.shadow_color;
  if (el.labelShadowColor) el.labelShadowColor.textContent = s.shadow_color;
  if (el.sliderShadowOffset) el.sliderShadowOffset.value = s.shadow_offset;
  if (el.valShadowOffset) el.valShadowOffset.textContent = `${s.shadow_offset}px`;
  if (el.checkBold) el.checkBold.checked = s.bold;
  if (el.checkItalic) el.checkItalic.checked = s.italic;
  if (el.inputPadTop) el.inputPadTop.value = s.padding_top;
  if (el.inputPadRight) el.inputPadRight.value = s.padding_right;
  if (el.inputPadBottom) el.inputPadBottom.value = s.padding_bottom;
  if (el.inputPadLeft) el.inputPadLeft.value = s.padding_left;
  if (el.selectFontName && s.font_name) el.selectFontName.value = s.font_name;

  // 同步文字方向按鈕外觀
  if (s.orientation === "vertical") {
    if (el.btnOrientV) el.btnOrientV.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
    if (el.btnOrientH) el.btnOrientH.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
  } else {
    if (el.btnOrientH) el.btnOrientH.className = "px-3 py-1 rounded text-xs bg-blue-600 text-white font-medium";
    if (el.btnOrientV) el.btnOrientV.className = "px-3 py-1 rounded text-xs text-zinc-400 hover:text-white";
  }

  // 反推並同步 X / Y 滑桿與文字標籤
  const vidW = state.video.width || 1920;
  const vidH = state.video.height || 1080;

  let pctX = 50;
  if (s.orientation === "vertical" || s.horizontal_align === "right") {
    pctX = Math.max(0, Math.min(100, Math.round(100 - (s.padding_right / Math.max(1, vidW * 0.82)) * 100)));
    if (el.valPosX) el.valPosX.textContent = `靠右 距右 ${s.padding_right}px (${pctX}%)`;
  } else if (s.horizontal_align === "left") {
    pctX = Math.max(0, Math.min(100, Math.round((s.padding_left / Math.max(1, vidW * 0.82)) * 100)));
    if (el.valPosX) el.valPosX.textContent = `靠左 距左 ${s.padding_left}px (${pctX}%)`;
  } else {
    const diff = (s.padding_left || 0) - (s.padding_right || 0);
    if (Math.abs(diff) <= 4) {
      pctX = 50;
      if (el.valPosX) el.valPosX.textContent = "水平置中 (50%)";
    } else if (diff < 0) {
      pctX = Math.max(0, Math.round(50 - (Math.abs(diff) / Math.max(1, vidW * 0.78)) * 50));
      if (el.valPosX) el.valPosX.textContent = `偏左 ${pctX}%`;
    } else {
      pctX = Math.min(100, Math.round(50 + (diff / Math.max(1, vidW * 0.78)) * 50));
      if (el.valPosX) el.valPosX.textContent = `偏右 ${pctX}%`;
    }
  }
  if (el.sliderPosX) el.sliderPosX.value = pctX;

  let pctY = 10;
  if (s.orientation === "vertical" || s.vertical_align === "top") {
    pctY = Math.max(0, Math.min(100, Math.round(100 - (s.padding_top / Math.max(1, vidH * 0.80)) * 100)));
    if (el.valPosY) el.valPosY.textContent = `距頂 ${s.padding_top}px (${pctY}%)`;
  } else if (s.vertical_align === "middle") {
    pctY = 50;
    if (el.valPosY) el.valPosY.textContent = "垂直置中 (50%)";
  } else {
    pctY = Math.max(0, Math.min(100, Math.round((s.padding_bottom / Math.max(1, vidH * 0.86)) * 100)));
    if (el.valPosY) el.valPosY.textContent = `距底 ${s.padding_bottom}px (${pctY}%)`;
  }
  if (el.sliderPosY) el.sliderPosY.value = pctY;

  updateGridButtonsHighlight();
}

function initPresets() {
  // 根據目前載入影片尺寸等比縮放 Preset 預設字級與邊距，兼顧 448x768 短影音與 1920x1080 橫式影片
  function getVideoRefScale() {
    const minDim = Math.min(state.video.width || 1920, state.video.height || 1080);
    return Math.max(0.52, Math.min(1.2, minDim / 1080));
  }

  if (el.presetYoutube) {
    el.presetYoutube.addEventListener("click", () => {
      state.styleCustomized = true;
      const k = getVideoRefScale();
      Object.assign(state.style, {
        font_size: Math.round(38 * k),
        primary_color: "#FFD700",
        outline_color: "#000000",
        outline_width: Number((3.2 * k).toFixed(1)),
        shadow_color: "#000000",
        shadow_offset: Number((2.5 * k).toFixed(1)),
        bold: true,
        opacity: 1.0,
        orientation: "horizontal",
        vertical_align: "bottom",
        horizontal_align: "center",
        padding_bottom: Math.round(60 * k),
        padding_top: Math.round(40 * k),
        padding_left: Math.round(32 * k),
        padding_right: Math.round(32 * k)
      });
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
      addLog("🌟 已套用「YouTube 醒目金黃」字幕樣式", "success");
    });
  }

  if (el.presetTiktok) {
    el.presetTiktok.addEventListener("click", () => {
      state.styleCustomized = true;
      const k = getVideoRefScale();
      Object.assign(state.style, {
        font_size: Math.round(34 * k),
        primary_color: "#FFFFFF",
        outline_color: "#111111",
        outline_width: Number((2.5 * k).toFixed(1)),
        shadow_color: "#000000",
        shadow_offset: Number((2.0 * k).toFixed(1)),
        bold: true,
        opacity: 1.0,
        orientation: "vertical",
        vertical_align: "top",
        horizontal_align: "right",
        padding_top: Math.round(60 * k),
        padding_right: Math.round(50 * k),
        padding_left: Math.round(24 * k),
        padding_bottom: Math.round(40 * k)
      });
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
      addLog("📱 已套用「TikTok 右側直排」字幕樣式", "success");
    });
  }

  if (el.presetClassic) {
    el.presetClassic.addEventListener("click", () => {
      state.styleCustomized = true;
      const k = getVideoRefScale();
      Object.assign(state.style, {
        font_size: Math.round(34 * k),
        primary_color: "#FFFFFF",
        outline_color: "#000000",
        outline_width: Number((2.2 * k).toFixed(1)),
        shadow_color: "#000000",
        shadow_offset: Number((1.5 * k).toFixed(1)),
        bold: true,
        opacity: 1.0,
        orientation: "horizontal",
        vertical_align: "bottom",
        horizontal_align: "center",
        padding_bottom: Math.round(52 * k),
        padding_top: Math.round(40 * k),
        padding_left: Math.round(32 * k),
        padding_right: Math.round(32 * k)
      });
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
      addLog("🎬 已套用「經典電影白字」字幕樣式", "success");
    });
  }

  if (el.presetMinimal) {
    el.presetMinimal.addEventListener("click", () => {
      state.styleCustomized = true;
      const k = getVideoRefScale();
      Object.assign(state.style, {
        font_size: Math.round(30 * k),
        primary_color: "#E2E8F0",
        outline_color: "#0F172A",
        outline_width: Number((1.5 * k).toFixed(1)),
        shadow_color: "#000000",
        shadow_offset: Number((1.0 * k).toFixed(1)),
        bold: false,
        opacity: 1.0,
        orientation: "horizontal",
        vertical_align: "bottom",
        horizontal_align: "center",
        padding_bottom: Math.round(46 * k),
        padding_top: Math.round(40 * k),
        padding_left: Math.round(32 * k),
        padding_right: Math.round(32 * k)
      });
      syncStateToControls();
      applySubtitleStyleToOverlay();
      ensureSubtitlePreviewVisible();
      addLog("📺 已套用「現代電視置中」字幕樣式", "success");
    });
  }
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

  function formatSubtitleTime(t, decimalSep = ",") {
    const sec = Math.max(0, Number(t) || 0);
    let totalSeconds = Math.floor(sec);
    let ms = Math.round((sec - totalSeconds) * 1000);
    if (ms >= 1000) {
      totalSeconds += 1;
      ms = 0;
    }
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}${decimalSep}${String(ms).padStart(3, "0")}`;
  }

  function normalizeExportCueText(text) {
    return String(text || "").replace(/<br\s*\/?>|\\N/gi, "\n").replace(/\r\n/g, "\n");
  }

  el.btnExportSrt.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    let srt = "";
    state.track.segments.forEach((seg, i) => {
      srt += `${i + 1}\n${formatSubtitleTime(seg.start, ",")} --> ${formatSubtitleTime(seg.end, ",")}\n${normalizeExportCueText(seg.text)}\n\n`;
    });
    const outName = `${getExportStem()}.srt`;
    downloadTextFile(srt, outName);
    addLog(`已匯出 ${outName}`, "success");
  });

  el.btnExportVtt.addEventListener("click", () => {
    if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
    let vtt = "WEBVTT\n\n";
    state.track.segments.forEach((seg, i) => {
      vtt += `${i + 1}\n${formatSubtitleTime(seg.start, ".")} --> ${formatSubtitleTime(seg.end, ".")}\n${normalizeExportCueText(seg.text)}\n\n`;
    });
    const outName = `${getExportStem()}.vtt`;
    downloadTextFile(vtt, outName);
    addLog(`已匯出 ${outName}`, "success");
  });

  if (el.btnExportOpenshot) {
    el.btnExportOpenshot.addEventListener("click", () => {
      if (!state.track.segments.length) { addLog("尚無字幕可供匯出", "error"); return; }
      const lines = [];
      state.track.segments.forEach((seg) => {
        const textLines = normalizeExportCueText(seg.text).split("\n").filter((l) => l.trim().length > 0);
        if (!textLines.length) return;
        lines.push(`${formatSubtitleTime(seg.start, ",")} --> ${formatSubtitleTime(seg.end, ",")}`);
        lines.push(...textLines);
      });
      if (!lines.length) { addLog("目前沒有非空字幕可匯出 OpenShot 格式", "warning"); return; }
      const outName = `${getExportStem()}_openshot.txt`;
      downloadTextFile(`${lines.join("\n")}\n`, outName);
      addLog(`已匯出 OpenShot 字幕格式 ${outName}`, "success");
    });
  }

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
    if (state.video.isAudioOnly) {
      addLog("純音訊檔案 (.wav / .mp3) 不支援影片燒錄，請改為下載 SRT / WebVTT 字幕檔", "warning");
      return;
    }
    if (!state.track.segments.length) {
      addLog("請先載入或生成字幕後再執行壓制", "error");
      return;
    }

    const renderMode = el.selectBurnRenderMode ? el.selectBurnRenderMode.value : "css";
    const engineLabel = renderMode === "css" ? "CSS 精準圖層 + NVENC" : "ASS 傳統引擎 + NVENC";
    addLog(`【影音壓制】啟動 ${engineLabel} 壓制燒錄影片至 ${videoPath}...`);
    el.btnStartBurn.disabled = true;
    el.btnStartBurn.textContent = "⏳ GPU 硬體編碼壓制中...";
    el.burnResultBox.classList.add("hidden");
    showBusyOverlay(
      renderMode === "css"
        ? `🎬 正在進行 CSS 瀏覽器精準排版＋NVENC 影片壓制... (${state.track.segments.length} 句)`
        : `🎬 正在進行 ASS 傳統引擎＋NVENC 影片壓制... (${state.track.segments.length} 句)`
    );

    try {
      const res = await fetch("/api/burn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: videoPath,
          track: state.track,
          style: state.style,
          render_mode: renderMode
        })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.status === "success") {
        addLog(`【壓制成功】已產出燒錄影片 (${data.render_mode || renderMode}): ${data.filename}`, "success");
        el.burnResultBox.classList.remove("hidden");
        el.linkDownloadBurned.href = data.url;
        el.btnPreviewBurned.onclick = () => {
          el.video.src = data.url;
          el.video.play();
          addLog("已切換播放器至壓制後影片", "info");
        };
        loadAssetLibrary();
      } else {
        throw new Error(data.detail || `壓制失敗 (HTTP ${res.status})`);
      }
    } catch (err) {
      addLog(`壓制失敗: ${err.message}`, "error");
    } finally {
      hideBusyOverlay();
      el.btnStartBurn.disabled = false;
      el.btnStartBurn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>開始壓制燒錄影片`;
    }
  });
}

// ---------------- 8. AI 視訊超解析放大 (Upscale) ----------------
let currentUpscaleTarget = null;
let currentUpscaleTaskId = null;
let activeUpscalePolling = false;

async function requestUpscaleEstimate() {
  if (!currentUpscaleTarget) return;
  const scale = parseInt(document.querySelector('input[name="upscale-scale"]:checked')?.value || "2", 10);
  const modelName = el.selectUpscaleModel?.value || "realesr-animevideov3";

  if (el.upscaleFramesInfo) el.upscaleFramesInfo.textContent = "試算中...";
  if (el.upscaleTimeEst) el.upscaleTimeEst.textContent = "試算中...";
  if (el.upscaleWarningBox) el.upscaleWarningBox.classList.add("hidden");

  try {
    const payload = {
      package_path: currentUpscaleTarget.package_path || null,
      media_path: (!currentUpscaleTarget.package_path && currentUpscaleTarget.media_path) ? currentUpscaleTarget.media_path : null,
      scale: scale,
      model_name: modelName
    };
    const res = await fetch("/api/upscale/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("試算失敗");
    const data = await res.json();
    const info = data.stream_info || {};
    const est = data.estimate || {};

    if (el.upscaleFramesInfo) {
      const fpsVal = typeof info.fps === "number" ? info.fps.toFixed(1) : "30.0";
      const totalF = (est.total_frames !== undefined && est.total_frames !== null) ? est.total_frames : (info.nb_frames || 0);
      el.upscaleFramesInfo.textContent = `${info.width || '?'}x${info.height || '?'} @ ${fpsVal}fps · 總影格: ${totalF.toLocaleString()} 幀`;
    }
    if (el.upscaleTimeEst) {
      el.upscaleTimeEst.textContent = `${est.estimated_text || '未知'} (~${est.sec_per_frame}s/幀)`;
      if (est.is_heavy_warning) {
        el.upscaleTimeEst.className = "font-bold text-red-400 font-mono";
      } else {
        el.upscaleTimeEst.className = "font-semibold text-emerald-400 font-mono";
      }
    }

    if (el.upscaleWarningBox && el.upscaleWarningText) {
      if (est.is_heavy_warning && est.warning_message) {
        el.upscaleWarningText.textContent = est.warning_message;
        el.upscaleWarningBox.classList.remove("hidden");
      } else {
        el.upscaleWarningBox.classList.add("hidden");
      }
    }
  } catch (err) {
    if (el.upscaleFramesInfo) el.upscaleFramesInfo.textContent = "無法取得視訊規格";
    if (el.upscaleTimeEst) el.upscaleTimeEst.textContent = "無法預估";
    if (el.upscaleWarningBox) el.upscaleWarningBox.classList.add("hidden");
  }
}

function openUpscaleModal(target) {
  if (!el.modalUpscale) return;
  currentUpscaleTarget = target;
  if (el.upscaleTargetName) el.upscaleTargetName.textContent = target.target_name || target.media_name || "未指定";
  if (el.upscaleTargetMeta) el.upscaleTargetMeta.textContent = target.meta_info || "準備就緒";
  updateUpscalePreviewName();
  el.modalUpscale.classList.remove("hidden");
  el.modalUpscale.classList.add("flex");
  requestUpscaleEstimate();
}

function closeUpscaleModal() {
  currentUpscaleTarget = null;
  if (el.modalUpscale) {
    el.modalUpscale.classList.add("hidden");
    el.modalUpscale.classList.remove("flex");
  }
}

function updateUpscalePreviewName() {
  if (!currentUpscaleTarget) return;
  const scale = document.querySelector('input[name="upscale-scale"]:checked')?.value || "2";
  const base = (currentUpscaleTarget.package_path || currentUpscaleTarget.media_name || "video").replace(/\.[^/.]+$/, "");
  if (el.upscalePreviewPkgName) {
    el.upscalePreviewPkgName.textContent = `${base}_${scale}x`;
  }
}

async function startUpscale() {
  if (!currentUpscaleTarget) return;
  const scale = parseInt(document.querySelector('input[name="upscale-scale"]:checked')?.value || "2", 10);
  const modelName = el.selectUpscaleModel?.value || "realesr-animevideov3";
  const target = currentUpscaleTarget;
  closeUpscaleModal();

  const payload = {
    package_path: target.package_path || null,
    media_path: (!target.package_path && target.media_path) ? target.media_path : null,
    scale: scale,
    model_name: modelName
  };

  try {
    addLog(`發起 AI 畫質超解析任務: ${target.target_name} (${scale}x, ${modelName})...`, "info");

    const response = await fetch("/api/upscale/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "無法啟動 AI 放大任務");
    }

    currentUpscaleTaskId = data.task_id;
    activeUpscalePolling = true;

    showBusyOverlay(`✨ 正在進行 AI 畫質超解析放大 (${scale}x)...`, {
      showProgress: true,
      onCancel: async () => {
        if (!confirm("確定要中止目前正在執行的 AI 畫質放大任務嗎？\n已產生的暫存影格將會被自動清理。")) {
          return;
        }
        if (!currentUpscaleTaskId) return;
        addLog(`正在請求中途停止 AI 放大任務 (${currentUpscaleTaskId})...`, "warning");
        try {
          await fetch(`/api/upscale/task/${currentUpscaleTaskId}/cancel`, { method: "POST" });
        } catch (e) {
          console.error("Cancel task error:", e);
        }
      }
    });

    // 輪詢任務進度
    await pollUpscaleTask(currentUpscaleTaskId);

  } catch (err) {
    hideBusyOverlay();
    addLog(`❌ AI 畫質放大失敗：${err.message}`, "error");
    alert(`AI 畫質放大失敗：${err.message}`);
  }
}

async function pollUpscaleTask(taskId) {
  while (activeUpscalePolling) {
    await new Promise(r => setTimeout(r, 1200));
    if (!activeUpscalePolling) break;

    try {
      const res = await fetch(`/api/upscale/task/${taskId}`);
      if (!res.ok) {
        if (res.status === 404) throw new Error("任務不存在或已被移除");
        continue;
      }
      const task = await res.json();

      updateBusyProgress({
        percent: task.percent,
        current_frame: task.current_frame,
        total_frames: task.total_frames,
        eta_text: task.eta_text,
        message: task.message,
        stage_text: task.stage === "extracting" ? "🎬 正在分解影片影格..." :
                    task.stage === "upscaling" ? `✨ 正在放大影格 (${task.percent}%)` :
                    task.stage === "encoding" ? "🎞️ 正在合成高解析度視訊..." : "✨ 處理中..."
      });

      if (task.stage === "completed") {
        activeUpscalePolling = false;
        hideBusyOverlay();
        addLog(`✔ ${task.message || 'AI 畫質放大完成！'}`, "success");
        await loadAssetLibrary();
        if (task.result && task.result.package && task.result.package.path) {
          await openPackage(task.result.package.path);
        }
        break;
      } else if (task.stage === "cancelled") {
        activeUpscalePolling = false;
        hideBusyOverlay();
        addLog(`⏹️ AI 放大任務已手動中止，暫存檔案已自動清理乾淨。`, "warning");
        break;
      } else if (task.stage === "failed") {
        activeUpscalePolling = false;
        hideBusyOverlay();
        addLog(`❌ AI 放大任務失敗: ${task.error || task.message}`, "error");
        alert(`AI 放大失敗: ${task.error || task.message}`);
        break;
      }
    } catch (e) {
      console.warn("Poll upscale task warning:", e);
    }
  }
}

function initUpscaleModal() {
  if (el.btnUpscaleActiveVideo) {
    el.btnUpscaleActiveVideo.addEventListener("click", () => {
      if (!state.video.filename) return;
      openUpscaleModal({
        package_path: state.activePackage ? state.activePackage.path : null,
        media_path: state.video.path || state.video.filename,
        media_name: state.video.filename,
        target_name: state.activePackage ? `資產包: ${state.activePackage.path}` : `影片: ${state.video.filename}`,
        meta_info: `目前解析度: ${el.video.videoWidth || '...'}x${el.video.videoHeight || '...'}`
      });
    });
  }

  if (el.btnCloseUpscaleModal) {
    el.btnCloseUpscaleModal.addEventListener("click", closeUpscaleModal);
  }
  if (el.btnCancelUpscale) {
    el.btnCancelUpscale.addEventListener("click", closeUpscaleModal);
  }
  if (el.btnConfirmUpscale) {
    el.btnConfirmUpscale.addEventListener("click", startUpscale);
  }

  document.querySelectorAll('input[name="upscale-scale"]').forEach(radio => {
    radio.addEventListener("change", () => {
      updateUpscalePreviewName();
      requestUpscaleEstimate();
    });
  });

  if (el.selectUpscaleModel) {
    el.selectUpscaleModel.addEventListener("change", requestUpscaleEstimate);
  }
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

  const safeInit = (fn, name) => {
    try {
      fn();
    } catch (err) {
      console.error(`Init error in ${name}:`, err);
    }
  };

  safeInit(initPlayer, "initPlayer");
  safeInit(initTabs, "initTabs");
  safeInit(initUniversalDragAndDrop, "initUniversalDragAndDrop");
  safeInit(initAiButtons, "initAiButtons");
  safeInit(initEditorViewToggle, "initEditorViewToggle");
  safeInit(initStyleEditor, "initStyleEditor");
  safeInit(initExport, "initExport");
  safeInit(initUpscaleModal, "initUpscaleModal");
  safeInit(syncStateToControls, "syncStateToControls");
  safeInit(applySubtitleStyleToOverlay, "applySubtitleStyleToOverlay");
  safeInit(ensureSubtitlePreviewVisible, "ensureSubtitlePreviewVisible");

  // 1. 讀取並渲染字型庫與資產庫
  await loadFontCatalog();
  await loadAssetLibrary();

  let lastPackage = null;
  try { lastPackage = localStorage.getItem("autosub_package_v1"); } catch (error) {}
  const initial = state.packages.find(item => item.path === lastPackage && !item.error) || state.packages.find(item => !item.error);
  if (initial) await openPackage(initial.path);

  updateWorkspaceSlots();
  addLog("AutoSubtitle AI Studio 系統初始化完成！(快捷鍵: Space 播放/暫停)", "success");
});
