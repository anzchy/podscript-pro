// ===== Result Page JavaScript =====

// Get task ID from URL
const urlParams = new URLSearchParams(window.location.search);
const taskId = urlParams.get('task_id');

// DOM Elements
const elements = {
  // Player
  mediaPlayer: document.getElementById('mediaPlayer'),
  audioPlaceholder: document.getElementById('audioPlaceholder'),
  subtitleOverlay: document.getElementById('subtitleOverlay'),
  subtitleText: document.getElementById('subtitleText'),

  // Controls
  playPauseBtn: document.getElementById('playPauseBtn'),
  playIcon: document.getElementById('playIcon'),
  pauseIcon: document.getElementById('pauseIcon'),
  skipBackBtn: document.getElementById('skipBackBtn'),
  skipForwardBtn: document.getElementById('skipForwardBtn'),
  progressBarContainer: document.getElementById('progressBarContainer'),
  progressBar: document.getElementById('progressBar'),
  progressHandle: document.getElementById('progressHandle'),
  currentTime: document.getElementById('currentTime'),
  totalTime: document.getElementById('totalTime'),
  volumeBtn: document.getElementById('volumeBtn'),
  volumeIcon: document.getElementById('volumeIcon'),
  volumeMuteIcon: document.getElementById('volumeMuteIcon'),
  volumeSlider: document.getElementById('volumeSlider'),
  speedBtn: document.getElementById('speedBtn'),
  fullscreenBtn: document.getElementById('fullscreenBtn'),

  // Transcript
  transcriptContainer: document.getElementById('transcriptContainer'),
  totalDuration: document.getElementById('totalDuration'),

  // Export
  exportBtn: document.getElementById('exportBtn'),
  exportDropdown: document.getElementById('exportDropdown'),

  // Edit
  editBtn: document.getElementById('editBtn'),
  editModal: document.getElementById('editModal'),
  editSegments: document.getElementById('editSegments'),
  closeModalBtn: document.getElementById('closeModalBtn'),
  cancelEditBtn: document.getElementById('cancelEditBtn'),
  saveEditBtn: document.getElementById('saveEditBtn'),

  // PiP
  pipBtn: document.getElementById('pipBtn'),
};

// State
let transcriptData = [];
let isPlaying = false;
let currentSegmentIndex = -1;
let selectedSegmentIndex = -1; // Track clicked segment for edit modal
let mediaType = 'audio'; // 'audio' or 'video'
let duration = 0;
let isPiPActive = false;

// Playback speeds
const playbackSpeeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
let currentSpeedIndex = 2;

// ===== Initialization =====
async function init() {
  if (!taskId) {
    showError('未找到任务 ID');
    return;
  }

  try {
    await loadTaskData();
    setupEventListeners();
  } catch (error) {
    console.error('Initialization error:', error);
    showError('加载失败: ' + error.message);
  }
}

// Load task data from API
async function loadTaskData() {
  // Try to get task from history first (persists across server restarts)
  let taskStatus = null;
  let historyRecord = null;

  // First try in-memory task store
  const taskRes = await fetch(`/tasks/${taskId}`);
  if (taskRes.ok) {
    const task = await taskRes.json();
    taskStatus = task.status;
  }

  // If task not in memory, try history records
  if (!taskStatus) {
    const historyRes = await fetch(`/history/${taskId}`);
    if (historyRes.ok) {
      historyRecord = await historyRes.json();
      taskStatus = historyRecord.status;
    }
  }

  if (!taskStatus) {
    throw new Error('任务不存在');
  }

  if (taskStatus !== 'completed') {
    throw new Error('任务尚未完成');
  }

  // Fetch transcript data - try API first, then load from artifacts
  const transcriptRes = await fetch(`/tasks/${taskId}/transcript`);
  if (transcriptRes.ok) {
    const data = await transcriptRes.json();
    transcriptData = data.segments || [];
    mediaType = data.media_type || 'audio';
    duration = data.duration || 0;

    // Set media source
    if (data.media_url) {
      elements.mediaPlayer.src = data.media_url;
    }
  } else {
    // Fallback: load directly from result.json in artifacts
    const resultJsonUrl = `/artifacts/${taskId}/result.json`;
    try {
      const resultJsonRes = await fetch(resultJsonUrl);
      if (resultJsonRes.ok) {
        const resultData = await resultJsonRes.json();
        transcriptData = resultData.segments || [];
        duration = resultData.duration || 0;
        mediaType = resultData.media_type || 'audio';
      }
    } catch (e) {
      console.log('Failed to load result.json, trying markdown');
    }

    // If still no data, try markdown
    if (transcriptData.length === 0) {
      const mdUrl = `/artifacts/${taskId}/result.md`;
      try {
        await loadFromMarkdown(mdUrl);
      } catch (e) {
        console.log('Failed to load markdown');
      }
    }
  }

  // Get media file info from artifacts
  try {
    const mediaInfoRes = await fetch(`/media-info/${taskId}`);
    if (mediaInfoRes.ok) {
      const mediaInfo = await mediaInfoRes.json();
      if (mediaInfo.media_url) {
        elements.mediaPlayer.src = mediaInfo.media_url;
        mediaType = mediaInfo.media_type || 'audio';
      }
    }
  } catch (e) {
    console.log('Failed to get media info');
  }

  // Update UI
  updateMediaDisplay();
  renderTranscript();
  updateTotalDuration();
}

// Load transcript from markdown file (fallback)
async function loadFromMarkdown(url) {
  const res = await fetch(url);
  if (!res.ok) return;

  const text = await res.text();
  transcriptData = parseMarkdownTranscript(text);
}

// Parse markdown transcript to segments
function parseMarkdownTranscript(text) {
  const segments = [];
  const lines = text.split('\n');

  let currentSpeaker = '';
  let currentTime = 0;
  let currentText = '';
  let segmentId = 0;

  for (const line of lines) {
    // Match speaker line: "发言人1  00:16" or just "00:16"
    const speakerMatch = line.match(/^(发言人\d+)?\s*(\d{2}:\d{2})/);
    if (speakerMatch) {
      // Save previous segment
      if (currentText.trim()) {
        segments.push({
          id: segmentId++,
          start: currentTime,
          end: currentTime + 10, // Estimate end time
          speaker: currentSpeaker,
          text: currentText.trim()
        });
      }

      currentSpeaker = speakerMatch[1] ? speakerMatch[1].replace('发言人', '') : '';
      currentTime = parseTimeToSeconds(speakerMatch[2]);
      currentText = '';
    } else if (line.trim() && !line.startsWith('#')) {
      currentText += (currentText ? ' ' : '') + line.trim();
    }
  }

  // Add last segment
  if (currentText.trim()) {
    segments.push({
      id: segmentId,
      start: currentTime,
      end: currentTime + 10,
      speaker: currentSpeaker,
      text: currentText.trim()
    });
  }

  // Fix end times based on next segment start
  for (let i = 0; i < segments.length - 1; i++) {
    segments[i].end = segments[i + 1].start;
  }

  return segments;
}

// Parse time string to seconds
function parseTimeToSeconds(timeStr) {
  const parts = timeStr.split(':');
  if (parts.length === 2) {
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  } else if (parts.length === 3) {
    return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
  }
  return 0;
}

// Format seconds to MM:SS
function formatTime(seconds) {
  if (isNaN(seconds)) seconds = 0;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Format seconds to HH:MM:SS,mmm (SRT format)
function formatSrtTime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds - Math.floor(seconds)) * 1000);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
}

// Update media display based on type
function updateMediaDisplay() {
  if (mediaType === 'audio') {
    elements.audioPlaceholder.hidden = false;
    elements.mediaPlayer.style.display = 'none';
  } else {
    elements.audioPlaceholder.hidden = true;
    elements.mediaPlayer.style.display = 'block';
  }
}

// Render transcript segments
function renderTranscript() {
  if (transcriptData.length === 0) {
    elements.transcriptContainer.innerHTML = `
      <div class="loading-placeholder">
        <span>暂无转写结果</span>
      </div>
    `;
    return;
  }

  const html = transcriptData.map((segment, index) => {
    const speakerNum = segment.speaker || '1';
    const speakerClass = parseInt(speakerNum) % 2 === 0 ? 'speaker-2' : 'speaker-1';

    return `
      <div class="transcript-segment" data-index="${index}" data-start="${segment.start}" data-end="${segment.end}">
        <div class="segment-avatar ${speakerClass}">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        </div>
        <div class="segment-content">
          <div class="segment-header">
            <span class="segment-speaker">发言人 ${speakerNum}</span>
            <span class="segment-time">${formatTime(segment.start)}</span>
          </div>
          <p class="segment-text">${segment.text}</p>
        </div>
      </div>
    `;
  }).join('');

  elements.transcriptContainer.innerHTML = html;

  // Add click listeners to segments
  document.querySelectorAll('.transcript-segment').forEach(el => {
    el.addEventListener('click', () => {
      const index = parseInt(el.dataset.index);
      const start = parseFloat(el.dataset.start);

      // Track selected segment for edit modal
      selectedSegmentIndex = index;

      // Remove previous selection visual
      document.querySelectorAll('.transcript-segment').forEach(s => s.classList.remove('segment-selected'));
      el.classList.add('segment-selected');

      seekTo(start);
    });
  });
}

// Update total duration display
function updateTotalDuration() {
  if (duration > 0) {
    elements.totalDuration.textContent = `总时长 ${formatTime(duration)}`;
    elements.totalTime.textContent = formatTime(duration);
  }
}

// ===== Event Listeners =====
function setupEventListeners() {
  // Play/Pause
  elements.playPauseBtn.addEventListener('click', togglePlayPause);

  // Skip buttons
  elements.skipBackBtn.addEventListener('click', () => skip(-10));
  elements.skipForwardBtn.addEventListener('click', () => skip(10));

  // Progress bar
  elements.progressBarContainer.addEventListener('click', handleProgressClick);

  // Volume
  elements.volumeBtn.addEventListener('click', toggleMute);
  elements.volumeSlider.addEventListener('input', handleVolumeChange);

  // Speed
  elements.speedBtn.addEventListener('click', cycleSpeed);

  // Fullscreen
  elements.fullscreenBtn.addEventListener('click', toggleFullscreen);

  // Media events
  elements.mediaPlayer.addEventListener('loadedmetadata', handleMetadataLoaded);
  elements.mediaPlayer.addEventListener('timeupdate', handleTimeUpdate);
  elements.mediaPlayer.addEventListener('ended', handleEnded);

  // Export dropdown
  elements.exportBtn.addEventListener('click', toggleExportDropdown);
  document.querySelectorAll('.dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
      exportAs(item.dataset.format);
    });
  });
  document.addEventListener('click', (e) => {
    if (!elements.exportBtn.contains(e.target)) {
      elements.exportDropdown.hidden = true;
    }
  });

  // Edit modal
  elements.editBtn.addEventListener('click', openEditModal);
  elements.closeModalBtn.addEventListener('click', closeEditModal);
  elements.cancelEditBtn.addEventListener('click', closeEditModal);
  elements.saveEditBtn.addEventListener('click', saveEdit);
  document.querySelector('.modal-backdrop')?.addEventListener('click', closeEditModal);

  // Picture-in-Picture
  elements.pipBtn.addEventListener('click', togglePiP);
  elements.mediaPlayer.addEventListener('enterpictureinpicture', handlePiPEnter);
  elements.mediaPlayer.addEventListener('leavepictureinpicture', handlePiPLeave);

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeydown);
}

// ===== Player Controls =====
function togglePlayPause() {
  if (isPlaying) {
    elements.mediaPlayer.pause();
  } else {
    elements.mediaPlayer.play();
  }
}

function updatePlayPauseIcon() {
  if (isPlaying) {
    elements.playIcon.classList.add('hidden');
    elements.pauseIcon.classList.remove('hidden');
  } else {
    elements.playIcon.classList.remove('hidden');
    elements.pauseIcon.classList.add('hidden');
  }
}

function skip(seconds) {
  const newTime = Math.max(0, Math.min(duration, elements.mediaPlayer.currentTime + seconds));
  elements.mediaPlayer.currentTime = newTime;
}

function seekTo(seconds) {
  elements.mediaPlayer.currentTime = seconds;
  if (!isPlaying) {
    elements.mediaPlayer.play();
  }
}

function handleProgressClick(e) {
  const rect = elements.progressBarContainer.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  const time = percent * duration;
  elements.mediaPlayer.currentTime = time;
}

function updateProgress(percent) {
  elements.progressBar.style.width = `${percent}%`;
  elements.progressHandle.style.left = `${percent}%`;
}

function toggleMute() {
  elements.mediaPlayer.muted = !elements.mediaPlayer.muted;
  updateVolumeIcon();
}

function handleVolumeChange(e) {
  const value = e.target.value;
  elements.mediaPlayer.volume = value / 100;
  elements.mediaPlayer.muted = value === '0';
  updateVolumeIcon();
  updateVolumeSliderBackground(value);
}

function updateVolumeIcon() {
  if (elements.mediaPlayer.muted || elements.mediaPlayer.volume === 0) {
    elements.volumeIcon.classList.add('hidden');
    elements.volumeMuteIcon.classList.remove('hidden');
  } else {
    elements.volumeIcon.classList.remove('hidden');
    elements.volumeMuteIcon.classList.add('hidden');
  }
}

function updateVolumeSliderBackground(value) {
  elements.volumeSlider.style.background = `linear-gradient(to right, #8b5cf6 ${value}%, rgba(255,255,255,0.2) ${value}%)`;
}

function cycleSpeed() {
  currentSpeedIndex = (currentSpeedIndex + 1) % playbackSpeeds.length;
  const speed = playbackSpeeds[currentSpeedIndex];
  elements.mediaPlayer.playbackRate = speed;
  elements.speedBtn.textContent = `${speed}x`;
}

function toggleFullscreen() {
  const container = document.querySelector('.player-container');
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    container.requestFullscreen();
  }
}

// ===== Picture-in-Picture =====
async function togglePiP() {
  try {
    if (document.pictureInPictureElement) {
      await document.exitPictureInPicture();
    } else if (document.pictureInPictureEnabled) {
      await elements.mediaPlayer.requestPictureInPicture();
    } else {
      console.log('Picture-in-Picture not supported');
    }
  } catch (error) {
    console.error('PiP error:', error);
  }
}

function handlePiPEnter() {
  isPiPActive = true;
  elements.pipBtn.classList.add('pip-active');
}

function handlePiPLeave() {
  isPiPActive = false;
  elements.pipBtn.classList.remove('pip-active');
}

// ===== Media Event Handlers =====
function handleMetadataLoaded() {
  duration = elements.mediaPlayer.duration;
  elements.totalTime.textContent = formatTime(duration);
  elements.totalDuration.textContent = `总时长 ${formatTime(duration)}`;
}

function handleTimeUpdate() {
  const currentTime = elements.mediaPlayer.currentTime;
  const percent = (currentTime / duration) * 100;

  elements.currentTime.textContent = formatTime(currentTime);
  updateProgress(percent);
  updateActiveSegment(currentTime);
  updateSubtitleOverlay(currentTime);
}

function handleEnded() {
  isPlaying = false;
  updatePlayPauseIcon();
}

// Watch for play/pause state changes
elements.mediaPlayer.addEventListener('play', () => {
  isPlaying = true;
  updatePlayPauseIcon();
});

elements.mediaPlayer.addEventListener('pause', () => {
  isPlaying = false;
  updatePlayPauseIcon();
});

// ===== Segment Synchronization =====
function updateActiveSegment(currentTime) {
  const segments = document.querySelectorAll('.transcript-segment');
  let newActiveIndex = -1;

  transcriptData.forEach((segment, index) => {
    if (currentTime >= segment.start && currentTime < segment.end) {
      newActiveIndex = index;
    }
  });

  if (newActiveIndex !== currentSegmentIndex) {
    // Remove active from previous
    segments.forEach(el => el.classList.remove('segment-active'));

    // Add active to current
    if (newActiveIndex >= 0 && segments[newActiveIndex]) {
      segments[newActiveIndex].classList.add('segment-active');
      segments[newActiveIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    currentSegmentIndex = newActiveIndex;
  }
}

function updateSubtitleOverlay(currentTime) {
  let currentText = '';

  for (const segment of transcriptData) {
    if (currentTime >= segment.start && currentTime < segment.end) {
      currentText = segment.text;
      break;
    }
  }

  elements.subtitleText.textContent = currentText;
  elements.subtitleOverlay.style.opacity = currentText ? '1' : '0';
}

// ===== Export Functions =====
function toggleExportDropdown(e) {
  e.stopPropagation();
  elements.exportDropdown.hidden = !elements.exportDropdown.hidden;
}

function exportAs(format) {
  let content = '';
  let filename = `transcript_${taskId}`;
  let mimeType = 'text/plain';

  if (format === 'txt') {
    content = transcriptData.map(s =>
      `[${formatTime(s.start)}] 发言人 ${s.speaker || '1'}: ${s.text}`
    ).join('\n\n');
    filename += '.txt';
  } else if (format === 'srt') {
    content = transcriptData.map((s, i) =>
      `${i + 1}\n${formatSrtTime(s.start)} --> ${formatSrtTime(s.end)}\n${s.text}`
    ).join('\n\n');
    filename += '.srt';
  } else if (format === 'md') {
    content = '# 转写结果\n\n' + transcriptData.map(s =>
      `**发言人 ${s.speaker || '1'}** ${formatTime(s.start)}\n\n${s.text}`
    ).join('\n\n---\n\n');
    filename += '.md';
  }

  // Download file
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);

  elements.exportDropdown.hidden = true;
}

// ===== Edit Functions =====
function openEditModal() {
  // Render editable segments
  const html = transcriptData.map((segment, index) => `
    <div class="edit-segment ${index === selectedSegmentIndex ? 'edit-segment-selected' : ''}" data-index="${index}">
      <div class="edit-segment-header">
        <span>发言人 ${segment.speaker || '1'}</span>
        <span>${formatTime(segment.start)}</span>
      </div>
      <textarea class="edit-segment-textarea" data-index="${index}">${segment.text}</textarea>
    </div>
  `).join('');

  elements.editSegments.innerHTML = html;
  elements.editModal.hidden = false;

  // Scroll to selected segment after modal is shown
  if (selectedSegmentIndex >= 0) {
    setTimeout(() => {
      const selectedEl = elements.editSegments.querySelector(`[data-index="${selectedSegmentIndex}"]`);
      if (selectedEl) {
        selectedEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Focus the textarea
        const textarea = selectedEl.querySelector('textarea');
        if (textarea) textarea.focus();
      }
    }, 100);
  }
}

function closeEditModal() {
  elements.editModal.hidden = true;
}

function saveEdit() {
  // Update transcript data from textareas
  document.querySelectorAll('.edit-segment-textarea').forEach(textarea => {
    const index = parseInt(textarea.dataset.index);
    if (transcriptData[index]) {
      transcriptData[index].text = textarea.value;
    }
  });

  // Re-render transcript
  renderTranscript();
  closeEditModal();

  // Show success message (could be a toast notification)
  console.log('字幕已保存');
}

// ===== Keyboard Shortcuts =====
function handleKeydown(e) {
  // Don't trigger if typing in input/textarea
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  switch (e.key) {
    case ' ':
      e.preventDefault();
      togglePlayPause();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      skip(-5);
      break;
    case 'ArrowRight':
      e.preventDefault();
      skip(5);
      break;
    case 'ArrowUp':
      e.preventDefault();
      elements.mediaPlayer.volume = Math.min(1, elements.mediaPlayer.volume + 0.1);
      elements.volumeSlider.value = elements.mediaPlayer.volume * 100;
      updateVolumeSliderBackground(elements.volumeSlider.value);
      break;
    case 'ArrowDown':
      e.preventDefault();
      elements.mediaPlayer.volume = Math.max(0, elements.mediaPlayer.volume - 0.1);
      elements.volumeSlider.value = elements.mediaPlayer.volume * 100;
      updateVolumeSliderBackground(elements.volumeSlider.value);
      break;
    case 'f':
      e.preventDefault();
      toggleFullscreen();
      break;
    case 'm':
      e.preventDefault();
      toggleMute();
      break;
  }
}

// ===== Error Handling =====
function showError(message) {
  elements.transcriptContainer.innerHTML = `
    <div class="loading-placeholder">
      <span style="color: #cf222e;">${message}</span>
      <a href="/" style="color: #6366f1; margin-top: 8px;">返回首页</a>
    </div>
  `;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
