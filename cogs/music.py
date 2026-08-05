import asyncio
import logging
import os
import random
import shutil
from collections import defaultdict, deque
from dataclasses import dataclass

import discord
from discord.ext import commands
import yt_dlp

try:
    import imageio_ffmpeg
except Exception:
    imageio_ffmpeg = None

logger = logging.getLogger("springbot.music")


@dataclass(slots=True)
class Track:
    query: str
    title: str
    webpage_url: str
    requester: str
    channel_id: int
    source: str = "Unknown"
    duration: int | None = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = defaultdict(deque)
        self.current: dict[int, Track] = {}
        self.volumes = defaultdict(lambda: 0.5)
        self.looping: set[int] = set()
        self.locks = defaultdict(asyncio.Lock)
        self.cookies_file = os.getenv("YTDLP_COOKIES_FILE", "cookies.txt")
        self.ffmpeg_path = self._find_ffmpeg()
        self.ytdl_options = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "cachedir": False,
            "source_address": "0.0.0.0",
            "cookiefile": self.cookies_file if os.path.isfile(self.cookies_file) else None,
        }

    @staticmethod
    def _find_ffmpeg() -> str:
        configured = os.getenv("FFMPEG_PATH")
        if configured and (shutil.which(configured) or os.path.isfile(configured)):
            return shutil.which(configured) or configured
        found = shutil.which("ffmpeg")
        if found:
            return found
        if imageio_ffmpeg:
            try:
                bundled = imageio_ffmpeg.get_ffmpeg_exe()
                if bundled and os.path.isfile(bundled):
                    return bundled
            except Exception:
                logger.exception("Could not locate imageio-ffmpeg")
        return "ffmpeg"

    def _ffmpeg_ready(self) -> bool:
        return bool(shutil.which(self.ffmpeg_path) or os.path.isfile(self.ffmpeg_path))

    async def _extract(self, target: str) -> dict:
        def run() -> dict:
            with yt_dlp.YoutubeDL(self.ytdl_options) as ydl:
                return ydl.extract_info(target, download=False)
        return await asyncio.to_thread(run)

    @staticmethod
    def _entry(data: dict) -> dict:
        if not data:
            raise RuntimeError("No results found.")
        entries = data.get("entries")
        if entries is not None:
            data = next((item for item in entries if item), None)
        if not data:
            raise RuntimeError("No results found.")
        return data

    async def _find_track(self, ctx: commands.Context, query: str) -> Track:
        targets = [query] if query.startswith(("http://", "https://")) else [
            f"ytsearch1:{query}",
            f"scsearch1:{query}",
        ]
        errors = []
        for target in targets:
            try:
                data = self._entry(await self._extract(target))
                return Track(
                    query=query,
                    title=data.get("title") or "Unknown title",
                    webpage_url=data.get("webpage_url") or data.get("original_url") or query,
                    requester=ctx.author.display_name,
                    channel_id=ctx.channel.id,
                    source=data.get("extractor_key") or data.get("extractor") or "Unknown",
                    duration=data.get("duration"),
                )
            except Exception as exc:
                errors.append(str(exc))
        detail = " | ".join(errors[-2:]).lower()
        if "sign in to confirm" in detail or "not a bot" in detail:
            raise RuntimeError("YouTube blocked the request. Try a SoundCloud link or configure YTDLP_COOKIES_FILE.")
        raise RuntimeError("No playable result was found.")

    async def _fresh_source(self, guild_id: int, track: Track) -> discord.AudioSource:
        data = self._entry(await self._extract(track.webpage_url or track.query))
        stream_url = data.get("url")
        if not stream_url:
            raise RuntimeError("The track did not provide an audio stream.")
        track.title = data.get("title") or track.title
        track.webpage_url = data.get("webpage_url") or track.webpage_url
        track.source = data.get("extractor_key") or data.get("extractor") or track.source
        track.duration = data.get("duration") or track.duration
        audio = discord.FFmpegPCMAudio(
            stream_url,
            executable=self.ffmpeg_path,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
            options="-vn -loglevel warning",
        )
        return discord.PCMVolumeTransformer(audio, volume=self.volumes[guild_id])

    async def _voice(self, ctx: commands.Context) -> discord.VoiceClient | None:
        if not ctx.guild:
            await ctx.send("Music only works inside a server.")
            return None
        if not getattr(ctx.author, "voice", None) or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None
        if not self._ffmpeg_ready():
            await ctx.send("FFmpeg is unavailable. Deploy with the repository Dockerfile.")
            return None
        target = ctx.author.voice.channel
        voice = ctx.guild.voice_client
        try:
            if voice is None:
                voice = await target.connect(reconnect=True, self_deaf=True)
            elif voice.channel != target:
                await voice.move_to(target)
            return voice
        except discord.Forbidden:
            await ctx.send("I need Connect and Speak permissions in that voice channel.")
        except Exception as exc:
            await ctx.send(f"I could not join the voice channel: {str(exc)[:250]}")
        return None

    async def _can_control(self, ctx: commands.Context) -> bool:
        voice = ctx.guild.voice_client if ctx.guild else None
        author_voice = getattr(ctx.author, "voice", None)
        if not voice:
            await ctx.send("I am not connected to voice.")
            return False
        if not author_voice or author_voice.channel != voice.channel:
            await ctx.send(f"Join **{voice.channel.name}** to control the player.")
            return False
        return True

    async def _announce(self, track: Track) -> None:
        channel = self.bot.get_channel(track.channel_id)
        if not channel:
            return
        duration = "Live/unknown" if not track.duration else f"{track.duration // 60}:{track.duration % 60:02d}"
        embed = discord.Embed(title="🎵 Now Playing", description=f"**{track.title}**", color=discord.Color.green())
        if track.webpage_url.startswith(("http://", "https://")):
            embed.url = track.webpage_url
        embed.add_field(name="Requester", value=track.requester)
        embed.add_field(name="Duration", value=duration)
        embed.add_field(name="Source", value=track.source)
        await channel.send(embed=embed)

    async def _play_next(self, guild_id: int) -> None:
        async with self.locks[guild_id]:
            guild = self.bot.get_guild(guild_id)
            voice = guild.voice_client if guild else None
            if not voice or voice.is_playing() or voice.is_paused():
                return
            if not self.queues[guild_id]:
                self.current.pop(guild_id, None)
                return
            track = self.queues[guild_id].popleft()
            self.current[guild_id] = track
            try:
                source = await self._fresh_source(guild_id, track)
            except Exception as exc:
                channel = self.bot.get_channel(track.channel_id)
                if channel:
                    await channel.send(f"Could not play **{track.title}**: {str(exc)[:300]}")
                self.current.pop(guild_id, None)
                asyncio.create_task(self._play_next(guild_id))
                return

            def after(error):
                asyncio.run_coroutine_threadsafe(self._finished(guild_id, track, error), self.bot.loop)

            voice.play(source, after=after)
        await self._announce(track)

    async def _finished(self, guild_id: int, track: Track, error) -> None:
        if error:
            logger.warning("Playback error in guild %s: %s", guild_id, error)
        async with self.locks[guild_id]:
            if self.current.get(guild_id) is track and guild_id in self.looping:
                self.queues[guild_id].appendleft(track)
            if self.current.get(guild_id) is track:
                self.current.pop(guild_id, None)
        await self._play_next(guild_id)

    @commands.command(name="join")
    @commands.guild_only()
    async def join(self, ctx: commands.Context):
        voice = await self._voice(ctx)
        if voice:
            await ctx.send(f"Joined **{voice.channel.name}**.")

    @commands.command(name="play", aliases=["p"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str = ""):
        if not query.strip():
            await ctx.send("Use `!play <song name or link>`.")
            return
        voice = await self._voice(ctx)
        if not voice:
            return
        status = await ctx.send("🔎 Finding that track…")
        try:
            track = await self._find_track(ctx, query.strip())
        except Exception as exc:
            await status.edit(content=f"Could not load that track: {str(exc)[:450]}")
            return
        self.queues[ctx.guild.id].append(track)
        await status.edit(content=f"✅ Queued **{track.title}**.")
        await self._play_next(ctx.guild.id)

    @commands.command(name="pause")
    @commands.guild_only()
    async def pause(self, ctx: commands.Context):
        if await self._can_control(ctx) and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.pause()
            await ctx.send("⏸️ Paused.")

    @commands.command(name="resume")
    @commands.guild_only()
    async def resume(self, ctx: commands.Context):
        if await self._can_control(ctx) and ctx.guild.voice_client.is_paused():
            ctx.guild.voice_client.resume()
            await ctx.send("▶️ Resumed.")

    @commands.command(name="skip", aliases=["next"])
    @commands.guild_only()
    async def skip(self, ctx: commands.Context):
        if await self._can_control(ctx) and (ctx.guild.voice_client.is_playing() or ctx.guild.voice_client.is_paused()):
            ctx.guild.voice_client.stop()
            await ctx.send("⏭️ Skipped.")

    @commands.command(name="stop")
    @commands.guild_only()
    async def stop(self, ctx: commands.Context):
        if not await self._can_control(ctx):
            return
        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.looping.discard(guild_id)
        if ctx.guild.voice_client.is_playing() or ctx.guild.voice_client.is_paused():
            ctx.guild.voice_client.stop()
        await ctx.send("⏹️ Stopped and cleared the queue.")

    @commands.command(name="leave", aliases=["disconnect"])
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        if not await self._can_control(ctx):
            return
        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.looping.discard(guild_id)
        self.current.pop(guild_id, None)
        await ctx.guild.voice_client.disconnect(force=True)
        await ctx.send("👋 Disconnected.")

    @commands.command(name="queue", aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx: commands.Context):
        current = self.current.get(ctx.guild.id)
        upcoming = list(self.queues[ctx.guild.id])
        if not current and not upcoming:
            await ctx.send("The queue is empty.")
            return
        lines = [f"**Now:** {current.title}"] if current else []
        lines.extend(f"`{i}.` {track.title} — {track.requester}" for i, track in enumerate(upcoming[:15], 1))
        await ctx.send("🎶 **Music Queue**\n" + "\n".join(lines))

    @commands.command(name="nowplaying", aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx: commands.Context):
        track = self.current.get(ctx.guild.id)
        if track:
            await self._announce(track)
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="volume", aliases=["vol"])
    @commands.guild_only()
    async def volume(self, ctx: commands.Context, percent: int = -1):
        if percent < 0:
            await ctx.send(f"Volume: **{round(self.volumes[ctx.guild.id] * 100)}%**")
            return
        if not await self._can_control(ctx):
            return
        percent = max(0, min(percent, 150))
        self.volumes[ctx.guild.id] = percent / 100
        source = ctx.guild.voice_client.source
        if isinstance(source, discord.PCMVolumeTransformer):
            source.volume = self.volumes[ctx.guild.id]
        await ctx.send(f"🔊 Volume set to **{percent}%**.")

    @commands.command(name="loop")
    @commands.guild_only()
    async def loop(self, ctx: commands.Context):
        if not await self._can_control(ctx):
            return
        guild_id = ctx.guild.id
        if guild_id in self.looping:
            self.looping.remove(guild_id)
            state = "OFF"
        else:
            self.looping.add(guild_id)
            state = "ON"
        await ctx.send(f"🔁 Loop is **{state}**.")

    @commands.command(name="shuffle")
    @commands.guild_only()
    async def shuffle(self, ctx: commands.Context):
        if not await self._can_control(ctx):
            return
        items = list(self.queues[ctx.guild.id])
        random.shuffle(items)
        self.queues[ctx.guild.id] = deque(items)
        await ctx.send("🔀 Queue shuffled.")

    @commands.command(name="clearqueue", aliases=["clearq"])
    @commands.guild_only()
    async def clearqueue(self, ctx: commands.Context):
        if await self._can_control(ctx):
            self.queues[ctx.guild.id].clear()
            await ctx.send("🧹 Queue cleared.")

    @commands.command(name="musichelp")
    async def musichelp(self, ctx: commands.Context):
        await ctx.send(
            "**🎵 Music Commands**\n"
            "`!join` · `!play <song/link>` · `!pause` · `!resume` · `!skip`\n"
            "`!stop` · `!leave` · `!queue` · `!nowplaying` · `!volume 50`\n"
            "`!loop` · `!shuffle` · `!clearqueue`\n\n"
            f"FFmpeg: **{'Ready' if self._ffmpeg_ready() else 'Missing'}** · "
            f"Cookies: **{'Configured' if os.path.isfile(self.cookies_file) else 'Not configured'}**"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
