const els = {
  url: document.getElementById('url'),
  file: document.getElementById('file'),
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
}

let currentTaskId = null
let pollTimer = null
let isReadyToTranscribe = false

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

async function startTranscribe(taskId, provider, modelName) {
  const params = new URLSearchParams({ provider })
  if (modelName && provider === 'whisper') {
    params.append('model_name', modelName)
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

function updateTranscribeButton() {
  if (isReadyToTranscribe) {
    els.transcribeBtn.disabled = false
    els.transcribeHint.textContent = '音频已就绪，点击开始转写'
    els.transcribeHint.style.color = '#2ea043'
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

function resetUI() {
  setDownloadError('')
  setTranscribeError('')
  els.taskId.textContent = '-'
  els.status.textContent = '-'
  setProgress(0)
  els.result.textContent = '尚未生成'
  els.links.hidden = true
  els.srtLink.href = '#'
  els.mdLink.href = '#'
  isReadyToTranscribe = false
  updateTranscribeButton()
  els.transcribeProgress.hidden = true
  els.logContent.innerHTML = ''
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

  resetUI()
  setTranscribeError('')

  try {
    els.status.textContent = '上传中...'
    const task = await uploadTask(file)
    currentTaskId = task.id
    els.taskId.textContent = currentTaskId
    els.status.textContent = getStatusText(task.status)
    setProgress(task.progress)

    if (task.status === 'downloaded') {
      isReadyToTranscribe = true
      updateTranscribeButton()
    }
  } catch (e) {
    setTranscribeError(String(e.message || e))
  }
}

async function transcribe() {
  if (!currentTaskId) {
    setTranscribeError('请先下载音频或上传文件')
    return
  }

  const provider = getSelectedProvider()
  const modelName = provider === 'whisper' ? els.whisperModel.value : null

  els.transcribeBtn.disabled = true
  els.transcribeHint.textContent = '转写进行中...'
  setTranscribeError('')

  // Show progress section
  els.transcribeProgress.hidden = false
  els.transcribeStatus.textContent = '准备中...'
  setTranscribeProgress(0.5)

  try {
    await startTranscribe(currentTaskId, provider, modelName)
    pollTranscription()
  } catch (e) {
    setTranscribeError(String(e.message || e))
    els.transcribeBtn.disabled = false
    updateTranscribeButton()
    els.transcribeProgress.hidden = true
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

      // Transcription complete - show results
      if (t.status === 'completed') {
        clearInterval(pollTimer)
        isReadyToTranscribe = false
        els.transcribeBtn.disabled = true
        els.transcribeHint.textContent = '转写完成！'
        els.transcribeHint.style.color = '#2ea043'
        els.transcribeStatus.textContent = '完成！'

        const r = await fetchResults(currentTaskId)
        els.links.hidden = false
        els.srtLink.href = r.srt_url
        els.mdLink.href = r.markdown_url
        try {
          const md = await fetchMarkdown(r.markdown_url)
          els.result.textContent = md
        } catch {
          els.result.textContent = '结果已生成，点击下方链接下载.'
        }
      }

      // Failed
      if (t.status === 'failed' && t.error) {
        clearInterval(pollTimer)
        setTranscribeError(t.error.message || '转写失败')
        isReadyToTranscribe = false
        updateTranscribeButton()
        els.transcribeStatus.textContent = '失败'
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

// Provider radio change
document.querySelectorAll('input[name="provider"]').forEach(radio => {
  radio.addEventListener('change', toggleProviderOptions)
})

// Initialize
toggleProviderOptions()
checkModelStatus()
