#!/usr/bin/python3.10
import json
import logging
import os.path
import sys
from email.message import EmailMessage
from logging import handlers
from smtplib import SMTP_SSL, SMTPAuthenticationError

import requests
from bs4 import BeautifulSoup


class TranslationItem:
    def __init__(self, title, volume, status):
        self.title = title
        self.volume = volume
        self.status = status

        self.logger = prepare_logger(f'{self.title.lower()}#{self.volume}')

    def create_message(self, sender_email, receiver_email):
        msg = EmailMessage()
        msg['Subject'] = f"{self.title} status has changed!"
        msg['To'] = receiver_email
        msg['From'] = f"Tymek's automated notification service <{sender_email}>"

        message = f"{self.title} LN vol.{self.volume} translation status on Kotori has changed! \n" \
                  f"Current status is: {self.status} \n\n" \
                  f"If you want to directly access the website, here is link: \n" \
                  f"https://kotori.pl/zapowiedzi/ \n\n" \
                  f"Have a great day!\n" \
                  f"Tymek's automated notification service"

        msg.set_content(message)
        return msg

    def read_file(self):
        path = os.path.join(os.path.dirname(__file__), f"{self.title}_{self.volume}.txt")
        if os.path.exists(path) and os.path.isfile(path):
            file = open(path, 'a+', encoding='cp1250')
            file.seek(0)
        else:
            file = open(path, 'w+', encoding='cp1250')
            file.write("first stage")
            file.seek(0)
        return file

    def check_for_update(self) -> bool:
        file = self.read_file()
        if self.status == file.readlines()[-1].strip():
            self.logger.info('status hasn\'t changed')
            file.close()
            return False
        else:
            self.logger.info('status has been updated')
            file.write('\n' + self.status)
            file.close()
            return True

    def send_notification(self, receiver_email) -> bool:
        self.logger.info(f'sending notification email to {receiver_email}')
        sender_email, app_password, server_address = read_credentials()

        try:
            server = SMTP_SSL(server_address)
            server.login(sender_email, app_password)
            server.send_message(self.create_message(sender_email, receiver_email))
            server.quit()
            self.logger.info(f'email successfully sent to {receiver_email}')
            return True
        except SMTPAuthenticationError:
            self.logger.error('authentication error for sending email')
            return False
        except Exception as e:
            self.logger.error(f'error: {e}')
            return False


def prepare_logger(logger_name: str = None, log_file: str = 'notify.log', log_level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    formatter = logging.Formatter(fmt='%(asctime)s - %(name)s:%(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # FILE handler
    handler = handlers.WatchedFileHandler(os.path.join(os.path.dirname(__file__), log_file))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # STDOUT handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def read_credentials():
    file_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    with open(file_path, 'r') as f:
        credentials = json.load(f)
        return credentials["email"], credentials["app_password"], credentials["server"]


def find_item(title, url, receiver_email):
    header = {"UserAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'}
    page = requests.get(url, headers=header)
    soup = BeautifulSoup(page.content, 'html.parser')

    items = soup.find('div', class_='post-content').findAll('td')
    items = [item.get_text() for item in items if title in item.get_text()]
    for item in items:
        item, status = [elem.strip() for elem in item.split('–')]
        volume = item.split('#')[-1]

        item = TranslationItem(title, volume, status)
        if item.check_for_update():
            item.send_notification(receiver_email)


if __name__ == "__main__":
    prepare_logger()
    if len(sys.argv) == 2:
        find_item('Overlord', 'https://kotori.pl/zapowiedzi/', sys.argv[1])
    else:
        logging.critical('missing necessary argument: [receiver_email]')
