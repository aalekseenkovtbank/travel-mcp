# Общая информация

| Назначение | Получение статической информации по локациям для автокомплита |
|---|---|
| Бизнес-процессы | Автокомплит Go |
| Контракт | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Метод | GET |
| URL | /internal\_api/v1/autocomplete/regions |

# Информация

Данный метод в Hotel Static API - прямая замена существующему в Hotel Engine API - \[Deprecated] GET /autocompletestatic/regions

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization | string | mandatory | Ключ авторизации |
| Query/path |  |  |  |
| timestamp | int | optional | Идентификатор версии записи в БД, начиная с которой нужно получить обновленные\\добавленные данные |
| Body |  |  |  |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Body |  |  |  |
| payload | HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionsApiResponse | optional | Объект, содержащий ответ |

### Структура объекта HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionsApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| nextTimestamp | int | optional | Идентификатор версии, с которой начинается следующий batch локаций. Значение должно быть указано при следующих запросах.<br />Если равно null, значит отелей с Version больше, чем искомая не нашлось. |
| regions | HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionInfoDetails | optional | Объект, содержащий информацию о локациях |

### Структура объекта HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionInfoDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| timestamp | int | optional | Идентификатор версии записи в БД |
| name | string | optional | Наименование локации |
| ostrovok\_location\_id | string | optional | Идентификатор локации у поставщика OstrovokNet |
| master\_location\_id | int | optional | Идентификатор master-локации |
| name\_en | string | optional | Наименовании локации на английском языке |
| is\_active | boolean | optional | Признак активности локации.<br />True - локация активна.<br />False - локация деактивирована. |
| parent\_name | string | optional | Наименование региона |
| parent\_name\_en | string | optional | Наименование региона на английском языке |
| type\_code | string | optional | Наименование типа локации<br />Возможные значения: см. |
| country\_name | string | optional | Наименование страны |
| country\_name\_en | string | optional | Наименование страны на английском языке |
| is\_search\_enabled | boolean | optional | Признак, указывающий на возможность поиска по локации.<br />True - поиск по локации разрешен.<br />False - поиск по локации запрещен. |

# Интеграционная схема

```plantuml
[CDATA[@startuml
participant "Hotel Static API" as HSAPI
database TravelDB

-HSAPI: GET-запрос /internal_api/v1/autocomplete/regions
HSAPI -> TravelDB: Вызов хранимой процедуры GetStaticForAutocomplete_Regions
HSAPI <- TravelDB: Результаты выполнения хранимой процедуры
<-HSAPI: Результаты GET-запроса

@enduml]]>
```

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по предоставленному ключу авторизации Authorization.
2. Вызывается хранимая процедура 🗂️ TravelDB.GetStaticForAutocomplete\_Regions \[HotelsStaticApi] со следующими параметрами:
   
   | Параметр | Источник данных |
   |---|---|
   | @TimeStamp | Значение timestamp из запроса |
   | @BatchSize | Значение RegionsBatchSize из конфигурации |
3. По событию получения результатов выполнения хранимой процедуры, происходит маппинг на ответ метода
   
   | Параметр | Источник данных |
   |---|---|
   | payload | - |
   | →nextTimestamp | Максимальное значение из всех TimeStamp<br />null, если из хранимой процедуры вернулась пустая выборка. |
   | →regions | Для каждой найденной локации в хранимой процедуре |
   | →→timestamp | TimeStamp |
   | →→name | NameRu |
   | →→ostrovok\_location\_id | SupplierLocationCode |
   | →→master\_location\_id | LocationID |
   | →→name\_en | NameEn |
   | →→is\_active | true, если IsActive = 1<br />false, если IsActive = 0 |
   | →→parent\_name | RegionNameRu |
   | →→parent\_name\_en | RegionNameEn |
   | →→type\_code | Значение по значению Type |
   | →→country\_name | CountryNameRu |
   | →→country\_name\_en | CountryNameEn |
   | →→is\_search\_enabled | true, если IsRegionSearchEnabled = 1<br />false, если IsRegionSearchEnabled = 0 |
4. Основной сценарий завершается.

## LocationType

| LocationType Id | LocationType Name |
|---|---|
| 1 | continent |
| 2 | country |
| 3 | state\_province |
| 4 | island |
| 5 | city |
| 6 | airport |
| 7 | railway\_station |
| 8 | city\_district |
| 9 | poi |
| 10 | travel\_destination |
| 11 | street |
| 12 | subway |
| 13 | neighborhood |
| 14 | bus\_station |
| 15 | area |

# Конфигурационные параметры

| Параметр | Значение | Описание |
|---|---|---|
| RegionsBatchSize | 1000 | Количество локаций в выборке |

# Метрики и алерты

## Метрики

HTTP-статистика по эндпоинту [отображается на борде Hotel Static API в Grafana - https://sage.tcsbank.ru/grafana/d/kvU-\_SbSk/hotel-static-api?orgId=2144](https://sage.tcsbank.ru/grafana/d/kvU-_SbSk/hotel-static-api?orgId=2144)

## Логи

Логи при ошибках (LEVEL = ERROR) работы метода пишутся в [Sage](https://sage.tcsbank.ru/search?query=group%3D%22hotels_prod%22%20system%3D%22hotels-static-api%22%20level%3D%22ERROR%22)

| Envrionment | Group | System |
|---|---|---|
| Prod | hotels\_prod | hotels-static-api |
| Test | hotels | hotels-static-api |

## Алерты

Алерт отправляется в канал ~nfs-hotels-alerts-prod ([https://time.tbank.ru/tinkoff/channels/nfs-hotels-alerts-prod](https://time.tbank.ru/tinkoff/channels/nfs-hotels-alerts-prod)) не чаще чем раз в 15 минут при превышении лимита в 5 сообщений в SAGE с типом "ERROR" за 5 минут.

### Конфигурация алертов

| Envrionment | Файл с конфигурацией |
|---|---|
| Prod | [https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-prod/hotels-static-api-prod.yaml](https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-prod/hotels-static-api-prod.yaml) |
| QA | [https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa.yaml](https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa.yaml) |
| QA1 | [https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa2.yaml](https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa2.yaml) |
| QA2 | [https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa3.yaml](https://gitlab.tcsbank.ru/hotels-backend/alerts/-/blob/master/triggers/api-qa/hotels-static-api-qa3.yaml) |

# Связанные документы

# Примеры использования

## Запрос

```
{
 "timestamp": 19087387
}
```

## Ответ

```
{
  "payload": {
    "nextTimestamp": 65951948,
    "regions": [
      {
        "timestamp": 65948371,
        "name": "Либерия",
        "ostrovok_location_id": "100",
        "master_location_id": 1500000010,
        "name_en": "Liberia",
        "is_active": true,
        "parent_name": null,
        "parent_name_en": null,
        "type_code": "country",
        "country_name": "Либерия",
        "country_name_en": "Liberia",
        "is_search_enabled": false
      }
    ]
  }
}
```

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Миграция метода для автокомплита по локациям из Hotel Engine API в Hotel Static API |  | THB-9564 |
| 2 | Метрики и алерты для GET /internal\_api/v1/autocomplete/regions | Текущая | THB-9634 |