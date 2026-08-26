# Общая информация

| Назначение | Получение статической информации о типах точках рядом с отелем |
|---|---|
| Бизнес-процессы | TTP-25001 |
| Контракт | QA: |
| URL | /internal\_api/v1/points\_of\_interest/{masterHotelId}/types |
| Метод | GET |

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization | string | REQUIRED | Ключ авторизации |
| Path |  |  |  |
| masterHotelId | int32 | REQUIRED | Идентификатор master-отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload | string:\[] | REQUIRED |  |

### Ошибки: коды и описания

### Структура Error

| code | string | REQUIRED | Код ошибки |
|---|---|---|---|
| message | string | optional | Текст ошибки |
| details | [ErrorDetails](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5402368128#id-%5BHotelStaticApi%5DGetHotelLandmarks%28/internal_api/v1/points_of_interest/landmarks%29-ErrorDetails) | optional | Описание ошибок валидации |

### Структура ErrorDetails

| code | 1 | string | REQUIRED | Код ошибки атрибута |
|---|---|---|---|---|
| message | 2 | string | optional | Текст ошибки атрибута |
| attribute | 3 | string | optional | Код атрибута |

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

# Интеграционная схема

# Алгоритмы работы метода

### MC. Основной сценарий

1. Выполняется авторизация запроса с использованием `apiKey`.
2. Производится разбор и валидация входного запроса.
3. Для указанного отеля выполняется получение связанных точек интереса.
   
   - Полученные точки интереса группируются по типу.
   - Коды типов точек кэшируем в приложении, для быстрого доступа и чтобы не делать лишний join в базе.
4. Если точки для данного отеля отсутствуют, возвращаем пустой ответ со статусом 204. Завершаем основной сценарий.
5. Если точки есть, то на основании полученных данных формируется массив *poiTypes*.
6. Выполняется маппинг данных в модель ответа.
7. Основной сценарий завершается.

## Маппинг данных на модель

| payload |  |
|---|---|
| -&gt; | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_points\_of\_interest\_types].code |

# Пример использования

## Запрос

```json
GET /internal_api/v1/points_of_interest/1426291/types
```

## Ответ

```json
{
  "payload": ["beach", "beach_for_map", "skilift"]
}
```

# Связанные документы

# История изменений

| Исходная версия документа | v1 | TTP-25418 |
|---|---|---|
|  |  |  |