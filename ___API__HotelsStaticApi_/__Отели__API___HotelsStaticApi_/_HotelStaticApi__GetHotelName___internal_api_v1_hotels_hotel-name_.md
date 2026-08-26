# Метод GetHotelName (/internal\_api/v1/hotels/hotel-name)

| Назначение | Получение названия отеля по идентификатору master-отеля |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/hotel-name |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer | REQUIRED | Идентификатор master-отеля |

## Структура ответа

### Структура HotelNameApiResponsePayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура HotelNameApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| hotelName | string | OPTIONAL | имя отеля |

# Ошибки: коды и описания

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
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Идентификатор master-отеля обязателен. | masterHotelId | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "noMasterHotelId",
            "message": "Идентификатор master-отеля обязателен.",
            "attribute": "masterHotelId"
        }
    }
}<br />``` |
| Не существует отелея с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetHotelName

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[HotelStaticApi\_GetHotelName] в TravelDB с параметром @HotelID = masterHotelId
4. Выполняется выборка из таблицы TravelDB.HotelDetails значения HotelDetails.HotelName, для которых HotelDetails.HotelId = @HotelID
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель HotelNameApiResponsePayloadApiResponse

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt;hotelName | TravelDB.HotelDetails.HotelName |

# Пример использования

## Запрос

```json
{
  "masterHotelId": 1426291
}
```

## Ответ

```json
{
  "payload": {
    "hotelName": "Отель Измайлово Альфа"
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **v. 1** |  |