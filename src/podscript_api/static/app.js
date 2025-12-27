const els = {
  url: document.getElementById('url'),
  file: document.getElementById('file'),
  fileLabel: document.getElementById('fileLabel'),
  fileLabelText: document.getElementById('fileLabelText'),
  fileStatus: document.getElementById('fileStatus'),
  fileStatusText: document.getElementById('fileStatusText'),
  directAudioUrl: document.getElementById('directAudioUrl'),
  downloadBtn: document.getElementById('downloadBtn'),
  transcribeBtn: document.getElementById('transcribeBtn'),
  transcribeHint: document.getElementById('transcribeHint'),
  downloadError: document.getElementById('downloadError'),
  transcribeError: document.getElementById('transcribeError'),
  taskId: document.getElementById('taskId'),
  status: document.getElementById('status'),
  progressBar: document.getElementById('progressBar'),
  result: document.getElementById('result'),
  links: document.getElementById('links'),
  srtLink: document.getElementById('srtLink'),
  mdLink: document.getElementById('mdLink'),
  viewResultLink: document.getElementById('viewResultLink'),
  // Progress elements
  transcribeProgress: document.getElementById('transcribeProgress'),
  transcribeStatus: document.getElementById('transcribeStatus'),
  transcribeProgressBar: document.getElementById('transcribeProgressBar'),
  logContent: document.getElementById('logContent'),
  // Provider options
  whisperOptions: document.getElementById('whisperOptions'),
  tingwuOptions: document.getElementById('tingwuOptions'),
  whisperModel: document.getElementById('whisperModel'),
  downloadModelBtn: document.getElementById('downloadModelBtn'),
  modelStatus: document.getElementById('modelStatus'),
  // Custom prompt
  customPrompt: document.getElementById('customPrompt'),
  // Streaming transcript
  streamingTranscript: document.getElementById('streamingTranscript'),
  transcriptSegments: document.getElementById('transcriptSegments'),
  segmentCount: document.getElementById('segmentCount'),
}

let currentTaskId = null
let pollTimer = null
let isReadyToTranscribe = false
let hasDirectAudioUrl = false  // Track if direct audio URL is provided
let displayedSegmentCount = 0  // Track how many segments have been rendered

// Get selected provider
function getSelectedProvider() {
  const checked = document.querySelector('input[name="provider"]:checked')
  return checked ? checked.value : 'whisper'
}

// Toggle provider options visibility
function toggleProviderOptions() {
  const provider = getSelectedProvider()
  els.whisperOptions.hidden = provider !== 'whisper'
  els.tingwuOptions.hidden = provider !== 'tingwu'
}

// Check model download status
async function checkModelStatus() {
  try {
    const res = await fetch('/asr/whisper/models')
    if (!res.ok) return
    const models = await res.json()
    const selected = els.whisperModel.value
    const model = models[selected]
    if (model) {
      if (model.downloaded) {
        els.modelStatus.textContent = '模型已下载'
        els.modelStatus.className = 'model-status downloaded'
      } else {
        els.modelStatus.textContent = '模型未下载，首次使用将自动下载'
        els.modelStatus.className = 'model-status'
      }
    }
  } catch (e) {
    els.modelStatus.textContent = 'Whisper 未安装，请运行: pip install openai-whisper'
    els.modelStatus.className = 'model-status'
  }
}

// Download Whisper model
async function downloadModel() {
  const modelName = els.whisperModel.value
  els.downloadModelBtn.disabled = true
  els.modelStatus.textContent = '正在下载模型...'
  els.modelStatus.className = 'model-status downloading'

  try {
    const res = await fetch('/asr/whisper/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName })
    })
    const data = await res.json()
    if (data.status === 'already_downloaded') {
      els.modelStatus.textContent = '模型已下载'
      els.modelStatus.className = 'model-status downloaded'
    } else {
      els.modelStatus.textContent = '模型下载中，请稍候...'
      els.modelStatus.className = 'model-status downloading'
      // Poll for completion
      setTimeout(checkModelStatus, 5000)
    }
  } catch (e) {
    els.modelStatus.textContent = '下载失败: ' + e.message
    els.modelStatus.className = 'model-status'
  } finally {
    els.downloadModelBtn.disabled = false
  }
}

async function createTask(sourceUrl) {
  const res = await fetch('/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_url: sourceUrl })
  })
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(msg || '请求失败')
  }
  return res.json()
}

async function uploadTask(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/tasks/upload', { method: 'POST', body: fd })
  if (!res.ok) { const msg = await res.text(); throw new Error(msg || '上传失败') }
  return res.json()
}

async function startTranscribe(taskId, provider, modelName, prompt) {
  const params = new URLSearchParams({ provider })
  if (modelName && provider === 'whisper') {
    params.append('model_name', modelName)
  }
  if (prompt && prompt.trim()) {
    params.append('prompt', prompt.trim())
  }
  const res = await fetch(`/tasks/${taskId}/transcribe?${params.toString()}`, { method: 'POST' })
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(msg || '转写请求失败')
  }
  return res.json()
}

async function fetchTask(id) {
  const res = await fetch(`/tasks/${id}`)
  if (!res.ok) throw new Error('任务查询失败')
  return res.json()
}

async function fetchResults(id) {
  const res = await fetch(`/tasks/${id}/results`)
  if (!res.ok) throw new Error('结果未就绪')
  return res.json()
}

async function fetchLogs(id) {
  const res = await fetch(`/tasks/${id}/logs`)
  if (!res.ok) return []
  return res.json()
}

async function fetchMarkdown(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error('Markdown 加载失败')
  return res.text()
}

function setDownloadError(text) {
  els.downloadError.textContent = text
  els.downloadError.hidden = !text
}

function setTranscribeError(text) {
  els.transcribeError.textContent = text
  els.transcribeError.hidden = !text
}

function setProgress(p) {
  const val = Math.max(0, Math.min(1, p || 0))
  els.progressBar.style.width = `${Math.floor(val * 100)}%`
}

function setTranscribeProgress(p) {
  const val = Math.max(0, Math.min(1, p || 0))
  els.transcribeProgressBar.style.width = `${Math.floor(val * 100)}%`
}

// Check if URL looks like an audio/video URL
function isAudioVideoUrl(url) {
  if (!url) return false
  try {
    new URL(url)  // Validate URL format
    // Check for common audio/video extensions or cloud storage patterns
    const audioVideoPatterns = [
      /\.(mp3|wav|m4a|aac|ogg|flac|wma|mp4|mkv|avi|mov|webm|m4v)(\?|$)/i,
      /\.(oss|cos)[-.].*\.aliyuncs\.com/i,  // Alibaba OSS
      /\.cos\..*\.myqcloud\.com/i,  // Tencent COS
      /storage\.googleapis\.com/i,  // Google Cloud Storage
      /\.s3\..*\.amazonaws\.com/i,  // AWS S3
      /\.blob\.core\.windows\.net/i,  // Azure Blob
    ]
    return audioVideoPatterns.some(pattern => pattern.test(url))
  } catch {
    return false
  }
}

// Check and update direct audio URL state
function checkDirectAudioUrl() {
  const url = els.directAudioUrl.value.trim()
  hasDirectAudioUrl = isAudioVideoUrl(url)
  updateTranscribeButton()
}

function updateTranscribeButton() {
  if (isReadyToTranscribe || hasDirectAudioUrl) {
    els.transcribeBtn.disabled = false
    if (hasDirectAudioUrl && !isReadyToTranscribe) {
      els.transcribeHint.textContent = '检测到音频链接，点击直接转写'
      els.transcribeHint.style.color = '#da7756'
    } else {
      els.transcribeHint.textContent = '音频已就绪，点击开始转写'
      els.transcribeHint.style.color = '#2ea043'
    }
  } else {
    els.transcribeBtn.disabled = true
    els.transcribeHint.textContent = '请先下载音频或上传本地文件'
    els.transcribeHint.style.color = '#666'
  }
}

function updateLogViewer(logs) {
  if (!logs || logs.length === 0) return

  let html = ''
  for (const log of logs) {
    const levelClass = log.level === 'error' ? 'log-error' : log.level === 'warn' ? 'log-warn' : 'log-info'
    html += `<div class="log-line"><span class="log-time">[${log.time}]</span> <span class="${levelClass}">${log.message}</span></div>`
  }
  els.logContent.innerHTML = html

  // Auto scroll to bottom
  const viewer = document.getElementById('logViewer')
  viewer.scrollTop = viewer.scrollHeight
}

// Format time in MM:SS format
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// Get speaker avatar class
function getSpeakerClass(speaker) {
  if (!speaker) return 'speaker-unknown'
  const num = parseInt(speaker.replace(/\D/g, '')) || 0
  if (num >= 1 && num <= 5) return `speaker-${num}`
  return `speaker-${(num % 5) + 1}`
}

// Render a single transcript segment
function renderTranscriptSegment(segment, index, isNew = false) {
  const speakerNum = segment.speaker ? segment.speaker.replace(/\D/g, '') || '?' : '?'
  const speakerLabel = segment.speaker ? `发言人 ${speakerNum}` : '发言人'
  const speakerClass = getSpeakerClass(segment.speaker)

  const div = document.createElement('div')
  div.className = `transcript-segment${isNew ? ' segment-new' : ''}`
  div.dataset.index = index

  div.innerHTML = `
    <div class="segment-speaker">
      <div class="segment-avatar ${speakerClass}">${speakerNum}</div>
      <span class="segment-time">${formatTime(segment.start)}</span>
    </div>
    <div class="segment-content">
      <div class="segment-label">${speakerLabel}</div>
      <div class="segment-text">${segment.text}</div>
    </div>
  `

  // Remove the "new" highlight after animation
  if (isNew) {
    setTimeout(() => {
      div.classList.remove('segment-new')
    }, 2000)
  }

  return div
}

// Show loading state in transcript
function showTranscriptLoading() {
  els.result.hidden = true
  els.streamingTranscript.hidden = false
  els.transcriptSegments.innerHTML = `
    <div class="segment-loading">
      <div class="segment-loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `
}

// Update streaming transcript display with new segments
function updateStreamingTranscript(segments) {
  if (!segments || segments.length === 0) return

  // If this is the first update, clear loading state
  if (displayedSegmentCount === 0 && els.transcriptSegments.querySelector('.segment-loading')) {
    els.transcriptSegments.innerHTML = ''
  }

  // Add only new segments
  for (let i = displayedSegmentCount; i < segments.length; i++) {
    const segment = segments[i]
    const isNew = i === segments.length - 1 && segments.length > displayedSegmentCount
    const segmentEl = renderTranscriptSegment(segment, i, isNew)
    els.transcriptSegments.appendChild(segmentEl)
  }

  // Update displayed count
  displayedSegmentCount = segments.length

  // Update segment count badge
  els.segmentCount.textContent = `${segments.length} 段`
  els.segmentCount.hidden = false

  // Auto scroll to the latest segment
  els.streamingTranscript.scrollTop = els.streamingTranscript.scrollHeight
}

// Reset streaming transcript
function resetStreamingTranscript() {
  displayedSegmentCount = 0
  els.transcriptSegments.innerHTML = ''
  els.streamingTranscript.hidden = true
  els.segmentCount.hidden = true
}

function resetUI() {
  setDownloadError('')
  setTranscribeError('')
  els.taskId.textContent = '-'
  els.status.textContent = '-'
  setProgress(0)
  els.result.textContent = '尚未生成'
  els.result.hidden = false
  els.links.hidden = true
  els.srtLink.href = '#'
  els.mdLink.href = '#'
  els.viewResultLink.href = '#'
  isReadyToTranscribe = false
  // Don't reset hasDirectAudioUrl here - let user keep their URL
  updateTranscribeButton()
  els.transcribeProgress.hidden = true
  els.logContent.innerHTML = ''
  resetStreamingTranscript()
  // Reset file upload status
  els.fileStatus.hidden = true
  els.fileLabel.classList.remove('file-selected')
  els.fileLabelText.textContent = '点击或拖拽上传本地音/视频文件'
}

function getStatusText(status) {
  const map = {
    'queued': '排队中',
    'downloading': '下载中...',
    'downloaded': '下载完成，可开始转写',
    'transcribing': '转写中...',
    'formatting': '格式化中...',
    'completed': '完成',
    'failed': '失败',
    'retrying': '重试中...'
  }
  return map[status] || status
}

async function startDownload() {
  resetUI()
  const url = els.url.value.trim()
  if (!url) { setDownloadError('请输入YouTube链接'); return }

  els.downloadBtn.disabled = true
  try {
    const task = await createTask(url)
    currentTaskId = task.id
    els.taskId.textContent = currentTaskId
    els.status.textContent = getStatusText(task.status)
    setProgress(task.progress)
    poll()
  } catch (e) {
    setDownloadError(String(e.message || e))
  } finally {
    els.downloadBtn.disabled = false
  }
}

async function handleFileUpload() {
  const file = els.file.files && els.file.files[0]
  if (!file) return

  // Reset file-specific UI only
  setTranscribeError('')
  els.fileStatus.hidden = true
  els.fileLabel.classList.remove('file-selected')

  try {
    // Show uploading state
    els.fileLabelText.textContent = '上传中...'

    const task = await uploadTask(file)
    currentTaskId = task.id

    // Show file selected status below upload area (not in status card)
    els.fileLabel.classList.add('file-selected')
    els.fileLabelText.textContent = '点击或拖拽上传本地音/视频文件'
    els.fileStatus.hidden = false
    els.fileStatusText.textContent = `已选定本地文件: ${file.name}`

    if (task.status === 'downloaded') {
      isReadyToTranscribe = true
      updateTranscribeButton()
    }
  } catch (e) {
    els.fileLabelText.textContent = '点击或拖拽上传本地音/视频文件'
    setTranscribeError(String(e.message || e))
  }
}

// Create task with direct audio URL (skip upload, go straight to transcription)
async function createDirectUrlTask(audioUrl, provider, modelName, prompt) {
  const body = {
    audio_url: audioUrl,
    provider: provider
  }
  if (modelName && provider === 'whisper') {
    body.model_name = modelName
  }
  if (prompt && prompt.trim()) {
    body.prompt = prompt.trim()
  }
  const res = await fetch('/tasks/transcribe-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(msg || '转写请求失败')
  }
  return res.json()
}

async function transcribe() {
  const directUrl = els.directAudioUrl.value.trim()
  const provider = getSelectedProvider()
  const modelName = provider === 'whisper' ? els.whisperModel.value : null
  const prompt = els.customPrompt ? els.customPrompt.value : ''

  // Reset streaming transcript for new transcription
  resetStreamingTranscript()
  showTranscriptLoading()

  // If direct URL is provided and no file is uploaded, use direct URL mode
  if (directUrl && hasDirectAudioUrl && !isReadyToTranscribe) {
    els.transcribeBtn.disabled = true
    els.transcribeHint.textContent = '转写进行中...'
    setTranscribeError('')

    // Show progress section
    els.transcribeProgress.hidden = false
    els.transcribeStatus.textContent = '提交转写任务...'
    setTranscribeProgress(0.3)

    try {
      const task = await createDirectUrlTask(directUrl, provider, modelName, prompt)
      currentTaskId = task.id
      els.taskId.textContent = currentTaskId
      els.status.textContent = getStatusText(task.status)
      pollTranscription()
    } catch (e) {
      setTranscribeError(String(e.message || e))
      els.transcribeBtn.disabled = false
      updateTranscribeButton()
      els.transcribeProgress.hidden = true
      resetStreamingTranscript()
      els.result.hidden = false
    }
    return
  }

  // Normal flow: require existing task
  if (!currentTaskId) {
    setTranscribeError('请先下载音频或上传文件')
    resetStreamingTranscript()
    els.result.hidden = false
    return
  }

  els.transcribeBtn.disabled = true
  els.transcribeHint.textContent = '转写进行中...'
  setTranscribeError('')

  // Show progress section
  els.transcribeProgress.hidden = false
  els.transcribeStatus.textContent = '准备中...'
  setTranscribeProgress(0.5)

  try {
    await startTranscribe(currentTaskId, provider, modelName, prompt)
    pollTranscription()
  } catch (e) {
    setTranscribeError(String(e.message || e))
    els.transcribeBtn.disabled = false
    updateTranscribeButton()
    els.transcribeProgress.hidden = true
    resetStreamingTranscript()
    els.result.hidden = false
  }
}

async function poll() {
  clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const t = await fetchTask(currentTaskId)
      els.status.textContent = getStatusText(t.status)
      setProgress(t.progress)

      // Update logs
      const logs = await fetchLogs(currentTaskId)
      updateLogViewer(logs)

      // Download complete - enable transcribe button
      if (t.status === 'downloaded') {
        clearInterval(pollTimer)
        isReadyToTranscribe = true
        updateTranscribeButton()
      }

      // Failed
      if (t.status === 'failed' && t.error) {
        clearInterval(pollTimer)
        setDownloadError(t.error.message || '下载失败')
      }
    } catch (e) {
      clearInterval(pollTimer)
      setDownloadError('状态轮询失败')
    }
  }, 1000)
}

async function pollTranscription() {
  clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const t = await fetchTask(currentTaskId)
      els.status.textContent = getStatusText(t.status)
      setProgress(t.progress)

      // Update transcription progress
      els.transcribeStatus.textContent = getStatusText(t.status)
      setTranscribeProgress(t.progress)

      // Update logs
      const logs = await fetchLogs(currentTaskId)
      updateLogViewer(logs)

      // Update streaming transcript with partial segments
      if (t.partial_segments && t.partial_segments.length > 0) {
        updateStreamingTranscript(t.partial_segments)
      }

      // Transcription complete - show results and enable view button
      if (t.status === 'completed') {
        clearInterval(pollTimer)
        isReadyToTranscribe = false
        els.transcribeBtn.disabled = true
        els.transcribeHint.textContent = '转写完成！'
        els.transcribeHint.style.color = '#2ea043'
        els.transcribeStatus.textContent = '完成！'

        // Show result links
        els.srtLink.href = `/artifacts/${currentTaskId}/result.srt`
        els.mdLink.href = `/artifacts/${currentTaskId}/result.md`
        els.viewResultLink.href = `/static/result.html?task_id=${currentTaskId}`
        els.links.hidden = false

        // If we have partial_segments, display them now (final update)
        if (t.partial_segments && t.partial_segments.length > 0) {
          updateStreamingTranscript(t.partial_segments)
        } else {
          // Fallback: fetch full transcript from result endpoint
          try {
            const transcript = await fetch(`/tasks/${currentTaskId}/transcript`)
            if (transcript.ok) {
              const data = await transcript.json()
              if (data.segments && data.segments.length > 0) {
                updateStreamingTranscript(data.segments)
              }
            }
          } catch (e) {
            console.log('Could not fetch transcript:', e)
          }
        }
      }

      // Failed
      if (t.status === 'failed' && t.error) {
        clearInterval(pollTimer)
        setTranscribeError(t.error.message || '转写失败')
        isReadyToTranscribe = false
        updateTranscribeButton()
        els.transcribeStatus.textContent = '失败'
        resetStreamingTranscript()
        els.result.hidden = false
      }
    } catch (e) {
      clearInterval(pollTimer)
      setTranscribeError('状态轮询失败')
    }
  }, 1000)
}

// Event Listeners
els.downloadBtn.addEventListener('click', startDownload)
els.transcribeBtn.addEventListener('click', transcribe)
els.file.addEventListener('change', handleFileUpload)
els.downloadModelBtn.addEventListener('click', downloadModel)
els.whisperModel.addEventListener('change', checkModelStatus)

// Direct audio URL input - check on input and blur
els.directAudioUrl.addEventListener('input', checkDirectAudioUrl)
els.directAudioUrl.addEventListener('blur', checkDirectAudioUrl)

// Provider radio change
document.querySelectorAll('input[name="provider"]').forEach(radio => {
  radio.addEventListener('change', toggleProviderOptions)
})

// Initialize
toggleProviderOptions()
checkModelStatus()
checkDirectAudioUrl()  // Check if URL was pre-filled
