"""Download audio from a YouTube URL and convert it to MP3 or WAV.

Usage:
    python youtube_to_audio.py <url> [--format mp3|wav] [--cookies-from-browser edge]

Requires: pip install yt-dlp imageio-ffmpeg
(imageio-ffmpeg bundles an ffmpeg binary; a system ffmpeg on PATH is used if present.)
"""

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Missing dependency: pip install yt-dlp imageio-ffmpeg")


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found. Install it or run: pip install imageio-ffmpeg")


def download_audio(
    url: str,
    fmt: str,
    output_dir: Path,
    bitrate: str,
    cookie_browser: str | None,
    browser_profile: str | None,
    cookie_file: Path | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    postprocessor = {"key": "FFmpegExtractAudio", "preferredcodec": fmt}
    if fmt == "mp3":
        postprocessor["preferredquality"] = bitrate

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "ffmpeg_location": find_ffmpeg(),
        "postprocessors": [postprocessor],
        "noplaylist": True,
        "quiet": False,
    }
    if cookie_browser:
        options["cookiesfrombrowser"] = (
            cookie_browser,
            browser_profile,
            None,
            None,
        )
    elif cookie_file:
        options["cookiefile"] = str(cookie_file)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        base = Path(ydl.prepare_filename(info)).with_suffix(f".{fmt}")
        print(f"\nSaved: {base}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a YouTube video to MP3 or WAV.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-f", "--format", choices=["mp3", "wav"], default="mp3", help="Output format (default: mp3)")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: ./output)")
    parser.add_argument("-b", "--bitrate", default="192", help="MP3 bitrate in kbps (default: 192)")
    cookies = parser.add_mutually_exclusive_group()
    cookies.add_argument(
        "--cookies-from-browser",
        choices=["brave", "chrome", "chromium", "edge", "firefox", "opera", "vivaldi"],
        help="Use cookies from a browser where you are signed in to YouTube",
    )
    cookies.add_argument(
        "--cookies",
        type=Path,
        help="Use a Netscape-format cookies.txt file",
    )
    parser.add_argument(
        "--browser-profile",
        help="Browser profile name or path, used with --cookies-from-browser",
    )
    args = parser.parse_args()

    if args.browser_profile and not args.cookies_from_browser:
        parser.error("--browser-profile requires --cookies-from-browser")
    if args.cookies and not args.cookies.is_file():
        parser.error(f"cookie file does not exist: {args.cookies}")

    try:
        download_audio(
            args.url,
            args.format,
            Path(args.output),
            args.bitrate,
            args.cookies_from_browser,
            args.browser_profile,
            args.cookies,
        )
    except yt_dlp.utils.DownloadError as e:
        sys.exit(f"Download failed: {e}")


if __name__ == "__main__":
    main()
