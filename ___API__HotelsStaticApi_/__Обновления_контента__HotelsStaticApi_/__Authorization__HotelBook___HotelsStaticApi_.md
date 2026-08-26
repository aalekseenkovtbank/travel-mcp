# Общая информация

| Назначение | Авторизация в системе для выполнения последующих запросов |
|---|---|
| HTTP-метод запроса | POST |
| URL Path | HotelbookSettings.ApiUrl [⚙️](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6023572719) /api/v1/{\_locale}/gateway/login |
| Документация | [/api/v1/{\_locale}/gateway/login](https://api.hbpro.expert/docs/#section/Description-%28rus%29) |

# Описание контракта

## Структура запроса

| Параметр | Описание | Заполнение |
|---|---|---|
| **Header-параметры** |  |  |
| Authorization | Токен авторизации |  |
| **Path-параметры** |  |  |
| \_locale | Язык ответа | ru |

## Структура ответа

| Параметр | Описание | Примечание |
|---|---|---|
| **Body-параметры** |  |  |
| login | Логин для авторизации в сервисе | HotelbookSettings.Login [⚙️](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6023572719) |
| password | Пароль для авторизации в сервисе | HotelbookSettings.Password [⚙️](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6023572719) |

## Коды ответов

| Код | Обработка ошибки | Пример ответа |
|---|---|---|
| 400 | В соответствии с общей обработкой ошибок - [EC-7](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6082759534#id-%F0%9F%93%97%D0%9E%D0%B1%D1%89%D0%B0%D1%8F%D0%BE%D0%B1%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%BA%D0%B0%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D0%BA%5BHotelBook%5D%5BHotelsStaticApi%5D-EC-7.%D0%9E%D1%88%D0%B8%D0%B1%D0%BA%D0%B0%D0%BA%D0%BB%D0%B8%D0%B5%D0%BD%D1%82%D0%B0HotelBook) | ```json<br />{
  "description": "string",
  "details": {
    "errorCode": "string",
    "errorId": "string"
  },
  "title": "string"
}<br />``` |
| 401 |  |  |
| 403 |  |  |
| 422 |  |  |
| 500 | В соответствии с общей обработкой ошибок - [EC-8](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=6082759534#id-%F0%9F%93%97%D0%9E%D0%B1%D1%89%D0%B0%D1%8F%D0%BE%D0%B1%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%BA%D0%B0%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D0%BA%5BHotelBook%5D%5BHotelsStaticApi%5D-EC-8.%D0%9E%D1%88%D0%B8%D0%B1%D0%BA%D0%B0%D1%81%D0%B5%D1%80%D0%B2%D0%B5%D1%80%D0%B0HotelBook) |  |

# Связанные документы

- ⚙️ Загрузка контента поставщиков \[Конфигурация] \[HotelsStaticApi]
- 📗 Обработка ошибок \[HotelBook] \[HotelsStaticApi]

# Изменения

| № | Описание изменений | Примечание |
|---|---|---|
| 1 | HTLS-4128 |  |