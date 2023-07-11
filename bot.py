import asyncio
import freeGPT
import aiosqlite
from io import BytesIO
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands, Intents, Embed, File, Status, Activity, ActivityType

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
models = ["gpt3", "gpt4", "alpaca_7b"]
db = None


@bot.event
async def on_ready():
    global db
    db = await aiosqlite.connect("database.db")
    async with db.cursor() as cursor:
        await cursor.execute(
            "CREATE TABLE IF NOT EXISTS database(guilds INTEGER, channels INTEGER, model TEXT)"
        )
    print(f"{bot.user.name} connected to Discord.")
    sync_commands = await bot.tree.sync()
    print(f"Synced {len(sync_commands)} command(s).")
    while True:
        await bot.change_presence(
            status=Status.online,
            activity=Activity(
                type=ActivityType.watching,
                name=f"{len(bot.guilds)} servers | /help",
            ),
        )
        await asyncio.sleep(300)


@bot.tree.command(name="help", description="Get help.")
async def help(interaction):
    embed = Embed(
        title="Help Menu",
        description=f"Available models: `{', '.join(models)}`",
        color=0x00FFFF,
    )
    embed.add_field(
        name="setup",
        value="Usage: `/setup {model}`",
    )
    embed.add_field(name="reset", value="Usage: `/reset`")
    embed.set_footer("Made by Lucid._.")
    view = View()
    view.add_item(
        Button(
            label="Invite",
            url="None yet",
        )
    )
    view.add_item(
        Button(
            label="Server",
            url="https://dsc.gg/voidutilssupport",
        )
    )
    
    
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="setup", description="Setup the chatbot.")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.checks.bot_has_permissions(manage_channels=True)
@app_commands.describe(model=f"Model to use. Choose between {', '.join(models)}")
async def setup(interaction, model: str):
    if model.lower() not in models:
        await interaction.response.send_message(
            f"**Error:** Model not found! Choose a model between `{', '.join(models)}`."
        )
       return

    cursor = await db.execute(
        "SELECT channels, model FROM database WHERE guilds = ?",
        (interaction.guild.id,),
    )
    data = await cursor.fetchone()
    if data:
        await interaction.response.send_message(
            "**Error:** The chatbot is already set up. Use the `/reset` command to fix this error."
        )
        return

    if model.lower() in models:
        channel = await interaction.guild.create_text_channel(
            f"{model}-chat", slowmode_delay=10
        )

        await db.execute(
            "INSERT OR REPLACE INTO database (guilds, channels, model) VALUES (?, ?, ?)",
            (
                interaction.guild.id,
                channel.id,
                model,
            ),
        )
        await db.commit()
        await interaction.response.send_message(
            f"**Success:** The chatbot has been set up. The channel is {channel.mention}."
        )
    else:
        await interaction.response.send_message(
            f"**Error:** Model not found! Choose a model between `{', '.join(models)}`."
        )


@bot.tree.command(name="reset", description="Reset the chatbot.")
@app_commands.checks.has_permissions(manage_channels=True)
async def reset(interaction):
    cursor = await db.execute(
        "SELECT channels, model FROM database WHERE guilds = ?",
        (interaction.guild.id,),
    )
    data = await cursor.fetchone()
    if not data:
        await interaction.response.send_message(
            "**Error:** The chatbot is not set up. Use the `/setup` command to fix this error."
        )
        return

    await db.execute("DELETE FROM database WHERE guilds = ?", (interaction.guild.id,))
    await db.commit()
    await interaction.response.send_message("**Success:** The chatbot has been reset.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if db:
        cursor = await db.execute(
            "SELECT channels, model FROM database WHERE guilds = ?", (message.guild.id,)
        )
        data = await cursor.fetchone()
        if data:
            channel_id, model = data
            if message.channel.id == channel_id:
                await message.channel.edit(slowmode_delay=10)
                async with message.channel.typing():
                    try:
                        resp = await getattr(freeGPT, model.lower()).Completion.create(
                            prompt=message.content
                        )
                        if len(resp) <= 2000:
                            await message.reply(resp)
                        else:
                            resp = File(
                                fp=BytesIO(resp.encode("utf-8")), filename="resp.txt"
                            )
                            await message.reply(file=resp)

                    except Exception as e:
                        await message.reply(str(e))



asyncio.run(bot.run(process.env.TOKEN))
