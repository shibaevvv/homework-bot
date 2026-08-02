# Telegram Homework Status Bot

Telegram-бот для автоматического отслеживания статуса проверки домашних работ в Яндекс Практикуме.

Бот периодически обращается к API Практикума и отправляет сообщение в Telegram, когда статус домашней работы изменяется.

## Возможности

* получение статуса последней отправленной домашней работы;
* отправка уведомлений в Telegram;
* обработка ответов API и HTTP-ошибок;
* проверка обязательных переменных окружения;
* защита от повторной отправки одинаковых сообщений;
* логирование работы приложения;
* автоматические тесты основных функций.

## Как работает бот

Бот выполняет запрос к API Практикума каждые 10 минут.

При изменении статуса домашней работы пользователь получает одно из сообщений:

* работа взята на проверку;
* работа успешно принята;
* работа возвращена с замечаниями.

Если во время работы возникает ошибка, бот отправляет информацию о ней в Telegram. Одинаковые сообщения об ошибках повторно не отправляются.

## Технологии

* Python
* Requests
* pyTelegramBotAPI
* python-dotenv
* Pytest
* Flake8

## Установка

Клонируйте репозиторий:

```bash
git clone https://github.com/shibaevvv/homework-bot.git
cd homework-bot
```

Создайте и активируйте виртуальное окружение:

```bash
python -m venv venv
```

Для Windows:

```bash
venv\Scripts\activate
```

Для Linux и macOS:

```bash
source venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Настройка переменных окружения

Создайте в корне проекта файл `.env`:

```env
PRACTICUM_TOKEN=your_practicum_token
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

Переменные:

| Переменная         | Описание                                             |
| ------------------ | ---------------------------------------------------- |
| `PRACTICUM_TOKEN`  | OAuth-токен API Яндекс Практикума                    |
| `TELEGRAM_TOKEN`   | Токен Telegram-бота, полученный через BotFather      |
| `TELEGRAM_CHAT_ID` | Идентификатор Telegram-чата для отправки уведомлений |

Файл `.env` не должен добавляться в репозиторий.

## Запуск

```bash
python homework.py
```

После запуска бот начинает проверять изменения статуса домашней работы.

## Тестирование

Запуск тестов:

```bash
pytest
```

Проверка стиля кода:

```bash
flake8
```

## Структура проекта

```text
homework-bot/
├── tests/              # Автоматические тесты
├── homework.py         # Основная логика приложения
├── requirements.txt    # Зависимости проекта
├── pytest.ini          # Настройки Pytest
├── setup.cfg           # Настройки Flake8
├── Procfile            # Команда запуска worker-процесса
└── README.md
```

## Автор

**Владимир Шибаев**

- GitHub: https://github.com/shibaevvv
- Telegram: https://t.me/shibaevvv
- Email: shibaev.vladimir@gmail.com
