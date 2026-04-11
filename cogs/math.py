import math
import re
from discord.ext import commands


class Math(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def safe_eval(self, expression: str):
        cleaned = expression.replace("^", "**").strip()

        allowed = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
            "sqrt": math.sqrt,
            "pi": math.pi,
            "e": math.e,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "factorial": math.factorial,
            "ceil": math.ceil,
            "floor": math.floor,
        }

        return eval(cleaned, allowed, {})

    @commands.command(help="Calculate a math expression. Example: !calc 5*(3+2)^2")
    async def calc(self, ctx, *, expression: str):
        try:
            result = self.safe_eval(expression)
            await ctx.send(f"Expression: `{expression}`\nAnswer: **{result}**")
        except Exception:
            await ctx.send("I could not solve that expression.")

    @commands.command(help="Add two numbers. Example: !add 5 7")
    async def add(self, ctx, a: float, b: float):
        await ctx.send(f"Answer: **{a + b}**")

    @commands.command(help="Subtract two numbers. Example: !subtract 10 4")
    async def subtract(self, ctx, a: float, b: float):
        await ctx.send(f"Answer: **{a - b}**")

    @commands.command(help="Multiply two numbers. Example: !multiply 6 8")
    async def multiply(self, ctx, a: float, b: float):
        await ctx.send(f"Answer: **{a * b}**")

    @commands.command(help="Divide two numbers. Example: !divide 20 5")
    async def divide(self, ctx, a: float, b: float):
        if b == 0:
            await ctx.send("You cannot divide by zero.")
            return
        await ctx.send(f"Answer: **{a / b}**")

    @commands.command(help="Raise a number to a power. Example: !power 2 8")
    async def power(self, ctx, base: float, exponent: float):
        await ctx.send(f"Answer: **{base ** exponent}**")

    @commands.command(help="Find a square root. Example: !sqrt 49")
    async def sqrt(self, ctx, number: float):
        if number < 0:
            await ctx.send("I cannot take the square root of a negative number here.")
            return
        await ctx.send(f"Answer: **{math.sqrt(number)}**")

    @commands.command(help="Find a percentage. Example: !percent 25 200")
    async def percent(self, ctx, part: float, whole: float):
        if whole == 0:
            await ctx.send("Whole cannot be zero.")
            return
        result = (part / whole) * 100
        await ctx.send(f"Answer: **{result}%**")

    @commands.command(help="Find what percent one number is of another. Example: !whatpercent 50 200")
    async def whatpercent(self, ctx, part: float, whole: float):
        if whole == 0:
            await ctx.send("Whole cannot be zero.")
            return
        result = (part / whole) * 100
        await ctx.send(f"**{part}** is **{result}%** of **{whole}**")

    @commands.command(help="Area of a rectangle. Example: !rectangle 5 9")
    async def rectangle(self, ctx, length: float, width: float):
        area = length * width
        await ctx.send(f"Area: **{area}**")

    @commands.command(help="Area of a triangle. Example: !triangle 10 4")
    async def triangle(self, ctx, base: float, height: float):
        area = 0.5 * base * height
        await ctx.send(f"Area: **{area}**")

    @commands.command(help="Area of a circle. Example: !circle 7")
    async def circle(self, ctx, radius: float):
        area = math.pi * radius * radius
        await ctx.send(f"Area: **{area}**")

    @commands.command(help="Circumference of a circle. Example: !circumference 7")
    async def circumference(self, ctx, radius: float):
        value = 2 * math.pi * radius
        await ctx.send(f"Circumference: **{value}**")

    @commands.command(help="Pythagorean theorem. Example: !pythagorean 3 4")
    async def pythagorean(self, ctx, a: float, b: float):
        c = math.sqrt((a ** 2) + (b ** 2))
        await ctx.send(f"Hypotenuse: **{c}**")

    @commands.command(help="Convert Celsius to Fahrenheit. Example: !ctof 25")
    async def ctof(self, ctx, celsius: float):
        fahrenheit = (celsius * 9 / 5) + 32
        await ctx.send(f"Answer: **{fahrenheit}°F**")

    @commands.command(help="Convert Fahrenheit to Celsius. Example: !ftoc 77")
    async def ftoc(self, ctx, fahrenheit: float):
        celsius = (fahrenheit - 32) * 5 / 9
        await ctx.send(f"Answer: **{celsius}°C**")

    @commands.command(help="Convert inches to centimeters. Example: !inchestocm 12")
    async def inchestocm(self, ctx, inches: float):
        await ctx.send(f"Answer: **{inches * 2.54} cm**")

    @commands.command(help="Convert centimeters to inches. Example: !cmtoinches 30")
    async def cmtoinches(self, ctx, cm: float):
        await ctx.send(f"Answer: **{cm / 2.54} inches**")

    @commands.command(help="Solve simple linear equations like 2x+3=11")
    async def solve(self, ctx, *, equation: str):
        eq = equation.replace(" ", "")
        match = re.fullmatch(r"([+-]?\d*)x([+-]\d+)?=([+-]?\d+)", eq)

        if not match:
            await ctx.send("I can solve simple equations like `2x+3=11`.")
            return

        a_str, b_str, c_str = match.groups()

        if a_str in ("", "+"):
            a = 1
        elif a_str == "-":
            a = -1
        else:
            a = int(a_str)

        b = int(b_str) if b_str else 0
        c = int(c_str)

        if a == 0:
            await ctx.send("That equation is invalid.")
            return

        x = (c - b) / a

        await ctx.send(
            f"Equation: **{equation}**\n"
            f"Step 1: move **{b}** to the other side -> **{a}x = {c - b}**\n"
            f"Step 2: divide by **{a}**\n"
            f"Answer: **x = {x}**"
        )

    @commands.command(help="Show all math commands.")
    async def mathhelp(self, ctx):
        await ctx.send(
            "**Math Commands**\n"
            "!calc <expression>\n"
            "!add <a> <b>\n"
            "!subtract <a> <b>\n"
            "!multiply <a> <b>\n"
            "!divide <a> <b>\n"
            "!power <base> <exponent>\n"
            "!sqrt <number>\n"
            "!percent <part> <whole>\n"
            "!whatpercent <part> <whole>\n"
            "!rectangle <length> <width>\n"
            "!triangle <base> <height>\n"
            "!circle <radius>\n"
            "!circumference <radius>\n"
            "!pythagorean <a> <b>\n"
            "!ctof <celsius>\n"
            "!ftoc <fahrenheit>\n"
            "!inchestocm <inches>\n"
            "!cmtoinches <cm>\n"
            "!solve <equation>"
        )


async def setup(bot):
    await bot.add_cog(Math(bot))