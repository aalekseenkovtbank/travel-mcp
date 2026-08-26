# Общая информация по сервису

| Назначение | Получение актуальных данных справочника \[TravelDB].\[**MealType**] |
|---|---|
| Бизнес процесс | –– |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html)<br />```<br />/internal_api/v1/dictionaries/mealTypes<br />``` |

# **Входные параметры**

Отсутствуют

# **Выходные параметры**

Массив элементов, сгруппированных по **Id**

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| id | int | mandatory | Идентификатор типа питания<br />\[TravelDB]..\[MealType].**MealTypeId** |
| name | string | mandatory | Наименование типа питания<br />\[TravelDB]..\[MealType].**Name** |
| code | string | OPTIONAL | Код типа питания<br />\[TravelDB]..\[MealType].**Code** |

# **Алгоритм работы метода**

1. Разбирается полученный запрос
2. Выполняется валидация параметров запроса с обработкой перечисленных ниже ошибок согласно имеющейся [классификации](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=3602654421#id-%D0%9E%D0%B1%D1%89%D0%B8%D0%B5%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8%5BHotelsStaticAPI%5D-%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%D0%BE%D0%B1%D1%89%D0%B8%D1%85%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D1%87%D0%BD%D1%8B%D1%85%D1%81%D1%86%D0%B5%D0%BD%D0%B0%D1%80%D0%B8%D0%B5%D0%B2):
   
   - **EC-1**. Не авторизованный запрос
   - **EC-2**. Ошибка сервера при выполнении запроса
3. В ответе возвращается и актуальное состояние справочника на момент запроса
   
   - В случае успеха – возвращается 200ок