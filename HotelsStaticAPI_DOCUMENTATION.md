# Документация HotelsStaticAPI

Сводная документация по всем API методам HotelsStaticAPI.

## Оглавление

1. [Autocomplete API](#autocomplete-api)
2. [Отели API](#отели-api)
3. [Поиск API](#поиск-api)
4. [Комнаты API](#комнаты-api)
5. [POI API](#poi-api)
6. [SummaryReview API](#summaryreview-api)
7. [Images API](#images-api)
8. [Справочники API](#справочники-api)
9. [Deprecated API](#deprecated-api)

---

## Autocomplete API

### GET /internal_api/v1/autocomplete/hotels

**Назначение:** Получение статической информации по отелям для автокомплита

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/autocomplete/hotels` |
| Бизнес-процессы | Автокомплит Go |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory) — ключ авторизации

**Query Parameters:**
- `timestamp` (int, optional) — идентификатор версии записи в БД
- `supplierIds` (int[], optional) — массив идентификаторов поставщиков

#### Ответ

```json
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

**Поля ответа:**
- `nextTimestamp` — версия для следующего batch-запроса (null если больше нет данных)
- `hotels` — массив отелей с полной информацией

---

### GET /internal_api/v1/autocomplete/hotels/byids

**Назначение:** Получение статической информации об отелях по списку ID

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/autocomplete/hotels/byids` |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

**Query Parameters:**
- `hotelIds` (int[], mandatory) — коллекция идентификаторов отелей

#### Ответ

```json
{
  "payload": {
    "nextTimestamp": null,
    "hotels": [
      {
        "timestamp": 40503472,
        "master_hotel_id": 20,
        "name": "Гостевой дом Ангелина",
        "is_active": true,
        "hotel_category": "hotel",
        "city_name": "Сочи",
        "certification_needed": true,
        "has_certification": true,
        "supplierIds": [36, 39]
      }
    ]
  }
}
```

---

### GET /internal_api/v1/autocomplete/regions

**Назначение:** Получение статической информации по локациям для автокомплита

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/autocomplete/regions` |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

**Query Parameters:**
- `timestamp` (int, optional) — идентификатор версии записи в БД

#### Ответ

```json
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
        "type_code": "country",
        "country_name": "Либерия",
        "country_name_en": "Liberia",
        "is_search_enabled": false
      }
    ]
  }
}
```

**LocationType значения:**
- `continent`, `country`, `state_province`, `island`, `city`, `airport`, `railway_station`, `city_district`, `poi`, `travel_destination`, `street`, `subway`, `neighborhood`, `bus_station`, `area`

---

### GET /internal_api/v1/autocomplete/regions/byids

**Назначение:** Получение статической информации о локациях по списку ID

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/autocomplete/regions/byids` |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

**Query Parameters:**
- `locationIds` (int[], mandatory) — коллекция идентификаторов локаций

#### Ответ

```json
{
  "payload": {
    "nextTimestamp": null,
    "regions": [
      {
        "timestamp": 65948371,
        "name": "Либерия",
        "master_location_id": 1500000010,
        "type_code": "country",
        "country_name": "Либерия",
        "is_search_enabled": false
      }
    ]
  }
}
```

---

## Отели API

### POST /internal_api/v1/hotels/rates-hotelinfo

**Назначение:** Получение информации о master-отеле по идентификатору отеля

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotels/rates-hotelinfo` |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

**Body:**
```json
{
  "masterHotelId": 1426291
}
```

#### Ответ

```json
{
  "payload": {
    "masterHotelId": 1426291,
    "ianaTimeZone": "Europe/Moscow",
    "roomGroups": [
      {
        "name": "Двухместный номер Standard двуспальная кровать",
        "nameEn": "Standard Double room with double bed",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 3,
          "family": 0,
          "bedding": 3,
          "quality": 2,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": ["soundproofing", "private-bathroom", "telephone", "air-conditioning"],
        "images": ["https://cdn.worldota.net/t/{size}/extranet/..."]
      }
    ]
  }
}
```

**RoomType словарь:** Standard, Deluxe, Executive, Luxury, Premium, Suite, Studio, Apartment, Villa, Bungalow и др. (44 типа)

**BedType словарь:** None, Single, Double, Queen, King, Bunk

---

### POST /internal_api/v1/hotels/lifestyle-hotelinfo

**Назначение:** Получение информации о master-отеле для платформы LifeStyle

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotels/lifestyle-hotelinfo` |

#### Запрос

```json
{
  "masterHotelId": 1426291
}
```

#### Ответ

```json
{
  "payload": {
    "masterHotelId": 1426291,
    "name": "Отель Измайлово Альфа",
    "location": {
      "masterLocationId": 47307,
      "name": "Москва",
      "type": "City",
      "countryCode": "RU"
    },
    "ianaTimeZone": "Europe/Moscow",
    "image": "https://cdn.worldota.net/t/{size}/extranet/...",
    "checkInTime": "14:00",
    "checkOutTime": "12:00"
  }
}
```

---

### POST /internal_api/v1/hotels/hotel-name

**Назначение:** Получение названия отеля по идентификатору master-отеля

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotels/hotel-name` |

#### Запрос

```json
{
  "masterHotelId": 1426291
}
```

#### Ответ

```json
{
  "payload": {
    "hotelName": "Отель Измайлово Альфа"
  }
}
```

---

### POST /internal_api/v1/hotels/hotel-supplier-mapping

**Назначение:** Получение маппинга по идентификатору master-отеля или получение master-отеля по коду поставщика

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotels/hotel-supplier-mapping` |

#### Запрос

**Вариант 1 — по masterHotelId:**
```json
{
  "masterHotelId": 1426291
}
```

**Вариант 2 — по коду поставщика:**
```json
{
  "supplierHotelCode": "izmailovo_alpha_hotel",
  "supplierId": 36
}
```

#### Ответ

```json
{
  "payload": [
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 11,
      "hotelCode": "test_93931821"
    },
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 36,
      "hotelCode": "izmailovo_alpha_hotel"
    }
  ]
}
```

---

### GET /internal_api/v1/hotels/rost-promo-hotels

**Назначение:** Получение идентификаторов Master-отелей, участвующих в программе РОСТ через Extranet

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/hotels/rost-promo-hotels` |
| Бизнес-процесс | Отели - Direct - Программа Рост для отелей |

#### Запрос

```
GET /internal_api/v1/hotels/rost-promo-hotels
```

#### Ответ

```json
{
  "payload": {
    "hotels": [101, 205]
  }
}
```

---

### POST /internal_api/v3/hotels/hotelinfolist

**Назначение:** Получение полной статической информации об отеле по набору идентификаторов master-отелей

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v3/hotels/hotelinfolist` |

#### Запрос

```json
{
  "masterHotelIds": [1426291, 1406924]
}
```

#### Ответ

```json
{
  "payload": [
    {
      "masterHotelId": 1426291,
      "isClosed": false,
      "deleted": false,
      "name": "Отель Измайлово Альфа",
      "nameEn": "Izmailovo Alpha Hotel",
      "hotelChain": "",
      "starRating": 4,
      "images": [...],
      "address": "Измайловское шоссе, д.71 А, Москва",
      "masterLocationId": 47307,
      "kind": "Hotel",
      "coordinates": {
        "latitude": 55.7898292542,
        "longitude": 37.7495040894
      },
      "ianaTimeZone": "Europe/Moscow",
      "checkInTime": "14:00",
      "checkOutTime": "12:00",
      "phone": "+7 (495) 123-45-67",
      "email": "info@hotel.ru",
      "description": [...],
      "facilities": [...],
      "metapolicy": {...},
      "paymentMethods": ["cash", "card"],
      "location": {...},
      "policy": [...],
      "certification": {...},
      "certificationNeeded": true,
      "cityName": "Москва",
      "countryName": "Россия",
      "apartmentFacts": {...}
    }
  ]
}
```

**Поля ответа включают:**
- Основную информацию об отеле
- Фотографии с категориями
- Описание
- Удобства (facilities)
- Политики (metapolicy: children, meal, pets, visa, parking, shuttle, internet, extraBed и др.)
- Сертификацию (для российских отелей)
- Данные для квартир (apartmentFacts)

---

## Поиск API

### POST /internal_api/v1/search/hotels

**Назначение:** Получение информации о master-отелях для SearchAPI (избранное)

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/search/hotels` |

#### Запрос

```json
{
  "masterHotelIds": [1426291, 1406924]
}
```

#### Ответ

```json
{
  "payload": [
    {
      "masterHotelId": 1406924,
      "name": "Отель Измайлово Бета",
      "nameEn": "Izmailovo Beta Hotel",
      "hotelChain": "",
      "hasImage": true,
      "starRating": 3,
      "address": "Измайловское шоссе, д.71, стр. 2Б, Москва",
      "masterLocationId": 47307,
      "ianaTimeZone": "Europe/Moscow",
      "location": {
        "masterLocationId": 47307,
        "name": "Москва",
        "type": "City",
        "countryCode": "RU",
        "countryName": "Россия"
      },
      "review": {
        "rating": 8.4,
        "count": 1395
      },
      "coordinates": {
        "latitude": 55.7895278931,
        "longitude": 37.7474975586
      },
      "kind": "Hotel",
      "apartmentFacts": {...}
    }
  ]
}
```

**HotelCategory маппинг:**
- 0: Resort
- 1: Sanatorium
- 2: Guesthouse
- 3: MiniHotel
- 4: Castle
- 5: Hotel
- 6: BoutiqueAndDesign
- 7: Apartment
- 8: CottagesAndHouses
- 9: Farm
- 10: VillasAndBungalows
- 11: Camping
- 12: Hostel
- 13: Bnb
- 14: ApartHotel
- 15: Glamping

---

### POST /internal_api/v1/search/hotel_amenities

**Назначение:** Получение удобств отелей

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/search/hotel_amenities` |

---

### POST /internal_api/v1/search/images

**Назначение:** Получение URL изображений

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/search/images` |

---

### POST /internal_api/v1/search/location_migration_info

**Назначение:** Получение информации о миграции локаций

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/search/location_migration_info` |

---

## Комнаты API

### GET /v1/hotels/{hotelId}/rooms

**Назначение:** Получение описания комнат по идентификатору отеля

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/v1/hotels/{hotelId}/rooms` |
| Бизнес-процессы | Карточка отеля и тарифы |

#### Запрос

**Headers:**
- `Authorization` (mandatory)

**Path:**
- `hotelId` (int32, mandatory)

#### Ответ

```json
{
  "payload": {
    "ianaTimeZone": "Europe/Moscow",
    "hotelRooms": [
      {
        "roomId": 12345,
        "name": "Двухместный номер Standard",
        "nameTranslations": [
          {"language": "en", "value": "Standard Double Room"}
        ],
        "description": "Уютный номер с двуспальной кроватью",
        "size": 24.5,
        "facilities": [1, 5, 10, 15],
        "images": ["https://...", "https://..."],
        "bedConfigurations": [
          {
            "bedTypes": [
              {"bedTypeId": 3, "isExtraBed": false},
              {"bedTypeId": 9, "isExtraBed": true}
            ]
          }
        ]
      }
    ]
  }
}
```

---

## POI API

### POST /internal_api/v1/points_of_interest/search

**Назначение:** Получение информации о расстоянии от отеля до ключевых точек интереса

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/points_of_interest/search` |
| Бизнес-процессы | 1-пейджер | Отели | Места рядом с отелем |

#### Запрос

```json
{
  "masterHotelIds": [1426291, 1298765]
}
```

#### Ответ

```json
{
  "payload": [
    {
      "hotelId": 1426291,
      "keyPoints": [
        {
          "name": "Химки",
          "type": "center",
          "distanceDirect": 490
        },
        {
          "name": null,
          "type": "skilift",
          "distanceDirect": 780
        }
      ]
    },
    {
      "hotelId": 1298765,
      "keyPoints": [
        {
          "name": "Сириус",
          "type": "center",
          "distanceDirect": 490
        }
      ]
    }
  ]
}
```

**Типы точек интереса:**
- `center` — центр города/курорта
- `beach` — пляж
- `skilift` — горнолыжный подъемник

---

### GET /internal_api/v1/points_of_interest/landmarks

**Назначение:** Получение достопримечательностей рядом с отелем

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/points_of_interest/landmarks` |

---

### GET /internal_api/v1/points_of_interest/groups

**Назначение:** Получение групп точек интереса по ID отеля

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/points_of_interest/groups` |

---

### GET /internal_api/v1/points_of_interest/types

**Назначение:** Получение типов точек интереса рядом с отелем

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/points_of_interest/types` |

---

## SummaryReview API

### GET /internal_api/v1/reviews/{masterHotelId}/summary

**Назначение:** Получение summary отзывов отеля

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/reviews/{masterHotelId}/summary` |
| Бизнес-процессы | Отзывы и рейтинг объекта размещения |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

**Path:**
- `masterHotelId` (int32, required)

#### Ответ

```json
{
  "payload": {
    "summary": "Отличный отель с прекрасным расположением и дружелюбным персоналом..."
  }
}
```

**Коды ошибок:**
- `400` — не передан masterHotelId
- `401` — неавторизованный запрос
- `204` — саммари не найдено
- `500` — ошибка сервера

---

### DELETE /internal_api/v1/reviews/{masterHotelId}/summary

**Назначение:** Удаление summary отзывов отеля

| Параметр | Значение |
|---|---|
| Метод | DELETE |
| URL | `/internal_api/v1/reviews/{masterHotelId}/summary` |

---

## Images API

### POST /internal_api/v1/hotel-image/get-dynamic-room-images

**Назначение:** Получение мастер-изображений по коллекциям ссылок поставщиков

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotel-image/get-dynamic-room-images` |

#### Запрос

```json
{
  "supplier_images": [
    {
      "supplier_id": 39,
      "image_url": "https://..."
    }
  ]
}
```

#### Ответ

```json
{
  "images": [
    {
      "supplier_id": 39,
      "supplier_image_url": "https://...",
      "public_image_url": "https://..."
    }
  ]
}
```

**Алгоритм:**
1. Вычисляется хэш изображения поставщика
2. По хэшу и supplier_id ищется соответствие в таблице `dynamic_room_images`
3. Возвращается public_image_url или null если не найдено

---

### POST /internal_api/v1/images/add-resize-task

**Назначение:** Добавление задачи на ресайз изображения

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/images/add-resize-task` |

---

## Справочники API

### GET /internal_api/v1/dictionaries/bedTypes

**Назначение:** Получение справочника кроватей

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/dictionaries/bedTypes` |

#### Ответ

```json
[
  {
    "masterId": 0,
    "nameRu": "разные типы кроватей",
    "nameEn": "different types of beds"
  },
  {
    "masterId": 1,
    "nameRu": "двуспальная",
    "nameEn": "double"
  },
  {
    "masterId": 3,
    "nameRu": "двуспальная",
    "nameEn": "double"
  },
  {
    "masterId": 4,
    "nameRu": "Queen",
    "nameEn": "queen"
  },
  {
    "masterId": 5,
    "nameRu": "King",
    "nameEn": "king"
  },
  {
    "masterId": 6,
    "nameRu": "одноместный диван",
    "nameEn": "sofa"
  },
  {
    "masterId": 9,
    "nameRu": "односпальная",
    "nameEn": "single"
  },
  {
    "masterId": 10,
    "nameRu": "двухъярусная",
    "nameEn": "bunk"
  }
]
```

---

### GET /internal_api/v1/dictionaries/facilities

**Назначение:** Получение справочника удобств

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/dictionaries/facilities` |

#### Запрос

**Query Parameters:**
- `facilityTypeId` (int, optional) — тип удобства:
  - `1` — Удобства отеля
  - `2` — Удобства номера

#### Ответ

```json
[
  {
    "facilityId": 1,
    "name": "Wi-Fi"
  },
  {
    "facilityId": 2,
    "name": "Кондиционер"
  }
]
```

---

### GET /internal_api/v1/dictionaries/mealTypes

**Назначение:** Получение справочника типов питания

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/dictionaries/mealTypes` |

#### Ответ

```json
[
  {
    "id": 1,
    "name": "Без питания",
    "code": "RO"
  },
  {
    "id": 2,
    "name": "Завтрак",
    "code": "BB"
  },
  {
    "id": 3,
    "name": "Полупансион",
    "code": "HB"
  },
  {
    "id": 4,
    "name": "Полный пансион",
    "code": "FB"
  },
  {
    "id": 5,
    "name": "Всё включено",
    "code": "AI"
  }
]
```

---

## Локации API

### GET /internal_api/v1/search/location-tree

**Назначение:** Получение дерева локаций

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/search/location-tree` |

#### Запрос

**Headers:**
- `HotelsStaticApi.Authorization` (mandatory)

#### Ответ

Дерево локаций с иерархией: континент → страна → регион → город → район

---

## Маппинг комнат API

### POST /internal_api/v1/room-mapping/get

**Назначение:** Получение маппинга названий комнат

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/room-mapping/get` |

---

### POST /internal_api/v1/room-mapping/verify

**Назначение:** Проверка результатов маппинга комнат

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/room-mapping/verify` |

---

### DELETE /internal_api/v1/room-mapping/deactivate

**Назначение:** Деактивация маппинга названий комнат

| Параметр | Значение |
|---|---|
| Метод | DELETE |
| URL | `/internal_api/v1/room-mapping/deactivate` |

---

## Маппинг отелей API

### POST /internal_api/v1/hotel-mapping/deduplicate

**Назначение:** Дедупликация отелей

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotel-mapping/deduplicate` |

---

### POST /internal_api/v1/hotel-mapping/save

**Назначение:** Сохранение результатов проверки маппинга отелей

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/hotel-mapping/save` |

---

## Обновления контента API

### GET /internal_api/v1/content/hotels

**Назначение:** Получение обновлений данных об отелях

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/content/hotels` |

---

### GET /internal_api/v1/content/invalidate-status

**Назначение:** Получение статуса процесса инвалидации

| Параметр | Значение |
|---|---|
| Метод | GET |
| URL | `/internal_api/v1/content/invalidate-status` |

---

### POST /internal_api/v1/content/invalidate

**Назначение:** Инвалидация кэша статических данных

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/content/invalidate` |

---

### POST /internal_api/v1/content/clean-invalidation-results

**Назначение:** Очистка результатов инвалидации

| Параметр | Значение |
|---|---|
| Метод | POST |
| URL | `/internal_api/v1/content/clean-invalidation-results` |

---

### Kafka-topics для обновлений

**Топики:**
- `UpdateCacheStaticData` — общие обновления кэша
- `UpdateHotelCoordinatesStaticData` — обновления координат отелей
- `UpdateSuppliersSearchAPICacheStaticData` — обновления кэша SearchAPI

---

## Deprecated API

Следующие методы устарели и не рекомендуются к использованию:

### Удаленные методы:

1. **GET /internal_api/v1/hotels/hotel** (GetHotelByMasterId) — удален
2. **GetHotelInfoForWallet** — удален
3. **GetRoomsAmenities** — удален
4. **GetHotelInfoForBookingNotificationCenter** — удален
5. **GetHotelWithRoomGroupImages / GetHotelInfo** — удален
6. **HotelScoreSync** — удален
7. **Review** — удален

**Причина удаления:** Миграция на новые версии API и оптимизация архитектуры.

---

## Общие ошибки

### Структура ошибки

```json
{
  "error": {
    "code": "incorrectValue",
    "message": "Ошибка при валидации запроса.",
    "details": {
      "code": "noMasterHotelId",
      "message": "Идентификатор master-отеля обязателен.",
      "attribute": "masterHotelId"
    }
  }
}
```

### Коды ошибок

| HTTP код | Сценарий |
|---|---|
| 400 | Ошибка валидации запроса |
| 401 | Неавторизованный запрос |
| 204 | Ресурс не найден |
| 500 | Ошибка сервера |

---

## Авторизация

Все методы требуют наличия заголовка авторизации:

```
HotelsStaticApi.Authorization: <api-key>
```

Ключ авторизации выдается администратором API.

---

## Swagger

Документация API доступна по адресу:
- **QA:** https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html

---

## Метрики и алерты

- **Grafana:** https://sage.tcsbank.ru/grafana/d/kvU-_SbSk/hotel-static-api
- **Sage логи:** group=hotels_prod, system=hotels-static-api
- **Алерты:** канал ~nfs-hotels-alerts-prod

---

## История изменений

Документация обновляется по мере изменения API. Актуальная версия доступна в Confluence.
