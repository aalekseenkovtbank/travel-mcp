# Метод удален.

| Назначение | Получение статической информации об отеле |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/notificationcenter-hotelinfo |

### Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer($int32) | REQUIRED | идентификатор master hotel id |

### Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | [NotificationCenterHotelInfoApiResponse](#id-%5BDELETED%5D%5BHotelStaticApi%5DGetHotelInfoForBookingNotificationCenter%28/internal_api/v1/hotels/notificationcenterhotelinfo%29-NotificationCenterHotelInfoApiResponse) | REQUIRED | Родительский объект, содерджащий ответ |

### Структура NotificationCenterHotelInfoApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| MasterHotelId | int | REQUIRED | идентификатор master hotel id |
| Name | string | REQUIRED | Наименование master-отеля |
| Address | string | REQUIRED | Адрес отеля |
| MasterLocationId | int | REQUIRED | Идентификатор master-локации |
| Location | [Location](#id-%5BDELETED%5D%5BHotelStaticApi%5DGetHotelInfoForBookingNotificationCenter%28/internal_api/v1/hotels/notificationcenterhotelinfo%29-Location) | REQUIRED | Объект, описывающий регион, в котором находится master-отель |
| CheckInTime | string | REQUIRED | Время заезда |
| CheckOutTime | string | REQUIRED | Время выезда |

### Структура Location

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| MasterLocationId | string | OPTIONAL | идентификатор master-локации |
| Name | string | OPTIONAL | имя региона\\локации |
| Type | string | OPTIONAL | тип региона\\локации |
| CountryCode | string | OPTIONAL | Код страны |

## Алгоритм работы метода GetHotelInfoForBookingNotificationCenter

1. Вызывается хранимая процедура \[HotelStaticApi\_GetNotificationCenterHotelInfo] в базе \[TravelDB]. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId
2. Хранимая процедура делает выборку данных из таблицы \[TravelDB]..\[HotelDetails] с условием \[HotelDetails].HotelID = masterHotelId  
   и выполняется операция объединения данных с таблицей \[TravelDB]..\[Location] для получения данных о локации, в которой находится master-отель по \[HotelDetails].PrimaryLocationID = \[Location].LocationID  
   и выполняется операция объединения данных с таблицей \[TravelDB]..\[Location] для получения данных о стране, в которой находится master-отель по \[HotelDetails].CountryID =  \[Location].LocationID  
   и выполняется операция объединения данных с таблицей \[TravelDB]..\[Hotel] для получения данных о master-отеле по \[HotelDetails].HotelID = \[Hotel].HotelID  
   и выполняется операция объединения данных с константными значениями, соответствующими \[HotelDetails]..\[Type]
3. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель NotificationCenterHotelInfoApiResponse (см. [🌍 Domain Models \[HotelsStaticApi\]](/pages/viewpage.action?pageId=3199850762))
   
   <table><colgroup><col/><col/></colgroup><tbody><tr><th><p>Параметр</p></th><th colspan="1">Источник данных</th></tr><tr><td colspan="1">payload</td><td colspan="1">-</td></tr><tr><td>-&gt;MasterHotelId</td><td colspan="1">[TravelDB]..[HotelDetails].HotelId</td></tr><tr><td>-&gt;Name</td><td colspan="1">[TravelDB]..[HotelDetails].HotelName</td></tr><tr><td>-&gt;Address</td><td colspan="1">[TravelDB]..[HotelDetails].HotelAddress</td></tr><tr><td>-&gt;MasterLocationId</td><td colspan="1">[TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td>-&gt;Location</td><td colspan="1">Объект, описывающий локацию, в которой находится master-отель с HotelId</td></tr><tr><td colspan="1">-&gt;-&gt;MasterLocationId</td><td colspan="1">[TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">-&gt;-&gt;Name</td><td colspan="1">[TravelDB]..[Location].LocationName для локации, в которой находится master-отель с HotelId</td></tr><tr><td colspan="1">-&gt;-&gt;Type</td><td colspan="1"><p>Принимает следующие значения в зависимости от [TravelDB]..[Location].LocationType </p><ul><li><span>1 - Continent</span></li><li><span>2 - Country</span></li><li><span>3 - Province (State)</span></li><li><span>5 - City</span></li><li><span>6 - Airport</span></li><li><span>7 - Railway Station</span></li><li><span>9 - Point of Interest</span></li><li><span>10 - Multi-Region (within a country)</span></li><li><span>11 - Street</span></li><li><span>12 - Subway (Entrace)</span></li><li><span>13 - Neighborhood</span></li><li><span>14 - Bus Station</span></li><li><span>15 - Multi-City (Vicinity)</span></li></ul></td></tr><tr><td colspan="1">-&gt;-&gt;CountryCode</td><td colspan="1">[TravelDB]..[Location].Code для страны, в которой находится локация, в которой находится master-отель с HotelId</td></tr><tr><td>-&gt;CheckInTime</td><td colspan="1">[TravelDB]..[Hotel].CheckIn</td></tr><tr><td>-&gt;CheckOutTime</td><td colspan="1">[TravelDB]..[Hotel].CheckOut</td></tr></tbody></table>
4. Возвращается результаты работы метода