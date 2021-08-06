import logging
import json
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, Bot
import os

class RegisteredChannelEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, RegisteredChannel):
            return {
                '__reg_channel__':True,
                'chat_id':obj.chat_id,
                'template':obj.template,
                'template_picture':obj.template_picture,
                'template_time_dif':obj.template_time_dif,
                'saved_messages':obj.saved_messages,
                'last_saved_messages':obj.last_saved_messages,
                'last_summary_message_id':obj.last_summary_message_id,
                'last_summary_time':obj.last_summary_time.isoformat()
            }
        return json.JSONEncoder.default(self, obj)

def as_registered_channel(dct):
    if '__reg_channel__' in dct:
        return RegisteredChannel(id=dct['chat_id'], template=dct['template'], template_picture=dct['template_picture'],
                                 template_time_dif=dct['template_time_dif'], saved_messages=dct['saved_messages'],
                                 last_saved_messages=dct['last_saved_messages'], last_summary_message_id=dct['last_summary_message_id'],
                                 last_summary_time=datetime.fromisoformat(dct['last_summary_time']))
    return dct

class RegisteredChannel:
    def __init__(self, id = 0, template = "", template_picture = "", template_time_dif = 12, saved_messages = [],
                 last_saved_messages = [], last_summary_message_id = -1, last_summary_time = datetime.now()):
        self.chat_id = id
        self.template = template
        self.template_picture = template_picture
        self.template_time_dif = template_time_dif
        self.saved_messages = saved_messages
        self.last_saved_messages = last_saved_messages
        self.last_summary_message_id = last_summary_message_id
        self.last_summary_time = last_summary_time

PORT = int(os.environ.get('PORT', 8443))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TOKEN', '')
bot = Bot(token=TOKEN)

STATUS_ID = "fgh_status"
CANCEL_MARKUP = "🔙 Atrás 🔙"
REGISTER_MARKUP = "➕ Registrar Canal ➕"
UNREGISTER_MARKUP = "✖️ Cancelar Registro de Canal ✖️"
CUSTOMIZE_MARKUP = "⚙ Configurar Canal Registrado ⚙"
CHANGE_TEMPLATE_MARKUP = "📋 Cambiar Plantilla 📋"
SEE_TEMPLATE_MARKUP = "📃 Ver plantilla actual 📃"
SEND_NOW_MARKUP = "✅ Enviar resumen ahora. ✅"
SEE_TEMPLATE_PICTURE_MARKUP = "📹 Ver foto de plantilla actual 📹"
CHANGE_SUMMARY_TIME_MARKUP = "🕑 Cambiar horario de los resumenes 🕑"
CHANGE_TEMPLATE_PICTURE_MARKUP = "📷 Cambiar Foto de Plantilla 📷"
CONTEXT_DATA_ID = "fgh_context_data"

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
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("¿Cuál es la @ del canal que desea configurar? 🧐",
                              reply_markup=markup)
    context.chat_data[STATUS_ID] = "requested_customization"

"""if the user is administrator then present reply
markups for the different settings
change template
change template picture"""
def customize_channel(update, context):
    username = update.message.text
    if username in registered_channels and is_admin(bot.get_chat(username), update.message.from_user.id):
        go_to_customization(update, context)
        context.chat_data[CONTEXT_DATA_ID] = username
    else:
        update.message.reply_text("El canal " + username + " no está registrado o no eres administrador. 😗")
        go_to_base(update, context)

def go_to_customization(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [SEND_NOW_MARKUP],
            [CHANGE_TEMPLATE_MARKUP, SEE_TEMPLATE_MARKUP],
            [CHANGE_TEMPLATE_PICTURE_MARKUP, SEE_TEMPLATE_PICTURE_MARKUP],
            [CHANGE_SUMMARY_TIME_MARKUP],
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(text="¿Qué desea configurar? 🧐", reply_markup=markup)
    context.chat_data[STATUS_ID] = "customizing"

def print_debug(update, context):
    if admin_chat_id == update.message.chat.id:
        for channel in registered_channels:
            update.message.reply_text(str(channel))

def request_change_template(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Envíe la nueva plantilla, debe contener el texto \"$plantilla$\" que será donde se colocará el resumen 🤖",
                              reply_markup=markup)
    context.chat_data[STATUS_ID] = "requested_template"

def change_template(update, context):
    if "$plantilla$" in update.message.text:
        registered_channels[context.chat_data[CONTEXT_DATA_ID]].template = update.message.text
        update.message.reply_text("Plantilla cambiada! :3")
        go_to_customization(update, context)
    else:
        update.message.reply_text("Plantilla incompleta! Debe contener el texto $plantilla$ que sera sustituido por los contenidos de la plantilla. 😐")

def see_template(update, context):
    update.message.reply_text(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template)

def request_change_template_picture(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Envíe la nueva foto de plantilla. 📸", reply_markup=markup)
    context.chat_data[STATUS_ID] = "requested_template_picture"

def change_template_picture(update, context):
    registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_picture = update.message.photo[-1].file_id
    update.message.reply_text("Foto establecida! :3")
    go_to_customization(update, context)

def see_template_picture(update, context):
    update.message.reply_photo(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_picture)

def request_change_summary_time(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Diga cada cuántas horas debo enviar el resumen, sólo envíe el numero\nejemplo: \"12\"\nValor actual:{}".format(registered_channels[context.chat_data[CONTEXT_DATA_ID]].template_time_dif),
                              reply_markup=markup)
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
        go_to_customization(update, context)

def request_register_channel(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Diga la @ del canal que desea registrar :D",
                              reply_markup=markup)
    context.chat_data[STATUS_ID] = "requested_register"

def register_channel(update, context):
    if update.message.text in registered_channels:
        update.message.reply_text("El canal {} ya se encuentra registrado".format(update.message.text))
        go_to_base(update, context)
        return
    try:
        channel = bot.get_chat(update.message.text)
    except TelegramError:
        update.message.reply_text("No se encontró el canal :|, recuerda que debe estar en el formato \"@NombreDeCanal\"")
        return
    atusername = get_at_username(channel.username)
    if atusername in registered_channels:
        update.message.reply_text("El canal {} ya se encuentra registrado".format(atusername))
        go_to_base(update, context)
        return
    if is_admin(channel, update.message.from_user.id):
        registered_channels[atusername] = RegisteredChannel(id=channel.id)
        update.message.reply_text("Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text("No eres administrador de este canal D:")
        go_to_base(update, context)

def request_unregister_channel(update, context):
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Diga la @ del canal que desea sacar del registro :(",
                              reply_markup=markup)
    context.chat_data[STATUS_ID] = "requested_unregister"

def unregister_channel(update, context):
    channel = update.message.text
    if channel in registered_channels:
        if is_admin(bot.get_chat(channel), update.message.from_user.id):
            registered_channels.pop(channel)
            update.message.reply_text("Canal eliminado del registro satisfactoriamente (satisfactorio para ti, pvto) ;-;")
            go_to_base(update, context)
    else:
        update.message.reply_text("Este canal no está registrado, recuerda que debe estar en el formato \"@NombreDeCanal\"")

def send_summary_now(update, context):
    post_summary(context.chat_data[CONTEXT_DATA_ID])
    update.message.reply_text("Resumen enviado :D")

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
    update.message.reply_text('No implementado uwu (fokiu)')

def backup(update, context):
    if update.message.chat.id != admin_chat_id:
        return
    serialize_bot_data("bot_data.json")
    file = open("bot_data.json", "rb")
    bot.send_document(chat_id=update.message.chat.id, document=file, filename="bot_data.json")
    file.close()

def restore(update, context):
    original = update.message.reply_to_message
    if original is not None and original.document is not None:
        t_file = original.document.get_file()
        deserialize_bot_data(t_file.download())
    else:
        update.message.reply_text("That command must be a reply to the backup file")

def deserialize_bot_data(filename):
    file = open(filename, "r")
    dict = json.load(file, object_hook=as_registered_channel)
    global admin_chat_id, registered_channels
    admin_chat_id = dict['admin_id']
    registered_channels = dict['registered_channels']
    file.close()

def serialize_bot_data(filename):
    file = open(filename, "w")
    bot_data = {
        'admin_id':admin_chat_id,
        'registered_channels':registered_channels
    }
    json.dump(bot_data, file, cls=RegisteredChannelEncoder)
    file.close()

def process_private_message(update, context):
    if STATUS_ID in context.chat_data:
        status = context.chat_data[STATUS_ID]
        text = update.message.text
        if status == "idle":
            if text == CUSTOMIZE_MARKUP:
                request_customize_channel(update, context)
            elif text == REGISTER_MARKUP:
                request_register_channel(update, context)
            elif text == UNREGISTER_MARKUP:
                request_unregister_channel(update, context)
            else:
                update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
        elif status == "requested_customization":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_base(update, context)
            else:
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
            elif text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_base(update, context)
            else:
                update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
        elif status == "requested_template":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_customization(update, context)
            else:
                change_template(update, context)
        elif status == "requested_template_picture":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_customization(update, context)
        elif status == "requested_register":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_base(update, context)
            else:
                register_channel(update, context)
        elif status == "requested_unregister":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_base(update, context)
            else:
                unregister_channel(update, context)
        elif status == "requested_summary_time":
            if text == CANCEL_MARKUP:
                update.message.reply_text("Cancelado")
                go_to_customization(update, context)
            else:
                change_summary_time(update, context)

def process_private_photo(update, context):
    if STATUS_ID in context.chat_data:
        status = context.chat_data[STATUS_ID]
        if status == "requested_template_picture":
            change_template_picture(update, context)
        else:
            update.message.reply_text("Quejeso? Tus nudes? :0")

def process_channel_photo(update, context):
    chat = update.channel_post.chat
    atusername = get_at_username(chat.username)
    if atusername not in registered_channels:
        return
    reg_channel = registered_channels[atusername]
    add_to_saved_messages(atusername, update.channel_post.message_id)

    if reg_channel.last_summary_message_id != -1:
        add_to_last_summary_messages(atusername, update.message.message_id)
        bot.edit_message_text(chat_id=chat.id,
                              message_id=reg_channel.last_summary_message_id,
                              text=get_template_string(atusername,
                                                       reg_channel.last_saved_messages))
    try_post_summary(atusername)

def process_channel_message(update, context):
    chat = update.channel_post.chat
    atusername = get_at_username(chat.username)
    if atusername not in registered_channels:
        return
    reg_channel = registered_channels[atusername]
    add_to_saved_messages(atusername, update.channel_post.message_id)

    if reg_channel.last_summary_message_id != -1:
        add_to_last_summary_messages(atusername, update.message.message_id)
        bot.edit_message_text(chat_id=chat.id,
                              message_id=reg_channel.last_summary_message_id,
                              text=get_template_string(atusername,
                                                       reg_channel.last_saved_messages))
    try_post_summary(atusername)

def try_post_summary(username):
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    delta = datetime.now() - reg_channel.last_summary_time
    if delta / timedelta(hours=1) >= reg_channel.template_time_dif:
        post_summary(atusername)

def post_summary(channel_username):
    atusername = get_at_username(channel_username)
    reg_channel = registered_channels[atusername]
    if len(reg_channel.saved_messages) == 0:
        return

    if reg_channel.template != "":
        if reg_channel.template_picture is not None:
            bot.send_photo(chat_id=reg_channel.chat_id, photo=reg_channel.template_picture)
        registered_channels[atusername].last_summary_message_id = bot.send_message(chat_id=reg_channel.chat_id,
            text=get_template_string(atusername, reg_channel.saved_messages)).message_id
        registered_channels[atusername].last_saved_messages = reg_channel.saved_messages
        registered_channels[atusername].saved_messages = []
        registered_channels[atusername].last_summary_time = datetime.now()

def add_to_saved_messages(username, message_id):
    atusername = get_at_username(username)
    registered_channels[atusername].saved_messages.append(message_id)

def add_to_last_summary_messages(username, message_id):
    atusername = get_at_username(username)
    registered_channels[atusername].last_saved_messages.append(message_id)

def get_template_string(username, messages_id):
    return registered_channels[get_at_username(username)].template.replace(
        "$plantilla$",
        "\n".join([get_message_link(username, id) for id in messages_id]))

def get_message_link(chat_username, message_id):
    return "t.me/{}/{}".format(get_no_at_username(chat_username), message_id)

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
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(CommandHandler("restore", restore))

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