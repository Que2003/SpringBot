from discord.ext import commands

class Education(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Explains what a packet is.")
    async def packet(self, ctx):
        await ctx.send(
            "A packet is a small chunk of data sent across a network. "
            "Instead of sending one giant block of data, computers break data into packets "
            "so it can travel more efficiently and be reassembled at the destination."
        )

    @commands.command(help="Explains the difference between a packet header and payload.")
    async def headerpayload(self, ctx):
        await ctx.send(
            "**Header:** the control information, such as source, destination, and protocol.\n"
            "**Payload:** the actual content being carried, such as webpage data, video data, or file data."
        )

    @commands.command(help="Explains the OSI layers most visible in Wireshark.")
    async def osi(self, ctx):
        await ctx.send(
            "**Layer 2 - Data Link:** local delivery using MAC addresses.\n"
            "**Layer 3 - Network:** routing across networks using IP.\n"
            "**Layer 4 - Transport:** delivery method using TCP or UDP.\n"
            "Wireshark commonly shows these layers together in captured traffic."
        )

    @commands.command(help="Explains what Wireshark does.")
    async def wireshark(self, ctx):
        await ctx.send(
            "Wireshark is a read-only packet analyzer. It captures network traffic, "
            "decodes it, and shows packet details layer by layer so you can inspect protocols, "
            "addresses, ports, and other traffic details."
        )

    @commands.command(help="Explains DNS.")
    async def dns(self, ctx):
        await ctx.send(
            "DNS stands for Domain Name System. It translates names like google.com into IP addresses "
            "so devices can find the correct server on a network or the internet."
        )

    @commands.command(help="Explains DHCP.")
    async def dhcp(self, ctx):
        await ctx.send(
            "DHCP stands for Dynamic Host Configuration Protocol. It automatically assigns devices "
            "network settings such as an IP address, subnet mask, gateway, and DNS server."
        )

    @commands.command(help="Shows common networking ports.")
    async def ports(self, ctx):
        await ctx.send(
            "**Common Ports**\n"
            "20/21 = FTP\n"
            "22 = SSH\n"
            "23 = Telnet\n"
            "25 = SMTP\n"
            "53 = DNS\n"
            "67/68 = DHCP\n"
            "80 = HTTP\n"
            "110 = POP3\n"
            "143 = IMAP\n"
            "137-139 = NetBIOS\n"
            "389 = LDAP\n"
            "443 = HTTPS\n"
            "445 = SMB/CIFS\n"
            "3389 = RDP"
        )

    @commands.command(help="Explains TCP vs UDP.")
    async def tcpudp(self, ctx):
        await ctx.send(
            "**TCP:** reliable, connection-based, ordered delivery.\n"
            "**UDP:** faster, connectionless, no delivery guarantee.\n"
            "Use TCP when accuracy matters. Use UDP when speed matters more."
        )

    @commands.command(help="Explains HTTP vs HTTPS.")
    async def httphttps(self, ctx):
        await ctx.send(
            "**HTTP:** unencrypted web traffic.\n"
            "**HTTPS:** encrypted web traffic using SSL/TLS, which is much more secure."
        )

    @commands.command(help="Explains private vs public IP addresses.")
    async def iptypes(self, ctx):
        await ctx.send(
            "**Private IP:** used inside local networks and not routable directly on the public internet.\n"
            "**Public IP:** used to identify a device or network on the internet."
        )

    @commands.command(help="Shows the main A+ Core 1 exam domains.")
    async def aobjective(self, ctx):
        await ctx.send(
            "**CompTIA A+ Core 1 main domains**\n"
            "1.0 Mobile Devices\n"
            "2.0 Networking\n"
            "3.0 Hardware\n"
            "4.0 Virtualization and Cloud Computing\n"
            "5.0 Hardware and Network Troubleshooting"
        )

    @commands.command(help="Explains common wireless technologies.")
    async def wireless(self, ctx):
        await ctx.send(
            "Common wireless topics include **2.4 GHz, 5 GHz, and 6 GHz Wi-Fi**, "
            "**Bluetooth**, **NFC**, and **RFID**. Channel choice, frequency band, and interference "
            "all affect wireless performance."
        )

async def setup(bot):
    await bot.add_cog(Education(bot))
