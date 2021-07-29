import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ExtBot
import os
PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = '1609173394:AAH4V-ShZIGXOBE9JPOUg3wVN_Q3BycCZG4'

admin_chat_id = -1

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')
    if len(context.args) >= 2 and context.args[0] == "admin" and context.args[1] == TOKEN:
        update.message.reply_text("Logged in as Admin!")
        global admin_chat_id
        admin_chat_id = update.message.chat.id


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def process_message(update, context):
    """Send message to admin."""
    if admin_chat_id != -1:
        update.message.reply_text("Enviando a admin")
        context.bot.send_message(chat_id=admin_chat_id, text=update.message.text)
    else:
        update.message.reply_text(update.message.text)

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
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, process_message))

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