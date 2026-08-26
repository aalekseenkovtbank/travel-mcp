<table><colgroup><col/><col/></colgroup><tbody><tr><th colspan="1">Назначение</th><td colspan="1">Метод возвращает информацию об отелях постранично.</td></tr><tr><th><p>Бизнес-процессы</p></th><td><p><a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3767697372">Отслеживание изменений в статике [HotelStaticApi]</a></p><p><a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3940601000">Обновление контента на стороне потребителя [HotelStaticApi]</a></p><p><a href="https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5837981795">Отказ от прямых походов в MSSQL сервисов hotels-search-api и hotels-suppliers-search-api</a></p></td></tr><tr><th colspan="1">Контракт</th><td colspan="1"><div><p><strong>POST</strong></p><table><tbody><tr><td><p><code>/internal_api/v1/search-pages/hotels</code></p></td></tr></tbody></table><p><br/></p></div></td></tr></tbody></table>

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Authorization | string | mandatory | Ключ авторизации |

### Структура запроса

```json
{
  "TimeStamp": long?,   // поле Version из CMS.Hotels
  "HotelsCount": int  // количество отелей на странице.
}
```

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload | HotelResponseData | mandatory | Объект, содержащий ответ |

### Структура ответа

```json
{
  "Data": [
  {
    "hotelId": int,
    "primaryLocationId": int,
    "certificationNeeded": bool,
    "hasCertification": bool,
    "isActive": bool
  }],
  "NextTimeStamp": long, // Используем Version - для единообразия
  "IsLastPage": bool
}
```

Нужно добавить поле Version в CMS.Hotel на основе аналогичного поля из TravelDb.Hotel.

**Используется тип ROWVERSION который обеспечивает уникальность значения на уровне БД**

### Алгоритмы работы метода

## MC.Основной сценарий

1. Выборка отелей происходит из таблицы CMS.Hotel
   
   1. Выбираются записи у которых поле Version &gt; timeStamp из запроса
   2. Размер батча равен hotelsCount
2. Отели из выборки мапятся в коллекцию data согласно контракту
3. В поле nextTimeStamp записывается максимальное значение Verson из объектов возвращаемой коллекции отелей
4. В поле isLastPage записывается значение от условия Response.data.Count &lt; Request.hotelsCount

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | mandatory | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | mandatory | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | mandatory | Код атрибута |

### Ошибки валидации запроса

HotelsCount является обязательным полем со значением &gt; 0. Иначе, возвращается ошибка BadRequest (400) с текстом "HotelsCount must be positive". 

# Связанные документы

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [TTP-29647](https://jira.tcsbank.ru/browse/TTP-29647) |