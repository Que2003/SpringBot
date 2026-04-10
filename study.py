import os
import asyncio
from collections import deque
from typing import Optional

import discord
from discord.ext import commands, tasks
import imageio_ffmpeg

DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.5"))
AUTO_DISCONNECT_MINUTES = int(os.getenv("AUTO_DISCONNECT_MINUTES", "10"))

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

RADIO_PRESETS = {
    "lofi": "https://stream.zeno.fm/fyn8eh3h5f8uv",
    "jazz": "https://icecast.omroep.nl/radio6-jazz-bb-mp3",
    "classical": "https://stream.live.vc.bbcmedia.co.uk/bbc_radio_three",
    "news": "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
}

class QueueItem:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url

class GuildAudioState:
    def __init__(self):
        self.voice_client: Optional[discord.VoiceClient] = None
        self.queue = deque()
        self.current: Optional[QueueItem] = None
        self.text_channel_id: Optional[int] = None
        self.volume = DEFAULT_VOLUME
        self.empty_since: Optional[float] = None
        self.lock = asyncio.Lock()

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildAudioState] = {}
        self.disconnect_watcher.start()

    def cog_unload(self):
        self.disconnect_watcher.cancel()

    def get_state(self, guild_id: int) -> GuildAudioState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildAudioState()
        return self.states[guild_id]

    async def ensure_voice(self, ctx: commands.Context) -> GuildAudioState:
        if ctx.guild is None:
            raise RuntimeError("This command only works in a server.")
        state = self.get_state(ctx.guild.id)
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise RuntimeError("Join a voice channel first.")
        voice_channel = ctx.author.voice.channel
        if state.voice_client and state.voice_client.is_connected():
            if state.voice_client.channel != voice_channel:
                await state.voice_client.move_to(voice_channel)
        else:
            state.voice_client = await voice_channel.connect(timeout=20, reconnect=True)
        state.text_channel_id = ctx.channel.id
        state.empty_since = None
        return state

    async def start_next(self, guild: discord.Guild):
        state = self.get_state(guild.id)
        async with state.lock:
            vc = state.voice_client
            if not vc or not vc.is_connected():
                return
            if not state.queue:
                state.current = None
                return

            item = state.queue.popleft()
            state.current = item

            def after_playing(error):
                if error:
                    print(f"PLAYER ERROR: {error}")
                fut = asyncio.run_coroutine_threadsafe(self.start_next(guild), self.bot.loop)
                try:
                    fut.result()
                except Exception as exc:
                    print(f"QUEUE ERROR: {exc}")

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(item.url, executable=FFMPEG_EXE, **FFMPEG_OPTIONS),
                volume=state.volume,
            )
            vc.play(source, after=after_playing)

            channel = guild.get_channel(state.text_channel_id) if state.text_channel_id else None
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"▶️ Now streaming: **{item.title}**")

    @commands.command(name="join")
    async def join_command(self, ctx: commands.Context):
        state = await self.ensure_voice(ctx)
        await ctx.send(f"Joined **{state.voice_client.channel}**")

    @commands.command(name="radio")
    async def radio_command(self, ctx: commands.Context, preset: str):
        key = preset.lower()
        if key not in RADIO_PRESETS:
            await ctx.send("Available presets: " + ", ".join(RADIO_PRESETS.keys()))
            return
        state = await self.ensure_voice(ctx)
        state.queue.clear()
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.voice_client.stop()
        state.queue.append(QueueItem(f"{key.title()} Radio", RADIO_PRESETS[key]))
        await self.start_next(ctx.guild)

    @commands.command(name="stream")
    async def stream_command(self, ctx: commands.Context, url: str):
        state = await self.ensure_voice(ctx)
        state.queue.clear()
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.voice_client.stop()
        state.queue.append(QueueItem(url, url))
        await self.start_next(ctx.guild)

    @commands.command(name="queueadd")
    async def queueadd_command(self, ctx: commands.Context, url: str):
        state = await self.ensure_voice(ctx)
        item = QueueItem(url, url)
        state.queue.append(item)
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            await ctx.send(f"Queued: **{item.title}**")
        else:
            await self.start_next(ctx.guild)

    @commands.command(name="queue")
    async def queue_command(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        lines = []
        if state.current:
            lines.append(f"Now: **{state.current.title}**")
        if state.queue:
            for i, item in enumerate(list(state.queue)[:10], start=1):
                lines.append(f"{i}. {item.title}")
        if not lines:
            lines.append("Queue is empty.")
        await ctx.send("\n".join(lines))

    @commands.command(name="skip")
    async def skip_command(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="stop")
    async def stop_command(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        if state.voice_client and (state.voice_client.is_playing() or state.voice_client.is_paused()):
            state.voice_client.stop()
        await ctx.send("Stopped streaming and cleared the queue.")

    @commands.command(name="leave")
    async def leave_command(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.disconnect()
            state.voice_client = None
            await ctx.send("Disconnected.")
        else:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(name="volume")
    async def volume_command(self, ctx: commands.Context, value: int):
        state = self.get_state(ctx.guild.id)
        state.volume = max(0, min(value, 100)) / 100
        if state.voice_client and state.voice_client.source:
            state.voice_client.source.volume = state.volume
        await ctx.send(f"Volume set to `{value}%`")

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying_command(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        await ctx.send(f"🎵 Now streaming: **{state.current.title}**" if state.current else "Nothing is streaming.")

    @tasks.loop(minutes=1)
    async def disconnect_watcher(self):
        now = asyncio.get_running_loop().time()
        for state in list(self.states.values()):
            vc = state.voice_client
            if not vc or not vc.is_connected() or not vc.channel:
                continue
            non_bot_members = [m for m in vc.channel.members if not m.bot]
            if non_bot_members or vc.is_playing() or vc.is_paused():
                state.empty_since = None
                continue
            if state.empty_since is None:
                state.empty_since = now
                continue
            if now - state.empty_since >= AUTO_DISCONNECT_MINUTES * 60:
                await vc.disconnect()
                state.voice_client = None
                state.current = None
                state.queue.clear()
                state.empty_since = None

    @disconnect_watcher.before_loop
    async def before_disconnect(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
