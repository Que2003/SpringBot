import os
import shutil
import asyncio
from collections import defaultdict, deque

import discord
from discord.ext import commands
import yt_dlp


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = defaultdict(deque)
        self.now_playing = {}

        self.cookies_file = os.getenv("YTDLP_COOKIES_FILE", "cookies.txt")
        self.ffmpeg_path = shutil.which("ffmpeg") or os.getenv("FFMPEG_PATH") or "ffmpeg"

        self.ytdl_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "scsearch1",
            "extract_flat": False,
            "cookiefile": self.cookies_file if os.path.exists(self.cookies_file) else None,
        }

        self.radio_stations = {
            "lofi": {
                "name": "Lofi Girl",
                "url": "https://play.streamafrica.net/lofiradio"
            },
            "jazz": {
                "name": "Jazz Radio",
                "url": "http://jazzradio.ice.infomaniak.ch/jazzradio-high.mp3"
            },
            "hiphop": {
                "name": "Hip Hop Radio",
                "url": "http://stream.radiotunes.com/hiphop"
            },
            "news": {
                "name": "BBC World Service",
                "url": "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"
            }
        }

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None

        if ctx.voice_client is None:
            try:
                return await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"Could not join voice channel: {e}")
                return None

        if ctx.voice_client.channel != ctx.author.voice.channel:
            try:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
            except Exception as e:
                await ctx.send(f"Could not move to your voice channel: {e}")
                return None

        return ctx.voice_client

    async def extract_info(self, query):
        loop = asyncio.get_running_loop()

        def run():
            with yt_dlp.YoutubeDL(self.ytdl_options) as ydl:
                return ydl.extract_info(query, download=False)

        return await loop.run_in_executor(None, run)

    async def create_song(self, query):
        if not shutil.which("ffmpeg") and not os.path.exists(self.ffmpeg_path):
            raise RuntimeError("FFmpeg is not installed.")

        data = await self.extract_info(query)

        if "entries" in data:
            entries = data.get("entries") or []
            if not entries:
                raise RuntimeError("No results found.")
            data = entries[0]

        if not data:
            raise RuntimeError("No results found.")

        title = data.get("title", "Unknown Title")
        url = data.get("webpage_url") or query
        stream_url = data.get("url")
        source_name = data.get("extractor_key") or data.get("extractor") or "Unknown"

        if not stream_url:
            raise RuntimeError("Could not get audio stream.")

        audio_source = discord.FFmpegPCMAudio(
            stream_url,
            executable=self.ffmpeg_path,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn",
        )

        return {
            "title": title,
            "url": url,
            "source_name": source_name,
            "audio_source": audio_source,
            "query": query,
        }

    async def start_next_song(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None or guild.voice_client is None:
            return

        if not self.queues[guild_id]:
            self.now_playing[guild_id] = None
            return

        next_song = self.queues[guild_id].popleft()
        self.now_playing[guild_id] = next_song

        def after_playing(error):
            if error:
                print(f"Playback error: {error}")

            future = asyncio.run_coroutine_threadsafe(
                self.start_next_song(guild_id),
                self.bot.loop
            )
            try:
                future.result()
            except Exception as e:
                print(f"Queue error: {e}")

        guild.voice_client.play(next_song["audio_source"], after=after_playing)

        text_channel = next_song["text_channel"]
        await text_channel.send(
            f"Now playing: **{next_song['title']}**\n"
            f"Source: **{next_song['source_name']}**"
        )

    @commands.command(help="Join your voice channel.")
    async def join(self, ctx):
        voice = await self.ensure_voice(ctx)
        if voice:
            await ctx.send(f"Joined **{voice.channel.name}**")

    @commands.command(help="Leave voice channel and clear queue.")
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None

        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected and cleared the queue.")

    @commands.command(help="Play a song from a SoundCloud link, Bandcamp link, or search.")
    async def play(self, ctx, *, query):
        voice = await self.ensure_voice(ctx)
        if voice is None:
            return

        try:
            song = await self.create_song(query)
            song["requester"] = ctx.author
            song["text_channel"] = ctx.channel
        except Exception as e:
            error_text = str(e)

            if "Sign in to confirm you're not a bot" in error_text:
                await ctx.send(
                    "YouTube blocked that request. Use a SoundCloud or Bandcamp link, "
                    "or add a valid cookies.txt file."
                )
            elif "FFmpeg is not installed" in error_text:
                await ctx.send(
                    "FFmpeg is missing in Railway. The bot cannot play audio until FFmpeg is installed."
                )
            else:
                await ctx.send(f"Could not load that track: {error_text}")
            return

        guild_id = ctx.guild.id

        if voice.is_playing() or voice.is_paused():
            self.queues[guild_id].append(song)
            await ctx.send(
                f"Queued: **{song['title']}**\n"
                f"Source: **{song['source_name']}**"
            )
            return

        self.now_playing[guild_id] = song

        def after_playing(error):
            if error:
                print(f"Playback error: {error}")

            future = asyncio.run_coroutine_threadsafe(
                self.start_next_song(guild_id),
                self.bot.loop
            )
            try:
                future.result()
            except Exception as e:
                print(f"Queue error: {e}")

        voice.play(song["audio_source"], after=after_playing)

        await ctx.send(
            f"Now playing: **{song['title']}**\n"
            f"Source: **{song['source_name']}**"
        )

    @commands.command(help="Play a live radio station. Example: !radio lofi")
    async def radio(self, ctx, station: str):
        voice = await self.ensure_voice(ctx)
        if voice is None:
            return

        key = station.lower().strip()
        if key not in self.radio_stations:
            await ctx.send("Unknown station. Use `!stations`.")
            return

        station_info = self.radio_stations[key]

        if voice.is_playing() or voice.is_paused():
            voice.stop()

        try:
            source = discord.FFmpegPCMAudio(
                station_info["url"],
                executable=self.ffmpeg_path,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            )
        except Exception as e:
            await ctx.send(f"Could not start radio stream: {e}")
            return

        voice.play(source)
        self.now_playing[ctx.guild.id] = {
            "title": station_info["name"],
            "source_name": "Live Radio",
        }

        await ctx.send(f"Now streaming live radio: **{station_info['name']}**")

    @commands.command(help="Show available live radio stations.")
    async def stations(self, ctx):
        await ctx.send(
            "**Live Radio Stations**\n"
            "!radio lofi\n"
            "!radio jazz\n"
            "!radio hiphop\n"
            "!radio news"
        )

    @commands.command(help="Stop the live radio stream or music.")
    async def stopradio(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            self.now_playing[ctx.guild.id] = None
            await ctx.send("Stopped the radio/music stream.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(help="Pause current music.")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(help="Resume paused music.")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed.")
        else:
            await ctx.send("Nothing is paused.")

    @commands.command(help="Skip current track.")
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(help="Stop music and clear queue.")
    async def stop(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        await ctx.send("Stopped music and cleared queue.")

    @commands.command(help="Show current queue.")
    async def queue(self, ctx):
        guild_queue = self.queues.get(ctx.guild.id, deque())

        if not guild_queue:
            await ctx.send("The queue is empty.")
            return

        lines = []
        for i, song in enumerate(list(guild_queue)[:10], start=1):
            lines.append(f"{i}. {song['title']}")

        await ctx.send("**Queue:**\n" + "\n".join(lines))

    @commands.command(help="Show current song.")
    async def nowplaying(self, ctx):
        song = self.now_playing.get(ctx.guild.id)

        if not song:
            await ctx.send("Nothing is playing.")
            return

        await ctx.send(
            f"Now playing: **{song['title']}**\n"
            f"Source: **{song['source_name']}**"
        )

    @commands.command(help="Show music and radio bot status.")
    async def musichelp(self, ctx):
        ffmpeg_ok = bool(shutil.which("ffmpeg") or os.path.exists(self.ffmpeg_path))
        cookies_ok = os.path.exists(self.cookies_file)

        await ctx.send(
            "**Music and Radio Commands**\n"
            "!join\n"
            "!play <song or link>\n"
            "!radio <station>\n"
            "!stations\n"
            "!pause\n"
            "!resume\n"
            "!skip\n"
            "!stop\n"
            "!stopradio\n"
            "!queue\n"
            "!nowplaying\n"
            "!leave\n\n"
            f"FFmpeg detected: **{ffmpeg_ok}**\n"
            f"Cookies file found: **{cookies_ok}**\n"
            f"FFmpeg path: **{self.ffmpeg_path}**"
        )


async def setup(bot):
    await bot.add_cog(Music(bot))