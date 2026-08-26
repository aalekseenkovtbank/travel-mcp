# Метод GetByMasterHotelIdsOrdered (/internal\_api/v1/search/hotels)

| Назначение | Получение информации о master-отелях<br />Используется для получения статики в запросе Избранного, потребитель: SearchAPI |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/hotels |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура SearchByHotelsIdApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelIds | integer:\[] | REQUIRED | Массив идентификаторов master-отелей |

## Структура ответа SearchHotelInfoApiResponseICollectionPayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | :\[] | REQUIRED | Содержимое ответа |

### **Структура SearchHotelInfoApiResponse**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer | REQUIRED | Идентификатор master-отеля |
| name | string | REQUIRED | Наименование master-отеля |
| nameEn | string | REQUIRED | Английское наименование master-отеля |
| hotelChain | string | OPTIONAL | Наименование сети, которой принадлежит отель |
| hasImage | bool | REQUIRED | Есть ли у master-отеля фотографии |
| starRating | integer | REQUIRED | Звездность master-отеля (в базе может быть null, мы конвертируем автоматом в 0) |
| address | string | REQUIRED | Адрес master-отеля |
| masterLocationId | integer | REQUIRED | Идентификатор master-локации отеля |
| ianaTimeZone | string | REQUIRED | Часовой пояс отеля |
| location |  | REQUIRED | Объект, описывающий расположение отеля |
| review |  | REQUIRED | Объект, описывающий отзывы об отеле |
| coordinates |  | REQUIRED | Объект, описывающий местоположение отеля (широта, долгота) |
| kind | string | REQUIRED | Категория master-отеля<br />Например: Resort |
| apartmentFacts |  | OPTIONAL | Объект с атрибутами, характерными для квартиры<br />Обязателен, если в БД для данного объекта размещения параметр isFlat=true |

### Структура LocationApi

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | integer | REQUIRED | Идентификатор master-локации |
| name | string | REQUIRED | Имя региона\\локации |
| type | string | REQUIRED | тип региона\\локации |
| countryCode | string | REQUIRED | Код страны |
| countryName | string | REQUIRED | Наименование страны |

### Структура ReviewApi

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| rating | float | REQUIRED | Рейтинг отеля |
| count | integer | REQUIRED | Количество отзывов |

### Структура GeoPoint

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| latitude | double | REQUIRED | Географическая широта |
| longitude | double | REQUIRED | Географическая долгота |

### Структура ApartmentFact

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| isFlat | bool | REQUIRED | Признак, что объект является квартирой |
| bedroomCount | int | optional | Количество комнат в квартире |
| size | decimal | optional | Площадь квартиры |
| isContactlessCheckin | bool | optional | Бесконтактное заселение |
| bedConfigurations |  | optional | Массив конфигураций кроватей |

### Структура BedConfiguration

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypes | object\[]: | REQUIRED | Описание спальных мест |

### Структура BedTypes

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypeId | int | REQUIRED | Идентификатор типа спального места |
| isExtraBed | bool | REQUIRED | Признак "Дополнительное спальное место" |

Словарь HotelCategory

| HotelCategoryId | HotelCategoryName |
|---|---|
| 0 | Resort |
| 1 | Sanatorium |
| 2 | Guesthouse |
| 3 | MiniHotel |
| 4 | Castle |
| 5 | Hotel |
| 6 | BoutiqueAndDesign |
| 7 | Apartment |
| 8 | CottagesAndHouses |
| 9 | Farm |
| 10 | VillasAndBungalows |
| 11 | Camping |
| 12 | Hostel |
| 13 | Bnb |
| 14 | ApartHotel |
| 15 | Glamping |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

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
| Идентификатор master-отеля равен нулю. | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Хотя бы один идентификатор master-отеля должен быть не нулевым. | masterHotelId |  | ```json<br />{
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
| Не существует отеля с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetByMasterHotelIdsOrdered

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура TravelDB..\[HotelStaticApi\_GetHotelsInfo] с параметром @hotels = masterHotelIds
4. Выполняется выборка из таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
   и выполняется операция объединения данных с таблицей TravelDB.Hotel по HotelDetails.HotelId = Hotel.HotelId;  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.PrimaryLocationId;  
   и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.CountryId;  
   и выполняется операция объединения данных с таблицей TravelDB.HotelChain по HotelChain.HotelChainId = HotelDetails.HotelChainId;  
   и выполняется операция объединения данных с таблицей TravelDB.HotelPhone по HotelPhone.HotelId = HotelDetails.HotelId и фильтруется по HotelPhone.PhoneTypeID = 1 и HotelPhone.IsDefault=1;  
   Данные выбираются только для HotelDetails.BrandId = 0.
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель SearchHotelInfoApiResponseICollectionPayloadApiResponse

# Маппинг данных на модель Hotel Static API

<table><thead><tr><th><p>Параметр</p></th><th><p>Источник данных</p></th></tr></thead><colgroup><col/><col/></colgroup><tbody><tr><td colspan="1"><span>payload</span></td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;masterHotelId</td><td colspan="1">[TravelDB]..[HotelDetails].HotelID</td></tr><tr><td colspan="1">-&gt;name</td><td colspan="1">[TravelDB]..[HotelDetails].HotelName</td></tr><tr><td colspan="1">-&gt;nameEn</td><td colspan="1">[TravelDB]..[HotelDetails].HotelNameOriginal</td></tr><tr><td>-&gt;hotelChain</td><td>[TravelDB]..[HotelChain].NameRu</td></tr><tr><td><p>-&gt;hasImage</p></td><td><ul><li>true, если существует хотя бы 1 запись в таблице [TravelDB]..[HotelImage] для отеля с искомым hotelId</li><li>false, если не существуют ни одной записи в таблице [TravelDB]..[HotelImage] для отеля с искомым hotelId</li></ul></td></tr><tr><td>-&gt;starRating</td><td>[TravelDB].[HotelDetails].StarRating</td></tr><tr><td>-&gt;address</td><td><div><p><span>[TravelDB]..[HotelDetails].HotelAddress </span></p></div></td></tr><tr><td>-&gt;masterLocationId</td><td><span>[TravelDB]..[HotelDetails].PrimaryLocationID</span></td></tr><tr><td>-&gt;ianaTimeZone</td><td>[TravelDB]..[Location].TimeZoneName для [TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">-&gt;location</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;masterLocationId</td><td colspan="1"><span>[TravelDB]..[HotelDetails].PrimaryLocationID</span></td></tr><tr><td colspan="1">-&gt;-&gt;name</td><td colspan="1">[TravelDB]..[HotelDetails].LocationName</td></tr><tr><td>-&gt;-&gt;type</td><td><p>Принимает следующие значения в зависимости от [TravelDB]..[Location].LocationType </p><table><tbody><tr><th>LocationType</th><th>type</th></tr><tr><td>1</td><td><span>Continent</span></td></tr><tr><td>2</td><td><span>Country</span></td></tr><tr><td>3</td><td><span>Province (State)</span></td></tr><tr><td>5</td><td><span>City</span></td></tr><tr><td>6</td><td><span>Airport</span></td></tr><tr><td>7</td><td><span>Railway Station</span></td></tr><tr><td>9</td><td><span>Point of Interest</span></td></tr><tr><td>10</td><td><span>Multi-Region (within a country)</span></td></tr><tr><td>11</td><td><span>Street</span></td></tr><tr><td>12</td><td><span>Subway (Entrance)</span></td></tr><tr><td>13</td><td><span>Neighborhood</span></td></tr><tr><td>14</td><td><span>Bus Station</span></td></tr><tr><td>15</td><td><span>Multi-City (Vicinity)</span></td></tr></tbody></table><p><br/></p></td></tr><tr><td>-&gt;-&gt;countryCode</td><td><span>[TravelDB]..[Location].Code для страны, в которой находится локация, в которой находится master-отель с HotelId</span></td></tr><tr><td colspan="1">-&gt;-&gt;countryName</td><td colspan="1"><span>[TravelDB]..[Location].Name для страны, в которой находится локация, в которой находится master-отель с HotelId</span></td></tr><tr><td colspan="1">-&gt;review</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;rating</td><td colspan="1">[TravelDB]..[HotelDetails].ReviewRating</td></tr><tr><td>-&gt;-&gt;count</td><td>[TravelDB]..[HotelDetails].ReviewCount</td></tr><tr><td colspan="1">-&gt;coordinates</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;latitude</td><td colspan="1"><span>[TravelDB]..[HotelDetails].latitude</span></td></tr><tr><td colspan="1">-&gt;-&gt;longitude</td><td colspan="1"><span>[TravelDB]..[HotelDetails].longitude</span></td></tr><tr><td colspan="1">-&gt;kind</td><td colspan="1"><p>В зависимости от [TravelDB]..[HotelDetails].HotelCategory (мапится по таблице )</p><ul><li><span>Если HotelCategory = 20, то мапится на HotelCategoryId  = 0, Kind = HotelCategoryName = Resort</span></li><li><span>Если HotelCategory = 40, то мапится на HotelCategoryId  = 1, Kind = HotelCategoryName = Sanatorium</span></li><li><span>Если HotelCategory = 13, то мапится на HotelCategoryId  = 2, Kind = HotelCategoryName = Guesthouse</span></li><li><span>Если HotelCategory = 26, то мапится на HotelCategoryId  = 3, Kind = HotelCategoryName = MiniHotel</span></li><li><span>Если HotelCategory = 10, то мапится на HotelCategoryId  = 4, Kind = HotelCategoryName = Castle</span></li><li><span>Если HotelCategory = 1, то мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li><li><span>Если HotelCategory = 3, то мапится на HotelCategoryId  = 7, Kind = HotelCategoryName = Apartment</span></li><li><span>Если HotelCategory = 11, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 14, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 12, то мапится на HotelCategoryId  = 9, Kind = HotelCategoryName = Farm</span></li><li><span>Если HotelCategory = 8, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 25, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 9, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 22, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 4, то мапится на HotelCategoryId  = 12, Kind = HotelCategoryName = Hostel</span></li><li><span>Если HotelCategory = 6, то мапится на HotelCategoryId  = 13, Kind = HotelCategoryName = Bnb</span></li><li><span>Если HotelCategory = 2, то мапится на HotelCategoryId  = 14, Kind = HotelCategoryName = ApartHotel</span></li><li><span>Если HotelCategory = 42, то мапится на HotelCategoryId  = 6, Kind = HotelCategoryName = BoutiqueAndDesign</span></li><li><span>Если HotelCategory = 43, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping<br/></span></li><li><span>Если HotelCategory = 44, то мапится на HotelCategoryId  = 15, Kind = HotelCategoryName = Glamping<br/></span></li><li><span>В противном случае мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li></ul></td></tr><tr><td colspan="1">apartmentFacts</td><td colspan="1"><div><p>Объект с атрибутами, характерными для квартиры (Апартамент с признаком IsFlat: true. Логика расчета признака описана <a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8345571527">здесь</a>)</p><p>Заполняется только если Hotel.IsFlat == true.</p><p>Некоторые атрибуты сохраняются из таблицы Room.</p><p><s>В случае, если в результате получения данных о комнатах объекта размещения было найдено несколько комнат, объект apartmentFacts не формируется вообще</s></p><p><span>Если у объекта несколько комнат, значения полей берется из данных комнаты поставщика, согласно приоритету: Экстранет → Островок → Броневик</span></p></div></td></tr><tr><td colspan="1">→ isFlat</td><td colspan="1">[TravelDB]..[Hotel].IsFlat</td></tr><tr><td colspan="1"><p>→ bedroomCount</p></td><td colspan="1">[TravelDB]..[Room].BedroomCount</td></tr><tr><td><p>→ size</p></td><td>[TravelDB]..[Room].Size</td></tr><tr><td>→ isContactlessCheckin</td><td>[TravelDB]..[HotelContactlessCheckin].IsContactless</td></tr><tr><td>→ bedConfigurations</td><td>Описание экземпляров RoomBedConfiguration, для которых RoomBedConfiguration.RoomId == Room.RoomId, отсортированные по RoomBedConfiguration.ConfigurationNumber по возрастанию</td></tr><tr><td>→ → bedTypeId</td><td><p>Описание экземпляров RoomBed.BedTypeId, входящих в RoomBedConfiguration, отсортированные по RoomBed.BedNumber по возрастанию</p></td></tr><tr><td>→ → isExtraBed</td><td>RoomBed.IsExtraBed</td></tr></tbody></table>

# Пример использования

## Запрос

```json
{
  "masterHotelIds": [
    1426291,
     1406924
  ]
}
```

## Ответ

```json
{
  "payload": [
    {
      "masterHotelId": 1406924,
      "name": "Отель Измайлово Бета",
      "nameEn": "Отель Измайлово Бета",
      "hotelChain": "",
      "hasImage": true,
      "starRating": 3,
      "address": "Измайловское шоссе, д.71, стр. 2Б, Москва",
      "masterLocationId": 47307,
      "ianaTimeZone": "Europe/Moscow",
      "location": {
        "masterLocationId": 47307,
        "name": "Москва",
        "type": "City",
        "countryCode": "RU"
      },
      "review": {
        "rating": 8.4,
        "count": 1395
      },
      "coordinates": {
        "latitude": 55.7895278931,
        "longitude": 37.7474975586
      },
      "kind": "Hotel"
    },
    {
      "masterHotelId": 1426291,
      "name": "Отель Измайлово Альфа",
      "nameEn": "Отель Измайлово Альфа",
      "hotelChain": "",
      "hasImage": true,
      "starRating": 4,
      "address": "Измайловское шоссе, д.71 А, Москва",
      "masterLocationId": 47307,
      "ianaTimeZone": "Europe/Moscow",
      "location": {
        "masterLocationId": 47307,
        "name": "Москва",
        "type": "City",
        "countryCode": "RU"
      },
      "review": {
        "rating": 8.9,
        "count": 858
      },
      "coordinates": {
        "latitude": 55.7898292542,
        "longitude": 37.7495040894
      },
      "kind": "Hotel"
    }
  ]
}
```

# Изменения

| # | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | [v. 12](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3484043039) |  |
| 2 | Добавление недостающих значений Kind | [v. 14](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3382484723) | THB-3915 |
| 3 | Добавление параметра countryName |  | THB-4520 |
| 4 | Исправление optional / required полей | [v.22](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8442161789) |  |
| 5 | Расширение контракта данными квартир - apartmentFacts | v.28 | TTP-35390 |
| 6 | Добавление условия формирования apartmentFacts, если у объекта несколько комнат | Текущая | TTP-39575 |