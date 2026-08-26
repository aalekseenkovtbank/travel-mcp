# Общая информация

| Назначение | Получение статической информации о локациях по списку id |
|---|---|
| Бизнес-процессы | Автокомплит Go |
| Контракт | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Метод | GET |
| URL | /internal\_api/v1/autocomplete/regions/byids |

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization | string | mandatory | Ключ авторизации |
| Query/path |  |  |  |
| locationIds | int\[] | mandatory | Коллекция идентификаторов локаций в БД, для которых нужно получить данные |
| Body |  |  |  |

Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Body |  |  |  |
| payload | HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionsApiResponse | optional | Объект, содержащий ответ |

### Структура объекта HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.RegionsApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| nextTimestamp | int? | optional | В данный момент не используется и всегда null. Контракт унаследован от /internal\_api/v1/autocomplete/regions |
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

-HSAPI: GET-запрос /internal_api/v1/autocomplete/regions/byids
HSAPI -> TravelDB: Вызов хранимой процедуры GetStaticForAutocomplete_RegionsById
HSAPI <- TravelDB: Результаты выполнения хранимой процедуры
<-HSAPI: Результаты GET-запроса

@enduml]]>
```

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по предоставленному ключу авторизации Authorization.
2. Вызывается хранимая процедура 🗂️ TravelDB.GetStaticForAutocomplete\_RegionsById \[HotelsStaticApi] со следующими параметрами:
   
   | Параметр | Источник данных |
   |---|---|
   | @LocationIds | Значение locationIds из запроса в строковом формате |
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

# Связанные документы

# Примеры использования

## Запрос

```
{
 "locationIds": [1500000010]
}
```

## Ответ

```
{
  "payload": {
    "nextTimestamp": null,
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
| 1 | Хранимки обновления данных по отелю\\локации для автокомлита |  | TTP-21204 |
| 2 | Api метод для автокомплита для обновлению инфы по отелю/региону | Текущая | TTP-20557 |