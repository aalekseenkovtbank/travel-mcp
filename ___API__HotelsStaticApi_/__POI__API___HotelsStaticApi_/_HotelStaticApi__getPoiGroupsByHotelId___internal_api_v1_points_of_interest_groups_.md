# Общая информация

| Назначение | Получение статической информации о расстоянии от отеля до всех точек интереса по Id master-отеля |
|---|---|
| Бизнес-процессы | [Места рядом с отелем - Бизнес-требования](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=4627685993) |
| Контракт | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html#/InternalApi/post\_internal\_api\_v1\_points\_of\_interest\_groups](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html#/InternalApi/post_internal_api_v1_points_of_interest_groups) |
| URL | /internal\_api/v1/points\_of\_interest/groups |
| Метод | POST |

# Протокол

## Структура запроса

Все 3 раздела опциональны. Соответствующие строки удаляются, если в них нет необходимости

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| HotelsStaticApi.Authorization |  |  | Ключ авторизации |
| Body |  |  |  |
| masterHotelId | integer | mandatory | Идентификатор master-отеля |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| payload | object: \[] | optional |  |

### Структура объекта PointsOfInterestGroup

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| groupCode | string | REQUIRED | Код типа точки интереса |
| groupName | string | REQUIRED | Наименование типа интереса на русском языке |
| points | object:<br />\[] | REQUIRED | Точки интереса указанного типа |

### Структура объекта pointOfInterestForList

Описание используемых в запросе или ответе сложных типов

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><th>Параметр</th><th>Тип</th><th><p>Обязательность</p></th><th>Описание</th></tr><tr><td colspan="1">name</td><td colspan="1">string</td><td colspan="1"><div><p>REQUIRED</p></div></td><td colspan="1">Наименование точки интереса на русском языке</td></tr><tr><td colspan="1">nameEn</td><td colspan="1">string</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1">Наименование точки интереса на англ. языке</td></tr><tr><td colspan="1">mainColor</td><td colspan="1">string (HEX)</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1">Основной цвет (линии метро)</td></tr><tr><td colspan="1">additionalColors</td><td colspan="1"><p>string[]</p><p>(HEX)</p></td><td colspan="1"><div><p>optional</p></div></td><td colspan="1">Доп.цвета (линии метро)</td></tr><tr><td>distanceDirect</td><td>double</td><td><div><p>REQUIRED</p></div></td><td>Расстояние по прямой от master-отеля до точки интереса в метрах</td></tr><tr><td colspan="1">images</td><td colspan="1">string[]</td><td colspan="1"><div><p>optional</p></div></td><td colspan="1"><div><p>URL-ы изображений точки интереса</p><p><ac:emoticon>Доступны {size}: </ac:emoticon></p><ul><li><p>x500</p></li><li><p>100x100</p></li><li><p>120x120</p></li><li><p>1024x768</p></li></ul></div></td></tr><tr><td colspan="1"><span>latitude</span></td><td colspan="1">double</td><td colspan="1"><div><p>REQUIRED</p></div></td><td colspan="1"><span>Координаты точки интереса: широта</span></td></tr><tr><td colspan="1"><span>longitude</span></td><td colspan="1">double</td><td colspan="1"><div><p>REQUIRED</p></div></td><td colspan="1"><span>Координаты точки интереса: долгота</span></td></tr><tr><td colspan="1">isLandmark</td><td colspan="1">boolean</td><td colspan="1"><div><p>REQUIRED</p></div></td><td colspan="1"><span>Признак - является ли точка интереса ориентиром для отеля</span></td></tr></tbody></table>

# Интеграционная схема

В случае если есть взаимодействие с внешними компонентами, добавляется диаграмма последовательности

Для описания метода могут быть предусмотрены и другие диаграммы, например, диаграмма статусов или видов деятельности

\[HotelsAPI] getPoiGroupsByHotelId - Получение списка сгруппированных точек интереса по отелю seq\_diagram\_poi\_list

# Алгоритмы работы метода

В этом разделе детально описывается порядок действий, которые выполняются в ходе работы метода для достижения ожидаемого результата.

Описание шагов или логики работы компонента, обращающегося к методу, не должно быть описано в структуре текущего алгоритма. Также как и не описывается логика работы компонента, к которому выполняется обращение из описываемого в алгоритме метода.

Описываются возможные ветвления и циклы. Дополнительно к вариациями позитивных сценариев описывается обработка исключительных сценариев.

Описание алгоритмов предполагает последовательность атомарных (по возможности) шагов, для каждого шага могут быть указаны переходы из него в случае возможных альтернативных, исключительных или суб-сценариев.

## MC.Основной сценарий

Для каждого метода должен быть обязательно определен один основной сценарий (MC). В MC описывается базовый (наиболее частый или наиболее короткий) позитивный сценарий работы метода. 

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Выполняется выборка из таблицы [**hotel\_points\_of\_interest**](https://wiki.tcsbank.ru/display/TRAVELHOTELS/Points+of+interest+Model#HotelPointsOfInterest) (БД: **hotels\_static** схема**: travel\_hotels\_static**), в которой хранится информации о расстоянии до точек интереса рядом с отелями, по hotel\_points\_of\_interest.hotel\_id **= masterHotelId**
   
   1. и выполняется операция объединения данных с таблицей **travel\_hotels\_static.[points\_of\_interest](https://wiki.tcsbank.ru/display/TRAVELHOTELS/Points+of+interest+Model#PointsOfInterest)** по hotel\_point\_of\_interest.point\_of\_interest\_id = points\_of\_interest.id
   2. и выполняется операция объединения данных с таблицей **travel\_hotels\_static.[point\_of\_interest\_types](https://wiki.tcsbank.ru/display/TRAVELHOTELS/Points+of+interest+Model#PointsOfInterestTypes)** по points\_of\_interest.point\_of\_interest\_type\_id = points\_of\_interest\_types.id
   3. и выполняется операция объединения данных с таблицей **travel\_hotels\_static.[point\_of\_interest\_images](https://wiki.tcsbank.ru/display/TRAVELHOTELS/Points+of+interest+Model#point_of_interest_images)** по points\_of\_interest.id = point\_of\_interest\_images.point\_of\_interest\_id
   4. в результирующую выборку (объект **points**) отбираются записи, удовлетворяющие условиям: point\_of\_interest\_types.code != (center, beach) И hotel\_points\_of\_interest.**distance\_direct** &lt;= point\_of\_interest\_types**.max\_distance\_direct** И points\_of\_interest.**is\_closed** = **false**
      
      1. доп.правила отбора данных по некоторым типам точек интереса:
         
         <table><colgroup><col/><col/></colgroup><tbody><tr><th>Тип </th><th>Правило</th></tr><tr><td>skilift</td><td><p>Если найдено несколько точек интереса с одинаковым названием (name), то добавить в результирующую выборку 1 ближайшую точку из найденных. Если несколько точек с одинаковым мин.расстоянием - выбрать 1 случайным образом</p></td></tr><tr><td>metro</td><td><p>Если найдено несколько точек интереса с одинаковым названием (name), то добавить в результирующую выборку 1 точку со следующими параметрами:</p><ul><li>mainColor - цвет (points_of_interest.<strong>color</strong>) точки интереса с ближайшим расстоянием. Если несколько точек с одинаковым мин.расстоянием - выбрать 1 случайным образом</li><li>additionalColors - цвета остальных точек</li></ul></td></tr></tbody></table>
4. Формируется полная ссылка на изображение - аналог **HotelsApi** **imagePathResolver**
5. Производится группировка данных по hotelID и типам точек интереса (points\_of\_interest.**point\_of\_interest\_type\_id**)
6. Для каждого отеля производится сортировка объектов массива **points** в порядке увеличения значения параметра **distanceDirect.**
7. Производится отсечение лишних точек для всех групп в соответствии с ограничением на максимальное количество отображаемых точек указанного типа - point\_of\_interest\_types.**output\_limit:** 
   
   1. для каждого типа точек интереса отбираются точки интереса с минимальным расстоянием с учетом ограничения: кол-во точек указанного типа для отеля &lt;= point\_of\_interest\_types.**output\_limit**
      
      1. если ограничение не задано - вернуть все найденные точки данного типа
      2. если расстояние до точек одинаковое - точки выбираются рандомно
8. Производится маппинг данных, полученных в результате запроса в БД на модель ответа
9. Основной сценарий завершается.

## Маппинг данных на модель

| **Параметр** | **Источник данных** |
|---|---|
| payload |  |
| -&gt; groupCode | \[hotels\_static].\[travel\_hotels\_static].\[point\_of\_interest\_types].code |
| -&gt; groupName | \[hotels\_static].\[travel\_hotels\_static].\[point\_of\_interest\_types].name |
| -&gt;points |  |
| -&gt;-&gt;name | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].name |
| -&gt;-&gt;name | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].name |
| -&gt;-&gt;nameEn | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].name\_en |
| -&gt;-&gt;mainColor | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].color |
| -&gt;-&gt;additionalColors | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].color |
| -&gt;-&gt;images | \[hotels\_static].\[travel\_hotels\_static].\[point\_of\_interest\_images].url (полная ссылка)<br />Первая ссылка в массиве - изображение с признаком is\_main = true. |
| -&gt;-&gt;distanceDirect | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_points\_of\_interest].distance\_direct |
| -&gt;-&gt;latitude | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].latitude |
| -&gt;-&gt;longitude | \[hotels\_static].\[travel\_hotels\_static].\[points\_of\_interest].longitude |
| -&gt;-&gt;isLandmark | \[hotels\_static].\[travel\_hotels\_static].\[hotel\_points\_of\_interest].is\_landmarks |

# Конфигурационные параметры

Перечень конфигурационных параметров, используемых в рамках алгоритмов работы методово

| Параметр | Значение | Описание |
|---|---|---|
|  |  |  |

# Пример использования

## Запрос

```json
{
	masterHotelId=1426291
}
```

## Ответ

```json
{
   "payload":[
      {
         "groupCode":"skilift",
         "groupName":"Подъемник",
         "points":[
            {
               "name":"Подъёмник К6",
               "nameEn":"Ski-lift K6",
               "mainColor":"ff0000",
		       "additionalColors": null,
			   "images": null,
               "distanceDirect":169,
               "latitude":55,
               "longitude":82
            },
            {
               "name":"Подъёмник H9",
               "nameEn":"Ski-lift H9",
               "mainColor": null,
 		       "additionalColors": null,
			   "images": null, 
               "distanceDirect":198,
               "latitude":55,
               "longitude":83,
               "isLandmark":"false"
             }
         ]
      },
      {
         "groupCode":"metro",
         "groupName":"Метро",
         "points":[
            {
               "name":"Павелецкая",
               "nameEn":"Paveletskaya",
               "mainColor":"ff0000",
               "additionalColors":[
                  "00ff00",
                  "8b00ff"
               ],
               "images": null,
               "distanceDirect":210,
               "latitude":55,
               "longitude":82,
               "isLandmark":"true"
             }
         ]
      },
      {
         "groupCode":"sight",
         "groupName":"Достопримечательность",
         "points":[
            {
               "name":"Красная площадь",
               "nameEn":"Krasnaya Ploshad",
               "mainColor": null,
 		       "additionalColors": null,
			   "images":[
                  "https://ссылка_на_публичный_бакет/{size}/poi/bbda892f86.jpeg",
                  "https://ссылка_на_публичный_бакет/{size}/poi/bbda892f86_2.jpeg"
               ],
               "distanceDirect":1090,
               "latitude":55.04,
               "longitude":82.93,
               "isLandmark":"false"
             },
            {
               "name":"Большой театр",
               "nameEn":"Bolshoy Teart",
               "mainColor": null,
 		       "additionalColors": null,
               "images":[
                  "https://ссылка_на_публичный_бакет/{size}/poi/bbda892f88.jpeg"
               ],
               "distanceDirect":465,
               "latitude":55.14,
               "longitude":83.03,
               "isLandmark":"false"
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

# История изменений

|  | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа | [v.17](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=5283832916) | THB-8668 |
| 2 | Возвращать признак isLandmarks |  | THB-10524 |