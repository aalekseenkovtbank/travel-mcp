# Метод GetRostPromoHotels (/internal\_api/v1/hotels/rost-promo-hotels)

| Назначение | Получение идентификатором Master-отелей, участвующих в программе РОСТ через Extranet |
|---|---|
| Бизнес процесс | 1 пейджер \\| Отели - Direct \\| Программа Рост для отелей |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/rost-promo-hotels |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload |  | REQUIRED | Объект, содержащий ответ |

### Структура HotelPromoApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| hotels | int\[] | REQUIRED | Коллекция идентификаторов Master-отелей, участвующих в программе РОСТ через Extranet |

# Словарь промо-программ

| Id | Code | Name |
|---|---|---|
| 1 | Rost | Рост |

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

# Алгоритм работы

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура 🗂️ CMS.HotelStaticApi\_GetHotelPromoHotels \[HotelsStaticApi] в базе CMS. В качестве аргумента функции @PromoId передается параметр промо-программы ROST (1)
4. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель ответа

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| →hotels | Значения всех MasterHotelId из результата работы хранимой процедуры, объединенные в коллекцию |

# Пример использования

## Запрос

```
/internal_api/v1/hotels/rost-promo-hotels
```

## Ответ

```json
{
  "payload": {
    "hotels": [101, 205]
  }
}
```

# Связанные страницы

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Метод для получения списка мастер отелей подключенных к программе Рост | Текущая | THB-10683 |