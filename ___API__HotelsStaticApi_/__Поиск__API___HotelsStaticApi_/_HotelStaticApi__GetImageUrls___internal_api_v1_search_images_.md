# Метод GetImageUrls (/internal\_api/v1/search/images)

| Назначение | Получение адресов всех фотографий по списку отелей |
|---|---|
| Бизнес процесс | TBD |
| Swagger | QA: [https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html](https://hotels-static-api-private.hotels-static-api-qa.internal.ya-ruc1-dev1.dev.k8s.tcsbank.ru/swagger/index.html) |
| Интеграционное тестирование | TBD |
| URL | /internal\_api/v1/search/images |
| Метод | POST |

## Структура запроса

### Header запроса

| Параметр | Значение |
|---|---|
| HotelsStaticApi.Authorization | Ключ авторизации |

### Структура SearchByHotelsIdApiRequest

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| masterHotelId | integer:\[] | REQUIRED | Массив идентификаторов master-отелей |

## Структура ответа Int32StringListDictionaryPayloadApiResponse

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| payload | Dictionary&lt;int, string\[]&gt; | REQUIRED | ключ - идентификатор отеля (master hotel id)<br />значение - массив url фото отеля |

# Ошибки: коды и описания

### Структура Error

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки |
| message | string | OPTIONAL | Текст ошибки |
| details | \[] | OPTIONAL | Описание ошибок валидации |

### Структура ErrorDetails

| Параметр | Тип | Обязательность | Описание |
|---|---|---|---|
| code | string | REQUIRED | Код ошибки атрибута |
| message | string | OPTIONAL | Текст ошибки атрибута |
| attribute | string | REQUIRED | Код атрибута |

| Сценарий | *error.code* | *error.message* | error.details.code | error.details.message | error.details.attribute | HTTP код | Пример ответа |
|---|---|---|---|---|---|---|---|
| Неавторизованный запрос | N/A | N/A | N/A | N/A | N/A | 401 | N/A |
| Ошибка сервера при выполнении запроса | N/A | N/A | N/A | N/A | N/A | 500 | N/A |
| Не передан обязательный параметр masterHotelId | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Идентификаторы master-отелей не могут быть пустыми. | masterHotelId | 400 | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Идентификаторы master-отелей не могут быть пустыми.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Идентификатор master-отеля равен нулю. | incorrectValue | Ошибка при валидации запроса. | noMasterHotelId | Хотя бы один идентификатор master-отеля должен быть не нулевым. | masterHotelId |  | ```json<br />{
	"error": {
		"code": "incorrectValue",
		"Message": "Ошибка при валидации запроса.",
		"details": {
			"code": "invalidDataFormat",
			"message": "Хотя бы один идентификатор master-отеля должен быть не нулевым.",
			"attribute": "masterHotelId"
		}
	}
}<br />``` |
| Не существует отеля с указанным masterHotelId | N/A | N/A | N/A | N/A | N/A | 204 | N/A |

# Алгоритм работы метода HotelSupplierMapping

## MC. Основной сценарий

1. Выполняется авторизация по предоставленному apiKey.
2. Разбор и валидация запроса.
3. Вызывается хранимая процедура HotelStaticApi\_GetHotelsImages в TravelDB с параметром @HotelID = masterHotelId
4. Выполняется выборка из таблицы TravelDB.HotelImage значения HotelImage.ImagePath, для которых HotelImage.HotelId = @HotelID
5. Производится маппинг данных, полученных в результате работы хранимой процедуры на модель Int32StringListDictionaryPayloadApiResponse

# Маппинг данных на модель Hotel Static API

| Параметр | Источник данных |
|---|---|
| payload |  |
| -&gt;key | TravelDB.HotelImage.HotelId |
| -&gt;value | TravelDB.HotelImage.ImagePath |

# Пример использования

## Запрос

```json
{
  "masterHotelIds": [
    1426291, 1406924
  ]
}
```

## Ответ

```json
{
  "payload": {
    "1406924": [
      "https://cdn.worldota.net/t/{size}/extranet/f7/c2/f7c278015af01bbca4bd4a87bd84020bd90c4b19.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f7/60/f7600fbc88ba77b7d4f4a926cd5be325959dbca8.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/b4/d2/b4d2f9118b92274acdb43a29931778238f0dcd1d.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/22/f0/22f0c4ba7667e768cf27ae7e178485f8b9129ee8.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/66/e1/66e178a538790626c2568f71f491a1476256d640.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/e0/67/e067e340a70860272d101b618b54804525441e03.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/3f/ea/3feac07b754d2ad0e5281d435f2e8dc10938a83a.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/78/f2/78f26838dac15bdb1eec2cfd409477edc08e3df4.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/e7/1e/e71e3dd7bed8f35984325b5a2590e788ad85f712.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/9c/56/9c562aa7e56cb5fade3980bed3ff88d03c72447a.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/a6/f7/a6f70a1d777c2ad0102d089476b1b52b89a9e30f.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/29/93/299304604dc7cf303dddeb8965c478dfd9407518.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/c9/be/c9be933e45b2abea17fae5a7c0b2237239876149.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/11/77/1177cfadc17451dd88fb94a7845bb07e80317aad.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/23/0e/230e61feda12daa7094e0c2a0fd64399b5e78ccf.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/54/21/5421cba1a6de96b956f2af29cdf3e7b706ccb023.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/31/70/317019239dbb97908adccc33f78029d25907eb9e.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/46/06/460623dcb2c08036a6542d790631f7f2bf7c0399.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/53/5e/535e5483893d2899904ba9481e9e1a8829d0ef01.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/85/9f/859f00f9b787acdbcafd89b6593eef8711f78727.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/53/d2/53d23fa4a2a84535d8efaf61705a283cdcf13748.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/98/76/98769b241c8f01c0991f7d6d732034a0380a9413.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f8/1b/f81ba6130c7cd8a24ad83d3c1475e1d5592a0574.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/b0/7e/b07e338052842e67081cf83f8575a18bf29a6954.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f5/96/f596312d8aabd536eee9f4fd5cecb6df58cce091.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f6/5c/f65c207b212d49f72528c3ede9eeb21555ef3463.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/e5/08/e508d42c12a07e50da0526845b5c39147218a733.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/64/49/6449d3f21af1c099192d9cdb7c591f8f6fb2b8b4.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/4f/35/4f358afeb35bae72358dde4582b1aa5c999b019d.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/77/45/77451ab0ba13a1c3232661788b5777c6cf95175a.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/5e/83/5e83f569ead8d1f38e1d73938ae6cf906a581458.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/cb/f9/cbf9ce8d0ba6360d9195b29419273c144589b69e.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/ce/d9/ced9bca7c7e504fc2265478f38793043d2296ce3.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/49/4f/494ff14ca5622af084b5ebf45fce14b4c01bc86c.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/91/74/9174e153ef74b91ec32e6b72a7a20c57b874ec36.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/b3/27/b3272fd6e36b0809d93b5914a64575904f7fbfd4.jpeg"
    ],
    "1426291": [
      "https://cdn.worldota.net/t/{size}/extranet/96/98/96983f21e5e46addb8d699744dd4e270a3ec0911.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/b8/5a/b85aba206a343aba17ed4ad325f3fcfead419f49.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/4d/eb/4deb934f4cc23d4b2a1945e732589c0cc7aa27b4.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/c3/37/c3373766818b22bb75e7e718860cdba3c361d5fa.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/a6/d3/a6d391ca697939ec214c2da89344fa6de7271081.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/bd/3e/bd3e927c5d6c043d57df1ca390a85ac5d4f05d39.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/8f/82/8f82acaec9ad41ec542ced6726ffd31b53fc0653.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/3d/a2/3da2d20c91e7a52fa27c5e6da0dd40d557befb03.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/1d/d3/1dd3b75e3d8b4f4eb29107f923f4287963497e65.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/59/14/5914bde960a96b36d09fd45fb2cdef96fcd9112b.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/79/ff/79ff77d7490389c4c90926b3c54f9af7cc5a17d2.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/64/e5/64e516047dd4178599b38950bdca0b2b588ecd02.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/8c/ef/8cefd2b48b0db0400d474c01da60d4cd997faec1.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/7f/21/7f213867f9afccb03a30ca71d79dd16ed7600574.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/4d/57/4d57f19de504c99503b6324380130ec8da1fe2e5.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/dd/89/dd898c79eaebae9c6ca10a5f202ef1f608622c73.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/d9/30/d930e2d278ae412eb342907b52f2d52ebd53eb58.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/6a/eb/6aebf3b4202375f322add4b2f05b37fed0add8b2.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/86/77/8677104199625a5c0771f5c05d938cd716fca6a8.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/37/c7/37c716ecfd5314b379b0612b99f4787567c7c82a.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/b6/0b/b60bc89a433e6e40ce60e7ab41e4fe7e1d1088be.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/11/46/1146d6db0c675db8f15bf40fb3e3b928e8652a4c.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/56/33/5633fd9ecdff26bf188eaf9046fe2cfa07d2f71c.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f9/e0/f9e05584ee7466c0b87e1e77b062f194761a5818.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/23/f7/23f7a6405116c91d5760e7b9723acdb8d65b5519.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/0f/04/0f04bd2c5128e17422fcd1eaf7ed2cf3db532d4e.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/22/99/229930dad354ec0c5202b983fd8e333a2386a1b2.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/d2/78/d278cc5db3e4b638e8863e274b695a8cb7c3c487.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/64/1d/641dbc71d91d8054499c0271f33b52b5fa63bc34.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/77/00/7700568c75f2486315711f98a99d8c1b33837606.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/07/c4/07c4168c798de97b2404f34ecc24a16a6430359d.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/fd/a2/fda2ab0a95a3c9c4fedbbab24c6976f3a7fb487d.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f8/26/f8266d50805e363a9e77a7707385b082ef5f9628.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/5e/21/5e212eec6e95e25611ec02acf1f95369be3c8469.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/be/45/be45450ce587c7f4ef80f64168bf4c9a74ae86b5.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/20/db/20db27200a4c1358b665acc9bc04a9fa4cdd789a.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/1d/46/1d461c04eb31cc7d5ef3dd298de394824093a2ce.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/3f/40/3f402005e4e7660784b38bd802707c3cba2bcdd1.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/34/ef/34ef90ef8472cfa4fda5f48deb90424f9fea5915.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/fc/78/fc789c7629a8d4667176bd2068354c37dc508db5.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/2a/b4/2ab47b99d90e9c8f9f053531930c36d0bd5d1605.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/f2/de/f2de6a57ffd5b5d173e276debd9a3ef821c5b584.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/73/a1/73a1419bde5988a3114cf6213cfccf22663d8be5.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/08/dc/08dc064379d00b6b0b37d5b5c0caef58d94c8fd7.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/c9/77/c977acc3956306473c19b8fb8577637dbe2dc8e7.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/16/1c/161c5fac5ca28a0420d5367e2589e7e54ad5268e.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/2b/be/2bbea2b1a14e1f36b711ed11e1b16270ae9b8f46.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/00/69/00697c4913a784b12fa7a194f667251b715fa2c1.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/8e/55/8e559382b2d3deb941d2468fd08939b8185b868c.jpeg",
      "https://cdn.worldota.net/t/{size}/extranet/media/e514ab7e116a4e12a53d79091b85dc72.jpg"
    ]
  }
}
```

# Изменения

| Версия | Изменение | Версия страницы | Задача |
|---|---|---|---|
| 1 | Документация существующего метода | **[v.](https://wiki.tcsbank.ru/pages/viewpage.action?pageId=2751197635) 1** |  |