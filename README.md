# Discord Bot - Sistema de Representantes e Boosters

Bot Discord automatizado para gerenciamento de cargos de representantes e boosters com integração de canal de voz.

## 🎯 Funcionalidades

- **Sistema de Representantes**: Usuários que adicionam `/clp` no status personalizado recebem cargo de representante
- **Gerenciamento de Boosters**: Atribuição automática de cargo para boosters do servidor
- **Conexão Automática ao Canal de Voz**: Bot mantém presença constante em canal de voz específico
- **Sistema de Reconexão Inteligente**: Reconecta automaticamente com sistema anti-loop
- **Comandos Slash**: Interface moderna com comandos `/url`, `/booster` e `/avs`

## 🚀 Deploy no Render

### 1. Preparação do Repositório

1. **Clone este repositório** ou faça upload dos arquivos para seu GitHub
2. **Configure as variáveis de ambiente** no arquivo `.env` (local) ou diretamente no Render

### 2. Configuração no Render

1. **Acesse** [render.com](https://render.com) e faça login
2. **Conecte seu repositório** GitHub
3. **Crie um novo Worker Service** (não Web Service!)
4. **Configure as variáveis de ambiente**:

```
BOT_TOKEN=seu_token_do_discord_aqui
SPECIFIC_CHANNEL_ID=1421251054032392222
VOICE_CHANNEL_ID=1421364668546683083
ROLE_ID=1421277379149697135
BOOSTER_CHANNEL_ID=1421251143085850678
BOOSTER_ROLE_ID=1421277205878673518
```

### 3. Obter Token do Bot Discord

1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie uma nova aplicação ou selecione uma existente
3. Vá para **Bot** → **Token** → **Copy**
4. Cole o token na variável `BOT_TOKEN` no Render

### 4. Configurar Permissões do Bot

O bot precisa das seguintes permissões no Discord:
- ✅ Read Messages/View Channels
- ✅ Send Messages  
- ✅ Use Slash Commands
- ✅ Connect (Voice)
- ✅ Speak (Voice)
- ✅ Manage Roles
- ✅ Read Message History
- ✅ Embed Links
- ✅ Attach Files
- ✅ Manage Webhooks

## 🔧 Configuração Local (Desenvolvimento)

### Pré-requisitos
- Python 3.8+
- Token do bot Discord

### Instalação

1. **Clone o repositório**:
```bash
git clone <seu-repositorio>
cd discord-bot
```

2. **Instale as dependências**:
```bash
pip install -r requirements.txt
```

3. **Configure as variáveis de ambiente**:
```bash
cp .env.example .env
# Edite o arquivo .env com seus valores
```

4. **Execute o bot**:
```bash
python main.py
```

## 📁 Estrutura do Projeto

```
discord-bot/
├── main.py              # Código principal do bot
├── requirements.txt     # Dependências Python
├── render.yaml         # Configuração do Render
├── .env.example        # Exemplo de variáveis de ambiente
├── .gitignore          # Arquivos ignorados pelo Git
└── README.md           # Este arquivo
```

## 🔍 Solução de Problemas

### Bot não conecta ao canal de voz
- Verifique se o `VOICE_CHANNEL_ID` está correto
- Confirme se o bot tem permissões de voz no canal
- Verifique os logs para erros específicos

### Comandos slash não funcionam
- Execute `/url` apenas no canal configurado em `SPECIFIC_CHANNEL_ID`
- Execute `/booster` apenas no canal configurado em `BOOSTER_CHANNEL_ID`
- Aguarde alguns minutos para sincronização dos comandos

### Erro de reconexão em loop
- O sistema anti-loop foi implementado com:
  - Máximo 5 tentativas de reconexão
  - Delays progressivos (15s, 30s, 60s, 120s, 300s)
  - Cooldown de 30s entre desconexões

## 📝 Comandos Disponíveis

- `/url` - Envia informações sobre como se tornar representante
- `/booster` - Envia informações sobre benefícios de boosters  
- `/avs <canal> <mensagem> [anexo]` - Envia mensagem como webhook

## 🔄 Sistema de Monitoramento

O bot monitora automaticamente:
- Status personalizados dos usuários para `/clp`
- Mudanças de boost no servidor
- Conexão com canal de voz
- Atribuição/remoção automática de cargos

## 🛡️ Recursos de Segurança

- ✅ Verificação de permissões por canal
- ✅ Logs detalhados de todas as operações
- ✅ Sistema anti-spam com cooldowns
- ✅ Tratamento de erros robusto
- ✅ Variáveis de ambiente para dados sensíveis