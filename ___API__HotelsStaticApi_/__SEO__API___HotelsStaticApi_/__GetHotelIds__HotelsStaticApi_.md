# Метод GetHotelIds

| Назначение | Получение идентификаторов активных отелей |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| URL | /internal\_api/v1/seo/hotel-ids |
| Метод | GET |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization | string | mandatory | SEO или General ключ авторизации |
| Query |  |  |  |
| offset | int32 | mandatory | Начиная с какой записи выводить данные |
| limit | int32 | mandatory | Максимальное количество записей, возвращаемых за один запрос |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload |  | mandatory | Объект, содержащий ответ |

### Структура объекта GetSeoHotelIdsResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| offset | int32 | mandatory | Значение параметра offset из запроса |
| limit | int32 | mandatory | Значение параметра limit из запроса |
| hasMore | boolean | mandatory | Есть ли еще активные отели после выбранных |
| hotelIds | int32\[] | mandatory | Массив идентификаторов активных мастер отелей |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Индекс | Тип | Обязательность | Описание |
|---|---|---|---|---|
| code | 1 | string | REQUIRED | Код ошибки атрибута |
| message | 2 | string | OPTIONAL | Текст ошибки атрибута |
| attribute | 3 | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details | HTTP код | Пример ответа |
|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | 500 | N/A |
| Значение limit превышает ограничение в 100 000 элементов | incorrectValue | Limit exceeds value 100000 | null | 400 | ```json<br />{
  "error": {
    "code": "incorrectValue",
    "details": null,
    "message": "Limit exceeds value 100000"
  }
}<br />``` |

# Алгоритм работы метода GetHotelIds

1. Выполняется авторизация по предоставленному ключу авторизации.
2. Выполняется валидация запроса.
3. Из таблицы TravelDB.Hotels выбираются значения Hotels.HotelID, где Hotels.IsActive = 1, с учетом пагинации (offset) и лимита (limit + 1). При выборке данные сортируются по Hotel.HotelID.
4. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель ответа.

# Маппинг данных на модель Hotel Static API

<table><colgroup><col/><col/></colgroup><tbody><tr><th>Параметр</th><th>Источник данных</th></tr><tr><td colspan="1"><span>payload</span></td><td colspan="1"><br/></td></tr><tr><td><span>-&gt;offset</span></td><td>Значение offset из запроса</td></tr><tr><td colspan="1">-&gt;limit</td><td colspan="1">Значение limit из запроса</td></tr><tr><td colspan="1">-&gt;hasMore</td><td colspan="1"><ul><li>true, если из БД вернулось ровно limit + 1 элемент</li><li>false, если из БД вернулось меньше limit + 1 элементов</li></ul></td></tr><tr><td colspan="1">-&gt;hotelIds</td><td colspan="1">Массив идентификаторов отелей из БД, ограниченный первыми limit записями из результата выборки</td></tr></tbody></table>

# Пример использования

## Запрос

```text
/internal_api/v1/seo/hotel-ids?offset=100&limit=10
```

## Ответ

```json
{
  "payload": {
    "offset": 100,
    "limit": 10,
    "hasMore": true,
    "hotelIds": [
      101,
      103,
      104,
      105,
      106,
      107,
      108,
      109,
      111,
      112
    ]
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Создание нового метода | **v. 1** | THB-8088 |