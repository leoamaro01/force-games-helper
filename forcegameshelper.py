import logging
import json
import telegram
import os
from threading import Timer
from datetime import datetime, timedelta
from typing import Optional
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, Bot, TelegramError, ReplyKeyboardRemove

__CHANNEL_VERSION = "1.0"
__USER_VERSION = "1.0"
__CATEGORY_VERSION = "1.0"
__MESSAGE_VERSION = "1.0"


class BotDataEncoder(json.JSONEncoder):
    def default(self, obj):
        global __CHANNEL_VERSION, __USER_VERSION, __CATEGORY_VERSION, __MESSAGE_VERSION
        if isinstance(obj, RegisteredChannel):
            return {
                '__reg_channel__': True,
                '__version__': __CHANNEL_VERSION,
                'chat_id': obj.chat_id,
                'template': obj.template,
                'template_picture': obj.template_picture,
                'template_time_dif': obj.template_time_dif,
                'saved_messages': obj.saved_messages,
                'last_saved_messages': obj.last_saved_messages,
                'last_summary_message_id': obj.last_summary_message_id,
                'last_summary_message_text': obj.last_summary_message_text,
                'categories': obj.categories,
                'last_summary_time': obj.last_summary_time.isoformat(),
                'pin_summaries': obj.pin_summaries
            }
        elif isinstance(obj, RegisteredUser):
            return {
                '__reg_user__': True,
                '__version__': __USER_VERSION,
                'chat_id': obj.chat_id,
                'status': obj.status,
                'context_data': obj.context_data,
                'known_channels': obj.known_channels
            }
        elif isinstance(obj, SavedMessage):
            return {
                '__saved_message__': True,
                '__version__': __MESSAGE_VERSION,
                'text': obj.text,
                'id': obj.message_id,
                'cat': obj.category,
                'message_time': obj.message_time.isoformat(),
                'custom_content': obj.custom_content
            }
        elif isinstance(obj, Category):
            return {
                '__category__': True,
                '__version__': __CATEGORY_VERSION,
                'name': obj.name,
                'identifiers': obj.identifiers,
                'custom_content_identifiers': obj.custom_content_identifiers,
                'template_format': obj.template_format
            }
        return json.JSONEncoder.default(self, obj)


def decode_bot_data(dct: dict):
    if '__reg_channel__' in dct:
        if "__version__" not in dct or dct['__version__'] != __CHANNEL_VERSION:
            return decode_legacy_data(dct)
        else:
            return RegisteredChannel(chat_id=dct['chat_id'],
                                     template=dct['template'],
                                     template_picture=dct['template_picture'],
                                     template_time_dif=dct['template_time_dif'],
                                     saved_messages=dct['saved_messages'],
                                     last_saved_messages=dct['last_saved_messages'],
                                     last_summary_message_id=dct['last_summary_message_id'],
                                     categories=dct['categories'],
                                     last_summary_time=datetime.fromisoformat(dct['last_summary_time']),
                                     last_summary_message_text=dct['last_summary_message_text'],
                                     pin_summaries=dct['pin_summaries'])
    elif '__reg_user__' in dct:
        if "__version__" not in dct or dct['__version__'] != __USER_VERSION:
            return decode_legacy_data(dct)
        else:
            return RegisteredUser(chat_id=dct['chat_id'],
                                  status=dct['status'],
                                  context_data=dct['context_data'],
                                  known_channels=dct['known_channels'])
    elif '__saved_message__' in dct:
        if "__version__" not in dct or dct['__version__'] != __MESSAGE_VERSION:
            return decode_legacy_data(dct)
        else:
            return SavedMessage(message_id=dct['id'],
                                text=dct['text'],
                                category=dct['cat'],
                                custom_content=dct['custom_content'],
                                message_time=datetime.fromisoformat(dct['message_time']))
    elif '__category__' in dct:
        if "__version__" not in dct or dct['__version__'] != __MESSAGE_VERSION:
            return decode_legacy_data(dct)
        else:
            return Category(name=dct['name'],
                            identifiers=dct['identifiers'],
                            custom_content_identifiers=dct['custom_content_identifiers'],
                            template_format=dct['template_format'])
    return dct


# TODO
def decode_legacy_data(dct: dict):
    return


class SavedMessage:
    def __init__(self, message_id, text, message_time, custom_content: Optional[list[str]],
                 category: Optional[str] = ""):
        """
        Args:
            message_id (int)
            text (str)
            message_time (datetime)
            custom_content (list of str)
        """
        self.message_id = message_id
        self.text = text
        self.category = category
        self.message_time = message_time
        self.custom_content = custom_content


class RegisteredChannel:
    def __init__(self, chat_id=0, template="", template_picture="", template_time_dif=24, saved_messages=None,
                 last_saved_messages=None, last_summary_message_id=-1, categories=None, last_summary_time=None,
                 last_summary_message_text="", pin_summaries=True):
        """
        Args:
            chat_id (int)
            template (str)
            template_picture (str)
            template_time_dif (int)
            saved_messages (list of SavedMessage)
            last_saved_messages (list of SavedMessage)
            last_summary_message_id (int)
            categories (list of Category)
            last_summary_time (datetime)
            last_summary_message_text (str)
            pin_summaries (bool)
        """
        self.chat_id = chat_id
        self.template = template
        self.template_picture = template_picture
        self.template_time_dif = template_time_dif
        self.last_summary_message_id = last_summary_message_id
        self.last_summary_message_text = last_summary_message_text
        self.pin_summaries = pin_summaries
        if saved_messages is not None:
            self.saved_messages = saved_messages
        else:
            self.saved_messages: list[SavedMessage] = []
        if last_saved_messages is not None:
            self.last_saved_messages = last_saved_messages
        else:
            self.last_saved_messages: list[SavedMessage] = []
        if last_summary_time is not None:
            self.last_summary_time = last_summary_time
        else:
            self.last_summary_time = datetime.now()
        if categories is not None:
            self.categories = categories
        else:
            self.categories: list[Category] = []


class Category:
    def __init__(self, name="", identifiers=None, custom_content_identifiers=None, template_format=""):
        """
        Args:
            name (str)
            template_format (str)
            identifiers (list of str)
            custom_content_identifiers (list of str)
        """
        self.name = name
        self.template_format = template_format
        if identifiers is not None:
            self.identifiers = identifiers
        else:
            self.identifiers = []
        if custom_content_identifiers is not None:
            self.custom_content_identifiers = custom_content_identifiers
        else:
            self.custom_content_identifiers = []


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
BOT_CLOUD = os.environ.get('BOT_CLOUD')

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
SEE_TEMPLATE_MARKUP = "📃 Ver Plantilla 📃"
SEND_NOW_MARKUP = "✅ Enviar Resumen Ahora ✅"
SEE_TEMPLATE_PICTURE_MARKUP = "📹 Ver Foto Actual 📹"
CHANGE_SUMMARY_TIME_MARKUP = "🕑 Cambiar Horario de los Resúmenes 🕑"
CHANGE_TEMPLATE_PICTURE_MARKUP = "📷 Cambiar Foto de Plantilla 📷"
CATEGORIES_MENU_MARKUP = "🔠 Categorías 🔠"
SEE_CATEGORIES_MARKUP = "🔢 Ver Categorías 🔢"
ADD_CATEGORY_MARKUP = "➕ Añadir Categoría ➕"
REMOVE_CATEGORY_MARKUP = "✖️ Eliminar Categoría ✖️"
REORDER_CATEGORIES_MARKUP = "⬆️ Reordenar Categorías ⬇️"
MOVE_UP_MARKUP = "🔼 Mover Arriba 🔼"
MOVE_DOWN_MARKUP = "🔽 Mover Abajo 🔽"
HELP_MARKUP = "ℹ Ayuda ℹ"
FIND_PROBLEMS_MARKUP = "⚠ Buscar Problemas ⚠"
DELETE_TEMPLATE_FORMAT_MARKUP = "🗑 Eliminar Formato 🗑"
DELETE_TEMPLATE_PICTURE_MARKUP = "🗑 Eliminar Foto 🗑"
TEMPLATE_MENU_MARKUP = "📄 Plantilla 📄"
ADD_CATEGORY_IDENTIFIER_MARKUP = "🆔 Añadir Identificador de Categoría 🆔"
REMOVE_CATEGORY_IDENTIFIER_MARKUP = "✖️ Eliminar Identificador ✖️"
ADD_CUSTOM_CONTENT_MARKUP = "📁 Añadir Contenido Personalizado 📁"
REMOVE_CUSTOM_CONTENT_MARKUP = "✖️ Eliminar Contenido ✖️"
CHANGE_CATEGORY_NAME_MARKUP = "🔤 Cambiar Nombre 🔤"
CUSTOMIZE_CATEGORY_MARKUP = "⚙ Configurar Categoría ⚙"
CAN_PIN_TEMPLATES_MARKUP = "📌 Anclar Plantillas: {} 📌"
SEE_CATEGORY_IDENTIFIERS_MARKUP = ""
CHANGE_CATEGORY_FORMAT_MARKUP = ""
SEE_FORMAT_MARKUP = ""
DELETE_CATEGORY_FORMAT_MARKUP = ""
REORDER_CUSTOM_CONTENTS_MARKUP = ""
SEE_CATEGORY_FORMAT_MARKUP = ""
CHANGE_TEMPLATE_FORMAT_MARKUP = ""
SEE_TEMPLATE_FORMAT_MARKUP = ""
ADD_TEMPLATE_CONTENT_MARKUP = ""
SEE_TEMPLATE_CONTENT_MARKUP = ""
REMOVE_TEMPLATE_CONTENT_MARKUP = ""
SEE_CUSTOM_CONTENTS_MARKUP = ""  # Markups

REGISTER_HELP = "➕ Registrar Canal:\n"\
                "Este es un paso obligatorio para que el bot funcione en tu canal, " \
                "registra tu canal en el sistema (debes ser admin de este, " \
                "al igual que el bot) y te permitirá configurarlo."
UNREGISTER_HELP = "➖ Cancelar Registro de Canal:\n" \
                  "En el caso de que no quieras seguir usando el bot en tu canal, " \
                  "deberías cancelar su registro, esto se hará automáticamente si " \
                  "eliminas al bot del canal y dejas que pase un tiempo, un canal " \
                  "eliminado del registro perdera todas sus configuraciones."
CUSTOMIZE_HELP = "⚙ Configurar Canal:\n" \
                 "Entrar aquí tambien es obligatorio para que funcione correctamente " \
                 "el bot y es donde pasarás la mayor parte del tiempo. [Más ayuda dentro]"

SEND_NOW_HELP = "✅ Enviar resumen ahora:\n" \
                "Si tienes un resumen válido " \
                "este será enviado inmediatamente al canal, se recomienda " \
                "hacer esto apenas termines de configurar el bot, ya que de " \
                "todas formas se actualiza automaticamente con todos los mensajes " \
                "que lleguen al canal. Enviar el resumen inmediatamente hará que " \
                "se reinicie el tiempo para enviar un nuevo resumen."
FIND_PROBLEMS_HELP = "⚠ Buscar Problemas:\n" \
                     "Este botón puedes usarlo cuando termines de configurar el bot, " \
                     "o cuando encuentres algún problema con tu resumen. Detecta " \
                     "problemas o errores que pueda tener tu configuración."
CHANGE_TEMPLATE_HELP = """
📋 Cambiar Plantilla:
Este botón es fundamental al configurar tu bot, ya que crearás la plantilla con la que el bot hará todos los resúmenes.
Si usas categorías (más acerca de las categorías más adelante), los mensajes del resumen se colocarán en diferentes lugares de la plantilla en dependencia de la categoría a la que pertenezcan, estos lugares los definirás tú mismo con las etiquetas de $plantilla#$, donde # es el número de la categoría, por ejemplo:
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
Este un ejemplo de plantilla perfectamente válido que usa categorías.
Si, por el contrario, no necesitas utilizar categorías ya que tu canal sube un solo tipo de contenido, debes usar la etiqueta $plantilla$, por ejemplo:
——————————
Resumen diario :D

$plantilla$

Se actualiza automático :3
——————————
"""
CHANGE_TEMPLATE_PICTURE_HELP = """
📷  Cambiar Foto de Plantilla:
Las plantillas pueden estar acompañadas opcionalmente de una foto que será enviada en el mensaje anterior a la plantilla, no se envían en el mismo mensaje ya que los mensajes con fotos tienen un limite de caracteres mucho mas corto que los mensajes de texto normales."""
CATEGORIES_MENU_HELP = """
🔠 Categorías:
Las categorías se usan cuando necesitas dividir el contenido de tu canal en diferentes secciones, por ejemplo "Información", "Juegos", etc. [Más ayuda dentro]"""
CHANGE_SUMMARY_TIME_HELP = """
🕑 Cambiar horario:
Con este botón puedes cambiar cada cuántas horas se envía un resumen al canal, por defecto tiene un valor de 24h. Los resúmenes son actualizados de la manera siguiente:
-Al enviarse un resumen este contendra todo lo que se ha enviado al canal desde el último resumen.
-Todo lo que se envíe al canal se seguirá añadiendo al último resumen que se envió.
-Al enviar el próximo resumen el anterior dejará de actualizarse y este nuevo resumen será el que se actualice."""
CHANGE_TEMPLATE_FORMAT_HELP = """
📑 Cambiar Formato de Plantilla:
Puedes cambiar el formato de cada elemento que sera enviado al resumen, por defecto este formato es:
-{titulo} {partes}
Que para el título Forza Horizon 4 y las partes 100-200 quedaría por ejemplo:
-Forza Horizon 4 [100-200]
Pero puedes cambiarlo a que sea lo que quieras, siempre y cuando contenga la etiqueta de {titulo} (la etiqueta de las partes es opcional y los corchetes [ ] se añaden automáticamente), por ejemplo:
=+={partes} {titulo} {partes}=+=
Quedaría:
=+=[100-200] Forza Horizon 4 [100-200]=+="""
CHANGE_PARTS_ID_HELP = """
📚 Cambiar Identificador de Partes:
Aquí podrás establecer el identificador con el que el bot busca las partes enviadas en el texto del mensaje, en este ejemplo de mensaje:
——————————————————
🌀Juego:  Forza Horizon 4
🔗Partes Enviadas: 2501-3000
⚙️Partes Totales:  6204
🕘Vencimiento:  4am

📥 Descarga el txt aquí 📥

🔰Mas info sobre el juego aquí 🔰

Para mas como esto visitad @Force_GamesS3 no se van a arrepentir😁🎉
——————————————————
El identificador de partes es "🔗Partes Enviadas:", dicho texto será eliminado a la hora de pasar las partes al formato, asi que solo quedaría "2501-3000"
"""

ADD_CATEGORY_HELP = """
➕ Añadir Categría:
Añade una nueva categoría, se te pedirá que des el identificador de esta, el identificador es el texto que esta antes del título de lo que se suba al canal, por ejemplo:
"🌀Juego:  Forza Horizon 4"
el identificador seria "🌀Juego:", y en el resumen lo único que se mostraría sería "Forza Horizon 4"
"""
REMOVE_CATEGORY_HELP = """
✖ Eliminar Categoría:
A cada categoría se le asigna un número comenzando por el 0 que será donde se colocará en la plantilla, por ejemplo los mensajes que entren en la categoría 0 se colocarán en la etiqueta $plantilla0$ de la plantilla.
Al eliminar se te mostrarán las categorías que has añadido y los números que ocupan, y debes decir el número que quieres que se elimine."""
REORDER_CATEGORIES_HELP = """
↕ Reordenar Categorías:
 Este botón te permitirá seleccionar una categoría y moverla en la lista."""

MAX_KNOWN_CHANNELS = 5
MAX_CHARACTERS_IN_TITLE = 64

BACKUP_TIME_DIF = 20  # minutes

admin_chat_id = -1

registered_channels: dict[str, RegisteredChannel] = {}
registered_users: dict[str, RegisteredUser] = {}

if BOT_CLOUD is not None and BOT_CLOUD != "":
    bot_cloud = bot.get_chat(BOT_CLOUD)
else:
    bot_cloud = None

update_checker: list[datetime] = []


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


def broadcast(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_user.id == admin_chat_id:
        for user in registered_users.values():
            try:
                bot.send_message(user.chat_id, update.message.text.replace("/broadcast", ""))
            except TelegramError:
                registered_users.pop(str(user.chat_id))


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def fix(update, context):
    return


def cleanup():
    for channel in registered_channels:
        try:
            member = bot.get_chat_member(channel, bot.get_me().id)
            if member is None:
                registered_channels.pop(channel)
        except TelegramError:
            registered_channels.pop(channel)


def get_chat_id(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_user.id == admin_chat_id:
        if len(context.args) > 0:
            try:
                update.message.reply_text(str(bot.get_chat(context.args[0]).id))
            except TelegramError:
                update.message.reply_text("Chat no encontrado.")


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
    # Commands


def auto_update():
    for channel in registered_channels:
        try_post_summary(channel)


def auto_backup():
    if bot_cloud is not None:
        cleanup()
        auto_update()
        serialize_bot_data("bot_data.json")
        file = open("bot_data.json", "rb")
        result = bot_cloud.send_document(document=file, filename="bot_data.json")
        bot_cloud.pin_message(result.message_id)
        file.close()
        global update_timer
        try:
            update_timer.cancel()
        except RuntimeError:
            logger.error("Couldn't cancel timer")
        finally:
            update_timer = Timer(BACKUP_TIME_DIF * 60, auto_backup)
            update_timer.start()


def auto_restore():
    if len(update_checker) == 0 and bot_cloud is not None and bot_cloud.pinned_message is not None:
        logger.info("Performing data restore.")
        t_file = bot_cloud.pinned_message.document.get_file()
        update_checker.append(datetime.now())
        deserialize_bot_data(t_file.download())


def get_categories_list_text(reg_channel, highlight: Optional[int] = -1):
    """
    Args:
        reg_channel (RegisteredChannel)
        highlight
    Returns:
        str: Formatted list of categories.
    """
    if not reg_channel.categories:
        return ""
    return "\n".join(["{}{}{}-{}{}".format(
        ("", "__*")[highlight == i],
        i,
        ("\\", "")[highlight == -1],
        (escape_for_telegram(reg_channel.categories[i].name), reg_channel.categories[i])[highlight == -1],
        ("", "*__")[highlight == i])
        for i in range(len(reg_channel.categories))])


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

    delta = timedelta(hours=reg_channel.template_time_dif)
    target_time = reg_channel.last_summary_time + delta
    if datetime.now() > target_time:
        post_summary(atusername)


def post_summary(channel_username):
    """

    Args:
        channel_username (str)

    Returns:
        bool: True if the message was succesfully posted, False otherwise
    """
    atusername = get_at_username(channel_username)
    reg_channel = registered_channels[atusername]

    bot_member = get_bot_chat_member(atusername)
    can_pin = reg_channel.pin_summaries
    if not bot_member.can_post_messages:
        return False
    if can_pin and not bot_member.can_edit_messages:
        can_pin = False

    if reg_channel.template != "":
        if reg_channel.template_picture is not None and reg_channel.template_picture != "":
            bot.send_photo(chat_id=reg_channel.chat_id, photo=reg_channel.template_picture,
                           reply_markup=ReplyKeyboardRemove())
        text = get_template_string(atusername, reg_channel.saved_messages)
        summary_id = bot.send_message(chat_id=reg_channel.chat_id,
                                      text=text,
                                      parse_mode='MarkdownV2',
                                      disable_web_page_preview=True).message_id
        if can_pin:
            bot.pin_chat_message(reg_channel.chat_id, summary_id)
        reg_channel.last_summary_message_text = text
        reg_channel.last_summary_message_id = summary_id
        reg_channel.last_saved_messages = reg_channel.saved_messages
        reg_channel.last_summary_time = datetime.now()
        return True
    return False


def get_bot_chat_member(chat_username):
    """
    Args:
        chat_username (str)

    Returns:
        telegram.ChatMember: The bot's member in the target chat

    """
    atusername = get_at_username(chat_username)
    chat: telegram.Chat = bot.get_chat(chat_username)
    bot_user: telegram.User = bot.get_me()
    return chat.get_member(bot_user.id)


def add_to_last_summary(chat, message):
    """

    Args:
        chat (telegram.Chat)
        message (telegram.Message)

    """
    atusername = get_at_username(chat.username)
    reg_channel = registered_channels[atusername]

    if reg_channel.last_summary_message_id != -1:
        bot_member = get_bot_chat_member(atusername)
        if not bot_member.can_post_messages:
            bot.send_message(chat_id=admin_chat_id,
                             text="Send Message permission denied in {}".
                             format(atusername))
            return
        add_to_last_summary_messages(atusername, message)
        text = get_template_string(atusername, reg_channel.last_saved_messages)
        if text != reg_channel.last_summary_message_text:
            try:
                bot.edit_message_text(chat_id=chat.id,
                                      message_id=reg_channel.last_summary_message_id,
                                      text=text,
                                      disable_web_page_preview=True,
                                      parse_mode='MarkdownV2')
                reg_channel.last_summary_message_text = text
            except TelegramError:
                reg_channel.last_summary_message_id = -1


def elements_in_text(text: str, elements: list[str]) -> str:
    for el in elements:
        if el in text:
            return el
    return ""


def get_cat_from_alias(alias: str, categories: list[Category]) -> Category:
    for cat in categories:
        if alias in cat.identifiers:
            return cat


def get_message_data(username, message):
    """

       Args:
           username (str)
           message (telegram.Message)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    title = ""
    category = None
    custom_content = []

    if message.text is not None:
        text = message.text
    elif message.caption is not None:
        text = message.caption
    else:
        return title, category, custom_content

    split = text.splitlines()

    if reg_channel.categories:
        for cat in reg_channel.categories:
            for i in range(len(split)):
                alias = elements_in_text(split[i], cat.identifiers)
                if alias:
                    category = alias
                    if split[i].replace(alias, "").strip():
                        title = split[i]
                    else:
                        for e in range(i + 1, len(split)):
                            if split[e].strip():
                                title = split[e]
                                break
                    break
        if category and title:
            for line in split:
                content = elements_in_text(line, get_cat_from_alias(category,
                                                                    reg_channel.categories).custom_content_identifiers)
                if content:
                    custom_content.append(line)
    else:
        for line in split:
            if line.strip():
                title = line
                break

    if len(title) > MAX_CHARACTERS_IN_TITLE:
        title = title[0:MAX_CHARACTERS_IN_TITLE - 1] + "..."

    return title, category, custom_content


def delete_old_messages(username):
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    now = datetime.now()
    _24h = timedelta(hours=24)
    for message in reg_channel.saved_messages:
        late_time = message.message_time + _24h
        if now > late_time:
            reg_channel.saved_messages.remove(message)


def add_to_saved_messages(username, message):
    """

       Args:
           username (str)
           message (telegram.Message)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    title, category, custom_content = get_message_data(atusername, message)

    if title and (category or not reg_channel.categories):
        reg_channel.saved_messages.append(
            SavedMessage(message.message_id, title, datetime.now(), custom_content, category))

    delete_old_messages(atusername)


def add_to_last_summary_messages(username, message):
    """

    Args:
        username (str)
        message (telegram.Message)

    """
    atusername = get_at_username(username)
    reg_channel = registered_channels[atusername]

    title, category, custom_content = get_message_data(atusername, message)

    if title and (category or not reg_channel.categories):
        reg_channel.last_saved_messages.append(
            SavedMessage(message.message_id, title, datetime.now(), custom_content, category))


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

    if reg_channel.categories:
        index = 0
        for cat in reg_channel.categories:
            if "$plantilla{}$".format(index) in template:
                if cat.template_format:
                    template_format = cat.template_format
                    cat_messages = []
                    for m in messages:
                        if m.category in cat.identifiers:
                            message = escape_for_telegram(template_format).replace(
                                        "$titulo$", "[{}]({})".format(
                                            escape_for_telegram(m.text.replace(m.category, "").strip()),
                                            get_message_link(username, m.message_id)))
                            for i in range(len(cat.custom_content_identifiers)):
                                if "$contenido{}$".format(i) in template_format:
                                    for content in m.custom_content:
                                        if cat.custom_content_identifiers[i] in content:
                                            message = message.replace("$contenido{}$".format(i),
                                                                      content.replace(cat.custom_content_identifiers[i], ""))
                                            break
                            cat_messages.append(message)
                else:
                    cat_messages = []
                    for m in messages:
                        if m.category in cat.identifiers:
                            message = "\\- [{}]({})".format(
                                    escape_for_telegram(m.text.replace(m.category, "").strip()),
                                    get_message_link(atusername, m.message_id))
                            for i in range(len(cat.custom_content_identifiers)):
                                for content in m.custom_content:
                                    if cat.custom_content_identifiers[i] in content:
                                        message += " " + content.replace(cat.custom_content_identifiers[i], "")
                                        break
                            cat_messages.append(message)
                if cat_messages:
                    template = template.replace("$plantilla{}$".format(index), "\n".join(cat_messages))
                else:
                    template_split = template.splitlines()
                    remove = []
                    for line in template_split:
                        if "$cabecera{}$".format(index) in line:
                            remove.append(line)
                        elif "$plantilla{}$".format(index) in line:
                            remove.append(line)
                    if len(remove) > 1:
                        for line in remove:
                            template_split.remove(line)
                    else:
                        template = template.replace("$plantilla{}$".format(index), "\\-")
            index += 1
    elif "$plantilla$" in template:
        if messages:
            final_messages = []
            for m in messages:
                message = "\\- [{}]({})".format(
                    escape_for_telegram(m.text.replace(m.category, "").strip()),
                    get_message_link(atusername, m.message_id))
                final_messages.append(message)
            template = template.replace("$plantilla$", "\n".join(final_messages))
        else:
            template = template.replace("$plantilla$", "\\-")
    template += "\n🤖📝 [\\[Bot de Resúmenes\\]](t.me/ForceGamesHelperBot) 📝🤖"
    return template


def is_admin(from_chat, user_id) -> tuple[bool, str]:
    """
    Args:
        from_chat (telegram.Chat)
        user_id (int)

    Returns:
        A tuple, Item 1 is True if user is admin and False otherwise,
            in this case Item 2 is the reason
    """
    if user_id == admin_chat_id:
        return True, ""
    if from_chat.type == "channel":
        try:
            bot_user: telegram.User = bot.get_me()
            bot_member = from_chat.get_member(bot_user.id)
            administrators = from_chat.get_administrators()
            if bot_member is not None:
                if bot_member not in administrators:
                    return False, "El bot no es administrador del canal"
                elif not bot_member.can_post_messages:
                    return False, "El bot no tiene permiso de publicar mensajes en el canal"
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
    json.dump(bot_data, file, cls=BotDataEncoder, indent="\t")
    file.close()


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
    if not username.startswith("@"):
        return username.lower()
    else:
        return "@" + username.lower()


def get_no_at_username(username):
    """

    Args:
        username (str)

    Returns:
        str: Returns username without @

    """
    if username.startswith("@"):
        return username[1:].lower()
    else:
        return username.lower()


def get_reg_user(user, chat):
    """
    Args:
        chat (telegram.Chat)
        user (telegram.User)

    Returns:
        RegisteredUser: Finds or creates a new registered user
    """
    str_id = str(user.id)
    if str_id not in registered_users:
        registered_users[str_id] = RegisteredUser(chat_id=chat.id)

    return registered_users[str_id]
    # Methods


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
    atusername = get_at_username(update.message.text)
    try:
        if atusername in registered_channels:
            admin_status = is_admin(bot.get_chat(atusername), update.effective_user.id)
            if admin_status[0]:
                go_to_customization(update, context)
                reg_user.context_data['channel'] = atusername
                add_to_known_channels(reg_user, atusername)
            else:
                update.message.reply_text(admin_status[1])
        else:
            update.message.reply_text("El canal " + atusername + " no está registrado 😗")
            go_to_base(update, context)
    except TelegramError:
        update.message.reply_text("El canal " + atusername + " no se encontró")
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
            [FIND_PROBLEMS_MARKUP],
            [TEMPLATE_MENU_MARKUP],
            [CATEGORIES_MENU_MARKUP],
            [CHANGE_SUMMARY_TIME_MARKUP],
            [HELP_MARKUP],
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text(text="¿Qué desea configurar? 🧐", reply_markup=markup)
    reg_user.status = "customizing"


def go_to_template(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    markup = ReplyKeyboardMarkup(
        [
            [CHANGE_TEMPLATE_MARKUP, SEE_TEMPLATE_MARKUP],
            [CHANGE_TEMPLATE_PICTURE_MARKUP, SEE_TEMPLATE_PICTURE_MARKUP, DELETE_TEMPLATE_PICTURE_MARKUP],
            [CHANGE_TEMPLATE_FORMAT_MARKUP, SEE_TEMPLATE_FORMAT_MARKUP, DELETE_TEMPLATE_FORMAT_MARKUP],
            [ADD_TEMPLATE_CONTENT_MARKUP, SEE_TEMPLATE_CONTENT_MARKUP, REMOVE_TEMPLATE_CONTENT_MARKUP],
            [CAN_PIN_TEMPLATES_MARKUP.format(("No", "Sí")[reg_channel.pin_summaries])],
            [HELP_MARKUP],
            [CANCEL_MARKUP],
        ], resize_keyboard=True
    )
    update.message.reply_text(text="Menú de Plantilla 🔡", reply_markup=markup)
    reg_user.status = "template"


def go_to_categories(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    markup = ReplyKeyboardMarkup(
        [
            [ADD_CATEGORY_MARKUP, REMOVE_CATEGORY_MARKUP],
            [CUSTOMIZE_CATEGORY_MARKUP],
            [REORDER_CATEGORIES_MARKUP],
            [HELP_MARKUP],
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    categories = get_categories_list_text(registered_channels[reg_user.context_data['channel']])
    if categories:
        categories = f"Categorías añadidas:\n{categories}"
    else:
        categories = "No ha añadido categorías."
    update.message.reply_text(text=f"Menú de categorías 🔢\n{categories}", reply_markup=markup)
    reg_user.status = "categories"


def go_to_category_customization(update, context):
    """
        Args:
            update (telegram.Update)
            context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    markup = ReplyKeyboardMarkup(
        [
            [CHANGE_CATEGORY_NAME_MARKUP],
            [ADD_CATEGORY_IDENTIFIER_MARKUP, SEE_CATEGORY_IDENTIFIERS_MARKUP, REMOVE_CATEGORY_IDENTIFIER_MARKUP],
            [CHANGE_CATEGORY_FORMAT_MARKUP, SEE_CATEGORY_FORMAT_MARKUP, DELETE_CATEGORY_FORMAT_MARKUP],
            [ADD_CUSTOM_CONTENT_MARKUP, SEE_CUSTOM_CONTENTS_MARKUP, REMOVE_CUSTOM_CONTENT_MARKUP],
            [REORDER_CUSTOM_CONTENTS_MARKUP],
            [HELP_MARKUP],
            [CANCEL_MARKUP],
        ], resize_keyboard=True
    )
    cat_name = reg_channel.categories[reg_user.context_data['category']].name
    update.message.reply_text(text=f"Editando Categoría \"{cat_name}\"", reply_markup=markup)
    reg_user.status = "customizing_category"


def find_problems(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    cat_count = len(reg_channel.categories)

    missing_template = False
    missing_template_tags = []
    missing_main_template_tag = False
    using_parts_but_no_id = False
    using_parts_id_but_no_format = False

    if reg_channel.template == "":
        missing_template = True
    elif cat_count > 0:
        for i in range(cat_count):
            tag = "$plantilla{}$".format(i)
            if tag not in reg_channel.template:
                missing_template_tags.append(tag)
    else:
        if "$plantilla$" not in reg_channel.template:
            missing_main_template_tag = True

    if reg_channel.template_format != "":
        if "{partes}" in reg_channel.template_format:
            if reg_channel.parts_identifier == "":
                using_parts_but_no_id = True
        elif reg_channel.parts_identifier != "":
            using_parts_id_but_no_format = True

    problems_text = ""
    if missing_template:
        problems_text = "❌ No has establecido una plantilla para este resumen y no podrá enviarse"
    elif missing_main_template_tag:
        problems_text = "❌ A tu plantilla le falta el texto '$plantilla$' para que pueda funcionar correctamente"
    elif len(missing_template_tags) > 0:
        problems_text = "❌ Tu resumen utiliza categorías, sin embargo no " \
                        "se encontraron las siguientes etiquetas:\n\n{}\n\n" \
                        "Recuerda que cuando usas categorías la etiqueta $plantilla$ no hace " \
                        "nada".format("\n".join(missing_template_tags))
    if using_parts_but_no_id:
        problems_text += "\n⚠ Tu formato de plantilla declara que usa identificador de partes, pero no has establecido uno"
    elif using_parts_id_but_no_format:
        problems_text += "\n⚠ Tu formato de plantilla declara que no usa identificador de partes, pero has establecido uno"

    if problems_text == "":
        problems_text = "✅ Perfecto!\nNo pude encontrar ningún problema en tu resumen!\n" \
                        "Si no está funcionando escríbele a @LeoAmaro01, el creador del bot!"
    update.message.reply_text(problems_text)


def request_change_format(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Introduzca el nuevo formato que desea utilizar{}".format(
        (", este canal está utilizando el formato por defecto\n'-{titulo} {partes}'",
         ", el formato actual es:\n{}".format(reg_channel.template_format))
        [reg_channel.template_format != ""]), reply_markup=markup)
    reg_user.status = "requested_format"


def change_format(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if "{titulo}" in update.message.text:
        reg_channel.template_format = update.message.text
        update.message.reply_text("Formato cambiado! :D")
        go_to_customization(update, context)
    else:
        update.message.reply_text("El formato debe contener la etiqueta {titulo} >:/")


def delete_format(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if reg_channel.template_format != "":
        reg_channel.template_format = ""
        update.message.reply_text("Formato eliminado, usa {} para crear uno nuevo.".format(CHANGE_TEMPLATE_FORMAT_MARKUP))
    else:
        update.message.reply_text("No se ha establecido un formato para este canal")


def request_change_parts_id(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    markup = ReplyKeyboardMarkup(
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
    )
    update.message.reply_text("Introduzca el nuevo identificador de partes que desea utilizar{}".format(
        ("", ", el identificador actual es:\n{}".format(reg_channel.parts_identifier))
        [reg_channel.parts_identifier != ""]), reply_markup=markup)
    reg_user.status = "requested_parts_id"


def change_parts_id(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    reg_channel.parts_identifier = update.message.text
    update.message.reply_text("Identificador cambiado! :D")
    go_to_customization(update, context)


def delete_parts_id(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if reg_channel.parts_identifier != "":
        reg_channel.parts_identifier = ""
        update.message.reply_text("Identificador eliminado, usa {} para crear uno nuevo.".format(CHANGE_PARTS_ID_MARKUP))
    else:
        update.message.reply_text("No se ha establecido un identificador de partes para este canal")


def delete_template_picture(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if reg_channel.template != "":
        reg_channel.template_picture = ""
        update.message.reply_text("Foto eliminada, usa {} para establecer una nueva.".format(CHANGE_TEMPLATE_PICTURE_MARKUP))
    else:
        update.message.reply_text("No se ha establecido una foto de resumen para este canal")


def base_help(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    update.message.reply_text(REGISTER_HELP)
    update.message.reply_text(UNREGISTER_HELP)
    update.message.reply_text(CUSTOMIZE_HELP)


def customize_help(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    update.message.reply_text(SEND_NOW_HELP)
    update.message.reply_text(FIND_PROBLEMS_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_PICTURE_HELP)
    update.message.reply_text(CATEGORIES_MENU_HELP)
    update.message.reply_text(CHANGE_SUMMARY_TIME_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_FORMAT_HELP)
    update.message.reply_text(CHANGE_PARTS_ID_HELP)


def categories_help(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    update.message.reply_text(ADD_CATEGORY_HELP)
    update.message.reply_text(REMOVE_CATEGORY_HELP)
    update.message.reply_text(REORDER_CATEGORIES_HELP)


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
    if update.message.text.strip(" \t") == "":
        update.message.reply_text("El identificador de la categoría no puede estar vacio")
        return
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
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if len(reg_channel.categories) > 0:
        markup = ReplyKeyboardMarkup(
            [
                [CANCEL_MARKUP]
            ], resize_keyboard=True
        )
        update.message.reply_text("Cuál es el número de la categoría que desea eliminar?",
                                  reply_markup=markup)
        reg_user.status = "requested_remove_category"
    else:
        update.message.reply_text("No se ha establecido ninguna categoría en este canal")


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
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if reg_channel.template != "":
        update.message.reply_text(reg_channel.template)
    else:
        update.message.reply_text("No se ha establecido una plantilla para este canal")


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
    reg_channel = registered_channels[reg_user.context_data['channel']]
    if reg_channel.template_picture != "":
        update.message.reply_photo(reg_channel.template_picture)
    else:
        update.message.reply_text("No ha establecido una foto para este canal.")


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
        "Diga cada cuántas horas debo enviar el resumen, sólo envíe el numero\nejemplo: \"24\"\nValor actual:{}"
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
        [
            [CANCEL_MARKUP]
        ], resize_keyboard=True
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


def help_handler(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    update.message.reply_text("Utiliza los botones de ayuda para obtener ayuda sobre el bot")


def backup(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_chat.id != admin_chat_id:
        return
    auto_backup()
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
        update_checker[0] = datetime.now()
    else:
        update.message.reply_text("That command must be a reply to the backup file")


def process_private_message(update, context):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.message is None:
        return
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
            base_help(update, context)
        else:
            update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
    elif status == "requested_customization":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_base(update, context)
        else:
            customize_channel(update, context)
    elif status == "template":
        pin_markup = CAN_PIN_TEMPLATES_MARKUP.format(
            ("No", "Sí")[registered_channels[reg_user.context_data['channel']].pin_summaries])
        if text == CHANGE_TEMPLATE_MARKUP:
            request_change_template(update, context)
        elif text == SEE_TEMPLATE_MARKUP:
            see_template(update, context)
        elif text == CHANGE_TEMPLATE_PICTURE_MARKUP:
            request_change_template_picture(update, context)
        elif text == SEE_TEMPLATE_PICTURE_MARKUP:
            see_template_picture(update, context)
        elif text == DELETE_TEMPLATE_PICTURE_MARKUP:
            delete_template_picture(update, context)
        elif text == pin_markup:
            switch_pin_summaries(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_customization(update, context)
        elif text == HELP_MARKUP:
            template_help(update, context)
        else:
            update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
    elif status == "customizing":
        if text == FIND_PROBLEMS_MARKUP:
            find_problems(update, context)
        elif text == CHANGE_SUMMARY_TIME_MARKUP:
            request_change_summary_time(update, context)
        elif text == CATEGORIES_MENU_MARKUP:
            go_to_categories(update, context)
        elif text == SEND_NOW_MARKUP:
            send_summary_now(update, context)
        elif text == TEMPLATE_MENU_MARKUP:
            go_to_template(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_base(update, context)
        elif text == HELP_MARKUP:
            customize_help(update, context)
        else:
            update.message.reply_text("Guat? No entendí :/ (recuerda que soy un bot y soy tonto X'''D")
    elif status == "categories":
        if text == ADD_CATEGORY_MARKUP:
            request_add_category(update, context)
        elif text == REMOVE_CATEGORY_MARKUP:
            request_remove_category(update, context)
        elif text == CUSTOMIZE_CATEGORY_MARKUP:
            request_customize_category(update, context)
        elif text == REORDER_CATEGORIES_MARKUP:
            request_reorder_categories(update, context)
        elif text == HELP_MARKUP:
            categories_help(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_customization(update, context)
    elif status == "customizing_category":
        if text == CHANGE_CATEGORY_NAME_MARKUP:
            request_change_category_name(update, context)
        elif text == ADD_CATEGORY_IDENTIFIER_MARKUP:
            request_add_category_identifier(update, context)
        elif text == SEE_CATEGORY_IDENTIFIERS_MARKUP:
            see_category_identifiers(update, context)
        elif text == REMOVE_CATEGORY_IDENTIFIER_MARKUP:
            request_remove_category_identifier(update, context)
        elif text == CHANGE_CATEGORY_FORMAT_MARKUP:
            request_change_category_format(update, context)
        elif text == SEE_CATEGORY_FORMAT_MARKUP:
            see_category_format(update, context)
        elif text == DELETE_CATEGORY_FORMAT_MARKUP:
            delete_category_format(update, context)
        elif text == ADD_CUSTOM_CONTENT_MARKUP:
            request_add_custom_content(update, context)
        elif text == SEE_CATEGORY_FORMAT_MARKUP:
            see_custom_contents(update, context)
        elif text == DELETE_CATEGORY_FORMAT_MARKUP:
            request_remove_custom_contents(update, context)
        elif text == REORDER_CUSTOM_CONTENTS_MARKUP:
            request_remove_custom_contents(update, context)
        elif text == HELP_MARKUP:
            category_customization_help(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
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
    elif status == "requested_format":
        if text == CANCEL_MARKUP:
            go_to_customization(update, context)
        else:
            change_format(update, context)
    elif status == "requested_parts_id":
        if text == CANCEL_MARKUP:
            go_to_customization(update, context)
        else:
            change_parts_id(update, context)
    elif status == "":
        go_to_base(update, context)


def process_private_photo(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    if update.message is None:
        return
    auto_restore()
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    status = reg_user.status
    if status == "requested_template_picture":
        change_template_picture(update, context)
    else:
        update.message.reply_text("Quejeso? Tus nudes? :0")


def process_channel_update(update, context):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    auto_restore()
    if update.channel_post is None:
        return

    chat = update.effective_chat
    atusername = get_at_username(chat.username)
    if atusername not in registered_channels:
        return
    reg_channel = registered_channels[atusername]
    add_to_saved_messages(atusername, update.channel_post)
    add_to_last_summary(chat, update.channel_post)

    try_post_summary(atusername)    # Updates
    # Updates


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
    dp.add_handler(CommandHandler("fix", fix))
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(CommandHandler("restore", restore))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("getchatid", get_chat_id))
    dp.add_handler(CommandHandler("stats", stats))

    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, process_private_message))
    dp.add_handler(MessageHandler(Filters.photo & Filters.chat_type.private, process_private_photo))

    dp.add_handler(MessageHandler(Filters.chat_type.channel & (Filters.text | Filters.caption),
                                  process_channel_update))

    auto_restore()
    auto_backup()

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN,
                          webhook_url='https://forcegameshelper.herokuapp.com/' + TOKEN)

    updater.idle()


update_timer = Timer(BACKUP_TIME_DIF * 60, auto_backup)

if __name__ == '__main__':
    main()
