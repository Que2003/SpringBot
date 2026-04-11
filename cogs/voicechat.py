import os
import uuid
import shutil
import asyncio
from pathlib import Path

import discord
from discord.ext import commands
import edge_tts


class VoiceChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_dir = Path("tts_audio")
        self.temp_dir.mkdir(exist_ok=True)

        self.voice_name = os.getenv("TTS_VOICE", "en-US-GuyNeural")
        self.rate = os.getenv("TTS_RATE", "+0%")
        self.ffmpeg_path = shutil.which("ffmpeg") or os.getenv("FFMPEG_PATH") or "ffmpeg"

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

    @commands.command(help="Join your voice channel for talking.")
    async def joinvc(self, ctx):
        voice_client = await self.ensure_voice(ctx)
        if voice_client:
            await ctx.send(f"Joined **{voice_client.channel.name}**")

    @commands.command(help="Leave the voice channel.")
    async def leavevc(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I am not in a voice channel.")
            return

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

    @commands.command(help="Show current VC talk settings.")
    async def vcstatus(self, ctx):
        ffmpeg_ok = bool(shutil.which("ffmpeg") or os.path.exists(self.ffmpeg_path))
        await ctx.send(
            f"TTS voice: **{self.voice_name}**\n"
            f"TTS rate: **{self.rate}**\n"
            f"FFmpeg detected: **{ffmpeg_ok}**\n"
            f"FFmpeg path: **{self.ffmpeg_path}**"
        )

    @commands.command(help="Show VC talking commands.")
    async def vchelp(self, ctx):
        await ctx.send(
            "**VC Commands**\n"
            "!joinvc - join your voice channel\n"
            "!leavevc - leave the voice channel\n"
            "!sayvc <message> - speak in voice chat\n"
            "!vcstatus - show TTS/FFmpeg status\n"
            "!vchelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(VoiceChat(bot))