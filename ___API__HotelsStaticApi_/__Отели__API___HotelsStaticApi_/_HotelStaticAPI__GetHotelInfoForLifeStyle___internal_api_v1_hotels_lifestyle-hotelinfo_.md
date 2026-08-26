# Метод GetHotelInfoForLifeStyle (/internal\_api/v1/hotels/lifestyle-hotelinfo)

| Назначение | Получение информации о master-отеле по идентифкатору отеля для платформы LifeStyle |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/lifestyle-hotelinfo |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | Идентификатор master-отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура LifeStyleHotelInfoApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | Идентификатор master hotel id |
| name | string | REQUIRED | Наименование отеля |
| location |  | REQUIRED | Объект, описывающий расположение отеля |
| ianaTimeZone | string | REQUIRED | Часовой пояс отеля |
| image | string | OPTIONAL | URL основной фотографии отеля |
| checkInTime | string | OPTIONAL | Стандартное время заезда в отель |
| checkOutTime | string | OPTIONAL | Стандартное время выезда из отеля |

### Структура Location

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | string | REQUIRED | Идентификатор master-локации |
| name | string | REQUIRED | Имя региона\\локации |
| type | string | REQUIRED | Тип региона\\локации |
| countryCode | string | REQUIRED | Код страны |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | MANDATORY | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details |  | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | MANDATORY | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | MANDATORY | Код атрибута |

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

# Алгоритм работы метода GetHotelInfoForLifeStyle

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[HotelStaticApi\_GetLifeStyleHotelInfo] в TravelDB. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId
4. Выполняется операция объединения таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.PrimaryLocationId;  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.CountryId;
5. Выполняется выборка даннных первой строки из таблицы TravelDB.HotelImage (для каждого отеля) в которой находится информация о фотография отеля, отсортированных по HotelImage.IsDefault по убыванию и HotelImage.Position по возрастанию.
6. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель LifeStyleHotelInfoApiResponsePayloadApiResponse

# Маппинг данных на модель Hotel Static API

<table><colgroup><col/><col/></colgroup><thead><tr><th><p>Параметр</p></th><th colspan="1"><p>Источник данных</p></th></tr></thead><tbody><tr><td colspan="1">payload</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;masterHotelId</td><td colspan="1"><span>[TravelDB]..[HotelDetails].HotelId</span></td></tr><tr><td colspan="1">-&gt;name</td><td colspan="1"><span>[TravelDB]..[HotelDetails].HotelName</span></td></tr><tr><td colspan="1">-&gt;location</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;masterLocationId</td><td colspan="1"><span>[TravelDB]..[HotelDetails].PrimaryLocationID</span></td></tr><tr><td colspan="1">-&gt;-&gt;name</td><td colspan="1"><span>[TravelDB]..[HotelDetails].LocationName</span></td></tr><tr><td colspan="1">-&gt;-&gt;type</td><td colspan="1"><p>Принимает следующие значения в зависимости от [TravelDB]..[Location].LocationType </p><table><tbody><tr><th>LocationType</th><th>Type</th></tr><tr><td>1</td><td>Continent</td></tr><tr><td>2</td><td>Country</td></tr><tr><td>3</td><td>Province (State)</td></tr><tr><td>5</td><td>City</td></tr><tr><td>6</td><td>Airport</td></tr><tr><td>7</td><td>Railway Station</td></tr><tr><td>9</td><td>Point of Interest</td></tr><tr><td>10</td><td>Multi-Region (within a country)</td></tr><tr><td>11</td><td>Street</td></tr><tr><td colspan="1">12</td><td colspan="1">Subway (Entrance)</td></tr><tr><td colspan="1">13</td><td colspan="1">Neighborhood</td></tr><tr><td>14</td><td>Bus Station</td></tr><tr><td colspan="1">15</td><td colspan="1">Multi-City (Vicinity)</td></tr></tbody></table><p><br/></p></td></tr><tr><td colspan="1">-&gt;-&gt;countryCode</td><td colspan="1">[TravelDB]..[Location].Code для страны, в которой находится локация, в которой находится master-отель с HotelId</td></tr><tr><td colspan="1">-&gt;ianaTimeZone</td><td colspan="1">[TravelDB]..[Location].TimeZoneName</td></tr><tr><td colspan="1">-&gt;image</td><td colspan="1">[TravelDB]..[HotelImage].ImagePath</td></tr><tr><td colspan="1">-&gt;checkInTime</td><td colspan="1"><span>[TravelDB]..[HotelDetails].CheckInTime</span></td></tr><tr><td colspan="1">-&gt;checkOutTime</td><td colspan="1"><span>[TravelDB]..[HotelDetails].CheckOutTime</span></td></tr></tbody></table>

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
    "masterHotelId": 1426291,
    "name": "Отель Измайлово Альфа",
    "location": {
      "masterLocationId": 47307,
      "name": "Москва",
      "type": "City",
      "countryCode": "RU"
    },
    "ianaTimeZone": "Europe/Moscow",
    "image": "https://cdn.worldota.net/t/{size}/extranet/96/98/96983f21e5e46addb8d699744dd4e270a3ec0911.jpeg",
    "checkInTime": "14:00",
    "checkOutTime": "12:00"
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **v. 1** |  |