# Метод HotelSupplierMapping (/internal\_api/v1/hotels/hotel-supplier-mapping)

| Назначение | Получение маппинга по идентификатору master-отеля или получение идентификатора master-отеля по коду поставщика |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/hotel-supplier-mapping |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура HotelSupplierMappingRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer | OPTIONAL | Идентификатор master-отеля |
| supplierHotelCode | string | OPTIONAL | Код отеля поставщика |
| supplierId | integer | OPTIONAL | Идентификатор поставщика |

## Структура ответа

### Структура HotelSupplierMappingResponseListPayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | \[] | REQUIRED | Объект, содержащий ответ |

### Структура HotelSupplierMappingResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| hotelId | integer | OPTIONAL | Идентификатор master-отеля |
| locationId | integer | OPTIONAL | Идентификатор локации |
| supplierId | integer | OPTIONAL | Идентификатор поставщика |
| hotelCode | string | OPTIONAL | Код отеля поставщика |

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

<table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><th colspan="1">Сценарий</th><th><p><em>error.code</em></p></th><th><p><em>error.message</em></p></th><th colspan="1">error.details.code</th><th colspan="1">error.details.message</th><th colspan="1">error.details.attribute</th><th>HTTP код</th><th colspan="1">Пример ответа</th></tr><tr><td colspan="1">Неавторизованный запрос</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">401</td><td colspan="1">N/A</td></tr><tr><td colspan="1">Ошибка сервера при выполнении запроса</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">500</td><td colspan="1">N/A</td></tr><tr><td colspan="1">Не передан обязательный параметр supplierId в запросе с непустым supplierHotelCode</td><td colspan="1">incorrectValue</td><td colspan="1">Ошибка при валидации запроса.</td><td colspan="1">noSuppplierId</td><td colspan="1">Идентификатор поставщика не может быть пустым.</td><td colspan="1">supplierId</td><td colspan="1">400</td><td colspan="1"><div><p><br/></p><pre><code>{
	&#34;error&#34;: {
		&#34;code&#34;: &#34;incorrectValue&#34;,
		&#34;message&#34;: &#34;Ошибка при валидации запроса.&#34;,
		&#34;details&#34;: {
			&#34;code&#34;: &#34;noSuppplierId&#34;,
			&#34;message&#34;: &#34;Идентификатор поставщика не может быть пустым.&#34;,
			&#34;attribute&#34;: &#34;supplierId&#34;
		}
	}
}</code></pre><p><br/></p></div></td></tr><tr><td colspan="1">Не передан один из двух обязательных параметра</td><td colspan="1">incorrectValue</td><td colspan="1">Ошибка при валидации запроса.</td><td colspan="1">noRequiredData</td><td colspan="1">Либо masterHotelId, либо supplierHotelCode обязательны в запросе.</td><td colspan="1">null</td><td colspan="1">400</td><td colspan="1"><div><p><br/></p><pre><code>{
	&#34;error&#34;: {
		&#34;code&#34;: &#34;incorrectValue&#34;,
		&#34;message&#34;: &#34;Ошибка при валидации запроса.&#34;,
		&#34;details&#34;: {
			&#34;code&#34;: &#34;noRequiredData&#34;,
			&#34;message&#34;: &#34;Либо masterHotelId, либо supplierHotelCode обязательны в запросе.&#34;,
			&#34;attribute&#34;: null
		}
	}
}</code></pre><p><br/></p></div></td></tr><tr><td colspan="1"><p>Не существует отелей с комбинацией переданных параметров</p><ul><li>masterHotelId</li><li>supplierHotelCode</li><li>supplierId</li></ul></td><td>N/A</td><td>N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td>204</td><td colspan="1"><div><p>N/A</p></div></td></tr></tbody></table>

# Алгоритм работы метода HotelSupplierMapping

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура \[HotelStaticApi\_GetHotelSupplierMapping] в TravelDB с параметром @HotelID = masterHotelId, @HotelCode = supplierHotelCode, @SupplierId = supplierId
4. Выполняется выборка из таблицы \[TravelDB].\[HotelMapping] в которой находится маппинг master-отелей с отелями поставщиков  
   и выполняется объединение данных с таблицей  \[TravelDB].\[Hotel] по  \[TravelDB].\[Hotel].HotelId = \[TravelDB].\[HotelMapping].HotelId  
   с условием \[TravelDB].\[HotelMapping].HotelID = @HotelId, \[TravelDB].\[HotelMapping].SupplierHotelCode = @HotelCode и \[TravelDB].\[HotelMapping].SupplierID = @SupplierId  
   Таким образом, если на вход переданы все три параметра, то возвращается результат их пересечения;  
   Если переданы только masterHotelId и supplierHotelCode, то возвращается ошибка с error.details.code = noSuppplierId.  
   Если передан только masterHotelId, то возвращается список всех отелей от поставщиков  
   Если переданы только supplierHotelCode и supplierId, то возвращается один master-отель, которому соответствует отель от этого поставщика.
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель HotelSupplierMappingResponseListPayloadApiResponse

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt;hotelId | \[TravelDB].\[HotelMapping].HotelID |
| -&gt;locationId | \[TravelDB].\[Hotel].PrimaryLocationID |
| -&gt;supplierId | \[TravelDB].\[HotelMapping].SupplierID |
| -&gt;hotelCode | \[TravelDB].\[HotelMapping].SupplierHotelCode |

# Пример использования

## Поиск по masterHotelId

### Запрос

```json
{
  "masterHotelId": 1426291
}
```

### Ответ

```json
{
  "payload": [
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 11,
      "hotelCode": "test_93931821"
    },
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 36,
      "hotelCode": "izmailovo_alpha_hotel"
    }
  ]
}
```

## Поиск по supplierHotelCode

### Запрос

```json
{
  "supplierHotelCode": "izmailovo_alpha_hotel",
  "supplierId": 36
}
```

### Ответ

```json
{
  "payload": [
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 36,
      "hotelCode": "izmailovo_alpha_hotel"
    }
  ]
}
```

## Поиск по supplierHotelCode и masterHotelId

### Запрос

```json
{
  "masterHotelId": 1426291,
  "supplierHotelCode": "izmailovo_alpha_hotel",
  "supplierId": 36
}
```

### Ответ

```json
{
  "payload": [
    {
      "hotelId": 1426291,
      "locationId": 47307,
      "supplierId": 36,
      "hotelCode": "izmailovo_alpha_hotel"
    }
  ]
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **v. 14** |  |