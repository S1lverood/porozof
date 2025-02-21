import logging
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from bot.database.methods.get import (
    get_all_user,
)
from bot.database.migrations import add_date_reg
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(filename)s:%(lineno)d "
           "[%(asctime)s] - %(name)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            filename='logs/all.log',
            maxBytes=1024 * 1024 * 25,
            encoding='UTF-8',
        ),
        RotatingFileHandler(
            filename='logs/errors.log',
            maxBytes=1024 * 1024 * 25,
            encoding='UTF-8',
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.getLogger().handlers[1].setLevel(logging.ERROR)

from bot.main import start_bot
import asyncio




def checkTime():
    while True:
        try:
            time.sleep(15)
            users = asyncio.run(get_all_user())
            for i in users:
                time_now = int(time.time())
                remained_time = int(i.subscription) - time_now
                if remained_time <= 0:
                    check = subprocess.call(f'/root/VPNHubBot/WG/deleteuserfromvpn.sh {str(i[1])}', shell=True)
                # if remained_time <= 86400 and i[4] == False:
                #     db = sqlite3.connect(DBCONNECT)
                #     db.execute(f"UPDATE userss SET notion_oneday=true where tgid=?", (i[1],))
                #     db.commit()
                #     BotChecking = TeleBot(BOTAPIKEY)
                #     BotChecking.send_message(i['tgid'], texts_for_bot["alert_to_renew_sub"], parse_mode="HTML")








        except Exception as err:
            print(err)
            pass



if __name__ == '__main__':
    # subprocess.call(f'/app/bot/WG/addusertovpn.sh docker', shell=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())
    # Run migrations
    loop.run_until_complete(add_date_reg.migrate())
    
    # Start bot
    threading.Thread(target=checkTime).start()
