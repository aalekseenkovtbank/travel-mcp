# Общая информация

| Назначение | Получение описания комнат по идентификатору отеля |
|---|---|
| Бизнес-процессы | [Карточка отеля и тарифы](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=1690674674) |
| Контракт | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | GET /v1/hotels/{hotelId}/rooms |

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Authorization | string | MANDATORY | Ключ авторизации |
| Path |  |  |  |
| hotelId | int32 | MANDATORY | Идентификатор отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload | [HotelRoomsApiResponse](#id-%F0%9F%9B%80%F0%9F%8F%BFGetHotelRooms%5BHotelStaticAPI%5D-HotelRoomsApiResponse) | MANDATORY | Объект, содержащий ответ |

### Структура объекта HotelRoomsApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| IanaTimeZone | string | - | Наименование таймзоны |
| hotelRooms | [HotelRoom](#id-%F0%9F%9B%80%F0%9F%8F%BFGetHotelRooms%5BHotelStaticAPI%5D-HotelRoom)\[] | MANDATORY | Описание комнат отеля |

### Структура объекта HotelRoom

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| roomId | int32 | MANDATORY | Идентификатор комнаты |
| name | string | MANDATORY | Название на русском |
| nameTranslations | [TextTranslation](#id-%F0%9F%9B%80%F0%9F%8F%BFGetHotelRooms%5BHotelStaticAPI%5D-TextTranslation)\[] | OPTIONAL | Названия на иностранных языках |
| description | string | OPTIONAL | Описание на русском |
| descriptionTranslations | [TextTranslation](#id-%F0%9F%9B%80%F0%9F%8F%BFGetHotelRooms%5BHotelStaticAPI%5D-TextTranslation)\[] | OPTIONAL | Описание на иностранных языках<br />Пока атрибут не добавляем |
| size | double | OPTIONAL | Площадь |
| facilities | int32\[] | OPTIONAL | Удобства в номере |
| images | string\[] | OPTIONAL | Фотографии комнаты |
| bedConfigurations | [BedConfiguration](#id-%F0%9F%9B%80%F0%9F%8F%BFGetHotelRooms%5BHotelStaticAPI%5D-BedConfiguration)\[] | MANDATORY | Конфигурации кроватей |

### Структура объекта BedConfiguration

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypes | BedType\[] | MANDATORY | Описание спальных мест |

### Структура объекта BedType

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypeId | int32 | MANDATORY | Идентификатор типа спального места |
| isExtraBed | boolean | MANDATORY | Признак "Дополнительное спальное место" |

### Структура объекта TextTranslation

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| language | enum | MANDATORY | Язык перевода |
| value | string | MANDATORY | Строковое значение на указанном языке |

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по значению заголовка Authorization.
   
   1. Ошибка авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
2. Выполняется проверка, что экземпляр Hotel найден по значению hotelId из запроса.
   
   1. Неуспешная проверка [Common-EC-4](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2).
3. Выполняется выборка экземпляров Room, для которых Room.HotelId == hotelId из параметров запроса.
   
   1. Техническая ошибка: [Common-EC-2](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2).
4. Для каждого найденного экземпляра Room выполняется поиск наименования на иностранном языке в таблице RoomTranslation, где Room.RoomId == RoomTranslation.RoomId, выполняется сохранение значений LanguageId и Name. В случае, если комната не была найдена, поле в ответе не заполняется.
5. Формируется структура ответа
   
   | Параметр | Значение |
   |---|---|
   | IanaTimeZone | Наименование таймзоны, берется значение Location.TimeZoneName, для которого Location.LocationID = HotelDetails.PrimaryLocationID отеля из запроса |
   | hotelRooms | Массив найденных экземпляров Room |
   | -&gt;roomId | Room.RoomId |
   | -&gt;name | Room.Name |
   | -&gt;nameTranslations | Массив наименований комнат на иностранном языке |
   | -&gt;-&gt;language | RoomTranslation.LanguageId |
   | -&gt;-&gt;value | RoomTranslation.Name |
   | -&gt;description | Room.Description |
   | -&gt;size | Room.Size |
   | -&gt;facilities | Массив значений RoomFacility.FacilityId экземпляров RoomFacility, для которых RoomFacility.RoomId == Room.RoomId |
   | -&gt;images | Массив значений RoomMedia.URL экземпляров RoomMedia, для которых RoomMedia.RoomId == Room.RoomId |
   | -&gt;bedConfigurations | Описание экземпляров RoomBedConfiguration, для которых RoomBedConfiguration.RoomId == Room.RoomId, отсортированные по RoomBedConfiguration.ConfigurationNumber по возрастанию |
   | -&gt;-&gt;bedTypes | Описание экземпляров RoomBed, входящих в RoomBedConfiguration, отсортированные по RoomBed.BedNumber по возрастанию |
   | -&gt;-&gt;-&gt;bedTypeId | RoomBed.BedTypeId |
   | -&gt;-&gt;-&gt;isExtraBed | RoomBed.IsExtraBed |
6. Ответ возвращается вызывающей стороне.
7. Основной сценарий завершается.

# Связанные документы

[StaticApi и JsonApi. Статика Прямых отелей](/pages/viewpage.action?pageId=3627777147)

[\[HotelsAPI\] SutochnoOrderWebhook - Обработка вебхука от Суточно](/pages/viewpage.action?pageId=4938271013)

[\[HotelsAPI\] getBookingOrder\_v1 - Получение карточки бронирования](/pages/viewpage.action?pageId=3043347904)

[\[HotelsAPI\] getBookingOrder\_v3 - Получение карточки бронирования](/pages/viewpage.action?pageId=1894107321)

[\[HotelsAPI\] getCheckOutRate\_v3 - Получение данных тарифа для CheckOut](/pages/viewpage.action?pageId=2722927693)

[\[HotelsAPI\] getRates\_v3 - Поиск доступных тарифов и комнат в отеле](/pages/viewpage.action?pageId=4248104199)

[\[HotelsAPI\] getUpgradedRate - Получение тарифа для улучшения](/pages/viewpage.action?pageId=7948358605)

[getBookingOrder - общая логика](/pages/viewpage.action?pageId=6054922512)

[hotels\_static.hotel\_rooms](/display/TRAVELHOTELS/hotels_static.hotel_rooms)

[Маппинг для документа о бронировании](/pages/viewpage.action?pageId=2599577169)

## Конфигурационные параметры

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [THB-4279](https://jira.tcsbank.ru/browse/THB-4279) - Getting issue details... STATUS |