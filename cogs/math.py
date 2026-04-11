import math
import re
import statistics
from fractions import Fraction
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
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "log": math.log,
            "log10": math.log10,
            "factorial": math.factorial,
            "ceil": math.ceil,
            "floor": math.floor,
        }

        return eval(cleaned, allowed, {})

    def parse_number_list(self, text: str):
        parts = [x.strip() for x in text.split(",")]
        return [float(x) for x in parts if x]

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

    @commands.command(help="Solve a quadratic equation ax^2+bx+c=0. Example: !quadratic 1 -3 2")
    async def quadratic(self, ctx, a: float, b: float, c: float):
        if a == 0:
            await ctx.send("For a quadratic, **a** cannot be zero.")
            return

        discriminant = (b ** 2) - (4 * a * c)

        if discriminant > 0:
            x1 = (-b + math.sqrt(discriminant)) / (2 * a)
            x2 = (-b - math.sqrt(discriminant)) / (2 * a)
            await ctx.send(
                f"Quadratic: **{a}x² + {b}x + {c} = 0**\n"
                f"Discriminant: **{discriminant}**\n"
                f"Two real solutions:\n"
                f"**x₁ = {x1}**\n"
                f"**x₂ = {x2}**"
            )
        elif discriminant == 0:
            x = -b / (2 * a)
            await ctx.send(
                f"Quadratic: **{a}x² + {b}x + {c} = 0**\n"
                f"Discriminant: **0**\n"
                f"One repeated real solution:\n"
                f"**x = {x}**"
            )
        else:
            real = -b / (2 * a)
            imag = math.sqrt(-discriminant) / (2 * a)
            await ctx.send(
                f"Quadratic: **{a}x² + {b}x + {c} = 0**\n"
                f"Discriminant: **{discriminant}**\n"
                f"Two complex solutions:\n"
                f"**x₁ = {real} + {imag}i**\n"
                f"**x₂ = {real} - {imag}i**"
            )

    @commands.command(help="Find slope from two points. Example: !slope 2 3 6 11")
    async def slope(self, ctx, x1: float, y1: float, x2: float, y2: float):
        if x2 - x1 == 0:
            await ctx.send("The slope is undefined because the line is vertical.")
            return

        m = (y2 - y1) / (x2 - x1)
        await ctx.send(
            f"Points: **({x1}, {y1})** and **({x2}, {y2})**\n"
            f"Slope formula: **(y₂ - y₁) / (x₂ - x₁)**\n"
            f"Answer: **{m}**"
        )

    @commands.command(help="Convert point-slope info to slope-intercept form. Example: !slopeintercept 2 3 4")
    async def slopeintercept(self, ctx, m: float, x: float, y: float):
        b = y - (m * x)
        await ctx.send(
            f"Given slope **m = {m}** and point **({x}, {y})**\n"
            f"Use **y = mx + b**\n"
            f"Substitute point values: **{y} = {m}({x}) + b**\n"
            f"Answer: **y = {m}x + {b}**"
        )

    @commands.command(help="Find midpoint of two points. Example: !midpoint 2 3 6 11")
    async def midpoint(self, ctx, x1: float, y1: float, x2: float, y2: float):
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        await ctx.send(f"Midpoint: **({mx}, {my})**")

    @commands.command(help="Find distance between two points. Example: !distance 2 3 6 11")
    async def distance(self, ctx, x1: float, y1: float, x2: float, y2: float):
        d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        await ctx.send(f"Distance: **{d}**")

    @commands.command(help="Reduce a fraction. Example: !fraction 24 36")
    async def fraction(self, ctx, numerator: int, denominator: int):
        if denominator == 0:
            await ctx.send("Denominator cannot be zero.")
            return

        frac = Fraction(numerator, denominator)
        await ctx.send(f"Reduced fraction: **{frac}**")

    @commands.command(help="Convert decimal to fraction. Example: !decimaltofraction 0.75")
    async def decimaltofraction(self, ctx, number: float):
        frac = Fraction(number).limit_denominator()
        await ctx.send(f"Fraction form: **{frac}**")

    @commands.command(help="Convert fraction to decimal. Example: !fractiontodecimal 3 4")
    async def fractiontodecimal(self, ctx, numerator: int, denominator: int):
        if denominator == 0:
            await ctx.send("Denominator cannot be zero.")
            return
        await ctx.send(f"Decimal form: **{numerator / denominator}**")

    @commands.command(help="Convert to scientific notation. Example: !scientific 1250000")
    async def scientific(self, ctx, number: float):
        await ctx.send(f"Scientific notation: **{number:.6e}**")

    @commands.command(help="Convert scientific notation to normal form. Example: !standard 1.25e6")
    async def standard(self, ctx, number: float):
        await ctx.send(f"Standard form: **{number}**")

    @commands.command(help="Find mean of comma-separated numbers. Example: !mean 2,4,6,8")
    async def mean(self, ctx, *, numbers: str):
        try:
            values = self.parse_number_list(numbers)
            await ctx.send(f"Mean: **{statistics.mean(values)}**")
        except Exception:
            await ctx.send("Use comma-separated numbers like `!mean 2,4,6,8`.")

    @commands.command(help="Find median of comma-separated numbers. Example: !median 2,4,6,8")
    async def median(self, ctx, *, numbers: str):
        try:
            values = self.parse_number_list(numbers)
            await ctx.send(f"Median: **{statistics.median(values)}**")
        except Exception:
            await ctx.send("Use comma-separated numbers like `!median 2,4,6,8`.")

    @commands.command(help="Find mode of comma-separated numbers. Example: !mode 2,2,3,4")
    async def mode(self, ctx, *, numbers: str):
        try:
            values = self.parse_number_list(numbers)
            result = statistics.mode(values)
            await ctx.send(f"Mode: **{result}**")
        except statistics.StatisticsError:
            await ctx.send("There is no single mode for that set.")
        except Exception:
            await ctx.send("Use comma-separated numbers like `!mode 2,2,3,4`.")

    @commands.command(help="Find range of comma-separated numbers. Example: !rangeof 2,4,6,8")
    async def rangeof(self, ctx, *, numbers: str):
        try:
            values = self.parse_number_list(numbers)
            result = max(values) - min(values)
            await ctx.send(f"Range: **{result}**")
        except Exception:
            await ctx.send("Use comma-separated numbers like `!rangeof 2,4,6,8`.")

    @commands.command(help="Find population standard deviation. Example: !stddev 2,4,6,8")
    async def stddev(self, ctx, *, numbers: str):
        try:
            values = self.parse_number_list(numbers)
            result = statistics.pstdev(values)
            await ctx.send(f"Population standard deviation: **{result}**")
        except Exception:
            await ctx.send("Use comma-separated numbers like `!stddev 2,4,6,8`.")

    @commands.command(help="Find permutations nPr. Example: !perm 5 2")
    async def perm(self, ctx, n: int, r: int):
        if n < 0 or r < 0 or r > n:
            await ctx.send("Use values where **n >= r >= 0**.")
            return
        result = math.perm(n, r)
        await ctx.send(f"Permutations (nPr): **{result}**")

    @commands.command(help="Find combinations nCr. Example: !comb 5 2")
    async def comb(self, ctx, n: int, r: int):
        if n < 0 or r < 0 or r > n:
            await ctx.send("Use values where **n >= r >= 0**.")
            return
        result = math.comb(n, r)
        await ctx.send(f"Combinations (nCr): **{result}**")

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
            "!solve <equation>\n"
            "!quadratic <a> <b> <c>\n"
            "!slope <x1> <y1> <x2> <y2>\n"
            "!slopeintercept <m> <x> <y>\n"
            "!midpoint <x1> <y1> <x2> <y2>\n"
            "!distance <x1> <y1> <x2> <y2>\n"
            "!fraction <numerator> <denominator>\n"
            "!decimaltofraction <decimal>\n"
            "!fractiontodecimal <numerator> <denominator>\n"
            "!scientific <number>\n"
            "!standard <scientific_number>\n"
            "!mean <comma-separated numbers>\n"
            "!median <comma-separated numbers>\n"
            "!mode <comma-separated numbers>\n"
            "!rangeof <comma-separated numbers>\n"
            "!stddev <comma-separated numbers>\n"
            "!perm <n> <r>\n"
            "!comb <n> <r>"
        )


async def setup(bot):
    await bot.add_cog(Math(bot))