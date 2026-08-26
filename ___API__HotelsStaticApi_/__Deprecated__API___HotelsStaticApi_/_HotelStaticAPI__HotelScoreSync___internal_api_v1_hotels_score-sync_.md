# Общая информация

<table><colgroup><col/><col/></colgroup><tbody><tr><th colspan="1">Назначение</th><td colspan="1">Запуск процесса полного обновления значений score для отелей</td></tr><tr><th><p>Бизнес-процессы</p></th><td><p><ac:placeholder>Перечень ссылок на связанные бизнес-процессы</ac:placeholder></p></td></tr><tr><th colspan="1">Контракт</th><td colspan="1"><ac:placeholder>Ссылка на swagger или другую схему, описывающую протокол</ac:placeholder></td></tr></tbody></table>

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| - |  |  |  |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| - |  |  |  |

# Интеграционная схема

```plantuml
[CDATA[@startuml
Actor Admin
database CMSDatabase
Participant HotelStaticAPI
Participant SearchIndexManager

activate Admin
Admin-HotelStaticAPI ++  : Запуск процедуры синхронизации
HotelStaticAPI-->Admin -- : 200 Ok
deactivate Admin

HotelStaticAPI->HotelStaticAPI: Запустить задачу на синхронизацию score отелей
group Задача на синхронизацию score отелей
activate HotelStaticAPI
loop пока nextOffset != null
HotelStaticAPI->SearchIndexManager ++: Запрос следующий batch
SearchIndexManager-->HotelStaticAPI --: batch
    alt Если первая пачка для загружамой версии
    HotelStaticAPI->CMSDatabase ++: Начать синхронизацию для версии score
    CMSDatabase-->HotelStaticAPI -- : Синхронизация для версии score стартовала
    else Если версия текущей пачки score отличается от уже загруженных 
    HotelStaticAPI -> CMSDatabase ++ : Очистить буфер для сохранения score
    CMSDatabase-->HotelStaticAPI -- : Буффер очищен
    else Если версия текущей пачки score совпадает с уже загруженными или это первая пачка для версии
    HotelStaticAPI->CMSDatabase ++: Сохранить пачку hotelScores в буфер
    CMSDatabase-->HotelStaticAPI -- : Вернуть коллекцию hotelIds для которых не найден отель
    end 
end
HotelStaticAPI->CMSDatabase ++ : Закончить синхронизацию для версии score
CMSDatabase-->HotelStaticAPI -- : Все hotelScores для версии score сохранены в таблицу отелей
end
deactivate HotelStaticAPI
@enduml]]>
```

# Алгоритмы работы метода

## MC.Основной сценарий

01. Обрабатывается полученный запрос.
02. Возвращается ответ вызывающей стороне с http 200.
03. В качестве значения переменной syncDateTime сохраняется значение Текущей даты и времени.
04. Формируется и отправляется запрос к методу [GetScoreHotels](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BSearchIndexManager%5D+GetScoreHotels)
    
    | Параметр | Значение |
    |---|---|
    | limit | Значение конфигурационного параметра hotelsScoreSyncRequestLimit |
    | offset | Значение переменной nextOffset<br />Не передается в случае если nextOffset == null |
05. Разбирается полученный ответ и выполняется проверка, что возвращен HTTP 200. (Неуспешная проверка: описание ошибки сохраняется в лог)
    
    1. При обработке первого ответа выполняется .
    2. В случае если значение переменной (ранее сохраненной в рамках получения предыдущей порции данных) previousResponseScoreVersion != null выполняется проверка, что previousResponseScoreVersion == scoreVersion, полученное в ответе [GetScoreHotels](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BSearchIndexManager%5D+GetScoreHotels).
       
       1. В случае неуспешной проверки выполняется .
06. В качестве значения переменной previousResponseScoreVersion сохраняется значение scoreVersion, полученное в ответе [GetScoreHotels](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BSearchIndexManager%5D+GetScoreHotels).
07. Выполняется сохранение массива score отелей - .
08. Выполняется проверка, что значение nextOffset, полученное в ответе [GetScoreHotels](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BSearchIndexManager%5D+GetScoreHotels), пустое.
    
    1. В случае неуспешной проверки в качестве значения переменной nextOffset сохраняется значение nextOffset, полученное в ответе [GetScoreHotels](https://wiki.tcsbank.ru/display/TRAVELHOTELS/%5BSearchIndexManager%5D+GetScoreHotels) и запускается повторно с Шага 3.
09. Выполняется постобработка сохраненных в очереди обновлений score отелей - .
10. Основной сценарий завершается.

## SC-1.Старт синхронизации версии скоров

1. Выполняется обращение к ХП HotelScoreSync со следующими параметрами:
   
   | Параметр | Значение |
   |---|---|
   | SyncVersion | scoreVersion |
   | Status | '1' |
2. ХП HotelScoreSync проверяет, что в таблице UpdateQueue отсутствуют записи, для которых UpdateQueue.Status == '4'.
   
   1. В случае неуспешной проверки сценарий завершается, ошибка записывается в лог.
   2. В случае если найден хотя бы один экземпляр и хотя бы для одно найденного экземпляра UpdateQueue.QueueName == SyncVersion возвращается ошибка 'Sync &lt;SyncVersion&gt; already exists'
   3. В случае если для найденных экземпляров UpdateQueue.QueueName != SyncVersion возвращается ошибка 'Sync &lt;SyncVersion&gt; not completed'
3. Продолжается выполнение .

## SC-2.Очистка очереди обновлений

1. Выполняется обращение к ХП HotelScoreSync со следующими параметрами:
   
   | Параметр | Значение |
   |---|---|
   | SyncVersion | scoreVersion |
   | Status | '3' |
2. ХП HotelScoreSync удаляет записи UpdateQueue, для которых UpdateQueue.QueueName == SyncVersion и UpdateQueue.TableName == 'HotelScore'.
3. запускается повторно с Шага 3.

## SC-3.Сохранение Score в очередь обновлений

1. Для каждого экземпляра hotelId, полученного в массиве hotelScores выполняется поиск экземпляра Hotel, для которого Hotel.HotelId == hotelScores/hotelId.
   
   1. В случае если экземпляр Hotel не найден - соответствующий экземпляр игнорируется, описание ошибки сохраняется в лог.
2. Выполняется обращение к ХП UpdateHotelScore со следующими параметрами:
   
   | Параметр | Значение |
   |---|---|
   | ScoreBatchJson | JSON содержимое элемента hotelScores |
   | SyncVersion | значение переменной scoreVersion |
   | SyncDateTime | значение переменной syncDateTime |
3. ХП SaveHotelScoreFullSyncResults для каждого экземпляра hotelId, полученного в массиве hotelScores выполняет поиск экземпляра Hotel, для которого Hotel.HotelId == hotelScores/hotelId.
   
   1. В случае если экземпляр Hotel не найден - соответствующий экземпляр игнорируется.
4. ХП SaveHotelScoreFullSyncResults для каждого экземпляра hotelId сохраняет экземпляр UpdateQueue
   
   | Атрибут | Значение |
   |---|---|
   | UpdateQueueID | Автоинкрементируемый идентификатор записи |
   | TableName | 'HotelScore' |
   | Data | Описание загружаемых данных в формате JSON |
   | -&gt;HotelId | hotelScores.hotelId |
   | -&gt;Fields | Массив именованных скоров, полученных в hotelScores/scores |
   | -&gt;-&gt;Name | hotelScores/scores/scoreName |
   | -&gt;-&gt;Value | hotelScores/scores/scoreValue |
   | -&gt;SyncDateTime | SyncDateTime |
   | User | system\_user |
   | CreateDate | Текущая дата и время |
   | StartDate | null |
   | FinishDate | null |
   | Status | 4 |
   | Message | null |
   | QueueName | SyncVersion |
5. Продолжается выполнение .

## SC-4.Применение изменений из очереди

1. Выполняется обращение к ХП UpdateHotelScore со следующими параметрами:
   
   | Параметр | Значение |
   |---|---|
   | SyncVersion | scoreVersion |
   | Status | '2' |
2. ХП UpdateHotelScore для каждого экземпляра UpdateQueue, для которого UpdateQueue.Status == 0 и UpdateQueue.QueueName == SyncVersion выполняет обновление экземпляров HotelScore в соответствии со следующими правилами:
   
   1. В случае если среди экземпляров HotelScore не найдено экземпляра, для которого HotelScore.HotelId == UpdateQueue.Data.HotelId и HotelScore.ScoreName == UpdateQueue.Data.Fields.Name, выполняется добавление соответствующего экземпляра HotelScore.
      
      | Атрибут | Значение |
      |---|---|
      | HotelScoreId | Автоинкрементируемый идентификатор записи |
      | HotelId | UpdateQueue.Data.HotelId |
      | ScoreName | UpdateQueue.Data.Fields.Name |
      | ScoreValue | UpdateQueue.Data.Fields.Value |
      | ScoreDate | UpdateQueue.Data.ScoreDate |
   2. В случае если среди экземпляров HotelScore найден экземпляр, для которого HotelScore.HotelId == UpdateQueue.Data.HotelId и HotelScore.ScoreName == UpdateQueue.Data.Fields.Name и HotelScore.ScoreDate &lt; UpdateQueue.Data.SyncDateTime выполняется обновление соответствующего экземпляра HotelScore.
      
      | Атрибут | Значение |
      |---|---|
      | ScoreValue | UpdateQueue.Data.Fields.Value |
      | ScoreDate | UpdateQueue.Data.ScoreDate |
   3. В случае если среди экземпляров HotelScore найден экземпляр, для которого в соответствующем (по HotelScore.HotelId == UpdateQueue.Data.HotelId) экземпляре UpdateQueue отсутствует элемент, для которого UpdateQueue.Data.Name == HotelScore.ScoreName и HotelScore.ScoreDate &lt; UpdateQueue.Data.SyncDateTime, выполняется удаление соответствующего экземпляра HotelScore.
3. После успешной обработки ХП UpdateHotelScore обновляет значение UpdateQueue.Status = 2.
   
   1. В случае если в ходе обработки экземпляра UpdateQueue возникло исключение, ХП UpdateHotelScore обновляет значение UpdateQueue.Status = 3.
4. Продолжается выполнение .

# Конфигурационные параметры

| Параметр | Значение | Описание |
|---|---|---|
| hotelsScoreSyncRequestLimit | 5000 | Количество отелей в одном запросе, для которых необходимо получить значение Score |

# Метрики и алерты

1. Алерт на ошибки, возникающие в ходе работы алгоритма асинхронного процесса.

# Связанные документы

## Конфигурационные параметры

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | THB-4144 |
| 2 | Расширена модель скоров для задачи AB-тестов | Текущая | THB-5397 |