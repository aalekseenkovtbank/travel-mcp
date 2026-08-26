# Общая информация

| Назначение | Метод  запускает процесс очистки записей зависших при сбои инвалидации |
|---|---|
| Бизнес-процессы | Отслеживание изменений в статике \[HotelStaticApi]<br />[\[HotelStaticApi\] Процесс обновления статических данных на стороне потребителя](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3940601000&src=contextnavpagetreemode) |
| Контракт | ```<br />/internal_api/v1/static_data/run_invalidate_clean_failed_invalidation_results<br />``` |

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Header |  |  |  |
| Authorization | string | mandatory | Ключ авторизации. |
| Body |  |  |  |
| invalidateStaticDataId | int\[] | mandatory | Ид записи из таблицы CMS.InvalidateStaticData. |
| errorMessage | string | optional | Текст ошибки. |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| N\\A | N\\A | N\\A | N\\A |

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

### Структура ErrorDetails

<table><thead><tr><th colspan="1">Сценарий</th><th><p><em>error.code</em></p></th><th><p><em>error.message</em></p></th><th colspan="1">error.details.code</th><th colspan="1">error.details.message</th><th colspan="1">error.details.attribute</th><th>HTTP код</th><th colspan="1">Пример ответа</th></tr></thead><colgroup><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td colspan="1">Неавторизованный запрос.</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">401</td><td colspan="1">N/A</td></tr><tr><td colspan="1">Ошибка сервера при выполнении запроса.</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">N/A</td><td colspan="1">500</td><td colspan="1">N/A</td></tr><tr><td colspan="1">Переданный значение во входном  параметре <span>invalidateStaticDataId отсутствует в таблице </span> <span>CMS.InvalidateStaticData.</span></td><td colspan="1"><pre><code><span>incorrectValue</span></code></pre></td><td colspan="1"><code><span>Невозможно запустить очистку результатов инвалидации.</span></code></td><td colspan="1"><code><span>invalidateStaticDataId</span></code></td><td colspan="1"><code><span>Один или несколько указанных InvalidateStaticDataId не существуют.</span></code></td><td colspan="1">invalidate_static_data_id</td><td colspan="1">400</td><td colspan="1"><div><p><span><span> </span><span>Свернуть исходный код</span></span></p><table><tbody><tr><td><p><code>{</code><br/><code>    &#34;error&#34;: {</code><br/><code>        &#34;code&#34;:<span> </span>&#34;<span>incorrectValue</span>&#34;,</code><br/><code>        &#34;Message&#34;:<span> </span>&#34;<span>Невозможно запустить очистку результатов инвалидации.</span>&#34;,</code><br/><code>        &#34;details&#34;: {</code><br/><code>            &#34;code&#34;:<span> </span>&#34;<span>invalidateStaticDataId</span>&#34;,</code><br/><code>            &#34;message&#34;:<span> </span>&#34;<span>Один или несколько указанных InvalidateStaticDataId не существуют.</span>&#34;</code>    ,</p><p>                  &#34;attribute&#34;: &#34;invalidate_static_data_id&#34;<br/><code>        }</code><br/><code>    }</code><br/><code>}</code></p></td></tr><tr><td colspan="1"><br/></td></tr></tbody></table><p><br/></p></div></td></tr><tr><td colspan="1">Переданный значение во входном параметре <span>invalidateStaticDataId -  пустой массив</span><span>.</span></td><td colspan="1"><code><span>incorrectValue</span></code></td><td colspan="1"><code><span>Невозможно запустить очистку результатов инвалидации.</span></code></td><td colspan="1"><code><span>invalidateStaticDataId</span></code></td><td colspan="1"><span>Не заполнен обязательный параметр invalidateStaticDataIds.</span></td><td colspan="1">invalidate_static_data_id</td><td colspan="1">400</td><td colspan="1"><div><p><span><span> </span><span>Свернуть исходный код</span></span></p><table><tbody><tr><td><p><code>{</code><br/><code>    &#34;error&#34;: {</code><br/><code>        &#34;code&#34;:<span> </span>&#34;<span>incorrectValue</span>&#34;,</code><br/><code>        &#34;Message&#34;:<span> </span>&#34;<span>Невозможно запустить очистку результатов инвалидации.</span>&#34;,</code><br/><code>        &#34;details&#34;: {</code><br/><code>            &#34;code&#34;:<span> </span>&#34;<span>invalidateStaticDataId</span>&#34;,</code><br/><code>            &#34;message&#34;:<span> </span>&#34;<span>Не заполнен обязательный параметр invalidateStaticDataIds.</span>&#34;</code> ,</p><p>                  &#34;attribute&#34;: &#34;invalidate_static_data_id&#34;<br/><code>        }</code><br/><code>    }</code><br/><code>}</code></p></td></tr><tr><td colspan="1"><br/></td></tr></tbody></table><p><br/></p></div></td></tr></tbody></table>

# Алгоритмы работы метода

## MC.Основной сценарий

1. Проверили наличие каждого ИД из входного параметра invalidateStaticDataId в таблице CMS.InvalidateStaticData .
   
   1. Если один или несколько ИД отсутствуют перешли к EC1.
2. Для каждого ИД из invalidateStaticDataId:
   
   1. Вызвали хранимую процедуру 🗂️ СMS.ClearQueueOnObserverInvalidation \[HotelsStaticApi] .
   2. На вход передали.
      
      | Параметры процедуры | Параметры метода |
      |---|---|
      | InvalidateStaticDataId | invalidateStaticDataId |
      | Error | errorMessage |
3. Вернули код 200.

## EC-1. Формирование ошибки

1. В зависимости от ошибки сформировали тело ответа ошибки .
2. Вернули ответ.

# Связанные документы

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | THB-6081 |