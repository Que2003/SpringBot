from discord.ext import commands

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Summarizes the CrowdStrike Channel File 291 incident.")
    async def crowdstrike(self, ctx):
        await ctx.send(
            "The CrowdStrike Channel File 291 incident was caused by a mismatch in expected input fields. "
            "The template expected 21 inputs, but the interpreter path supplied 20. "
            "When new content used the 21st field, it triggered an out-of-bounds read and caused Windows system crashes."
        )

    @commands.command(help="Explains the root cause of the CrowdStrike incident.")
    async def rca(self, ctx):
        await ctx.send(
            "**Root cause summary:**\n"
            "1. The IPC template type defined 21 inputs.\n"
            "2. The interpreter path only supplied 20 values.\n"
            "3. A new non-wildcard rule used the 21st field.\n"
            "4. That caused an out-of-bounds memory read.\n"
            "5. The result was a system crash."
        )

    @commands.command(help="Lists major mitigation steps from the CrowdStrike RCA.")
    async def mitigations(self, ctx):
        await ctx.send(
            "**Major mitigations:**\n"
            "Compile-time validation for input counts.\n"
            "Runtime bounds checking in the content interpreter.\n"
            "Correcting the IPC template input count.\n"
            "Expanding test coverage for non-wildcard matching.\n"
            "Improving validator logic.\n"
            "Using staged deployments for new template instances."
        )

    @commands.command(help="Explains what an out-of-bounds read is.")
    async def oobread(self, ctx):
        await ctx.send(
            "An out-of-bounds read happens when software tries to read memory outside the valid range of an array or buffer. "
            "This can cause crashes, instability, or unintended behavior."
        )

    @commands.command(help="Explains what an RCA is in cybersecurity and IT.")
    async def whatisrca(self, ctx):
        await ctx.send(
            "RCA stands for Root Cause Analysis. It is the process of identifying the real underlying cause of an incident, "
            "not just the visible symptoms, so the issue can be fixed and prevented from happening again."
        )

    @commands.command(help="Gives lessons learned from the CrowdStrike incident.")
    async def lessonslearned(self, ctx):
        await ctx.send(
            "**Lessons learned:**\n"
            "Validate assumptions at build time.\n"
            "Add runtime safety checks.\n"
            "Expand test coverage to include edge cases.\n"
            "Test content with the real interpreter path.\n"
            "Use staged rollouts to reduce blast radius."
        )

async def setup(bot):
    await bot.add_cog(Security(bot))
