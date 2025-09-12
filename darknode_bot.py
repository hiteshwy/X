
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import subprocess
import psutil
import platform
import datetime
import sys

# Load .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

vps_instances = {}

def is_admin(interaction: discord.Interaction):
    return interaction.user.id in ADMIN_IDS

def get_sysinfo():
    cpu = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    processes = len(psutil.pids())
    return (
        f"🖥️ CPU Cores: {cpu}\n"
        f"💾 Memory: {mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB\n"
        f"📀 Disk: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB\n"
        f"⚙️ Running Processes: {processes}\n"
    )

def darknode_embed(title, description, color=0x2f3136):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="DarkNode VPS • Powered by tmate")
    return embed

def get_ssh_info():
    try:
        return subprocess.check_output('cat /etc/ssh/sshd_config', shell=True, text=True)[:1000]
    except:
        return "Failed to get SSH info"

def get_user_info():
    try:
        return subprocess.check_output('cat /etc/passwd', shell=True, text=True)[:1000]
    except:
        return "Failed to get user info"

def get_container_info():
    try:
        return subprocess.check_output('docker ps -a', shell=True, text=True)[:1000]
    except:
        return "Failed to get container info"

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online as {bot.user}, commands synced.")

class VPSGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="vps", description="VPS management commands")

    @app_commands.command(name="deploy", description="Deploy a new VPS session (tmate)")
    async def deploy(self, interaction: discord.Interaction, container_name: str, ram: str = "1GB", cpu: str = "1", target_user: discord.Member = None):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        user = target_user or interaction.user

        try:
            subprocess.check_output(f"tmate -S /tmp/{container_name}.sock new-session -d", shell=True)
            subprocess.call(f"tmate -S /tmp/{container_name}.sock send-keys 'hostnamectl set-hostname DarkNode' C-m", shell=True)
            ssh_info = subprocess.check_output(f"tmate -S /tmp/{container_name}.sock display -p '{{tmate_ssh}}'", shell=True, text=True).strip()

            vps_instances[container_name] = {
                "user": str(user),
                "ram": ram,
                "cpu": cpu,
                "ssh_info": ssh_info,
                "status": "running",
                "deployed_at": str(datetime.datetime.now())
            }

            try:
                await user.send(embed=darknode_embed("🚀 VPS Deployed", f"Here is your SSH:\n`{ssh_info}`"))
            except:
                pass

            await interaction.response.send_message(embed=darknode_embed("🚀 VPS Deployed", f"VPS `{container_name}` deployed for {user.mention}\n🔧 RAM: {ram}\n⚡ CPU: {cpu}\n🔑 SSH: `{ssh_info}`"))
        except Exception as e:
            await interaction.response.send_message(embed=darknode_embed("❌ Deployment Failed", str(e)), ephemeral=True)

    @app_commands.command(name="list", description="List VPS instances")
    async def list(self, interaction: discord.Interaction):
        if not vps_instances:
            await interaction.response.send_message(embed=darknode_embed("📋 VPS List", "No active VPS instances."))
            return
        desc = "".join([f"**{n}** - {i['user']} - {i['status']} - {i['deployed_at']}\n" for n,i in vps_instances.items()])
        await interaction.response.send_message(embed=darknode_embed("📋 Active VPS", desc))

    @app_commands.command(name="start", description="Start a VPS instance")
    async def start(self, interaction: discord.Interaction, container_name: str):
        if container_name in vps_instances and vps_instances[container_name]["status"] == "stopped":
            vps_instances[container_name]["status"] = "running"
            await interaction.response.send_message(embed=darknode_embed("▶️ VPS Started", f"{container_name} is now running."))
        else:
            await interaction.response.send_message(embed=darknode_embed("❌ Start Failed", "Invalid container or already running."))

    @app_commands.command(name="stop", description="Stop a VPS instance")
    async def stop(self, interaction: discord.Interaction, container_name: str):
        if container_name in vps_instances and vps_instances[container_name]["status"] == "running":
            vps_instances[container_name]["status"] = "stopped"
            await interaction.response.send_message(embed=darknode_embed("⏹️ VPS Stopped", f"{container_name} has been stopped."))
        else:
            await interaction.response.send_message(embed=darknode_embed("❌ Stop Failed", "Invalid container or already stopped."))

    @app_commands.command(name="restart", description="Restart a VPS instance")
    async def restart(self, interaction: discord.Interaction, container_name: str):
        if container_name in vps_instances:
            vps_instances[container_name]["status"] = "running"
            await interaction.response.send_message(embed=darknode_embed("🔄 VPS Restarted", f"{container_name} has been restarted."))
        else:
            await interaction.response.send_message(embed=darknode_embed("❌ Restart Failed", "Invalid container."))

    @app_commands.command(name="tmate_info", description="Get SSH info for a VPS")
    async def tmate_info(self, interaction: discord.Interaction, container_name: str):
        if container_name in vps_instances:
            ssh_info = vps_instances[container_name]["ssh_info"]
            await interaction.response.send_message(embed=darknode_embed("🔧 SSH Info", f"`{ssh_info}`"))
        else:
            await interaction.response.send_message(embed=darknode_embed("❌ Not Found", "VPS not found."))

    @app_commands.command(name="clear_vps", description="Clear all VPS records (admin only)")
    async def clear_vps(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return
        vps_instances.clear()
        await interaction.response.send_message(embed=darknode_embed("🧹 VPS Cleared", "All VPS records have been cleared."))

    @app_commands.command(name="regen_ssh", description="Regenerate SSH for a VPS")
    async def regen_ssh(self, interaction: discord.Interaction, container_name: str):
        if container_name in vps_instances:
            new_ssh = f"ssh-regenerated-{datetime.datetime.now().strftime('%H%M%S')}"
            vps_instances[container_name]["ssh_info"] = new_ssh
            await interaction.response.send_message(embed=darknode_embed("🔑 SSH Regenerated", f"New SSH: `{new_ssh}`"))
        else:
            await interaction.response.send_message(embed=darknode_embed("❌ Not Found", "VPS not found."))

    @app_commands.command(name="restart_bot", description="Restart the bot")
    async def restart_bot(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return
        await interaction.response.send_message(embed=darknode_embed("🔄 Restarting", "Bot is restarting..."))
        os.execv(sys.executable, ['python3'] + sys.argv)

class SystemGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="system", description="System info commands")

    @app_commands.command(name="sysinfo", description="System information")
    async def sysinfo(self, interaction: discord.Interaction):
        info = get_sysinfo()
        await interaction.response.send_message(embed=darknode_embed("📊 System Info", f"```{info}```"))

    @app_commands.command(name="cpu", description="CPU usage")
    async def cpu(self, interaction: discord.Interaction):
        usage = psutil.cpu_percent(interval=1)
        await interaction.response.send_message(embed=darknode_embed("⚡ CPU Usage", f"{usage}%"))

    @app_commands.command(name="memory", description="Memory usage")
    async def memory(self, interaction: discord.Interaction):
        mem = psutil.virtual_memory()
        await interaction.response.send_message(embed=darknode_embed("💾 Memory Usage", f"{mem.percent}%"))

    @app_commands.command(name="disk", description="Disk usage")
    async def disk(self, interaction: discord.Interaction):
        d = psutil.disk_usage("/")
        await interaction.response.send_message(embed=darknode_embed("📀 Disk Usage", f"{d.percent}%"))

    @app_commands.command(name="uptime", description="System uptime")
    async def uptime(self, interaction: discord.Interaction):
        uptime_seconds = (datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).total_seconds()
        uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))
        await interaction.response.send_message(embed=darknode_embed("⏱️ Uptime", uptime_str))

    @app_commands.command(name="platform_info", description="Platform info")
    async def platform_info(self, interaction: discord.Interaction):
        info = (
            f"System: {platform.system()}\n"
            f"Node: {platform.node()}\n"
            f"Release: {platform.release()}\n"
            f"Version: {platform.version()}\n"
            f"Machine: {platform.machine()}\n"
            f"Processor: {platform.processor()}"
        )
        await interaction.response.send_message(embed=darknode_embed("💻 Platform Info", f"```{info}```"))

    @app_commands.command(name="processes", description="Running processes count")
    async def processes(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=darknode_embed("⚙️ Processes", f"{len(psutil.pids())}"))

    @app_commands.command(name="network", description="Network I/O")
    async def network(self, interaction: discord.Interaction):
        net = psutil.net_io_counters()
        info = f"Sent: {net.bytes_sent}\nReceived: {net.bytes_recv}"
        await interaction.response.send_message(embed=darknode_embed("🌐 Network I/O", f"```{info}```"))

class AdminGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="admin", description="Admin commands")

    @app_commands.command(name="allinfo", description="Show SSH, user, and container info")
    async def allinfo(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return
        ssh_info = get_ssh_info()
        user_info = get_user_info()
        container_info = get_container_info()
        embed = darknode_embed("📚 All Info", "")
        embed.add_field(name="SSH", value=f"```{ssh_info}```", inline=False)
        embed.add_field(name="Users", value=f"```{user_info}```", inline=False)
        embed.add_field(name="Containers", value=f"```{container_info}```", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shutdown", description="Shutdown the bot")
    async def shutdown(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return
        await interaction.response.send_message(embed=darknode_embed("🔌 Shutdown", "Bot is shutting down..."))
        await bot.close()

    @app_commands.command(name="env", description="Show environment variable")
    async def env(self, interaction: discord.Interaction, var_name: str):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return
        value = os.getenv(var_name, "Not Found")
        await interaction.response.send_message(embed=darknode_embed(f"🌐 ENV VAR {var_name}", value))

    @app_commands.command(name="clear", description="Clear recent messages")
    async def clear(self, interaction: discord.Interaction, amount: int = 5):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages permission.", ephemeral=True)
            return
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(embed=darknode_embed("🧹 Cleared", f"Deleted {len(deleted)} messages."), ephemeral=True)

    @app_commands.command(name="server_info", description="Server info")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        info = f"Name: {guild.name}\nID: {guild.id}\nMembers: {guild.member_count}\nChannels: {len(guild.channels)}"
        await interaction.response.send_message(embed=darknode_embed("🏰 Server Info", f"```{info}```"))

class UtilityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="utility", description="Utility commands")

    @app_commands.command(name="ping", description="Ping latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=darknode_embed("🏓 Pong!", f"{round(bot.latency*1000)}ms"))

    @app_commands.command(name="echo", description="Echo a message")
    async def echo(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(embed=darknode_embed("📣 Echo", message))

    @app_commands.command(name="time", description="Server time")
    async def time(self, interaction: discord.Interaction):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await interaction.response.send_message(embed=darknode_embed("🕰️ Time", now))

@bot.tree.command(name="help", description="Show help")
async def help(interaction: discord.Interaction):
    help_text = (
        "/vps deploy <container_name> <ram> <cpu> [target_user]\n"
        "/vps list\n"
        "/vps start <container_name>\n"
        "/vps stop <container_name>\n"
        "/vps restart <container_name>\n"
        "/vps tmate_info <container_name>\n"
        "/vps clear_vps\n"
        "/vps regen_ssh <container_name>\n"
        "/vps restart_bot\n"
        "/system sysinfo\n"
        "/system cpu\n"
        "/system memory\n"
        "/system disk\n"
        "/system uptime\n"
        "/system platform_info\n"
        "/system processes\n"
        "/system network\n"
        "/admin allinfo\n"
        "/admin shutdown\n"
        "/admin env <var_name>\n"
        "/admin clear [amount]\n"
        "/admin server_info\n"
        "/utility ping\n"
        "/utility echo <message>\n"
        "/utility time"
    )
    await interaction.response.send_message(embed=darknode_embed("🌟 Help - All Commands", help_text))

bot.tree.add_command(VPSGroup())
bot.tree.add_command(SystemGroup())
bot.tree.add_command(AdminGroup())
bot.tree.add_command(UtilityGroup())

bot.run(TOKEN)
