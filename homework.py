from http import HTTPStatus
import logging
import os
import requests
import sys
import time


from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def check_tokens():
    """Функция проверяет наличие необходимых переменных окружения."""
    logger.debug('Проверка переменных окружения')
    for name, token in [('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
                        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
                        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)]:
        if token is None:
            logger.critical('Отсутствует обязательная переменная окружения: '
                            f'{name}. Программа принудительно остановлена.')
            raise SystemExit


def send_message(bot, message):
    """Функция для отправки сообщения в чат Телеграмм."""
    logger.debug('Отправляем сообщение в чат Телеграмма.')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправленно.')
    except Exception as error:
        logger.error(error)


def get_api_answer(timestamp):
    """
    Функция возвращает словарь с данными из ответа API-сервиса.
    Если запрос вернул статус отличный от успешного, то репортим о
    неудаче в лог и пользователю в чат.
    Параметром выступает временная метка с которой происходит проверка
    ответов.
    """
    logger.debug('Отправка запроса к API-сервису')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        raise Exception(f'ошибка при запросе к API {error}')
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError(f'ошибка {response.status_code}'
                                 f' при запросе к API - {response.reason}')
    return response.json()


def check_response(response):
    """Функция проверяет ответ API-сервиса на форматы из документации."""
    logger.debug('Проверка ответа API-сервиса на соотвествие форматов.')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует формату. '
                        'Получен не словарь')
    for key in ['homeworks', 'current_date']:
        if response.get(key) is None:
            raise KeyError(f'В словаре отсутствует ключ "{key}".')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ответ API не соответствует формату. '
                        'Получен не словарь') 


def parse_status(homework):
    """Функция для проверки статуса последней домашней работы."""
    logger.debug('Проверка статуса домашнего задания.')
    for key in ['homework_name', 'status', 'reviewer_comment']:
        if key not in homework:
            raise KeyError(f'В словаре отсутствует ключ "{key}".')
    return (
        f'Изменился статус проверки работы "{homework['homework_name']}".'
        f' {HOMEWORK_VERDICTS[homework['status']]}'
    )


def main():
    """Основная логика работы бота."""
    logger.info('***** Старт бота *****')
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time())
    timestamp = 1753071817
    last_message = None
    new_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response['current_date']
            new_message = parse_status(response['homeworks'][0]) if (
                response['homeworks']) else last_message
            if last_message != new_message:
                send_message(bot, new_message)
                last_message = new_message
            else:
                logger.debug('Новый статус домашки отсутствует.')
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
        logger.debug(f'Пауза {RETRY_PERIOD} секунд.')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
