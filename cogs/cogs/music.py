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

        self.ytdl_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch",
            "extract_flat": False,
        }

        self.ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

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
        data = await self.extract_info(query)

        if "entries" in data:
            data = data["entries"][0]

        if not data:
            raise RuntimeError("No results found.")

        title = data.get("title", "Unknown Title")
        webpage_url = data.get("webpage_url") or query
        stream_url = data.get("url")

        if not stream_url:
            raise RuntimeError("Could not get an audio stream.")

        source = discord.FFmpegPCMAudio(stream_url, **self.ffmpeg_options)

        return {
            "title": title,
            "url": webpage_url,
            "source": source,
        }

    async def play_next(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        voice_client = guild.voice_client
        if voice_client is None:
            return

        if not self.queues[guild_id]:
            self.now_playing[guild_id] = None
            return

        next_song = self.queues[guild_id].popleft()
        self.now_playing[guild_id] = next_song

        def after_playing(error):
            if error:
                print(f"Music playback error: {error}")

            fut = asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Queue advance error: {e}")

        voice_client.play(next_song["source"], after=after_playing)

        channel = next_song["text_channel"]
        await channel.send(f"Now playing: **{next_song['title']}**")

    @commands.command(help="Joins your current voice channel.")
    async def join(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client:
            await ctx.send(f"Joined **{voice_client.channel.name}**")

    @commands.command(help="Leaves the voice channel and clears the queue.")
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None

        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected and cleared the music queue.")

    @commands.command(help="Plays a song from a YouTube link or search term.")
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
            await ctx.send(f"Queued: **{song['title']}**")
            return

        self.now_playing[guild_id] = song

        def after_playing(error):
            if error:
                print(f"Music playback error: {error}")

            fut = asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Queue advance error: {e}")

        voice_client.play(song["source"], after=after_playing)
        await ctx.send(f"Now playing: **{song['title']}**")

    @commands.command(help="Pauses the current track.")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused the music.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command(help="Resumes the paused track.")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed the music.")
        else:
            await ctx.send("Nothing is paused right now.")

    @commands.command(help="Stops playback and clears the queue.")
    async def stop(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        guild_id = ctx.guild.id
        self.queues[guild_id].clear()
        self.now_playing[guild_id] = None

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        await ctx.send("Stopped playback and cleared the queue.")

    @commands.command(help="Skips the current track.")
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send("Skipped the current track.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command(help="Shows the current track.")
    async def nowplaying(self, ctx):
        song = self.now_playing.get(ctx.guild.id)

        if not song:
            await ctx.send("Nothing is playing right now.")
            return

        await ctx.send(f"Now playing: **{song['title']}**")

    @commands.command(help="Shows the queued tracks.")
    async def queue(self, ctx):
        guild_queue = self.queues.get(ctx.guild.id, deque())

        if not guild_queue:
            await ctx.send("The queue is empty.")
            return

        lines = []
        for index, song in enumerate(list(guild_queue)[:10], start=1):
            lines.append(f"{index}. {song['title']}")

        await ctx.send("**Queue:**\n" + "\n".join(lines))

    @commands.command(help="Removes a song from the queue by number.")
    async def remove(self, ctx, index: int):
        guild_id = ctx.guild.id
        guild_queue = self.queues.get(guild_id)

        if not guild_queue:
            await ctx.send("The queue is empty.")
            return

        if index < 1 or index > len(guild_queue):
            await ctx.send("That queue number does not exist.")
            return

        queue_list = list(guild_queue)
        removed = queue_list.pop(index - 1)
        self.queues[guild_id] = deque(queue_list)

        await ctx.send(f"Removed: **{removed['title']}**")

    @commands.command(help="Shows all music commands.")
    async def musichelp(self, ctx):
        await ctx.send(
            "**Music Commands**\n"
            "!join - Join your voice channel\n"
            "!play <song name or YouTube link> - Play or queue a song\n"
            "!pause - Pause music\n"
            "!resume - Resume music\n"
            "!skip - Skip current song\n"
            "!stop - Stop music and clear queue\n"
            "!queue - Show queued songs\n"
            "!remove <number> - Remove a queued song\n"
            "!nowplaying - Show current song\n"
            "!leave - Leave voice channel"
        )

async def setup(bot):
    await bot.add_cog(Music(bot))
