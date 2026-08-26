# Метод GetLocationMigrationInfo (/internal\_api/v1/search/location\_migration\_info)

| Назначение | Получение массива мастер локаций по переданному островковому региону |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/location\_migration\_info |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура SearchByOstrovokRegionApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| ostrovokRegionId | string | REQUIRED | Строковый идентификатор локации островка |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | LocationMigrationInfoApiResponse | REQUIRED | Содержимое ответа |

### **Структура LocationMigrationInfoApiResponse**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterLocationId | integer:\[] | REQUIRED | Список привязанных master-локаций |

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
| Не передан обязательный параметр ostrovokRegionId или передана пустая строка | incorrectValue | Ошибка при валидации запроса. | noOstrovokRegionId | Идентификатор ostrovok-локации должен быть заполнен. | ostrovokRegionId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "noOstrovokRegionId",
			"message": "Идентификатор ostrovok-локации должен быть заполнен.",
			"attribute": "ostrovokRegionId"
		}
	}
}<br />``` |
| Не существует мастер локаций привязанных к переданному ostrovok region id | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода HotelSupplierMapping

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура HotelStaticApi\_GetMasterLocationIds в TravelDB с параметром @OstrovokRegionId = ostrovokRegionId
4. Выполняется выборка из таблицы TravelDB.LocationMapping значения LocationID, для которых SupplierId = 36 и IsActive = 1 и SupplierLocationCode = @OstrovokRegionId
5. Полученные данные из хранимой процедуры возвращаются массивом

# Пример использования

## Запрос

```json
{
  "ostrovokRegionId": "2395"
}
```

## Ответ

```json
{
  "payload": {
    masterLocationId:[17039]
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **[v.](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=2751197635) 1** |  |