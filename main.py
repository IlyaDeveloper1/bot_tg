import logging, aiohttp, sqlite3
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

BOT_TOKEN = '7992901322:AAFWhXx8WQnKN3NcsDKBRMIDVTyvFPH0gPg'

# Запускаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)

reply_keyboard = [['Найти', 'Статистика'],
                  ['Помощь', 'Выход']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

# подключение базы данных
con = sqlite3.connect("userdb.db")

async def start(update, context):
    user = update.effective_user
    userid = user.id
    print(userid)

    # Подключение к БД
    cur = con.cursor()
    cur.execute(f'SELECT * FROM main WHERE userid = {userid}')
    result = cur.fetchall()
    print(result)
    if not result:
        cur.execute(f'INSERT INTO main(userid, totalqueries) VALUES({userid}, 0)')
        con.commit()

    await update.message.reply_html(
        rf"Привет {user.mention_html()}! Я бот по поиску картинок. Для поиска нажми кнопку 'Найти'.",
        reply_markup=markup
    )

async def help(update, context):
    await update.message.reply_text(
        "Этот бот по поиску картинок использует API сайта https://www.pexels.com",
        reply_markup=markup
    )

async def close(update, context):
    await update.message.reply_text(
        "До встречи!",
        reply_markup=ReplyKeyboardRemove()
    )

async def query(update, context):
    await update.message.reply_text(
        'Напишите ключевое слово для поиска картинки.')
    return 1

async def stop(update, context):
    await update.message.reply_text("Операция была прервана!")
    return ConversationHandler.END

async def find_pic(update, context):
    url = "https://api.pexels.com/v1/search"
    response = await get_response(url,
        params={
        "query": update.message.text,
        "per_page": 1},
        headers={
        "Authorization": "MFqOtIr0GjvcI28ROuepepE7eb0BEtX8VOpeSKsFd7QqpcbkRhFItoOJ"}
    )
    # print(response)

    # запись статистики в базу данных
    cur = con.cursor()
    cur.execute(f'UPDATE main SET totalqueries = totalqueries + 1 WHERE userid = {update.effective_user.id}')
    con.commit()

    if response['total_results'] == 0:
        await update.message.reply_text("По вашему запросу ничего не найдено.\n"
                                        "Попробуйте поискать что-то ещё.\n"
                                        "Для этого нажмите кнопку 'Найти'.")
    else:
        # Разбираем json
        pic = response['photos'][0]
        # "id": 00001,
        # "width": 3066,
        # "height": 3968,
        # "url": "https://www.pexels.com/photo/trees-during-day-3573351/",
        # "photographer": "Lukas Rodriguez",
        # "photographer_url": "https://www.pexels.com/@lukas-rodriguez-1845331",
        # "photographer_id": 1845331,
        # "avg_color": "#374824",
        # "src": {
        #     "original": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png",
        #     "large2x": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        #     "large": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&h=650&w=940",
        #     "medium": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&h=350",
        #     "small": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&h=130",
        #     "portrait": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&fit=crop&h=1200&w=800",
        #     "landscape": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&fit=crop&h=627&w=1200",
        #     "tiny": "https://images.pexels.com/photos/3573351/pexels-photo-3573351.png?auto=compress&cs=tinysrgb&dpr=1&fit=crop&h=200&w=280"
        # },
        # "liked": false,
        # "alt": "Brown Rocks During Golden Hour"

        tiny_pic_request = f"{pic['src']['tiny']}"
        await context.bot.send_photo(
            update.message.chat_id,
            tiny_pic_request,
            caption = f"Описание: {pic['alt']}\n"
                      f"Фотограф: {pic['photographer']}\n"
                      f"Ссылка на оригинал: {pic['src']['original']}"
        )
    return ConversationHandler.END

async def get_response(url, params, headers):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            return await resp.json()

async def stat(update, context):
    cur = con.cursor()
    cur.execute(f'SELECT totalqueries FROM main WHERE userid = {update.effective_user.id}')
    result = cur.fetchone()

    await update.message.reply_text(
        f"Ваше количество запросов: {result[0]}.",
        reply_markup=markup
    )


def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Диалог
    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        entry_points=[CommandHandler('query', query),
                      MessageHandler(filters.Regex(r'Найти'), query)],

        # Состояние внутри диалога.
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_pic)]
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    # Регистрация обработчиков
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.Regex(r'Найти'), query))
    application.add_handler(MessageHandler(filters.Regex(r'Помощь'), help))
    application.add_handler(MessageHandler(filters.Regex(r'Выход'), close))
    application.add_handler(MessageHandler(filters.Regex(r'Статистика'), stat))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("close", close))
    application.add_handler(CommandHandler("query", query))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("stat", stat))

    # Запускаем приложение
    application.run_polling()

# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()