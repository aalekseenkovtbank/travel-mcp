# Метод GetHotelsAmenities (/internal\_api/v1/search/hotel\_amenities)

| Назначение | Получение классификации и услуг отеля по идентификатору master-локации |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/hotel\_amenities |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура SearchByLocationApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | integer | REQUIRED | Идентификатор master-локации |

## Структура ответа HotelAmenitiesApiResponseICollectionPayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | :\[] | REQUIRED | Содержимое ответа |

### **Структура HotelAmenitiesApiResponse**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer | REQUIRED | Идентификатор master-отеля |
| hotelAmenities | :\[] | REQUIRED | Массив услуг master-отеля |

### **Структура HotelAmenityApi**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| amenities | string:\[] | REQUIRED | Список удобств |
| groupName | string | REQUIRED | Наименование группы |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки атрибута |
| message | string | OPTIONAL | Текст ошибки атрибута |
| attribute | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Идентификаторы master-отелей не могут быть пустыми. | masterHotelId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Идентификаторы master-отелей не могут быть пустыми.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Идентификатор master-отеля равен нулю. | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Хотя бы один идентификатор master-отеля должен быть не нулевым. | masterHotelId |  | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Хотя бы один идентификатор master-отеля должен быть не нулевым.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Не существует отеля с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetHotelsAmenities

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[TravelDB]..\[HotelStaticApi\_GetHotelsAmenities]
4. Выборка данных из таблицы TravelDB.HotelFacility в которой находятся информация об услугах отеля  
   и выполняется операция объединения данных с таблицей TravelDB.Facility в которой находятся услуги по Facility.FacilityID = HotelFacility.FacilityID  
   и выполняется операция объединения данных с таблицей TravelDB.FacilityCategory с условием, что FacilityCategory.FacilityCategoryID = Facility.FacilityID  
   и выполняется операция объединения данных с таблицей TravelDB.HotelDetails с условием, что HotelDetails.PrimaryLocationID = @LocationId  
   и выполняется сортировка по FacilityCategory.FacilityCategoryID и Facility.FacilityID в порядке возрастания.
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель HotelAmenitiesApiResponseICollectionPayloadApiResponse

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt;masterHotelId | \[TravelDB].\[HotelFacility].HotelId |
| -&gt;hotelAmenities |  |
| -&gt;-&gt;amenities | \[TravelDB].\[Facility].Name |
| -&gt;-&gt;groupName | \[TravelDB].\[FacilityCategory].Name |

# Пример использования

## Запрос

```json
{
  "masterLocationId": 13231
}
```

## Ответ

```json
{
  "payload": [
    {
      "masterHotelId": 1462705,
      "hotelAmenities": [
        {
          "amenities": [
            "Магазины"
          ],
          "groupName": "Общее"
        },
        {
          "amenities": [
            "Парковка"
          ],
          "groupName": "Парковка"
        }
      ]
    },
    {
      "masterHotelId": 1458807,
      "hotelAmenities": [
        {
          "amenities": [
            "Прачечная",
            "Химчистка"
          ],
          "groupName": "Услуги и удобства"
        },
        {
          "amenities": [
            "Парковка"
          ],
          "groupName": "Парковка"
        }
      ]
    },
    {
      "masterHotelId": 1406423,
      "hotelAmenities": [
        {
          "amenities": [
            "Wi-fi в отеле"
          ],
          "groupName": "Интернет"
        },
        {
          "amenities": [
            "Парковка"
          ],
          "groupName": "Парковка"
        }
      ]
    }
  ]
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **[v.](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=2751197635) 1** |  |