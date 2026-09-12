# T-Bank MCP: доступные вызовы и текущий статус

Контракт `tools/list`, имена и режимы сверены: **10 сентября 2026,
Europe/Moscow**. Живые статусы источников в таблицах зафиксированы по проверке
**10 сентября 2026** для `afisha_catalog`; остальные статусы сохраняют указанные
ниже даты и ограничения.

Единый T-Bank MCP успешно запускается по stdio и публикует **106 инструментов**:

- **88 READ** — только чтение;
- **12 WRITE** — меняют состояние локально или во внешней системе, но сами по
  себе не списывают деньги;
- **6 MONEY** — могут начать или завершить списание.

Во время проверки запускались **только READ-вызовы**. Переводы, оплаты, бронирования,
сообщения, загрузка файлов и изменения корзины не выполнялись.

## Обозначения

| Значок | Значение |
|---|---|
| ✅ | Подтверждён живым успешным запросом в этой сессии |
| 🟡 | Опубликован MCP, но живой вызов не делался: нужен ID, пользовательский ввод или приватный результат |
| 🟠 | Доступен с обязательным контекстом или поддержан частично |
| 🔴 | Сейчас не работает из этой среды |
| ⛔ | Намеренно не запускался: меняет данные или может списать деньги |

Режимы: `R` — чтение, `W` — изменение без прямого списания, `₽` — денежная операция.

## Сессия

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `login(phone)` | W | ⛔ | Начинает новый вход |
| `confirm_otp(otp)` | W | ⛔ | Подтверждает SMS-код |
| `confirm_password(password)` | W | ⛔ | Шаг авторизации |
| `confirm_pin(pin)` | W | ⛔ | Шаг авторизации |
| `refresh_session()` | W | ⛔ | Обновляет и сохраняет сессию |
| `session_status()` | R | ✅ | Сессия активна |
| `keepalive()` | R | ✅ | Пинг проходит |
| `push_unread_count()` | R | ✅ | Счётчик push отвечает |

## Счета и операции

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `list_accounts()` | R | ✅ | Счета, балансы и идентификаторы карт |
| `list_operations(account_id, days=30, limit=50)` | R | ✅ | Проверено на одном реальном счёте |
| `spending_categories(account_id, days=30)` | R | ✅ | Категории трат отвечают |
| `operations_histogram(account_id="", days=30)` | R | ✅ | Проверена дневная группировка по категориям |
| `audience_profile()` | R | ✅ | Возвращает только возрастной диапазон и допустимость 18+, без даты рождения и пола |
| `trip_personalization_profile(...)` | R | 🟡 | Агрегированный бюджет и предпочтения поездки без сырых операций и банковских данных |
| `get_data(section, arg="", days=30)` | R | ✅ | Проверена секция `services`; доступны и другие секции из схемы инструмента |

## Карты и документы

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `list_cards()` | R | ✅ | Список карт отвечает |
| `card_limits(ucid)` | R | 🟡 | Нужен `ucid` из `list_accounts()` |
| `card_requisites(ucid, reveal=False)` | R | 🟡 | Приватные реквизиты; намеренно не запрашивались |
| `card_operations(card_id, days=30, limit=50)` | R | 🟡 | Нужен `card_id` |
| `account_requisites(account_id, currencies="RUB")` | R | 🟡 | Приватные реквизиты; намеренно не запрашивались |
| `documents(kind="", include_others=False)` | R | ✅ | Хранилище документов отвечает |
| `bank_documents()` | R | ✅ | Банковские справки отвечают |
| `insurance_policies()` | R | 🔴 | `api.tinsurance.ru`: сетевой `ConnectTimeout` |
| `payment_receipt(payment_id, save_to="")` | W | ⛔ | Скачивает чек в локальный файл; не запускался |

## Заказы

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `orders(kind="", limit=10)` | R | ✅ | Общий список заказов отвечает |
| `order_details(order_id)` | R | 🟡 | Нужен ID заказа кино/афиши |
| `travel_order_details(order_id)` | R | 🟠 | Отели поддержаны; для авиа и ЖД полная веб-сессия пока не реализована |

## Продукты и доставка

Для большинства вызовов сначала нужны `app_id` и `point_id` из `grocery_stores()`.

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `grocery_stores()` | R | ✅ | Магазины по сохранённому адресу отвечают |
| `grocery_search(query, app_id, point_id)` | R | ✅ | Проверено с контекстом магазина |
| `grocery_rank(query, app_id, point_id)` | R | ✅ | Проверено с контекстом магазина |
| `grocery_good_info(good_id, app_id, point_id)` | R | 🟡 | Нужен ID товара |
| `grocery_plan_order(ingredients, app_id, point_id)` | R | 🟡 | Нужны ингредиенты и магазин |
| `grocery_cart(app_id, point_id)` | R | ✅ | Без магазина даёт ожидаемый `NO_STORE_CONTEXT`; с IDs отвечает |
| `grocery_attempts(limit=15)` | R | ✅ | История попыток оформления отвечает |
| `grocery_order_status(order_id, app_id="")` | R | 🟡 | Нужен ID заказа |
| `grocery_add_to_cart(items, app_id, point_id)` | W | ⛔ | Меняет корзину |
| `grocery_set_cart(items, app_id, point_id)` | W | ⛔ | Перезаписывает/очищает корзину |
| `grocery_order_cancel(order_id, app_id="")` | W | ⛔ | Отменяет заказ |
| `grocery_checkout(...)` | ₽ | ⛔ | Оформление и оплата заказа |

## Кино, концерты и афиша

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `cinema_search(query="", city="Москва")` | R | ✅ | Город обязателен; с городом отвечает |
| `cinema_schedule(event_id, date, city=...)` | R | 🟡 | Нужен фильм/кинотеатр и дата; банковская авторизация необязательна |
| `afisha_catalog(kind, city, date_from, date_to)` | R | ✅ | Город и даты обязательны; отвечает без банковской сессии |
| `afisha_places(kind="movie", city="Москва")` | R | ✅ | Список площадок отвечает |
| `place_schedule(object_id)` | R | 🟡 | Нужен ID площадки |
| `place_info(object_id)` | R | 🟡 | Нужен ID площадки |
| `cinema_seats(event_id, slot_id, object_id)` | R | 🟡 | Нужны IDs события, сеанса и площадки |
| `concert_schedule(event_id, kind="concert")` | R | 🟡 | Нужен ID события; банковская авторизация необязательна |
| `concert_hall(event_id, slot_id, object_id)` | R | 🟡 | Нужны IDs из расписания |
| `ticket_qr(order_id)` | R | 🟡 | Нужен оплаченный заказ |
| `cinema_book(event_id, slot_id, object_id, seats)` | W | ⛔ | Создаёт бронь |
| `ticket_cancel(order_id)` | W | ⛔ | Отменяет заказ |
| `ticket_pay(order_id, amount, nfs_payment_token)` | ₽ | ⛔ | Оплачивает бронь |

## Поиск, путешествия и маркетплейс

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `search_app(query, screen="afisha")` | R | ✅ | Полнотекстовый поиск отвечает |
| `flight_search(from_code, to_code, date)` | R | ✅ | Живой поиск `LED → MOW` на 19.08.2026 прошёл |
| `flight_history()` | R | ✅ | История и IATA-коды отвечают |
| `flight_price_calendar(...)` | R | 🟡 | Публичный кэш минимальных цен по датам; новая живая проверка в этой ревизии не выполнялась |
| `flight_price_forecast(search_id)` | R | 🟡 | Прогноз изменения цены для `searchId` уже выполненного поиска |
| `flight_schedule(from_code, to_code, date="")` | R | 🟡 | Публичное расписание рейсов направления, не живой поиск тарифов |
| `geodata_by_code(codes)` | R | 🟡 | Публичные названия, координаты и timezone по известным IATA-кодам |
| `compare_flight_prices(...)` | R | 🟡 | Сравнивает авиапредложения по нескольким окнам дат |
| `train_stations(search_text)` | R | 🟡 | Публичный резолвер города или станции в числовой `searchCode` |
| `train_search(origin, destination, date)` | R | 🟡 | Публичный read-only поиск `trains.tbank.ru`; текущий контракт опубликован, новая живая проверка не выполнялась |
| `train_calendar(origin, destination)` | R | 🔴 | Старый mobile rail host `trains.t-bank-app.ru:443`: TCP/`ConnectTimeout` |
| `compare_train_prices(...)` | R | 🟡 | Сравнивает ЖД-предложения по нескольким окнам дат |
| `hotel_autocomplete(query)` | R | ✅ | Прод: «Москва» вернула 5 локаций и 1 конкретный отель |
| `hotel_search(destination_id, checkin_date, checkout_date)` | R | ✅ | Актуальный v2-поиск: priced ids из `searchHotelPoints` объединяются со статическими карточками |
| `hotel_details(hotel_id, max_facilities, max_images)` | R | ✅ | Прод: карточка первого результата, удобства и до 12 официальных HTTPS-фото |
| `hotel_rates(hotel_id, checkin_date, checkout_date, ...)` | R | ✅ | Прод: v3-комнаты и тарифы; точный POST body и отсутствие credentials закреплены транспортным тестом |
| `hotel_reviews(hotel_id, ...)` | R | ✅ | Прод: текущий v2 feedback, сортировка/поиск/cursor; ответ проверен на публичном маршруте |
| `hotel_filters()` | R | ✅ | Прод: 14 фильтров и 7 популярных |
| `hotel_search_filters(location_id, ...)` | R | 🟡 | `searchFilters_v3`: контракт, валидация, sticky/language headers и публичный transport покрыты offline-тестами |
| `hotel_latest_offers(hotel_ids, ...)` | R | 🟡 | `getLatestHotelOffer`: batch 1–1000 id, финальность цены и публичный transport покрыты offline-тестами |
| `hotel_checkout_url(..., book_hash, rate_confirmed=true)` | R | 🟡 | Создаёт ссылку на оформление выбранного тарифа; не создаёт бронь и не списывает деньги |
| `compare_hotel_prices(...)` | R | 🟡 | Сравнивает отельные предложения по нескольким окнам дат |
| `compare_flight_hotel_prices(...)` | R | 🟡 | Сравнивает сумму двух перелётов и отеля; не является полной стоимостью поездки |
| `nearby_search(...)` | R | 🟡 | Рестораны и места рядом через OpenStreetMap/Nominatim/Overpass |
| `weather(...)` | R | 🟡 | Прогноз Open-Meteo или климатическая оценка ERA5 |
| `shop_search(query)` | R | ✅ | Поиск товаров отвечает |
| `shop_cart(limit=20)` | R | ✅ | Корзины маркетплейса отвечают |

Покупка авиа- и ЖД-билетов и бронирование отелей через MCP не реализованы:
travel-инструменты предназначены для поиска и сравнения. Все hotel-вызовы идут
через публичный production proxy `www.tbank.ru/api/hotels/` без банковского
`Authorization`, `Cookie` и session-параметров; это отдельно закреплено
транспортным тестом.

## Мессенджер

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `messenger_conversations()` | R | ✅ | Список чатов отвечает |
| `messenger_messages(conversation_id)` | R | 🟡 | Нужен ID чата; приватный текст не запрашивался |
| `messenger_unread()` | R | ✅ | Список непрочитанных отвечает |
| `messenger_file(conversation_id, file_id)` | R | 🟡 | Нужен ID вложения; сохраняет файл при вызове |
| `messenger_send(conversation_id, text)` | W | ⛔ | Отправляет сообщение живому получателю |

## Платежи и переводы

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `transfer_sbp_resolve(phone)` | R | 🟡 | Нужен телефон получателя |
| `payment_qr(qr)` | R | 🟡 | Нужна строка платёжного QR |
| `payment_commission(body)` | R | 🟡 | Нужны реквизиты предполагаемой операции |
| `payment_providers()` | R | ✅ | Каталог групп провайдеров отвечает |
| `payment_status(attempt_id)` | R | 🟡 | Нужен ID существующей попытки |
| `pay_bill(provider_id, fields, amount)` | ₽ | ⛔ | Оплата услуги |
| `transfer(amount, to_account, ...)` | ₽ | ⛔ | Перевод по телефону/счёту |
| `transfer_requisites(...)` | ₽ | ⛔ | Перевод юрлицу по реквизитам |
| `confirm_payment(attempt_id, otp="")` | ₽ | ⛔ | Завершает удерживаемое списание |

## Инвестиции

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `invest_accounts()` | R | ✅ | Список инвест-счетов отвечает |
| `invest_portfolio(broker_account_id, days=30)` | R | 🟡 | Нужен ID брокерского счёта |
| `invest_operations(broker_account_id)` | R | 🟡 | Нужен ID брокерского счёта |
| `invest_securities(broker_account_id="")` | R | ✅ | Список портфелей/бумаг отвечает |

## Служебные инструменты

| Вызов | Режим | Статус | Примечание |
|---|:---:|:---:|---|
| `flows(topic="")` | R | ✅ | Подсказки по последовательностям вызовов |
| `diagnostics(limit=40)` | R | ✅ | Локальные очищенные события платежных сценариев |
| `debug_report(runs=0, top=6)` | R | ✅ | Локальная статистика использования MCP |
| `restaurant_search(city, ...)` | R | ✅ | Публичный поиск ресторанов Яндекс.Карт; возвращает report-ready карточки без банковской сессии |
| `get_trip_report(request, output_mode)` | R | 🟡 | Валидирует `trip-page/v2`/`hotel-page/v1`, автоматически заполняет пустой `venues` ресторанами Яндекс.Карт и возвращает HTML или Markdown; события берутся из прямого `afisha_catalog` |
| `render_trip_page(document)` | R | ⛔ | Возвращает HTML + replyMarkdown в памяти (trip-page/v1); файлы не пишет |
| `render_travel_page(document)` | R | ⛔ | Возвращает `trip-page/v2`/`hotel-page/v1` как готовый HTML + replyMarkdown в памяти; файлы не пишет |

## Практический минимальный набор для Travel-ассистента

```text
session_status()
list_accounts()
list_operations(account_id, days=30)
spending_categories(account_id, days=30)
orders(kind="путешествия")
flight_history()
flight_search("LED", "MOW", "2026-08-19")
hotel_autocomplete("Москва")
hotel_search(17039, "2026-08-19", "2026-08-20")
cinema_search(city="Москва")
afisha_catalog(kind="movie", city="Москва", date_from="2026-08-16", date_to="2026-08-23")
```

Для основного ЖД-сценария используй `train_stations()` и `train_search()` единого
T-Bank MCP: они работают через публичные read-only источники. Ограничение
`trains.t-bank-app.ru` относится только к дополнительному `train_calendar()`.
