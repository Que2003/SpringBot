import os
import json
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

        self.state_file = "voice_settings.json"
        self.voice_settings = self.load_state()

        self.voice_name = os.getenv("TTS_VOICE", "en-US-GuyNeural")
        self.rate = os.getenv("TTS_RATE", "+0%")
        self.ffmpeg_path = shutil.which("ffmpeg") or os.getenv("FFMPEG_PATH") or "ffmpeg"

        self.listen_state = {}

    def load_state(self):
        if not os.path.exists(self.state_file):
            return {}

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.voice_settings, f, indent=2)

    def get_guild_state(self, guild_id: int):
        key = str(guild_id)
        if key not in self.voice_settings:
            self.voice_settings[key] = {
                "stay_connected": False,
                "channel_id": 0
            }
        return self.voice_settings[key]

    def set_stay_state(self, guild_id: int, enabled: bool, channel_id: int = 0):
        state = self.get_guild_state(guild_id)
        state["stay_connected"] = enabled
        state["channel_id"] = channel_id
        self.save_state()

    async def connect_recv(self, channel: discord.VoiceChannel):
        return await channel.connect(cls=voice_recv.VoiceRecvClient)

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None

        voice_client = ctx.voice_client

        if voice_client is None:
            try:
                vc = await self.connect_recv(ctx.author.voice.channel)
                self.set_stay_state(ctx.guild.id, True, ctx.author.voice.channel.id)
                return vc
            except Exception as e:
                await ctx.send(f"Could not join voice channel: {e}")
                return None

        if voice_client.channel != ctx.author.voice.channel:
            try:
                await voice_client.move_to(ctx.author.voice.channel)
                self.set_stay_state(ctx.guild.id, True, ctx.author.voice.channel.id)
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

    async def try_reconnect(self, guild: discord.Guild):
        state = self.get_guild_state(guild.id)

        if not state.get("stay_connected", False):
            return

        channel_id = int(state.get("channel_id", 0) or 0)
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            return

        if guild.voice_client is not None:
            return

        await asyncio.sleep(3)

        try:
            await self.connect_recv(channel)
            print(f"Reconnected to VC in guild {guild.id} channel {channel.id}")
        except Exception as e:
            print(f"Failed to reconnect VC in guild {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            state = self.get_guild_state(guild.id)
            if state.get("stay_connected", False):
                self.bot.loop.create_task(self.try_reconnect(guild))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if self.bot.user is None:
            return

        if member.id != self.bot.user.id:
            return

        guild = member.guild
        state = self.get_guild_state(guild.id)

        if after.channel is not None:
            state["channel_id"] = after.channel.id
            self.save_state()
            return

        if before.channel is not None and after.channel is None:
            if state.get("stay_connected", False):
                self.bot.loop.create_task(self.try_reconnect(guild))

    @commands.command(help="Join your voice channel and stay there until !leavevc is used.")
    async def joinvc(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client:
            self.set_stay_state(ctx.guild.id, True, voice_client.channel.id)
            await ctx.send(f"Joined **{voice_client.channel.name}** and I will stay until you tell me to leave.")

    @commands.command(help="Leave the voice channel and stop auto staying.")
    async def leavevc(self, ctx):
        guild_id = ctx.guild.id

        if ctx.voice_client is None:
            self.set_stay_state(guild_id, False, 0)
            await ctx.send("I am not in a voice channel.")
            return

        try:
            if hasattr(ctx.voice_client, "is_listening") and ctx.voice_client.is_listening():
                ctx.voice_client.stop_listening()
        except Exception:
            pass

        self.listen_state.pop(guild_id, None)
        self.set_stay_state(guild_id, False, 0)

        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel and I will not auto-rejoin.")

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
        self.set_stay_state(ctx.guild.id, True, voice_client.channel.id)

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

    @commands.command(help="Show VC listening and stay-connected status.")
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

        stay_state = self.get_guild_state(guild_id)
        voice_client = ctx.voice_client
        receive_capable = isinstance(voice_client, voice_recv.VoiceRecvClient)

        users = list(state.get("users", set()))
        users_text = ", ".join(users[:5]) if users else "No users detected yet."

        await ctx.send(
            f"Receive-capable VC client: **{receive_capable}**\n"
            f"Stay connected: **{stay_state.get('stay_connected', False)}**\n"
            f"Saved channel ID: **{stay_state.get('channel_id', 0)}**\n"
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
            "!joinvc - join your voice channel and stay there\n"
            "!leavevc - leave the voice channel\n"
            "!sayvc <message> - speak in VC\n"
            "!startlisten - start listening and recording VC audio\n"
            "!stoplisten - stop listening\n"
            "!vcstatus - show voice status\n"
            "!vchelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(VoiceChat(bot))