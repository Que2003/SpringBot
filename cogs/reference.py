import asyncio
import json
import urllib.parse
import urllib.request
import urllib.error

from discord.ext import commands


class Reference(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_json(self, url, headers=None):
        headers = headers or {}
        request = urllib.request.Request(url, headers=headers, method="GET")

        def run_request():
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, run_request)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} from source.")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}")

    def shorten(self, text, limit=400):
        if not text:
            return "No summary available."
        text = " ".join(str(text).split())
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    @commands.command(help="Look up a book with sourced details. Example: !book dune")
    async def book(self, ctx, *, query: str):
        encoded = urllib.parse.quote(query)
        google_url = f"https://www.googleapis.com/books/v1/volumes?q={encoded}&maxResults=3"

        try:
            data = await self.fetch_json(google_url)
        except Exception as e:
            await ctx.send(f"Book lookup failed: {e}")
            return

        items = data.get("items", [])
        if not items:
            await ctx.send("No books found.")
            return

        book = items[0]
        info = book.get("volumeInfo", {})

        title = info.get("title", "Unknown title")
        subtitle = info.get("subtitle", "")
        authors = ", ".join(info.get("authors", [])) or "Unknown"
        published = info.get("publishedDate", "Unknown")
        publisher = info.get("publisher", "Unknown")
        categories = ", ".join(info.get("categories", [])) or "Unknown"
        description = self.shorten(info.get("description", "No description available."), 500)
        preview = info.get("previewLink", "No preview link")
        info_link = info.get("infoLink", preview)

        text = (
            f"**Book:** {title}"
            + (f" — {subtitle}" if subtitle else "")
            + "\n"
            f"**Author(s):** {authors}\n"
            f"**Published:** {published}\n"
            f"**Publisher:** {publisher}\n"
            f"**Categories:** {categories}\n"
            f"**Summary:** {description}\n"
            f"**Source:** Google Books\n"
            f"{info_link}"
        )

        await ctx.send(text)

    @commands.command(help="Look up an author. Example: !author octavia butler")
    async def author(self, ctx, *, query: str):
        encoded = urllib.parse.quote(query)
        url = f"https://openlibrary.org/search/authors.json?q={encoded}"

        try:
            data = await self.fetch_json(url)
        except Exception as e:
            await ctx.send(f"Author lookup failed: {e}")
            return

        docs = data.get("docs", [])
        if not docs:
            await ctx.send("No authors found.")
            return

        author = docs[0]
        name = author.get("name", "Unknown")
        top_work = author.get("top_work", "Unknown")
        work_count = author.get("work_count", "Unknown")
        birth_date = author.get("birth_date", "Unknown")
        top_subjects = ", ".join(author.get("top_subjects", [])[:5]) or "Unknown"
        key = author.get("key", "")
        link = f"https://openlibrary.org{key}" if key else "No profile link"

        await ctx.send(
            f"**Author:** {name}\n"
            f"**Birth date:** {birth_date}\n"
            f"**Top work:** {top_work}\n"
            f"**Work count:** {work_count}\n"
            f"**Common subjects:** {top_subjects}\n"
            f"**Source:** Open Library\n"
            f"{link}"
        )

    @commands.command(help="Look up a country or region-style country entry. Example: !region japan")
    async def region(self, ctx, *, query: str):
        encoded = urllib.parse.quote(query)
        restcountries_url = f"https://restcountries.com/v3.1/name/{encoded}"

        try:
            country_data = await self.fetch_json(restcountries_url)
        except Exception as e:
            await ctx.send(f"Region lookup failed: {e}")
            return

        if not isinstance(country_data, list) or not country_data:
            await ctx.send("No region/country match found.")
            return

        country = country_data[0]

        name = country.get("name", {}).get("common", "Unknown")
        official = country.get("name", {}).get("official", "Unknown")
        capital_list = country.get("capital", [])
        capital = ", ".join(capital_list) if capital_list else "Unknown"
        population = country.get("population", "Unknown")
        region = country.get("region", "Unknown")
        subregion = country.get("subregion", "Unknown")

        languages_obj = country.get("languages", {})
        languages = ", ".join(languages_obj.values()) if languages_obj else "Unknown"

        currencies_obj = country.get("currencies", {})
        if currencies_obj:
            currency_names = []
            for _, value in currencies_obj.items():
                currency_names.append(value.get("name", "Unknown currency"))
            currencies = ", ".join(currency_names)
        else:
            currencies = "Unknown"

        cca2 = country.get("cca2", "")
        world_bank_text = ""
        if cca2:
            wb_url = f"https://api.worldbank.org/v2/country/{cca2}?format=json"
            try:
                wb_data = await self.fetch_json(wb_url)
                if isinstance(wb_data, list) and len(wb_data) > 1 and wb_data[1]:
                    wb = wb_data[1][0]
                    wb_region = wb.get("region", {}).get("value", "Unknown")
                    wb_admin = wb.get("adminregion", {}).get("value", "Unknown")
                    wb_income = wb.get("incomeLevel", {}).get("value", "Unknown")
                    world_bank_text = (
                        f"\n**World Bank region:** {wb_region}"
                        f"\n**Admin region:** {wb_admin}"
                        f"\n**Income level:** {wb_income}"
                    )
            except Exception:
                world_bank_text = "\n**World Bank region:** Unavailable right now."

        await ctx.send(
            f"**Country/Region Entry:** {name}\n"
            f"**Official name:** {official}\n"
            f"**Capital:** {capital}\n"
            f"**Population:** {population}\n"
            f"**Region:** {region}\n"
            f"**Subregion:** {subregion}\n"
            f"**Languages:** {languages}\n"
            f"**Currencies:** {currencies}"
            f"{world_bank_text}\n"
            f"**Sources:** REST Countries + World Bank"
        )

    @commands.command(help="Compare two countries. Example: !comparecountries japan | brazil")
    async def comparecountries(self, ctx, *, text: str):
        if "|" not in text:
            await ctx.send("Use this format: `!comparecountries country1 | country2`")
            return

        left, right = [part.strip() for part in text.split("|", 1)]
        if not left or not right:
            await ctx.send("Use this format: `!comparecountries country1 | country2`")
            return

        async def get_country(name):
            encoded = urllib.parse.quote(name)
            url = f"https://restcountries.com/v3.1/name/{encoded}"
            data = await self.fetch_json(url)
            if not isinstance(data, list) or not data:
                return None
            return data[0]

        try:
            a = await get_country(left)
            b = await get_country(right)
        except Exception as e:
            await ctx.send(f"Country comparison failed: {e}")
            return

        if not a or not b:
            await ctx.send("One or both countries could not be found.")
            return

        def info(country):
            name = country.get("name", {}).get("common", "Unknown")
            capital = ", ".join(country.get("capital", [])) or "Unknown"
            population = country.get("population", "Unknown")
            region = country.get("region", "Unknown")
            subregion = country.get("subregion", "Unknown")
            return name, capital, population, region, subregion

        a_name, a_capital, a_pop, a_region, a_sub = info(a)
        b_name, b_capital, b_pop, b_region, b_sub = info(b)

        await ctx.send(
            f"**Country Comparison**\n\n"
            f"**{a_name}**\n"
            f"Capital: {a_capital}\n"
            f"Population: {a_pop}\n"
            f"Region: {a_region}\n"
            f"Subregion: {a_sub}\n\n"
            f"**{b_name}**\n"
            f"Capital: {b_capital}\n"
            f"Population: {b_pop}\n"
            f"Region: {b_region}\n"
            f"Subregion: {b_sub}\n\n"
            f"**Source:** REST Countries"
        )

    @commands.command(help="Show which sources the region/book commands use.")
    async def sourceshelp(self, ctx):
        await ctx.send(
            "**Reference Sources**\n"
            "Books: Google Books, Open Library\n"
            "Regions/Countries: REST Countries, World Bank\n\n"
            "**Commands**\n"
            "!book <title>\n"
            "!author <name>\n"
            "!region <country>\n"
            "!comparecountries <country1 | country2>\n"
            "!sourceshelp"
        )


async def setup(bot):
    await bot.add_cog(Reference(bot))