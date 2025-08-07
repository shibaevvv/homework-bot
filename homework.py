import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKEN_NAMES = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
HOMEWORKS_KEY = 'homeworks'
HOMEWORK_NAME = 'homework_name'
STATUS_KEY = 'status'

CHECK_TOKENS_MESSAGE = 'Проверка переменных окружения'
TOKENS_ERROR_MESSAGE = ('Отсутствует обязательная переменная окружения: {}.')

TELEGRAM_SEND_MESSAGE = 'Отправляем сообщение в чат Телеграмма.'
SUCCESS_SEND_MESSAGE = 'Сообщение ({}) успешно отправленно.'
ERROR_SEND_MESSAGE = 'Ошибка отправки сообщения в Телеграм: {error}'

API_ANSWER_ERROR_MESSAGE = (
    'Ошибка при запросе к API {error}. Параметры запроса: '
    'url = {url}, headers = {headers}, params = {params}'
)
API_HTTP_ERROR_MESSAGE = (
    'Ответ вернул статус - {code}. Параметры запроса: '
    'url = {url}, headers = {headers}, params = {params}'
)
ERROR_IN_RESPONSE_MESSAGE = (
    'Ошибка при запросе к API. Получен ответ: '
    '{response}. Параметры запроса: '
    'url = {url}, headers = {headers}, params = {params}'
)

EXPECTED_DICT = 'словарь'
EXPECTED_LIST = 'список'
WRONG_TYPE_ERROR_MESSAGE = (
    'Ответ API не соответствует формату. '
    'Получен не {expected}, а {type}'
)

MISSING_KEY_MESSAGE = 'В словаре отсутствует ключ {key}.'

WRONG_STATUS_MESSAGE = (
    'API возвращает недокументированный статус '
    'домашней работы либо домашку без статуса'
)
CHANGED_STATUS_MESSAGE = 'Изменился статус проверки работы "{name}". {status}'

NEW_STATUS_MISSING_MESSAGE = 'Новый статус домашки отсутствует.'

ERROR_MESSAGE = 'Сбой в работе программы: {error}'

PAUSE_MESSAGE = 'Пауза {retry_period} секунд.'

EMERGENCY_EXIT_MESSAGE = 'Программа принудительно остановлена.'

logger = logging.getLogger(__name__)


class TelegramSendError(Exception):
    """Исключение для выявления ошибки по отсутствующим токенам."""


class HttpStatusError(Exception):
    """Исключение для выявления ошибки по отсутствующим токенам."""


def check_tokens():
    """Функция проверяет наличие необходимых переменных окружения."""
    logger.debug(CHECK_TOKENS_MESSAGE)
    error_tokens = []
    for name in TOKEN_NAMES:
        if not globals().get(name):
            error_tokens.append(name)
    if error_tokens:
        logger.critical(TOKENS_ERROR_MESSAGE.format(', '.join(error_tokens)))
        raise EnvironmentError


def send_message(bot, message):
    """Функция для отправки сообщения в чат Телеграмм."""
    logger.debug(TELEGRAM_SEND_MESSAGE)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(SUCCESS_SEND_MESSAGE.format(message))
    except Exception as error:
        raise TelegramSendError(ERROR_SEND_MESSAGE.format(error=error))
        # logger.error(error, exc_info=True)


def get_api_answer(timestamp):
    """
    Функция возвращает словарь с данными из ответа API-сервиса.
    Если запрос вернул статус отличный от успешного, то репортим о
    неудаче в лог и пользователю в чат.
    Параметром выступает временная метка с которой происходит проверка
    ответов.
    """
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise ConnectionError(API_ANSWER_ERROR_MESSAGE.format(
            error=error,
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        )
    if response.status_code != HTTPStatus.OK:
        # Подходящее исключение из стандартных не нашел.
        raise HttpStatusError(API_HTTP_ERROR_MESSAGE.format(
            code=response.status_code,
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        )
    response = response.json()
    error_in_response = []
    for key in ['error', 'code']:
        if key in response:
            error_in_response.append(key + ' ' + str(response[key]))
    if error_in_response:
        raise ValueError(ERROR_IN_RESPONSE_MESSAGE.format(
            response=', '.join(error_in_response),
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        )
    return response


def check_response(response):
    """Функция проверяет ответ API-сервиса на форматы из документации."""
    if not isinstance(response, dict):
        raise TypeError(WRONG_TYPE_ERROR_MESSAGE.format(
            expected=EXPECTED_DICT, type=type(response)))
    if response.get(HOMEWORKS_KEY) is None:
        raise KeyError(MISSING_KEY_MESSAGE.format(key=HOMEWORKS_KEY))
    homeworks = response[HOMEWORKS_KEY]
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_TYPE_ERROR_MESSAGE.format(
            expected=EXPECTED_LIST, type=type(homeworks)))


def parse_status(homework):
    """Функция для проверки статуса последней домашней работы."""
    for key in [HOMEWORK_NAME, STATUS_KEY]:
        if key not in homework:
            raise KeyError(MISSING_KEY_MESSAGE.format(key=key))
    if homework[STATUS_KEY] not in HOMEWORK_VERDICTS:
        raise ValueError(WRONG_STATUS_MESSAGE)
    return (CHANGED_STATUS_MESSAGE.format(
        name=homework[HOMEWORK_NAME],
        status=HOMEWORK_VERDICTS[homework[STATUS_KEY]]))


def main():
    """Основная логика работы бота."""
    logger.info('***** Старт бота *****')
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = None
    new_message = None
    old_error_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response[HOMEWORKS_KEY]
            new_message = parse_status(homeworks[0]) if homeworks else (
                last_message)
            if last_message != new_message:
                send_message(bot, new_message)
                last_message = new_message
                timestamp = response.get('current_date', timestamp)
            else:
                logger.debug(NEW_STATUS_MISSING_MESSAGE)
        except EnvironmentError:
            logger.error(EMERGENCY_EXIT_MESSAGE)
            sys.exit
        except TelegramSendError as error:
            logger.error(ERROR_MESSAGE.format(
                error=error), exc_info=True)
        except Exception as error:
            logger.error(ERROR_MESSAGE.format(error=error))
            error_message = str(error)
            if error_message != old_error_message:
                try:
                    send_message(bot, error_message)
                    old_error_message = error_message
                except TelegramSendError as telegram_error:
                    logger.error(ERROR_MESSAGE.format(
                        error=telegram_error), exc_info=True)
        logger.debug(PAUSE_MESSAGE.format(retry_period=RETRY_PERIOD))
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s,'
        ' строка %(lineno)d',
        handlers=[logging.FileHandler(__file__ + '.log'),
                  logging.StreamHandler(sys.stdout)]
    )
    main()
