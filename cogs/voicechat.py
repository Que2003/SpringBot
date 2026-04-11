import os
import uuid
import shutil
import asyncio
from pathlib import Path

import discord
from discord.ext import commands, voice_recv
import edge_tts


class PacketLoggerSink(voice_recv.AudioSink):
    def __init__(self, parent_cog, guild_id: int):
        super().__init__()
        self.parent_cog = parent_cog
        self.guild_id = guild_id

    def wants_opus(self) -> bool:
        return False

    def write(self, user, data):
        if user is None:
            return

        state = self.parent_cog.listen_state.setdefault(
            self.guild_id,
            {
                "listening": False,
                "packets": 0,
                "users": set(),
                "wave_file": None,
                "started_by": None,
            },
        )

        state["packets"] += 1
        state["users"].add(str(user))


class VoiceChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_dir = Path("tts_audio")
        self.temp_dir.mkdir(exist_ok=True)

        self.record_dir = Path("vc_recordings")
        self.record_dir.mkdir(exist_ok=True)

        self.voice_name = os.getenv("TTS_VOICE", "en-US-GuyNeural")
        self.rate = os.getenv("TTS_RATE", "+0%")
        self.ffmpeg_path = shutil.which("ffmpeg") or os.getenv("FFMPEG_PATH") or "ffmpeg"

        self.listen_state = {}

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None

        voice_client = ctx.voice_client

        if voice_client is None:
            try:
                return await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
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

    async def make_tts_file(self, text: str):
        file_name = self.temp_dir / f"{uuid.uuid4().hex}.mp3"
        communicator = edge_tts.Communicate(
            text=text,
            voice=self.voice_name,
            rate=self.rate
        )
        await communicator.save(str(file_name))
        return file_name

    async def cleanup_file_later(self, path: Path, delay: float = 10):
        await asyncio.sleep(delay)
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass

    def build_recording_path(self, guild_id: int):
        return self.record_dir / f"{guild_id}_{uuid.uuid4().hex}.wav"

    @commands.command(help="Join your voice channel using the voice receive client.")
    async def joinvc(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client:
            await ctx.send(f"Joined **{voice_client.channel.name}**")

    @commands.command(help="Leave the voice channel and stop listening.")
    async def leavevc(self, ctx):
        guild_id = ctx.guild.id

        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        try:
            if hasattr(ctx.voice_client, "is_listening") and ctx.voice_client.is_listening():
                ctx.voice_client.stop_listening()
        except Exception:
            pass

        self.listen_state.pop(guild_id, None)

        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel.")

    @commands.command(help="Speak a message in the voice channel.")
    async def sayvc(self, ctx, *, message: str):
        voice_client = await self.ensure_voice(ctx)
        if voice_client is None:
            return

        if len(message) > 400:
            await ctx.send("Keep the message under 400 characters.")
            return

        if voice_client.is_playing() or voice_client.is_paused():
            await ctx.send("I am already speaking. Wait a second.")
            return

        try:
            audio_file = await self.make_tts_file(message)
        except Exception as e:
            await ctx.send(f"TTS generation failed: {e}")
            return

        try:
            source = discord.FFmpegPCMAudio(
                str(audio_file),
                executable=self.ffmpeg_path
            )
        except Exception as e:
            await ctx.send(f"FFmpeg playback failed: {e}")
            return

        def after_playing(error):
            if error:
                print(f"TTS playback error: {error}")
            asyncio.run_coroutine_threadsafe(
                self.cleanup_file_later(audio_file),
                self.bot.loop
            )

        voice_client.play(source, after=after_playing)
        await ctx.send(f"Speaking in **{voice_client.channel.name}**")

    @commands.command(help="Start listening in VC and save audio to a WAV file.")
    async def startlisten(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client is None:
            return

        guild_id = ctx.guild.id

        if not isinstance(voice_client, voice_recv.VoiceRecvClient):
            await ctx.send("Voice receive is not active on this connection.")
            return

        if voice_client.is_listening():
            await ctx.send("I am already listening.")
            return

        recording_path = self.build_recording_path(guild_id)

        packet_sink = PacketLoggerSink(self, guild_id)
        wave_sink = voice_recv.WaveSink(str(recording_path))
        packet_sink.child = wave_sink

        self.listen_state[guild_id] = {
            "listening": True,
            "packets": 0,
            "users": set(),
            "wave_file": str(recording_path),
            "started_by": str(ctx.author),
        }

        def after_listen(error):
            if error:
                print(f"Voice receive error: {error}")

        voice_client.listen(packet_sink, after=after_listen)

        await ctx.send(
            f"Started listening in **{voice_client.channel.name}**.\n"
            f"Recording file: **{recording_path.name}**"
        )

    @commands.command(help="Stop listening in VC.")
    async def stoplisten(self, ctx):
        guild_id = ctx.guild.id
        voice_client = ctx.voice_client

        if voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

        if not hasattr(voice_client, "is_listening") or not voice_client.is_listening():
            await ctx.send("I am not currently listening.")
            return

        voice_client.stop_listening()

        if guild_id in self.listen_state:
            self.listen_state[guild_id]["listening"] = False

        await ctx.send("Stopped listening.")

    @commands.command(help="Show VC listening status.")
    async def vcstatus(self, ctx):
        guild_id = ctx.guild.id
        state = self.listen_state.get(
            guild_id,
            {
                "listening": False,
                "packets": 0,
                "users": set(),
                "wave_file": None,
                "started_by": None,
            },
        )

        voice_client = ctx.voice_client
        receive_capable = isinstance(voice_client, voice_recv.VoiceRecvClient)

        users = list(state.get("users", set()))
        if users:
            users_text = ", ".join(users[:5])
        else:
            users_text = "No users detected yet."

        await ctx.send(
            f"Receive-capable VC client: **{receive_capable}**\n"
            f"Listening: **{state.get('listening', False)}**\n"
            f"Packets received: **{state.get('packets', 0)}**\n"
            f"Detected speakers: **{users_text}**\n"
            f"Recording file: **{state.get('wave_file')}**\n"
            f"TTS voice: **{self.voice_name}**"
        )

    @commands.command(help="Show voice chat commands.")
    async def vchelp(self, ctx):
        await ctx.send(
            "**VC Commands**\n"
            "!joinvc - join your voice channel\n"
            "!leavevc - leave the voice channel\n"
            "!sayvc <message> - speak in VC\n"
            "!startlisten - start listening and recording VC audio\n"
            "!stoplisten - stop listening\n"
            "!vcstatus - show voice status\n"
            "!vchelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(VoiceChat(bot))