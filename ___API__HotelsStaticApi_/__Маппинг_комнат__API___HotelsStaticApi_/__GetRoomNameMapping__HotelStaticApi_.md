# Общая информация по методу

| Назначение | Получение списка маппингов |
|---|---|
| Бизнес процесс | [Поддержка](/pages/viewpage.action?pageId=1690696875) |
| Swagger | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | GET /v1/hotels/{hotelId}/rooms/name\_mapping |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| headers |  |  |  |
| - |  |  |  |
| path |  |  |  |
| hotelId | int32 | MANDATORY | Идентификатор отеля |
| query |  |  |  |
| roomId | int32 | OPTIONAL | Идентификатор мастер-комнаты |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | [RoomNameMappingApiResponse](#id-%F0%9F%8F%A8GetRoomNameMapping%5BHotelStaticApi%5D-RoomNameMappingApiResponse) | MANDATORY | Объект, содержащий ответ |

### Структура RoomNameMappingApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| roomNameMappings | [RoomNameMapping](#id-%F0%9F%8F%A8GetRoomNameMapping%5BHotelStaticApi%5D-RoomNameMapping)\[] | MANDATORY | Массив мастер-комнат |

### Структура RoomNameMapping

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| roomId | int32 | MANDATORY | Идентификатор мастер-комнаты |
| roomName | string | MANDATORY | Название мастер-комнаты |
| isActive | boolean | MANDATORY | Признак "Комната активна" |
| nameMappings | [NameMapping](#id-%F0%9F%8F%A8GetRoomNameMapping%5BHotelStaticApi%5D-NameMapping)\[] | MANDATORY | Массив маппингов на комнаты поставщиков |

### Структура NameMapping

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| supplierRoomName | string | MANDATORY | Название комнаты поставщика |
| supplierRoomNameHash | string | MANDATORY | Хэш от названия комнаты поставщика |
| supplierId | int32 | MANDATORY | Идентификатор поставщика |
| isActive | boolean | MANDATORY | Признак "Маппинг активен" |

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по значению заголовка Authorization.
   
   1. Ошибка авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
2. Выполняется выборка экземпляров CMS.SupplierRoomHashMapping, для которых SupplierRoomHashMapping.HotelId == hotelId из параметров запроса и SupplierRoomHashMapping.RoomId == roomId из параметров запроса (в случае если атрибут передан в запросе и значение не пустое).
   
   1. Техническая ошибка: [Common-EC-2](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2).
3. Выполняется группировка записей по значению SupplierRoomHashMapping.RoomId.
4. Формируется структура ответа
   
   | Параметр | Значение |
   |---|---|
   | roomNameMappings | Массив мастер-комнат |
   | -&gt;roomId | SupplierRoomHashMapping.RoomId |
   | -&gt;roomName | Room.Name записи, для которой Room.RoomId == SupplierRoomHashMapping.RoomId |
   | -&gt;isActive | Room.IsActive записи, для которой Room.RoomId == SupplierRoomHashMapping.RoomId |
   | -&gt;nameMappings | Массив смаппленных комнат поставщиков |
   | -&gt;-&gt;supplierRoomName | SupplierRoomHashMapping.SupplierRoomName |
   | -&gt;-&gt;supplierRoomNameHash | SupplierRoomHashMapping.SupplierRoomNameHash |
   | -&gt;-&gt;supplierId | SupplierRoomHashMapping.SupplierId |
   | -&gt;-&gt;isActive | SupplierRoomHashMapping.IsActive |
5. Ответ с http = 200 возвращается вызывающей стороне.
6. Основной сценарий завершается.

## Конфигурационные параметры

# Связанные документы

- Travel Hotels: \[[HTLS-4652](/pages/createpage.action?spaceKey=TRAVELHOTELS&title=HTLS-4652&linkCreation=true&fromPageId=4366653377) 1-pager | Hotels Content | Повышение качества маппинга комнат] —
- Travel Hotels: \[[HotelsAPI](/display/TRAVELHOTELS/HotelsAPI "HotelsAPI") POST internal\_api/v1/hotels/booking/
  
  Unknown macro: {orderId}
  
  /room\_name\_mapping/deactivate] —

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [THB-6258](https://jira.tcsbank.ru/browse/THB-6258) - Getting issue details... STATUS |