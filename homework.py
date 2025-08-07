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

CHECK_TOKENS = 'Проверка переменных окружения'
TOKENS_ERROR = (
    'Отсутствует обязательная переменная окружения: {}.'
    'Программа принудительно остановлена.'
)

TELEGRAM_SEND_SUCCESS = (
    'Сообщение успешно отправленно в Телеграм. Текст сообщения: {}'
)
TELEGRAM_SEND_ERROR = (
    'Ошибка отправки сообщения в Телеграм: {error}. Текст сообщения: {message}'
)

PARAMS = 'url = {url}, headers = {headers}, params = {params}'
API_ANSWER_ERROR = (
    f'Ошибка при запросе к API: {{error}}. Параметры запроса: {PARAMS}'
)
API_HTTP_ERROR = (
    'Ошибка при запросе к API, ответ вернул статус - {code}. '
    f'Параметры запроса: {PARAMS}'
)
ERROR_IN_RESPONSE = (
    'Ошибка при запросе к API, получен ответ: {response}. '
    f'Параметры запроса: {PARAMS}'
)

WRONG_TYPE_ERROR = (
    'Ответ API не соответствует формату. '
    'Получен не {expected}, а {type}'
)

MISSING_KEY = 'В словаре отсутствует ключ {key}.'

WRONG_STATUS = (
    'API возвращает недокументированный статус домашней работы: {status}'
)
CHANGED_STATUS = 'Изменился статус проверки работы "{name}". {status}'

NEW_STATUS_MISSING = 'Новый статус домашки отсутствует.'

ERROR = 'Сбой в работе программы: {error}'

PAUSE = f'Пауза {RETRY_PERIOD} секунд.'

logger = logging.getLogger(__name__)


class HttpStatusError(Exception):
    """Исключение для статусов ответов API отличных от 200."""


class APIResponseError(Exception):
    """Исключение для выявления ошибочных ключей в ответе API."""


def check_tokens():
    """Функция проверяет наличие необходимых переменных окружения."""
    logger.debug(CHECK_TOKENS)
    error_tokens = [name for name in TOKEN_NAMES if not globals().get(name)]
    if error_tokens:
        message = TOKENS_ERROR.format(error_tokens)
        logger.critical(message)
        raise EnvironmentError(message)


def send_message(bot, message):
    """Функция для отправки сообщения в чат Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(TELEGRAM_SEND_SUCCESS.format(message))
        return True
    except Exception as error:
        logger.exception(TELEGRAM_SEND_ERROR.format(error=error,
                                                    message=message))
        return False


def get_api_answer(timestamp):
    """
    Функция возвращает словарь с данными из ответа API-сервиса.
    Если запрос вернул статус отличный от успешного, то репортим о
    неудаче в лог и пользователю в чат.
    Параметром выступает временная метка с которой происходит проверка
    ответов.
    """
    request_params = dict(
        url=ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
    )
    try:
        response = requests.get(**request_params)
    except requests.RequestException as error:
        raise ConnectionError(API_ANSWER_ERROR.format(
            error=error, **request_params))
    if response.status_code != HTTPStatus.OK:
        raise HttpStatusError(API_HTTP_ERROR.format(
            code=response.status_code, **request_params))
    response = response.json()
    for key in ['error', 'code']:
        if key in response:
            raise APIResponseError(ERROR_IN_RESPONSE.format(
                response=f'{key}: {str(response[key])}', **request_params))
    return response


def check_response(response):
    """Функция проверяет ответ API-сервиса на форматы из документации."""
    if not isinstance(response, dict):
        raise TypeError(WRONG_TYPE_ERROR.format(
            expected='словарь', type=type(response)))
    if 'homeworks' not in response:
        raise KeyError(MISSING_KEY.format(key='homeworks'))
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_TYPE_ERROR.format(
            expected='список', type=type(homeworks)))


def parse_status(homework):
    """Функция для проверки статуса последней домашней работы."""
    for key in ['homework_name', 'status']:
        if key not in homework:
            raise KeyError(MISSING_KEY.format(key=key))
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(WRONG_STATUS.format(status=status))
    return CHANGED_STATUS.format(
        name=homework['homework_name'],
        status=HOMEWORK_VERDICTS[status])


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = None
    error_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
                if last_message != message and send_message(bot, message):
                    last_message = message
                    timestamp = response.get('current_date', timestamp)
            else:
                logger.debug(NEW_STATUS_MISSING)
        except Exception as error:
            message = ERROR.format(error=error)
            logger.error(message)
            if message != error_message and send_message(bot, message):
                error_message = message
        finally:
            logger.debug(PAUSE)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(funcName)s:%(lineno)d, '
               '%(message)s',
        handlers=[logging.FileHandler(f'{__file__}.log'),
                  logging.StreamHandler(sys.stdout)]
    )
    logger.info('***** Старт бота *****')
    main()
