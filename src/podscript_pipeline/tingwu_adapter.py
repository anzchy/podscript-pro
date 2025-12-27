"""
Alibaba Cloud Tingwu (通义听悟) adapter for audio transcription.
API Version: 2023-09-30
Docs: https://help.aliyun.com/zh/tingwu/voice-transcription
"""
import logging
import os
import json
import time
import datetime
import mimetypes
import re
from pathlib import Path
from typing import Dict, Any, Callable, TypeVar

from podscript_shared.models import AppConfig

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 2  # Initial backoff in seconds
MAX_BACKOFF_S = 30  # Maximum backoff in seconds

# Error codes that should NOT be retried (business/account errors)
NON_RETRYABLE_ERROR_CODES = {
    "BRK.OverdueTenant",  # Account overdue
    "BRK.InvalidAppKey",  # Invalid AppKey
    "BRK.NoPermission",  # No permission
    "InvalidAccessKeyId.NotFound",  # Invalid AccessKey
    "SignatureDoesNotMatch",  # Invalid signature
}

T = TypeVar('T')


def _is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (transient network/server error)."""
    error_str = str(error)

    # Check for non-retryable business errors
    for code in NON_RETRYABLE_ERROR_CODES:
        if code in error_str:
            return False

    # Check for HTTP status codes in error message
    # 4xx errors (except 429) are generally not retryable
    if "HTTP Status: 4" in error_str and "HTTP Status: 429" not in error_str:
        return False

    # All other errors are considered retryable (network, timeout, 5xx, etc.)
    return True


def _with_retry(
    func: Callable[[], T],
    operation_name: str,
    max_retries: int = MAX_RETRIES,
) -> T:
    """
    Execute a function with exponential backoff retry.

    Args:
        func: Function to execute
        operation_name: Name for logging
        max_retries: Maximum number of retries

    Returns:
        Result from the function

    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    backoff = INITIAL_BACKOFF_S

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt >= max_retries:
                logger.error(f"{operation_name}: All {max_retries + 1} attempts failed")
                raise

            if not _is_retryable_error(e):
                logger.error(f"{operation_name}: Non-retryable error, not retrying: {e}")
                raise

            logger.warning(
                f"{operation_name}: Attempt {attempt + 1} failed: {e}. "
                f"Retrying in {backoff}s..."
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_S)

    raise last_exception  # Should not reach here


def upload_to_oss(cfg: AppConfig, local_file: Path) -> str:
    """Upload local audio file to Alibaba Cloud OSS and return signed URL."""
    import oss2

    logger.info(f"upload_to_oss: Starting upload for {local_file}")
    logger.debug(f"upload_to_oss: file_size={local_file.stat().st_size} bytes")

    ak = (cfg.access_key_id or "").strip()
    sk = (cfg.access_key_secret or "").strip()
    st = (cfg.security_token or "").strip()

    if st:
        logger.debug("upload_to_oss: Using STS authentication")
        auth = oss2.StsAuth(ak, sk, st)
    else:
        logger.debug("upload_to_oss: Using AK/SK authentication")
        auth = oss2.Auth(ak, sk)

    endpoint = cfg.storage_endpoint or f"https://oss-{cfg.storage_region}.aliyuncs.com"
    logger.info(f"upload_to_oss: endpoint={endpoint}, bucket={cfg.storage_bucket}")
    bucket = oss2.Bucket(auth, endpoint, cfg.storage_bucket, connect_timeout=60)

    # Sanitize filename for OSS (preserve Chinese and other Unicode characters)
    sanitized = re.sub(r"\s+", "_", local_file.name)
    # Only remove characters that are problematic for object keys: / \ : * ? " < > | and control chars
    sanitized = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "-", sanitized)

    # Build object key with optional prefix
    prefix = (cfg.storage_prefix or "tingwu-audio").strip().strip("/")
    object_key = f"{prefix}/{sanitized}"
    logger.info(f"upload_to_oss: object_key={object_key}")

    content_type = mimetypes.guess_type(sanitized)[0] or "application/octet-stream"
    headers = {"Content-Type": content_type}
    logger.debug(f"upload_to_oss: content_type={content_type}")

    with open(local_file, "rb") as f:
        logger.info("upload_to_oss: Uploading file to OSS...")
        result = bucket.put_object(object_key, f, headers=headers)
        logger.info(f"upload_to_oss: Upload response status={result.status}")
        if result.status != 200:
            logger.error(f"upload_to_oss: Upload failed with status {result.status}")
            raise RuntimeError(f"OSS upload failed with status: {result.status}")

    # Return signed URL valid for 1 hour
    url = bucket.sign_url("GET", object_key, 3600)
    logger.info(f"upload_to_oss: Generated signed URL (length={len(url)})")
    return url


def _create_tingwu_client(cfg: AppConfig):
    """Create Alibaba Cloud AcsClient for Tingwu API."""
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.auth.credentials import AccessKeyCredential

    logger.debug("_create_tingwu_client: Creating AcsClient with AccessKeyCredential")
    credentials = AccessKeyCredential(
        cfg.access_key_id,
        cfg.access_key_secret
    )
    client = AcsClient(region_id='cn-beijing', credential=credentials)
    logger.debug("_create_tingwu_client: AcsClient created successfully")
    return client


def _create_common_request(method: str, uri: str):
    """Create CommonRequest for Tingwu API."""
    from aliyunsdkcore.request import CommonRequest

    logger.debug(f"_create_common_request: method={method}, uri={uri}")
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('tingwu.cn-beijing.aliyuncs.com')
    request.set_version('2023-09-30')
    request.set_protocol_type('https')
    request.set_method(method)
    request.set_uri_pattern(uri)
    request.add_header('Content-Type', 'application/json')
    return request


def submit_transcribe_job(
    cfg: AppConfig,
    audio_url: str,
    custom_prompt: str | None = None
) -> str:
    """
    Submit an offline transcription task to Tingwu.

    Args:
        cfg: Application config with Alibaba Cloud credentials
        audio_url: Public URL of the audio file to transcribe
        custom_prompt: Optional custom prompt for LLM post-processing.
            Useful for generating different summary granularities,
            extracting specific business information, etc.

    Returns:
        Task ID for polling status
    """
    logger.info(f"submit_transcribe_job: Starting, audio_url length={len(audio_url)}")
    client = _create_tingwu_client(cfg)

    # Build request body
    task_key = 'task' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    logger.info(f"submit_transcribe_job: task_key={task_key}")

    body = {
        'AppKey': cfg.tingwu_app_key,  # Required: Tingwu AppKey from console
        'Input': {
            'SourceLanguage': 'cn',
            'TaskKey': task_key,
            'FileUrl': audio_url,
        },
        'Parameters': {
            'Transcription': {
                'DiarizationEnabled': True,  # Enable speaker diarization
            }
        }
    }

    # Add custom prompt if provided
    # CustomPrompt format: https://help.aliyun.com/zh/tingwu/custom-prompt
    if custom_prompt:
        body['Parameters']['CustomPromptEnabled'] = True
        body['Parameters']['CustomPrompt'] = {
            'Contents': [
                {
                    'Name': 'custom_analysis',
                    'Model': 'tingwu-turbo',  # Options: tingwu-turbo (28k), tingwu-plus (125k), qwen-max (28k)
                    'Prompt': f'{custom_prompt}\n\n转写内容:\n{{Transcription}}',  # Must include {{Transcription}} placeholder
                    'TransType': 'chat',  # Options: default, chat (with speaker), sentence-chat
                }
            ]
        }
        logger.info(f"submit_transcribe_job: Custom prompt enabled, length={len(custom_prompt)}")
    logger.debug(f"submit_transcribe_job: Request body (without FileUrl): AppKey={cfg.tingwu_app_key[:8] if cfg.tingwu_app_key else 'None'}..., SourceLanguage=cn")

    # Create task request with retry logic
    def _submit_request() -> str:
        request = _create_common_request('PUT', '/openapi/tingwu/v2/tasks')
        request.add_query_param('type', 'offline')
        request.set_content(json.dumps(body).encode('utf-8'))

        logger.info("submit_transcribe_job: Sending CreateTask request to Tingwu API...")
        response = client.do_action_with_exception(request)
        result = json.loads(response)
        logger.info(f"submit_transcribe_job: Response Code={result.get('Code')}, Message={result.get('Message')}")

        if result.get('Code') != '0' and result.get('Code') != 0:
            logger.error(f"submit_transcribe_job: CreateTask failed: {result}")
            raise RuntimeError(f"Tingwu CreateTask failed: {result.get('Message', result)}")

        task_id = result['Data']['TaskId']
        logger.info(f"submit_transcribe_job: Task created successfully, task_id={task_id}")
        return task_id

    return _with_retry(_submit_request, "submit_transcribe_job")


def poll_transcribe_result(cfg: AppConfig, task_id: str, timeout_s: int = 600) -> Dict[str, Any]:
    """
    Poll Tingwu task until completion and return transcription result.

    Args:
        cfg: Application config with Alibaba Cloud credentials
        task_id: Task ID from submit_transcribe_job
        timeout_s: Maximum seconds to wait (default 10 minutes)

    Returns:
        Dict with transcription results including sentences and timing
    """
    import httpx

    logger.info(f"poll_transcribe_result: Starting to poll task_id={task_id}, timeout={timeout_s}s")
    client = _create_tingwu_client(cfg)
    start = time.time()
    poll_count = 0

    def _poll_once() -> Dict[str, Any]:
        """Single poll request with retry."""
        request = _create_common_request('GET', f'/openapi/tingwu/v2/tasks/{task_id}')
        response = client.do_action_with_exception(request)
        result = json.loads(response)

        if result.get('Code') != '0' and result.get('Code') != 0:
            logger.error(f"poll_transcribe_result: GetTask failed: {result}")
            raise RuntimeError(f"Tingwu GetTask failed: {result.get('Message', result)}")

        return result

    def _fetch_transcription(url: str) -> Dict[str, Any]:
        """Fetch transcription JSON with retry."""
        logger.info("poll_transcribe_result: Fetching transcription JSON from URL...")
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    while time.time() - start < timeout_s:
        poll_count += 1
        elapsed = int(time.time() - start)
        logger.info(f"poll_transcribe_result: Poll #{poll_count}, elapsed={elapsed}s")

        # Poll with retry
        result = _with_retry(
            _poll_once,
            f"poll_transcribe_result (poll #{poll_count})",
            max_retries=2  # Fewer retries for individual polls
        )

        task_status = result['Data'].get('TaskStatus', '')
        logger.info(f"poll_transcribe_result: TaskStatus={task_status}")

        if task_status == 'COMPLETED':
            logger.info("poll_transcribe_result: Task completed successfully")
            # Get transcription result URL and fetch content
            transcription_url = result['Data'].get('Result', {}).get('Transcription')
            logger.info(f"poll_transcribe_result: Transcription URL exists={bool(transcription_url)}")
            if transcription_url:
                # Fetch the actual transcription JSON with retry
                transcription_data = _with_retry(
                    lambda: _fetch_transcription(transcription_url),
                    "fetch_transcription_json"
                )
                logger.info(f"poll_transcribe_result: Transcription data fetched, keys={list(transcription_data.keys())}")
                return _parse_transcription(transcription_data)
            logger.warning("poll_transcribe_result: No transcription URL in result, returning empty")
            return {'text': '', 'segments': [], 'language': 'zh'}

        elif task_status == 'FAILED':
            error_msg = result['Data'].get('ErrorMessage', 'Task failed')
            logger.error(f"poll_transcribe_result: Task failed with error: {error_msg}")
            raise RuntimeError(f"Tingwu transcription failed: {error_msg}")

        # Still processing, wait and retry
        logger.debug(f"poll_transcribe_result: Task still processing, waiting 5s...")
        time.sleep(5)

    logger.error(f"poll_transcribe_result: Timeout after {timeout_s}s, poll_count={poll_count}")
    raise TimeoutError(f"Tingwu task {task_id} timed out after {timeout_s}s")


def _parse_transcription(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Tingwu transcription result into standard format.

    Args:
        data: Raw transcription JSON from Tingwu

    Returns:
        Normalized dict with text, segments, and language
    """
    logger.info("_parse_transcription: Starting to parse transcription data")
    sentences = []
    full_text_parts = []

    # Tingwu returns transcription in Transcription.Paragraphs or similar structure
    transcription = data.get('Transcription', {})
    paragraphs = transcription.get('Paragraphs', [])
    logger.info(f"_parse_transcription: Found {len(paragraphs)} paragraphs in Transcription.Paragraphs")

    for para in paragraphs:
        words = para.get('Words', [])
        para_text = ''.join(w.get('Text', '') for w in words)
        full_text_parts.append(para_text)

        if words:
            start_time = words[0].get('Start', 0) / 1000.0  # Convert ms to seconds
            end_time = words[-1].get('End', 0) / 1000.0
            sentences.append({
                'start': start_time,
                'end': end_time,
                'text': para_text,
                'speaker': para.get('SpeakerId', '')
            })

    # Alternative structure: direct Sentences array
    if not sentences:
        direct_sentences = data.get('Sentences', [])
        logger.info(f"_parse_transcription: No paragraphs, trying Sentences array ({len(direct_sentences)} items)")
        for sent in direct_sentences:
            sentences.append({
                'start': float(sent.get('StartTime', 0) or sent.get('Start', 0)) / 1000.0,
                'end': float(sent.get('EndTime', 0) or sent.get('End', 0)) / 1000.0,
                'text': sent.get('Text', '') or sent.get('Sentence', ''),
                'speaker': sent.get('SpeakerId', '')
            })
            full_text_parts.append(sent.get('Text', '') or sent.get('Sentence', ''))

    result = {
        'text': '\n'.join(full_text_parts),
        'segments': sentences,
        'language': data.get('Language', 'zh')
    }
    logger.info(f"_parse_transcription: Parsed {len(sentences)} segments, text length={len(result['text'])}")
    return result
