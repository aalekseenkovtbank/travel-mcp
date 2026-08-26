| Назначение | Получение информации о master-отеле по идентифкатору отеля для формирования ответа с деталями бронирования для старых версий МБ |
|---|---|
| Бизнес процесс | [HTLS-2726](https://jira.tcsbank.ru/browse/HTLS-2726) - Getting issue details... STATUS |
| Swagger |  |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/{masterHotelId}/reservation-hotelinfo |
| Метод | GET |

# Протокол

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Path

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | master id отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | [object: Response](#HotelStaticAPIgetHotelInfoForReservationDetails-Response) | REQUIRED | Объект, содержащий ответ |

### Структура GetHotelInfoForReservationDetailsResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | Идентификатор master hotel id |
| name | string | REQUIRED | Наименование отеля |
| location | [object: LocationForReservationDetails](#HotelStaticAPIgetHotelInfoForReservationDetails-LocationForReservationDetails) | REQUIRED | Объект, описывающий расположение отеля |
| image | string | OPTIONAL | URL основной фотографии отеля |
| checkInTime | string($timeonly) | OPTIONAL | Стандартное время заезда в отель |
| checkOutTime | string($timeonly) | OPTIONAL | Стандартное время выезда из отеля |
| phone | string | OPTIONAL | Номер телефона отеля |
| email | string | OPTIONAL | E-mail отеля |

### Структура LocationForReservationDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| address | string | REQUIRED | Адрес отеля |
| countryCode | string | REQUIRED | Код страны |
| name | string | REQUIRED | Название региона\\локации |
| coordinates | object: [Coordinates](#HotelStaticAPIgetHotelInfoForReservationDetails-Coordinates) | REQUIRED | Объект, описывающий местоположение отеля (широта, долгота) |
| cityName | string | OPTIONAL | Название города на русском языке |
| countryName | string | OPTIONAL | Название страны на русском языке |

### Структура Coordinates

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| latitude | decimal | REQUIRED | Географическая широта |
| longitude | decimal | REQUIRED | Географическая долгота |

# Ошибки: коды и описания

| Сценарий | HTTP код |
|---|---|
| Неавторизованный запрос | 401 |
| Ошибка сервера при выполнении запроса | 500 |
| Не передан обязательный параметр masterHotelId | 404 |
| Не существует отеля с указанным masterHotelId | 204 |

# Алгоритм работы метода

1. Выполняется авторизация по предоставленному apiKey
2. Разбор и валидация запроса
3. Вызывается хранимая процедура \[ HotelStaticApi\_GetHotelInfoForReservationDetails ] в TravelDB. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId
4. Выполняется операция объединения таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
   и выполняется операция объединения данных с таблицей TravelDB.HotelPhone по HotelPhone.HotelId = HotelDetails.HotelId и фильтруется по HotelPhone.PhoneTypeID = 1 и HotelPhone.IsDefault=1;
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель

# Маппинг данных на модель Hotel Static API

<table><colgroup><col/><col/></colgroup><thead><tr><th><p>Параметр</p></th><th colspan="1"><p>Источник данных</p></th></tr></thead><tbody><tr><td colspan="1">payload</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;masterHotelId</td><td colspan="1"><span>[TravelDB]..[HotelDetails].HotelId</span></td></tr><tr><td colspan="1">-&gt;name</td><td colspan="1"><span>[TravelDB]..[HotelDetails].HotelName</span></td></tr><tr><td colspan="1">-&gt;image</td><td colspan="1"><ul><li><span>[TravelDB]..[<span>HotelDetails</span>].ImagePath</span></li><li><span>Если нет значения - не<span> </span><span>передаем ссылку на картинку</span></span></li></ul></td></tr><tr><td colspan="1">-&gt;checkInTime</td><td colspan="1"><span>[TravelDB]..[HotelDetails].CheckInTime</span></td></tr><tr><td colspan="1">-&gt;checkOutTime</td><td colspan="1"><span>[TravelDB]..[HotelDetails].CheckOutTime</span></td></tr><tr><td colspan="1">-&gt;phone</td><td colspan="1">[TravelDB]..[HotelPhone].Number</td></tr><tr><td colspan="1">-&gt;email</td><td colspan="1"><ul><li>[TravelDB]..[HotelDetails].Email</li><li><span>Если нет значения - не<span> </span><span>передаем почту</span></span></li></ul></td></tr><tr><td colspan="1">-&gt;location</td><td colspan="1"><br/></td></tr><tr><td colspan="1"><span>-&gt;-&gt;address</span></td><td colspan="1"><div><p>[TravelDB]..[HotelDetails].HotelAddress</p></div></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span>countryCode</td><td colspan="1"><p><span>[TravelDB]</span>..[HotelDetails].CountryCode</p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span>name</td><td colspan="1"><span>[TravelDB]..[HotelDetails].LocationName</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span>cityName</td><td colspan="1"><ul><li><span><span>[TravelDB]..[HotelDetails].</span>CityName</span></li><li><span>Если нет значения - не <span>передаем название города</span></span></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span>countryName</td><td colspan="1"><ul><li><span><span>[TravelDB]..[HotelDetails].CountryName</span></span></li><li><span>Если нет значения - не <span>передаем название страны</span></span></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;coordinates</span></td><td colspan="1"><br/></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span><span>-&gt;latitude</span></td><td colspan="1"><span>[TravelDB]..[HotelDetails].latitude</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;</span><span>-&gt;longitude</span></td><td colspan="1"><span>[TravelDB]..[HotelDetails].longitude</span></td></tr></tbody></table>

# Связанные документы

- \[[HotelsAPI](/display/TRAVELHOTELS/HotelsAPI "HotelsAPI") getReservation - Получение бронирования для МБ]

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создание нового метода | **Текущая** | [THB-7243](https://jira.tcsbank.ru/browse/THB-7243) - Getting issue details... STATUS |
| 2 |  |  |  |