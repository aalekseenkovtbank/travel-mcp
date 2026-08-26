# Краткое описание

Для формировании и отправки сообщений в топик используются регулярные джобы, которые отслеживают наличие изменений в статике.  

- Проблематка решения описана в [RFC](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3785575889)

# Формирование и отправка сообщений в топик

## MC.Основной сценарий

**Триггер**: наступление регламентного времени

1. Выполняется вызов хранимой процедуры[](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564) [\[HotelStaticApi\] СMS.StaticDataChangeNotify\_Get](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048660564&src=contextnavpagetreemode) со следующими параметрами:
   
   | Входные параметры | Значения |
   |---|---|
   | ObserverId | 3 |
   | WorkerProcessName | Уникальное имя процесса джобы |
   | BatchSize | 10 |
2. Формируется сообщение для отправки в соответствии со .
3. Выполняется отправка сообщения в топик UpdateSuppliersSearchAPICacheStaticData.
4. Выполняется вызов хранимой процедуры [СMS.StaticDataChangeNotify\_Done](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4048662818)со следующими параметрами:
   
   | Входные параметры | Значения |
   |---|---|
   | Success | Список StaticDataChangeNotifyID всех успешно обработанных записей. Составила строку с ИД через ",". |
   | Errors | Список StaticDataChangeNotifyID всех записей, при отправки которых возникли ошибки. Составила строку с ИД через ",". |
5. Сценария завершается.

* * *

# Структура сообщения в Kafka

Вместе с каждым сообщением Кафка нужно прикладывать **Traceparent** в Headers для каждого сообщения

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| operationType | string | mandatory | Тип операции |
| data |  | mandatory | Объект с актуальными данными, соответствующий конкретному **operationType** |

## Объект "Data"

Структура объекта зависит от значения **operationType:**

### \[19] Data для operationType = "fakeRoomRelationAdd"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| fakeRoomId | int | mandatory | Id фейковой комнаты<br />\[TravelDB]..\[FakeRoomRelation].**FakeRoomId** |
| roomId | int | mandatory | Id комнаты<br />\[TravelDB]..\[FakeRoomRelation].**RoomId** |
| hotelId | int | mandatory | Id отеля мастеровой комнаты |

```xml
{
  "operationType": "fakeRoomRelationAdd",
  "data": 
    {       
      "fakeRoomId": "17039",
      "roomId": "99123",
      "hotelId": "5"
    }         
}
```

### \[20] Data для operationType = "fakeRoomRelationDelete"

| Параметр | Тип | Обязательность | Описание и источник данных |
|---|---|---|---|
| fakeRoomId | int | mandatory | Id фейковой комнаты<br />\[TravelDB]..\[FakeRoomRelation].**FakeRoomId** |
| roomId | int | mandatory | Id комнаты<br />\[TravelDB]..\[FakeRoomRelation].**RoomId** |
| hotelId | int | mandatory | Id отеля мастеровой комнаты |

```xml
{
  "operationType": "fakeRoomRelationDelete",
  "data": 
    {       
      "fakeRoomId": "17039",
      "roomId": "99123",
      "hotelId": "5" 
    }         
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа | Текущая | THB-7087 |