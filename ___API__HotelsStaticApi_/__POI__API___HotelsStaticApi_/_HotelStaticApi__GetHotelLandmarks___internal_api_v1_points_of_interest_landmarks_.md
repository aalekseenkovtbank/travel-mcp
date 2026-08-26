# Общая информация

| Назначение | Получение статической информации о расстоянии от отеля до ориентиров по набору идентификаторов master-отелей |
|---|---|
| Бизнес-процессы | 1-пейджер \\| Отели \\| Места рядом с отелем |
| Контракт | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html#/InternalApi/post\_internal\_api\_v1\_points\_of\_interest\_landmarks](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html#/InternalApi/post_internal_api_v1_points_of_interest_landmarks) |
| URL | /internal\_api/v1/points\_of\_interest/landmarks |
| Метод | POST |

# Протокол

## Структура запроса

Все 3 раздела опциональны. Соответствующие строки удаляются, если в них нет необходимости

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization |  |  | Ключ авторизации |
| Body |  |  |  |
| masterHotelIds | int32:\[] | REQUIRED | Идентификаторы master-отелей |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload | :\[] | optional |  |

### Структура hotelLandmarks

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| hotelId | int4 | REQUIRED | Идентификатор отеля |
| landmarks | \[] | REQUIRED | Массив ориентиров (метро, вокзалы, аэропорты) |

### Структура landmark

Описание используемых в запросе или ответе сложных типов

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| name | string | OPTIONAL | Наименование точки интереса на русском языке |
| nameEn | string | optional | Наименование точки интереса на англ. языке |
| color | string | optional | Цвет (линии метро) |
| type | string | REQUIRED | Код типа точки интереса |
| distanceDirect | double | REQUIRED | Расстояние от master-отеля до точки интереса (в метрах) |

## Ошибки: коды и описания

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
| Не передан обязательный параметр masterHotelIds | incorrectValue | Ошибка при валидации запроса. | noMasterHotelIds | Идентификатор master-отеля обязателен. | masterHotelIds | 400 | ```json<br />{
    "error": {
        "code": "incorrectValue",
        "Message": "Ошибка при валидации запроса.",
        "details": {
            "code": "noMasterHotelIds",
            "message": "Идентификатор master-отеля обязателен.",
            "attribute": "masterHotelIds"
        }
    }
}<br />``` |
| Не существует отелей с указанным masterHotelIds | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Интеграционная схема

В случае если есть взаимодействие с внешними компонентами, добавляется диаграмма последовательности

Для описания метода могут быть предусмотрены и другие диаграммы, например, диаграмма статусов или видов деятельности

\[HotelsAPI] getHotelLandmarks\_v1 - Поиск ориентиров рядом с отелем seq\_diagram\_top\_poi

# Алгоритмы работы метода

В этом разделе детально описывается порядок действий, которые выполняются в ходе работы метода для достижения ожидаемого результата.

Описание шагов или логики работы компонента, обращающегося к методу, не должно быть описано в структуре текущего алгоритма. Также как и не описывается логика работы компонента, к которому выполняется обращение из описываемого в алгоритме метода.

Описываются возможные ветвления и циклы. Дополнительно к вариациями позитивных сценариев описывается обработка исключительных сценариев.

Описание алгоритмов предполагает последовательность атомарных (по возможности) шагов, для каждого шага могут быть указаны переходы из него в случае возможных альтернативных, исключительных или суб-сценариев.

## MC.Основной сценарий

Для каждого метода должен быть обязательно определен один основной сценарий (MC). В MC описывается базовый (наиболее частый или наиболее короткий) позитивный сценарий работы метода. 

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Выполняется выборка из таблицы [**hotel\_points\_of\_interest**](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BTO_DO%5D+Points+of+interest+Model#HotelPointsOfInterest) (БД: **hotels\_static** схема**: travel\_hotels\_static**), в которой хранится информации о расстоянии до точек интереса рядом с отелями, по hotel\_points\_of\_interest.**hotel\_id = masterHotelId**
   
   1. и выполняется операция объединения данных с таблицей **[points\_of\_interest](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BTO_DO%5D+Points+of+interest+Model#PointsOfInterest)** по hotel\_point\_of\_interest.**point\_of\_interest\_id** = points\_of\_interest.**id**
   2. и выполняется операция объединения данных с таблицей **[point\_of\_interest\_types](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BTO_DO%5D+Points+of+interest+Model#PointsOfInterestTypes)** по points\_of\_interest.**point\_of\_interest\_type\_id** = points\_of\_interest\_types.**id**
   3. в результирующую выборку (массив **landmarks**) отбираются записи, удовлетворяющие условиям: hotel\_points\_of\_interest.**is\_landmark** = **true** И points\_of\_interest.**is\_closed** = false. *Для инфо:* *Максимальное кол-во объектов в массиве **landmarks** для одного отеля - 3 (ограничение в джобе на пересчет расстояний).*
4. Производится группировка данных по **hotel\_id** и по points\_of\_interest.**point\_of\_interest\_type\_id**
5. Для каждого отеля производится сортировка:
   
   1. объекты массива **landmarks** сортируются в порядке увеличения значения параметра **distanceDirect**. *Таким образов возможны комбинации:*
      
      1. *Если есть метро: 1 метро и 1 аэропорт и 1 вокзал; 2 метро и 1 аэропорт; 1 метро и 1 аэропорт;  2 метро и 1 вокзал; 1 метро и 1 вокзал; 3 или 2 или 1 метро.*
      2. *Если нет метро: 1 аэропорт и 2 вокзала; 2 аэропорта и 1 вокзал; 3 аэропорта или 3 вокзала; 2 аэропорта или 2 вокзала; 1 аэропорт и 1 вокзал; 1 аэропорт или 1 вокзал.*
6. Производится маппинг данных, полученных в результате запроса в БД на модель ответа
7. Основной сценарий завершается.

## Маппинг данных на модель

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt; hotelId | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_points\_of\_interest].hotelID |
| -&gt;landmarks |  |
| -&gt;-&gt;name | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].name |
| -&gt;-&gt;nameEn | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].name\_en |
| -&gt;-&gt;color | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].color |
| -&gt;-&gt;type | \[hotels\_static].\[travel\_hotels\_static].\[point\_of\_interest\_types].code |
| -&gt;-&gt;distanceDirect | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_points\_of\_interest].distance\_direct |

# Пример использования

## Запрос

```json
{
  "masterHotelIds": [1426291, 1298765]
}
```

## Ответ

```json
{
	"payload":  [
	  {
  		"hotelId": 1426291,   
        "landmarks":    [
          {
            "type" : "metro",
            "name" : "Суконная слобода",
            "nameEn" : "Sukonnaya Sloboda",
            "color" : "ff0000",
            "distanceDirect" : 110
          },
          {
            "type" : "airport",
            "name" : "Аэропорт Казань им. Габдуллы Тукая",
            "nameEn" : "Gabdulla Tuqay Kazan International Airport",
            "color" : null, 
            "distanceDirect" : 20400
          }
       ]       
      },
  	  {
   		"hotelId": 1298765, {
        "landmarks":    [
          {
            "type" : "metro",
            "name" : "Суконная слобода",
            "nameEn" : "Sukonnaya Sloboda",
            "color" : "ff0000",
            "distanceDirect" : 110
          },
          {
            "type" : "metro",
            "name" : "Площадь Габдуллы Тукая",
            "nameEn" : "Ploshad Gabdulla Tuqay",
            "color" : null,
            "distanceDirect" : 250
          }
       ]     
     }
 	]
}
```

# Метрики и алерты

Зайди в БТ, посмотри, какие бизнес метрики нужны, напиши как их можно вычислить, если это возможно.

Напиши, какие ошибки нужно залогировать, какие могут быть аллерты.

# Связанные документы

## Конфигурационные параметры

# История изменений

|  | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа | [v.7](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5552548262) | THB-8666 |
| 2 | Исключение закрытых точек интереса из результирующей выборки | v.9 | THB-9865 |