import logging
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
import os

class RegisteredChannel:
    def __init__(self, id,template = None, template_picture = None, template_time_dif = 12):
        self.chat_id = id
        self.template = template
        self.template_picture = template_picture
        self.template_time_dif = template_time_dif
    def __str__(self):
        return  "chat_id={} template={} template_time_dif={} template_picture={}".format(self.chat_id, self.template, self.template_time_dif, self.template_picture)

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
SEE_TEMPLATE_MARKUP = "📃 Ver plantilla actual 📃"
SEND_NOW_MARKUP = "✅ Enviar resumen al canal despues del próximo mensaje ✅"
SEE_TEMPLATE_PICTURE_MARKUP = "📹 Ver foto de plantilla actual 📹"
CHANGE_SUMMARY_TIME_MARKUP = "🕑 Cambiar horario de los resumenes 🕑"
CHANGE_TEMPLATE_PICTURE_MARKUP = "📷 Cambiar Foto de Plantilla 📷"
CONTEXT_DATA_ID = "fgh_context_data"
LAST_SUMMARY_ID = "fgh_last_summary"
LAST_SUMMARY_TIME = "fgh_last_summary_time"
LAST_SUMMARY_MESSAGES_ID = "fgh_last_summary_messages"
SAVED_MESSAGES_ID = "fgh_saved_messages"

admin_chat_id = -1

registered_channels = {}

def start(update, context):
    """Send a message when the command /start is issued."""
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
    ], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(text="Menú 🤓\nPuedes usar /cancel en cualquier momento para volver aquí :D",
                             reply_markup=markup)
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
                [SEND_NOW_MARKUP],
                [CHANGE_TEMPLATE_MARKUP, SEE_TEMPLATE_MARKUP],
                [CHANGE_TEMPLATE_PICTURE_MARKUP, SEE_TEMPLATE_PICTURE_MARKUP],
                [CHANGE_SUMMARY_TIME_MARKUP]
                [CANCEL_MARKUP]
            ], resize_keyboard=True, one_time_keyboard=True
        )
        update.message.reply_text(text="¿Qué desea configurar? 🧐", reply_markup=markup)
        context.chat_data[STATUS_ID] = "customizing"
        context.chat_data[CONTEXT_DATA_ID] = username
    else:
        update.message.reply_text("El canal " + username + " no está registrado o no eres administrador. 😗")
        go_to_base(update, context)

def print_debug(update, context):
    if admin_chat_id == update.message.chat.id:
        for channel in registered_channels:
            update.message.reply_text(str(channel))

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

def see_template(update, context):
    update.message.reply_text(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template)

def request_change_template_picture(update, context):
    update.message.reply_text("Envíe la nueva foto de plantilla. 📸")
    context.chat_data[STATUS_ID] = "requested_template_picture"

def change_template_picture(update, context):
    registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_picture = update.message.photo
    update.message.reply_text("Foto establecida! :3")
    go_to_base(update, context)

def see_template_picture(update, context):
    update.message.reply_photo(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_picture)

def request_change_summary_time(update, context):
    update.message.reply_text("Diga cada cuántas horas debo enviar el resumen, sólo envíe el numero\nejemplo: \"12\"\nValor actual:{}".format(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_time_dif))
    context.chat_data[STATUS_ID] = "requested_summary_time"

def change_summary_time(update, context):
    try:
        time = int(update.message.text)
        if time <= 0:
            update.message.reply_text("Eso no es un número válido :/")
        else:
            registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_time_dif = time
            update.message.reply_text("Tiempo entre resumenes cambiado :3")
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
    finally:
        go_to_base(update, context)

def request_register_channel(update, context):
    update.message.reply_text("Diga la @ del canal que desea registrar :D")
    context.chat_data[STATUS_ID] = "requested_register"

def register_channel(update, context):
    try:
        channel = context.bot.get_chat(update.message.text)
    except TelegramError:
        update.message.reply_text("No se encontró el canal :|")
        go_to_base(update, context)
        return

    if is_admin(channel, update.message.from_user.id):
        registered_channels[update.message.text] = RegisteredChannel(id=channel.id)
        update.message.reply_text("Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text("No eres administrador de este canal D:")
        go_to_base(update, context)

def request_unregister_channel(update, context):
    update.message.reply_text("Diga la @ del canal que desea sacar del registro :(")
    context.chat_data[STATUS_ID] = "requested_unregister"

def unregister_channel(update, context):
    channel = update.message.text
    if channel in registered_channels and is_admin(context.bot.get_chat(channel), update.message.from_user.id):
        registered_channels.pop(channel)
        update.message.reply_text("Canal eliminado del registro satisfactoriamente ;-;")
        go_to_base(update, context)
    else:
        update.message.reply_text("Canal no encontrado o no eres admin D:<")
        go_to_base(update, context)

def send_summary_now(update, context):
    update.message.reply_text("El resumen sera enviado luego del próximo mensaje al canal :D")
    registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_time_dif *= -1

def is_admin(from_chat, user_id):
    if from_chat.type == "channel":
        member = from_chat.get_member(user_id)
        if member is not None:
            if member in from_chat.get_administrators():
                return True
            else:
                update.message.reply_text("No eres administrador de ese canal :/ eres tonto o primo de JAVIER?")
                return False
        else:
            update.message.reply_text("No perteneces a ese canal :/ eres tonto o primo de JAVIER?")
            return False
    else:
        update.message.reply_text("Ese mensaje no viene de un canal :/ eres tonto o primo de JAVIER?")
        return False

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
            elif text == SEE_TEMPLATE_MARKUP:
                see_template(update, context)
            elif text == SEE_TEMPLATE_PICTURE_MARKUP:
                see_template_picture(update, context)
            elif text == CHANGE_SUMMARY_TIME_MARKUP:
                request_change_summary_time(update, context)
            elif text == SEND_NOW_MARKUP:
                send_summary_now(update, context)
        elif status == "requested_template":
            change_template(update, context)
        elif status == "requested_register":
            register_channel(update, context)
        elif status == "requested_unregister":
            unregister_channel(update, context)
        elif status == "requested_summary_time":
            change_summary_time(update, context)

def process_private_photo(update, context):
    if STATUS_ID in context.chat_data:
        status = context.chat_data[STATUS_ID]
        if status == "requested_template_picture":
            change_template_picture(update, context)

def process_channel_photo(update, context):
    if get_at_username(update.message.chat.username) not in registered_channels:
        return

    add_to_saved_messages(update, context)

    if LAST_SUMMARY_ID in context.chat_data and context.chat_data[LAST_SUMMARY_ID] is not None:
        add_to_last_summary_messages(update, context)
        context.bot.edit_message_text(chat_id=update.message.chat.id, message_id=context.chat_data[LAST_SUMMARY_ID],
                                      text=get_template_string(update.message.chat, context.chat_data[LAST_SUMMARY_MESSAGES_ID]))

    try_post_summary(update, context)

def process_channel_message(update, context):
    if get_at_username(update.message.chat.username) not in registered_channels:
        return

    add_to_saved_messages(update, context)

    if LAST_SUMMARY_ID in context.chat_data and context.chat_data[LAST_SUMMARY_ID] is not None:
        add_to_last_summary_messages(update, context)
        context.bot.edit_message_text(chat_id=update.message.chat.id, message_id=context.chat_data[LAST_SUMMARY_ID],
                                      text=get_template_string(update.message.chat, context.chat_data[LAST_SUMMARY_MESSAGES_ID]))
    try_post_summary(update, context)

def try_post_summary(update, context):
    atusername = get_at_username(update.message.chat.username)

    if LAST_SUMMARY_TIME in context.chat_data and context.chat_data[LAST_SUMMARY_TIME] is not None:
        delta = datetime.now() - context.chat_data[LAST_SUMMARY_TIME]
        if delta / timedelta(hours=1) >= registered_channels[atusername].template_time_dif:
            if registered_channels[atusername].template_time_dif < 0:
                registered_channels[atusername].template_time_dif *= -1

            reg_channel = registered_channels[atusername]
            if reg_channel.template_picture is not None:
                update.message.reply_photo(registered_channels[atusername].template_picture)
            if reg_channel.template is not None and reg_channel.template != "":
                context.chat_data[LAST_SUMMARY_ID] = update.message.reply_text(get_template_string(update.message.chat, context.chat_data[SAVED_MESSAGES_ID])).message_id

            context.chat_data[LAST_SUMMARY_MESSAGES_ID] = context.chat_data[SAVED_MESSAGES_ID]
            context.chat_data[SAVED_MESSAGES_ID] = []
            context.chat_data[LAST_SUMMARY_TIME] = datetime.now()

def add_to_saved_messages(update, context):
    if SAVED_MESSAGES_ID in context.chat_data and context.chat_data[SAVED_MESSAGES_ID] is not None:
        context.chat_data[SAVED_MESSAGES_ID].append(update.message.message_id)
    else:
        context.chat_data[SAVED_MESSAGES_ID] = [update.message.message_id]

def add_to_last_summary_messages(update, context):
    if LAST_SUMMARY_MESSAGES_ID in context.chat_data and context.chat_data[LAST_SUMMARY_MESSAGES_ID] is not None and len(context.chat_data[LAST_SUMMARY_MESSAGES_ID]) > 0:
        context.chat_data[LAST_SUMMARY_MESSAGES_ID].append(update.message.message_id)

def get_template_string(chat, messages_id):
    return registered_channels[get_at_username(chat.username)].template.replace(
        "$plantilla$",
        "\n".join([get_message_link(chat, id) for id in messages_id]))

def get_message_link(chat, message_id):
    return chat.link + "/" + str(id)

def get_at_username(username):
    if username[0] == "@":
        return username
    else:
        return "@" + username

def get_no_at_username(username):
    if username[0] == "@":
        return username[1:]
    else:
        return  username

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
    dp.add_handler(CommandHandler("debug", print_debug))

    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, process_private_message))
    dp.add_handler(MessageHandler(Filters.photo & Filters.chat_type.private, process_private_photo))

    dp.add_handler(MessageHandler(Filters.chat_type.channel & Filters.photo, process_channel_photo))
    dp.add_handler(MessageHandler(Filters.chat_type.channel & Filters.text, process_channel_message))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN,
                          webhook_url='https://forcegameshelper.herokuapp.com/' + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()