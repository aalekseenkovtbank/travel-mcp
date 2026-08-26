# Общая информация по методу

| Назначение | Постановка задачи на пережатие изображения |
|---|---|
| Бизнес процесс |  |
| Swagger | [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| url | POST /v1/images/resize |

## Структура запроса

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| headers |  |  |  |
| - |  |  |  |
| body |  |  |  |
| images | ImageForResize\[] | MANDATORY | Набор изображения для пережатия |

### Структура ImageForResize

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| path | string | MANDATORY | Путь до изображения в бакете S3 |
| source | string | MANDATORY | Имя источника изображения |

## Структура ответа

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| - |  |  |  |

# Алгоритмы работы метода

## MC.Основной сценарий

1. Выполняется авторизация по значению заголовка Authorization. (Ошибки авторизации: [Common-EC-1](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
2. Выполняется валидация параметров запроса (Ошибки валидации: [Common-EC-3](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2))
   
   | Атрибут | Описание проверки | Код ошибки для атрибута | Текст ошибки для атрибута |
   |---|---|---|---|
   | images.path | Длина имени файла не превышает 255 символов | length\_exceeded | Длина имени файла не должна превышать 255 символов |
   | images.path | Длина пути до директории не превышает 255 символов | length\_exceeded | Длина пути до директории не должна превышать 255 символов |
   | images.source | Длина значения не превышает 100 символов | length\_exceeded | Длина значения не должна превышать 100 символов |
3. Для каждого элемента ImageForResize массива images выполняется добавление следующей записи в таблицу CMS.HotelIImageProcessingQueue
   
   | Колонка | Значение |
   |---|---|
   | Id | Автогенерируемое значение |
   | SourcePath | Директория от пути ImageForResize.s3Path |
   | SourceFileName | Имя файла из пути ImageForResize.s3Path |
   | Source | Параметр ImageForResize.source |
   | Attempts | 0 |
   | CreationDate | Текущая дата и время |
   | ModificationDate | Текущая дата и время |
   | WorkerId | null |
4. Ответ с http = 200 возвращается вызывающей стороне.
5. Основной сценарий завершается.

# Связанные документы

- Travel Hotels: \[[ExtranetWorker](/pages/createpage.action?spaceKey=TRAVELHOTELS&title=ExtranetWorker&linkCreation=true&fromPageId=6969186770) Отправка новых фотографий отеля в Hotel Static API] —

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Исходная версия документа |  | [TTP-15542](https://jira.tcsbank.ru/browse/TTP-15542) - Getting issue details... STATUS |