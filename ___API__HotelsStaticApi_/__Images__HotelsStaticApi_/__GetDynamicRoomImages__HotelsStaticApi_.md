# Общая информация

<table><colgroup><col/><col/></colgroup><tbody><tr><th colspan="1">Назначение</th><td colspan="1">Получить список ссылок на мастер-изображения по коллекции ссылок на изображения поставщиков</td></tr><tr><th><p>Бизнес-процессы</p></th><td><p><ac:placeholder>Перечень ссылок на связанные бизнес-процессы</ac:placeholder></p></td></tr><tr><th colspan="1">Контракт</th><td colspan="1"><span>POST<a href="https://hotels-static-api-private.hotels-static-api-qa2.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html?urls.primaryName=1.0#/InternalApi/post_internal_api_v1_hotel_image_get_dynamic_room_images"><span>/internal_api/v1/hotel-image/get-dynamic-room-images</span></a></span></td></tr></tbody></table>

# Протокол

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Query/path |  |  |  |
| internal\_api/v1/hotel-image/get-dynamic-room-images |  | mandatory |  |
| Body |  |  |  |
| ```json<br />{
    "supplier_images":[ 
        {
            "supplier_id": 39,
            "image_url": "url"
        }
     ]
}<br />``` | json |  |  |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| Body |  |  |  |
| ```json<br />{
  "images":[ 
      {
          "supplier_id": 39,
          "supplier_image_url": "url",
          "public_image_url": "url"
      }
   ]
}<br />``` | json |  | public\_image\_url - Url мастер-изображение. Null если картинка не загружена |

### Структура объекта

Описание используемых в запросе или ответе сложных типов

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
|  |  |  |  |

## MC.Основной сценарий

1. Из переданной коллекции ссылок supplier\_images.image\_url посчитать хэш используя метод из существующей библиотеки  hash = StringHashHelper.GetDeterministicHashCode(string str).
2. Используя полученный хэш получить из таблицы dynamic\_room\_images список ссылок на мастер-изображения **hash == dynamic\_room\_images.supplier\_image\_path\_hash + dynamic\_room\_images.supplier\_id == supplier\_images.supplier\_id**
3. Для ссылок по которым не найдены соответствия, необходимо вернуть ***null***.

**Завершить сценарий.**

## Схема `dynamic_room_images`

| Колонка | Значение | Комментарий |
|---|---|---|
| id | int |  |
| supplier\_id | int |  |
| supplier\_image\_path\_hash | int |  |
| image\_path | string |  |
| created\_at | timestamp |  |
| updated\_at | timestamp |  |

# Конфигурационные параметры

Перечень конфигурационных параметров, используемых в рамках алгоритмов работы методово

| Параметр | Значение | Описание |
|---|---|---|
|  |  |  |

# Метрики и алерты

В случае нахождения более одной записи в таблице `dynamic_room_images`по полям supplier\_id + supplier\_image\_path\_hash, записать ошибку в лог:

***Duplicate dynamic image records found***

# Связанные документы

## Конфигурационные параметры

# История изменений

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  |  |