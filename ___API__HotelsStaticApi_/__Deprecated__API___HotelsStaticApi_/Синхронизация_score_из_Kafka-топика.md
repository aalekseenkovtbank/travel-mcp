# Общая информация

<table><colgroup><col/><col/></colgroup><tbody><tr><th colspan="1">Назначение</th><td colspan="1">Процесс инкрементального обновления скоров отелей</td></tr><tr><th><p>Бизнес-процессы</p></th><td><p><ac:placeholder>Перечень ссылок на связанные бизнес-процессы</ac:placeholder></p></td></tr><tr><th colspan="1">Спецификация </th><td colspan="1">[SearchIndexManager] to Kafka-топик &#34;UpdateScoreHotels&#34;</td></tr></tbody></table>

## Краткое описание

Есть необходимость актуализировать "скор" рейтинг популярности отелей для того, чтобы suppliers-search-api мог ранжировать выдачу отелей для affiliate - hotel-api. Данные с измененным скором попадают в топик hotels-backend.score-hotels.  
Топик на тесте - [devplatform](https://devplatform.tcsbank.ru/tenants/hotels-backend/kafka/topics/view/16693)

## Интеграционная схема

```plantuml
[CDATA[@startuml
title "Get score from Kafka-topic"   

Participant StaticApi
Participant Kafka 
Participant HotelsSearchApi
database TravelDB

	HotelsSearchApi - Kafka: Сообщение с изменением score отеля
StaticApi-> Kafka: Вычитывает сообщение

Alt Нашли отель с hotelId из сообщения
	StaticApi->TravelDB: Обновление Hotel.Score отеля
else Не нашли отель с пришедшим hotelId

    StaticApi -> StaticApi: ERROR в логи с пришедшим hotelId

end

@enduml]]>
```

## Алгоритм

### MC.Основной сценарий

1. Consumer слушает топик hotels-backend.score-hotels
2. При появлении в топике нового сообщения запускается процесс обработки:
   
   1. Вычитывается сообщение
      
      `{`  
      `"hotelId": "123",`  
      `"score": "12.7"`  
      `}`
      
      {
      
          "type": "record",  
          "name": "scores",  
          "fields": [  
               {  
                   "name": "hotelId",  
                   "type": "string"  
              },  
              {  
                  "name": "score",  
                  "type": "double"  
              }  
          ]  
      }
   2. Новый score сохраняется в поле CMS..Hotel → Score
      
      1. Если пришел score == 0, необходимо в CMS..Hotel → Score записать значение null, поскольку 0 в данном случае означает удаление скоринга для данного отеля
      2. Если отель с hotelId из сообщения не был найден, записывается WARN в лог и инкрементится метрика на общее количество полученных сообщений с несуществующими отелями
      3. Если сохранение скора в базу не прошло успешно, ретраить 3 раза с увеличивающимся промежутком, если не получилось сохранить на 3й раз - записать ERROR в лог
3. Основной сценарий завершается