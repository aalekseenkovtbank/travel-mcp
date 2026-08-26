## Структура запроса GetHotelWithRoomGroupImages (/internal\_api/v1/hotels/hotelinfo)

## Метод удален.

### Структура GetHotelWithRoomGroupImages

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer($int32) | REQUIRED | идентификатор master hotel id |

Структура ответа

### Структура GetHotelWithRoomGroupImagesResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| MasterHotelId | int | REQUIRED | идентификатор master hotel id |
| IsClosed | bool | REQUIRED | Флаг закрыт ли отель |
| Deleted | bool | REQUIRED | Удален ли отель |
| Name | string | REQUIRED |  |
| NameEn | string | REQUIRED |  |
| HotelChanin | string | OPTIONAL |  |
| StarRating | int | REQUIRED |  |
| Images | string:\[] | REQUIRED |  |
| Address | string | REQUIRED |  |
| MasterRegionId | int | REQUIRED |  |
| [Kind](#id-%5BDELETED%5D%5BHotelStaticApi%5DGetHotelWithRoomGroupImages/GetHotelInfo%28/internal_api/v1/hotels/hotelinfo%29-HotelCategory) | enum | REQUIRED |  |
| Coordinates | GeoPoint | REQUIRED |  |
| IanaTimeZone | string | REQUIRED |  |
| CheckInTime | string($timeonly) | OPTIONAL |  |
| CheckOutTime | string($timeonly) | OPTIONAL |  |
| Phone | string | OPTIONAL |  |
| Email | string | OPTIONAL |  |
| Description | string | REQUIRED |  |
| Facts | string | REQUIRED |  |
| AmenityGroups | [AmenityGroup](#id-%5BDELETED%5D%5BHotelStaticApi%5DGetHotelWithRoomGroupImages/GetHotelInfo%28/internal_api/v1/hotels/hotelinfo%29-AmenityGroup)\[] | REQUIRED |  |
| MetapolicyExtraInfo | string | OPTIONAL |  |
| Metapolicy | string | REQUIRED |  |
| PaymentMethods | string | REQUIRED |  |
| Region | string | REQUIRED |  |
| Policy | string | REQUIRED |  |
| RoomGroups | [RoomGroup](#id-%5BDELETED%5D%5BHotelStaticApi%5DGetHotelWithRoomGroupImages/GetHotelInfo%28/internal_api/v1/hotels/hotelinfo%29-RoomGroup)\[] | REQUIRED |  |