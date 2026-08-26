# Метод GetHotelInfos (/internal\_api/v3/hotels/hotelinfolist)

| Назначение | Получение полной статической информации об отеле по набору идентификаторов master-отелей |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-b-cloud-test-wl1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-b-cloud-test-wl1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v3/hotels/hotelinfolist |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelListApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelIds | integer:\[] | REQUIRED | Идентификаторы master-отелей |

## Структура ответа

### Структура HotelInfoByMasterId

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | int | REQUIRED | Идентификатор master-отеля |
| isClosed | bool | REQUIRED | Флаг закрыт ли отель |
| deleted | bool | REQUIRED | Удален ли отель |
| name | string | REQUIRED | Наименование master-отеля |
| nameEn | string | OPTIONAL | Английское наименование master-отеля |
| hotelChain | string | OPTIONAL | Наименование сети, которой принадлежит отель |
| starRating | int | REQUIRED | Звездность отеля |
| images | HotelImage\[] | REQUIRED | Коллекция фотографий отеля |
| address | string | REQUIRED | Адрес отеля |
| addressEn | string | OPTIONAL | Адрес отеля на английском языке |
| masterLocationId | int | REQUIRED | Идентификатор master-локации отеля |
| kind | string | REQUIRED | Тип отеля |
| coordinates |  | REQUIRED | Объект, описывающий местоположение отеля (широта, долгота) |
| ianaTimeZone | string | REQUIRED | Часовой пояс отеля |
| checkInTime | string($timeonly) | OPTIONAL | Стандартное время заезда в отель |
| checkOutTime | string($timeonly) | OPTIONAL | Стандартное время выезда из отеля |
| phone | string | OPTIONAL | Номер телефона отеля |
| email | string | OPTIONAL | E-mail отеля |
| description | \[] | OPTIONAL | Коллекция объектов, содержащих описание отеля |
| facts |  | optional | Объект, описывающий факты об отеле |
| facilities | Facility\[] | REQUIRED | Объект, описывающий услуги в отеле |
| metapolicyExtraInfo | string | OPTIONAL | Дополнительная информация об отеле |
| metapolicyExtraInfoEn | string | OPTIONAL | Дополнительная информация об отеле на английском языке |
| metapolicy |  | OPTIONAL | Объект, описывающий мета-данные политик отеля. |
| paymentMethods | string\[] | optional | Доступные способы оплаты в отеле |
| location |  | REQUIRED | Объект, описывающий расположение отеля |
| policy | \[] | OPTIONAL | Объект, описывающий условия отеля |
| certification |  | OPTIONAL | Объект, описывающий параметры сертификации |
| certificationNeeded | bool | REQUIRED | Флаг, нужна ли для данного объекта размещения сертификация или нет. |
| cityName | string | REQUIRED | Наименование города |
| cityNameEn | string | REQUIRED | Наименование города на английском |
| countryName | string | REQUIRED | Наименование страны |
| countryNameEn | string | REQUIRED | Наименование страны на английском |
| apartmentFacts |  | OPTIONAL | Объект с атрибутами характерными для квартиры<br />Обязателен, если в БД для данного объекта размещения параметр isFlat=true |

### Структура HotelImage

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| imagePath | string | REQUIRED | URL фото |
| categories | HotelImageCategory\[] | REQUIRED | Категории фотографии |
| aestheticScore | double | OPTIONAL | Оценка эстетичности фотографии |

Структура HotelImageCategory

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| categoryId | string | REQUIRED | Идентификатор категории фотографии |
| categoryName | string | REQUIRED | Название категории фотографии |
| confidence | double | REQUIRED | Уверенность определения категории |

### Структура GeoPoint

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| latitude | decimal | REQUIRED | Географическая широта |
| longitude | decimal | REQUIRED | Географическая долгота |

### Структура Description

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| title | string | OPTIONAL | Заголовок описания |
| paragraphs | string | OPTIONAL | Текст описания |

### Структура Location

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | string | REQUIRED | Идентификатор master-локации |
| name | string | REQUIRED | Имя региона\\локации |
| type | string | REQUIRED | Тип региона\\локации |
| countryCode | string | REQUIRED | Код страны |

### Структура Facts

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| yearBuilt | int | optional | Год постройки отеля |
| electricity |  | optional | Объект, описывающий информацию о розетках в отеле |
| roomsNumber | int | optional | Количество номеров в отеле |
| floorsNumber | int | optional | Количество этажей в отеле |
| yearRenovated | int | optional | Год последнего капитального ремонта в отеле |

### Структура Electricity

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| sockets | string:\[] | optional | Список доступных разъемов |
| voltage | int:\[] | optional | Список доступных напряжений тока |
| frequency | int:\[] | optional | Список доступных частот тока |

### Структура Facility

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| id | int | REQUIRED | ID услуги |
| name | string | REQUIRED | Наименование услуги |
| priority | int | optional | Приоритет услуги |
| groupId | int | REQUIRED | ID группы |
| groupName | string | REQUIRED | Наименование типа услуг |

### Структура Metapolicy

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| cot |  | optional | Массив объектов, описывающий дополнительные услуги, связанные с детскими кроватями |
| meal |  | optional | Массив объектов, описывающий дополнительные услуги, связанные питанием |
| pets |  | optional | Массив объектов, описывающий дополнительные услуги, связанные с размещением с животными |
| visa |  | optional | Объект, описывающий доступность услуги визовой поддержки |
| addFee |  | optional | Массив объектов, описывающий дополнительные платежи |
| deposit |  | optional | Массив объектов, описывающий депозиты в отеле |
| noShow |  | optional | Объект, описывающий штраф за незаезд по бронированию |
| parking |  | optional | Массив объектов, описывающий доступные варианты парковки |
| shuttle |  | optional | Массив объектов, описывающий доступные варианты трансфера |
| children |  | optional | Массив объектов, описывающий доступные дополнительные детские кровати |
| internet |  | optional | Массив объектов, описывающий дополнительные услуги, связанные с доступом в интернет |
| extraBed |  | optional | Массив объектов, описывающий доступные дополнительные кровати для взрослых |
| childrenMeal |  | optional | Массив объектов, описывающий дополнительные услуги, связанные питанием для детей |
| checkInCheckOut |  | optional | Массив объектов, описывающий условия заезда и выезда из отеля |

### Структура ChildrenBed

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| amount | int | optional | Количество детских кроватей |
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |

### Структура Meal

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| mealType | string | optional | Код типа питания |
| mealName | string | optional | Наименование типа питания |
| price | decimal | optional | Цена в валюте Currency |

### Структура Pets

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| petsType | string | optional | Тип животных |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |

### Структура Visa

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| visaSupport | string | optional | Возможность визовой поддержки |

### Структура AddFee

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| feeType | string | optional | Тип дополнительного платежа |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |

### Структура Deposit

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| availability | string | optional | Обязательность услуги |
| currency | string | optional | Валюта оплаты |
| depositType | string | optional | Тип депозита |
| paymentType | string | optional | Тип оплаты |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |
| pricingMethod | string | optional | Способ оплаты |

### Структура NoShow

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| time | string | optional | Время, применимое для правил не заезда |
| dayPeriod | string | optional | Период дня, применимый для правил не заезда |
| availability | string | optional | Обязательность услуги |

### Структура Parking

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| price | decimal | optional | Цена в валюте Currency |
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| priceUnit | string | optional | Единица за которую производится оплата |
| territoryType | string | optional | Тип территории парковки |

### Структура Shuttle

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| destinationType | string | optional | Направление трансфера |
| price | decimal | optional | Цена в валюте Currency |
| shuttleType | string | optional | Тип трансфера |

### Структура ChildrenExtraBed

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| ageEnd | int | optional | Максимальный возраст ребенка для которого доступна дополнительная кровать |
| ageStart | int | optional | Минимальный возраст ребенка для которого доступна дополнительная кровать |
| currency | string | optional | Валюта оплаты |
| extraBed | string | optional | Доступность дополнительных кроватей |
| price | decimal | optional | Цена в валюте Currency |

### Структура Internet

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| internetType | string | optional | Тип доступа в интернет |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |
| workArea | string | optional | Место доступа в интернет |

### Структура ExtraBed

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| amount | int | optional | Количество доступных дополнительных кроватей для взрослых |
| currency | string | optional | Валюта оплаты |
| inclusion | string | optional | Включенность услуги в стоимость |
| price | decimal | optional | Цена в валюте Currency |
| priceUnit | string | optional | Единица за которую производится оплата |

### Структура ChildrenMeal

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| price | decimal | optional | Цена в валюте Currency |
| ageEnd | int | optional | Максимальный возраст ребенка для которого доступно дополнительное питание |
| currency | string | optional | Валюта оплаты |
| ageStart | int | optional | Минимальный возраст ребенка для которого доступно дополнительное питание |
| inclusion | string | optional | Включенность услуги в стоимость |
| mealType | string | optional | Тип питания |

### Структура CheckInCheckOut

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| currency | string | optional | Валюта оплаты |
| checkInCheckOutType | string | optional | Тип заезда или выезда из отеля |
| inclusion | string | optional | Включенность услуги в стоимость |
| price | decimal | optional | Цена в валюте Currency |

### Структура Certification

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| resortId | string | REQUIRED | ID объекта размещения в системе Росреестра. Пример: 4864e408-78f4-11f0-aea5-05a7293da819 |
| status | string | REQUIRED | Статус объекта размещения |
| type | string | REQUIRED | Тип объекта размещения |
| registerRecord | string | REQUIRED | Номер реестровой записи |
| fullName | string | REQUIRED | Наименование объекта |
| addressList | string\[] | optional | Массив адресов объекта |
| ownerName | string | optional | Наименование собственника |
| ownerInn | string | REQUIRED | ИНН собственника |
| ownerKpp | string | optional | КПП собственника |
| ownerOgrn | string | optional | ОГРН собственника |
| room |  | optional | Массив комнат |

### Структура Room

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| apartmentCount | int | optional | Количество апартаментов |
| numberSeats | int | optional | Количество спальных мест |
| roomCategoryName | string | optional | Наименование удобства из справочника  Росреестра |
| roomCategoryId | int | optional | ID объекта удобств из справочника  Росреестра |

### Структура ApartmentFacts

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| isFlat | bool | REQUIRED | Признак, что объект является квартирой |
| roomsCount | int | optional | Количество комнат в апартаментах/квартире |
| size | int | optional | Площадь апартаментов/квартиры |
| currentFloor | int | optional | Этаж расположения апартаментов/квартиры |
| guestsCount | int | optional | Максимальное количество гостей для заселения |
| contactlessCheckin | object: | optional | Бесконтактное заселение |
| bedConfigurations | object\[]: | optional | Массив конфигураций кроватей |
| roomFacilities | int\[] | optional | Удобства комнаты |

### Структура C**ontactlessCheckin**

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th colspan="1">Параметр</th><th colspan="1">Тип</th><th colspan="1">Обязательность</th><th colspan="1">Описание</th></tr><tr><td colspan="1">isContactless</td><td colspan="1">bool</td><td colspan="1"><div><p>REQUIRED</p></div></td><td colspan="1"><div><p>Признак бесконтактного заселения</p></div></td></tr><tr><td colspan="1">keysPickupType</td><td colspan="1">enum</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><p>Способ передачи, возможные значения:</p><ul><li>phone</li><li>address</li><li>keypad</li><li>apartments</li><li>office</li><li>reception</li><li>smartlock</li><li>lockbox</li></ul></td></tr><tr><td colspan="1">keysPickupPhone</td><td colspan="1">string</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1">Телефон для получения инструкции по заселению</td></tr></tbody></table>

### Структура BedConfigurations

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypes | object\[]: | REQUIRED | Описание спальных мест |

### Структура BedTypes

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| bedTypeId | int | REQUIRED | Идентификатор типа спального места |
| isExtraBed | bool | REQUIRED | Признак "Дополнительное спальное место" |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details |  | OPTIONAL | Описание ошибок валидации |

Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | REQUIRED | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | REQUIRED | Код атрибута |

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

# Алгоритм работы метода

## MC.Основной сценарий

01. Проверяется фича-тоггл UseCassandraForHotelDetails:
    
    1. Если tue, то переходим к п.2
    2. Если false, то переходим к п.3
02. Получаем данные формата json [hotels\_static.master\_hotel\_details.hotel\_data](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%9A%D0%BE%D1%80%D0%BD%D0%B5%D0%B2%D0%BE%D0%B9%20%D0%BE%D0%B1%D1%8A%D0%B5%D0%BA%D1%82%3A%20HotelDetails) из таблицы Cassandra по ключу master\_hotel\_id. Если записи мастер отеле нет, то переходим к п.3, такое событие логируем (на случай, если первоначальная проливка не смогла пролить все отели)
    
    01. Получаем данные формата json [hotels\_static.master\_location.location\_data](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_location) из таблицы Cassandra по ключу master\_location\_id, который содержится в [master\_hotel\_details.hotel\_data.masterLocationId](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%9E%D1%80%D0%B8%D0%B3%D0%B8%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9%20%D0%B0%D0%B4%D1%80%D0%B5%D1%81-,masterLocationId,-int). Если записи мастер локации нет,  
        то переходим к п.3, такое событие логируем (на случай, если первоначальная проливка не смогла пролить все локации)
    02. Получаем данные формата json hotels\_static.master\_location.location\_data из таблицы Cassandra по ключу master\_location\_id, который содержится в [master\_hotel\_details.hotel\_data.countyId](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=ID%C2%A0%20%D0%B3%D0%BE%D1%80%D0%BE%D0%B4%D0%B0%20%D0%BE%D1%82%D0%B5%D0%BB%D1%8F-,countryId,-int)
    03. Получаем данные формата json hotels\_static.master\_location.location\_data из таблицы Cassandra по ключу master\_location\_id, который содержится в [master\_hotel\_details.hotel\_data.cityId](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=ID%20%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BC%D0%B5%D1%81%D1%82%D0%BE%D0%BF%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D1%8F-,cityId,-int)
    04. Получаем следующие справочники из ImemoryCache(если данных нет в кеше, получаем из CMS):
        
        1. 1. СMS.HotelDescriptionType
           2. CMS.Facility
           3. CMS.FacilityCategory
           4. CMS.HotelSocketType
           5. CMS.MealType
           6. CMS.TimeZone
    05. Выборка данных из json [hotel\_data.descriptions](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%9F%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0%20%D0%B2%D0%B8%D0%B7-,descriptions,-HotelDescription%5B%5D)
        
        1. Выполняется операция объединения данных с полученными данными из шага d.1(СMS.HotelDescriptionType) в которой находятся типы описания отеля по HotelDescriptionType.HotelDescriptionTypeID = HotelDescription.HotelDescriptionTypeID.
        2. Выбирают описания, где СMS.HotelDescriptionType.ShowInDetails=1
        3. Выполняется сортировка по HotelDescriptionType.Position (приоритет типа описания), [hotel\_data.descriptions.isDefault](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%A2%D0%B5%D0%BA%D1%81%D1%82%20%D0%BE%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D1%8F-,isDefault,-bool) (основное описание отеля) в порядке уменьшения,  HotelDescription.HotelDescriptionID в порядке увеличения. Используем данные по HotelDescriptionType.HotelDescriptionTypeID: 4, 5, 7, 10-15.  В ответе передаем title и paragraph для всех HotelDescriptionType, кроме DescriptionTypeId = 7 (Описание отеля), для него передаем значение в paragraph, и title=null.
        4. Если Description содержит спец сивмолы \\r\\n или просто \\r, то дополнительно разбивать значение на несколько отдельных элементов.
    06. Выборка данных из json [hotel\_data](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%9F%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0%20%D0%B2%D0%B8%D0%B7-,descriptions,-HotelDescription%5B%5D)[.facilities](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D0%98%D0%B7%D0%BE%D0%B1%D1%80%D0%B0%D0%B6%D0%B5%D0%BD%D0%B8%D1%8F%20%D0%BE%D1%82%D0%B5%D0%BB%D1%8F-,facilities,-int%5B%5D)
        
        1. Объединяем c данными полученными из шага d.2(CMS.Facility) по ключу FacilityID
        2. Объединяем с данными полученными из шага d.3(CMS.FacilityCategory) по ключу FacilityCategoryID
        3. Сортируем по c.FacilityCategoryID, b.FacilityID ASC
        4. Получаем маппинги из travel\_hotels\_static.facility\_mappings и travel\_hotels\_static.facility\_priorities для маппинга приоритетов удобств
    07. Выборка данных  из json [hotel\_data](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#:~:text=%D0%9F%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%BA%D0%B0%20%D0%B2%D0%B8%D0%B7-,descriptions,-HotelDescription%5B%5D)[.facts.electricity.sockets](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5-,sockets,-int%5B%5D) в которой находятся связи между отелями и их типами разъемов для которых  
        выполняется операция объединения c данными полученными в пункте d.4 (CMS.HotelSocketType) в которой находится словарь типов разъемов по SocketType.SocketTypeID=HotelSocketType.SocketTypeIDи выполняется сортировка по SocketType.Code (код разъема) в порядке увеличения.
    08. Выборка данных из json [hotel\_data.metaPolicy.meal](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D0%9F%D0%BE%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B8%20%D0%B4%D0%B5%D1%82%D1%81%D0%BA%D0%B8%D1%85%20%D0%BA%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D0%BE%D0%BA-,meal,-HotelMeal%5B%5D) в которой находятся отели с соответствующими им типами питания для которых   
        выполняется операция объединения данных с таблицей c данными полученными в пункте d.5 (CMS.MealType) в которой находится словарь типов питания, их названия и коды по MealType.MealTypeID=HotelMeal.mealTypeId.
    09. Выборка данных из json [hotel\_data.metaPolicy.childrenMeal](https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D0%9F%D0%BE%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B8%20%D0%B4%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D1%8B%D1%85%20%D0%BA%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%B9-,childrenMeal,-HotelChildrenMeal%5B%5D) в которой находятся отели с соответствующими им типами питания для которых  выполняется операция объединения c данными полученными в пункте d.5 (CMS.MealType) в которой находится словарь типов питания и их кодов по MealType.MealTypeID=HotelChildrenMeal.mealTypeId.
    10. Формируется ответ вызывающей стороне в соответствии с алгоритмом
    11. Сценарий завершен
        
        ## SC-1.Формирование ответа
        
        1. Формируется структура HotelInfoApiResponseListPayloadApiResponse в соответствии с маппингом:
           
           <table><colgroup><col/><col/></colgroup><tbody><tr><th><p><span>Параметр</span></p></th><th colspan="1"><span>Источник данных</span></th></tr><tr><td><span>masterHotelId</span></td><td colspan="1"><span>Запрашиваемый masterHotelId</span></td></tr><tr><td><span>isClosed</span></td><td colspan="1"><p><span>Если  <a href="https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D1%81%D1%85%D0%B5%D0%BC%D1%8B%20(%D1%82%D0%B5%D0%BA%D1%83%D1%89%D0%B0%D1%8F%3A%201)-,isActive,-bool">hotel_data.isActive </a></span><span>= 1, тогда false</span></p><p><span>Если <a href="https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_hotel_details#hotels_static.master_hotel_details-,facilities,-int%5B%5D:~:text=%D1%81%D1%85%D0%B5%D0%BC%D1%8B%20(%D1%82%D0%B5%D0%BA%D1%83%D1%89%D0%B0%D1%8F%3A%201)-,isActive,-bool">hotel_data.isActive</a> = 0, тогда true</span></p></td></tr><tr><td colspan="1"><span>deleted</span></td><td colspan="1"><span>Всегда false</span></td></tr><tr><td colspan="1"><span>name</span></td><td colspan="1"><p><span>Первое непустое по приоритету из: hotel_data.nameRu, hotel_data.nameEn, hotel_data.nameOriginal</span></p></td></tr><tr><td colspan="1"><span>nameEn</span></td><td colspan="1"><span>hotel_data.nameEn</span></td></tr><tr><td colspan="1"><span>hotelChain</span></td><td colspan="1"><span>hotel_data.hotelChain</span></td></tr><tr><td colspan="1"><span>starRating</span></td><td colspan="1"><span>hotel_data.starRating</span></td></tr><tr><td colspan="1"><span>images</span></td><td colspan="1"><p><span>images Формируется из hotel_data.images:</span><br/><span>imagePath = image.imagePath</span><br/><span>categories = image.categories, Категории заполняются только для фотографий, у которых внутренний признак moderation.isFlagged = false.</span><br/><span>Если moderation.isFlagged = true, categories возвращается пустым массивом.</span><br/><span>aestheticScore = image.aesthetic.score</span></p></td></tr><tr><td colspan="1"><span>address</span></td><td colspan="1"><div><p><span>Первое непустое по приоритету из: hotel_data.addressRu, hotel_data.addressOriginal, если все значение null or empty, то empty</span></p></div></td></tr><tr><td colspan="1"><span>addressEn</span></td><td colspan="1"><span>hotel_data.addressEn</span></td></tr><tr><td colspan="1"><span>masterLocationId</span></td><td colspan="1"><span>hotel_data.masterLocationId</span></td></tr><tr><td colspan="1"><span>kind</span></td><td colspan="1"><p><span>В зависимости от hotel_data.</span><span>h</span><span><span>otelCategoryId</span> </span><span>(мапится по таблице </span>)</p><ul><li><span>Если HotelCategory = 20, то мапится на HotelCategoryId  = 0, Kind = HotelCategoryName = Resort</span></li><li><span>Если HotelCategory = 40, то мапится на HotelCategoryId  = 1, Kind = HotelCategoryName = Sanatorium</span></li><li><span>Если HotelCategory = 13, то мапится на HotelCategoryId  = 2, Kind = HotelCategoryName = Guesthouse</span></li><li><span>Если HotelCategory = 26, то мапится на HotelCategoryId  = 3, Kind = HotelCategoryName = MiniHotel</span></li><li><span>Если HotelCategory = 10, то мапится на HotelCategoryId  = 4, Kind = HotelCategoryName = Castle</span></li><li><span>Если HotelCategory = 1, то мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li><li><span>Если HotelCategory = 3, то мапится на HotelCategoryId  = 7, Kind = HotelCategoryName = Apartment</span></li><li><span>Если HotelCategory = 11, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 14, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 12, то мапится на HotelCategoryId  = 9, Kind = HotelCategoryName = Farm</span></li><li><span>Если HotelCategory = 8, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 25, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 9, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 22, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 4, то мапится на HotelCategoryId  = 12, Kind = HotelCategoryName = Hostel</span></li><li><span>Если HotelCategory = 6, то мапится на HotelCategoryId  = 13, Kind = HotelCategoryName = Bnb</span></li><li><span>Если HotelCategory = 2, то мапится на HotelCategoryId  = 14, Kind = HotelCategoryName = ApartHotel</span></li><li><span>Если HotelCategory = 42, то мапится на HotelCategoryId  = 6, Kind = HotelCategoryName = BoutiqueAndDesign</span></li><li><span>Если HotelCategory = 43, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping<br/></span></li><li><span>Если HotelCategory = 44, то мапится на HotelCategoryId  = 15, Kind = HotelCategoryName = Glamping</span></li><li><span>В противном случае мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li></ul></td></tr><tr><td colspan="1"><span>coordinates</span></td><td colspan="1"><br/></td></tr><tr><td colspan="1"><span>-&gt;latitude</span></td><td colspan="1"><span>hotel_data.latitude</span></td></tr><tr><td colspan="1"><span>-&gt;longitude</span></td><td colspan="1"><span>hotel_data.longitude</span></td></tr><tr><td colspan="1"><span>ianaTimeZone</span></td><td colspan="1"><p><span>![CMS]..[</span><span>TimeZone].TimeZoneName!</span></p><p><span><a href="https://wiki.tcsbank.ru/display/TRAVELHOTELS/hotels_static.master_location">location_data</a>.TimeZoneName</span></p></td></tr><tr><td colspan="1"><span>checkInTime</span></td><td colspan="1"><span>hotel_data.сheckInTime</span></td></tr><tr><td><span>checkOutTime</span></td><td><span>hotel_data.сheckOutTime</span></td></tr><tr><td><span>phone</span></td><td><span>hotel_data.phone</span></td></tr><tr><td><span>email</span></td><td><span>hotel_data.email</span></td></tr><tr><td><span>description</span></td><td><p><span>Маппинг описан в п 2.е </span></p></td></tr><tr><td colspan="1"><span>-&gt;title</span></td><td colspan="1"><span>СMS.[HotelDescriptionType].Name</span></td></tr><tr><td colspan="1"><span>-&gt;paragraphs</span></td><td colspan="1"><span>hotel_data.descriptions.description</span></td></tr><tr><td><span>facts</span></td><td><span>hotel_data.facts</span></td></tr><tr><td colspan="1"><span>-&gt;yearBuilt</span></td><td colspan="1"><span>hotel_data.facts.yearBuilt</span></td></tr><tr><td colspan="1"><span>-&gt;electricity</span></td><td colspan="1"><span>hotel_data.facts.electricity</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;sockets</span></td><td colspan="1"><p><span><span>Все выбранные значения из hotel_data.facts.electricity.sockets</span></span></p><p><span>Маппинг описан в <span>п 2.g</span></span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;voltage</span></td><td colspan="1"><span>Все выбранные значения из hotel_data.facts.electricity.voltage</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;frequency</span></td><td colspan="1"><span>Все выбранные значения из hotel_data.facts.electricity.frequency</span></td></tr><tr><td colspan="1"><span>-&gt;roomsNumber</span></td><td colspan="1"><span>hotel_data.facts.roomsCount</span></td></tr><tr><td colspan="1"><span>-&gt;floorsNumber</span></td><td colspan="1"><span>hotel_data.facts.floorsCount</span></td></tr><tr><td colspan="1"><span>-&gt;yearRenovated</span></td><td colspan="1"><span>hotel_data.facts.yearRenovated</span></td></tr><tr><td><span>amenityGroups</span></td><td><p><span><span>Все выбранные значения из hotel_data.facilities</span></span></p><p><span><span>Маппинг описан в п 2.f</span></span></p></td></tr><tr><td colspan="1"><span>-&gt;amenities</span></td><td colspan="1"><span>[CMS]..[Facility].Name</span></td></tr><tr><td colspan="1"><span>-&gt;groupName</span></td><td colspan="1"><span>[CMS]..[FacilityCategory].Name</span></td></tr><tr><td><span>metapolicyExtraInfo</span></td><td><p><span>hotel_data.r<span>ulesExtraInfo</span></span></p></td></tr><tr><td colspan="1"><span>metapolicyExtraInfoEn</span></td><td colspan="1"><p><span>hotel_data.rulesExtraInfoEn</span></p></td></tr><tr><td colspan="1"><span>metapolicy</span></td><td colspan="1"><span>hotel_data.metaPolicy</span></td></tr><tr><td colspan="1"><span>-&gt;childrenBed</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;amount</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed.amount</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.childrenBed.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><p><span>Маппинг по в зависимости от hotel_data.metaPolicy.cot.inclusion</span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.cot.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span><span>Маппинг по в зависимости hotel_data.metaPolicy.cot.</span>priceUnitId</span></td></tr><tr><td colspan="1"><span>-&gt;meal</span></td><td colspan="1"><span>hotel_data.metaPolicy.meal</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.meal.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.meal.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;mealType</span></td><td colspan="1"><p><span>Все выбранные значения из hotel_data.metaPolicy.meal.m<span>ealTypeId</span></span></p><p><span>Маппинг описан в п 2.g</span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;mealName</span></td><td colspan="1"><p><span>Значение [CNS]..[MealType].Name для выбранных hotel_data.metaPolicy.meal.m<span>ealTypeId</span></span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.meal.price</span></td></tr><tr><td colspan="1"><span>-&gt;pets</span></td><td colspan="1"><span>hotel_data.metaPolicy.pets</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span><span>Маппинг по в зависимости от hotel_data.metaPolicy.pets.currencyTypeId</span></span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.pets.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;petsType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.pets.petsType</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.pets.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span><span>Маппинг по в зависимости hotel_data.metaPolicy.pets.</span><u>priceUnit</u></span></td></tr><tr><td colspan="1"><span>-&gt;visa</span></td><td colspan="1"><br/></td></tr><tr><td colspan="1"><span>-&gt;-&gt;visaSupport</span></td><td colspan="1"><p><span>&#34;true&#34; если hotel_data.visaSupport = 1</span></p><p><span>&#34;false&#34; если hotel_data.visaSupport = 0</span></p></td></tr><tr><td colspan="1"><span>-&gt;addFee</span></td><td colspan="1"><span>hotel_data.metaPolicy.addFee</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span><span>Маппинг по в зависимости от hotel_data.metaPolicy.addFee.c</span>urrencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;feeType</span></td><td colspan="1"><span>Маппинг по в зависимости от  hotel_data.metaPolicy.addFee.feeTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span> hotel_data.metaPolicy.addFee.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span>Маппинг по в зависимости  hotel_data.metaPolicy.addFee.priceUnitId</span></td></tr><tr><td colspan="1"><span>-&gt;deposit</span></td><td colspan="1"><span><span>hotel_data.metaPolicy.deposit</span></span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;availability</span></td><td colspan="1"><p><span>&#34;true&#34; если hotel_data.metaPolicy.deposit.IsAvailable = 1</span></p><p><span>&#34;false&#34; если hotel_data.metaPolicy.deposit.IsAvailable = 0</span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.deposit.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;depositType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.deposit.depositType</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;paymentType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.deposit.paymentType</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.deposit.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span>Маппинг по в зависимости hotel_data.metaPolicy.deposit.priceUnitID </span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;pricingMethod</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.deposit.pricingMethod</span></td></tr><tr><td colspan="1"><span>-&gt;noShow</span></td><td colspan="1"><span><span>hotel_data.metaPolicy</span>.<span>noShow</span></span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;time</span></td><td colspan="1"><span>hotel_data.metaPolicy.noShow.NoShowTime</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;dayPeriod</span></td><td colspan="1"><span>Маппинг по в зависимости от [TravelDB]..[HotelDetails].NoShowDayPeriod</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;availability</span></td><td colspan="1"><p><span>&#34;true&#34; если hotel_data.metaPolicy.noShow.noShowIsAvailable = 1</span></p><p><span>&#34;false&#34; если hotel_data.metaPolicy.noShow</span>.<span>noShowIsAvailable = 0</span></p></td></tr><tr><td colspan="1"><span>-&gt;parking</span></td><td colspan="1"><span><span>hotel_data.metaPolicy</span>.<span>parking</span></span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.parking.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.parking.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.parking.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span>Маппинг по в зависимости hotel_data.metaPolicy.parking.priceUnitId </span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;territoryType</span></td><td colspan="1"><span>Маппинг по словарю в зависимости от  hotel_data.metaPolicy.parking.territoryType</span></td></tr><tr><td colspan="1"><span>-&gt;shuttle</span></td><td colspan="1"><span>hotel_data.metaPolicy.shuttle</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.shuttle.currencyTypeID</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.shuttle.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;destinationType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.shuttle.destinationType</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.shuttle.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;shuttleType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.shuttle.shuttleType</span></td></tr><tr><td colspan="1"><span>-&gt;childrenExtraBed</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;ageEnd</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed.ageEnd</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;ageStart</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed.ageStart</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.childrenBed.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;extraBed</span></td><td colspan="1"><p><span>&#34;true&#34; если hotel_data.metaPolicy.childrenBed.isExtraBedAvailable = 1</span></p><p><span>&#34;false&#34; если hotel_data.metaPolicy.childrenBed.isExtraBedAvailable = 0</span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenBed.price</span></td></tr><tr><td colspan="1"><span>-&gt;internet</span></td><td colspan="1"><span>hotel_data.metaPolicy.internet</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от [hotel_data.metaPolicy.internet.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.internet.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;internetType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.internet.internetType</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.internet.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span>Маппинг по в зависимости hotel_data.metaPolicy.internet.priceUnitId </span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;workArea</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.internet.workArea</span></td></tr><tr><td colspan="1"><span>-&gt;extraBed</span></td><td colspan="1"><span><span>hotel_data.metaPolicy.extraBed</span></span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;amount</span></td><td colspan="1"><span><span><span>hotel_data.metaPolicy.extraBed</span></span>.amount</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.extraBed.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.extraBed.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.extraBed.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;priceUnit</span></td><td colspan="1"><span>Маппинг по в зависимости hotel_data.metaPolicy.extraBed.priceUnitId</span></td></tr><tr><td colspan="1"><span>-&gt;childrenMeal</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenMeal</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenMeal.price</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;ageEnd</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenMeal.ageEnd</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;ageStart</span></td><td colspan="1"><span>hotel_data.metaPolicy.childrenMeal.ageStart</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.childrenMeal.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.childrenMeal.inclusion</span></td></tr><tr><td colspan="1"><p><span>-&gt;-&gt;mealType</span></p></td><td colspan="1"><p><span>Значение [CMS]..[MealType].Code для выбранных  hotel_data.metaPolicy.childrenMeal.mealTypeId</span></p><p><span>&#34;unspecified&#34; если [MealType].code = null</span></p></td></tr><tr><td colspan="1"><span>-&gt;checkInCheckOut</span></td><td colspan="1"><span>hotel_data.metaPolicy.checkInCheckOut</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;currency</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.checkInCheckOut.currencyTypeId</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;checkInCheckOutType</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.checkInCheckOut.checkInCheckOutTypeID</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;inclusion</span></td><td colspan="1"><span>Маппинг по в зависимости от hotel_data.metaPolicy.checkInCheckOut.inclusion</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;price</span></td><td colspan="1"><span>hotel_data.metaPolicy.checkInCheckOut.price</span></td></tr><tr><td><span>paymentMethods</span></td><td><span><span>Все выбранные значения с маппингом по в зависимости от hotel_data.paymentMethods в</span></span><span> объединенные в список</span></td></tr><tr><td><span>location</span></td><td><span>location_data</span></td></tr><tr><td colspan="1"><span>-&gt;masterLocationId</span></td><td colspan="1"><span>hotel_data.masterLocationId</span></td></tr><tr><td colspan="1"><span>-&gt;name</span></td><td colspan="1"><span>location_data.name</span></td></tr><tr><td colspan="1"><span>-&gt;type</span></td><td colspan="1"><p><span>Принимает следующие значения в зависимости от location_data.type</span></p><table><tbody><tr><th><span>LocationType</span></th><th><span>type</span></th></tr><tr><td><span>1</span></td><td><span>Continent</span></td></tr><tr><td><span>2</span></td><td><span>Country</span></td></tr><tr><td><span>3</span></td><td><span>Province (State)</span></td></tr><tr><td><span>5</span></td><td><span>City</span></td></tr><tr><td><span>6</span></td><td><span>Airport</span></td></tr><tr><td><span>7</span></td><td><span>Railway Station</span></td></tr><tr><td><span>9</span></td><td><span>Point of Interest</span></td></tr><tr><td><span>10</span></td><td><span>Multi-Region (within a country)</span></td></tr><tr><td><span>11</span></td><td><span>Street</span></td></tr><tr><td><span>12</span></td><td><span>Subway (Entrance)</span></td></tr><tr><td><span>13</span></td><td><span>Neighborhood</span></td></tr><tr><td><span>14</span></td><td><span>Bus Station</span></td></tr><tr><td><span>15</span></td><td><span>Multi-City (Vicinity)</span></td></tr></tbody></table><p><br/></p></td></tr><tr><td colspan="1"><span>-&gt;countryCode</span></td><td colspan="1"><span>location_data.code для страны, в которой находится локация, в которой находится master-отель с HotelId</span></td></tr><tr><td><span>policy</span></td><td><span>Всегда пустое.</span></td></tr><tr><td colspan="1"><span>apartmentFacts</span></td><td colspan="1"><div><p><span>hotel_data.apartmentFacts</span></p><p><span>Объект с атрибутами, характерными для квартиры (Апартамент с признаком IsFlat: true. Логика расчета признака описана <a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8345571527">здесь</a>)</span></p><p><span>Заполняется <strong>только</strong> если Hotel.IsFlat == true.</span></p><p><span>Некоторые атрибуты сохраняются из таблицы Room.</span></p><p><span>В случае, если в результате получения данных о комнатах объекта размещения было найдено несколько комнат, объект apartmentFacts <strong>не формируется вообще</strong></span></p><p><span><strong>Сейчас</strong> не должно быть ситуации, когда у квартиры есть несколько комнат. Однако это может измениться впоследствии и нужно здесь изменить логику формирования apartmentFacts</span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>-&gt;isFlat</span></td><td colspan="1"><span>hotel_data.apartmentFacts.isFlat</span></td></tr><tr><td colspan="1"><p><span>-&gt;roomsCount</span></p></td><td colspan="1"><span>hotel_data.apartmentFacts.rooms[0].bedroomCount</span></td></tr><tr><td colspan="1"><p><span>-&gt;roomSize</span></p></td><td colspan="1"><span>hotel_data.apartmentFacts.rooms[0].size</span></td></tr><tr><td colspan="1"><span>-&gt;currentFloor</span></td><td colspan="1"><span>hotel_data.apartmentFacts.rooms[0].floorNumber</span></td></tr><tr><td colspan="1"><span>-&gt;guestsCount</span></td><td colspan="1"><span>hotel_data.apartmentFacts.rooms[0].maxGuestsCount</span></td></tr><tr><td colspan="1"><span>-&gt;contactlessCheckin</span></td><td colspan="1"><span><span>hotel_data.apartmentFacts.c</span>ontactlessCheckin</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;isContactless</span></td><td colspan="1"><span>hotel_data.apartmentFacts.contactlessCheckin[0].isContactless</span></td></tr><tr><td colspan="1"><span>-&gt;-&gt;keysPickupType</span></td><td colspan="1"><p><span>Маппинг по в зависимости от hotel_data.apartmentFacts.contactlessCheckin[0].contactlessCheckinTypeID</span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;keysPickupPhone</span></td><td colspan="1"><span>hotel_data.apartmentFacts.contactlessCheckin[0].phone</span></td></tr><tr><td colspan="1"><span>-&gt;bedConfigurations</span></td><td colspan="1"><p><span>hotel_data.apartmentFacts.rooms[0].b<span>edConfigurations</span></span></p><p><span>Описание экземпляров RoomBedConfiguration, для которых RoomBedConfiguration.<span>RoomId == Room.RoomId, отсортированные по RoomBedConfiguration.ConfigurationNumber по возрастанию</span></span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;bedTypeId</span></td><td colspan="1"><p><span>hotel_data.apartmentFacts.rooms[0].b<span>edConfigurations.b</span></span><span>edTypeId</span></p><p><span>Описание экземпляров <span>RoomBed.BedTypeId, входящих в RoomBedConfiguration, отсортированные по RoomBed.BedNumber по возрастанию</span></span></p></td></tr><tr><td colspan="1"><span>-&gt;-&gt;isExtraBed</span></td><td colspan="1"><span>hotel_data.apartmentFacts.rooms[0].b<span>edConfigurations.isExtraBed</span></span></td></tr><tr><td colspan="1"><span>-&gt;roomFacilities</span></td><td colspan="1"><span>Массив значений hotel_data.apartmentFacts.rooms[0].facilityId экземпляров RoomFacility, для которых RoomFacility.RoomId == Room.RoomId</span></td></tr></tbody></table>
03. Вызывается хранимая процедура \[HotelStaticApi\_GetHotelListStaticDetails] в TravelDB. В качестве аргумента функции @HotelID передается параметр из запроса метода masterHotelId  
    Выполняется выборка из таблицы TravelDB.HotelDetails в которой находится информация о деталях отеля  
    и выполняется операция объединения данных с таблицей TravelDB.Hotel по HotelDetails.HotelId = Hotel.HotelId;  
    и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.PrimaryLocationId;  
    и выполняется операция объединения данных с таблицей TravelDB.Location по Location.LocationId = HotelDetails.CountryId;  
    и выполняется операция объединения данных с таблицей TravelDB.HotelChain по HotelChain.HotelChainId = HotelDetails.HotelChainId;  
    и выполняется операция объединения данных с таблицей TravelDB.HotelPhone по HotelPhone.HotelId = HotelDetails.HotelId и фильтруется по HotelPhone.PhoneTypeID = 1 и HotelPhone.IsDefault=1;  
    Данные выбираются только для HotelDetails.BrandId = 0.
04. Если в предыдущем пункте по отелю в данных присутствует признак isFlat=true, параллельно дальнейшему сбору информации по отелю необходимо запустить процесс получения статики по этой комнате:
    
    1. Выборка экземпляров Room, для которых Room.HotelId == hotelId.
    2. Также выполняется операция объединения данных с таблицей TravelDB.RoomFacility по RoomFacility.RoomId = Room.RoomId;
    3. Также выполняется операция объединения данных с таблицей TravelDB.RoomBedConfiguration по RoomBedConfiguration.RoomId = Room.RoomId, отсортированные по RoomBedConfiguration.ConfigurationNumber по возрастанию;
    4. Также выполняется операция объединения данных с таблицей TravelDB.RoomBed по RoomBed.RoomBedConfigurationId = RoomBedConfiguration.RoomBedConfigurationId, отсортированные по RoomBed.BedNumber по возрастанию
05. Выборка данных из таблицы TravelDB..HotelImages для которых HotelId = @HotelID. Выбираются адреса картинок для master-отеля и сортируются по TravelDB..HotelImages.IsDefault (основная фотография отеля становится первой) и по TravelDB..HotelImages.Position (остальные фотографии располагаются в соответствие с установленным порядком).
06. Выборка данных из таблицы TravelDB..HotelDescription для которых HotelId = @HotelID. Выбираются описания для master-отеля HotelId = @HotelID с параметром BrandId = 0   
    и выполняется операция объединения данных с таблицей \[TravelDB]..\[HotelDescriptionType] в которой находятся типы описания отеля по HotelDescriptionType.HotelDescriptionTypeID = HotelDescription.HotelDescriptionTypeID  
    и выполняется сортировка по HotelDescriptionType.Position (приоритет типа описания), HotelDescription.IsDefault (основное описание отеля) в порядке уменьшения, HotelDescription.Position (приоритет описания), HotelDescription.HotelDescriptionID в порядке увеличения. Используем данные по \[TravelDB]..\[HotelDescriptionType].HotelDescriptionTypeID: 4, 5, 7, 10-15.  В ответе передаем title и paragraph для всех HotelDescriptionType, кроме DescriptionTypeId = 7 (Описание отеля), для него передаем значение в paragraph, и title=null. Отбираем только те записи, в которых \[TravelDB]..\[HotelDescription].Description!=null 
    
    1. Если Description содержит спец сивмолы \\r\\n или просто \\r, то дополнительно разбивать значение на несколько отдельных элементов.
07. Выборка данных из таблицы TravelDB..HotelSocketType в которой находятся связи между отелями и их типами разъемов для которых HotelId = @HotelID,  
    и выполняется операция объединения данных с таблицей TravelDB..SocketType в которой находится словарь типов разъемов по SocketType.SocketTypeID=HotelSocketType.SocketTypeID  
    и выполняется сортировка по SocketType.Code (код разъема) в порядке увеличения.
08. Выборка данных из таблицы TravelDB..HotelElectricityVoltage в которой находятся отели с соответствующими им напряжениями для которых HotelId = @HotelID.
09. Выборка данных из таблицы TravelDB..HotelElectricityFrequency в которой находятся отели с соответствующими им частотами для которых HotelId = @HotelID.
10. Выборка данных из таблицы TravelDB..HotelCot в которой находятся отели с соответствующими им дополнительными услугами относящимися к детским кроватям для которых HotelId = @HotelID.
11. Выборка данных из таблицы TravelDB..HotelMeal в которой находятся отели с соответствующими им типами питания для которых HotelId = @HotelID,  
    и выполняется операция объединения данных с таблицей  TravelDB..MealType в которой находится словарь типов питания, их названия и коды по MealType.MealTypeID=HotelMeal.MealTypeID.
12. Выборка данных из таблицы TravelDB..HotelPet в которой находятся отели с соответствующими им дополнительными услугами, относящимися к проживанию с животными для которых HotelId = @HotelID.
13. Выборка данных из таблицы TravelDB..HotelAddFee в которой находятся отели с соответствующими им дополнительными платежами для которых HotelId = @HotelID.
14. Выборка данных из таблицы TravelDB..HotelDeposit в которой находятся отели с соответствующими им депозитами для которых HotelId = @HotelID.
15. Выборка данных из таблицы TravelDB..HotelParking в которой находятся отели с соответствующими им типами доступных парковок для которых HotelId = @HotelID.
16. Выборка данных из таблицы TravelDB..HotelShuttle в которой находятся отели с соответствующими им типами доступного трансфера для которых HotelId = @HotelID.
17. Выборка данных из таблицы TravelDB..HotelChildrenBed в которой находятся отели с соответствующими им доступными дополнительными детскими кроватями для которых HotelId = @HotelID.
18. Выборка данных из таблицы TravelDB..HotelInternet в которой находятся отели с соответствующими им услугам по доступу в интернет для которых HotelId = @HotelID.
19. Выборка данных из таблицы TravelDB..HotelExtraBed в которой находятся отели с соответствующими им дополнительными кроватями для взрослых для которых HotelId = @HotelID.
20. Выборка данных из таблицы TravelDB..HotelChildrenMeal в которой находятся отели с соответствующими им типами питания для которых HotelId = @HotelID,  
    и выполняется операция объединения данных с таблицей TravelDB..MealType в которой находится словарь типов питания и их кодов по MealType.MealTypeID=HotelMeal.MealTypeID.
21. Выборка данных из таблицы TravelDB..HotelCheckInCheckOutType в которой находятся отели с соответствующими им условиями заезда и выезда из отеля для которых HotelId = @HotelID.
22. Выборка данных из таблицы TravelDB..HotelPaymentMethod в которой находятся отели с соответствующими им способами оплаты в отеле для которых HotelId = @HotelID.
23. Формируется ответ вызывающей стороне в соответствии с алгоритмом
24. Сценарий завершен

## SC-1.1 Формирование ответа

1. Формируется структура HotelInfoApiResponseListPayloadApiResponse в соответствии с маппингом:
   
   <table><colgroup><col/><col/></colgroup><tbody><tr><th><p>Параметр</p></th><th colspan="1">Источник данных</th></tr><tr><td>masterHotelId</td><td colspan="1">[TravelDB]..[HotelDetails].HotelId</td></tr><tr><td>isClosed</td><td colspan="1"><p>Если [TravelDB]..[HotelDetails].IsActive = 1, тогда false</p><p>Если [TravelDB]..[HotelDetails].IsActive = 0, тогда true</p></td></tr><tr><td colspan="1">deleted</td><td colspan="1">Всегда false</td></tr><tr><td colspan="1">name</td><td colspan="1">[TravelDB]..[HotelDetails].HotelName</td></tr><tr><td colspan="1">nameEn</td><td colspan="1">[TravelDB]..[HotelTranslation].Name (where LanguageID=1)</td></tr><tr><td colspan="1">hotelChain</td><td colspan="1">[TravelDB]..[HotelChain].NameRu для [TravelDB]..[HotelDetails].HotelChainID</td></tr><tr><td colspan="1">starRating</td><td colspan="1">[TravelDB]..[HotelDetails].StarRating</td></tr><tr><td colspan="1">images</td><td colspan="1">Значения всех [TravelDB]..[HotelImages].ImagePath для выбранного master-отеля, объединенных в массив</td></tr><tr><td colspan="1">address</td><td colspan="1"><div><p>[TravelDB]..[HotelDetails].HotelAddress</p></div></td></tr><tr><td colspan="1">addressEn</td><td colspan="1">[TravelDB]..[HotelTranslation].Address (where LanguageID=1)</td></tr><tr><td colspan="1">masterLocationId</td><td colspan="1">[TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">kind</td><td colspan="1"><p>В зависимости от [TravelDB]..[HotelDetails].HotelCategory (мапится по таблице )</p><ul><li><span>Если HotelCategory = 20, то мапится на HotelCategoryId  = 0, Kind = HotelCategoryName = Resort</span></li><li><span>Если HotelCategory = 40, то мапится на HotelCategoryId  = 1, Kind = HotelCategoryName = Sanatorium</span></li><li><span>Если HotelCategory = 13, то мапится на HotelCategoryId  = 2, Kind = HotelCategoryName = Guesthouse</span></li><li><span>Если HotelCategory = 26, то мапится на HotelCategoryId  = 3, Kind = HotelCategoryName = MiniHotel</span></li><li><span>Если HotelCategory = 10, то мапится на HotelCategoryId  = 4, Kind = HotelCategoryName = Castle</span></li><li><span>Если HotelCategory = 1, то мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li><li><span>Если HotelCategory = 3, то мапится на HotelCategoryId  = 7, Kind = HotelCategoryName = Apartment</span></li><li><span>Если HotelCategory = 11, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 14, то мапится на HotelCategoryId  = 8, Kind = HotelCategoryName = CottagesAndHouses</span></li><li><span>Если HotelCategory = 12, то мапится на HotelCategoryId  = 9, Kind = HotelCategoryName = Farm</span></li><li><span>Если HotelCategory = 8, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 25, то мапится на HotelCategoryId  = 10, Kind = HotelCategoryName = VillasAndBungalows</span></li><li><span>Если HotelCategory = 9, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 22, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping</span></li><li><span>Если HotelCategory = 4, то мапится на HotelCategoryId  = 12, Kind = HotelCategoryName = Hostel</span></li><li><span>Если HotelCategory = 6, то мапится на HotelCategoryId  = 13, Kind = HotelCategoryName = Bnb</span></li><li><span>Если HotelCategory = 2, то мапится на HotelCategoryId  = 14, Kind = HotelCategoryName = ApartHotel</span></li><li><span>Если HotelCategory = 42, то мапится на HotelCategoryId  = 6, Kind = HotelCategoryName = BoutiqueAndDesign</span></li><li><span>Если HotelCategory = 43, то мапится на HotelCategoryId  = 11, Kind = HotelCategoryName = Camping<br/></span></li><li><span>Если HotelCategory = 44, то мапится на HotelCategoryId  = 15, Kind = HotelCategoryName = Glamping</span></li><li><span>В противном случае мапится на HotelCategoryId  = 5, Kind = HotelCategoryName = Hotel</span></li></ul></td></tr><tr><td colspan="1">coordinates</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;latitude</td><td colspan="1">[TravelDB]..[HotelDetails].latitude</td></tr><tr><td colspan="1">-&gt;longitude</td><td colspan="1">[TravelDB]..[HotelDetails].longitude</td></tr><tr><td colspan="1">ianaTimeZone</td><td colspan="1">[TravelDB]..[Location].TimeZoneName для [TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">checkInTime</td><td colspan="1">[TravelDB]..[HotelDetails].CheckInTime</td></tr><tr><td>checkOutTime</td><td>[TravelDB]..[HotelDetails].CheckOutTime</td></tr><tr><td>phone</td><td>[TravelDB]..[HotelPhone].Number</td></tr><tr><td>email</td><td>[TravelDB]..[HotelDetails].Email</td></tr><tr><td>description</td><td><p>Массив объектов выбранных описаний, сгруппированных по [TravelDB]..[HotelDescriptionType].Name</p></td></tr><tr><td colspan="1">-&gt;title</td><td colspan="1">[TravelDB]..[HotelDescriptionType].Name</td></tr><tr><td colspan="1">-&gt;paragraphs</td><td colspan="1">[TravelDB]..[HotelDescription].Description</td></tr><tr><td>facts</td><td><br/></td></tr><tr><td colspan="1">-&gt;yearBuilt</td><td colspan="1">[TravelDB]..[HotelDetails].YearOpened</td></tr><tr><td colspan="1">-&gt;electricity</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;sockets</td><td colspan="1">Все выбранные значения [TravelDB]..[SocketType].Name, объединенные в список</td></tr><tr><td colspan="1">-&gt;-&gt;voltage</td><td colspan="1">Все выбранные значения [TravelDB]..[HotelElectricityVoltage].Voltage, объединенные в список</td></tr><tr><td colspan="1">-&gt;-&gt;frequency</td><td colspan="1">Все выбранные значения [TravelDB]..[HotelElectricityFrequency].Frequency, объединенные в список</td></tr><tr><td colspan="1">-&gt;roomsNumber</td><td colspan="1">[TravelDB]..[HotelDetails].FactRoomsCount</td></tr><tr><td colspan="1">-&gt;floorsNumber</td><td colspan="1">[TravelDB]..[HotelDetails].FactFloorsCount</td></tr><tr><td colspan="1">-&gt;yearRenovated</td><td colspan="1">[TravelDB]..[HotelDetails].YearRenovated</td></tr><tr><td>amenityGroups</td><td><br/></td></tr><tr><td colspan="1">-&gt;amenities</td><td colspan="1">[TravelDB]..[Facility].Name</td></tr><tr><td colspan="1">-&gt;groupName</td><td colspan="1">[TravelDB]..[FacilityCategory].Name</td></tr><tr><td>metapolicyExtraInfo</td><td><p>[TravelDB]..[HotelDetails].RulesExtraInfo<span> </span></p></td></tr><tr><td colspan="1">metapolicyExtraInfoEn</td><td colspan="1"><p>[TravelDB]..<span>[HotelTranslation].RulesExtraInfo</span></p></td></tr><tr><td colspan="1">metapolicy</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;childrenBed</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;amount</td><td colspan="1">[TravelDB]..[HotelCot].Amount</td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelCot].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1"><p>Маппинг по в зависимости от [TravelDB]..[HotelCot].Inclusion</p></td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelCot].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelCot].PriceUnitID </td></tr><tr><td colspan="1">-&gt;meal</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelMeal].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelMeal].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;mealType</td><td colspan="1"><p>Значение [TravelDB]..[MealType].Code для выбранных  [TravelDB]..[HotelMeal].MealTypeID</p><p>&#34;unspecified&#34; если [MealType].code = null</p></td></tr><tr><td colspan="1">-&gt;-&gt;mealName</td><td colspan="1"><p>Значение [TravelDB]..[MealType].Name для выбранных  [TravelDB]..[HotelMeal].MealTypeID</p></td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelMeal].Price</td></tr><tr><td colspan="1">-&gt;pets</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelPet].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelPet].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;petsType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelPet].PetsType</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelPet].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelPet].PriceUnitID </td></tr><tr><td colspan="1">-&gt;visa</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;visaSupport</td><td colspan="1"><p>&#34;true&#34; если [TravelDB]..[HotelDetails].VisaSupport = 1</p><p>&#34;false&#34; если [TravelDB]..[HotelDetails].VisaSupport = 0</p></td></tr><tr><td colspan="1">-&gt;addFee</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelAddFee].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;feeType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelAddFee].FeeTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelAddFee].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelAddFee].PriceUnitID </td></tr><tr><td colspan="1">-&gt;deposit</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;availability</td><td colspan="1"><p>&#34;true&#34; если [TravelDB]..[HotelDeposit].IsAvailable = 1</p><p>&#34;false&#34; если [TravelDB]..[HotelDeposit].IsAvailable = 0</p></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelDeposit].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;depositType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelDeposit].DepositType</td></tr><tr><td colspan="1">-&gt;-&gt;paymentType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelDeposit].PaymentType</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelDeposit].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelDeposit].PriceUnitID </td></tr><tr><td colspan="1">-&gt;-&gt;pricingMethod</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelDeposit].PricingMethod</td></tr><tr><td colspan="1">-&gt;noShow</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;time</td><td colspan="1">[TravelDB]..[HotelDetails].NoShowTime</td></tr><tr><td colspan="1">-&gt;-&gt;dayPeriod</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelDetails].NoShowDayPeriod</td></tr><tr><td colspan="1">-&gt;-&gt;availability</td><td colspan="1"><p><span>&#34;true&#34; если [TravelDB]..[HotelDetails].NoShowIsAvailable = 1</span></p><p>&#34;false&#34; если [TravelDB]..[HotelDetails].NoShowIsAvailable = 0</p></td></tr><tr><td colspan="1">-&gt;parking</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelParking].Price</td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelParking].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelParking].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelParking].PriceUnitID </td></tr><tr><td colspan="1">-&gt;-&gt;territoryType</td><td colspan="1">Маппинг по словарю в зависимости от [TravelDB]..[HotelParking].TerritoryType</td></tr><tr><td colspan="1">-&gt;shuttle</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelShuttle].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelShuttle].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;destinationType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelShuttle].DestinationType</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelParking].Price</td></tr><tr><td colspan="1">-&gt;-&gt;shuttleType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelShuttle].ShuttleType</td></tr><tr><td colspan="1">-&gt;childrenExtraBed</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;ageEnd</td><td colspan="1">[TravelDB]..[HotelChildrenBed].AgeEnd</td></tr><tr><td colspan="1">-&gt;-&gt;ageStart</td><td colspan="1">[TravelDB]..[HotelChildrenBed].AgeStart</td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelChildrenBed].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;extraBed</td><td colspan="1"><p>&#34;true&#34; если [TravelDB]..[HotelChildrenBed].IsExtraBedAvailable = 1</p><p>&#34;false&#34; если [TravelDB]..[HotelChildrenBed].IsExtraBedAvailable = 0</p></td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelChildrenBed].Price</td></tr><tr><td colspan="1">-&gt;internet</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelInternet].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelInternet].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;internetType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelInternet].InternetType</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelInternet].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelInternet].PriceUnitID </td></tr><tr><td colspan="1">-&gt;-&gt;workArea</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelInternet].WorkArea</td></tr><tr><td colspan="1">-&gt;extraBed</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;amount</td><td colspan="1">[TravelDB]..[HotelExtraBed].Amount</td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelExtraBed].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelExtraBed].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelExtraBed].Price</td></tr><tr><td colspan="1">-&gt;-&gt;priceUnit</td><td colspan="1">Маппинг по в зависимости [TravelDB]..[HotelExtraBed].PriceUnitID </td></tr><tr><td colspan="1">-&gt;childrenMeal</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelChildrenMeal].Price</td></tr><tr><td colspan="1">-&gt;-&gt;ageEnd</td><td colspan="1">[TravelDB]..[HotelChildrenMeal].AgeEnd</td></tr><tr><td colspan="1">-&gt;-&gt;ageStart</td><td colspan="1">[TravelDB]..[HotelChildrenMeal].AgeStart</td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelChildrenMeal].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelChildrenMeal].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;mealType</td><td colspan="1"><p>Значение [TravelDB]..[MealType].Code для выбранных  [TravelDB]..[HotelChildrenMeal].MealTypeID</p><p>&#34;unspecified&#34; если [MealType].code = null</p></td></tr><tr><td colspan="1">-&gt;checkInCheckOut</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;currency</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelCheckInCheckOutType].CurrencyTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;checkInCheckOutType</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelCheckInCheckOutType].CheckInCheckOutTypeID</td></tr><tr><td colspan="1">-&gt;-&gt;inclusion</td><td colspan="1">Маппинг по в зависимости от [TravelDB]..[HotelCheckInCheckOutType].Inclusion</td></tr><tr><td colspan="1">-&gt;-&gt;price</td><td colspan="1">[TravelDB]..[HotelCheckInCheckOutType].Price</td></tr><tr><td>paymentMethods</td><td><span>Все выбранные значения с маппингом по в зависимости от [TravelDB]..[HotelPaymentMethod].PaymentMethod, , объединенные в список</span></td></tr><tr><td>location</td><td><br/></td></tr><tr><td colspan="1">-&gt;masterLocationId</td><td colspan="1">[TravelDB]..[HotelDetails].PrimaryLocationID</td></tr><tr><td colspan="1">-&gt;name</td><td colspan="1">[TravelDB]..[HotelDetails].LocationName</td></tr><tr><td colspan="1">-&gt;type</td><td colspan="1"><p>Принимает следующие значения в зависимости от [TravelDB]..[Location].LocationType </p><table><tbody><tr><th>LocationType</th><th>type</th></tr><tr><td>1</td><td><span>Continent</span></td></tr><tr><td>2</td><td><span>Country</span></td></tr><tr><td>3</td><td><span>Province (State)</span></td></tr><tr><td>5</td><td><span>City</span></td></tr><tr><td>6</td><td><span>Airport</span></td></tr><tr><td>7</td><td><span>Railway Station</span></td></tr><tr><td>9</td><td><span>Point of Interest</span></td></tr><tr><td>10</td><td><span>Multi-Region (within a country)</span></td></tr><tr><td>11</td><td><span>Street</span></td></tr><tr><td>12</td><td><span>Subway (Entrance)</span></td></tr><tr><td>13</td><td><span>Neighborhood</span></td></tr><tr><td>14</td><td><span>Bus Station</span></td></tr><tr><td>15</td><td><span>Multi-City (Vicinity)</span></td></tr></tbody></table><p><br/></p></td></tr><tr><td colspan="1">-&gt;countryCode</td><td colspan="1">[TravelDB]..[Location].Code для страны, в которой находится локация, в которой находится master-отель с HotelId</td></tr><tr><td>policy</td><td>Всегда пустое.</td></tr><tr><td colspan="1">apartmentFacts</td><td colspan="1"><div><p>Объект с атрибутами, характерными для квартиры (Апартамент с признаком IsFlat: true. Логика расчета признака описана <a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8345571527">здесь</a>)</p><p>Заполняется <strong>только</strong> если Hotel.IsFlat == true.</p><p>Некоторые атрибуты сохраняются из таблицы Room.</p><p>В случае, если в результате получения данных о комнатах объекта размещения было найдено несколько комнат, объект apartmentFacts <strong>не формируется вообще</strong></p><p><strong>Сейчас</strong> не должно быть ситуации, когда у квартиры есть несколько комнат. Однако это может измениться впоследствии и нужно здесь изменить логику формирования apartmentFacts</p><p><br/></p></div></td></tr><tr><td colspan="1">-&gt;isFlat</td><td colspan="1">[TravelDB]..[Hotel].IsFlat</td></tr><tr><td colspan="1"><p>-&gt;roomsCount</p></td><td colspan="1">[TravelDB]..[Room].BedroomCount</td></tr><tr><td colspan="1"><p>-&gt;roomSize</p></td><td colspan="1">[TravelDB]..[Room].Size</td></tr><tr><td colspan="1">-&gt;currentFloor</td><td colspan="1">[TravelDB]..[Room].FloorNumber</td></tr><tr><td colspan="1">-&gt;guestsCount</td><td colspan="1">[TravelDB]..[Room].MaxGuestsCount</td></tr><tr><td colspan="1">-&gt;contactlessCheckin</td><td colspan="1"><br/></td></tr><tr><td colspan="1">-&gt;-&gt;isContactless</td><td colspan="1">[TravelDB]..[HotelContactlessCheckin].IsContactless</td></tr><tr><td colspan="1">-&gt;-&gt;keysPickupType</td><td colspan="1"><p>Маппинг по в зависимости от [TravelDB]..[HotelContactlessCheckin].ContactlessCheckinTypeID</p></td></tr><tr><td colspan="1">-&gt;-&gt;keysPickupPhone</td><td colspan="1">[TravelDB]..[HotelContactlessCheckin].Phone</td></tr><tr><td colspan="1">-&gt;bedConfigurations</td><td colspan="1">Описание экземпляров RoomBedConfiguration, для которых RoomBedConfiguration.<span>RoomId == Room.RoomId, отсортированные по RoomBedConfiguration.ConfigurationNumber по возрастанию</span></td></tr><tr><td colspan="1">-&gt;-&gt;bedTypeId</td><td colspan="1"><p>Описание экземпляров <span>RoomBed.BedTypeId, входящих в RoomBedConfiguration, отсортированные по RoomBed.BedNumber по возрастанию</span></p></td></tr><tr><td colspan="1">-&gt;-&gt;isExtraBed</td><td colspan="1">RoomBed.IsExtraBed</td></tr><tr><td colspan="1">-&gt;roomFacilities</td><td colspan="1">Массив значений RoomFacility.FacilityId экземпляров RoomFacility, для которых RoomFacility.RoomId == Room.RoomId</td></tr></tbody></table>
2. Проверяется значение поля \[TravelDB]..\[Hotel].CertificationNeeded :
   
   1. Если значение true, то производится маппинг данных на таблицу (PostgreSQL) travel\_hotels\_static.rosreestr\_hotel\_mappings HotelId = master\_hotel\_id и выборка данных из таблицы (PostgreSQL) travel\_hotels\_static.rosreestr\_hotels в которой находятся объекты размещения от Росреестра, с соответствующими им информации по master\_hotel\_id, где rosreestr\_hotel\_id = id. В модели HotelInfoApiResponseListPayloadApiResponse дополнительно формируется объект следующей стурктуры:
      
      | Параметр | Источник данных |
      |---|---|
      | certification |  |
      | -&gt;resortId | \[travel\_hotels\_static]..\[rosreestr\_hotels].resort\_id |
      | -&gt;status | \[travel\_hotels\_static]..\[rosreestr\_hotels].hotel\_status\_name |
      | -&gt;type | По \[travel\_hotels\_static]..\[rosreestr\_hotels].hotel\_type\_id получаем из \[travel\_hotels\_static]..\[rosreestr\_hotel\_type].name |
      | -&gt;registerRecord | \[travel\_hotels\_static]..\[rosreestr\_hotels].register\_record |
      | -&gt;fullName | \[travel\_hotels\_static]..\[rosreestr\_hotels].full\_name |
      | -&gt;addressList | По \[travel\_hotels\_static]..\[rosreestr\_hotels].id получаем значения всех \[travel\_hotels\_static]..\[rosreestr\_address\_list].name для выбранного hotel\_id, объединенных в массив |
      | -&gt;ownerName | По \[travel\_hotels\_static]..\[rosreestr\_hotels].owner\_id получаем из \[travel\_hotels\_static]..\[rosreestr\_owners].name |
      | -&gt;ownerInn | По \[travel\_hotels\_static]..\[rosreestr\_hotels].owner\_id получаем из \[travel\_hotels\_static]..\[rosreestr\_owners].inn |
      | -&gt;ownerKpp | По \[travel\_hotels\_static]..\[rosreestr\_hotels].owner\_id получаем из \[travel\_hotels\_static]..\[rosreestr\_owners].kpp |
      | -&gt;ownerOgrn | По \[travel\_hotels\_static]..\[rosreestr\_hotels].owner\_id получаем из \[travel\_hotels\_static]..\[rosreestr\_owners].ogrn |
      | -&gt;room |  |
      | -&gt;-&gt;apartmentCount | По \[travel\_hotels\_static]..\[rosreestr\_hotels].id получаем из \[travel\_hotels\_static]..\[rosreestr\_hotel\_room\_groups].apartment\_count для выбранного hotel\_id |
      | -&gt;-&gt;numberSeats | По \[travel\_hotels\_static]..\[rosreestr\_hotels].id получаем из \[travel\_hotels\_static]..\[rosreestr\_hotel\_room\_groups].number\_seats для выбранного hotel\_id |
      | -&gt;-&gt;roomCategoryName | По \[travel\_hotels\_static]..\[rosreestr\_hotels].id получаем из \[travel\_hotels\_static]..\[rosreestr\_hotel\_room\_groups].room\_category\_name для выбранного hotel\_id |
      | -&gt;-&gt;roomCategoryId | По \[travel\_hotels\_static]..\[rosreestr\_hotels].id получаем из \[travel\_hotels\_static]..\[rosreestr\_hotel\_room\_groups].room\_category\_id для выбранного hotel\_id |
      | certificationNeeded | \[TravelDB]..\[Hotel].CertificationNeeded |
   2. Если значение false, то маппинг не производим и передаем объект certification=null.
3. Продолжается выполнение .

**Словарь HotelContactlessCheckinType**

| HotelCategoryId | HotelCategoryName |
|---|---|
| 1 | Phone |
| 2 | Address |
| 3 | Smartlock |
| 4 | Keypad |
| 5 | Lock |
| 6 | Reception |

Словарь HotelCategory

| HotelCategoryId | HotelCategoryName |
|---|---|
| 0 | Resort |
| 1 | Sanatorium |
| 2 | Guesthouse |
| 3 | MiniHotel |
| 4 | Castle |
| 5 | Hotel |
| 6 | BoutiqueAndDesign |
| 7 | Apartment |
| 8 | CottagesAndHouses |
| 9 | Farm |
| 10 | VillasAndBungalows |
| 11 | Camping |
| 12 | Hostel |
| 13 | Bnb |
| 14 | ApartHotel |
| 15 | Glamping |

**Словарь валют**

| CurrencyTypeId | Код валюты |
|---|---|
| 8 | ALL |
| 12 | DZD |
| 32 | ARS |
| 36 | AUD |
| 44 | BSD |
| 48 | BHD |
| 50 | BDT |
| 51 | AMD |
| 52 | BBD |
| 60 | BMD |
| 64 | BTN |
| 68 | BOB |
| 72 | BWP |
| 84 | BZD |
| 90 | SBD |
| 96 | BND |
| 104 | MMK |
| 108 | BIF |
| 116 | KHR |
| 124 | CAD |
| 132 | CVE |
| 136 | KYD |
| 144 | LKR |
| 152 | CLP |
| 156 | CNY |
| 170 | COP |
| 174 | KMF |
| 188 | CRC |
| 191 | HRK |
| 192 | CUP |
| 203 | CZK |
| 208 | DKK |
| 214 | DOP |
| 222 | SVC |
| 230 | ETB |
| 232 | ERN |
| 238 | FKP |
| 242 | FJD |
| 262 | DJF |
| 270 | GMD |
| 292 | GIP |
| 320 | GTQ |
| 324 | GNF |
| 328 | GYD |
| 332 | HTG |
| 340 | HNL |
| 344 | HKD |
| 348 | HUF |
| 352 | ISK |
| 356 | INR |
| 360 | IDR |
| 364 | IRR |
| 368 | IQD |
| 376 | ILS |
| 388 | JMD |
| 392 | JPY |
| 398 | KZT |
| 400 | JOD |
| 404 | KES |
| 408 | KPW |
| 410 | KRW |
| 414 | KWD |
| 417 | KGS |
| 418 | LAK |
| 422 | LBP |
| 426 | LSL |
| 430 | LRD |
| 434 | LYD |
| 446 | MOP |
| 454 | MWK |
| 458 | MYR |
| 462 | MVR |
| 478 | MRO |
| 480 | MUR |
| 484 | MXN |
| 496 | MNT |
| 498 | MDL |
| 504 | MAD |
| 512 | OMR |
| 516 | NAD |
| 524 | NPR |
| 532 | ANG |
| 533 | AWG |
| 548 | VUV |
| 554 | NZD |
| 558 | NIO |
| 566 | NGN |
| 578 | NOK |
| 586 | PKR |
| 590 | PAB |
| 598 | PGK |
| 600 | PYG |
| 604 | PEN |
| 608 | PHP |
| 634 | QAR |
| 643 | RUB |
| 646 | RWF |
| 654 | SHP |
| 682 | SAR |
| 690 | SCR |
| 694 | SLL |
| 702 | SGD |
| 704 | VND |
| 706 | SOS |
| 710 | ZAR |
| 716 | ZWD |
| 728 | SSP |
| 748 | SZL |
| 752 | SEK |
| 756 | CHF |
| 760 | SYP |
| 764 | THB |
| 776 | TOP |
| 780 | TTD |
| 784 | AED |
| 788 | TND |
| 800 | UGX |
| 807 | MKD |
| 818 | EGP |
| 826 | GBP |
| 834 | TZS |
| 840 | USD |
| 858 | UYU |
| 860 | UZS |
| 882 | WST |
| 886 | YER |
| 901 | TWD |
| 925 | SLE |
| 926 | VED |
| 927 | UYW |
| 928 | VES |
| 929 | MRU |
| 930 | STN |
| 931 | CUC |
| 932 | ZWL |
| 933 | BYN |
| 934 | TMT |
| 936 | GHS |
| 938 | SDG |
| 940 | UYI |
| 941 | RSD |
| 943 | MZN |
| 944 | AZN |
| 946 | RON |
| 947 | CHE |
| 948 | CHW |
| 949 | TRY |
| 950 | XAF |
| 951 | XCD |
| 952 | XOF |
| 953 | XPF |
| 954 | XEU |
| 955 | XBA |
| 956 | XBB |
| 957 | XBC |
| 958 | XBD |
| 959 | XAU |
| 960 | XDR |
| 961 | XAG |
| 962 | XPT |
| 963 | XTS |
| 964 | XPD |
| 965 | XUA |
| 967 | ZMW |
| 968 | SRD |
| 969 | MGA |
| 970 | COU |
| 971 | AFN |
| 972 | TJS |
| 973 | AOA |
| 974 | BYR |
| 975 | BGN |
| 976 | CDF |
| 977 | BAM |
| 978 | EUR |
| 979 | MXV |
| 980 | UAH |
| 981 | GEL |
| 984 | BOV |
| 985 | PLN |
| 986 | BRL |
| 990 | CLF |
| 994 | XSU |
| 997 | USN |
| 999 | XXX |

**Словарь единиц**

| PriceUnitId | PriceUnit | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | PerGuestPerNight | За каждого гостя за ночь |
| 2 | PerGuestPerStay | За каждого гостя за весь период проживания |
| 3 | PerRoomPerNight | За комнату за ночь |
| 4 | PerRoomPerStay | За комнату за весь период проживания |
| 5 | PerHour | За час |
| 6 | PerWeek | За неделю |

**Словарь включенности в стоимость**

| InclusionId | Inclusion | Описание |
|---|---|---|
| 0 | false | Не включено в стоимость |
| 1 | true | Включено в стоимость |

**Словарь типов животных**

| PetsTypeId | PetsType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Gt5kg | Более 5 кг |
| 2 | Lt5kg | Менее 5 кг |

 

**Словарь типов дополнительных платежей**

| FeeTypeId | FeeType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Television | Телевизор |
| 2 | Towels | Полотенца |
| 3 | Conditioning | Кондиционер |
| 4 | Housekeeping | Уборка |
| 5 | Heating | Отопление |
| 6 | Refrigerator | Холодильник |
| 7 | Utility |  |
| 8 | Safe | Сейф |
| 9 | Microwave | Микроволновая печь |
| 10 | LuggageStorage | Хранение багажа |
| 11 | TourGuide | Туристический гид |
| 12 | BicycleRental | Аренда велосипедов |
| 13 | BabyHighchair | Детский стульчик |
| 14 | BedLinen | Постельное белье |
| 15 | TowelsOnly | Только полотенца |
| 16 | LuggageStorageApartment |  |
| 17 | LuggageStorageOffice |  |

**Словарь типов депозитов**

| DepositTypeId | DepositType | Описание |
|---|---|---|
| 0 | Pet | Депозит за животных |
| 1 | Breakage | Депозит за возможный ущерб |
| 2 | Keys | Депозит за ключ от номера |
| 3 | Unspecified | Не определено |

**Словарь типов оплаты**

| PaymentTypeId | PaymentType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Cash | Наличные |
| 2 | Card | Банковская карта |
| 3 | CashAndCard | Наличные и банковская карта |

**Словарь типов ценообразования**

| PricingTypeId | PricingType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Percent | Процент от стоимости |
| 2 | Fixed | Фиксированная цена |

**Словарь типов территорий парковки**

| ParkingTerritoryTypeId | ParkingTerritoryType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | OnSide | Парковка на территории отеля |
| 2 | OffSide | Парковка за пределами территории отеля |

**Словарь типов времени дня**

| HotelDetailsTimeOfDayId | HotelDetailsTimeOfDay | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | BeforeMidday | До полудня |
| 2 | AfterMidday | После полудня |

**Словарь типов направлений трансфера**

| ShuttleDestinationTypeId | ShuttleDestinationType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Airport | Аэропорт |
| 2 | Train | Вокзал |
| 3 | Ship | Порт |
| 4 | AirportTrain | Аэропорт / Вокзал |

Словарь типов трансфера

| ShuttleTypeId | ShuttleType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | OneWay | В одну сторону |
| 2 | TwoWays | В обе стороны |

**Словарь типов доступа в интернет**

| InternetTypeId | InternetType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Wireless | Беспроводной доступ |
| 2 | Wired | Проводной доступ |

**Словарь типов мест доступа в интернет**

| InternetWorkAreaId | InternetWorkArea | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | Hotel | Доступ в интернет на территории отеля |
| 2 | Room | Доступ в интернет в номере |

**Словарь типов заезда и выезда из отеля**

| CheckInCheckOutTypeId | CheckInCheckOutType | Описание |
|---|---|---|
| 0 | Unspecified | Не определено |
| 1 | EarlyCheckin | Ранний заезд |
| 2 | LateCheckout | Поздний выезд |
| 3 | HolidayCheckin | Заезд в праздничные дни |
| 4 | HolidayCheckout | Выезд в праздничные дни |

Словарь способов оплаты в отеле

| PaymentMethodId | PaymentMethod |
|---|---|
| 0 | Unspecified |
| 1 | AmericanExpress |
| 2 | Cash |
| 3 | ChinaUnionpay |
| 4 | DinersClub |
| 5 | EuroMastercard |
| 6 | Jcb |
| 7 | Maestro |
| 8 | MasterCard |
| 9 | SwitchMaestro |
| 10 | Visa |
| 11 | VisaDebit |
| 12 | VisaDelta |
| 13 | VisaElectron |
| 14 | Pro100 |
| 15 | Mir |

**Словарь типов номеров в Extranet**

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

**Словарь типов кроватей в Extranet**

| BedType | BedTypeId |
|---|---|
| None | 0 |
| Single | 1 |
| Double | 3 |
| Queen | 4 |
| King | 5 |
| Bunk | 6 |

# Пример использования

## Запрос

```json
{
  "masterHotelId": [
    1426291
  ]
}
```

## Ответ

```json
[CDATA[{
	"payload": [
		{
			"masterHotelId": 1445633,
			"isClosed": false,
			"deleted": false,
			"name": "Golden Hills 3*",
			"nameEn": "Golden Hills Hotel",
			"hotelChain": null,
			"starRating": 3,
			"images": [
				"https://extranet-cdn.tinkoff.ru/b2/extranet/{size}/20828/20542f5f-4369-484e-b5b9-f2d3c4f754fd.jpg",
				"https://extranet-cdn.tinkoff.ru/b13/extranet/{size}/20828/3290bf9e-cdc8-43a5-bb0e-4a7de659d506.jpg",
				"https://extranet-cdn.tinkoff.ru/b20/extranet/{size}/20828/15f6eaf9-a7b9-44e2-a622-7b6faaf2c1e1.jpg",
				"https://extranet-cdn.tinkoff.ru/b3/extranet/{size}/20828/7866c320-de6b-4fcf-9f78-950493d41bf4.jpg",
				"https://extranet-cdn.tinkoff.ru/b11/extranet/{size}/20828/31e1364d-e0f9-4abf-8a53-1c17eec71a6a.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/51ab4d82-6b19-4bf8-9f2e-4d186876e0ab.jpg",
				"https://extranet-cdn.tinkoff.ru/b23/extranet/{size}/20828/84b3c237-7b1b-43d0-a240-d99a26feef28.jpg",
				"https://extranet-cdn.tinkoff.ru/b18/extranet/{size}/20828/49c47bea-31bd-4003-9ab6-5a593aab397e.jpg",
				"https://extranet-cdn.tinkoff.ru/b24/extranet/{size}/20828/c76e4ad6-2b35-452b-947f-1b4ad932a4bc.jpg",
				"https://extranet-cdn.tinkoff.ru/b9/extranet/{size}/20828/5e396283-828a-4a8a-b177-981030b3d93a.jpg",
				"https://extranet-cdn.tinkoff.ru/b6/extranet/{size}/20828/7433b4de-7911-4f92-a910-7f551c25a2c9.jpg",
				"https://extranet-cdn.tinkoff.ru/b22/extranet/{size}/20828/93275619-c514-432b-8a7e-a16b1e6ab70d.jpg",
				"https://extranet-cdn.tinkoff.ru/b16/extranet/{size}/20828/1eb2a950-f0f6-437a-b5ff-39cd4c2eb59e.jpg",
				"https://extranet-cdn.tinkoff.ru/b11/extranet/{size}/20828/0e83b8ce-2387-4a3e-93b5-782f319ef587.jpg",
				"https://extranet-cdn.tinkoff.ru/b25/extranet/{size}/20828/1c1051cc-e409-480f-a2c0-9e6e62a86b4f.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/c1b26df4-34a2-4ecb-b804-14bad9fee24d.jpg",
				"https://extranet-cdn.tinkoff.ru/b7/extranet/{size}/20828/ac10bf3e-9dea-4e2f-872e-f2adf111a0b5.jpg",
				"https://extranet-cdn.tinkoff.ru/b11/extranet/{size}/20828/a184bc20-ca2c-43a0-b45c-6ee035fc6168.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/3bf41721-9272-41bc-aafd-20c55cee7b59.jpg",
				"https://extranet-cdn.tinkoff.ru/b17/extranet/{size}/20828/719685c0-9ca4-4a99-a2dd-7b2ac9ed78ed.jpg",
				"https://extranet-cdn.tinkoff.ru/b4/extranet/{size}/20828/9a559f73-5059-4372-811f-470570498a0a.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/de80b210-c482-4c54-b060-35035336ce8d.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/f886bbb9-0a88-48fb-8dfe-688c7997bc5c.jpg",
				"https://extranet-cdn.tinkoff.ru/b7/extranet/{size}/20828/66fdc27a-a745-4807-a502-ad9069a7ab0e.jpg",
				"https://extranet-cdn.tinkoff.ru/b21/extranet/{size}/20828/18be549b-74a7-42e7-8baf-ddba138e1815.jpg",
				"https://extranet-cdn.tinkoff.ru/b5/extranet/{size}/20828/7d842f18-7ad4-4ec2-b98a-93d1f6fba96b.jpg",
				"https://extranet-cdn.tinkoff.ru/b1/extranet/{size}/20828/63aeb437-8c6b-4fac-bbdd-9b79bd390e12.jpg",
				"https://extranet-cdn.tinkoff.ru/b13/extranet/{size}/20828/d28c5024-46be-4c0c-ae7b-d271a7625553.jpg",
				"https://extranet-cdn.tinkoff.ru/b8/extranet/{size}/20828/c67dcfcd-8558-41ea-b6ee-309e56c5c480.jpg",
				"https://extranet-cdn.tinkoff.ru/b4/extranet/{size}/20828/98b9e274-a4e6-450f-b157-d15e543f1d01.jpg",
				"https://extranet-cdn.tinkoff.ru/b2/extranet/{size}/20828/44197dff-80e7-45db-8fdd-676af74f1c9c.jpg",
				"https://extranet-cdn.tinkoff.ru/b2/extranet/{size}/20828/9e3b292f-24fe-4fc2-9591-1ddc782ed153.jpg",
				"https://extranet-cdn.tinkoff.ru/b25/extranet/{size}/20828/5e2e23fb-8a7b-469b-8a00-091a7641eb3a.jpg",
				"https://extranet-cdn.tinkoff.ru/b3/extranet/{size}/20828/10449dec-0921-40d1-b441-fb67d4d428c4.jpg",
				"https://extranet-cdn.tinkoff.ru/b24/extranet/{size}/20828/e9c91537-af21-46cf-8427-15122e1836f4.jpg",
				"https://extranet-cdn.tinkoff.ru/b5/extranet/{size}/20828/fda15962-a4f0-4d68-80bf-19c5dc6311e7.jpg",
				"https://extranet-cdn.tinkoff.ru/b5/extranet/{size}/20828/9c8fea32-4c58-45ee-a0e4-8648162d220d.jpg",
				"https://extranet-cdn.tinkoff.ru/b17/extranet/{size}/20828/108f8492-de8c-4f8a-9ac4-7fb5c346c642.jpg",
				"https://extranet-cdn.tinkoff.ru/b20/extranet/{size}/20828/309239d5-65a6-464b-bde8-14896daa4587.jpg",
				"https://extranet-cdn.tinkoff.ru/b25/extranet/{size}/20828/fc0e645a-f937-4648-9b48-e3e9ae1c2281.jpg",
				"https://extranet-cdn.tinkoff.ru/b24/extranet/{size}/20828/99a978d9-fa8a-4fce-b74b-5ca827810f08.jpg",
				"https://extranet-cdn.tinkoff.ru/b10/extranet/{size}/20828/094a133f-fd11-48bb-a92f-278f59e1383f.jpg",
				"https://extranet-cdn.tinkoff.ru/b13/extranet/{size}/20828/ef6f6f53-2843-4ccf-9b99-d6a883a75fdf.jpg",
				"https://extranet-cdn.tinkoff.ru/b7/extranet/{size}/20828/aa4cf673-4a30-46da-b976-16351cbedb25.jpg",
				"https://extranet-cdn.tinkoff.ru/b5/extranet/{size}/20828/cfd923ff-7069-4cf8-a7ab-d2c1676b6e7b.jpg",
				"https://extranet-cdn.tinkoff.ru/b12/extranet/{size}/20828/86f55844-adfd-4e70-b7d4-afdf9d713827.jpg",
				"https://extranet-cdn.tinkoff.ru/b12/extranet/{size}/20828/3e2b3b44-f636-4d88-b427-1d2122eb41e2.jpg",
				"https://extranet-cdn.tinkoff.ru/b5/extranet/{size}/20828/0aa5f3ef-b68a-4b74-b8e5-d9298a4a1c78.jpg",
				"https://extranet-cdn.tinkoff.ru/b25/extranet/{size}/20828/e5b46003-4f34-411b-85ba-ab2126972f6b.jpg",
				"https://extranet-cdn.tinkoff.ru/b13/extranet/{size}/20828/9459e4ea-b930-4984-8df9-d4d985c1a7a5.jpg"
			],
			"address": "улица Автодорога М-27 Джубга-Сочи, д.6,, Лермонтово",
			"addressEn": "ulitsa Avtodoroga M-27 Dzhubga-Sochi, 6, Lermontovo",
			"masterLocationId": 66791,
			"kind": "Hotel",
			"coordinates": {
				"latitude": 44.28225300000000,
				"longitude": 38.78986700000000
			},
			"ianaTimeZone": "Europe/Moscow",
			"checkInTime": "15:00",
			"checkOutTime": "12:00",
			"phone": "+78002009036",
			"email": "sales@golden-hills.pro",
			"description": [
				{
					"title": null,
					"paragraphs": [
						"Коллекция SPA-отелей Golden Hills расположена в живописном месте Краснодарского края, на одном из лучших песчано-галечных пляжей курорта Лермонтово. Вдали от городской суеты, забот и режима многозадачности, Вы переключаетесь и погружаетесь в единство с чистым воздухом, красотой природы, завораживающими закатами и многообещающими рассветами. Время словно останавливается, чтобы Вы почувствовали силу и энергию основных природных стихий (Земля, Вода, Огонь, Воздух), основополагающих элементов, которые уникально собраны в одном месте.. Месте, наполненном любовью и заботой, состоящим из мелочей, и приносящим много счастья.",
						"Наша философия основана на создании особого пространства, где пятый, главный элемент – Вы!",
						"Здесь хочется быть и вновь возвращаться, чувствовать себя как дома, здесь действительно ждут!"
					]
				},
				{
					"title": "Расположение",
					"paragraphs": [
						"Как добраться:",
						"1. Собственным автотранспортом (см схема проезда).",
						"2. Железнодорожный вокзал Туапсе – 31 км, вокзал Горячий ключ - 70 км, далее на выбор: такси, автобус, аренда автомобиля, заказ индивидуального трансфера.",
						"3. Аэропорт Сочи – 190 км, далее оптимальный маршрут: электропоезд Ласточка до станции Туапсе, далее см п2.",
						"4. Железнодорожный вокзал Краснодара – 130 км, далее на выбор: такси, автобус, аренда автомобиля, заказ индивидуального трансфера."
					]
				},
				{
					"title": "Рестораны ",
					"paragraphs": [
						"Кафе Чайка",
						"Приглашаем Вас посетить наше кафе Чайка, откуда Вы сможете отправиться в гастрономическое путешествие, не покидая пределы отеля.",
						"Летняя терраса",
						"Одно из любимых мест наших гостей – верхняя терраса ресторана Чайка! Здесь часто проходят музыкальные вечера и гастрономические ужины.",
						"Пляж-бар VoDa",
						"Команда нашего бара, расположенного у самой кромки воды, позаботится обо всем необходимом для того, чтобы Вы наслаждались морем и солнцем. Здесь легко решить вопрос с быстрым сытным или лёгким перекусом после моря.",
						"Ресторан VOZДУХ",
						"В этом месте собраны лучшие нотки высокой кухни и безупречного сервиса. Кулинарная философия ресторана «VOZДУХ» - приготовленные с душой фермерские продукты, ведь мы заботимся о Вашем здоровье.",
						"Лобби-бар",
						"Наш лобби-бар - это приятное пространство для ожидания, кратковременного отдыха и вечерних встреч. Вы можете расположиться в уютной зоне с напитками и легкими закусками за просмотром любимого телеканала. Комфортная обстановка с мягкими диванами располагает как к бизнес-переговорам, так и дружескому общению за чашечкой кофе или любимого коктейля."
					]
				},
				{
					"title": "СПА",
					"paragraphs": [
						"Для гостей отеля 3* и 4* услуги wellness-центра (крытый бассейн, хамам, финская сауна, фитнес зона) бесплатно ПО ПРЕДВАРИТЕЛЬНОЙ ЗАПИСИ   Для гостей 3* - 2 часа в день, для гостей 4 и 5* - без ограничения по времени!",
						"Крытый бассейн с панорамным видом работает в любую погоду и наполнен тёплой чистой водой.",
						"Зарядиться энергией, привести мышцы в тонус или просто остановить время и поймать состояние невесомости.",
						"График работы wellness-центра",
						"(крытый бассейн, хамам, финская сауна, фитнес зона)",
						"Ежедневно, кроме понедельника, 9.00-22.00",
						"понедельник 12.00-22.00",
						"с 09:00 до 19:00 – Взрослые и дети",
						"с 19:00 до 22:00 – Взрослые"
					]
				},
				{
					"title": "Дополнительные услуги",
					"paragraphs": [
						"В зависимости от категории возможно размещение гостей на дополнительном месте.",
						"Стоимость дополнительного места 3 500 руб - за ребенка от 7 лет и взрослого, 2 500 руб - за ребенка до 7 лет",
						"Количество дополнительных мест зависит от категории",
						"Информацию можно уточнить по телефону: +78002009036 или 89889660317",
						"Оплата при заселении"
					]
				},
				{
					"title": "Правила размещения с животными",
					"paragraphs": [
						"Допускается размещение с питомцами по согласованию и за дополнительную плату только на первом этаже."
					]
				}
			],
			"facts": {
				"yearBuilt": null,
				"electricity": {
					"sockets": [
						{
							"code": "c",
							"name": "Европейская розетка (без заземления)"
						}
					],
					"voltage": [
						220
					],
					"frequency": [
						50
					]
				},
				"roomsNumber": 49,
				"floorsNumber": null,
				"yearRenovated": null
			},
			"facilities": [
				{
					"id": 1,
					"name": "Лифт",
					"priority": null,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 4,
					"name": "Отопление",
					"priority": null,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 7,
					"name": "Терраса",
					"priority": 56,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 93,
					"name": "Кондиционер",
					"priority": null,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 112,
					"name": "Банкомат",
					"priority": 52,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 132,
					"name": "Круглосуточная стойка регистрации",
					"priority": 27,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 134,
					"name": "Охрана",
					"priority": null,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 166,
					"name": "Компьютер",
					"priority": null,
					"groupId": 1,
					"groupName": "Общее"
				},
				{
					"id": 16,
					"name": "Телевизор",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 17,
					"name": "Фен",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 22,
					"name": "Сейф (в номере)",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 98,
					"name": "Мини-бар",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 121,
					"name": "Тапочки",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 155,
					"name": "Халат",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 298,
					"name": "Интернет в номере",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 399,
					"name": "Балкон",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 564,
					"name": "Гладильные принадлежности",
					"priority": null,
					"groupId": 2,
					"groupName": "В номерах"
				},
				{
					"id": 27,
					"name": "Прачечная",
					"priority": null,
					"groupId": 4,
					"groupName": "Услуги и удобства"
				},
				{
					"id": 28,
					"name": "Сейф",
					"priority": 50,
					"groupId": 4,
					"groupName": "Услуги и удобства"
				},
				{
					"id": 29,
					"name": "Услуги консьержа",
					"priority": null,
					"groupId": 4,
					"groupName": "Услуги и удобства"
				},
				{
					"id": 123,
					"name": "Утюг",
					"priority": null,
					"groupId": 4,
					"groupName": "Услуги и удобства"
				},
				{
					"id": 32,
					"name": "Бар",
					"priority": 4,
					"groupId": 5,
					"groupName": "Питание"
				},
				{
					"id": 33,
					"name": "Завтрак",
					"priority": null,
					"groupId": 5,
					"groupName": "Питание"
				},
				{
					"id": 36,
					"name": "Ресторан",
					"priority": null,
					"groupId": 5,
					"groupName": "Питание"
				},
				{
					"id": 240,
					"name": "Возможен полный пансион",
					"priority": null,
					"groupId": 5,
					"groupName": "Питание"
				},
				{
					"id": 212,
					"name": "Wi-Fi",
					"priority": 14,
					"groupId": 0,
					"groupName": "Интернет"
				},
				{
					"id": 147,
					"name": "Трансфер от/до аэропорта",
					"priority": null,
					"groupId": 7,
					"groupName": "Трансфер"
				},
				{
					"id": 197,
					"name": "Трансфер",
					"priority": null,
					"groupId": 7,
					"groupName": "Трансфер"
				},
				{
					"id": 42,
					"name": "на английском",
					"priority": null,
					"groupId": 8,
					"groupName": "Персонал говорит"
				},
				{
					"id": 103,
					"name": "на русском",
					"priority": null,
					"groupId": 8,
					"groupName": "Персонал говорит"
				},
				{
					"id": 214,
					"name": "Подходит для проведения праздничных мероприятий",
					"priority": null,
					"groupId": 10,
					"groupName": "Развлечения"
				},
				{
					"id": 49,
					"name": "Парковка",
					"priority": 7,
					"groupId": 0,
					"groupName": "Парковка"
				},
				{
					"id": 84,
					"name": "Крытый бассейн",
					"priority": 41,
					"groupId": 12,
					"groupName": "Бассейн и пляж"
				},
				{
					"id": 85,
					"name": "Удобства для пляжа",
					"priority": null,
					"groupId": 12,
					"groupName": "Бассейн и пляж"
				},
				{
					"id": 107,
					"name": "Полотенца для пляжа/бассейна",
					"priority": null,
					"groupId": 12,
					"groupName": "Бассейн и пляж"
				},
				{
					"id": 190,
					"name": "Развлечения на воде",
					"priority": null,
					"groupId": 12,
					"groupName": "Бассейн и пляж"
				},
				{
					"id": 139,
					"name": "Организация встреч и банкетов",
					"priority": null,
					"groupId": 13,
					"groupName": "Бизнес"
				},
				{
					"id": 87,
					"name": "Фитнес-центр",
					"priority": 23,
					"groupId": 14,
					"groupName": "Спорт"
				},
				{
					"id": 273,
					"name": "Яхтинг",
					"priority": null,
					"groupId": 14,
					"groupName": "Спорт"
				},
				{
					"id": 55,
					"name": "Массаж",
					"priority": 11,
					"groupId": 15,
					"groupName": "Красота и здоровье"
				},
				{
					"id": 56,
					"name": "Сауна",
					"priority": null,
					"groupId": 15,
					"groupName": "Красота и здоровье"
				},
				{
					"id": 241,
					"name": "Хаммам",
					"priority": null,
					"groupId": 15,
					"groupName": "Красота и здоровье"
				},
				{
					"id": 60,
					"name": "Размещение подходит для семей/детей",
					"priority": null,
					"groupId": 16,
					"groupName": "Дети"
				},
				{
					"id": 90,
					"name": "Размещение с домашними животными",
					"priority": 12,
					"groupId": 18,
					"groupName": "Животные"
				}
			],
			"metapolicyExtraInfo": "Российским гражданам при заезде обязательно нужно иметь оригинал действующего паспорта РФ.\nСтойка регистрации работает 24/7.\nРазмещение с животными доступно по предварительному запросу.<pДополнительные платежиРоссийским гражданам при заезде обязательно нужно иметь оригинал действующего паспорта РФ.\nСтойка регистрации работает 24/7.\nРазмещение с животными доступно по предварительному запросу.\nВ зависимости от категории возможно размещение гостей на дополнительном месте.\nСтоимость дополнительного места 3 500 руб - за ребенка от 7 лет и взрослого, 2 500 руб - за ребенка до 7 лет\nКоличество дополнительных мест зависит от категории\nИнформацию можно уточнить по телефону: +78002009036 или 89889660317\nОплата при заселении",
			"metapolicyExtraInfoEn": null,
			"metapolicy": {
				"cot": [],
				"meal": [],
				"pets": [],
				"visa": {
					"visaSupport": "false"
				},
				"addFee": [
					{
						"currency": "Rub",
						"feeType": "TowelsOnly",
						"price": 800.00,
						"priceUnit": "PerRoomPerStay"
					}
				],
				"deposit": [],
				"noShow": {
					"time": null,
					"dayPeriod": "Unspecified",
					"availability": "false"
				},
				"parking": [],
				"shuttle": [],
				"children": [],
				"internet": [],
				"extraBed": [],
				"childrenMeal": [],
				"checkInCheckOut": []
			},
			"paymentMethods": [
				"Cash"
			],
			"location": {
				"masterLocationId": 66791,
				"name": "Лермонтово",
				"type": "City",
				"countryCode": "RU"
			},
			"policy": [],
			"certificationNeeded": true,
			"certification": {
				"resortId": "019ce11b-a236-76b2-b761-28a6dfffb215",
				"status": "Действует",
				"type": "Гостиница",
				"registerRecord": "С232026022520",
				"fullName": "Курортный отель \"Голден Хиллс\" (\"Golden Hills\") 3*",
				"addressList": [
					"352847, Краснодарский Край, м.о. Туапсинский, с Лермонтово, ул Автодорога М-27 Джубга-Сочи, д. 6"
				],
				"ownerName": "Индивидуальный предприниматель Понамаренко Елена Павловна",
				"ownerInn": "233907321253",
				"ownerKpp": "",
				"ownerOgrn": "323237500027033",
				"room": [
					{
						"apartmentCount": 44,
						"numberSeats": 88,
						"roomCategoryName": "Первая (стандарт)",
						"roomCategoryId": 1
					},
					{
						"apartmentCount": 2,
						"numberSeats": 4,
						"roomCategoryName": "Люкс",
						"roomCategoryId": 62
					},
					{
						"apartmentCount": 3,
						"numberSeats": 6,
						"roomCategoryName": "Джуниор сюит",
						"roomCategoryId": 63
					},
					{
						"apartmentCount": 1,
						"numberSeats": 6,
						"roomCategoryName": "Апартамент",
						"roomCategoryId": 61
					}
				]
			},
			"cityName": "Лермонтово",
			"cityNameEn": "Lermontovo",
			"countryName": "Россия",
			"countryNameEn": "Russia"
		}
	]
}]]>
```

# Изменения

| № | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создание v3 метода (оранжевым цветом изменения по отношению к v2) |  | TTP-36818 |