async def extract_soundcloud_song_info(search: str) -> dict:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")

    loop = asyncio.get_running_loop()

    def _extract():
        target = search.strip()

        with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ydl:
            if is_url(target):
                if not is_soundcloud_url(target):
                    raise RuntimeError("Only SoundCloud links are allowed.")
                info = ydl.extract_info(target, download=False)
            else:
                # do NOT manually fall back anywhere else
                info = ydl.extract_info(target, download=False)

            if info is None:
                return None

            if "entries" in info:
                entries = info.get("entries") or []
                if not entries:
                    return None
                info = entries[0]

            if info is None:
                return None

            webpage_url = info.get("webpage_url") or ""
            extractor = str(info.get("extractor", "")).lower()
            extractor_key = str(info.get("extractor_key", "")).lower()

            valid_sc = (
                "soundcloud" in extractor
                or "soundcloud" in extractor_key
                or is_soundcloud_url(webpage_url)
            )

            if not valid_sc:
                raise RuntimeError(
                    f"Blocked non-SoundCloud result. extractor={extractor} extractor_key={extractor_key} url={webpage_url}"
                )

            return {
                "title": info.get("title", "Unknown title"),
                "url": info.get("url"),
                "webpage_url": webpage_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown uploader"),
                "thumbnail": info.get("thumbnail"),
                "requested_by": None,
            }

    return await loop.run_in_executor(None, _extract)