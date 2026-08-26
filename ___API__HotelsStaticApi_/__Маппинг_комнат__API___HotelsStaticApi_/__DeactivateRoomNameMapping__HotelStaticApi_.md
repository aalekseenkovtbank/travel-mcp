# Общая информация по методу

| Назначение | Обновление статуса маппинга комнаты |
|---|---|
| Бизнес процесс | [Поддержка](/pages/viewpage.action?pageId=1690696875) |
| Swagger | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | POST /v1/room\_name\_mapping/deactivate |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| headers |  |  |  |
| - |  |  |  |
| body |  |  |  |
| hotelId | int32 | MANDATORY | Идентификатор мастер-отеля |
| roomId | int32 | MANDATORY | Идентификатор мастер-комнаты |
| supplierRoomNameHash | string | MANDATORY | Хэш от названия комнаты поставщика |
| supplierId | int32 | MANDATORY | Идентификатор поставщика |
| deactivateReasonCodes | int32\[] | MANDATORY | Перечень кодов причин деактивации |
| deactivateReasonComment | string | OPTIONAL | Комментарий о причине деактивации в свободной форме |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| - |  |  |  |

# Алгоритмы работы метода

## MC.Основной сценарий

01. Выполняется авторизация по значению заголовка Authorization. (Ошибки авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
02. Выполняется валидация параметров запроса (Ошибки валидации: [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
    
    | Атрибут | Описание проверки | Код ошибки для атрибута | Текст ошибки для атрибута |
    |---|---|---|---|
    | deactivateReasonComment | Длина значения не превышает 250 символов | length\_exceeded | Длина значения не должна превышать 250 символов |
    | deactivateReasonComment | Значение не пустое в случае если среди значений deactivateReasonCodes найдено значение '99' | empty\_value | Значение атрибута не может быть пустым, если среди значений deactivateReasonCodes передано значение "99 (Другое)" |
03. Выполняется поиск экземпляра CMS.SupplierRoomHashMapping, для которого одновременно выполняются следующие условия:
    
    1. SupplierRoomHashMapping.RoomId == roomId из параметров запроса
    2. SupplierRoomHashMapping.SupplierRoomNameHash == supplierRoomNameHash из параметров запроса
    3. SupplierRoomHashMapping.SupplierId == supplierId из параметров запроса
04. Выполняется проверка, что найден единственный экземпляр CMS.SupplierRoomHashMapping.
    
    1. Экземпляр не найден или найдено более одного экземпляра: переход к [EC-1](#id-%E2%9D%8CDeactivateRoomNameMapping%5BHotelStaticApi%5D-EC-1).
05. Выполняется поиск экземпляра CMS.SupplierRoomHashMappingTask, для которого одновременно выполняются следующие условия:
    
    1. SupplierRoomHashMappingTask.SupplierRoomNameHash == supplierRoomNameHash из параметров запроса
    2. SupplierRoomHashMappingTask.SupplierId == supplierId из параметров запроса
    3. SupplierRoomHashMappingTask.HotelId == hotelId из параметров запроса
    4. SupplierRoomHashMappingTask.Status != '[9](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5009334578)'.
06. Выполняется проверка, что найден единственный экземпляр CMS.SupplierRoomHashMappingTask.
    
    1. Экземпляр не найден: продолжение выполнения сценария.
       
       Такое поведение заложено на случай, если мы захотим обновить причины удаления деактивации маппинга для ранее деактивированного маппинга или захотим удалить маппинг, созданный вручную (без задачи)
    2. Найдено больше одного экземпляра: [Common-EC-2](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
07. Выполняется поиск экземпляра TravelDB.SupplierRoomHashMapping, для которого одновременно выполняются следующие условия:
    
    1. SupplierRoomHashMapping.RoomId == roomId из параметров запроса
    2. SupplierRoomHashMapping.SupplierRoomNameHash == supplierRoomNameHash из параметров запроса
    3. SupplierRoomHashMapping.SupplierId == supplierId из параметров запроса.
08. Выполняется проверка, что найден единственный экземпляр TravelDB.SupplierRoomHashMapping.
    
    1. Экземпляр не найден: продолжение выполнения сценария.
       
       Такое поведение заложено на случай, если мы захотим обновить причины удаления деактивации маппинга для ранее деактивированного маппинга
09. Выполняется обновление найденных экземпляров объектов:
    
    1. CMS.SupplierRoomHashMappingTask (в случае если был найден единственный экземпляр)
       
       1. SupplierRoomHashMappingTask.Status = 5
       2. SupplierRoomHashMappingTask.UpdatedAt = Текущая дата и время
    2. CMS.SupplierRoomHashMapping
       
       1. SupplierRoomHashMapping.IsActive = 0
       2. SupplierRoomHashMapping.Moved = 0
       3. SupplierRoomHashMapping.DeactivateReasonCodes = массив deactivateReasonCodes из параметров запроса
       4. SupplierRoomHashMapping.DeactivateReasonComment = deactivateReasonComment из параметров запроса
10. Выполняется запуск процедуры импорта изменений маппинга комнат из CMS в TravelDb
11. Ответ с http = 200 возвращается вызывающей стороне.
12. Основной сценарий завершается.

## EC-1. Маппинг не найден

1. Формируется структура error следующего содержания:
   
   1. code - mapping\_not\_found.
2. Описание ошибки возвращается вызывающей стороне.
3. Ответ с http = 400 и описанием ошибки возвращается вызывающей стороне.
4. Продолжается выполнение [основного сценария](#id-%E2%9D%8CDeactivateRoomNameMapping%5BHotelStaticApi%5D-MC).

## Конфигурационные параметры

# Связанные документы

- Travel Hotels: \[[HTLS-4652](/pages/createpage.action?spaceKey=TRAVELHOTELS&title=HTLS-4652&linkCreation=true&fromPageId=4366659068) 1-pager | Hotels Content | Повышение качества маппинга комнат] —
- Travel Hotels: \[[HotelsAPI](/display/TRAVELHOTELS/HotelsAPI "HotelsAPI") POST internal\_api/v1/hotels/booking/
  
  Unknown macro: {orderId}
  
  /room\_name\_mapping/deactivate] —

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [THB-6258](https://jira.tcsbank.ru/browse/THB-6258) - Getting issue details... STATUS |
| 2 | Добавлена проверка на статус 9 при поиске задачи на удаление |  | [THB-10726](https://jira.tcsbank.ru/browse/THB-10726) - Getting issue details... STATUS |