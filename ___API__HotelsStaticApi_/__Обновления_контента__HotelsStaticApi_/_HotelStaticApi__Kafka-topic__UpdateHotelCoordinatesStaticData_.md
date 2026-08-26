# Краткое описание

При изменении данных статики отеля (координат), в топике аккумулируются сообщения, отражающие актуальное состояние данных. Для формировании и отправки сообщений в топик используется регулярная джоба в hotelStatic, которая отслеживает наличие изменений в статике.

Для инфо: Удаление данных статики отеля (координат) не отслеживается.

# Формирование и отправка сообщений в топик

## MC.Основной сценарий

1. Джоба **NotifyHotelCoordinatesUpdatedJob** запускается каждые 10 минут.
2. Выполняется вызов хранимой процедуры[](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564) [\[HotelStaticApi\] СMS.StaticDataChangeNotify\_Get](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564&src=contextnavpagetreemode) со следующими параметрами:
   
   | Входные параметры | Значения |
   |---|---|
   | ObserverId | 4 |
   | WorkerProcessName | **NotifyHotelCoordinatesUpdatedJob** |
   | BatchSize | 10 |
3. Джоба получает записи из таблицы очереди [CMS.StaticDataChangeNotify](https://wiki.tcsbank.ru/display/TRAVELHOTELS/CMS.StaticDataChangeNotify).
4. Формируется сообщение для отправки в соответствии со ниже. Ключом сообщения является hotelId.
5. Выполняется отправка сообщения в топик **update-hotel-coordinates-static-data**
6. Выполняется вызов хранимой процедуры [СMS.StaticDataChangeNotify\_Done](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048662818) со следующими параметрами:
   
   | Входные параметры | Значения |
   |---|---|
   | Success | Список StaticDataChangeNotifyID всех успешно обработанных записей. Составила строку с ИД через ",". |
   | Errors | Список StaticDataChangeNotifyID всех записей, при отправки которых возникли ошибки. Составила строку с ИД через ",". |
7. Сценарий завершается

# Структура сообщения в Kafka для operationType = "hotelCoordinatesUpdate"

### \[21] HotelCoordinatesUpdateMessage

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| hotelId | int | mandatory | Id отеля<br />\[TravelDB]..\[HotelDetails].**HotelId** |
| latitude | double | mandatory | Координаты отеля: широта<br />\[TravelDB]..\[HotelDetails].**latitude** |
| longitude | double | mandatory | Координаты отеля: долгота<br />\[TravelDB]..\[HotelDetails].**longitude** |

```xml
{
	"hotelId": "14948653",
  	"latitude": "56.0485725403",
  	"longitude": "92.9090881348"
}
```

# Принцип формирования сообщений топика "update-hotel-coordinates-static-data"

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><th><br/></th><th><strong><span>Тип сообщения</span></strong><br/><span>(operationType)</span></th><th><strong><span>Триггер к формированию</span></strong></th></tr><tr><td>1</td><td>hotelCoordinatesUpdate</td><td><ol><li><span><span>По отелю изменилось значение хотя бы одного из параметров объекта &#34;HotelCoordinatesUpdateMessage</span></span><span>&#34;</span></li><li><span>Добавился новый &#34;hotelId&#34;</span></li></ol></td></tr></tbody></table>

# Изменения

|  | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создание страницы: новый кафка-топик для отслеживая изменения координат отеля. Проект: "Места рядом с отелем" |  | THB-7712 |
| 2 |  |  |  |