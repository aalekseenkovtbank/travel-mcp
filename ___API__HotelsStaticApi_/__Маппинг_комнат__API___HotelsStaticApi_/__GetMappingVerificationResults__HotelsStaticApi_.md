**Оглавление:**

# Общая информация по методу

| Назначение | Получение результатов валидации маппинга комнат от Kleks |
|---|---|
| Бизнес процесс | [Повышение качества маппинга комнат](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6252908016) |
| Swagger | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | POST /v1/room-mappings/verified |

## Структура запроса

Метод является сервисным для получения данных со стороны Kleks. Структура запроса и пример тела описаны в документации Kleks: [Сервис экспорта](https://twork.tinkoff.ru/klecks-customer/documentation/index.html#%D0%A1%D0%B5%D1%80%D0%B2%D0%B8%D1%81-%D1%8D%D0%BA%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0)

## Структура ответа

### Успешный ответ

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| body |  |  |  |
| id | integer | REQUIRED | Идентификатор полученного задания |

### Неуспешный ответ

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| body |  |  |  |
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Описание ошибки |
| details | [ErrorDetails](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3348934699#id-%5BHotelStaticApi%5DGetImageUrls%28/internal_api/v1/search/images%29-ErrorDetails)\[] | OPTIONAL | Идентификатор ошибки |

#### Структура ErrorDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки атрибута |
| message | string | OPTIONAL | Текст ошибки атрибута |
| attribute | string | REQUIRED | Код атрибута |

# Описание логики

Описание параметров, получаемых от Kleks: [Комнаты. Описание API Klecks](/pages/viewpage.action?pageId=6339582037)

## MC. Основной сценарий

1. Проверить, что taskMetadata.taskId присутствует;
   
   1. Иначе - отправить неуспешный ответ;
2. По каждому объекту отправить событие в топик [kleks-room-mapping-results](/pages/viewpage.action?pageId=6423619874):
   
   <table><colgroup><col/><col/></colgroup><tbody><tr><th>Атрибут</th><th>Значение</th></tr><tr><td>source</td><td>StaticAPI: GetMappingVerificationResults</td></tr><tr><td colspan="1">response</td><td colspan="1"><p><span>json-объект, состоящий из параметров запроса:</span></p><ul><li><span><span>taskMetadata.taskId</span></span></li><li><span>taskMetadata.masterRoomId</span></li><li><span>taskMetadata.masterRoomName</span></li><li><span>correctAnswer.answer.mapping</span></li><li><span>correctAnswer.answer.flagCrit</span></li><li><span>taskMetadata.isBookingVerification</span></li></ul><!--THE END--></td></tr></tbody></table>
   
   1. В случае ошибок в формировании события - [EC-1](#id-%F0%9F%93%A8GetMappingVerificationResults%5BHotelsStaticApi%5D-EC-1);
3. Основной сценарий завершается.

## EC-1. Ошибка формирования события

1. Создать запись в логе уровня Error с описанием ошибки с передачей task\_id;
2. Отправить алерт "Ошибка формирования события валидации";
3. Завершить выполнение [основного сценария](#id-%F0%9F%93%A8GetMappingVerificationResults%5BHotelsStaticApi%5D-MC).

# Связанные документы

- [📭 kleks-room-mapping-results \[HotelsStaticApi\]](/pages/viewpage.action?pageId=6423619874)
- [🔬 Валидация бронирований \[HotelsStaticApi\]](/pages/viewpage.action?pageId=6381177903)

# Изменения

| № | Описание изменений | Примечание |
|---|---|---|
| 1 | [THB-12012](https://jira.tcsbank.ru/browse/THB-12012) - Getting issue details... STATUS |  |