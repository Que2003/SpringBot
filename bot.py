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
        self.loop_mode = defaultdict(bool)

        self.cookies_file = os.getenv("YTDLP_COOKIES_FILE", "cookies.txt")

        self.ytdl_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "auto",
            "extract_flat": False,
            "source_address": "0.0.0.0",
        }

        if os.path.exists(self.cookies_file):
            self.ytdl_options["cookiefile"] = self.cookies_file

        detected_ffmpeg = (
            os.getenv("FFMPEG_PATH")
            or shutil.which("ffmpeg")
            or "/usr/bin/ffmpeg"
            or "/nix/var/nix/profiles/default/bin/ffmpeg"
        )

        self.ffmpeg_executable = detected_ffmpeg

        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
            "executable": self.ffmpeg_executable,
        }

    def is_direct_link(self, query: str) -> bool:
        query = query.lower().strip()
        return query.startswith("http://") or query.startswith("https://")

    def preferred_search_query(self, query: str) -> str:
        if self.is_direct_link(query):
            return query
        return f"scsearch1:{query}"

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None

        voice_client = ctx.voice_client

        if voice_client is None:
            try:
                return await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"Could not join voice channel: {e}")
                return None

        if voice_client.channel != ctx.author.voice.channel:
            try:
                await voice_client.move_to(ctx.author.voice.channel)
            except Exception as e:
                await ctx.send(f"Could not move to your voice channel: {e}")
                return None

        return voice_client

    async def extract_info(self, query):
        loop = asyncio.get_running_loop()

        def run():
            with yt_dlp.YoutubeDL(self.ytdl_options) as ydl:
                return ydl.extract_info(query, download=False)

        return await loop.run_in_executor(None, run)

    async def build_source(self, query):
        if not shutil.which("ffmpeg") and not os.path.exists(self.ffmpeg_executable):
            raise RuntimeError(
                "FFmpeg is not installed in Railway. Add nixpacks.toml in the repo root "
                "or set Railway variable NIXPACKS_PKGS=ffmpeg, then redeploy."
            )

        search_target = self.preferred_search_query(query)
        data = await self.extract_info(search_target)

        if "entries" in data:
            entries = data.get("entries") or []
            if not entries:
                raise RuntimeError("No results found.")
            data = entries[0]

        if not data:
            raise RuntimeError("No results found.")

        title = data.get("title", "Unknown Title")
        webpage_url = data.get("webpage_url") or query
        stream_url = data.get("url")
        extractor = data.get("extractor_key") or data.get("extractor") or "Unknown"

        if not stream_url:
            raise RuntimeError("Could not get an audio stream.")

        source = discord.FFmpegPCMAudio(stream_url, **self.ffmpeg_options)

        return {
            "title": title,
            "url": webpage_url,
            "source": source,
            "extractor": extractor,
            "original_query": query,
        }

    async def play_next(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        voice_client = guild.voice_client
        if voice_client is None:
            return

        current_song = self.now_playing.get(guild_id)
        if self.loop_mode[guild_id] and current_song is not None:
            try:
                looped_song = await self.build_source(current_song["original_query"])
                looped_song["requester"] = current_song.get("requester")
                looped_song["text_channel"] = current_song["text_channel"]
                self.now_playing[guild_id] = looped_song

                def after_playing(error):
                    if error:
                        print(f"Music playback error: {error}")

                    future = asyncio.run_coroutine_threadsafe(
                        self.play_next(guild_id),
                        self.bot.loop
                    )
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Queue advance error: {e}")

                voice_client.play(looped_song["source"], after=after_playing)
                await looped_song["text_channel"].send(f"Looping: **{looped_song['title']}**")
                return
            except Exception as e:
                await current_song["text_channel"].send(f"Loop failed: {e}")

        if not self.queues[guild_id]:
            self.now_playing[guild_id] = None
            return

        next_song = self.queues[guild_id].popleft()
        self.now_playing[guild_id] = next_song

        def after_playing(error):
            if error:
                print(f"Music playback error: {error}")

            future = asyncio.run_coroutine_threadsafe(
                self.play_next(guild_id),
                self.bot.loop
            )
            try:
                future.result()
            except Exception as e:
                print(f"Queue advance error: {e}")

        voice_client.play(next_song["source"], after=after_playing)

        channel = next_song["text_channel"]
        await channel.send(
            f"Now playing: **{next_song['title']}**\n"
            f"Source: **{next_song['extractor']}**"
        )

    @commands.command()
    async def join(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client:
            await ctx.send(f"Joined **{voice_client.channel.name}**")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None
        self.loop_mode[guild_id] = False

        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected and cleared the music queue.")

    @commands.command()
    async def play(self, ctx, *, query):
        voice_client = await self.ensure_voice(ctx)
        if voice_client is None:
            return

        try:
            song = await self.build_source(query)
            song["requester"] = ctx.author
            song["text_channel"] = ctx.channel
        except Exception as e:
            await ctx.send(f"Could not load that track: {e}")
            return

        guild_id = ctx.guild.id

        if voice_client.is_playing() or voice_client.is_paused():
            self.queues[guild_id].append(song)
            await ctx.send(
                f"Queued: **{song['title']}**\n"
                f"Source: **{song['extractor']}**"
            )
            return

        self.now_playing[guild_id] = song

        def after_playing(error):
            if error:
                print(f"Music playback error: {error}")

            future = asyncio.run_coroutine_threadsafe(
                self.play_next(guild_id),
                self.bot.loop
            )
            try:
                future.result()
            except Exception as e:
                print(f"Queue advance error: {e}")

        voice_client.play(song["source"], after=after_playing)
        await ctx.send(
            f"Now playing: **{song['title']}**\n"
            f"Source: **{song['extractor']}**"
        )

    @commands.command()
    async def musichelp(self, ctx):
        ffmpeg_found = shutil.which("ffmpeg") or os.path.exists(self.ffmpeg_executable)
        await ctx.send(
            "**Music Commands**\n"
            "!join\n!play <link or song>\n!pause\n!resume\n!skip\n!stop\n!queue\n!leave\n"
            f"FFmpeg detected: **{bool(ffmpeg_found)}**\n"
            f"FFmpeg path: **{self.ffmpeg_executable}**"
        )

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused the music.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed the music.")
        else:
            await ctx.send("Nothing is paused right now.")

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None
        self.loop_mode[guild_id] = False

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        await ctx.send("Stopped playback and cleared the queue.")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            self.loop_mode[ctx.guild.id] = False
            ctx.voice_client.stop()
            await ctx.send("Skipped the current track.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command()
    async def nowplaying(self, ctx):
        song = self.now_playing.get(ctx.guild.id)
        if not song:
            await ctx.send("Nothing is playing right now.")
            return
        await ctx.send(f"Now playing: **{song['title']}**")

    @commands.command()
    async def queue(self, ctx):
        guild_queue = self.queues.get(ctx.guild.id, deque())
        if not guild_queue:
            await ctx.send("The queue is empty.")
            return
        lines = [f"{i}. {song['title']}" for i, song in enumerate(list(guild_queue)[:10], start=1)]
        await ctx.send("**Queue:**\n" + "\n".join(lines))


async def setup(bot):
    await bot.add_cog(Music(bot))
