| Назначение | Получение информации о дереве локаций |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/location-tree |
| Метод | POST |

# Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура LocationTreeApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| locationIds | int\[] | OPTIONAL | Идентификаторы локаций, для которых необходимо возвращать родителей (включая их самих) |

# Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура LocationTreeApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| locations | \[] | REQUIRED | Список локаций |

### Структура LocationTreeItem

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| locationId | int | REQUIRED | Идентификатор локации |
| parentLocationId | int | OPTIONAL | Идентификатор родительской локации |

# Ошибки: коды и описания

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| По переданному списку лакаций не найдено ни одно локации | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetLocationTree

1. Выполняется авторизация по предоставленному apiKey.
2. Вызывается хранимая процедура 🗂️ TravelDB.HotelStaticAPI\_GetLocationTree \[HotelsStaticApi] в TravelDB. В качестве аргумента функции @Locations передается параметр из запроса метода locationIds (или NULL, если локации не переданы)
3. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| →locations |  |
| →→locationId | \[TravelDB]..\[Location].LocationID |
| →→parentLocationId | \[TravelDB]..\[Location].ParentID |

# Пример использования

## Запрос

```json
{
  "locationIds": [1150, 1157, 1158, 1161, 1161]
}
```

## Ответ

```json
{
    "payload": {
        "locations": [{
                "locationId": 93,
                "parentLocationId": null
            }, {
                "locationId": 194,
                "parentLocationId": null
            }, {
                "locationId": 209,
                "parentLocationId": null
            }, {
                "locationId": 1150,
                "parentLocationId": 194
            }, {
                "locationId": 1157,
                "parentLocationId": 194
            }, {
                "locationId": 1158,
                "parentLocationId": 93
            }, {
                "locationId": 1161,
                "parentLocationId": 209
            }
        ]
    }
```

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | TTP-15090 |