# Общая информация

| Назначение | Получение статической информации по отелям для автокомплита |
|---|---|
| Бизнес-процессы | Автокомплит Go |
| Контракт | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Метод | GET |
| URL | /internal\_api/v1/autocomplete/hotels |

# Информация

Данный метод в Hotel Static API - прямая замена существующему в Hotel Engine API - \[Deprecated] GET /autocompletestatic/hotels 

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization | string | mandatory | Ключ авторизации |
| Query/path |  |  |  |
| timestamp | int | optional | Идентификатор версии записи в БД, начиная с которой нужно получить обновленные\\добавленные данные |
| supplierIds | int\[] | optional | Массив идентификаторов поставщиков в БД. Используется для сужения получаемых данных и возврата отелей только имеющих привязку к определенному поставщику |
| Body |  |  |  |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Body |  |  |  |
| payload | HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.HotelsApiResponse | optional | Объект, содержащий ответ |

### Структура объекта HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.HotelsApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| nextTimestamp | int | optional | Идентификатор версии, с которой начинается следующий batch отелей. Значение должно быть указано при следующих запросах.<br />Если равно null, значит отелей с Version больше, чем искомая не нашлось. |
| hotels | HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.HotelInfoDetails | optional | Объект, содержащий информацию об отелях |

### Структура объекта HotelsStaticApi.Web.Models.InternalApi.Hotels.Autocomplete.HotelInfoDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| timestamp | int | optional | Идентификатор версии записи в БД |
| master\_hotel\_id | int | optional | Идентификатор master-отеля |
| name | string | optional | Наименование отеля |
| name\_en | string | optional | Наименование отеля на английском языке |
| is\_active | boolean | optional | Признак активности отеля.<br />true - отель активен.<br />false - отель деактивирован. |
| hotel\_category | string | optional | Категория отеля.<br />Возможные значения: см. |
| hotel\_code | string | optional | Всегда "hotel" |
| hotel\_address | string | optional | Адрес отеля |
| hotel\_address\_en | string | optional | Адрес отеля на английском языке |
| region\_name | string | optional | Наименование региона отеля |
| region\_name\_en | string | optional | Наименование региона отеля на английском языке |
| country\_name | string | optional | Наименование страны отеля |
| country\_name\_en | string | optional | Наименование страны отеля на английском языке |
| city\_name | string | optional | Наименование локации отеля |
| city\_name\_en | string | optional | Наименование локации отеля на английском языке |
| certification\_needed | boolean | optional | Признак необходимости сертификации отеля<br />true - сертификация нужна.<br />false - сертификация не нужна. |
| has\_certification | boolean | optional | Признак сертификации отеля в Росаккредитации<br />true - есть данные о сертификации отеля.<br />false - нет данных о сертификации отеля. |
| supplierIds | int\[] | optional | Коллекция идентификаторов поставщиков у master-отеля |

# Интеграционная схема

```plantuml
[CDATA[@startuml
participant "Hotel Static API" as HSAPI
database TravelDB

-HSAPI: GET-запрос /internal_api/v1/autocomplete/hotels
HSAPI -> TravelDB: Вызов хранимой процедуры GetStaticForAutocomplete_Hotels
HSAPI <- TravelDB: Результаты выполнения хранимой процедуры
<-HSAPI: Результаты GET-запроса

@enduml]]>
```

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по предоставленному ключу авторизации Authorization.
2. Вызывается хранимая процедура 🗂️ TravelDB.GetStaticForAutocomplete\_Hotels \[HotelsStaticApi] со следующими параметрами
   
   | Параметр | Источник данных |
   |---|---|
   | @TimeStamp | Значение timestamp из запроса |
   | @BatchSize | Значение HotelsBatchSize из конфигурации |
   | @Supplier | Значение supplierIds из запроса преобразованное в строку с запятой как разделитель |
3. По событию получения результатов выполнения хранимой процедуры, происходит маппинг на ответ метода
   
   | Параметр | Источник данных |
   |---|---|
   | payload | - |
   | →nextTimestamp | Максимальное значение из всех TimeStamp<br />null, если из хранимой процедуры вернулась пустая выборка. |
   | →hotels | Для каждого найденного отеля в хранимой процедуре |
   | →→timestamp | TimeStamp |
   | →→master\_hotel\_id | HotelID |
   | →→name | NameRu |
   | →→name\_en | NameEn |
   | →→is\_active | true, если IsActive = 1<br />false, если IsActive = 0 |
   | →→hotel\_category | Маппинг идентификатора категории HotelCategory на enum.<br />См. |
   | →→hotel\_code | Всегда "hotel" |
   | →→hotel\_address | HotelAddressRu |
   | →→hotel\_address\_en | HotelAddressEn |
   | →→region\_name | RegionNameRu |
   | →→region\_name\_en | RegionNameEn |
   | →→country\_name | CountryNameRu |
   | →→country\_name\_en | CountryNameEn |
   | →→city\_name | CityNameRu |
   | →→city\_name\_en | CityNameEn |
   | →→certification\_needed | CertificationNeeded |
   | →→has\_certification | HasCertification |
   | →→supplierIds | Коллекция из всех SupplierID для текущего master\_hotel\_id |
4. Основной сценарий завершается.

## HotelCategory

| HotelCategory Id | HotelCategory Name |
|---|---|
| 1 | hotel |
| 2 | apartment\_hotel |
| 3 | apartment\_condominium |
| 4 | hostel |
| 5 | motel |
| 6 | bed\_and\_breakfast |
| 7 | boatel |
| 8 | bungalow |
| 9 | campsite |
| 10 | castle\_chateaux\_fortress |
| 11 | cottage |
| 12 | farmhouse |
| 13 | guesthouse |
| 14 | house |
| 15 | huts |
| 16 | inn |
| 17 | lodge |
| 18 | pension |
| 19 | pousada |
| 20 | resort |
| 21 | serviced\_apartments |
| 22 | tented\_camp |
| 23 | timeshare |
| 24 | townhouse |
| 25 | villa |
| 26 | mini\_hotel |
| 27 | holiday\_home |
| 28 | country\_house |
| 29 | holiday\_park |
| 30 | chalet |
| 31 | family\_stay |
| 32 | economy\_hotels |
| 33 | riad |
| 34 | ryokan |
| 35 | luxury\_tent |
| 36 | love\_hotel |
| 37 | capsule\_hotel |
| 38 | guest\_accommodation |
| 39 | residences |
| 40 | sanatorium |
| 41 | boarding\_house |
| 42 | boutique\_and\_design |
| 43 | camping |
| 44 | glamping |

# Конфигурационные параметры

| Параметр | Значение | Описание |
|---|---|---|
| HotelsBatchSize | 1000 | Количество отелей в выборке |

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

Конфигурация алертов

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
 "timestamp": 22069435
}
```

## Ответ

```
{
  "payload": {
    "nextTimestamp": 53616946,
    "hotels": [
      {
        "timestamp": 40503472,
        "master_hotel_id": 20,
        "name": "Гостевой дом Ангелина",
        "name_en": "Гостевой дом Ангелина",
        "is_active": true,
        "hotel_category": "hotel",
        "hotel_code": "hotel",
        "hotel_address": "ул. Лазурная, 6, Сочи",
        "hotel_address_en": "ул. Лазурная, 6, Сочи",
        "region_name": "Краснодарский край",
        "region_name_en": "Krasnodar Krai",
        "country_name": "Россия",
        "country_name_en": "Russia",
        "city_name": "Сочи",
        "city_name_en": "Sochi",
        "certification_needed": true,
        "has_certification": true,
        "supplierIds": [36, 39]
      }
    ]
  }
}
```

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Миграция метода для отельного автокомплита из Hotel Engine API в Hotel Static API |  | THB-9559 |
| 2 | Метрики и алерты для GET /internal\_api/v1/autocomplete/hotels |  | THB-9635 |
| 3 | Расширить контракт для автокомплита информацией о сертификации |  | TTP-20528 |
| 4 | Расширить входящий запрос опциональным массивом supplierIds | Текущая | TTP-22654TTP-22475 |