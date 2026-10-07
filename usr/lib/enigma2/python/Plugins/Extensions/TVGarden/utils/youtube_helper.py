# -*- coding: utf-8 -*-
"""
TV Garden Plugin - YouTube helper
[TVGarden patch] Risoluzione YouTube con yt-dlp.

yt-dlp is started with a format fallback chain ("18/22/.../best"):
live webcams only offer HLS, so trying formats one by one (one slow
yt-dlp start each) used to hit the timeouts on receivers.

Recent yt-dlp needs a JavaScript runtime (deno) for the default YouTube
clients; deno does not exist for most receivers (32-bit ARM / MIPS).
The android_vr client works without JavaScript and returns a muxed HLS
stream, so it is tried first; the default clients are the fallback.
"""
import subprocess
import re
import sys
from os.path import exists
from shutil import which
from urllib.parse import unquote
from ..helpers import log


# Receivers are slow: starting yt-dlp alone can take 10+ seconds
VERSION_TIMEOUT = 60
RESOLVE_TIMEOUT = 150

# Progressive MP4 first (VOD), then anything playable (live = HLS)
FORMAT_CHAIN = "18/22/best[ext=mp4][protocol^=http]/best"

# Attempts in order: extra yt-dlp arguments for each run
CLIENT_ATTEMPTS = [
    ["--extractor-args", "youtube:player_client=android_vr"],
    [],
]

# JavaScript runtimes yt-dlp can use besides deno (enabled if installed)
JS_RUNTIMES = (("node", "node"), ("bun", "bun"), ("quickjs", "qjs"))

_ytdlp_cmd = None
_js_args = None


def find_js_runtime_args():
    """--js-runtimes arguments for an installed runtime (empty if none)"""
    global _js_args
    if _js_args is None:
        _js_args = []
        for runtime, binary in JS_RUNTIMES:
            path = which(binary)
            if path:
                log.info("JavaScript runtime found: %s" %
                         path, module="YouTube")
                _js_args = ["--js-runtimes", "%s:%s" % (runtime, path)]
                break
    return _js_args


def find_ytdlp():
    """
    Return the command (list) used to run yt-dlp, or None.
    Supports the yt-dlp binary and the python module (python3 -m yt_dlp).
    """
    global _ytdlp_cmd
    if _ytdlp_cmd:
        return _ytdlp_cmd

    candidates = []
    found = which("yt-dlp")
    if found:
        candidates.append([found])
    for path in ("/usr/bin/yt-dlp", "/usr/local/bin/yt-dlp"):
        if exists(path) and [path] not in candidates:
            candidates.append([path])
    for python in (sys.executable, "/usr/bin/python3", "/usr/bin/python"):
        if python and exists(python):
            candidates.append([python, "-m", "yt_dlp"])

    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd + ["--version"], capture_output=True, text=True,
                timeout=VERSION_TIMEOUT)
            if result.returncode == 0:
                log.info("yt-dlp found: %s (version %s)" %
                         (" ".join(cmd), result.stdout.strip()),
                         module="YouTube")
                _ytdlp_cmd = cmd
                return cmd
        except subprocess.TimeoutExpired:
            log.warning("yt-dlp too slow to start: %s" %
                        " ".join(cmd), module="YouTube")
        except Exception as e:
            log.debug("yt-dlp candidate %s failed: %s" %
                      (" ".join(cmd), e), module="YouTube")

    log.error("yt-dlp not found", module="YouTube")
    return None


def extract_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?(?:.*&)?v=([^&#]+)',
        r'(?:https?://)?youtu\.be/([^?&#/]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^/?&#]+)',
        r'(?:https?://)?(?:www\.)?youtube-nocookie\.com/embed/([^/?&#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^/?&#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^/?&#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/live/([^/?&#]+)',
    ]
    try:
        decoded = unquote(url)
        for pattern in patterns:
            match = re.search(pattern, decoded, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception as e:
        log.error("Error extracting video ID: %s" % e, module="YouTube")
    return None


def _short_error(stderr):
    """Last meaningful yt-dlp error line"""
    lines = [line.strip() for line in (stderr or "").splitlines()
             if line.strip()]
    errors = [line for line in lines if line.startswith("ERROR")]
    text = (errors or lines or ["unknown error"])[-1]
    text = text.replace("ERROR: ", "")
    return text[:160]


def _run_ytdlp(cmd):
    """Run one yt-dlp command; return (stream_url, error_message)"""
    log.info("yt-dlp: %s" % " ".join(cmd), module="YouTube")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=RESOLVE_TIMEOUT)
    except subprocess.TimeoutExpired:
        log.warning("yt-dlp timeout", module="YouTube")
        return None, "yt-dlp timeout"
    except Exception as e:
        log.warning("yt-dlp error: %s" % e, module="YouTube")
        return None, str(e)

    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if line.startswith(("http://", "https://")):
            log.info("yt-dlp OK: %s..." % line[:80], module="YouTube")
            return line, None

    log.warning("yt-dlp failed (code %s): %s" %
                (result.returncode, result.stderr[-500:] if result.stderr else ""),
                module="YouTube")
    return None, _short_error(result.stderr)


def get_stream_with_ytdlp(ytdlp_cmd, video_id):
    """Resolve video_id; return (stream_url, error_message)"""
    youtube_url = "https://www.youtube.com/watch?v=" + video_id
    base = ytdlp_cmd + [
        "-g", "--no-playlist", "--no-warnings",
        "--socket-timeout", "20",
        "-f", FORMAT_CHAIN,
    ] + find_js_runtime_args()

    error = None
    for extra in CLIENT_ATTEMPTS:
        stream_url, error = _run_ytdlp(base + extra + [youtube_url])
        if stream_url:
            return stream_url, None
        if error == "yt-dlp timeout":
            break
    return None, error


def resolve_youtube(url):
    """Resolve a YouTube URL; return (stream_url, error_message)"""
    video_id = extract_video_id(url)
    if not video_id:
        log.error("Cannot extract video ID from: %s" % url, module="YouTube")
        return None, "invalid YouTube URL"

    ytdlp = find_ytdlp()
    if not ytdlp:
        return None, "yt-dlp is not installed"

    return get_stream_with_ytdlp(ytdlp, video_id)


def get_youtube_stream(url):
    """Resolve a YouTube URL; return the stream URL or None"""
    return resolve_youtube(url)[0]
