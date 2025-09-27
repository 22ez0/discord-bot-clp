import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
import io
from urllib.parse import urlparse, parse_qs
from typing import Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)

# --- CONFIGURAÇÕES DO BOT ---
# ATENÇÃO: Substitua estes IDs pelos seus IDs reais.
SPECIFIC_CHANNEL_ID = 1421251054032392222
VOICE_CHANNEL_ID = 1421364668546683083
ROLE_ID = 1421277379149697135
BOOSTER_CHANNEL_ID = 1421251143085850678
BOOSTER_ROLE_ID = 1421277205878673518
EMBED_COLOR = 0x020405
# URLs ESTÁVEIS DAS IMAGENS: Removido os parâmetros de expiração (?ex=...).
REPRESENTANTE_IMAGE_URL = "https://cdn.discordapp.com/attachments/1421251054032392222/1421490143075893368/IMG_0290.png"
BOOSTER_IMAGE_URL = "https://cdn.discordapp.com/attachments/1421251143085850678/1421541267027792084/IMG_0305.png?ex=68d968f9&is=68d81779&hm=8f55cec5b3ef521e43d85c93d2e7ac90a473e736d8822449a49ca573dcc254d3&"

# Intents necessários
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.presences = True

# --- VIEW PERSISTENTE COM BOTÃO ---

class StatusCheckView(discord.ui.View):
    def __init__(self, bot_instance=None):
        super().__init__(timeout=None)
        self.bot_instance = bot_instance
        # Lista de usuários que já clicaram no botão
        self.clicked_users = set()

    @discord.ui.button(
        emoji="<a:A_Tada:1418647260002254981>",
        label="url", 
        style=discord.ButtonStyle.grey,
        custom_id="status_check_button"
    )
    async def check_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild

        print(f"🔎 Usuário {user.name} clicou no botão de verificação")

        if not guild:
            print("❌ Guild não encontrada")
            await interaction.response.send_message(
                "❌ Erro: Guild não encontrada.", 
                ephemeral=True
            )
            return

        # Adicionar usuário à lista de quem já clicou
        self.clicked_users.add(user.id)
        # Também adicionar ao bot para persistência
        if self.bot_instance:
            self.bot_instance.clicked_users.add(user.id)

        # Buscar o membro para obter atividades
        member = guild.get_member(user.id)
        if not member:
            await interaction.response.send_message(
                "❌ Não foi possível encontrar suas informações. Tente novamente.", 
                ephemeral=True
            )
            return

        # Verificar se /clp está na barra de status
        has_clp = False
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name and '/clp' in activity.name.lower():
                has_clp = True
                break
            elif hasattr(activity, 'state') and getattr(activity, 'state', None) and '/clp' in str(getattr(activity, 'state')).lower():
                has_clp = True
                break
            elif hasattr(activity, 'name') and getattr(activity, 'name', None) and '/clp' in str(getattr(activity, 'name')).lower():
                has_clp = True
                break

        role = guild.get_role(ROLE_ID)
        if not role:
            await interaction.response.send_message(
                "❌ Erro: Cargo não encontrado.", 
                ephemeral=True
            )
            return

        if has_clp:
            # Adicionar cargo
            if role not in member.roles:
                await member.add_roles(role)
                await interaction.response.send_message(
                    "✅ **Parabéns!** Você recebeu o cargo de representante! 🎉\n"
                    "Agora você pode mover membros e silenciar nos canais de voz.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "ℹ️ Você já possui o cargo de representante!", 
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "❌ **Não encontrado!**\n"
                "Adicione **/clp** na sua barra de status personalizado e tente novamente.\n\n"
                "**Como fazer:**\n"
                "1. Clique no seu perfil\n"
                "2. Defina um status personalizado\n"
                "3. Digite **/clp** no campo de texto\n"
                "4. Clique novamente no botão", 
                ephemeral=True
            )

# --- CLASSE PRINCIPAL DO BOT ---

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        self.status_view = None  # Será inicializado no setup_hook
        self.clicked_users = set()  # Backup para persistência
        self.voice_reconnect_attempts = 0  # Contador de tentativas de reconexão
        self.max_reconnect_attempts = 5  # Máximo de tentativas
        self.last_voice_disconnect = 0.0  # Timestamp da última desconexão
        self.voice_reconnect_cooldown = 30  # Cooldown em segundos

    async def setup_hook(self):
        # Criar e adicionar a view persistente
        self.status_view = StatusCheckView(bot_instance=self)
        self.add_view(self.status_view)

        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            print(f"Sincronizados {len(synced)} comandos slash")
        except Exception as e:
            print(f"Erro ao sincronizar comandos: {e}")

    async def on_ready(self):
        print(f'{self.user} está online!')
        if self.user:
            print(f'ID do bot: {self.user.id}')

        # Entrar no canal de voz
        await self.join_voice_channel()

        # Definir atividade de streaming
        try:
            await self.change_presence(
                activity=discord.Streaming(
                    name="/clp",
                    url="https://twitch.tv/example"  # URL necessária para streaming
                ),
                status=discord.Status.online
            )
        except Exception as e:
            print(f"Erro ao definir atividade: {e}")

        # Iniciar monitoramento de status
        self.monitor_status.start()

    async def join_voice_channel(self, is_reconnect=False):
        """Entrar no canal de voz específico"""
        try:
            channel = self.get_channel(VOICE_CHANNEL_ID)
            if channel and isinstance(channel, discord.VoiceChannel):
                # Verificar se já está conectado ao canal correto
                voice_client = channel.guild.voice_client
                if voice_client and voice_client.channel:
                    current_channel = voice_client.channel
                    if isinstance(current_channel, discord.VoiceChannel) and current_channel.id == VOICE_CHANNEL_ID:
                        print(f"Já conectado ao canal de voz correto: {channel.name}")
                        if is_reconnect:
                            self.voice_reconnect_attempts = 0  # Reset contador se já conectado
                        return
                    else:
                        # Desconectar do canal atual e conectar ao correto
                        await voice_client.disconnect(force=True)
                        await asyncio.sleep(2)  # Pequeno delay após desconexão

                await channel.connect(timeout=15.0, reconnect=False)
                print(f"✅ Conectado ao canal de voz: {channel.name}")
                if is_reconnect:
                    self.voice_reconnect_attempts = 0  # Reset contador em sucesso
                    print(f"🔄 Reconexão bem-sucedida após {self.voice_reconnect_attempts} tentativas")
            else:
                print(f"❌ Canal de voz {VOICE_CHANNEL_ID} não encontrado")
                raise Exception(f"Canal {VOICE_CHANNEL_ID} não encontrado")
        except asyncio.TimeoutError:
            print("⏱️ Timeout ao conectar ao canal de voz")
            # Não incrementar aqui se for reconexão, será feito em voice_reconnect_loop
            raise
        except Exception as e:
            print(f"❌ Erro ao conectar ao canal de voz: {e}")
            # Não incrementar aqui se for reconexão, será feito em voice_reconnect_loop
            raise

    async def voice_reconnect_loop(self):
        """Loop de reconexão com tentativas limitadas"""
        while self.voice_reconnect_attempts < self.max_reconnect_attempts:
            # Calcular delay progressivo: 15s, 30s, 60s, 120s, 300s
            delays = [15, 30, 60, 120, 300]
            delay = delays[min(self.voice_reconnect_attempts, len(delays) - 1)]
            
            print(f"🔄 Tentativa {self.voice_reconnect_attempts + 1}/{self.max_reconnect_attempts} em {delay}s...")
            await asyncio.sleep(delay)
            
            try:
                await self.join_voice_channel(is_reconnect=True)
                print("✅ Reconexão bem-sucedida!")
                return  # Sucesso, sair do loop
            except Exception as e:
                print(f"❌ Falha na reconexão: {e}")
                self.voice_reconnect_attempts += 1  # Incrementar apenas aqui
                
                if self.voice_reconnect_attempts >= self.max_reconnect_attempts:
                    print("💔 Todas as tentativas de reconexão falharam. Bot ficará desconectado do canal de voz.")
                    return

    @tasks.loop(seconds=15)  # Verificar a cada 15 segundos (mais frequente)
    async def monitor_status(self):
        """Monitorar mudanças no status personalizado dos usuários"""
        try:
            print(f"🔄 Monitoramento ativo - Usuários cadastrados: {len(self.clicked_users)}")

            for guild in self.guilds:
                role = guild.get_role(ROLE_ID)
                if not role:
                    print(f"❌ Cargo não encontrado: {ROLE_ID}")
                    continue

                # Verificar apenas usuários cadastrados
                monitored_users = [member for member in guild.members if member.id in self.clicked_users]
                print(f"📋 Monitorando {len(monitored_users)} usuários nesta guild")

                for member in monitored_users:
                    try:
                        # Verificar se /clp está no status personalizado
                        has_clp = False
                        custom_activities = []

                        # Buscar atividades customizadas
                        for activity in member.activities:
                            if isinstance(activity, discord.CustomActivity):
                                custom_activities.append(activity)
                                if activity.name and '/clp' in activity.name.lower():
                                    has_clp = True
                                    break

                        # Log de debug
                        status_info = f"{member.display_name}: "
                        if custom_activities:
                            for act in custom_activities:
                                status_info += f"'{act.name}' "
                        else:
                            status_info += "sem status personalizado"
                        print(f"👤 {status_info}")

                        # Gerenciar cargo baseado no status
                        has_role = role in member.roles

                        if has_clp and not has_role:
                            await member.add_roles(role)
                            print(f"✅ Cargo ADICIONADO para {member.display_name}")
                        elif not has_clp and has_role:
                            await member.remove_roles(role)
                            print(f"❌ Cargo REMOVIDO de {member.display_name}")
                        elif has_clp and has_role:
                            print(f"✅ {member.display_name} já tem o cargo")
                        elif not has_clp and not has_role:
                            print(f"ℹ️ {member.display_name} sem /clp e sem cargo")

                    except Exception as member_error:
                        print(f"❌ Erro ao processar {member.display_name}: {member_error}")

        except Exception as e:
            print(f"❌ Erro geral no monitoramento: {e}")
            import traceback
            traceback.print_exc()

    @monitor_status.before_loop
    async def before_monitor_status(self):
        await self.wait_until_ready()

# Instanciar o bot
bot = DiscordBot()

# --- COMANDOS SLASH ---

@bot.tree.command(name="url", description="Enviar informações sobre representante")
@app_commands.describe()
async def url_command(interaction: discord.Interaction):
    """Comando /url para enviar embed com informações do representante"""
    channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else 'DM'
    print(f" Comando /url executado por {interaction.user.name} no canal {channel_name}")

    # Verificar se o canal é o correto
    if not interaction.channel or interaction.channel.id != SPECIFIC_CHANNEL_ID:
        print(f"❌ Canal incorreto: {interaction.channel.id if interaction.channel else 'None'}, esperado: {SPECIFIC_CHANNEL_ID}")
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado em um canal específico.", 
            ephemeral=True
        )
        return

    print("✅ Canal correto, criando embed...")

    # Criar embed
    embed = discord.Embed(
        title="<:verify:1421493602684768326> _**SEJA REPRESENTANTE**_",
        description=(
            "adicione a url _**/clp**_ na sua barra de status personalizado e libere os seguintes recursos:\n\n"
            "• mover membros (mov call): permite que você transfira outros usuários entre os canais de voz.\n"
            "• silenciar (mutar): confere a você a permissão de mutar membros nos canais de voz.\n\n"
            "_**importante:**_ o uso indevido desses comandos resultará em punição."
        ),
        color=EMBED_COLOR
    )

    # Adicionar imagem (USANDO A URL ESTÁVEL CORRIGIDA)
    try:
        embed.set_image(url=REPRESENTANTE_IMAGE_URL)
        print(f"✅ Imagem adicionada ao embed: {REPRESENTANTE_IMAGE_URL}")
    except Exception as e:
        print(f"❌ Erro ao adicionar imagem: {e}")
        pass

    # Usar a view persistente do bot
    if not bot.status_view:
        print("🔄 Criando nova view persistente")
        bot.status_view = StatusCheckView(bot_instance=bot)
        bot.add_view(bot.status_view)
    else:
        print("✅ Usando view persistente existente")

    print("📤 Enviando embed com botão...")
    await interaction.response.send_message(embed=embed, view=bot.status_view)
    print("✅ Embed enviado com sucesso!")

@bot.tree.command(name="booster", description="Enviar informações sobre boosters")
@app_commands.describe()
async def booster_command(interaction: discord.Interaction):
    """Comando /booster para enviar embed com informações dos boosters"""
    channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else 'DM'
    print(f"🎉 Comando /booster executado por {interaction.user.name} no canal {channel_name}")

    # Verificar se o canal é o correto para boosters
    if not interaction.channel or interaction.channel.id != BOOSTER_CHANNEL_ID:
        print(f"❌ Canal incorreto: {interaction.channel.id if interaction.channel else 'None'}, esperado: {BOOSTER_CHANNEL_ID}")
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado em um canal específico.", 
            ephemeral=True
        )
        return

    print("✅ Canal correto, criando embed de booster...")

    # Criar embed de booster
    embed = discord.Embed(
        title="<a:Nitro_boosting_level:1421543769282445433> _**BOOSTER'S**_ <a:alert_white:1421543759467774063>",
        description=(
            "_de boost em nossa comunidade e faça dela cada vez maior!_\n"
            "> de cortesia você ganha o benefício:\n\n"
            "<:gh_3BlackArrow:1421493564310945903> _**tela:**_ como booster, você garante a aquisição do cargo tela, que permite a você iniciar transmissões de tela e câmera em canais de voz.\n\n"
            "<a:alert_white:1421543759467774063> _**importante:**_ sujeito a punição por transmissões inadequadas."
        ),
        color=EMBED_COLOR
    )

    # Adicionar imagem (USANDO A URL ESTÁVEL CORRIGIDA)
    try:
        embed.set_image(url=BOOSTER_IMAGE_URL)
        print(f"✅ Imagem adicionada ao embed: {BOOSTER_IMAGE_URL}")
    except Exception as e:
        print(f"❌ Erro ao adicionar imagem: {e}")
        pass

    print("📤 Enviando embed de booster...")
    await interaction.response.send_message(embed=embed)
    print("✅ Embed de booster enviado com sucesso!")

@bot.tree.command(name="avs", description="Enviar mensagem como webhook (com anexos)")
@app_commands.describe(
    canal="Canal onde enviar a mensagem",
    mensagem="Texto da mensagem (opcional se tiver anexo)",
    anexo="Arquivo para enviar (imagem, documento, etc.)"
)
async def avs_command(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    mensagem: Optional[str] = None,
    anexo: Optional[discord.Attachment] = None
):
    """Comando /avs para enviar mensagens como webhook com anexos"""
    
    # Verificar se há mensagem ou anexos
    if not mensagem and not anexo:
        await interaction.response.send_message(
            "❌ Você precisa fornecer uma mensagem ou anexar um arquivo!", 
            ephemeral=True
        )
        return

    try:
        # Preparar arquivo para envio se houver
        file_to_send = None
        if anexo:
            try:
                # Baixar o arquivo
                file_data = await anexo.read()
                # Criar objeto discord.File
                file_to_send = discord.File(
                    fp=io.BytesIO(file_data),
                    filename=anexo.filename
                )
                print(f"✅ Anexo processado: {anexo.filename} ({anexo.size} bytes)")
            except Exception as e:
                print(f"❌ Erro ao processar anexo {anexo.filename}: {e}")
                await interaction.response.send_message(
                    f"❌ Erro ao processar o arquivo {anexo.filename}: {str(e)}", 
                    ephemeral=True
                )
                return

        # Buscar ou criar webhook no canal
        webhooks = await canal.webhooks()
        webhook = None
        
        # Procurar webhook existente do bot
        for wh in webhooks:
            if wh.user == bot.user:
                webhook = wh
                break
        
        # Criar webhook se não existir
        if not webhook:
            webhook = await canal.create_webhook(
                name=f"AVS Webhook",
                reason="Webhook criado pelo comando /avs"
            )
            print(f"✅ Webhook criado no canal {canal.name}")
        
        # Enviar mensagem através do webhook
        if mensagem and file_to_send:
            sent_message = await webhook.send(
                content=mensagem,
                file=file_to_send,
                username=interaction.user.display_name,
                avatar_url=interaction.user.display_avatar.url,
                wait=True
            )
        elif mensagem:
            sent_message = await webhook.send(
                content=mensagem,
                username=interaction.user.display_name,
                avatar_url=interaction.user.display_avatar.url,
                wait=True
            )
        elif file_to_send:
            sent_message = await webhook.send(
                file=file_to_send,
                username=interaction.user.display_name,
                avatar_url=interaction.user.display_avatar.url,
                wait=True
            )

        # Confirmação de sucesso
        success_parts = [f"✅ Mensagem enviada para {canal.mention}!"]
        if file_to_send and anexo:
            success_parts.append(f"📎 Arquivo anexado: {anexo.filename}")
        
        await interaction.response.send_message(
            "\n".join(success_parts), 
            ephemeral=True
        )

    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ Erro ao enviar mensagem: {str(e)}", 
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erro inesperado: {str(e)}", 
            ephemeral=True
        )

@bot.event
async def on_voice_state_update(member, before, after):
    """Reconectar ao canal de voz se desconectado"""
    if bot.user and member.id == bot.user.id and after.channel is None:
        # Bot foi desconectado do canal de voz
        print("🔌 Bot desconectado do canal de voz")
        
        # Verificar se excedeu tentativas máximas
        if bot.voice_reconnect_attempts >= bot.max_reconnect_attempts:
            print(f"❌ Máximo de {bot.max_reconnect_attempts} tentativas de reconexão atingido. Parando tentativas.")
            return
        
        # Verificar cooldown desde última desconexão
        import time
        current_time = time.time()
        if current_time - bot.last_voice_disconnect < bot.voice_reconnect_cooldown:
            print(f"⏳ Cooldown ativo. Aguardando {bot.voice_reconnect_cooldown} segundos entre tentativas.")
            return
        
        bot.last_voice_disconnect = current_time
        
        # Iniciar task de reconexão com retry loop
        asyncio.create_task(bot.voice_reconnect_loop())

@bot.event
async def on_member_update(before, after):
    """Detectar quando alguém boostar o servidor e dar o cargo automaticamente"""
    try:
        # Verificar se o membro começou a booster o servidor
        was_booster = before.premium_since is not None
        is_booster = after.premium_since is not None

        if not was_booster and is_booster:
            # Membro começou a booster agora
            print(f"🎉 {after.display_name} começou a boostar o servidor!")

            # Buscar o cargo de booster
            guild = after.guild
            booster_role = guild.get_role(BOOSTER_ROLE_ID)

            if booster_role:
                # Adicionar o cargo
                if booster_role not in after.roles:
                    try:
                        await after.add_roles(booster_role)
                        print(f"✅ Cargo de booster ADICIONADO automaticamente para {after.display_name}")
                    except discord.Forbidden:
                        print(f"❌ Sem permissão para adicionar cargo de booster para {after.display_name}")
                    except discord.HTTPException as e:
                        print(f"❌ Erro HTTP ao adicionar cargo de booster para {after.display_name}: {e}")
                else:
                    print(f"ℹ️ {after.display_name} já possui o cargo de booster")
            else:
                print(f"❌ Cargo de booster não encontrado (ID: {BOOSTER_ROLE_ID})")

        elif was_booster and not is_booster:
            # Membro parou de booster
            print(f"💔 {after.display_name} parou de boostar o servidor")

            # Buscar o cargo de booster
            guild = after.guild
            booster_role = guild.get_role(BOOSTER_ROLE_ID)

            if booster_role and booster_role in after.roles:
                # Remover o cargo
                try:
                    await after.remove_roles(booster_role)
                    print(f"❌ Cargo de booster REMOVIDO automaticamente de {after.display_name}")
                except discord.Forbidden:
                    print(f"❌ Sem permissão para remover cargo de booster de {after.display_name}")
                except discord.HTTPException as e:
                    print(f"❌ Erro HTTP ao remover cargo de booster de {after.display_name}: {e}")

    except Exception as e:
        print(f"❌ Erro ao processar atualização de booster: {e}")
        import traceback
        traceback.print_exc()

# --- EXECUÇÃO DO BOT ---

if __name__ == "__main__":
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("❌ BOT_TOKEN não encontrado nas variáveis de ambiente! Certifique-se de que está definido no Replit.")
        exit(1)

    try:
        bot.run(token)
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")
