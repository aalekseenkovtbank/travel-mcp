# Краткое описание

При изменении/удалении данных статики (локации/отеля/комнаты), в топике аккумулируются сообщения, отражающие актуальное состояние данных. Для формировании и отправки сообщений в топик используются регулярные джобы, которые отслеживают наличие изменений в статике.  

- Проблематка решения описана в [RFC](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3785575889)

# Формирование и отправка сообщений в топик

## Описание

Для всех типов сообщений существует ряд джоб, которые раз в минуту отслеживает изменение в статике - проверяет наличие своих записей в таблице очереди ( см.  Отслеживание изменений в статике \[HotelStaticApi] ) . При появлении изменений формируют сообщения и отправляют в топик. 

### Схема

```plantuml
[CDATA[@startuml
participant StaticDataChangeNotify
participant StoredProcedure
participant TravelDB
participant Task
participant Topic




Task - StoredProcedure : Джоба вызвала хранимую процедуру по observerId and status = 1 для получения записей в таблице очереди   
alt Записей нет
Task -> Task : Закончила свою работу
else
StoredProcedure -> StaticDataChangeNotify : Хранимая процедура запросила N записей для джобы.\nПроставила для них статус - 2
StaticDataChangeNotify -> StoredProcedure : Хранимая процедура получила все записи из таблицы очереди
StoredProcedure -> Task: Хранимая процедура передала джобе все записи

Task->Task : Джоба сгруппировала записи для оптимизации получения данных
Task -> TravelDB : Сделала запрос данных из TravelDBдля составления сообщений
TravelDB -> Task : Получила данные для всех сообщений

loop N записей

Task -> Topic: Для каждой записи сформировала и отправила сообщение в топик 

end
end
@enduml]]>
```

### Алгоритм джобы

MC. Основной сценарий. 

1. Джоба запускается каждые 5 минут. Время ожидания между запусками зависит от того, есть ли еще записи на обработку в таблице очереди [CMS.StaticDataChangeNotify](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.StaticDataChangeNotify).
2. Джоба вызывает хранимую процедуру[](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564) [\[HotelStaticApi\] СMS.StaticDataChangeNotify\_Get](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564&src=contextnavpagetreemode). Во входные параметры передала.
   
   | Входные параметры | Значения |
   |---|---|
   | ObserverId | 2 |
   | WorkerProcessName | Уникальное имя процесса джобы |
   | BatchSize | 10 |
3. Джоба получила таблицу с записями из таблицы очереди [CMS.StaticDataChangeNotify](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.StaticDataChangeNotify).
4. Джоба меняет время ожидания на 1 минуту ( пункт 1 ). 
   
   1. Если таблица пустая установила значение в 5 минут ( пункт 1 ).
5. Джоба сгруппировала полученные записи по MasterItemId and ItemType, для оптимизации запроса данных из travelDB.
6. Джоба запросила для всех сгруппированых записей данные из travelDB.
7. Джоба для каждой уникальной записи по MasterItemId, ItemType и ConsumerId.
   
   1. Составила сообщения для отправки. .
   2. Отправила сообщения в топик. Ключ для сообщения является locationId.
   3. Если параметр Item2ID != null, подставили значение для параметра hotelId в схеме события.
8. Джоба вызвала хранимую процедуру [СMS.StaticDataChangeNotify\_Done](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048662818). Во входящие параметры передала.
   
   | Входные параметры | Значения |
   |---|---|
   | Success | Список StaticDataChangeNotifyID всех успешно обработанных записей. Составила строку с ИД через ",". |
   | Errors | Список StaticDataChangeNotifyID всех записей, при отправки которых возникли ошибки. Составила строку с ИД через ",". |
9. Джоба закончила свою работу.

* * *

# Структура сообщения в Kafka

Вместе с каждым сообщением Кафка нужно прикладывать **Traceparent** в Headers для каждого сообщения

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th>Параметр</th><th colspan="1">Тип</th><th colspan="1"><p>Обязате<span>льность</span></p></th><th>Описание</th></tr><tr><td colspan="1"><span>operationType</span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Одно из возможных значений:</span></p><ol><li><span>locationInfoUpdate</span><span></span></li><li><span>locationInfoDelete</span></li><li><span>hotelPropertiesUpdate</span></li><li><span>hotelPropertiesDelete</span></li><li><span>hotelFiltersUpdate</span><span> </span></li><li><span>hotelFiltersDelete</span></li><li><span>hotelFacilityBitmapsUpdate</span></li><li><span>hotelFacilityBitmapsDelete</span></li><li><span>roomFacilityBitmapsUpdate</span></li><li><span>roomFacilityBitmapsDelete</span></li></ol></div></td></tr><tr><td colspan="1"><span>data</span></td><td colspan="1"><div><p></p></div></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Объект с актуальными данными, соответствующий конкретному <strong>operationType</strong></span></p></div></td></tr></tbody></table>

## Объект "Data"

Структура объекта зависит от значения **operationType:**

### \[1] Data для operationType = "locationInfoUpdate"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[Location].**LocationID** |
| locationName | string | mandatory | Наименование локации<br />\[TravelDB]..\[Location].**Name** |
| locationType | int | mandatory | Тип локации<br />\[TravelDB]..\[Location].**Type** |
| locationCode | string | optional | Код локации<br />\[TravelDB]..\[Location].**Code** |
| countryName | string | mandatory | Название страны<br />Определяем по дереву locations (первая встретившаяся страна).<br />Начальный уровень location = Страна |
| timeZone | string | optional | Временная зона<br />\[TravelDB]..\[Location].**TimeZoneName** |

```xml
{
  "operationType": "locationInfoUpdate",
  "data": 
    {       
      "locationId": "17039",
      "locationName": "Москва",
      "locationType": "5",
      "locationCode": "RU",
      "countryName": "Россия",
      "timeZone": "Africa/Ceuta"
    }         
}
```

### \[2] Data для operationType = "locationInfoDelete"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[HotelDetails].**PrimaryLocationID** |

```xml
{
  "operationType": "locationInfoDelete",
  "data": 
    {       
      "locationId": "17039"
    }         
}
```

### \[3] Data для operationType = "**hotelPropertiesUpdate"**

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th><p><span>Параметр</span></p></th><th colspan="1"><span>Тип</span></th><th colspan="1"><p><span>Обязательность</span></p></th><th><span>Описание и источник данных</span></th></tr><tr><td colspan="1"><span>locationId</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id локации </span></p><p><span>[TravelDB]..[HotelDetails].<strong>PrimaryLocationID</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelId</span></td><td colspan="1">int</td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelId</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span><span>hotel</span><span>Name</span></span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Название отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelName</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span><span>hotel</span>NameOriginal</span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Название отеля (оригинальное)</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelNameOriginal</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelAddress</span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Адрес отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelAddress</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>coordinatesLatitude</span></td><td colspan="1"><span>float<ac:emoticon></ac:emoticon></span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Координаты отеля: широта</span></p><p><span>[TravelDB]..[HotelDetails].<strong>latitude</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>coordinatesLongitude</span></td><td colspan="1"><span>float<ac:emoticon></ac:emoticon></span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Координаты отеля: долгота</span></p><p><span>[TravelDB]..[HotelDetails].<strong>longitude</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>images</span></td><td colspan="1"><span>string[]</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Изображения </span></p><p><span>Массив из всех значений [TravelDB]..[HotelImages].<strong>ImagePath</strong><span> </span>для выбранного master-отеля, с сортировкой:</span></p><ul><li><span>Сперва записи со значением [TravelDB]..[HotelImages].IsDefault = &#34;1&#34; (основная фотография отеля)</span><ul><li><span>если таковых несколько – приоритет за меньшим [TravelDB]..[HotelImages].HotelImageId</span></li></ul></li><li><span>Затем согласно значению [TravelDB]..[HotelImages].Position (от меньшего к большему)</span></li></ul><p><br/></p></div></td></tr><tr><td colspan="1">isFlat</td><td colspan="1">bool</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p><span>Признак &#34;Квартира&#34;</span></p><p><span>[TravelDB]..[Hotel].<strong>isFlat</strong></span></p><p><br/></p></div></td></tr></tbody></table>

```xml
{
  "operationType": "hotelPropertiesUpdate",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234",      
      "hotelName": "Воронцовский",
      "hotelNameOriginal": "Воронцовский",
      "hotelAddress": "Воронцовский переулок, д. 5/7, стр. 2",
      "coordinatesLatitude": "55.7343",
      "coordinatesLongitude": "37.6589",
      "images": 
        [
          "https://extranet-cdn.tinkoff.ru/extranet/{size}/10324/452f5911-70d6-4dec-9335-2cad128b1b18.jpg",
          "https://extranet-cdn.tinkoff.ru/extranet/{size}/10324/e54bed1b-d197-420a-844d-fbc207d7b5b9.jpg"
        ]
    }         
}
```

### \[4] Data для operationType = "**hotelPropertiesDelete"**

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[HotelDetails].**PrimaryLocationID** |
| hotelId | int | mandatory | Id отеля<br />\[TravelDB]..\[HotelDetails].**HotelId** |

```xml
{
  "operationType": "hotelPropertiesDelete",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234"      
    }         
}
```

### \[5] Data для operationType = "hotelFiltersUpdate"

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th><p><span>Параметр</span></p></th><th colspan="1"><span>Тип</span></th><th colspan="1"><p><span>Обязательность</span></p></th><th><span>Описание и источник данных</span></th></tr><tr><td colspan="1"><span>locationId</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id локации </span></p><p><span>[TravelDB]..[HotelDetails].<strong>PrimaryLocationID</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelId</span></td><td colspan="1">int</td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelId</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>starRating</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p><span>Звёздность отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>StarRating</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelCategory</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Категория отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelCategory</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hasImages</span></td><td colspan="1"><span>bool</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Если ли изображения</span></p><p><span>[TravelDB]..[HotelDetails].<strong>imagePath != null</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>reviewRating</span></td><td colspan="1"><span>float<ac:emoticon></ac:emoticon></span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Оценка по отзывам</span></p><p><span>[TravelDB]..[HotelDetails].<strong>ReviewRating</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>reviewCount</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Кол-во отзывов</span></p><p><span>[TravelDB]..[HotelDetails].<strong>ReviewCount</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>chain</span><span> </span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p><span>Сеть отеля</span></p><p><span>[TravelDB]..[HotelDetails].HotelChainID → [TravelDB]..[HotelChain].<strong>NameRu</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><div><p><span>bedType</span></p><p><br/></p></div></td><td colspan="1"><span></span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Тип кроватей в разрезе комнат</span></p><p><br/></p></div></td></tr><tr><td colspan="1">bedroomCount</td><td colspan="1">int</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p>Количество комнат в объекте размещения, актуально для квартир</p><p><span>[TravelDB]..[Room].BedroomCount</span></p><p><span>В случаях, когда у объекта несколько комнат, значение поля берется из данных комнаты поставщика, согласно приоритету: Экстранет → Островок → Броневик.</span></p></div></td></tr><tr><td colspan="1">size</td><td colspan="1">decimal</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p>Площадь объекта размещения, актуально для квартир</p><p><span>[TravelDB]..[Room].Size</span></p><p><span>В случаях, когда у объекта несколько комнат, значение поля берется из данных комнаты поставщика, согласно приоритету: Экстранет → Островок → Броневик.</span></p></div></td></tr><tr><td colspan="1">IsContactlessCheckin</td><td colspan="1">bool</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p>Признак &#34;Бесконтактное заселение&#34;, актуально для квартир</p><p><span>[TravelDB]..[HotelContactlessCheckin].IsContactless</span></p><p><br/></p></div></td></tr><tr><td colspan="1">IsDepositAvailable</td><td colspan="1">bool</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p>Признак &#34;Запрашивается ли депозит&#34;, актуально для квартир</p><p><span>[TravelDB]..[HotelDeposit].IsAvailable</span></p><p><br/></p></div></td></tr></tbody></table>

#### Объект "BedType\[]"

1. Для HotelId находим все записи \[TravelDB]..\[Room].**RoomId**
2. Для каждой RoomId находим все записи \[TravelDB].\[RoomBedConfiguration].**RoomBedConfigurationId**
3. Для каждой RoomBedConfigurationId находим все **уникальные** записи \[TravelDB].\[RoomBed].**BedTypeId** и формируем из них объект ниже.

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| roomId | int | mandatory | Id комнаты |
| bedTypeIds | int\[] | mandatory | Типы кроватей |

```xml
{
  "operationType": "hotelFiltersUpdate",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234",  
      "starRating": "4",
      "hotelCategory": "1",
      "hasImages": "true",
      "reviewRating": "4.76",
      "reviewCount": "112",
      "chain": "Safmar",        
      "bedType": 
        [
          {
          "roomId": "3287438",
          "bedTypeIds": 
            [
              "1",
              "5",
              "8"
            ]  
          }  
        ]
    }         
}
```

### \[6] Data для operationType = "hotelFiltersDelete"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[HotelDetails].**PrimaryLocationID** |
| hotelId | int | mandatory | Id отеля<br />\[TravelDB]..\[HotelDetails].**HotelId** |

```xml
{
  "operationType": "hotelFiltersUpdate",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234"
    }         
}
```

### \[7] Data для operationType = "hotelFacilityBitmapsUpdate"

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th><p><span>Параметр</span></p></th><th colspan="1"><span>Тип</span></th><th colspan="1"><p><span>Обязательность</span></p></th><th><span>Описание и источник данных</span></th></tr><tr><td colspan="1"><span>locationId</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id локации </span></p><p><span>[TravelDB]..[HotelDetails].<strong>PrimaryLocationID</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelId</span></td><td colspan="1">int</td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id отеля</span></p><p><span>[TravelDB]..[HotelDetails].<strong>HotelId</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>hotelFacilityBitmaps</span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Битмапа с удобствами отеля</span></p><p><span>[TravelDB]..[HotelDetails].HotelId<strong> → </strong>[TravelDB]..[HotelFacility].<strong>FacilityID</strong></span></p><ul><li><span>&#39;0&#39; - удобства нет</span></li><li><span>&#39;1&#39; - удобство есть</span></li></ul><p><span><span>Маппинг конкретного бита на конкретное удобство соответствует последовательности {FacilityId} схемы битмапы.</span></span></p><ul><li><span><span>получение схемы битмапы удобств <strong>отеля</strong> происходит через вызов метода <a href="https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BHotelStaticApi%5D+GetFacilities">GetFacilities</a> с входным параметром <strong>facilityTypeId</strong> = <strong>1</strong> </span></span></li></ul><p><br/></p></div></td></tr></tbody></table>

```xml
{
  "operationType": "hotelFacilityBitmapsUpdate",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234", 
      "hotelFacilityBitmaps": "0111100010001010010010101001010100101010010101010110000001111"
    }         
}
```

### \[8] Data для operationType = "hotelFacilityBitmapsDelete"

| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[HotelDetails].**PrimaryLocationID** |
|---|---|---|---|
| hotelId | int | mandatory | Id отеля<br />\[TravelDB]..\[HotelDetails].**HotelId** |

```xml
{
  "operationType": "hotelFacilityBitmapsDelete",
  "data": 
    {
      "locationId": "17039",
      "hotelId": "1234"
    }         
}
```

### \[9] Data для operationType = "roomFacilityBitmapsUpdate"

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th><p><span>Параметр</span></p></th><th colspan="1"><span>Тип</span></th><th colspan="1"><p><span>Обязательность</span></p></th><th><span>Описание и источник данных</span></th></tr><tr><td colspan="1"><span>locationId</span></td><td colspan="1"><span>int</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Id локации </span></p><p><span>[TravelDB]..[HotelDetails].<strong>PrimaryLocationID</strong></span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>roomId</span></td><td colspan="1">int</td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>id комнаты</span></p><p><span>[TravelDB]..[Room].RoomId<strong> </strong>(where HotelID=HotelDetails.HotelID)</span></p><p><br/></p></div></td></tr><tr><td colspan="1"><span>roomFacilityBitmaps</span></td><td colspan="1"><span>string</span></td><td colspan="1"><div><p>mandatory</p></div></td><td colspan="1"><div><p><span>Битмапа с удобствами номера</span></p><p><span>[TravelDB]..[Room].RoomId (where HotelID=HotelDetails.HotelID) <strong>→ </strong>[TravelDB]..[RoomFacility].<strong>FacilityId</strong></span></p><ul><li><span>&#39;0&#39; - удобства нет</span></li><li><span>&#39;1&#39; - удобство есть</span></li></ul><p><span><span>Маппинг конкретного бита на конкретное удобство соответствует последовательности {FacilityId} схемы битмапы.</span></span></p><ul><li><span><span>получение схемы битмапы удобств <strong>комнаты</strong> происходит через вызов метода <a href="https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BHotelStaticApi%5D+GetFacilities">GetFacilities</a> с входным параметром <strong>facilityTypeId</strong> = <strong>2</strong> </span></span></li></ul><p><br/></p></div></td></tr></tbody></table>

```xml
{
  "operationType": "roomFacilityBitmapsUpdate",
  "data": 
    {
      "locationId": "17039",
      "roomId": "784384",  
      "roomFacilityBitmaps": "0111100010001010010010101001010100101010010101010110000001111"
    }         
}
```

### \[10] Data для operationType = "roomFacilityBitmapsDelete"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| locationId | int | mandatory | Id локации<br />\[TravelDB]..\[HotelDetails].**PrimaryLocationID** |
| roomId | int | mandatory | id комнаты<br />\[TravelDB]..\[Room].RoomId (where HotelID=HotelDetails.HotelID) |

```xml
{
  "operationType": "roomFacilityBitmapsDelete",
  "data": 
    {
      "locationId": "17039",
      "roomId": "784384"
    }         
}
```

* * *

# Принцип формирования сообщений топика "UpdateCacheStaticData"

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th colspan="1"><span>#</span></th><td><strong><span>Тип сообщения</span></strong><br/><span>(operationType)</span></td><td><strong><span>Триггер к формированию</span></strong></td><td><strong><span>Комментарий</span></strong></td></tr><tr><th colspan="1">1</th><td><span>locationInfoUpdate</span></td><td><p><span>Изменилось значение хотя бы одного из параметров его объекта &#34;Data&#34;</span></p></td><td><br/></td></tr><tr><th colspan="1">2</th><td><span>locationInfoDelete</span></td><td><span>Деактивировалась локация –– [TravelDB]..[Location].isActive = 0</span></td><td><span>При этом кеш по отелям такой локации остается валидным, т.к. локацию в какой-то момент могут заново активировать</span></td></tr><tr><th colspan="1">3</th><td><span>hotelPropertiesUpdate</span></td><td><ol><li><span>По отелю изменилось значение хотя бы одного из параметров объекта &#34;Data&#34;</span></li><li><span>В локациию добавился новый &#34;hotelId&#34;</span></li></ol></td><td><br/></td></tr><tr><th colspan="1">4</th><td><span>hotelPropertiesDelete</span></td><td><ol><li><span>Деактивировался отель –– [TravelDB]..[Hotel].isActive = 0</span></li><li><span>Отель мигрировал в другую локацию </span></li></ol></td><td><br/></td></tr><tr><th colspan="1">5</th><td><span>hotelFiltersUpdate</span></td><td><ol><li><span>По отелю изменилось значение хотя бы одного из параметров объекта &#34;Data&#34;</span></li><li><span>В локацию добавился новый &#34;hotelId&#34;</span></li></ol></td><td><br/></td></tr><tr><th colspan="1">6</th><td colspan="1"><span>hotelFiltersDelete</span></td><td colspan="1"><ol><li><span>Деактивировался отель –– [TravelDB]..[Hotel].isActive = 0</span></li><li><span>Отель мигрировал в другую локацию </span></li></ol></td><td colspan="1"><br/></td></tr><tr><th colspan="1">7</th><td colspan="1"><span>hotelFacilityBitmapsUpdate</span></td><td colspan="1"><ol><li><span>По отелю изменилось значение хотя бы одного из параметров объекта &#34;Data&#34;</span></li><li><span>В локацию добавился новый &#34;hotelId&#34;</span></li></ol></td><td colspan="1"><br/></td></tr><tr><th colspan="1">8</th><td colspan="1"><span>hotelFacilityBitmapsDelete</span></td><td colspan="1"><ol><li><span>Деактивировался отель –– [TravelDB]..[Hotel].isActive = 0</span></li><li><span>Отель мигрировал в другую локацию </span></li><li><span>У отеля нет ни одного удобства</span></li></ol></td><td colspan="1"><br/></td></tr><tr><th colspan="1">9</th><td colspan="1"><span>roomFacilityBitmapsUpdate</span></td><td colspan="1"><ol><li><span>По комнате изменилось значение хотя бы одного из параметров объекта &#34;Data&#34;</span></li><li><span>В локацию (в рамках отеля) добавился новый &#34;roomId&#34;</span></li></ol></td><td colspan="1"><br/></td></tr><tr><th colspan="1">10</th><td colspan="1"><span>roomFacilityBitmapsDelete</span></td><td colspan="1"><ol><li><span>Деактивировался отель –– [TravelDB]..[Hotel].isActive = 0</span></li><li><span>Отель мигрировал в другую локацию </span></li><li><span>Удалилась комната отеля</span></li></ol></td><td colspan="1"><br/></td></tr></tbody></table>

# Топики в devplatform

| # | **Название** | **Environment** |
|---|---|---|
| 1 | [hotels-backend.update-cache-static-data](https://devplatform.tcsbank.ru/tenants/hotels-backend/kafka/topics/view/20397) | prod |
| 2 | [hotels-backend.update-cache-static-data-qa](https://devplatform.tcsbank.ru/tenants/hotels-backend/kafka/topics/view/20392) | qa |
| 3 | [hotels-backend.update-cache-static-data-qa2](http://hotels-backend.update-cache-static-data-qa2) | qa2 |
| 4 | [hotels-backend.update-cache-static-data-qa3](http://hotels-backend.update-cache-static-data-qa3) | qa3 |

# Изменения

<table><colgroup><col/><col/><col/><col/></colgroup><thead><tr><th>Версия</th><th><p>Изменение</p></th><th><p>Версия страницы</p></th><th colspan="1"><p>Задача</p></th></tr></thead><tbody><tr><td>1</td><td colspan="1">Исходная версия документа</td><td colspan="1"><a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8442150990">v.76</a></td><td colspan="1"><div><ul><li>THB-4994</li><li>THB-5010</li><li>THB-5011</li><li>THB-5012</li><li>THB-5013</li><li>THB-5091</li></ul></div></td></tr><tr><td>2</td><td colspan="1">Новые атрибуты для квартир</td><td colspan="1"><a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=8442158771">v.77</a></td><td colspan="1"><div><p>TTP-35390</p></div></td></tr><tr><td colspan="1">3</td><td colspan="1"><span>Добавлены условия заполнения полей bedRoomCount и size для hotelFiltersUpdate</span></td><td colspan="1"><span>Текущая</span></td><td colspan="1"><div><p>TTP-39575</p></div></td></tr></tbody></table>