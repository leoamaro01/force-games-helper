import logging
import json

import telegram
import telegram.ext
import os
import re
from threading import Timer
from datetime import datetime, timedelta
from typing import Optional, Any
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, Bot, TelegramError, ReplyKeyboardRemove, \
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyMarkup

CHANNEL_VERSION = "1.1"
USER_VERSION = "1.0"
CATEGORY_VERSION = "1.1"
MESSAGE_VERSION = "1.1"


class BotDataEncoder(json.JSONEncoder):
    def default(self, obj):
        global CHANNEL_VERSION, USER_VERSION, CATEGORY_VERSION, MESSAGE_VERSION
        if isinstance(obj, RegisteredChannel):
            return {
                '__reg_channel__': True,
                '__version__': CHANNEL_VERSION,
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
                'pin_summaries': obj.pin_summaries,
                'template_format': obj.template_format,
                'identifiers': obj.identifiers,
                'template_contents': obj.template_contents,
                'send_automatically': obj.send_automatically
            }
        elif isinstance(obj, RegisteredUser):
            return {
                '__reg_user__': True,
                '__version__': USER_VERSION,
                'chat_id': obj.chat_id,
                'status': obj.status,
                'context_data': obj.context_data,
                'known_channels': obj.known_channels
            }
        elif isinstance(obj, SavedMessage):
            return {
                '__saved_message__': True,
                '__version__': MESSAGE_VERSION,
                'text': obj.text,
                'id': obj.message_id,
                'cat': obj.category,
                'message_time': obj.message_time.isoformat(),
                'custom_contents': obj.custom_contents
            }
        elif isinstance(obj, Category):
            return {
                '__category__': True,
                '__version__': CATEGORY_VERSION,
                'name': obj.name,
                'identifiers': obj.identifiers,
                'category_contents': obj.category_contents,
                'template_format': obj.template_format
            }
        return json.JSONEncoder.default(self, obj)


def decode_bot_data(dct: dict):
    global CHANNEL_VERSION, USER_VERSION, CATEGORY_VERSION, MESSAGE_VERSION
    if '__reg_channel__' in dct:
        if "__version__" not in dct or dct['__version__'] != CHANNEL_VERSION:
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
                                     pin_summaries=dct['pin_summaries'],
                                     template_format=dct['template_format'],
                                     identifiers=dct['identifiers'],
                                     template_contents=dct['template_contents'],
                                     send_automatically=dct['send_automatically'])
    elif '__reg_user__' in dct:
        if "__version__" not in dct or dct['__version__'] != USER_VERSION:
            return decode_legacy_data(dct)
        else:
            return RegisteredUser(chat_id=dct['chat_id'],
                                  status=dct['status'],
                                  context_data=dct['context_data'],
                                  known_channels=dct['known_channels'])
    elif '__saved_message__' in dct:
        if "__version__" not in dct or dct['__version__'] != MESSAGE_VERSION:
            return decode_legacy_data(dct)
        else:
            return SavedMessage(message_id=dct['id'],
                                text=dct['text'],
                                category=dct['cat'],
                                custom_contents=dct['custom_contents'],
                                message_time=datetime.fromisoformat(dct['message_time']))
    elif '__category__' in dct:
        if "__version__" not in dct or dct['__version__'] != MESSAGE_VERSION:
            return decode_legacy_data(dct)
        else:
            return Category(name=dct['name'],
                            identifiers=dct['identifiers'],
                            category_contents=dct['category_contents'],
                            template_format=dct['template_format'])
    return dct


# TODO
def decode_legacy_data(dct: dict):
    global CHANNEL_VERSION, USER_VERSION, CATEGORY_VERSION, MESSAGE_VERSION
    if '__reg_channel__' in dct:
        if "__version__" not in dct:
            return None  # TODO
        elif dct['__version__'] == "1.0":
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
                                     pin_summaries=dct['pin_summaries'],
                                     template_format=dct['template_format'],
                                     identifiers=dct['identifiers'],
                                     template_contents=dct['contents'],
                                     send_automatically=dct['send_automatically'])
    elif '__reg_user__' in dct:
        if "__version__" not in dct:
            return None  # TODO
        elif dct['__version__'] == "1.0":
            return None  # Yet unused
    elif '__saved_message__' in dct:
        if "__version__" not in dct:
            return None  # TODO
        elif dct['__version__'] == "1.0":
            return SavedMessage(message_id=dct['id'],
                                text=dct['text'],
                                category=dct['cat'],
                                custom_contents=dct['custom_content'],
                                message_time=datetime.fromisoformat(dct['message_time']))
    elif '__category__' in dct:
        if "__version__" not in dct:
            return None  # TODO
        elif dct['__version__'] == "1.0":
            return Category(name=dct['name'],
                            identifiers=dct['identifiers'],
                            category_contents=dct['category_content'],
                            template_format=dct['template_format'])
    return dct


class SavedMessage:
    def __init__(self, message_id: int, text: str, message_time: datetime,
                 custom_contents: Optional[list[str]], category: Optional[str] = ""):
        self.message_id = message_id
        self.text = text
        self.category = category
        self.message_time = message_time
        self.custom_contents = custom_contents


class Category:
    def __init__(self, name: str = "", identifiers: str = None,
                 category_contents: list[str] = None, template_format: str = ""):
        self.name = name
        self.template_format = template_format
        if identifiers is not None:
            self.identifiers = identifiers
        else:
            self.identifiers = []
        if category_contents is not None:
            self.category_contents = category_contents
        else:
            self.category_contents = []


class RegisteredChannel:
    def __init__(self, chat_id: int = 0, template: str = "", template_picture: str = "",
                 template_time_dif: int = 24, saved_messages: list[SavedMessage] = None,
                 last_saved_messages: list[SavedMessage] = None, last_summary_message_id: int = -1,
                 categories: list[Category] = None, last_summary_time: datetime = None,
                 last_summary_message_text: str = "", pin_summaries: bool = True,
                 template_format: str = "", template_contents: list[str] = None,
                 identifiers: list[str] = None, send_automatically: bool = True):
        self.chat_id = chat_id
        self.template = template
        self.template_picture = template_picture
        self.template_time_dif = template_time_dif
        self.last_summary_message_id = last_summary_message_id
        self.last_summary_message_text = last_summary_message_text
        self.pin_summaries = pin_summaries
        self.template_format = template_format
        self.send_automatically = send_automatically
        if identifiers is not None:
            self.identifiers = identifiers
        else:
            self.identifiers: list[str] = []
        if template_contents is not None:
            self.template_contents = template_contents
        else:
            self.template_contents: list[str] = []
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


class RegisteredUser:
    def __init__(self, chat_id: int = 0, status: str = "", context_data: list = None,
                 known_channels: list[str] = None):
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
WEBHOOK = os.environ.get("WEBHOOK")
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

SEE_TEMPLATE_MARKUP = "📃 Ver Plantilla 📃"
SEE_TEMPLATE_PICTURE_MARKUP = "📹 Ver Foto Actual 📹"
CHANGE_TEMPLATE_PICTURE_MARKUP = "📷 Cambiar Foto de Plantilla 📷"
CHANGE_TEMPLATE_MARKUP = "📋 Cambiar Plantilla 📋"
DELETE_TEMPLATE_FORMAT_MARKUP = "🗑 Eliminar Formato 🗑"
DELETE_TEMPLATE_PICTURE_MARKUP = "🗑 Eliminar Foto 🗑"
CHANGE_TEMPLATE_FORMAT_MARKUP = "Cambiar Formato"
SEE_TEMPLATE_FORMAT_MARKUP = "Ver Formato"
ADD_TEMPLATE_CONTENT_MARKUP = "Añadir Contenido Personalizado"
SEE_TEMPLATE_CONTENT_MARKUP = "Ver Contenidos Personalizados"
REMOVE_TEMPLATE_CONTENT_MARKUP = "Eliminar Contenido Personalizado"
ADD_TEMPLATE_IDENTIFIER_MARKUP = "Añadir Identificador"
SEE_TEMPLATE_IDENTIFIERS_MARKUP = "Ver Identificadores"
REMOVE_TEMPLATE_IDENTIFIER_MARKUP = "Eliminar Identificador"
REORDER_TEMPLATE_CONTENT_MARKUP = "Reordenar Contenidos Personalizados"
CAN_PIN_TEMPLATES_ON_MARKUP = "📌 Anclar Plantillas: Sí 📌"
CAN_PIN_TEMPLATES_OFF_MARKUP = "📌 Anclar Plantillas: No 📌"

SEND_NOW_MARKUP = "✅ Enviar Resumen Ahora ✅"
CHANGE_SUMMARY_TIME_MARKUP = "🕑 Cambiar Horario de los Resúmenes 🕑"
CATEGORIES_MENU_MARKUP = "🔠 Categorías 🔠"
TEMPLATE_MENU_MARKUP = "📄 Plantilla 📄"
SEND_AUTOMATICALLY_ON_MARKUP = "🤖 Enviar Automáticamente: Sí 🤖"
SEND_AUTOMATICALLY_OFF_MARKUP = "🤖 Enviar Automáticamente: No 🤖"
FIND_PROBLEMS_MARKUP = "⚠ Buscar Problemas ⚠"

SEE_CATEGORIES_MARKUP = "🔢 Ver Categorías 🔢"
ADD_CATEGORY_MARKUP = "➕ Añadir Categoría ➕"
REMOVE_CATEGORY_MARKUP = "✖️ Eliminar Categoría ✖️"
REORDER_CATEGORIES_MARKUP = "⬆️ Reordenar Categorías ⬇️"
CUSTOMIZE_CATEGORY_MARKUP = "⚙ Configurar Categoría ⚙"

ADD_CATEGORY_IDENTIFIER_MARKUP = "🆔 Añadir Identificador de Categoría 🆔"
REMOVE_CATEGORY_IDENTIFIER_MARKUP = "✖️ Eliminar Identificador ✖️"
REMOVE_CATEGORY_CONTENT_MARKUP = "✖️ Eliminar Contenido ✖️"
CHANGE_CATEGORY_NAME_MARKUP = "🔤 Cambiar Nombre 🔤"
SEE_CATEGORY_IDENTIFIERS_MARKUP = "Ver Idenfiticadores"
DELETE_CATEGORY_FORMAT_MARKUP = "Eliminar Formato"
REORDER_CATEGORY_CONTENTS_MARKUP = "Reordenar Contenidos Personalizados"
CHANGE_CATEGORY_FORMAT_MARKUP = "Cambiar Formato"
SEE_CATEGORY_FORMAT_MARKUP = "Ver Formato"
SEE_CATEGORY_CONTENTS_MARKUP = "Ver Contenidos Personalizados"
ADD_CATEGORY_CONTENT_MARKUP = "📁 Añadir Contenido Personalizado 📁"

MOVE_UP_MARKUP = "🔼 Mover Arriba 🔼"
MOVE_DOWN_MARKUP = "🔽 Mover Abajo 🔽"
DONE_MARKUP = "✅ Hecho ✅"

HELP_MARKUP = "ℹ Ayuda ℹ"
# Markups

REGISTER_HELP = "➕ Registrar Canal:\n" \
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
WARNING_TEMPLATE_LENGTH = 1024
MAX_TEMPLATE_LENGTH = 2048
BOT_AD = "\n🤖📝 [\\[Bot de Resúmenes\\]](t.me/ForceGamesHelperBot) 📝🤖"

BACKUP_TIME_DIF = 25  # minutes

admin_chat_id = -1

registered_channels: dict[str, RegisteredChannel] = {}
registered_users: dict[str, RegisteredUser] = {}

if BOT_CLOUD is not None and BOT_CLOUD != "":
    bot_cloud = bot.get_chat(BOT_CLOUD)
else:
    bot_cloud = None

update_checker: list[datetime] = []


def start(update: telegram.Update, context: telegram.ext.CallbackContext):
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


def broadcast(update: telegram.Update, context: telegram.ext.CallbackContext):
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


def error(update: telegram.Update, context: telegram.ext.CallbackContext):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def fix(update: telegram.Update, context: telegram.ext.CallbackContext):
    return


def cleanup():
    for channel in registered_channels:
        try:
            member = bot.get_chat_member(channel, bot.get_me().id)
            if member is None:
                registered_channels.pop(channel)
        except TelegramError:
            registered_channels.pop(channel)


def get_chat_id(update: telegram.Update, context: telegram.ext.CallbackContext):
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


def stats(update: telegram.Update, context: telegram.ext.CallbackContext):
    """
    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)
    """
    if update.effective_user.id == admin_chat_id:
        text = \
            "Registered Channels: {}\n" \
            "Registered Users: {}\n" \
            "Last Update: {}". \
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


def get_list_text(lst: list[str], highlight: Optional[int] = -1):
    if not lst:
        return ""
    return "\n".join(["{}{}{}-{}{}".format(
        ("", "__*")[highlight == i],
        i,
        ("\\", "")[highlight == -1],
        (escape_for_telegram(lst[i]), lst[i])[highlight == -1],
        ("", "*__")[highlight == i])
        for i in range(len(lst))])


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
        delta = timedelta(hours=reg_channel.template_time_dif)
        if datetime.now() > reg_channel.last_summary_time + delta:
            reg_channel.last_summary_time = reg_channel.last_summary_time + delta
        else:
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
            reg_channel.send_automatically = False
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


def send_request(update: telegram.Update, text: str, new_status: str, **kwargs):
    if 'reg_user' not in kwargs:
        reg_user, _, markup = get_update_data(update, new_status, nochannel=True, **kwargs)
    else:
        reg_user = kwargs['reg_user']
        markup = kwargs['markup']

    update.message.reply_text(text, reply_markup=markup)
    reg_user.status = new_status


def get_cat_from_alias(alias: str, categories: list[Category]) -> Category:
    for cat in categories:
        if alias in cat.identifiers:
            return cat


def get_update_data(update: telegram.Update, status: str = "", **kwargs) -> tuple[RegisteredUser, RegisteredChannel, ReplyMarkup]:
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = None
    markup = None
    if 'nochannel' not in kwargs and 'channel' in reg_user.context_data:
        reg_channel = registered_channels[reg_user.context_data['channel']]
        kwargs['reg_channel'] = reg_channel
    if 'nomarkup' not in kwargs:
        if status:
            markup = get_markup(status, **kwargs)
        elif reg_user.status:
            markup = get_markup(reg_user.status, **kwargs)

    return reg_user, reg_channel, markup


def get_markup(status, **kwargs) -> ReplyMarkup:
    if status == "base":
        return ReplyKeyboardMarkup([
            [CUSTOMIZE_MARKUP],
            [REGISTER_MARKUP, UNREGISTER_MARKUP],
            [HELP_MARKUP]
        ], resize_keyboard=True)
    elif status == "customizing":
        return ReplyKeyboardMarkup(
            [
                [SEND_NOW_MARKUP],
                [FIND_PROBLEMS_MARKUP],
                [TEMPLATE_MENU_MARKUP],
                [CATEGORIES_MENU_MARKUP],
                [SEND_AUTOMATICALLY_ON_MARKUP if kwargs['reg_channel'].send_automatically else SEND_AUTOMATICALLY_OFF_MARKUP],
                [CHANGE_SUMMARY_TIME_MARKUP],
                [HELP_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True)
    elif status == "template":
        return ReplyKeyboardMarkup(
            [
                [CHANGE_TEMPLATE_MARKUP, SEE_TEMPLATE_MARKUP],
                [CHANGE_TEMPLATE_PICTURE_MARKUP, SEE_TEMPLATE_PICTURE_MARKUP, DELETE_TEMPLATE_PICTURE_MARKUP],
                [ADD_TEMPLATE_IDENTIFIER_MARKUP, SEE_TEMPLATE_IDENTIFIERS_MARKUP, REMOVE_TEMPLATE_IDENTIFIER_MARKUP],
                [CHANGE_TEMPLATE_FORMAT_MARKUP, SEE_TEMPLATE_FORMAT_MARKUP, DELETE_TEMPLATE_FORMAT_MARKUP],
                [ADD_TEMPLATE_CONTENT_MARKUP, SEE_TEMPLATE_CONTENT_MARKUP, REMOVE_TEMPLATE_CONTENT_MARKUP],
                [REORDER_TEMPLATE_CONTENT_MARKUP],
                [CAN_PIN_TEMPLATES_ON_MARKUP if kwargs['reg_channel'].pin_summaries else CAN_PIN_TEMPLATES_OFF_MARKUP],
                [HELP_MARKUP],
                [CANCEL_MARKUP],
            ], resize_keyboard=True)
    elif status == "categories":
        return ReplyKeyboardMarkup(
            [
                [ADD_CATEGORY_MARKUP, REMOVE_CATEGORY_MARKUP],
                [CUSTOMIZE_CATEGORY_MARKUP],
                [REORDER_CATEGORIES_MARKUP],
                [HELP_MARKUP],
                [CANCEL_MARKUP]
            ], resize_keyboard=True)
    elif status == "customizing_category":
        return ReplyKeyboardMarkup(
            [
                [CHANGE_CATEGORY_NAME_MARKUP],
                [ADD_CATEGORY_IDENTIFIER_MARKUP, SEE_CATEGORY_IDENTIFIERS_MARKUP, REMOVE_CATEGORY_IDENTIFIER_MARKUP],
                [CHANGE_CATEGORY_FORMAT_MARKUP, SEE_CATEGORY_FORMAT_MARKUP, DELETE_CATEGORY_FORMAT_MARKUP],
                [ADD_CATEGORY_CONTENT_MARKUP, SEE_CATEGORY_CONTENTS_MARKUP, REMOVE_CATEGORY_CONTENT_MARKUP],
                [REORDER_CATEGORY_CONTENTS_MARKUP],
                [HELP_MARKUP],
                [CANCEL_MARKUP],
            ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup(
            [
                [CANCEL_MARKUP]
            ], resize_keyboard=True)


def get_message_data(username, message) -> tuple[str, Optional[Category], list[str]]:
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
            cat = get_cat_from_alias(category, reg_channel.categories)
            if cat.category_contents:
                for line in split:
                    content = elements_in_text(line, cat.category_contents)
                    if content:
                        custom_content.append(line)
            elif reg_channel.template_contents:
                for line in split:
                    content = elements_in_text(line, reg_channel.template_contents)
                    if content:
                        custom_content.append(line)
    else:
        if reg_channel.identifiers:
            for line in split:
                identifier = elements_in_text(line.strip(), reg_channel.identifiers)
                if identifier:
                    title = line
                    category = identifier
                    break
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

    if title and (category or (not reg_channel.categories and not reg_channel.identifiers)):
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

    if title and (category or (not reg_channel.categories and not reg_channel.identifiers)):
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
                            if cat.category_contents:
                                for i in range(len(cat.category_contents)):
                                    if "$contenido{}$".format(i) in template_format:
                                        for content in m.custom_contents:
                                            if cat.category_contents[i] in content:
                                                message = message.replace("$contenido{}$".format(i),
                                                                          content.replace(
                                                                              cat.category_contents[i], ""))
                                                break
                            elif reg_channel.template_contents:
                                for i in range(len(reg_channel.template_contents)):
                                    if "$contenido{}$".format(i) in template_format:
                                        for content in m.custom_contents:
                                            if reg_channel.template_contents[i] in content:
                                                message = message.replace("$contenido{}$".format(i),
                                                                          content.replace(reg_channel.template_contents[i],
                                                                                          ""))
                                                break
                            cat_messages.append(message)
                elif not reg_channel.template_format:
                    cat_messages = []
                    for m in messages:
                        if m.category in cat.identifiers:
                            message = "\\- [{}]({})".format(
                                escape_for_telegram(m.text.replace(m.category, "").strip()),
                                get_message_link(atusername, m.message_id))
                            for i in range(len(cat.category_contents)):
                                for content in m.custom_contents:
                                    if cat.category_contents[i] in content:
                                        message += " " + content.replace(cat.category_contents[i], "")
                                        break
                            cat_messages.append(message)
                else:
                    template_format = reg_channel.template_format
                    cat_messages = []
                    for m in messages:
                        if m.category in cat.identifiers:
                            message = escape_for_telegram(template_format).replace(
                                "$titulo$", "[{}]({})".format(
                                    escape_for_telegram(m.text.replace(m.category, "").strip()),
                                    get_message_link(username, m.message_id)))
                            if cat.category_contents:
                                for i in range(len(cat.category_contents)):
                                    if "$contenido{}$".format(i) in template_format:
                                        for content in m.custom_contents:
                                            if cat.category_contents[i] in content:
                                                message = message.replace("$contenido{}$".format(i),
                                                                          content.replace(
                                                                              cat.category_contents[i], ""))
                                                break
                            elif reg_channel.template_contents:
                                for i in range(len(reg_channel.template_contents)):
                                    if "$contenido{}$".format(i) in template_format:
                                        for content in m.custom_contents:
                                            if reg_channel.template_contents[i] in content:
                                                message = message.replace("$contenido{}$".format(i),
                                                                          content.replace(reg_channel.template_contents[i],
                                                                                          ""))
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

    if len(template) > 4096:
        template = template[0:4092 - len(BOT_AD)] + "..."

    template += BOT_AD
    return template


def is_admin(from_chat: telegram.chat, user_id: int) -> tuple[bool, str]:
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
                    return False, "No eres administrador de ese canal :/ eres tonto o primo de Javier?"
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


def get_at_username(username: str):
    if not username:
        return ""

    if username.startswith("@"):
        return username.lower()
    else:
        return "@" + username.lower()


def get_no_at_username(username):
    if not username:
        return ""

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


def go_to_base(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, _, markup = get_update_data(update, "base", nochannel=True)

    update.message.reply_text(text="Menú 🤓\nPuedes usar /cancel en cualquier momento para volver aquí :D",
                              reply_markup=markup)
    reg_user.status = "base"


def request_customize_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, _, _ = get_update_data(update, nochannel=True, nomarkup=True)
    markup = ReplyKeyboardMarkup(
        [[ch] for ch in reg_user.known_channels] + [[CANCEL_MARKUP]], resize_keyboard=True
    )

    send_request(update, "¿Cuál es la @ del canal que desea configurar? 🧐",
                 "requested_customization", reg_user=reg_user, markup=markup)


def customize_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, _, _ = get_update_data(update, nochannel=True, nomarkup=True)
    atusername = get_at_username(update.message.text)
    try:
        if atusername in registered_channels:
            admin_status = is_admin(bot.get_chat(atusername), update.effective_user.id)
            if admin_status[0]:
                reg_user.context_data['channel'] = atusername
                go_to_customization(update, context)
                add_to_known_channels(reg_user, atusername)
            else:
                update.message.reply_text(admin_status[1])
        else:
            update.message.reply_text("El canal " + atusername + " no está registrado 😗")
            go_to_base(update, context)
    except TelegramError:
        update.message.reply_text("El canal " + atusername + " no se encontró")
        go_to_base(update, context)


def go_to_customization(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "customizing")
    bot.send_message(chat_id=update.effective_chat.id, text="¿Qué desea configurar? 🤔", reply_markup=markup)
    reg_user.status = "customizing"


def go_to_template(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "template")
    bot.send_message(chat_id=update.effective_chat.id, text="Menú de Plantilla 🔡", reply_markup=markup)
    reg_user.status = "template"


def go_to_categories(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "categories")

    categories = get_list_text([c.name for c in reg_channel.categories])
    if categories:
        categories = f"Categorías añadidas:\n{categories}"
    else:
        categories = "No ha añadido categorías."
    bot.send_message(chat_id=update.effective_chat.id, text=f"Menú de categorías 🔢\n{categories}", reply_markup=markup)
    reg_user.status = "categories"


def go_to_category_customization(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "customizing_category")
    cat_name = reg_channel.categories[reg_user.context_data['category']].name
    bot.send_message(chat_id=update.effective_chat.id, text=f"Editando Categoría \"{cat_name}\"", reply_markup=markup)
    reg_user.status = "customizing_category"


# TODO
def find_problems(update: telegram.Update, context: telegram.ext.CallbackContext):
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


def request_remove_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_remove_template_content")

    if reg_channel.template_contents:
        send_request(update, "Cuál es el número del contenido que quiere eliminar?",
                     "requested_remove_template_content", reg_user=reg_user, markup=markup)
    else:
        update.message.reply_text("No ha añadido ningun Contenido Personalizado.")


def request_customize_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál es el número de la categoría que quiere configurar?", "requested_customize_category")


def request_change_category_name(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el nuevo nombre de esta categoría?", "requested_category_name")


def request_add_category_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el nuevo identificador de categoría?", "requested_category_identifier")


def request_remove_category_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_remove_category_identifier")
    category = reg_channel.categories[reg_user.context_data['category']]

    if category.identifiers:
        send_request(update, "Cuál es el número del identificador de categoría que desea eliminar?",
                     "requested_remove_category_identifier", reg_user=reg_user, markup=markup)
    else:
        update.message.reply_text("No ha añadido ningun identificador a esta categoría")


def see_category_identifiers(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    if category.identifiers:
        update.message.reply_text(get_list_text(category.identifiers))
    else:
        update.message.reply_text("No ha añadido ningun identificador a esta categoría")


def request_change_category_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el nuevo formato de la plantilla?", "requested_category_format")


def see_category_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    update.message.reply_text(reg_channel.categories[reg_user.context_data['category']].template_format)


def request_reorder_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "template")

    if len(reg_channel.template_contents) <= 1:
        update.message.reply_text("Solo puede reordenar contenidos luego de añadir 2 o más.")
        go_to_categories(update, context)
        return

    send_request(update, "Cuál es el número del contenido que desea mover?",
                 "requested_reorder_template_contents", reg_user=reg_user, markup=markup)


def switch_pin_summaries(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    reg_channel.pin_summaries = not reg_channel.pin_summaries

    update.message.reply_text("Ahora se anclarán los resúmenes al canal 📌" if reg_channel.pin_summaries
                              else "Ya no se anclarán los resúmenes al canal")
    go_to_template(update, context)


def switch_send_automatically(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    reg_channel.send_automatically = not reg_channel.send_automatically

    update.message.reply_text("Ahora se enviarán automáticamente los resúmenes al canal 🔁" if reg_channel.send_automatically
                              else "Ya no se enviarán automáticamente los resúmenes al canal")
    go_to_customization(update, context)


def request_change_template_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Introduzca el nuevo formato que desea utilizar", "requested_template_format")


def change_template_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if "$titulo$" in update.message.text:
        reg_channel.template_format = update.message.text
        update.message.reply_text("Formato cambiado! :D")
        go_to_template(update, context)
    else:
        update.message.reply_text("El formato debe contener la etiqueta $titulo$ >:/")


def see_template_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template_format:
        update.message.reply_text(reg_channel.template_format)
    else:
        update.message.reply_text("No se ha establecido un formato de plantilla")


def request_add_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el identificador del nuevo Contenido de Plantilla?",
                 "requested_template_content")


def add_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    text = update.message.text
    if not text.strip():
        update.message.reply_text("El identificador de plantilla no puede estar vacío.")

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    reg_channel.template_contents.append(text)

    update.message.reply_text(f"Contenido {text} añadido, para utilizarlo "
                              f"$contenido{len(reg_channel.template_contents) - 1}$"
                              f"debe estar presente en el formato de plantilla")
    go_to_template(update, context)


def see_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    _, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template_contents:
        update.message.reply_text(get_list_text(reg_channel.template_contents))
    else:
        update.message.reply_text("No ha añadido ningun Contenido Personalizado")


def delete_template_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template_format:
        reg_channel.template_format = ""
        update.message.reply_text(
            "Formato eliminado, usa {} para crear uno nuevo.".format(CHANGE_TEMPLATE_FORMAT_MARKUP))
    else:
        update.message.reply_text("No se ha establecido un formato para este canal")


def delete_category_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    if category.template_format:
        category.template_format = ""
        update.message.reply_text(
            "Formato eliminado, usa {} para crear uno nuevo.".format(CHANGE_TEMPLATE_FORMAT_MARKUP))
    else:
        update.message.reply_text("No se ha establecido un formato para este canal")


def request_add_category_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el identificador del nuevo Contenido de Categoría?",
                 "requested_category_content")


def see_category_contents(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    if category.category_contents:
        update.message.reply_text(get_list_text(category.category_contents))
    else:
        update.message.reply_text("No se ha establecido ningun contenido en esta categoría")


def request_remove_category_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_remove_category")
    category = reg_channel.categories[reg_user.context_data['category']]

    if len(category.category_contents) > 0:
        send_request(update, "Cuál es el número del contenido que desea eliminar?",
                     "requested_remove_category_content", reg_user=reg_user, markup=markup)
    else:
        update.message.reply_text("No se ha establecido ningun contenido en esta categoría")


def delete_template_picture(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template != "":
        reg_channel.template_picture = ""
        update.message.reply_text(
            "Foto eliminada, usa {} para establecer una nueva.".format(CHANGE_TEMPLATE_PICTURE_MARKUP))
    else:
        update.message.reply_text("No se ha establecido una foto de resumen para este canal")


def base_help(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(REGISTER_HELP)
    update.message.reply_text(UNREGISTER_HELP)
    update.message.reply_text(CUSTOMIZE_HELP)


# TODO
def category_customization_help(update: telegram.Update, context: telegram.ext.CallbackContext):
    return


def template_help(update: telegram.Update, context: telegram.ext.CallbackContext):
    return


def customize_help(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(SEND_NOW_HELP)
    update.message.reply_text(FIND_PROBLEMS_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_PICTURE_HELP)
    update.message.reply_text(CATEGORIES_MENU_HELP)
    update.message.reply_text(CHANGE_SUMMARY_TIME_HELP)
    update.message.reply_text(CHANGE_TEMPLATE_FORMAT_HELP)
    update.message.reply_text(CHANGE_PARTS_ID_HELP)


def categories_help(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(ADD_CATEGORY_HELP)
    update.message.reply_text(REMOVE_CATEGORY_HELP)
    update.message.reply_text(REORDER_CATEGORIES_HELP)


def request_add_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el nombre de la nueva categoría?", "requested_add_category")


def add_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    if not update.message.text.strip():
        update.message.reply_text("El nombre de la categoría no puede estar vacio")
        return
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]
    reg_channel.categories.append(Category(name=update.message.text.strip()))
    update.message.reply_text(
        f"Categoría {update.message.text.strip()} añadida! Para que esta funcione "
        f"$plantilla{len(reg_channel.categories) - 1}$ debe estar en el texto de la plantilla")
    go_to_categories(update, context)


def request_remove_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_remove_category")

    if len(reg_channel.categories) > 0:
        send_request(update, "Cuál es el número de la categoría que desea eliminar?",
                     "requested_remove_category", reg_user=reg_user, markup=markup)
    else:
        update.message.reply_text("No se ha establecido ninguna categoría en este canal")


def remove_template_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if index < 0 or index >= len(reg_channel.identifiers):
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_channel.identifiers.pop(index)
    update.message.reply_text("Identificador eliminado!")
    go_to_template(update, context)


def remove_category_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    if index < 0 or index >= len(category.identifiers):
        update.message.reply_text("Eso no es un número válido :/")
        return

    category.identifiers.pop(index)
    update.message.reply_text("Identificador eliminado!")
    go_to_category_customization(update, context)


def customize_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if index < 0 or index >= len(reg_channel.categories):
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user.context_data['category'] = index
    go_to_category_customization(update, context)


def remove_category_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    if index < 0 or index >= len(category.category_contents):
        update.message.reply_text("Eso no es un número válido :/")
        return

    category.category_contents.pop(index)
    update.message.reply_text("Contenido eliminado!")
    go_to_category_customization(update, context)


def remove_template_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if index < 0 or index >= len(reg_channel.template_contents):
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_channel.template_contents.pop(index)
    update.message.reply_text("Contenido eliminado!")
    go_to_template(update, context)


def remove_category(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if index < 0 or index >= len(reg_channel.categories):
        update.message.reply_text("Eso no es un número válido :/")
        return

    reg_channel.categories.pop(index)

    update.message.reply_text("Categoría eliminada.")
    go_to_categories(update, context)


def request_reorder_categories(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_reorder_categories")

    if len(reg_channel.categories) <= 1:
        update.message.reply_text("Solo puede reordenar categorías luego de añadir 2 o más.")
        go_to_categories(update, context)
        return

    send_request(update, "Cuál es el número de la categoría que desea mover?",
                 "requested_reorder_categories", reg_user=reg_user, markup=markup)


def request_reorder_category_contents(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_reorder_category_contents")
    category = reg_channel.categories[reg_user.context_data['category']]

    if len(category.category_contents) <= 1:
        update.message.reply_text("Solo puede reordenar contenidos luego de añadir 2 o más.")
        go_to_categories(update, context)
        return

    send_request(update, "Cuál es el número del contenido que desea mover?",
                 "requested_reorder_category_contents", reg_user=reg_user, markup=markup)


def add_template_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    if not update.message.text.strip():
        update.message.reply_text("El identificador de plantilla no puede estar vacío.")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    reg_channel.identifiers.append(update.message.text.strip())
    update.message.reply_text(f"Identificador \"{update.message.text.strip()}\" añadido!")
    go_to_template(update, context)


def request_add_template_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Cuál será el nuevo identificador de plantilla?", "requested_template_identifier")


def see_template_identifiers(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.identifiers:
        update.message.reply_text(get_list_text(reg_channel.identifiers))
    else:
        update.message.reply_text("No ha añadido ningún identificador a este canal")


def request_remove_template_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_remove_tempalte_identifier")
    if reg_channel.identifiers:
        send_request(update, "Cuál es el número del identificador que desea eliminar?", "requested_remove_template_identifier",
                     reg_user=reg_user, markup=markup)
    else:
        update.message.reply_text("No ha añadido ningún identificador a esta plantilla")
        go_to_template(update, context)


def reorder_list(update: telegram.Update, context: telegram.ext.CallbackContext, status: str, name_list: list[str]):
    try:
        index = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :c")
        return

    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if index < 0 or index >= len(name_list):
        update.message.reply_text("Eso no es un número válido :c")
        return

    move_up_button = InlineKeyboardButton(text=MOVE_UP_MARKUP, callback_data=MOVE_UP_MARKUP)
    move_down_button = InlineKeyboardButton(text=MOVE_DOWN_MARKUP, callback_data=MOVE_DOWN_MARKUP)
    done_button = InlineKeyboardButton(text=DONE_MARKUP, callback_data=DONE_MARKUP)

    if index == 0:
        markup = InlineKeyboardMarkup(
            [
                [move_down_button],
                [done_button]
            ], resize_keyboard=True
        )
    elif index == len(name_list) - 1:
        markup = InlineKeyboardMarkup(
            [
                [move_up_button],
                [done_button]
            ], resize_keyboard=True
        )
    else:
        markup = InlineKeyboardMarkup(
            [
                [move_up_button],
                [move_down_button],
                [done_button]
            ], resize_keyboard=True
        )
    update.message.reply_text(
        f"Utilice los botones para mover el elemento seleccionado:\n\n"
        f"{get_list_text(name_list, index)}\n\n"
        f"Presione {DONE_MARKUP} para terminar",
        reply_markup=markup,
        parse_mode="MarkdownV2")
    reg_user.status = status
    reg_user.context_data['index'] = index


def reorder_up(update: telegram.Update, context: telegram.ext.CallbackContext,
               source_list: list[Any], name_list: Optional[list[str]] = None):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    move_up_button = InlineKeyboardButton(text=MOVE_UP_MARKUP, callback_data=MOVE_UP_MARKUP)
    move_down_button = InlineKeyboardButton(text=MOVE_DOWN_MARKUP, callback_data=MOVE_DOWN_MARKUP)
    done_button = InlineKeyboardButton(text=DONE_MARKUP, callback_data=DONE_MARKUP)

    index = reg_user.context_data['index']
    name_list = name_list if name_list is not None else list(source_list)

    if index == 0:
        markup = InlineKeyboardMarkup(
            [
                [move_down_button],
                [done_button]
            ], resize_keyboard=True
        )
        update.message.reply_text("No se puede mover más arriba.")
    else:
        index -= 1
        item = name_list[index]
        name_list.pop(index)
        name_list.insert(index + 1, item)

        src_item = source_list[index]
        source_list.pop(index)
        source_list.insert(index + 1, src_item)

        if index == 0:
            markup = InlineKeyboardMarkup(
                [
                    [move_down_button],
                    [done_button]
                ], resize_keyboard=True
            )
        else:
            markup = InlineKeyboardMarkup(
                [
                    [move_up_button],
                    [move_down_button],
                    [done_button]
                ], resize_keyboard=True
            )
        reg_user.context_data['index'] = index
    update.callback_query.edit_message_text(
        f"Utilice los botones para mover el elemento seleccionado:\n\n"
        f"{get_list_text(name_list, index)}\n\n"
        f"Presione {DONE_MARKUP} para terminar",
        reply_markup=markup,
        parse_mode="MarkdownV2")


def reorder_down(update: telegram.Update, context: telegram.ext.CallbackContext,
                 source_list: list[Any], name_list: Optional[list[str]] = None):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    move_up_button = InlineKeyboardButton(text=MOVE_UP_MARKUP, callback_data=MOVE_UP_MARKUP)
    move_down_button = InlineKeyboardButton(text=MOVE_DOWN_MARKUP, callback_data=MOVE_DOWN_MARKUP)
    done_button = InlineKeyboardButton(text=DONE_MARKUP, callback_data=DONE_MARKUP)

    index = reg_user.context_data['index']
    name_list = name_list if name_list is not None else list(source_list)

    if index == len(name_list) - 1:
        markup = InlineKeyboardMarkup(
            [
                [move_up_button],
                [done_button]
            ], resize_keyboard=True
        )
        update.message.reply_text("No se puede mover más abajo.")
    else:
        index += 1
        item = name_list[index - 1]
        name_list.pop(index - 1)
        name_list.insert(index, item)

        src_item = source_list[index - 1]
        source_list.pop(index - 1)
        source_list.insert(index, src_item)
        if index == len(reg_channel.categories) - 1:
            markup = InlineKeyboardMarkup(
                [
                    [move_up_button],
                    [done_button]
                ], resize_keyboard=True
            )
        else:
            markup = InlineKeyboardMarkup(
                [
                    [move_up_button],
                    [move_down_button],
                    [done_button]
                ], resize_keyboard=True
            )
        reg_user.context_data['index'] = index
    update.callback_query.edit_message_text(
        f"Utilice los botones para mover el elemento seleccionado:\n\n"
        f"{get_list_text(name_list, index)}\n\n"
        f"Presione {DONE_MARKUP} para terminar",
        reply_markup=markup,
        parse_mode="MarkdownV2")


def request_change_template(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update,
                 "Envíe la nueva plantilla, debe contener el texto \"$plantilla$\" o "
                 "$plantilla#$ si usas categorias (donde # es el numero de la categoria) "
                 "que será donde se colocará el resumen 🤖.\nTampoco puede ser demasiado larga.",
                 "requested_template")


def change_category_name(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    category.name = update.message.text
    update.message.reply_text("Nombre de categoría cambiado! 😎")
    go_to_category_customization(update, context)


def change_category_format(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    new_format = update.message.text

    if "$titulo$" not in new_format:
        update.message.reply_text("El formato de categoría debe contener la etiqueta $titulo$")
        return

    category.template_format = new_format
    update.message.reply_text("Formato de categoría cambiado! 😎")
    go_to_category_customization(update, context)


def add_category_identifier(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    category.identifiers.append(update.message.text)

    update.message.reply_text("Identificador de categoría añadido!")
    go_to_category_customization(update, context)


def add_category_content(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)
    category = reg_channel.categories[reg_user.context_data['category']]

    category.category_contents.append(update.message.text)

    update.message.reply_text("Contenido de categoría añadido!")
    go_to_category_customization(update, context)


def change_template(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    new_template = update.message.text

    if len(new_template) > MAX_TEMPLATE_LENGTH:
        update.message.reply_text(f"❌ Esa plantilla excede el máximo de caracteres permitidos ({MAX_TEMPLATE_LENGTH}), intente acortarla")
        return
    elif len(new_template) > WARNING_TEMPLATE_LENGTH:
        update.message.reply_text(f"⚠️ Esa plantilla excede el número de caracteres recomendados ({WARNING_TEMPLATE_LENGTH}), es posible que no se publique correctamente si el canal recibe demasiado contenido")

    pattern = r"\$plantilla\d*\$"
    if not re.search(pattern, new_template):
        update.message.reply_text("Esa plantilla no contiene ninguna de las etiquetas $plantilla$ o $plantilla#$, debe contener una de las dos.")
        return

    reg_channel.template = new_template
    update.message.reply_text("Plantilla cambiada! 😎")
    go_to_template(update, context)


def see_template(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template:
        update.message.reply_text(reg_channel.template)
    else:
        update.message.reply_text("No se ha establecido una plantilla para este canal")


def request_change_template_picture(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Envíe la nueva foto de plantilla. 📸", "requested_template_picture")


def change_template_picture(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    reg_channel.template_picture = update.message.photo[-1].file_id
    update.message.reply_text("Foto establecida! :3")
    go_to_template(update, context)


def see_template_picture(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    if reg_channel.template_picture != "":
        update.message.reply_photo(reg_channel.template_picture)
    else:
        update.message.reply_text("No ha establecido una foto para este canal.")


def request_change_summary_time(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, markup = get_update_data(update, "requested_summary_time")

    send_request(update,
                 f"Diga cada cuántas horas debo enviar el resumen, sólo envíe el numero\nEjemplo: \"24\"\n"
                 f"Valor actual: {reg_channel.template_time_dif}h", "requested_summary_time",
                 reg_user=reg_user, markup=markup)


def change_summary_time(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    try:
        time = int(update.message.text)
    except ValueError:
        update.message.reply_text("Eso no es un número válido :/")
        return

    if time <= 0:
        update.message.reply_text("Eso no es un número válido :/")
    else:
        reg_channel.template_time_dif = time
        update.message.reply_text(f"Tiempo entre resumenes cambiado a {time}h :3")
        go_to_customization(update, context)


def request_register_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Diga la @ del canal que desea registrar :D", "requested_register")


def register_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    atusername = get_at_username(update.message.text)
    if atusername in registered_channels:
        update.message.reply_text("El canal {} ya se encuentra registrado".format(atusername))
        go_to_base(update, context)
        return
    try:
        logger.info(atusername)
        channel = bot.get_chat(atusername)
    except TelegramError:
        update.message.reply_text(
            "No se encontró el canal :/ Asegúrate de que enviaste el nombre correcto")
        return

    admin, fail_reason = is_admin(channel, update.effective_user.id)
    if admin:
        registered_channels[atusername] = RegisteredChannel(chat_id=channel.id)
        add_to_known_channels(get_reg_user(update.effective_user, update.effective_chat), atusername)
        update.message.reply_text(
            "Canal registrado! :D Ahora en el menú debes configurar la plantilla antes de que pueda ser usada 📄")
        go_to_base(update, context)
    else:
        update.message.reply_text(fail_reason)
        go_to_base(update, context)


def request_unregister_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    send_request(update, "Diga la @ del canal que desea sacar del registro :(", "requested_unregister")


def unregister_channel(update: telegram.Update, context: telegram.ext.CallbackContext):
    channel = get_at_username(update.message.text)
    if channel in registered_channels:
        admin, fail_reason = is_admin(bot.get_chat(channel), update.effective_user.id)
        if admin:
            reg_user = get_reg_user(update.effective_user, update.effective_chat)
            registered_channels.pop(channel)
            if channel in reg_user.known_channels:
                reg_user.known_channels.remove(channel)
            update.message.reply_text(
                "Canal eliminado del registro satisfactoriamente (satisfactorio para ti, pvto) ;-;")
            go_to_base(update, context)
        else:
            update.message.reply_text(fail_reason)
            go_to_base(update, context)
    else:
        update.message.reply_text("Este canal no está registrado")


def send_summary_now(update: telegram.Update, context: telegram.ext.CallbackContext):
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    post_summary(reg_user.context_data['channel'])
    update.message.reply_text("Resumen enviado :D")


def help_handler(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(f"Utiliza los botones de \"{HELP_MARKUP}\" para obtener ayuda sobre el bot")


def backup(update: telegram.Update, context: telegram.ext.CallbackContext):
    if update.effective_chat.id != admin_chat_id:
        return
    auto_backup()
    file = open("bot_data.json", "rb")
    bot.send_document(chat_id=update.effective_chat.id, document=file, filename="bot_data.json")
    file.close()


def restore(update: telegram.Update, context: telegram.ext.CallbackContext):
    original = update.message.reply_to_message
    if update.effective_user.id == admin_chat_id:
        if original is not None and original.document is not None:
            t_file = original.document.get_file()
            deserialize_bot_data(t_file.download())
            update.message.reply_text("Restored previous data!")
            update_checker[0] = datetime.now()
        else:
            update.message.reply_text("El comando /restore debe ser una respuesta a un archivo de respaldo.")


def process_private_message(update: telegram.Update, context: telegram.ext.CallbackContext):
    if update.message is None:
        return
    auto_restore()
    reg_user, reg_channel, _ = get_update_data(update, nomarkup=True)

    status = reg_user.status
    text = update.message.text
    if status == "base":
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
        pin_markup = CAN_PIN_TEMPLATES_ON_MARKUP if \
            reg_channel.pin_summaries else CAN_PIN_TEMPLATES_OFF_MARKUP
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
        elif text == CHANGE_TEMPLATE_FORMAT_MARKUP:
            request_change_template_format(update, context)
        elif text == SEE_TEMPLATE_FORMAT_MARKUP:
            see_template_format(update, context)
        elif text == DELETE_TEMPLATE_FORMAT_MARKUP:
            delete_template_format(update, context)
        elif text == ADD_TEMPLATE_CONTENT_MARKUP:
            request_add_template_content(update, context)
        elif text == SEE_TEMPLATE_CONTENT_MARKUP:
            see_template_content(update, context)
        elif text == REMOVE_TEMPLATE_CONTENT_MARKUP:
            request_remove_template_content(update, context)
        elif text == REORDER_TEMPLATE_CONTENT_MARKUP:
            request_reorder_template_content(update, context)
        elif text == ADD_TEMPLATE_IDENTIFIER_MARKUP:
            request_add_template_identifier(update, context)
        elif text == REMOVE_TEMPLATE_IDENTIFIER_MARKUP:
            request_remove_template_identifier(update, context)
        elif text == SEE_TEMPLATE_IDENTIFIERS_MARKUP:
            see_template_identifiers(update, context)
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
        send_automatically_markup = SEND_AUTOMATICALLY_ON_MARKUP if \
            reg_channel.send_automatically else SEND_AUTOMATICALLY_OFF_MARKUP
        if text == FIND_PROBLEMS_MARKUP:
            find_problems(update, context)
        elif text == CHANGE_SUMMARY_TIME_MARKUP:
            request_change_summary_time(update, context)
        elif text == CATEGORIES_MENU_MARKUP:
            go_to_categories(update, context)
        elif text == send_automatically_markup:
            switch_send_automatically(update, context)
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
        elif text == ADD_CATEGORY_CONTENT_MARKUP:
            request_add_category_content(update, context)
        elif text == SEE_CATEGORY_CONTENTS_MARKUP:
            see_category_contents(update, context)
        elif text == REMOVE_CATEGORY_CONTENT_MARKUP:
            request_remove_category_content(update, context)
        elif text == REORDER_CATEGORY_CONTENTS_MARKUP:
            request_reorder_category_contents(update, context)
        elif text == HELP_MARKUP:
            category_customization_help(update, context)
        elif text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
    elif status == "requested_template":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            change_template(update, context)
    elif status == "requested_template_picture":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
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
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
        else:
            add_category(update, context)
    elif status == "requested_template_identifier":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            add_template_identifier(update, context)
    elif status == "requested_remove_template_identifier":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            remove_template_identifier(update, context)
    elif status == "requested_template_content":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            add_template_content(update, context)
    elif status == "requested_remove_template_content":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            remove_template_content(update, context)
    elif status == "requested_reorder_template_contents":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            reorder_list(update, context, "reordering_template_content", reg_channel.template_contents)
    elif status == "requested_category_name":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            change_category_name(update, context)
    elif status == "requested_category_identifier":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            add_category_identifier(update, context)
    elif status == "requested_remove_category_identifier":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            remove_category_identifier(update, context)
    elif status == "requested_category_format":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            change_category_format(update, context)
    elif status == "requested_category_content":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            add_category_content(update, context)
    elif status == "requested_remove_category_content":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            remove_category_content(update, context)
    elif status == "requested_reorder_category_contents":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_category_customization(update, context)
        else:
            reorder_list(update, context, "reordering_category_contents",
                         reg_channel.categories[reg_user.context_data['category']].category_contents)
    elif status == "requested_remove_category":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
        else:
            remove_category(update, context)
    elif status == "requested_reorder_categories":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
        else:
            reorder_list(update, context, "reordering_categories",
                         [c.name for c in reg_channel.categories])
    elif status == "requested_template_format":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_template(update, context)
        else:
            change_template_format(update, context)
    elif status == "requested_customize_category":
        if text == CANCEL_MARKUP:
            update.message.reply_text("Cancelado")
            go_to_categories(update, context)
        else:
            customize_category(update, context)
    elif status == "":
        go_to_base(update, context)


def process_private_photo(update: telegram.Update, context: telegram.ext.CallbackContext):
    if update.message is None:
        return
    auto_restore()
    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    status = reg_user.status
    if status == "requested_template_picture":
        change_template_picture(update, context)
    else:
        update.message.reply_text("Quejeso? Tus nudes? :0")


def process_channel_update(update: telegram.Update, context: telegram.ext.CallbackContext):
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

    try_post_summary(atusername)


def process_callback_query(update: telegram.Update, context: telegram.ext.CallbackContext):
    """

    Args:
        update (telegram.Update)
        context (telegram.ext.CallbackContext)

    """
    query = update.callback_query
    if isinstance(query, telegram.ext.InvalidCallbackData):
        return

    reg_user = get_reg_user(update.effective_user, update.effective_chat)
    reg_channel = registered_channels[reg_user.context_data['channel']]

    query.answer()

    data = query.data

    names = None
    source = None

    if reg_user.status == "reordering_categories":
        names = [c.name for c in reg_channel.categories]
        source = reg_channel.categories
    elif reg_user.status == "reordering_template_content":
        source = reg_channel.template_contents
    elif reg_user.status == "reordering_category_contents":
        category = reg_channel.categories[reg_user.context_data['category']]
        source = category.category_contents

    if source is not None:
        if data == MOVE_UP_MARKUP:
            reorder_up(update, context, source, names)
        elif data == MOVE_DOWN_MARKUP:
            reorder_down(update, context, source, names)
        elif data == DONE_MARKUP:
            query.answer()
            query.edit_message_text(text=f"{get_list_text(names)}\n\n{DONE_MARKUP}")
            if reg_user.status == "reordering_categories":
                go_to_categories(update, context)
            elif reg_user.status == "reordering_template_content":
                go_to_template(update, context)
            elif reg_user.status == "reordering_category_contents":
                go_to_category_customization(update, context)


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

    dp.add_handler(CallbackQueryHandler(process_callback_query))

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
                          webhook_url=WEBHOOK + TOKEN)

    updater.idle()


update_timer = Timer(BACKUP_TIME_DIF * 60, auto_backup)

if __name__ == '__main__':
    main()
