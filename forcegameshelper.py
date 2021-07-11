from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os

def start(bot, update):
    update.message.reply_text('Ahoy {}! Welcome to JBossStarsBot. \n\nTo get started, use the /stars command to fetch the stars from the GitHub repos of JBoss'.format(update.message.from_user.first_name))


def stars(bot, update):
    api = requests.get('https://api.github.com/orgs/JBossOutreach/repos')
    json = api.json()
    stars = ''
    for i in range(len(json)):
        stars = stars + '\n' + json[i]['name'] + ' : ' + str(json[i]['stargazers_count'])

    update.message.reply_text('Here\'s the list of all the JBoss repositories on GitHub along with their respective star count. \n\n' + stars + '\n\nTo get the stars of a specific repository, enter the name of the repository.')


def repo_stars(bot, update):
    api = requests.get('https://api.github.com/orgs/JBossOutreach/repos')
    json = api.json()
    star = ''
    for i in range(len(json)):
        cur = json[i]['name']
        if cur == update.message.text:
            star += cur + ' : ' + str(json[i]['stargazers_count'])
            break
        elif cur == '':
            star = 'No such repository found.'

    bot.send_message(chat_id=update.message.chat_id, out=star)

TOKEN = ''
PORT = int(os.environ.get('PORT', '8443'))
updater = Updater(TOKEN)                           

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('stars', stars))
updater.dispatcher.add_handler(MessageHandler(Filters.text, repo_stars))

updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
updater.bot.set_webhook("https://gcijbossbot.herokuapp.com/" + TOKEN)
updater.idle()
