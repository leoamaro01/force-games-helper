import logging
import json
from datetime import datetime, timedelta
from typing import Optional

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, Bot, TelegramError
import os


class BotDataEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, RegisteredChannel):
            return {
                '__reg_channel__': True,
                'chat_id': obj.chat_id,
                'template': obj.template,
                'template_picture': obj.template_picture,
                'template_time_dif': obj.template_time_dif,
                'saved_messages': obj.saved_messages,
                'last_saved_messages': obj.last_saved_messages,
                'last_summary_message_id': obj.last_summary_message_id,
                'last_summary_message_text': obj.last_summary_message_text,
                'categories': obj.categories,
                'last_summary_time': obj.last_summary_time.isoformat()
            }
        elif isinstance(obj, RegisteredUser):
            return {
                '__reg_user__': True,
                'chat_id': obj.chat_id,
                'status': obj.status,
                'context_data': obj.context_data,
                'known_channels': obj.known_channels
            }
        elif isinstance(obj, SavedMessage):
            return {
                '__saved_message__': True,
                'text': obj.text,
                'id': obj.message_id,
                'cat': obj.category
            }
        return json.JSONEncoder.default(self, obj)


def decode_bot_data(dct):
    if '__reg_channel__' in dct:
        return RegisteredChannel(chat_id=dct['chat_id'],
                                 template=dct['template'],
                                 template_picture=dct['template_picture'],
                                 template_time_dif=dct['template_time_dif'],
                                 saved_messages=dct['saved_messages'],
                                 last_saved_messages=dct['last_saved_messages'],
                                 last_summary_message_id=dct['last_summary_message_id'],
                                 categories=dct['categories'],
                                 last_summary_time=datetime.fromisoformat(dct['last_summary_time']),
                                 last_summary_message_text=dct['last_summary_message_text'])
    elif '__reg_user__' in dct:
        return RegisteredUser(chat_id=dct['chat_id'],
                              status=dct['status'],
                              context_data=dct['context_data'],
                              known_channels=dct['known_channels'])
    elif '__saved_message__' in dct:
        return SavedMessage(message_id=dct['id'],
                            text=dct['text'],
                            category=dct['cat'])
    return dct


class SavedMessage:
    def __init__(self, message_id, text, category: Optional[str] = ""):
        """
        Args:
            message_id (int)
            text (str)
        """
        self.message_id = message_id
        self.text = text
        self.category = category


class RegisteredChannel:
    def __init__(self, chat_id=0, template="", template_picture="", template_time_dif=12, saved_messages=None,
                 last_saved_messages=None, last_summary_message_id=-1, categories=None, last_summary_time=None,
                 last_summary_message_text=""):
        """
        Args:
            chat_id (int)
            template (str)
            template_picture (str)
            template_time_dif (int)
            saved_messages (list of SavedMessage)
            last_saved_messages (list of SavedMessage)
            last_summary_message_id (int)
            categories (list of str)
            last_summary_time (datetime)
        """
        self.chat_id = chat_id
        self.template = template
        self.template_picture = template_picture
        self.template_time_dif = template_time_dif
        self.last_summary_message_id = last_summary_message_id
        self.last_summary_message_text = last_summary_message_text
        if saved_messages is not None:
            self.saved_messages = saved_messages
        else:
            self.saved_messages = []
        if last_saved_messages is not None:
            self.last_saved_messages = last_saved_messages
        else:
            self.last_saved_messages = []
        if last_summary_time is not None:
            self.last_summary_time = last_summary_time
        else:
            self.last_summary_time = datetime.now()
        if categories is not None:
            self.categories = categories
        else:
            self.categories = []


class RegisteredUser:
    def __init__(self, chat_id=0, status="", context_data=None, known_channels=None):
        """
        Args:
            chat_id (int)
            status (str)
            context_data (dict[str, str])
            known_channels (list of str)
        """
        self.chat_id = chat_id
        self.status = status
        if context_data is not None:
            self.context_data = context_data
        else:
            self.context_data = {}
        if known_channels is not None:
            self.known_channels = known_channels
        else:
            self.known_channels = []


PORT = int(os.environ.get('PORT', 8443))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TOKEN', '')
bot = Bot(token=TOKEN)

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
CATEGORIES_MENU_MARKUP = "🔠 Categorías 🔠"
SEE_CATEGORIES_MARKUP = "🔢 Ver Categorías 🔢"
ADD_CATEGORY_MARKUP = "➕ Añadir Categoría ➕"
REMOVE_CATEGORY_MARKUP = "✖️ Eliminar Categoría ✖️"
REORDER_CATEGORIES_MARKUP = "⬆️ Reordenar Categorías ⬇️"
MOVE_UP_MARKUP = "🔼 Mover Arriba 🔼"
MOVE_DOWN_MARKUP = "🔽 Mover Abajo 🔽"
HELP_MARKUP = "ℹ Cómo utilizar el Bot ℹ"
HELP_TEXT = """Este bot te permitira publicar resumenes de todo lo publicado en tu canal de forma automática, para aprender a utilizarlo, sigue esta guía!

Paso 1⃣: Registra tu canal.
En el menu principal del bot tendrás un boton que titulado Registrar Canal, ahi debes dar la @ de tu canal, por ejemplo @Force_GamesS3. Para poder registrar un canal debes ser administrador del canal y el bot debe pertenecer al canal.

Paso 2⃣: Configura el resumen.
Este paso es obligatorio para que el bot funcione en tu canal. En el menu principal le dan al boton de Configurar Canal Registrado, y una vez adentro al boton de Cambiar Plantilla.

Como debe ser la plantilla:
La plantilla debe contener uno o varios (si usas categorías) lugares determinados por el usuario que será donde se colocarán los contenidos del resumen, estos lugares se identificaran por el texto $plantilla$ (o $plantilla0$, $plantilla1$, $plantilla2$, etc si usas categorias), por ejemplo:
——————————
Resumen del dia:

Juegos:
$plantilla0$

Anime:
$plantilla1$

Programas:
$plantilla2$

Se seguirá actualizando :3
——————————
Ese es un ejemplo te plantilla perfectamente válido.

(Opcional) Además puedes poner una foto que será enviada cada vez que se envíe el resumen al canal.

Puedes cambiar cada cuántas horas se envían los resumenes en el menú de Cambiar Horario de Resumenes, puedes hacer que se envíen cada 12h (por defecto), o incluso cada 1h, como prefieras.

Paso 3⃣: Categorías.
En el menú de Categorías (dentro de la configuración) puedes personalizar las categorías de tu plantilla, esto lo puedes hacer si tu canal envía diferentes tipos de contenido. Si no añades ninguna categoría todo lo que subas al canal se colocará en donde pusiste el texto $plantilla$
Antes de poder hacer nada deberás añadir una categoría, esta será tu primera categoría y tendra asignado el número 0, y en el texto de tu plantilla los post de esta categoría se colocarán donde pusiste el texto de $plantilla0$
El identificador de la categoría será lo que el bot debe encontrar en la primera linea de una publicacion del canal para considerarlo de esta categoría, por ejemplo, si el identificador de la categoría de Juegos es "🎮Game🎮", entonces en la primera linea de cada publicación de un juego debe estar ese exacto texto.
Dentro del menú de categorías estas pueden ser reordenadas e incluso eliminadas"""
MAX_KNOWN_CHANNELS = 5

BACKUP_TIME_DIF = 10  # minutes

admin_chat_id = -1

registered_channels: dict[str, RegisteredChannel] = {}
registered_users: dict[str, RegisteredUser] = {}

update_checker: list[datetime] = []

# TODO automatic client deletion if last update was too long ago


def start(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    user = update.effective_user
    get_reg_user(user, update.effective_chat)
    if len(context.args) >= 2 and context.args[0] == "admin" and context.args[1] == TOKEN:
        global admin_chat_id
        if admin_chat_id == user.id:
            update.message.reply_text("Ya eres mi onii-chan!...baka")
        else:
            update.message.reply_text("Ahora eres mi onii-chan! :3")
            admin_chat_id = user.id

    go_to_base(update, context)


def print_debug(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if admin_chat_id == update.effective_chat.id:
        for channel in registered_channels:
            update.message.reply_text(str(channel))


def broadcast(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_user.id == admin_chat_id:
        if update.message.reply_to_message is not None:
            for user in registered_users.values():
                bot.copy_message(chat_id=user.chat_id, from_chat_id=update.effective_chat.id,
                                 message_id=update.message.reply_to_message.message_id)


def stats(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_user.id == admin_chat_id:
        text = \
            "Registered Channels: {}\n" \
            "Registered Users: {}\n" \
            "Last Update: {}".\
            format(len(registered_channels),
                   len(registered_users),
                   (update_checker[0].isoformat(), "Never")[len(update_checker) == 0])
        update.message.reply_text(text)


def auto_backup():
    if len(update_checker) != 0:
        delta = datetime.now() - update_checker[0]
        if delta / timedelta(minutes=1) > BACKUP_TIME_DIF:
            logger.info("Performing timed Bot Data Backup")
            serialize_bot_data("bot_data.json")
            update_checker[0] = datetime.now()


def auto_restore():
    if len(update_checker) == 0:
        update_checker.append(datetime.now())
        deserialize_bot_data("bot_data.json")


def add_to_known_channels(reg_user, channel):
    """
    Args:
        reg_user (RegisteredUser)
        channel (str)
    """
    reg_user.known_channels.insert(0, channel)
    while len(reg_user.known_channels) > MAX_KNOWN_CHANNELS:
        reg_user.known_channels.pop(-1)


def try_post_summary(username):
    """

    Args:
        username (str)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    delta = datetime.now() - reg_channel.last_summary_time
    if delta / timedelta(hours=1) >= reg_channel.template_time_dif:
        post_summary(atusername)


def post_summary(channel_username):
    """

    Args:
        channel_username (str)

    """
    atusername = get_at_username(channel_username)
    reg_channel = registered_channels[atusername]

    if reg_channel.template != "":
        if reg_channel.template_picture is not None and reg_channel.template_picture != "":
            bot.send_photo(chat_id=reg_channel.chat_id, photo=reg_channel.template_picture)
        text = get_template_string(atusername, reg_channel.saved_messages)
        summary_id = bot.send_message(chat_id=reg_channel.chat_id,
                                      text=text,
                                      parse_mode='MarkdownV2').message_id
        bot.pin_chat_message(reg_channel.chat_id, summary_id)
        reg_channel.last_summary_message_text = text
        reg_channel.last_summary_message_id = summary_id
        reg_channel.last_saved_messages = reg_channel.saved_messages
        reg_channel.saved_messages = []
        reg_channel.last_summary_time = datetime.now()


def add_to_last_summary(chat, message):
    """

    Args:
        chat (telegram.Chat)
        message (telegram.Message)

    """
    atusername = get_at_username(chat.username)
    reg_channel = registered_channels[atusername]
    if reg_channel.last_summary_message_id != -1:
        add_to_last_summary_messages(atusername, message)
        text = get_template_string(atusername, reg_channel.last_saved_messages)
        if text != reg_channel.last_summary_message_text:
            bot.edit_message_text(chat_id=chat.id,
                                  message_id=reg_channel.last_summary_message_id,
                                  text=text,
                                  parse_mode='MarkdownV2')
            reg_channel.last_summary_message_text = text


def add_to_saved_messages(username, message):
    """

    Args:
        username (str)
        message (telegram.Message)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    if message.caption is None:
        text = message.text.splitlines()[0]
    else:
        text = message.caption.splitlines()[0]

    if len(reg_channel.categories) > 0:
        for cat in reg_channel.categories:
            if cat in text:
                reg_channel.saved_messages.append(
                    SavedMessage(message.message_id, text, cat))
                return
    else:
        reg_channel.saved_messages.append(
            SavedMessage(message.message_id, text))
        return


def add_to_last_summary_messages(username, message):
    """

    Args:
        username (str)
        message (telegram.Message)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    if message.caption is None:
        text = message.text.splitlines()[0]
    else:
        text = message.caption.splitlines()[0]

    for cat in reg_channel.categories:
        if cat in text:
            reg_channel.last_saved_messages.append(
                SavedMessage(message.message_id, text, cat))
            return


def get_template_string(username, messages):
    """
    Args:
        username (str)
        messages (list of SavedMessage)

    Returns:
        str: The formatted template for chanel `username`
    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]
    template = escape_for_telegram(reg_channel.template)
    if len(reg_channel.categories) > 0:
        index = 0
        for cat in reg_channel.categories:
            if "$plantilla{}$".format(index) in template:
                cat_messages = ["\\-[{}]({})".format(escape_for_telegram(m.text.replace(cat, "")), get_message_link(username, m.message_id))
                                for m in messages
                                if m.category == cat]
                if len(cat_messages) > 0:
                    template = template.replace("$plantilla{}$".format(index), "\n".join(cat_messages))
                else:
                    template = template.replace("$plantilla{}$".format(index), "\\-")
            index += 1
    elif "$plantilla$" in template:
        if len(messages) > 0:
            final_messages = ["\\-[{}]({})".format(escape_for_telegram(m.text), get_message_link(username, m.message_id)) for m
                              in
                              messages]
            template = template.replace("$plantilla$", "\n".join(final_messages))
        else:
            template = template.replace("$plantilla$", "\\-")
    return template


def escape_for_telegram(text):
    """
    Args:
        text (str)

    Returns:
        str: Escaped text
    """
    return text \
        .replace('\\', '\\\\') \
        .replace('[', '\\[') \
        .replace(']', '\\]') \
        .replace('(', '\\(') \
        .replace(')', '\\)') \
        .replace('`', '\\`') \
        .replace('>', '\\>') \
        .replace('#', '\\#') \
        .replace('+', '\\+') \
        .replace('-', '\\-') \
        .replace('=', '\\=') \
        .replace('|', '\\|') \
        .replace('{', '\\{') \
        .replace('}', '\\}') \
        .replace('.', '\\.') \
        .replace('!', '\\!') \
        .replace('*', '\\*') \
        .replace('_', '\\_') \
        .replace('~', '\\~')


def get_message_link(chat_username, message_id):
    """
    Args:
        chat_username (str)
        message_id (int)

    Returns:
        str: Link of the message with id `message_id` in chat with
            username `chat_username` in the format `t.me/chat/id`
    """
    return "t.me/{}/{}".format(get_no_at_username(chat_username), message_id)


def get_at_username(username):
    """

    Args:
        username (str)

    Returns:
        str: Returns username with @

    """
    if username[0] == "@":
        return username
    else:
        return "@" + username


def get_no_at_username(username):
    """

    Args:
        username (str)

    Returns:
        str: Returns username without @

    """
    if username[0] == "@":
        return username[1:]
    else:
        return username


def get_reg_user(user, chat):
    """
    Args:
        chat (telegram.Chat)
        user (telegram.User)

    Returns:
        RegisteredUser: Finds or creates a new registered user
    """
    logger.info(json.dumps(registered_users, cls=BotDataEncoder))
    str_id = str(user.id)
    if str_id not in registered_users:
        logger.info("Adding user {}".format(str_id))
        registered_users[str_id] = RegisteredUser(chat_id=chat.id)

    return registered_users[str_id]


def go_to_base(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)

    markup = ReplyKeyboardMarkup([
        [CUSTOMIZE_MARKUP],
        [REGISTER_MARKUP, UNREGISTER_MARKUP],
        [HELP_MARKUP]
    ], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(text="Menú 🤓\nPuedes usar /cancel en cualquier momento para volver aquí :D",
                              reply_markup=markup)
    reg_user.status = "idle"


def request_customize_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [[ch] for ch in reg_user.known_channels] + [[CANCEL_MARKUP]], resize_keyboard=True
    )
    update.message.reply_text("¿Cuál es la @ del canal que desea configurar? 🧐",
                              reply_markup=markup)
    reg_user.status = "requested_customization"


def customize_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    username = get_at_username(update.message.text)
    try:
        if username in registered_channels:
            admin_status = is_admin(bot.get_chat(username), update.effective_user.id)
            if admin_status[0]:
                go_to_customization(update, context)
                reg_user.context_data['channel'] = username
            else:
                update.message.reply_text(admin_status[1])
        else:
            update.message.reply_text("El canal " + username + " no está registrado 😗")
            go_to_base(update, context)
    except TelegramError:
        update.message.reply_text("El canal " + username + " no se encontró")
        go_to_base(update, context)


def go_to_customization(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [SEND_NOW_MARKUP],
            [CHANGE_TEMPLATE_MARKUP, SEE_TEMPLATE_MARKUP],
            [CHANGE_TEMPLATE_PICTURE_MARKUP, SEE_TEMPLATE_PICTURE_MARKUP],
            [CATEGORIES_MENU_MARKUP],
            [CHANGE_SUMMARY_TIME_MARKUP],
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(text="¿Qué desea configurar? 🧐", reply_markup=markup)
    reg_user.status = "customizing"


def go_to_categories(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [SEE_CATEGORIES_MARKUP],
            [ADD_CATEGORY_MARKUP, REMOVE_CATEGORY_MARKUP],
            [REORDER_CATEGORIES_MARKUP],
            [CANCEL_MARKUP],
        ], resize_keyboard=True
    )
    update.message.reply_text(text="Menú de categorías 🔢", reply_markup=markup)
    reg_user.status = "categories"


def get_categories_list_text(reg_channel, highlight: Optional[int] = -1):
    """
    Args:
        reg_channel (RegisteredChannel)
        highlight
    Returns:
        str: Formatted list of categories.
    """
    return "\n".join(["{}{}{}-{}{}".format(
        ("", "__*")[highlight == i],
        i,
        ("\\", "")[highlight == -1],
        (escape_for_telegram(reg_channel.categories[i]), reg_channel.categories[i])[highlight == -1],
        ("", "*__")[highlight == i])
        for i in range(len(reg_channel.categories))])


def see_categories(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if len(reg_channel.categories) == 0:
        update.message.reply_text("No hay ninguna categoría establecida para este canal")
    else:
        update.message.reply_text(get_categories_list_text(reg_channel))


def request_add_category(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Cuál sera el identificador de la nueva categoría?", reply_markup=markup)
    reg_user.status = "requested_add_category"


def add_category(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    reg_channel.categories.append(update.message.text)
    update.message.reply_text(
        "Categoría {} añadida! Para que esta funcione $plantilla{}$ debe estar en el texto de la plantilla"
        .format(update.message.text, len(reg_channel.categories) - 1))
    go_to_categories(update, context)


def request_remove_category(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Cuál es el número de la categoría que desea eliminar?", reply_markup=markup)
    reg_user.status = "requested_remove_category"


def remove_category(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :c")
        return

    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]

    if index < 0 or index >= len(reg_channel.categories):
        update.message.reply_text("Eso no es un número válido :c")
        return

    reg_channel.categories.pop(index)
    update.message.reply_text("Categoría eliminada.")
    go_to_categories(update, context)


def request_reorder_categories(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if len(reg_channel.categories) <= 1:
        update.message.reply_text("Solo puede reordenar categorías luego de añadir 2 o mas categorías.")
        go_to_categories(update, context)
        return
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(
        "Estas son las categorías que ha añadido:\n\n"
        "{}\n\n"
        "Cuál es el número de la categoría que desea mover?".
        format(get_categories_list_text(reg_channel)),
        reply_markup=markup)
    reg_user.status = "requested_reorder_categories"


def reorder_categories(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :c")
        return

    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]

    if index < 0 or index >= len(reg_channel.categories):
        update.message.reply_text("Eso no es un número válido :c")
        return

    if index == 0:
        markup = ReplyKeyboardMarkup(
            [
                [MOVE_DOWN_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
    elif index == len(reg_channel.categories) - 1:
        markup = ReplyKeyboardMarkup(
            [
                [MOVE_UP_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
    else:
        markup = ReplyKeyboardMarkup(
            [
                [MOVE_UP_MARKUP],
                [MOVE_DOWN_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
    update.message.reply_text(
        "Utilice los botones para mover el elemento seleccionado:\n\n"
        "{}\n\n"
        "Presione {} para terminar".format(get_categories_list_text(reg_channel, index), CANCEL_MARKUP),
        reply_markup=markup,
        parse_mode="MarkdownV2")
    reg_user.status = "reordering_categories"
    reg_user.context_data['index'] = index


def move_category_up(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]

    index = reg_user.context_data['index']
    if index == 0:
        markup = ReplyKeyboardMarkup(
            [
                [MOVE_DOWN_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
        update.message.reply_text("No se puede mover más arriba.")
    else:
        index -= 1
        item = reg_channel.categories[index]
        reg_channel.categories.pop(index)
        reg_channel.categories.insert(index + 1, item)
        if index == 0:
            markup = ReplyKeyboardMarkup(
                [
                    [MOVE_DOWN_MARKUP],
                    [CANCEL_MARKUP]
                ], resize_keyboard=True
            )
        else:
            markup = ReplyKeyboardMarkup(
                [
                    [MOVE_UP_MARKUP],
                    [MOVE_DOWN_MARKUP],
                    [CANCEL_MARKUP]
                ], resize_keyboard=True
            )
        reg_user.context_data['index'] = index
    update.message.reply_text(
        "Utilice los botones para mover el elemento seleccionado:\n\n"
        "{}\n\n"
        "Presione {} para terminar".format(get_categories_list_text(reg_channel, index), CANCEL_MARKUP),
        reply_markup=markup,
        parse_mode="MarkdownV2")


def move_category_down(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]

    index = reg_user.context_data['index']
    if index == len(reg_channel.categories) - 1:
        markup = ReplyKeyboardMarkup(
            [
                [MOVE_UP_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
        update.message.reply_text("No se puede mover más abajo.")
    else:
        index += 1
        item = reg_channel.categories[index - 1]
        reg_channel.categories.pop(index - 1)
        reg_channel.categories.insert(index, item)
        if index == len(reg_channel.categories) - 1:
            markup = ReplyKeyboardMarkup(
                [
                    [MOVE_UP_MARKUP],
                    [CANCEL_MARKUP]
                ], resize_keyboard=True
            )
        else:
            markup = ReplyKeyboardMarkup(
                [
                    [MOVE_UP_MARKUP],
                    [MOVE_DOWN_MARKUP],
                    [CANCEL_MARKUP]
                ], resize_keyboard=True
            )
        reg_user.context_data['index'] = index
    update.message.reply_text(
        "Utilice los botones para mover el elemento seleccionado:\n\n"
        "{}\n\n"
        "Presione {} para terminar".format(get_categories_list_text(reg_channel, index), CANCEL_MARKUP),
        reply_markup=markup,
        parse_mode="MarkdownV2")


def request_change_template(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(
        "Envíe la nueva plantilla, debe contener el texto \"$plantilla$\" o "
        "$plantilla#$ si usas categorias (donde # es el numero de la categoria) "
        "que será donde se colocará el resumen 🤖",
        reply_markup=markup)
    reg_user.status = "requested_template"


def change_template(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    registered_channels[reg_user.context_data['channel']].template = update.message.text
    update.message.reply_text("Plantilla cambiada! :3")
    go_to_customization(update, context)


def see_template(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    update.message.reply_text(registered_channels[reg_user.context_data['channel']].template)


def request_change_template_picture(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Envíe la nueva foto de plantilla. 📸", reply_markup=markup)
    reg_user.status = "requested_template_picture"


def change_template_picture(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    registered_channels[reg_user.context_data['channel']].template_picture = update.message.photo[-1].file_id
    update.message.reply_text("Foto establecida! :3")
    go_to_customization(update, context)


def see_template_picture(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    update.message.reply_photo(registered_channels[reg_user.context_data['channel']].template_picture)


def request_change_summary_time(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(
        "Diga cada cuántas horas debo enviar el resumen, sólo envíe el numero\nejemplo: \"12\"\nValor actual:{}"
        .format(registered_channels[reg_user.context_data['channel']].template_time_dif),
        reply_markup=markup)
    reg_user.status = "requested_summary_time"


def change_summary_time(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    try:
        time = int(update.message.text)
        if time <= 0:
            update.message.reply_text("Eso no es un número válido :/")
        else:
            registered_channels[reg_user.context_data['channel']].template_time_dif = time
            update.message.reply_text("Tiempo entre resumenes cambiado :3")
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
    finally:
        go_to_customization(update, context)


def request_register_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [[ch] for ch in reg_user.known_channels] + [[CANCEL_MARKUP]], resize_keyboard=True
    )

    update.message.reply_text("Diga la @ del canal que desea registrar :D",
                              reply_markup=markup)
    reg_user.status = "requested_register"


def register_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    atusername = get_at_username(update.message.text)
    if atusername in registered_channels:
        update.message.reply_text("El canal {} ya se encuentra registrado".format(atusername))
        go_to_base(update, context)
        return
    try:
        channel = bot.get_chat(atusername)
    except TelegramError:
        update.message.reply_text(
            "No se encontró el canal :|")
        return
    if atusername in registered_channels:
        update.message.reply_text("El canal {} ya se encuentra registrado".format(atusername))
        go_to_base(update, context)
        return
    admin_status = is_admin(channel, update.effective_user.id)
    if admin_status[0]:
        registered_channels[atusername] = RegisteredChannel(chat_id=channel.id)
        add_to_known_channels(get_reg_user(update.effective_user, update.effective_chat), atusername)
        update.message.reply_text(
            "Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text(admin_status[1])
        go_to_base(update, context)


def request_unregister_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Diga la @ del canal que desea sacar del registro :(",
                              reply_markup=markup)
    reg_user.status = "requested_unregister"


def unregister_channel(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    channel = update.message.text
    if channel in registered_channels:
        admin_status = is_admin(bot.get_chat(channel), update.effective_user.id)
        if admin_status[0]:
            reg_user = get_reg_user(update.effective_user, update.effective_chat)
            registered_channels.pop(channel)
            if channel in reg_user.known_channels:
                reg_user.known_channels.remove(channel)
            update.message.reply_text(
                "Canal eliminado del registro satisfactoriamente (satisfactorio para ti, pvto) ;-;")
            go_to_base(update, context)
        else:
            update.message.reply_text(admin_status[1])
            go_to_base(update, context)
    else:
        update.message.reply_text(
            "Este canal no está registrado, recuerda que debe estar en el formato \"@NombreDeCanal\"")


def send_summary_now(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    post_summary(reg_user.context_data['channel'])
    update.message.reply_text("Resumen enviado :D")


def is_admin(from_chat, user_id) -> tuple[bool, str]:
    """
    Args:
        from_chat (telegram.Chat)
        user_id (int)

    Returns:
        A tuple, Item 1 is True if user is admin and False otherwise,
            in this case Item 2 is the reason
    """
    if from_chat.type == "channel":
        try:
            bot_user: telegram.User = bot.get_me()
            bot_member = from_chat.get_member(bot_user.id)
            administrators = from_chat.get_administrators()
            if bot_member is not None:
                if bot_member not in administrators:
                    return False, "El bot no es administrador del canal"
            else:
                return False, "El bot no pertenece al canal"
            member = from_chat.get_member(user_id)
            if member is not None:
                if member in administrators:
                    return True, ""
                else:
                    return False, "No eres administrador de ese canal :/ eres tonto o primo de JAVIER?"
            else:
                return False, "No perteneces a ese canal"
        except TelegramError:
            return False, "No perteneces a este canal, o el bot no pertenece a este"
    else:
        return False, "Ese chat no es un canal"


def help_handler(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    update.message.reply_text(HELP_TEXT)


def backup(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_chat.id != admin_chat_id:
        return
    serialize_bot_data("bot_data.json")
    file = open("bot_data.json", "rb")
    bot.send_document(chat_id=update.effective_chat.id, document=file, filename="bot_data.json")
    file.close()


def restore(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    original = update.message.reply_to_message
    if original is not None and original.document is not None:
        t_file = original.document.get_file()
        deserialize_bot_data(t_file.download())
        update.message.reply_text("Restored previous data!")
    else:
        update.message.reply_text("That command must be a reply to the backup file")


def deserialize_bot_data(filename):
    """
    Args:
        filename (str)
    """
    try:
        file = open(filename, "r")
        dct = json.load(file, object_hook=decode_bot_data)
        global admin_chat_id, registered_channels, registered_users
        admin_chat_id = dct['admin_id']
        registered_channels = dct['registered_channels']
        registered_users = dct['registered_users']
        file.close()
        return True
    except OSError:
        logger.warning("Could not load bot data.")
        return False


def serialize_bot_data(filename):
    """
    Args:
        filename (str)
    """
    file = open(filename, "w")
    bot_data = {
        'admin_id': admin_chat_id,
        'registered_channels': registered_channels,
        'registered_users': registered_users
    }
    json.dump(bot_data, file, cls=BotDataEncoder)
    file.close()


def process_private_message(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    auto_restore()
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    status = reg_user.status
    text = update.message.text
    if status == "idle":
        if text == CUSTOMIZE_MARKUP:
            request_customize_channel(update, context)
        elif text == REGISTER_MARKUP:
            request_register_channel(update, context)
        elif text == UNREGISTER_MARKUP:
            request_unregister_channel(update, context)
        elif text == HELP_MARKUP:
            help_handler(update, context)
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
        elif text == CATEGORIES_MENU_MARKUP:
            go_to_categories(update, context)
        elif text == SEND_NOW_MARKUP:
            send_summary_now(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_base(update, context)
        else:
            update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
    elif status == "categories":
        if text == ADD_CATEGORY_MARKUP:
            request_add_category(update, context)
        elif text == REMOVE_CATEGORY_MARKUP:
            request_remove_category(update, context)
        elif text == SEE_CATEGORIES_MARKUP:
            see_categories(update, context)
        elif text == REORDER_CATEGORIES_MARKUP:
            request_reorder_categories(update, context)
        elif text == CANCEL_MARKUP:
            go_to_customization(update, context)
    elif status == "reordering_categories":
        if text == MOVE_UP_MARKUP:
            move_category_up(update, context)
        elif text == MOVE_DOWN_MARKUP:
            move_category_down(update, context)
        elif text == CANCEL_MARKUP:
            go_to_categories(update, context)
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
    elif status == "requested_add_category":
        if text == CANCEL_MARKUP:
            go_to_categories(update, context)
        else:
            add_category(update, context)
    elif status == "requested_remove_category":
        if text == CANCEL_MARKUP:
            go_to_categories(update, context)
        else:
            remove_category(update, context)
    elif status == "requested_reorder_categories":
        if text == CANCEL_MARKUP:
            go_to_categories(update, context)
        else:
            reorder_categories(update, context)
    elif status == "":
        go_to_base(update, context)
    auto_backup()


def process_private_photo(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    auto_restore()
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    status = reg_user.status
    if status == "requested_template_picture":
        change_template_picture(update, context)
    else:
        update.message.reply_text("Quejeso? Tus nudes? :0")
    auto_backup()


def process_channel_update(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    auto_restore()
    chat = update.effective_chat
    atusername = get_at_username(chat.username)
    if atusername not in registered_channels:
        auto_backup()
        return
    reg_channel = registered_channels[atusername]
    add_to_saved_messages(atusername, update.channel_post)
    add_to_last_summary(chat, update.channel_post)

    try_post_summary(atusername)
    auto_backup()


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
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CommandHandler("debug", print_debug))
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(CommandHandler("restore", restore))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("stats", stats))

    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, process_private_message))
    dp.add_handler(MessageHandler(Filters.photo & Filters.chat_type.private, process_private_photo))

    dp.add_handler(MessageHandler(Filters.chat_type.channel & (Filters.text | Filters.caption),
                                  process_channel_update))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN,
                          webhook_url='https://forcegameshelper.herokuapp.com/' + TOKEN)

    auto_restore()

    updater.idle()


if __name__ == '__main__':
    main()
