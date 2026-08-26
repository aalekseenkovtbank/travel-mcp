# Общая информация по методу

| Назначение | Сохранение результатов проверки маппинга отелей |
|---|---|
| Бизнес-процесс | [\[HTLS-3429\] Поиск мастер-отеля для отеля поставщика](/pages/viewpage.action?pageId=5105535126) |
| Swagger |  |
| url | POST /v1/hotel-mapping/check-result' |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| headers |  |  |  |
| HotelsStaticApi.Authorization | Заголовок авторизации |  |  |
| Json in body |  |  |  |
| Динамическая Json структура<br />Структура тела запроса определяется реализацией на стороне платформы Клекс, мы ей не управляем.<br />Описание API Klecks<br />[Отели. Описание API Klecks](/pages/viewpage.action?pageId=5135277544) |  |  |  |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| - |  |  |  |

# Статусная модель

Статусная модель отражена на [странице](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5284158154) и данный сценарий затрагивает изменение статусов (результатов) для следующих таблиц:

- check\_supplier\_hotel\_mapping\_tasks
- check\_supplier\_hotel\_mapping\_result

# Алгоритмы работы метода

## MC.Основной сценарий

01. Выполняется авторизация по значению заголовка Authorization. (Ошибки авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
02. Выполняется валидация параметров запроса (Ошибки валидации: [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
    
    | Атрибут | Описание проверки | Код ошибки для атрибута | Текст ошибки для атрибута |
    |---|---|---|---|
    | taskMetadata/masterHotelID | Элемент присутствует в ответе, значение не пустое | empty\_required\_field | - |
    | taskMetadata/supplierHotelCode | Элемент присутствует в ответе, значение не пустое | empty\_required\_field | - |
    | taskMetadata/supplier | Элемент присутствует в ответе, значение не пустое | empty\_required\_field | - |
03. Запрос отсылается к топик hotels-backend.check-hotel-mapping.results в Kafka, который служит буфером накопления запросов для оптимизации использования ресурсов
04. Ответ с http = 200 возвращается вызывающей стороне.
05. Данные сообщения порционно вычитывает HotelMappingCheckResultsConsumer после чего выполняется обработка результатов проверки маппинга отелей
06. Выполняется поиск экземпляра check\_supplier\_hotel\_mapping\_tasks, для которого одновременно выполняются следующие условия:
    
    1. check\_supplier\_hotel\_mapping\_tasks.status == '[InProgress](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)'
    2. check\_supplier\_hotel\_mapping\_tasks.master\_hotel\_id == taskMetadata/masterHotelID из тела запроса
    3. check\_supplier\_hotel\_mapping\_tasks.supplier\_hotel\_id == taskMetadata/supplierHotelCode из тела запроса
    4. check\_supplier\_hotel\_mapping\_tasks.supplier\_id == taskMetadata/supplier из тела запроса
07. Выполняется проверка, что найден единственный экземпляр check\_supplier\_hotel\_mapping\_tasks.
    
    1. В случае если экземпляр не найден: формируем алерт 1.
    2. В случае если найдено более одного экземпляра: формируем алерт 2.
08. Выполняется обновление соответствующего экземпляра [check\_supplier\_hotel\_mapping\_tasks](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5201387526)
    
    | Атрибут | Значение |
    |---|---|
    | status | '[Match](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)' в случае если в json-теле сообщения значение correctAnswer/answer/radioButtonResult1 == 'yes'<br />'[NotMatch](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)' в случае если в json-теле сообщения значение correctAnswer/answer/radioButtonResult1 == 'no'<br />'[ExternalError](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)' в случае если в json-теле сообщения отсутствует элемент correctAnswer/answer/radioButtonResult1 |
    | completed\_at | Текущая дата и время |
09. В случае если в json-теле сообщения значение correctAnswer/answer/radioButtonResult1 == 'yes' добавляется экземпляр [check\_supplier\_hotel\_mapping\_result](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5201387526)
    
    | Атрибут | Значение |
    |---|---|
    | id | Автоинкрементируемое значение |
    | supplier\_hotel\_mapping\_task\_id | Сквозной идентификатор задачи на маппинг из соответствующего экземпляра check\_supplier\_hotel\_mapping\_tasks.supplier\_hotel\_mapping\_task\_id |
    | supplier\_hotel\_id | taskMetadata/supplierHotelCode |
    | master\_hotel\_id | taskMetadata/masterHotelID |
    | result | '[Match](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)' |
    | created\_at | Текущая дата и время |
10. В случае если в json-теле сообщения значение correctAnswer/answer/radioButtonResult1 == 'no' добавляется экземпляр [check\_supplier\_hotel\_mapping\_result](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5201387526)
    
    | Атрибут | Значение |
    |---|---|
    | id | Автоинкрементируемое значение |
    | supplier\_hotel\_mapping\_task\_id | Сквозной идентификатор задачи на маппинг из соответствующего экземпляра check\_supplier\_hotel\_mapping\_tasks.supplier\_hotel\_mapping\_task\_id |
    | supplier\_hotel\_id | taskMetadata/supplierHotelCode |
    | master\_hotel\_id | null |
    | result | '[NotMatch](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5590776823)' |
    | created\_at | Текущая дата и время |
11. В случае если в json-теле сообщения отсутствует элемент correctAnswer/answer/radioButtonResult1, то в [check\_supplier\_hotel\_mapping\_result](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5201387526) добавлять запись не нужно, такие ошибки будем отлавливать метриками и разбирать вручную.
12. Основной сценарий завершается.

Алерты

1. Необходимо сформировать алерт, что задача не была найдена (с указанием: supplier\_hotel\_id, master\_hotel\_id, supplier\_id).
2. Необходимо сформировать алерт, что было найдено более одной задачи (с указанием номеров этих задач).

# Связанные документы

[7 🏨 Запуск проверки маппинга \[Маппинг отелей\] \[HotelStaticApi\]](/pages/viewpage.action?pageId=5138008528)

# Изменения

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><th>№</th><th>Описание изменения</th><th>Примечание</th></tr><tr><td>1</td><td colspan="1"><div><p><span><a href="https://jira.tcsbank.ru/browse/THB-8758"><span></span>THB-8758</a> - <span>Getting issue details...</span> <span>STATUS</span></span></p></div></td><td colspan="1"><p>Исходная версия документа</p></td></tr><tr><td>2</td><td colspan="1"><div><p><span><a href="https://jira.tcsbank.ru/browse/THB-10085"><span></span>THB-10085</a> - <span>Getting issue details...</span> <span>STATUS</span></span></p></div></td><td colspan="1">Обновлено название атрибута task_status</td></tr><tr><td colspan="1">3</td><td colspan="1"><div><p><span><a href="https://jira.tcsbank.ru/browse/THB-8758"><span></span>THB-8758</a> - <span>Getting issue details...</span> <span>STATUS</span></span></p></div></td><td colspan="1"><ol><li>Изменена таблица с supplier_hotel_mapping_result на check_supplier_hotel_mapping_result</li><li>Добавлен сценарий &#34;В случае если в json-теле сообщения значение correctAnswer/answer/radioButtonResult1 == &#39;no&#39; &#34;</li><li>Ошибки EC-1, EC-2 заменены на алерты.</li><li>Для таблицы: check_supplier_hotel_mapping_result изменено поле status на result; удалено поле <span>source_type.</span></li><li><span><span>Добавлен сценарий &#34;В случае если в json-теле сообщения отсутствует элемент correctAnswer/answer/radioButtonResult1&#34;</span></span></li></ol></td></tr></tbody></table>