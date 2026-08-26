# Общая информация

| Назначение | Получение summary отзывов отеля |
|---|---|
| Бизнес-процессы | Отзывы и рейтинг объекта размещения |
| Контракт |  |
| URL | /internal\_api/v1/review/{masterHotelId}/summary |
| Метод | GET |

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization |  |  | Ключ авторизации |
| Route |  |  |  |
| masterHotelId | int32 | REQUIRED | Идентификатор master-отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload |  | optional |  |

### Структура Payload

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| summary | string | REQUIRED | Саммари отзывов отеля |

## Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details |  | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | REQUIRED | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| Не передан обязательный параметр masterHotelId | incorrectValue | One or more validation errors occurred. | masterHotelId | The value '&lt;value&gt;' is not valid. | masterHotelId | 400 | ```json<br />[CDATA[{
	"errors": {
		"masterHotelId": [
			"The value '<value' is not valid."
		]
	},
	"type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
	"title": "One or more validation errors occurred.",
	"status": 400,
	"traceId": "00-8b6ed66c104b5a1e638ff3a3150af222-afdb3b07159d0671-01"
}]]><br />``` |
| Не существует саммари с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритмы работы метода

### Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Получаем данные из таблицы [hotel\_reviews\_summary](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6511437261) (БД: **hotels\_static** схема**: travel\_hotels\_static**), в которой хранится саммари отзывов, по hotel\_reviews\_summary.hotel\_id **= masterHotelId**
4. Если данные в таблице нашлись, то возвращаем в ответе данные согласно маппингу
   
   | payload |  |
   |---|---|
   | -&gt; summary | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_reviews\_summary].summary |
5. Иначе возвращаем пустой ответ со статус кодом 204.
6. Основной сценарий завершается.

# Метрики и алерты

Зайди в БТ, посмотри, какие бизнес метрики нужны, напиши как их можно вычислить, если это возможно.

Напиши, какие ошибки нужно залогировать, какие могут быть аллерты.

# Связанные документы

# История изменений

|  | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создана страница | v1 | HTLS-4930 |
| 2 |  |  |  |