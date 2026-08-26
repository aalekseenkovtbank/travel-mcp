| Назначение | Получение статической информации об отеле |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/hotels/hotel |

# То же самое, что [\[HotelStaticApi\] GetHotelInfos (/internal\_api/v2/hotels/hotelinfolist)](/pages/viewpage.action?pageId=3303420240)

## Структура запроса

### Структура GetHotelInfo

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer:\[] | REQUIRED | Идентификаторы master-отелей |