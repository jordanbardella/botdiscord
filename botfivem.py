import discord
from discord import app_commands
from discord.ext import commands
import aiofiles
import aiohttp
import asyncio
import subprocess
import re

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot en ligne")
    try:
        synced = await bot.tree.sync()
        print(f"Synchronisation de {len(synced)} commande(s)")
    except Exception as e:
        print(e)

async def fetch_xbox_info(account_id):
    url = f"https://xbl.io/api/v2/account/{account_id}"
    
    headers = {
        "accept": "application/json",
        "x-authorization": "5ee3d375-dcad-4865-aaf1-188083e4d8d4"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if "profileUsers" in data and len(data["profileUsers"]) > 0:
                    profile_user = data["profileUsers"][0]
                    if "settings" in profile_user:
                        settings = profile_user["settings"]
                        gamertag = "Not available"
                        avatar = "Not available"
                        location = "Not available"
                        bio = "Not available"
                        real_name = "Not available"
                        for setting in settings:
                            if setting['id'] == 'Gamertag':
                                gamertag = setting['value']
                            elif setting['id'] == 'GameDisplayPicRaw':
                                avatar = setting['value']
                            elif setting['id'] == 'Location':
                                location = setting['value']
                            elif setting['id'] == 'Bio':
                                bio = setting['value']
                            elif setting['id'] == 'RealName':
                                real_name = setting['value']
                        return gamertag, avatar, location, bio, real_name
                else:
                    return None
            else:
                return None

async def fetch_steam_info(steamid):
    steamid_decimal = steamid_to_decimal(steamid)
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=B9D6C260DFDD2E0A73001DBFAFB2AF77&steamids={steamid_decimal}"
    async with aiohttp.ClientSession() as session:
        print("DEBUG: STEAMAPI")
        async with session.get(url) as response:
            data = await response.json()

            if data['response']['players']:
                player = data['response']['players'][0]
                personaname = player.get('personaname', 'Not available')
                profileurl = player.get('profileurl', 'Not available')
                avatarfull = player.get('avatarfull', 'Not available')
                loccountrycode = player.get('loccountrycode', 'Not available')
                personastate = player.get('personastate', 'Not available')
                gameextrainfo = player.get('gameextrainfo', 'Not available')
                return personaname, profileurl, gameextrainfo, avatarfull, loccountrycode, personastate
            else:
                return None

def steamid_to_decimal(steamid):
    return str(int(steamid, 16))
    
@bot.tree.command(name="lookup")
@app_commands.describe(user_id="L'ID de l'utilisateur à rechercher")
async def lookup(interaction: discord.Interaction, user_id: str):
    verif = 1319035547112570950
    if interaction.channel.id != verif:
        await interaction.response.send_message("Cette commande ne peut être utilisée que dans un salon spécifique.", ephemeral=True)
        return 
    else:
        rg = r"rg.exe"
        fichier = ["test1.txt"]
        cmd = [rg, user_id] + fichier

        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        result = stdout.decode().strip()
        error = stderr.decode().strip()

        if error:
            await interaction.response.send_message(f"Erreur lors de la recherche : {error}", ephemeral=True)
            return

        results = result.split('\n')  
        if not results or results == ['']:
            await interaction.response.send_message("Aucun résultat trouvé.", ephemeral=True)
            return

        unique_results = []
        seen_info = set()  

        for result_line in results:
            info_tuple = tuple(re.findall(r"(?<=:)[a-zA-Z0-9]+", result_line))  
            if info_tuple not in seen_info:
                unique_results.append(result_line)
                seen_info.add(info_tuple)

        if not unique_results:
            await interaction.response.send_message("Aucun résultat unique trouvé.", ephemeral=True)
            return

        page = 0
        max_page = len(unique_results) - 1
        
        def generate_embed(page_index):
            result_line = unique_results[page_index]
            name_search = re.search(r"Name: ([\w\s]+)", result_line)
            name = name_search.group(1) if name_search else 'Unknown'

            title = f"🔎 Information de {name} ({user_id}) - Page {page_index + 1} de {max_page + 1}"
            embed = discord.Embed(title=title, color=discord.Color.blue())
            embed.add_field(name="📋 Name", value=name, inline=False)

            fields = {
                'DiscordID': ('discord', '<:discord:1234483757243826256>'),
                'SteamID': ('steam', '<:steam:1234483447150674030>'),
                'Xbox LiveID': ('xbl', '<:xbox:1234483839460442205>'),
                'Microsoft LiveID': ('live', '<:microsoft:1234484070055018536>'),
                'FivemID': ('fivem', '<:fivem:1234484381079572491>'),
                'License': ('license', '🔗'),
                'License2': ('license2', '🔗')
            }
            steam_id = None
            xbox_gamertag = None
            for key, (prefix, emoji) in fields.items():
                regex = re.search(f"{prefix}:([a-zA-Z0-9]+)", result_line)
                value = regex.group(1) if regex else '?'
                if key == 'SteamID' and value != '?':
                    steam_id = value
                    value = steamid_to_decimal(value)
                    print(value)
                if key == 'Xbox LiveID' and value != '?':
                    xbox_gamertag = value

                embed.add_field(name=f"{emoji} {key}", value=value, inline=True)
            
            return embed, steam_id, xbox_gamertag
            
        embed, steam_id, xbox_gamertag = generate_embed(page)

    class ResultView(discord.ui.View):
        def __init__(self, page, max_page, steam_id=None, xbox_gamertag=None):
            super().__init__(timeout=180)  # Timeout de 180 secondes
            self.page = page
            self.max_page = max_page
            self.steam_id = steam_id
            self.xbox_gamertag = xbox_gamertag
            
            self.back_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="<<", disabled=(self.page == 0))
            self.back_button.callback = self.back_button_callback
            self.add_item(self.back_button)

            if self.steam_id:
                self.steam_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Steam Lookup")
                self.steam_button.emoji = discord.PartialEmoji(name="steam", id=1234483447150674030)
                self.steam_button.callback = self.steam_button_callback
                self.add_item(self.steam_button)

            if self.xbox_gamertag:
                self.xbox_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Xbox Lookup")
                self.xbox_button.emoji = discord.PartialEmoji(name="xbox", id=1234483839460442205)
                self.xbox_button.callback = self.xbox_button_callback
                self.add_item(self.xbox_button)
                
            self.forward_button = discord.ui.Button(style=discord.ButtonStyle.primary, label=">>", disabled=(self.page == self.max_page))
            self.forward_button.callback = self.forward_button_callback
            self.add_item(self.forward_button)
            
        async def back_button_callback(self, interaction):
            try:
                if self.page > 0:
                    self.page -= 1
                embed, steam_id, xbox_gamertag = generate_embed(self.page)
                self.steam_id = steam_id
                self.back_button.disabled = (self.page == 0)
                self.forward_button.disabled = (self.page == self.max_page)
                
                self.clear_items()
                self.add_item(self.back_button)
                if hasattr(self, 'steam_button'):
                    self.add_item(self.steam_button)
                if hasattr(self, 'xbox_button'):
                    self.add_item(self.xbox_button)
                self.add_item(self.forward_button)

                await interaction.response.edit_message(embed=embed, view=self)
            except discord.errors.NotFound:
                await interaction.response.send_message("L'interaction a expiré. Veuillez réessayer.", ephemeral=True)

        async def forward_button_callback(self, interaction):
            try:
                if self.page < self.max_page:
                    self.page += 1
                embed, steam_id, xbox_gamertag = generate_embed(self.page)
                self.steam_id = steam_id
                self.back_button.disabled = (self.page == 0)
                self.forward_button.disabled = (self.page == self.max_page)

                self.clear_items()
                self.add_item(self.back_button)
                if hasattr(self, 'steam_button'):
                    self.add_item(self.steam_button)
                if hasattr(self, 'xbox_button'):
                    self.add_item(self.xbox_button)
                self.add_item(self.forward_button)

                await interaction.response.edit_message(embed=embed, view=self)
            except discord.errors.NotFound:
                await interaction.response.send_message("L'interaction a expiré. Veuillez réessayer.", ephemeral=True)

        async def steam_button_callback(self, interaction):
            if self.steam_id:
                steam_info = await fetch_steam_info(self.steam_id)
                if steam_info:
                    personaname, profileurl, gameextrainfo, avatarfull, loccountrycode, personastate = steam_info

                    state_mapping = {
                        0: "Offline",
                        1: "Online",
                        2: "Occupé",
                        3: "AFK"
                    }

                    state = state_mapping.get(personastate, "Statut inconnu")

                    new_embed = discord.Embed(title=f"🔎 Steam Profile Information - {personaname} ({state})", color=discord.Color.green())
                    new_embed.add_field(name="📋 Name", value=personaname, inline=False)
                    new_embed.add_field(name="🔗 Profile URL", value=profileurl, inline=False)
                    new_embed.add_field(name="🎮 Game Info", value=gameextrainfo, inline=False)
                    new_embed.set_thumbnail(url=avatarfull)

                    new_view = discord.ui.View()
                    back_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Retour")
                    back_button.callback = self.back_button_callback
                    new_view.add_item(back_button)
                    await interaction.response.edit_message(embed=new_embed, view=new_view)
                else:
                    await interaction.response.send_message("Impossible de récupérer les informations du profil Steam.", ephemeral=True)

        async def xbox_button_callback(self, interaction):
            if self.xbox_gamertag:
                xbox_info = await fetch_xbox_info(self.xbox_gamertag)
                if xbox_info:
                    gamertag, avatar, location, bio, real_name = xbox_info

                    gamertag = gamertag if gamertag else "?"
                    avatar = avatar if avatar else "?"
                    location = location if location else "?"
                    bio = bio if bio else "?"
                    real_name = real_name if real_name else "?"

                    new_embed = discord.Embed(title=f"🔎 Xbox Profile Information - {gamertag}", color=discord.Color.green())
                    new_embed.add_field(name="📋 Gamertag", value=gamertag, inline=False)
                    new_embed.add_field(name="🏠 Location", value=location, inline=False)
                    new_embed.add_field(name="ℹ️ Bio", value=bio, inline=False)
                    new_embed.add_field(name="👤 Real Name", value=real_name, inline=False)
                    new_embed.set_thumbnail(url=avatar)

                    new_view = discord.ui.View()
                    back_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Retour")
                    back_button.callback = self.back_button_callback
                    new_view.add_item(back_button)
                    await interaction.response.edit_message(embed=new_embed, view=new_view)
                else:
                    await interaction.response.send_message("Erreur lors de la récupération des informations Xbox.", ephemeral=True)

    view = ResultView(page, max_page, steam_id, xbox_gamertag)
    await interaction.response.send_message(embed=embed, view=view)

bot.run('MTIzNDk1NDU3MTUxNjg3NDg0Mg.Gy6nHa.A8C-kdCZ-_a2NrjSokJSDrI6-UyLubrb7k5Lrw')
