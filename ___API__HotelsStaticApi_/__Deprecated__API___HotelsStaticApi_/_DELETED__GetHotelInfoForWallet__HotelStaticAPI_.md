# Метод GetHotelInfoForWallet (/internal\_api/v1/hotels/wallet-hotelinfo)

| Назначение | Получение информации о master-отеле по идентифкатору отеля |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/wallet-hotelinfo |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelListApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer\[] | REQUIRED | Массив идентификаторов master-отелей |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура WalletHotelInfoApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | идентификатор master hotel id |
| hotelName | string | REQUIRED | Наименование отеля |
| Location |  | REQUIRED | Объект, описывающий расположение отеля |
| HotelMainPhotoUrl | string | OPTIONAL | URL основной фотографии отеля |

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
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details |  | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки атрибута |
| message | string | OPTIONAL | Текст ошибки атрибута |
| attribute | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Идентификаторы master-отелей не могут быть пустыми. | masterHotelId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Идентификаторы master-отелей не могут быть пустыми.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Идентификатор master-отеля равен нулю. | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | `Хотя бы один идентификатор master-отеля должен быть не нулевым.` | masterHotelId |  | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Хотя бы один идентификатор master-отеля должен быть не нулевым.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Не существует отелея с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetHotelByMasterId

1. Вызывается хранимая процедура \[HotelStaticApi\_GetWalletHotelInfo] в TravelDB. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId (список индентификаторов master-отелей)
2. Выполняется операция объединения таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.PrimaryLocationId;  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.CountryId;
3. Выполняется выборка даннных первой строки из таблицы TravelDB.HotelImage (для каждого отеля) в которой находится информация о фотография отеля, отсортированных по HotelImage.IsDefault по убыванию и HotelImage.Position по возрастанию.
4. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель WalletHotelInfoApiResponseICollectionPayloadApiResponse

# Маппинг данных на модель Hotel Static API

<table><colgroup><col/><col/></colgroup><thead><tr><th><p>Параметр</p></th><th colspan="1"><p>Источник данных</p></th></tr></thead><tbody><tr><td colspan="1">payload</td><td colspan="1"><br/></td></tr><tr><td>-&gt;MasterHotelId</td><td colspan="1">[TravelDB]..[HotelDetails].HotelId</td></tr><tr><td colspan="1">-&gt;hotelName</td><td colspan="1">[TravelDB]..[HotelDetails].HotelName</td></tr><tr><td>-&gt;Location</td><td><br/></td></tr><tr><td colspan="1">-&gt;-&gt;masterLocationId</td><td colspan="1">[TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">-&gt;-&gt;name</td><td colspan="1">[TravelDB]..[HotelDetails].LocationName</td></tr><tr><td colspan="1">-&gt;-&gt;type</td><td colspan="1"><p>Принимает следующие значения в зависимости от [TravelDB]..[Location].LocationType </p><table><tbody><tr><th>LocationType</th><th>Type</th></tr><tr><td>1</td><td><span>Continent</span></td></tr><tr><td>2</td><td><span>Country</span></td></tr><tr><td>3</td><td><span>Province (State)</span></td></tr><tr><td>5</td><td><span>City</span></td></tr><tr><td colspan="1">6</td><td colspan="1"><span>Airport</span></td></tr><tr><td colspan="1">7</td><td colspan="1"><span>Railway Station</span></td></tr><tr><td colspan="1">9</td><td colspan="1"><span>Point of Interest</span></td></tr><tr><td colspan="1">10</td><td colspan="1"><span>Multi-Region (within a country)</span></td></tr><tr><td colspan="1">11</td><td colspan="1"><span>Street</span></td></tr><tr><td colspan="1">12</td><td colspan="1"><span>Subway (Entrance)</span></td></tr><tr><td colspan="1">13</td><td colspan="1"><span>Neighborhood</span></td></tr><tr><td colspan="1">14</td><td colspan="1"><span>Bus Station</span></td></tr><tr><td colspan="1">15</td><td colspan="1"><span>Multi-City (Vicinity)</span></td></tr></tbody></table><p><br/></p></td></tr><tr><td colspan="1">-&gt;-&gt;countryCode</td><td colspan="1">[TravelDB]..[Location].Code для страны, в которой находится локация, в которой находится master-отель с HotelId</td></tr><tr><td colspan="1">-&gt;-&gt;HotelMainPhotoUrl</td><td colspan="1">[TravelDB]..[HotelImage].ImagePath</td></tr></tbody></table>

# Пример использования

## Запрос

```json
{
  "masterHotelId": [
    1426291, 1406924
  ]
}
```

## Ответ

```json
{
  "payload": [
    {
      "masterHotelId": 1406924,
      "hotelName": "Отель Измайлово Бета",
      "location": {
        "masterLocationId": 47307,
        "name": "Москва",
        "type": "City",
        "countryCode": "RU"
      },
      "hotelMainPhotoUrl": "https://cdn.worldota.net/t/{size}/extranet/f7/c2/f7c278015af01bbca4bd4a87bd84020bd90c4b19.jpeg"
    },
    {
      "masterHotelId": 1426291,
      "hotelName": "Отель Измайлово Альфа",
      "location": {
        "masterLocationId": 47307,
        "name": "Москва",
        "type": "City",
        "countryCode": "RU"
      },
      "hotelMainPhotoUrl": "https://cdn.worldota.net/t/{size}/extranet/96/98/96983f21e5e46addb8d699744dd4e270a3ec0911.jpeg"
    }
  ]
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **v. 1** |  |