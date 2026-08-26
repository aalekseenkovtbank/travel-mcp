# Общая информация по методу

| Назначение | Поиск лучшего отеля и дедубликация |
|---|---|
| Бизнес процесс | [Поддержка](/pages/viewpage.action?pageId=1690696875) |
| Swagger | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-b-cloud-test-wl1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-b-cloud-test-wl1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | POST /internal\_api/v1/support/hotels/deduplicate |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| headers |  |  |  |
| - |  |  |  |
| body |  |  |  |
| hotelIds | int32\[] | MANDATORY | Перечень идентификаторов мастер-отелей для которых надо выполнить дедубликацию. |
| username | string |  | идентификатор пользователя |

## Структура ответа

HTTP 200 OK

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
|  |  |  |  |

HTTP 400 BadRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
|  |  |  | С сообщением ошибки валидации при работе процесса дедубликации |

При Ошибки валидации запроса:

1. В переданном списке идентификаторов отелей присутствует несуществующий отель или отель из исключенной категории [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
   
    Свернуть исходный код
   
   | `{`<br />`"error": {`<br />`"code": "incorrectValue",`<br />`"Message": "Ошибка при валидации запроса.",`<br />`"details": {`<br />`"code": "incorrectHotelIds",`<br />`"message": "Отели '<id не найденных отелей через запятую>' не найдены или принадлежат к исключенной категории.",`<br />`"attribute": "hotelIds"`<br />`}`<br />`}`<br />`}` |
   |---|

# Параметры конфигурации

| Параметр | Тип | Описание |
|---|---|---|
| ExcludedCategories | int\[] | Список идентификаторов категорий для которых не проводится дедубликация |

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по значению заголовка Authorization. (Ошибки авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
2. Выполняется валидация параметров запроса (Ошибки валидации: [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
   
   | Атрибут | Описание проверки | Код ошибки для атрибута | Текст ошибки для атрибута |
   |---|---|---|---|
   | hotelIds | Значение не пустое | empty\_value | Значение атрибута не может быть пустым |
3. Выполняется проверка на существование отелей переданных в запросе. В случае если не для всех идентификаторов отелей найдены отели в БД возвращается ошибка. http 400.
4. Выполняется запуск сервиса дедубликации.
5. Ответ http = 200 возвращается вызывающей стороне.

## SC-1. Алгоритм работы сервиса запуска хранимой процедуры

1. Выполняется валидация запроса
   
   1. Если параметр hotelIds пустой  возвращается ошибка [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
   2. Если параметр hotelIds содержит идентификатор несуществующего отеля [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
   3. Если параметр hotelIds содержит идентификатор отеля принадлежащего исключенной категории, из параметра конфигурации ExcludedCategories [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2)
2. Выполняется обращение к хранимой процедуре CMS.HotelStaticApi\_MergeHotels.
   
   Входные параметры:
   
    - коллекция hotelIds в виде строки где идентификаторы отелей разделены запятой
   
    - идентификатор пользователя.
   
   Поскольку дедубликация подразумевает изменение контента для отелей, рекомендованный **Timeout** при ожидании ответа от хранимой процедуры = **120 секунд**
3. В таблице **CMS.HotelHistory** появляется новая запись
   
   | Атрибут | Значение |
   |---|---|
   | HotelID | Значение не пустое |
   | Type | ? |
   | Action | ? |
   | ChangeDate | текущая дата и время |
   | Editor | идентификатор пользователя из запроса |
4. Если во время ожидания результатов работы хранимой процедуры вернулась ошибка: [EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5909146685#id-%F0%9F%8D%92DeduplicateHotels%5BHotelStaticApi%5D-EC-1.%D0%9E%D1%88%D0%B8%D0%B1%D0%BA%D0%B0%D0%BE%D0%B1%D1%80%D0%B0%D1%89%D0%B5%D0%BD%D0%B8%D1%8F%D0%BA%D0%B1%D0%B0%D0%B7%D0%B5%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85)
5. Основной сценарий завершается.

## EC-1. Ошибка обращения к базе данных

1. Ошибка записывается в лог.
2. Завершение работы сценария.

# Связанные документы

- Business Process Management: \[URP:- [Hotels](/pages/createpage.action?spaceKey=TRAVELHOTELS&title=Hotels&linkCreation=true&fromPageId=5909146685) Взаимодействие с API] —

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [THB-10488](https://jira.tcsbank.ru/browse/THB-10488) - Getting issue details... STATUS |
|  |  |  | [THB-11336](https://jira.tcsbank.ru/browse/THB-11336) - Getting issue details... STATUS |