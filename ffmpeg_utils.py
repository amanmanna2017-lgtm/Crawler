import asyncio
import subprocess
import os

async def run_ffmpeg(cmd):
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    return proc.returncode == 0, stderr.decode()

async def extract_metadata(file_path):
    duration = width = height = 0
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    if stdout:
        try:
            duration = int(float(stdout.decode().strip()))
        except: pass
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", file_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    if stdout:
        parts = stdout.decode().strip().split(',')
        if len(parts) >= 2:
            try:
                width = int(parts[0])
                height = int(parts[1])
            except: pass
    return duration, width, height

async def generate_thumbnail(video_path, thumb_path, time_offset="00:00:01"):
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    success, _ = await run_ffmpeg([
        "ffmpeg", "-i", video_path, "-ss", time_offset, "-vframes", "1",
        "-vf", "scale=320:-1", "-q:v", "2", thumb_path, "-y"
    ])
    return success

async def verify_integrity(file_path):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", file_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    return len(stderr) == 0
