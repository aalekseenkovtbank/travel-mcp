# Метод GetRoomsAmenities (/internal\_api/v1/search/room\_amenities)

| Назначение | Получение классификации и услуг комнат по идентификатору master-локации |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/room\_amenities |
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

## Структура ответа RoomAmenitiesApiResponseICollectionPayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | :\[] | REQUIRED | Содержимое ответа |

### **Структура RoomAmenitiesApiResponse**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | Идентификатор master-отеля |
| hotelRoomAmenities | :\[] | REQUIRED | Массив комнат |

### **Структура RoomGroupApi**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| rgExt | [RgExt](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=2587856642) | REQUIRED | Структура rgExt |
| roomAmenities | string:\[] | OPTIONAL | Услуги в номере |

### Словарь типов номеров в Extranet

| RoomType | RoomTypeId |
|---|---|
| RunOfHouse | 0 |
| Deluxe | 1 |
| Executive | 2 |
| Luxury | 3 |
| Premium | 4 |
| Standard | 5 |
| Studio | 6 |
| Suite | 7 |
| JuniorSuite | 8 |
| Apartment | 9 |
| DeluxeSuite | 10 |
| ExecutiveSuite | 11 |
| Bungalow | 12 |
| Villa | 13 |
| Penthouse | 14 |
| DeluxeStudio | 15 |
| SharedRoom | 16 |
| Tent | 17 |
| StudioSuite | 18 |
| ParlorSuite | 19 |
| FamilyRoom | 20 |
| Superior | 21 |
| SuperiorSuite | 22 |
| SuperiorStudio | 23 |
| PresidentialSuite | 24 |
| Chalet | 26 |
| DeluxeFamily | 27 |
| DeluxeVilla | 28 |
| FamilySuite | 29 |
| LuxurySuite | 30 |
| LuxuryVilla | 31 |
| SuperiorVilla | 32 |
| Cabin | 33 |
| DeluxeBungalow | 34 |
| DeluxeExecutive | 35 |
| Lodge | 36 |
| EconomyBudget | 37 |
| SuperiorBungalow | 38 |
| RoyalSuite | 39 |
| LuxuryStudio | 40 |
| GrandRoom | 41 |
| GrandSuite | 42 |
| GrandDeluxe | 43 |
| Duplex | 44 |
| Comfort | 45 |
| Capsule | 46 |
| Cottage | 47 |
| Camping | 48 |

### Словарь типов кроватей в Extranet

| BedType | BedTypeId |
|---|---|
| None | 0 |
| Single | 1 |
| Double | 3 |
| Queen | 4 |
| King | 5 |
| Bunk | 6 |

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
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterLocationId | Идентификатор master-локации должен быть заполнен. | masterLocationId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "noMasterLocationId",
			"message": "Идентификатор master-локации должен быть заполнен.",
			"attribute": "masterLocationId"
		}
	}
}<br />``` |
| Не существует отеля с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetRoomsAmenities

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура HotelStaticApi\_GetRoomsAmenities в TravelDB.
4. Выборка данных из таблицы TravelDB.RoomContent в которой находятся информация о комнатах отеля  
   и выполняется операция объединения данных с таблицей TravelDB.RoomAmenity в которой находятся услуги на уровне комнаты по RoomContent.RoomContentId = RoomAmenity.RoomContentId  
   и выполняется операция объединения данных с таблицей TravelDB.HotelDetails с условием, что TravelDB.HotelDetails.PrimaryLocationID = @LocationId  
   и выполняется сортировка по TravelDB.RoomContent.RoomContentId (по возрастанию)
5. В зависимости от TravelDB.RoomContent.SupplierId:  
   Для Ostrovok (id=35) заполняется rgExt по TravelDB.RoomContent.SupplierRoomCode;  
   Для Tinkoff Extranet (id=11) заполняется rgExt после выполнения процедуры в базе HotelInventory - HotelStaticApi\_GetRoomsInfo в которую передается в качестве параметра TravelDB.RoomContent.SupplierRoomCode для каждой комнаты этого поставщика.
6. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель RoomAmenitiesApiResponseICollectionPayloadApiResponse

# Маппинг данных на модель Hotel Static API

<table><thead><tr><th><p>Параметр</p></th><th><p>Источник данных</p></th></tr></thead><colgroup><col/><col/></colgroup><tbody><tr><td colspan="1"><span>payload</span></td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;masterHotelId</td><td colspan="1"> [TravelDB].[RoomContent].HotelId</td></tr><tr><td colspan="1">-&gt;hotelRoomAmenities</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;rgExt</td><td colspan="1"><br/></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Sex</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 15 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): <br/>В зависимости от [HotelInvenotry].[Room].Gender для выбранной комнаты.</p><table><tbody><tr><th> [HotelInvenotry].[Room].Gender</th><th>Sex</th></tr><tr><td>0</td><td>3</td></tr><tr><td>1</td><td>2</td></tr><tr><td>2</td><td>1</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Club</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 21 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Class</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 0 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): в зависимости от по значению [HotelInvenotry].[Room].RoomTypeId</p><table><tbody><tr><th>Тип номера</th><th>Class</th></tr><tr><td>Standard</td><td>3</td></tr><tr><td>EconomyBudget</td><td>3</td></tr><tr><td colspan="1">Superior</td><td colspan="1">3</td></tr><tr><td colspan="1">Deluxe</td><td colspan="1">3</td></tr><tr><td colspan="1">Suite</td><td colspan="1">3</td></tr><tr><td colspan="1">FamilyRoom</td><td colspan="1">3</td></tr><tr><td colspan="1">Executive</td><td colspan="1">3</td></tr><tr><td colspan="1">PresidentialSuite</td><td colspan="1">3</td></tr><tr><td colspan="1">Studio</td><td colspan="1">3</td></tr><tr><td colspan="1">SharedRoom</td><td colspan="1">1</td></tr><tr><td colspan="1">Apartment</td><td colspan="1">6</td></tr><tr><td colspan="1">Cabin</td><td colspan="1">9</td></tr><tr><td colspan="1">Lodge</td><td colspan="1">17</td></tr><tr><td colspan="1">Villa</td><td colspan="1">8</td></tr><tr><td colspan="1">Chalet</td><td colspan="1">18</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Family</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 18 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): &#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;13&#34; (для выбранной комнаты), &#34;0&#34;, если нет.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Bedding</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 6 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet):<br/>Если количество уникальных вариантов ([HotelInventory].[BedConfiguration].BedType для выбранной комнаты) не равно 1:</p><table><tbody><tr><th>Условие</th><th>Bedding</th></tr><tr><td>Количество уникальных [HotelInventory].[BedConfiguration].BedType = 0</td><td>0</td></tr><tr><td>Количество уникальных [HotelInventory].[BedConfiguration].BedType &gt; 1</td><td>7</td></tr></tbody></table><p>Если количество уникальных вариантов типов кроватей ([HotelInventory].[BedConfiguration].BedType для выбранной комнаты) равно 1:</p><table><tbody><tr><th>BedType</th><th>Bedding</th></tr><tr><td>Single</td><td>4</td></tr><tr><td><ul><li>Double</li><li>Queen</li><li>King</li></ul></td><td>3</td></tr><tr><td>Bunk</td><td>1</td></tr><tr><td colspan="1">None</td><td colspan="1">0</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Quality</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 3 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): в зависимости от по значению [HotelInvenotry].[Room].RoomTypeId</p><table><tbody><tr><th>Тип номера</th><th>Quality</th></tr><tr><td>Standard</td><td>2</td></tr><tr><td colspan="1">EconomyBudget</td><td colspan="1">1</td></tr><tr><td colspan="1">Superior</td><td colspan="1">3</td></tr><tr><td colspan="1">Deluxe</td><td colspan="1">4</td></tr><tr><td colspan="1">Suite</td><td colspan="1">5</td></tr><tr><td colspan="1">FamilyRoom</td><td colspan="1">6</td></tr><tr><td colspan="1">Executive</td><td colspan="1">8</td></tr><tr><td colspan="1">PresidentialSuite</td><td colspan="1">9</td></tr><tr><td colspan="1">Studio</td><td colspan="1">20</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Bathroom</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 9 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet):<br/>&#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;410&#34; (для выбранной комнаты);<br/>&#34;2&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;18&#34; или &#34;19&#34; (для выбранной комнаты);<br/>&#34;3&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;415&#34; (для выбранной комнаты);<br/>&#34;0&#34; для всех остальных случаев.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Capacity</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 12 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): Значение [HotelInventory].[RoomAmenity].MaxPersons если оно меньше 6, иначе &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Balcony</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 27 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): &#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;399&#34; (для выбранной комнаты), &#34;0&#34;, если нет.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Bedrooms</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 24 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;View</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 30 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1"><span>-&gt;-&gt;-&gt;Floor</span></td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 33 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1">-&gt;-&gt;roomAmenities</td><td colspan="1">Список [TravelDB].[RoomAmenity].AmenityName для каждого из доступных [TravelDB].[RoomContent].RoomContentId для выбранного master-отеля с HotelId</td></tr></tbody></table>

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
      "hotelId": 1458807,
      "hotelRoomAmenities": [
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 1,
            "family": 0,
            "bedding": 0,
            "quality": 0,
            "bathroom": 1,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "shared-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 1,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "shared-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 3,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 1,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 1,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "shared-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 3,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 4,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
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
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 2,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 5,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 5,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 5,
            "family": 0,
            "bedding": 0,
            "quality": 0,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "towels",
            "mirror",
            "toiletries",
            "safe",
            "private-bathroom",
            "telephone"
          ]
        }
      ]
    },
    {
      "hotelId": 1462705,
      "hotelRoomAmenities": [
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom",
            "wi-fi"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 1,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom",
            "wi-fi"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 3,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom",
            "wi-fi"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 4,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "wi-fi",
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
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
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 2,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        }
      ]
    },
    {
      "hotelId": 1406423,
      "hotelRoomAmenities": [
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 2,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 2,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 5,
            "family": 0,
            "bedding": 0,
            "quality": 0,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "wi-fi",
            "shower",
            "mirror",
            "towels",
            "safe",
            "toiletries",
            "private-bathroom",
            "telephone"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 4,
            "quality": 1,
            "bathroom": 2,
            "capacity": 2,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 0,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "wi-fi",
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 4,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "wi-fi",
            "private-bathroom"
          ]
        },
        {
          "rgExt": {
            "sex": 0,
            "club": 0,
            "class": 3,
            "family": 0,
            "bedding": 0,
            "quality": 1,
            "bathroom": 2,
            "capacity": 1,
            "balcony": 0,
            "bedrooms": 0,
            "view": 0,
            "floor": 0
          },
          "roomAmenities": [
            "private-bathroom",
            "wi-fi"
          ]
        }
      ]
    }
  ]
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **v. 1** |  |