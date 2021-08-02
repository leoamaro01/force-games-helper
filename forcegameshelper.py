import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
import os

class RegisteredChannel:
    def __init__(self, id,template = None, template_picture = None):
        self.chat_id = id
        self.template = template
        self.template_picture = template_picture

PORT = int(os.environ.get('PORT', 8443))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1609173394:AAH4V-ShZIGXOBE9JPOUg3wVN_Q3BycCZG4'
STATUS_ID = "fgh_status"
CANCEL_MARKUP = "🔙 Atrás 🔙"
REGISTER_MARKUP = "➕ Registrar Canal ➕"
UNREGISTER_MARKUP = "✖️ Cancelar Registro de Canal ✖️"
CUSTOMIZE_MARKUP = "⚙ Configurar Canal Registrado ⚙"
CHANGE_TEMPLATE_MARKUP = "📋 Cambiar Plantilla 📋"
CHANGE_TEMPLATE_PICTURE_MARKUP = "📷 Cambiar Foto de Plantilla 📷"
CONTEXT_DATA_ID = "fgh_context_data"

admin_chat_id = -1

registered_channels = {}

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')
    if len(context.args) >= 2 and context.args[0] == "admin" and context.args[1] == TOKEN:
        update.message.reply_text("Logged in as Admin!")
        global admin_chat_id
        admin_chat_id = update.message.chat.id

    go_to_base(update, context)

"""
set reply markups for:
    register channel (requires sudo)
    customize channel (requires sudo)
    unregister channel (requires sudo)
"""
def go_to_base(update, context):
    markup = ReplyKeyboardMarkup([
        [CUSTOMIZE_MARKUP],
        [REGISTER_MARKUP, UNREGISTER_MARKUP]
    ])
    context.message.reply_text(text="Menú 🤓\nPuedes usar /cancel en cualquier momento para volver aquí :D",
                             reply_markup=markup, one_time_keyboard=True)
    context.chat_data[STATUS_ID] = "idle"

"""
ask the user for the channel username (in the future will add inline buttons for the channels
the user already registered or customized) 
"""
def request_customize_channel(update, context):
    update.message.reply_text("¿Cuál es la @ del canal que desea configurar? 🧐")
    context.chat_data[STATUS_ID] = "requested_customization"

"""if the user is administrator then present reply
markups for the different settings
change template
change template picture"""
def customize_channel(update, context):
    username = update.message.text
    if username in registered_channels and is_admin(context.bot.get_chat(username), update.message.from_user.id):
        markup = ReplyKeyboardMarkup(
            [
            [CHANGE_TEMPLATE_MARKUP],
            [CHANGE_TEMPLATE_PICTURE_MARKUP],
            [CANCEL_MARKUP]
            ]
        )
        context.message.reply_text(text="¿Qué desea configurar? 🧐",
                                   reply_markup=markup, one_time_keyboard=True)
        context.chat_data[STATUS_ID] = "customizing"
        context.chat_data[CONTEXT_DATA_ID] = username
    else:
        update.message.reply_text("El canal " + username + " no está registrado o no eres administrador. 😗")
        go_to_base(update, context)

def request_change_template(update, context):
    update.message.reply_text("Envíe la nueva plantilla, debe contener el texto \"$plantilla$\" que será donde se colocará el resumen 🤖")
    context.chat_data[STATUS_ID] = "requested_template"

def change_template(update, context):
    if "$plantilla$" in update.message.text:
        registered_channels[context.chat_data[CONTEXT_DATA_ID]].template = update.message.text
        update.message.reply_text("Plantilla cambiada! :3")
        go_to_base(update, context)
    else:
        update.message.reply_text("Plantilla incompleta! Debe contener el texto $plantilla$ que sera sustituido por los contenidos de la plantilla. 😐")
        go_to_base(update, context)

def request_change_template_picture(update, context):
    update.message.reply_text("Envíe la nueva foto de plantilla. 📸")
    context.chat_data[STATUS_ID] = "requested_template_picture"

def change_template_picture(update, context):
    registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_picture = update.message.photo
    update.message.reply_text("Foto establecida! :3")
    go_to_base(update, context)

def request_register_channel(update, context):
    update.message.reply_text("Diga la @ del canal que desea registrar :D")
    context.chat_data[STATUS_ID] = "requested_register"

def register_channel(update, context):
    channel = context.bot.get_chat(update.message.text)
    if channel in registered_channels and is_admin(channel, update.message.from_user.id):
        registered_channels[channel] = RegisteredChannel(id=channel.id)
        update.message.reply_text("Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text("No se encontró el canal o no eres administrador de este D:")
        go_to_base(update, context)

def request_unregister_channel(update, context):
    update.message.reply_text("Diga la @ del canal que desea sacar del registro :(")
    context.chat_data[STATUS_ID] = "requested_unregister"

def unregister_channel(update, context):
    channel = context.bot.get_chat(update.message.text)
    if channel is not None and is_admin(channel, update.message.from_user.id):
        registered_channels[channel] = RegisteredChannel(id=channel.id)
        update.message.reply_text("Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text("Canal no encontrado o no eres admin D:<")
        go_to_base(update, context)

def is_admin(from_chat, user_id):
    if from_chat.type == "channel":
        member = from_chat.get_member(user_id)
        if member is not None:
            if member in from_chat.get_administrators():
                return true
            else:
                update.message.reply_text("No eres administrador de ese canal :/ eres tonto o primo de JAVIER?")
                return false
        else:
            update.message.reply_text("No perteneces a ese canal :/ eres tonto o primo de JAVIER?")
            return false
    else:
        update.message.reply_text("Ese mensaje no viene de un canal :/ eres tonto o primo de JAVIER?")
        return false

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('No implementado uwu')

def process_private_message(update, context):
    if STATUS_ID in context.chat_data:
        status = context.chat_data[STATUS_ID]
        text = update.message.text
        if text == CANCEL_MARKUP:
            go_to_base(update, context)
        elif status == "idle":
            if text == CUSTOMIZE_MARKUP:
                request_customize_channel(update, context)
            elif text == REGISTER_MARKUP:
                request_register_channel(update, context)
            elif text == UNREGISTER_MARKUP:
                request_unregister_channel(update, context)
            else:
                update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto XD")
        elif status == "requested_customization":
            customize_channel(update, context)
        elif status == "customizing":
            if text == CHANGE_TEMPLATE_MARKUP:
                request_change_template(update, context)
            elif text == CHANGE_TEMPLATE_PICTURE_MARKUP:
                request_change_template_picture(update, context)
        elif status == "requested_template":
            change_template(update, context)
        elif status == "requested_register":
            register_channel(update, context)
        elif status == "requested_unregister":
            unregister_channel(update, context)

def process_private_photo(update, context):
    if STATUS_ID in context.chat_data:
        status = context.chat_data[STATUS_ID]
        if status == "requested_template_picture":
            change_template_picture(update, context)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("cancel", go_to_base))
    dp.add_handler(CommandHandler("help", help))

    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, process_private_message))
    dp.add_handler(MessageHandler(Filters.photo & Filters.chat_type.private, process_private_photo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook('https://forcegameshelper.herokuapp.com/' + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()