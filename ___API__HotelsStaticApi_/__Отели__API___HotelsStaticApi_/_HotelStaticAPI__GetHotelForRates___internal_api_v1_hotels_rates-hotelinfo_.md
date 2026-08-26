# Метод GetHotelForRates (/internal\_api/v1/hotels/rates-hotelinfo)

| Назначение | Получение информации о master-отеле по идентификатору отеля |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/rates-hotelinfo |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer | REQUIRED | Идентификатор master-отеля |

### Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура RatesHotelInfoApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| MasterHotelId | int | REQUIRED | идентификатор master hotel id |
| IanaTimeZone | string | REQUIRED | Наименование часового пояса |
| RoomGroups | \[] | REQUIRED | Объект, описывающий типы комнат в master-отеле |

### Структура RoomGroup

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Name | string | REQUIRED | Наименование типа комнаты |
| NameEn | string | optional | Наименование типа комнаты на английском языке |
| RgExt | [RgExt](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=2587856642) | REQUIRED | Структура RgExt |
| RoomAmenities | string\[] | REQUIRED | Список услуг в данном типе комнат. Может быть пустой |
| Images | string\[] | optional | Коллекция URL фотографий типа комнат |

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
| details |  | OPTIONAL | Описание ошибок валидации |

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
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Идентификатор master-отеля обязателен. | masterHotelId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "noMasterHotelId",
			"message": "Идентификатор master-отеля обязателен.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Не существует отелея с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода GetHotelByMasterId

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[HotelStaticApi\_GetRateHotelInfo] в TravelDB. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId
4. Выполняется выборка из таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
   и выполняется операция объединения данных с таблицей TravelDB.Location с информацией о часовом поясе локации по HotelDetails.PrimaryLocationID = TravelDB.Location.LocationID.
5. Выборка данных из таблицы TravelDB.RoomContent в которой находятся информация о комнатах отеля для которых HotelId = @HotelID  
   и выполняется операция  объединения данных с таблицей TravelDB.RoomAmenity в которой находятся услуги на уровне комнаты по RoomContent.RoomContentId = RoomAmenity.RoomContentId
6. Выборка данных из таблицы TravelDB.RoomContent в которой находятся информация о комнатах отеля для которых HotelId = @HotelID  
   и выполняется операция  объединения данных с таблицей TravelDB.RoomImage в которой находятся фотографиях комнат по RoomContent.RoomContentId = RoomImage.RoomContentId.
7. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель RatesHotelInfoApiResponsePayloadApiResponse.

# Маппинг данных на модель Hotel Static API

<table><colgroup><col/><col/></colgroup><thead><tr><th><p>Параметр</p></th><th colspan="1"><p>Источник данных</p></th></tr></thead><tbody><tr><td colspan="1">payload</td><td colspan="1"><br/></td></tr><tr><td>-&gt;MasterHotelId</td><td colspan="1">[TravelDB]..[HotelDetails].HotelId</td></tr><tr><td colspan="1">-&gt;IanaTimeZone</td><td colspan="1"><p>[TravelDB]..[Location].TimeZoneName</p></td></tr><tr><td colspan="1">-&gt;RoomGroups</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;Name</td><td colspan="1">[TravelDB].[RoomContent].Name</td></tr><tr><td colspan="1">-&gt;-&gt;NameEn</td><td colspan="1">[TravelDB].[RoomContent].NameEn</td></tr><tr><td colspan="1">-&gt;-&gt;RgExt</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;-&gt;Sex</td><td colspan="1"><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 15 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): <br/>В зависимости от [HotelInvenotry].[Room].Gender для выбранной комнаты.</p><table><tbody><tr><th> [HotelInvenotry].[Room].Gender</th><th>Sex</th></tr><tr><td>0</td><td>3</td></tr><tr><td>1</td><td>2</td></tr><tr><td>2</td><td>1</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Club</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 21 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Class</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 0 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): в зависимости от по значению [HotelInvenotry].[Room].RoomTypeId</p><table><tbody><tr><th>Тип номера</th><th>Class</th></tr><tr><td>Standard</td><td>3</td></tr><tr><td>EconomyBudget</td><td>3</td></tr><tr><td colspan="1">Superior</td><td colspan="1">3</td></tr><tr><td colspan="1">Deluxe</td><td colspan="1">3</td></tr><tr><td colspan="1">Suite</td><td colspan="1">3</td></tr><tr><td colspan="1">FamilyRoom</td><td colspan="1">3</td></tr><tr><td colspan="1">Executive</td><td colspan="1">3</td></tr><tr><td colspan="1">PresidentialSuite</td><td colspan="1">3</td></tr><tr><td colspan="1">Studio</td><td colspan="1">3</td></tr><tr><td colspan="1">SharedRoom</td><td colspan="1">1</td></tr><tr><td colspan="1">Apartment</td><td colspan="1">6</td></tr><tr><td colspan="1">Cabin</td><td colspan="1">9</td></tr><tr><td colspan="1">Lodge</td><td colspan="1">17</td></tr><tr><td colspan="1">Villa</td><td colspan="1">8</td></tr><tr><td colspan="1">Chalet</td><td colspan="1">18</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Family</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 18 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): &#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;13&#34; (для выбранной комнаты), &#34;0&#34;, если нет.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Bedding</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 6 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet):<br/>Если количество уникальных вариантов ([HotelInventory].[BedConfiguration].BedType для выбранной комнаты) не равно 1:</p><table><tbody><tr><th>Условие</th><th>Bedding</th></tr><tr><td>Количество уникальных [HotelInventory].[BedConfiguration].BedType = 0</td><td>0</td></tr><tr><td>Количество уникальных [HotelInventory].[BedConfiguration].BedType &gt; 1</td><td>7</td></tr></tbody></table><p>Если количество уникальных вариантов типов кроватей ([HotelInventory].[BedConfiguration].BedType для выбранной комнаты) равно 1:</p><table><tbody><tr><th>BedType</th><th>Bedding</th></tr><tr><td>Single</td><td>4</td></tr><tr><td><ul><li>Double</li><li>Queen</li><li>King</li></ul></td><td>3</td></tr><tr><td>Bunk</td><td>1</td></tr><tr><td colspan="1">None</td><td colspan="1">0</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Quality</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 3 + перевод в int</li><li><p>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): в зависимости от по значению [HotelInvenotry].[Room].RoomTypeId</p><table><tbody><tr><th>Тип номера</th><th>Quality</th></tr><tr><td>Standard</td><td>2</td></tr><tr><td colspan="1">EconomyBudget</td><td colspan="1">1</td></tr><tr><td colspan="1">Superior</td><td colspan="1">3</td></tr><tr><td colspan="1">Deluxe</td><td colspan="1">4</td></tr><tr><td colspan="1">Suite</td><td colspan="1">5</td></tr><tr><td colspan="1">FamilyRoom</td><td colspan="1">6</td></tr><tr><td colspan="1">Executive</td><td colspan="1">8</td></tr><tr><td colspan="1">PresidentialSuite</td><td colspan="1">9</td></tr><tr><td colspan="1">Studio</td><td colspan="1">20</td></tr></tbody></table><p>Для всех остальных случаев - &#34;0&#34;.</p></li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Bathroom</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 9 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet):<br/>&#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;410&#34; (для выбранной комнаты);<br/>&#34;2&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;18&#34; или &#34;19&#34; (для выбранной комнаты);<br/>&#34;3&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;415&#34; (для выбранной комнаты);<br/>&#34;0&#34; для всех остальных случаев.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Capacity</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 12 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): Значение [HotelInventory].[RoomAmenity].MaxPersons если оно меньше 6, иначе &#34;0&#34;.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Balcony</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 27 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): &#34;1&#34;, если существует [HotelInventory].[RoomAmenity] с идентификатором &#34;399&#34; (для выбранной комнаты), &#34;0&#34;, если нет.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Bedrooms</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 24 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;View</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 30 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td>-&gt;-&gt;-&gt;Floor</td><td><ul><li>Для [TravelDB].[RoomContent].SupplierId = 36 (Ostrovok): значение первых 3 символов из [TravelDB].[RoomContent].SupplierRoomCode начиная с 33 + перевод в int</li><li>Для [TravelDB].[RoomContent].SupplierId = 11 (Tinkoff Extranet): всегда &#34;0&#34;.</li></ul></td></tr><tr><td colspan="1">-&gt;-&gt;RoomAmenities</td><td colspan="1">Список [TravelDB].[RoomAmenity].AmenityName для каждого из доступных [TravelDB].[RoomContent].RoomContentId для выбранного master-отеля с HotelId</td></tr><tr><td>-&gt;-&gt;Images</td><td>Список [TravelDB].[RoomImage].Url для каждого из доступных [TravelDB].[RoomContent].RoomContentId для выбранного master-отеля с HotelId</td></tr></tbody></table>

# Пример использования

## Запрос

```json
{
  "masterHotelId": 1426291
}
```

## Ответ

```json
{
  "payload": {
    "masterHotelId": 1426291,
    "ianaTimeZone": "Europe/Moscow",
    "roomGroup": [
      {
        "name": "Двухместный номер Standard двуспальная кровать",
		"nameEn": "Standard Double room with double bed"
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
          "soundproofing",
          "private-bathroom",
          "telephone",
          "air-conditioning",
          "bedsheets",
          "slippers",
          "tv",
          "wardrobe",
          "heating",
          "fan",
          "addon-service",
          "hairdryer",
          "bathrobe",
          "towels",
          "bath",
          "shower",
          "mini-bar",
          "with-view",
          "desk",
          "wi-fi",
          "toiletries",
          "fridge",
          "safe"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/extranet/2a/73/2a73213a0f70052790b1872f7001ee59b165edbb.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/33/5c/335ccbbebc1912c0c0e7962755436d7da3d04872.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/3d/11/3d1192e64a6f31de1aa3180e1fcf0fc49dfe99ba.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/3e/61/3e6192bbbf15d107470e50c7d8b84191c63150eb.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/7a/bb/7abb05ad820b309cede4ad3aa37886ed16997881.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/af/12/af1225700c019aaa870e2be418b09a77bab30188.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/d9/69/d9698b57458ab6fc88e2675573352902293cf282.jpeg"
        ]
      },
      {
        "name": "Двухместный номер plus Superior двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 3,
          "family": 1,
          "bedding": 3,
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
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/54/d3/54d308bf6d9cc2a9fd84a5acd76bb1c6f1075a09.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/70/56/7056c1c106593939d78c41d091c6495f2b6c6cb0.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/d1/4f/d14f2ab7145c66d9e4c515a9226206f671570341.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/fc/67/fc67ba6ba633c1cf9343360bc910159af26a2b2f.jpeg"
        ]
      },
      {
        "name": "Двухместный полулюкс Premium двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 17,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/04/b8/04b8b3748bf040fc75560a7ea9afc93b800a2051.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/59/14/5914bde960a96b36d09fd45fb2cdef96fcd9112b.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/88/5e/885e068f59f51361ab966c42b596f9d1421f0521.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/d2/78/d278cc5db3e4b638e8863e274b695a8cb7c3c487.jpeg"
        ]
      },
      {
        "name": "Двухместный номер Standard 2 отдельные кровати",
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
          "telephone",
          "private-bathroom",
          "heating",
          "wardrobe",
          "bedsheets",
          "tv",
          "air-conditioning",
          "slippers",
          "tea",
          "bathrobe",
          "fan",
          "hairdryer",
          "desk",
          "toiletries",
          "fridge",
          "safe"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/extranet/18/b3/18b3583702957d49ffb8846abe9fd18834937396.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/39/78/39786ecdbe10d013a9e1be888ed83260a6160f10.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/75/80/75805211e749a557d4635eba95554e67486a4823.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/a2/3a/a23a2dc392e837c0bce9934a1de5394770140c2f.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/a3/8b/a38b3b645cc260482ab63949912d039f7175946f.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/bd/c3/bdc330360be60e678de07a50a578806739d09cdf.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/c6/42/c64246045146f6d5a2581ed1c41522dbe4184935.jpeg"
        ]
      },
      {
        "name": "Двухместный номер Comfort двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 3,
          "family": 0,
          "bedding": 3,
          "quality": 3,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/23/55/2355dab0dfe0fcf661669bc19a07c9d527da03a9.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/29/b6/29b6f7bcd5550f7bdbba77022f1a86fc85a2e027.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/48/1c/481c635a938c32964f41524c9ba7428fcc2609db.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/72/c2/72c27b71676f4b76ace11ceb72b4166d60313989.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/82/0f/820f322a9e430c3ae3e65d8ec33f64da6f22b0a1.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/db/67/db670e61a0c958f0d46ea3965ef3feb94f339c50.png"
        ]
      },
      {
        "name": "Двухместный номер клубный Superior двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 1,
          "class": 3,
          "family": 0,
          "bedding": 3,
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
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/0a/10/0a100ecabf3de8891e45429241d77ffa01a8fac2.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/29/3e/293e1cf3ee54ca2df0401aba476c19d0339157e1.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/3e/7c/3e7cf6fdc53bec1340cbfe84d63cf4fbd0953184.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/fd/84/fd84f650a89d15d5de0b7c9851ac1cc2adb25dd4.png"
        ]
      },
      {
        "name": "Двухместный полулюкс двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 0,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/extranet/0c/e7/0ce7607fd6c987ab3f36ce888e8f960c6cef03b7.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/33/e8/33e89d1d16e6ca8e0706a80da23fa6a8a8938607.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/3c/00/3c005688884017c0b07308d34a32a55e182aafa0.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/47/1c/471c3d023121a6a998a2aa8086298d452aecdd9f.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/4f/1b/4f1bd1731fc421d63af0ea6095da5d2655a17746.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/78/d5/78d5e576900343a1326570ae0965fc9593b9c81d.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/89/a0/89a0f7e04e03f74a431af12f4e63731b31597132.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/8b/fb/8bfbfb5379856a2dcc096c6928f7a43b78bc9d62.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/8f/b7/8fb751adf81e2dd32e2c12b2cf922c7357063c12.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/94/5b/945b852f92c9d21778374c31ff12b33782cf98f7.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/9c/03/9c037356ee9e499cd5b1f032b63da69c253490fe.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/a9/dc/a9dcf935f13fbc3169bbef26352192622d7cc8a1.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/af/34/af3421adfef83e0261dfec0358825420e29d2c11.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/b4/b1/b4b1455c48bf414d598906f35a6da8321dff2e77.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/b6/65/b665b5a9af4af6352a9c54a126e9235f678a3f25.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/b9/cb/b9cb4b7937278847c5b1f366d27a36af911bebbc.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/c3/fc/c3fcdeabaf1c25a096c74fa49cffe8b810dcb442.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/c9/38/c938f5f74edd112fd9c61f9abfeadb7a9feae9c9.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/cc/40/cc40e7308bd0612eaa73e09926945873eeffefb4.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/d4/f6/d4f65ecf1d15885ff3e4ad380c35ef56468f37ad.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/db/27/db27d2cb8aabd98acc78f79fc56879759a9afb08.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/f7/c1/f7c1acd4afa1fc4c368c0c30d5e67d0e0d6eba9a.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/fa/28/fa284f501ae8673ede71b1196377e08ab08cd5e5.jpeg"
        ]
      },
      {
        "name": "Двухместный клубный полулюкс Classic двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 1,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 18,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/13/3a/133a2307f80c8f5301a7822f20c7dc0b4f16586e.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/7c/00/7c00249b6c1a74c6894256ff31beaa322f77e395.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/a7/8e/a78e8bcebf5d81fbb983b806225f5f46fecfd84d.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/f5/88/f588d6fce347f337a646a20700132e07faa7ce60.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/fb/70/fb70d3faffd58fee669896c7894241724f6b9801.png"
        ]
      },
      {
        "name": "Двухместный люкс Premium двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 5,
          "family": 0,
          "bedding": 3,
          "quality": 17,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "mirror",
          "towels",
          "private-bathroom",
          "telephone",
          "toiletries",
          "safe"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/28/61/2861203651606a62ff73f51fa990a0f204106d44.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/34/0f/340f247e1ffda5dc87fad308204eda3b78d504e8.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/54/b5/54b5153db7b3ce7dd58ad7fb5bedfb46f47729b8.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/67/bf/67bf7c4c571cfcbaf7163fa405ee832ee5263d85.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/91/59/9159d87e84109744f945a3d31bc077b8c021ee2d.jpeg"
        ]
      },
      {
        "name": "Двухместный номер Superior двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 3,
          "family": 0,
          "bedding": 3,
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
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/content/01/24/012485931ac3dfc92cbb51e9c117234293321d3a.jpeg",
          "https://cdn.worldota.net/t/{size}/content/54/db/54dbfb634ad1c08b7650aa33d945436cd74e53b1.jpeg",
          "https://cdn.worldota.net/t/{size}/content/6a/27/6a27c07132e7301abcd70cfb4cca039079349951.jpeg",
          "https://cdn.worldota.net/t/{size}/content/87/e2/87e286e417043098e3275d91adbb0247f547f142.jpeg",
          "https://cdn.worldota.net/t/{size}/content/8e/31/8e31b3b37aa4653149fb6d82ee0ae21c626c442e.jpeg",
          "https://cdn.worldota.net/t/{size}/content/a2/13/a2132a553a7d0ddb0cf6412188a7777cf83a4ccd.jpeg",
          "https://cdn.worldota.net/t/{size}/content/cd/89/cd899d1941c0b1e9db057b311e5f757670645c36.jpeg",
          "https://cdn.worldota.net/t/{size}/content/cf/53/cf538e376f7665a14ffb11bc8b720430405b2070.jpeg",
          "https://cdn.worldota.net/t/{size}/content/ec/ef/ecef2f5eb8c4366d35e56b4eab39bcd9f488cb2a.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/46/e0/46e02f6326638c4034e1a3598c50419b08f45d59.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/9a/d6/9ad600dd8058c786beaf64ca9d3529b9d6b72cca.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/9b/51/9b514f3be920e709b8036351c0b32fd7d1811733.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/be/50/be50e0aac4c4996387d1251556e3ab82b70475fe.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/da/c9/dac94809d9d1fe232d8c8c83f97b04ff7aa752f4.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/ec/a4/eca4e6a63a15bbe927946fa9e3581a4880b26bbd.jpeg"
        ]
      },
      {
        "name": "Двухместный люкс двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 5,
          "family": 0,
          "bedding": 3,
          "quality": 0,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "mirror",
          "towels",
          "private-bathroom",
          "telephone",
          "toiletries",
          "safe"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/extranet/0c/6f/0c6fa5bed1c22c4202603fac99d0e8c1ec1dfafb.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/5b/18/5b1838bea5cf9bead7c2c8d49519fb066682fdf0.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/96/c0/96c0338705109a5742cf8924316e7e3eca0938aa.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/bd/89/bd89193988882a1f7eb0d109c446f18e10145b9d.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/f0/b6/f0b6f2cbc854843c379e1a330b7805f2b399ba73.jpeg"
        ]
      },
      {
        "name": "Двухместные апартаменты Premium двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 6,
          "family": 0,
          "bedding": 3,
          "quality": 17,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/content/2e/12/2e12cfec7e9d9987bad96ec7c604bab6e5fd3f6f.jpeg",
          "https://cdn.worldota.net/t/{size}/content/c8/8b/c88b6883010e74c076021fce5f80101f7196f5ea.jpeg",
          "https://cdn.worldota.net/t/{size}/content/f3/f3/f3f3493824d3788c41a2822f54067b39740fa9c4.jpeg",
          "https://cdn.worldota.net/t/{size}/content/ff/8b/ff8bd2f3c7dd98a3a055a095aa6816588f60e404.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/b8/65/b86525c43e148fb00869512a37af08a3d763d30c.png"
        ]
      },
      {
        "name": "Двухместные апартаменты Grand двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 6,
          "family": 0,
          "bedding": 3,
          "quality": 20,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/23/8d/238d43d3bdd35fe7160edbc6d20555ab12fcb830.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/2c/d4/2cd4ddb7162456d9457852d37e9bca914e094a78.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/54/90/5490032d3769c0dd8792a6fd94f9317ec455a51a.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/8f/a1/8fa1ff9a031911d3641073bed32dcc6304c4a740.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/c9/4c/c94c623e142aa63d2c514c56cdc9b203468c73a3.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/fc/cb/fccbd0c1b93f76d4cf366be86357a736c46adb80.jpeg"
        ]
      },
      {
        "name": "Одноместный номер Standard",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 3,
          "family": 0,
          "bedding": 0,
          "quality": 2,
          "bathroom": 2,
          "capacity": 1,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "fan",
          "tea",
          "heating",
          "private-bathroom",
          "telephone",
          "shower",
          "toiletries",
          "safe",
          "tv",
          "slippers"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/extranet/05/32/0532ea6c902816297241b07811f0a1b306af86dc.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/2f/0a/2f0a4a4c07ac0c8ae4d86e1422761db2ce662d7b.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/33/5c/335ccbbebc1912c0c0e7962755436d7da3d04872.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/cd/ab/cdab8d9d79844f0cb61d65a4a0ab0de7b804bc19.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/d7/11/d7119d9a11b9f42c7481c93cde625cb2a545cb02.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/e2/45/e2457e42a01534cbee81c3e45d98aa7918c4380f.jpeg",
          "https://cdn.worldota.net/t/{size}/extranet/ec/54/ec5490d85e16bbdd0d5248808dbd02acf5c04184.jpeg"
        ]
      },
      {
        "name": "Двухместный люкс Elegant двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 5,
          "family": 0,
          "bedding": 3,
          "quality": 21,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "mirror",
          "towels",
          "private-bathroom",
          "telephone",
          "toiletries",
          "safe"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/68/e4/68e4b4907e2949d889d328fe59afd4f7bb18a26f.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/71/e2/71e247f3a2cd1429f99dd6d2efd6c156c3b07397.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/d4/c4/d4c4b1a90c8fdda1a25ff3fcabdde43c675fc99e.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/e2/81/e2817cb87f0985afb19d065ef2e912672d200262.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/e7/41/e7416bc457084efaefd7d3395f0b05b98ea7c537.jpeg"
        ]
      },
      {
        "name": "Двухместный полулюкс Deluxe двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 6,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/09/9a/099a2cbc1be8ea336ea16550e7b75813d69e522c.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/67/3c/673c286d534946a8c067e3478d015fa7d90fba07.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/6f/9b/6f9b286e034c27cc7f611a7516885821ef264ffc.jpeg",
          "https://cdn.worldota.net/t/{size}/ostrovok/bd/3e/bd3e927c5d6c043d57df1ca390a85ac5d4f05d39.jpeg"
        ]
      },
      {
        "name": "Двухместный клубный полулюкс Prestige двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 1,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 23,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/3b/32/3b32606280af8dfdebfc93cd272a220b7a159b0c.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/44/0a/440a1958c657a458a136121b5ac9a48455bef4f6.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/6a/45/6a4506fc65a898a2031f4e4cdf677bf989a64a9f.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/84/31/84314b8d8c775999a625187340c814ccfde89533.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/zz/32/ad32abb5f067667f3ff8d0c6d0c92d090849f5ea.png"
        ]
      },
      {
        "name": "Двухместный полулюкс Classic двуспальная кровать",
        "rgExt": {
          "sex": 0,
          "club": 0,
          "class": 4,
          "family": 0,
          "bedding": 3,
          "quality": 18,
          "bathroom": 2,
          "capacity": 2,
          "balcony": 0,
          "bedrooms": 0,
          "view": 0,
          "floor": 0
        },
        "roomAmenities": [
          "private-bathroom",
          "toiletries"
        ],
        "images": [
          "https://cdn.worldota.net/t/{size}/ostrovok/24/6c/246c1cd41c6cafba09bed5ce85acf758f69f904e.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/32/5d/325d9eae0bc3a16dc1b88f922eca4238b09d2c99.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/70/3c/703c6149198626e2d8cc3cf37f60ac7ff4b25286.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/c6/6b/c66bd006e159520892e9729e3c187ae69463f6f2.png",
          "https://cdn.worldota.net/t/{size}/ostrovok/d1/46/d146a6304fe9429b438e61d9bf08a4df07fd771f.png"
        ]
      }
    ]
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | [**v. 10**](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3322313003&version=10) |  |
| 2 | Добавление полей для ваучера на английском языке | Текущая | THB-4224 |