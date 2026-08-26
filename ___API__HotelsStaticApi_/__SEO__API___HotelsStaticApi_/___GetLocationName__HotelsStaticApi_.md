# Общая информация по методу

| Назначение | Получение названия локации по идентификатору master-локации |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| URL | /internal\_api/v1/seo/location-name |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура GetByLocationIdApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | integer | REQUIRED | Идентификатор master-локации |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура LocationNameApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| locationName | string | REQUIRED | Наименование master-локации |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | {} | OPTIONAL | Описание ошибок валидации |

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
| Не передан обязательный параметр masterLocationId | incorrectValue | Ошибка при валидации запроса. | noMasterLocationId | Идентификатор master-локации обязателен. | masterLocationId | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "noMasterLocationId",
            "message": "Идентификатор master-локации обязателен.",
            "attribute": "masterLocationId"
        }
    }
}<br />``` |
| Не существует локации с указанным masterLocationId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetLocationName

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[HotelStaticApi\_GetLocationName] в TravelDB с параметром @LocationID = masterLocationId
4. Выполняется выборка из таблицы TravelDB.Location значения Location.Name, для которых Location.LocationId = @LocationId
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель ответа

# Маппинг данных на модель Hotels Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt;locationName | TravelDB.Location.Name |

# Пример использования

## Запрос

```json
/internal_api/v1/seo/hotel-ids?offset=100&limit=10
```

## Ответ

```json
{
  "payload": {
    "offset": 100,
    "limit": 10,
    "hasMore": true,
    "hotelIds": [
      101,
      103,
      104,
      105,
      106,
      107,
      108,
      109,
      111,
      112
    ]
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создание нового метода | **v. 1** | THB-8088 |