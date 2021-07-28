from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os

def start(bot, update):
    update.message.reply_text('Hola {}! Añademe a un canal para utilizarme!'.format(update.message.from_user.first_name))

def receive_message(bot, update):
	bot.send_message(chat_id=update.message.chat_id, out='received')	
	
	

TOKEN = '1609173394:AAH4V-ShZIGXOBE9JPOUg3wVN_Q3BycCZG4'
PORT = int(os.environ.get('PORT', '8443'))
updater = Updater(TOKEN)                           

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(MessageHandler(Filters.chat_type.channel, receive_message))

updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
updater.bot.set_webhook("https://forcegameshelper.herokuapp.com/" + TOKEN)
updater.idle()
