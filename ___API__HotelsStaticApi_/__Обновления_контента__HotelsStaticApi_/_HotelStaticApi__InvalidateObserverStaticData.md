# Общая информация

| Назначение | Метод заполняет таблицу очереди для потребителей данных статики. |
|---|---|
| Бизнес-процессы | Отслеживание изменений в статике \[HotelStaticApi]<br />Обновление контента на стороне потребителя \[HotelStaticApi] |
| Контракт | ```<br />/internal_api/v1/static_data/invalidate_observer_static_data<br />``` |

# Протокол

## Структура запроса

Все 3 раздела опциональны. Соответствующие строки удаляются, если в них нет необходимости

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Authorization | string | mandatory | Ключ авторизации |
| Body |  |  |  |
| observer\_id | integer | mandatory | Идентификатор системы потребителей |
| consumers\_list | :\[] | optional | Массив объектов потребителей. Максимальная длинная массива 10 элементов. |

**consumer**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| consumer\_id | integer | mandatory | Идентификатор потребителей |
| master\_items\_list | integer:\[] | optional | Массив мастеровых идентификаторов сущностей. Максимальная длинна массива 10000 элементов. |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload |  | mandatory | Объект, содержащий ответ |

### Структура объекта InvalidateObserverStaticData

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| status | enum | mandatory | Статус процесса инвалидации.<br />Варианты ответа:<br />New<br />InProgress<br />Success<br />Failed<br />Соответствие значений статуса метода и статуса в таблицы [см тут](https://wiki.tcsbank.ru/display/TRAVELHOTELS/InvalidateStaticData) |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | REQUIRED | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| Прошлый процесс инвалидации не закончился.  В таблице InvalidateStaticData есть запись со статусом - 1 | ```<br />processStart<br />``` | Ошибка запуска процесса инвалидации. | previousProcessInProgress | Предыдущий процесс инвалидации еще не закончился. | N/A | 400 | ```json<br />{
    "error": {
        "code": "processStart",
        "Message": "Ошибка запуска процесса инвалидации.",
        "details": {
            "code": "previousProcessInProgress",
            "message": "Предыдущий процесс инвалидации еще не закончился."     
        }
    }
}<br />``` |
| observer\_id - null или нет в таблице CMS..Observer | incorrectValue | Ошибка при валидации запроса. | noObserverId | Индентификатор системы поставщика не передан или отсутствует в системе. | observer\_Id | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "noObserverId",
            "message": "Индентификатор системы поставщика не передан или отсутствует в системе.",
            "attribute": "observer_Id"
        }
    }
}<br />``` |
| Сonsumer\_id из массива не относится к указанному observer\_id | incorrectValue | Ошибка при валидации запроса. | incorrectСonsumerId | Не корректный идентификакор потребителя. | consumer\_id | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "incorrectСonsumerId",
            "message": "Не корректный идентификакор потребителя.",
            "attribute": "consumer_id"
        }
    }
}<br />``` |
| Указанный consumer\_id нет в таблице  CMS..Consumer |  |  |  |  |  |  |  |
| Сonsumers\_list.length &gt;10 | incorrectValue | Ошибка при валидации запроса. | consumersListLimit | Массив потребителей превышает максимальное значение. | consumers\_list | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "consumersListLimit",
            "message": "Массив потребителей превышает максимальное значение.",
            "attribute": "consumer_id"
        }
    }
}<br />``` |
| Master\_items\_list.length &gt;1000 | incorrectValue | Ошибка при валидации запроса. | masterItemsListLimit | Массив ид сущности превышает максимальное значение. | master\_items\_list | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "masterItemsListLimit",
            "message": "Массив ид сущности превышает максимальное значение.",
            "attribute": "master_items_list"
        }
    }
}<br />``` |
| CMS..Consumer.InvalidateData = null \\|\\| CMS..Consumer.InvalidateData = "" | incorrectValue | Ошибка при получении Consumer.InvalidateData. | incorrectInvalidateData | Значение Customer.InvalidateData пустое. | N/A | 400 | ```json<br />{
"error": {
    "code": "incorrectValue",
    "Message": "Ошибка при получении Consumer.InvalidateData.",
    "details": {
        "code": "incorrectInvalidateData",
        "message": "Значение Customer.InvalidateData пустое.",
        "attribute": "N/A"
    }
  }
}<br />``` |

# Алгоритмы работы метода

## MC.Основной сценарий

1. Проверили есть ли запущенные процесс заполенния. Сделали запрос в таблицу CMS.InvalidateStaticData на наличие записей со статусом 0 или 1.
   
   1. Если есть запись со статусом 0 или 1. Перешли к .
2. Распарсили запрос.
3. Выполнили валидацию observer\_id по таблице CMS..Observer. 
   
   1. Если не нашли ИД, перешли к .
   2. Если observer\_id пустой, перешли к .
4. Выполнили валидацию массива consumers\_list. 
   
   1. Если массив consumers\_list.length &gt;10 перешли к .
   2. Если массив consumers\_list.length = null перешли к .
   3. Если массив consumers\_list.length &lt; = 10 перешли к .
5. Запустили работу [джобы](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3940601000) - УКАЗАТЬ НАЗВАНИЕ
6. Сформировали ответ, где status = "inProgress".
7. Вернули тело ответа с кодом 200.

## AC-1. Альтернативный сценарий если consumers\_list.length = null

1. Сформировали запись в таблице CMS.InvalidateStaticData.
   
   | Таблица | Запрос |
   |---|---|
   | CreateAt | Текущая время и дата. Для всех записей одного вызова значение одинаковое |
   | ObserverId | observer\_id |
   | ConsumerId | не заполняем |
   | Item | не заполняем |
   | Status | 0 |
2. Вернулись к основному сценарию пункт 5.

## AC-2. Альтернативный сценарий если consumers\_list.length &lt; = 10

1. Проверили значения consumer\_id.  
   
   1. Проверили значения consumer\_id по таблице [CMS..Consumer](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.Consumer) если не нашли хотя бы один ИД, перешли к .
   2. Проверили значения consumer\_id по таблице [CMS..Consumer](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.Consumer) если хотя бы один consumer\_id не принадлежит ИД observer, перешли к .
2. Для каждого consumer\_id выполнили валидацию master\_items\_list.
   
   1. Если массив master\_items\_list.length &gt;10000 перешли к .
3. Для каждого consumer\_id .
   
   1. По ConsumerId запросили значение столбца InvalidateData из таблицы [CMS..Consumer](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.Consumer).
      
      1. Если InvalidateData = null или пустое, перешли к .
   2. Сформировали запись в таблице CMS.InvalidateStaticData.
      
      <table><colgroup><col/><col/></colgroup><tbody><tr><th>Таблица</th><th>Запрос</th></tr><tr><td>CreateAt</td><td>Текущая время и дата. Для всех записей одного вызова значение одинаковое</td></tr><tr><td>ObserverId</td><td>observer_id</td></tr><tr><td>ConsumerId</td><td>consumers_list.consumer_id проверяем уникальные набор ИД, дубли пропускаем.</td></tr><tr><td>Item</td><td><p>Формируем объекты JSON исходя из полученного значения <span>InvalidateData.<br/></span></p><table><tbody><tr><th>Параметры Items</th><th><span>Источник</span></th></tr><tr><td><p>itemType</p></td><td><span>InvalidateData.itemType.</span></td></tr><tr><td>itemFields</td><td><span>InvalidateData.itemFields.</span></td></tr><tr><td>itemIds</td><td>consumers_list.master_items_list. Заполняем если master_items_list != null. Проверяем уникальные набор ИД, дубли пропускаем.</td></tr></tbody></table><p><br/></p></td></tr><tr><td>Status</td><td>0</td></tr></tbody></table>
4. Вернулись к основному сценарию пункт 5.

## EC-1. Формирование ошибки

1. В зависимости от ошибки сформировали тело ответа ошибки ( см. таблицу кейсов ).
2. Вернули ответ.

# Связанные документы

## Конфигурационные параметры

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | THB-4761 |