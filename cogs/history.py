from discord.ext import commands

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Explains the history of AI from early milestones to modern models.")
    async def aihistory(self, ctx):
        await ctx.send(
            "**AI History Overview**\n"
            "1950: Alan Turing proposed the Turing Test as a way to judge machine intelligence.\n"
            "1966: ELIZA became one of the first famous chatbots.\n"
            "Later, neural network research continued, but AI progress slowed during multiple 'AI Winters' "
            "when funding and confidence dropped.\n"
            "Modern AI accelerated again because of better data, stronger hardware, and deep learning."
        )

    @commands.command(help="Explains why Transformers changed AI.")
    async def transformer(self, ctx):
        await ctx.send(
            "The Transformer architecture changed AI by using **attention** to focus on the most relevant "
            "parts of a sentence or sequence. That made language processing much more effective than older "
            "methods that handled words in a more limited step-by-step way."
        )

    @commands.command(help="Shows the GPT model timeline.")
    async def gpttimeline(self, ctx):
        await ctx.send(
            "**GPT Timeline**\n"
            "GPT-1 (2018): showed that a model could learn language patterns from large text data.\n"
            "GPT-2 (2019): became much larger and could generate longer, more coherent writing.\n"
            "GPT-3 (2020): scaled massively and became much stronger at writing, answering questions, and coding.\n"
            "ChatGPT (2022): based on GPT-3.5, optimized for conversation and released publicly."
        )

    @commands.command(help="Explains what RLHF is.")
    async def rlhf(self, ctx):
        await ctx.send(
            "RLHF stands for **Reinforcement Learning from Human Feedback**. "
            "It means humans review model behavior and help guide it toward being more helpful, safer, "
            "and better at conversation instead of just predicting the next word with no guidance."
        )

    @commands.command(help="Explains why ChatGPT feels more conversational than older models.")
    async def chatgpt(self, ctx):
        await ctx.send(
            "ChatGPT feels more conversational because it combines a large language model with instruction tuning "
            "and RLHF. That makes it better at following requests, keeping context, and responding in a more useful way."
        )

    @commands.command(help="Gives a timeline of major AI milestones.")
    async def aitimeline(self, ctx):
        await ctx.send(
            "**Major AI Milestones**\n"
            "1950 - Turing Test\n"
            "1966 - ELIZA chatbot\n"
            "AI Winter periods - progress slowed due to limited results and funding\n"
            "2017 - Transformer architecture introduced\n"
            "2018 - GPT-1\n"
            "2019 - GPT-2\n"
            "2020 - GPT-3\n"
            "2022 - ChatGPT public release"
        )

    @commands.command(help="Shows prompt styles for learning history better.")
    async def historyprompts(self, ctx):
        await ctx.send(
            "**History Prompt Styles**\n"
            "Roleplay: Act as a reporter witnessing the Fall of the Berlin Wall.\n"
            "Simulated Dialogue: Act as William the Conqueror and answer questions.\n"
            "What If: What if JFK had survived?\n"
            "Analysis: Explain World War I from the viewpoints of multiple major powers."
        )

    @commands.command(help="Gives a roleplay prompt example for history learning.")
    async def roleplayprompt(self, ctx):
        await ctx.send(
            'Example: **"Act as a reporter witnessing the Fall of the Berlin Wall. '
            'Write an eye-witness account of the atmosphere."**'
        )

    @commands.command(help="Gives a simulated dialogue prompt example for history learning.")
    async def dialogueprompt(self, ctx):
        await ctx.send(
            'Example: **"Act as William the Conqueror. I will ask you questions about why you invaded England."**'
        )

    @commands.command(help="Gives a what-if history prompt example.")
    async def whatifprompt(self, ctx):
        await ctx.send(
            'Example: **"What if John F. Kennedy had survived the assassination attempt? '
            'Explain the likely political consequences."**'
        )

    @commands.command(help="Gives a history analysis prompt example.")
    async def analysisprompt(self, ctx):
        await ctx.send(
            'Example: **"Explain the causes of World War I by comparing the viewpoints of three different major powers."**'
        )

async def setup(bot):
    await bot.add_cog(History(bot))
