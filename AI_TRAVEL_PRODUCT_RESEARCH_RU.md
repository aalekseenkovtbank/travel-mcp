# AI в путешествиях: рынок, продуктовые паттерны и ставка на следующий travel-инструмент

**Срез рынка:** 16 августа 2026 года  
**География:** мировой рынок  
**Цель:** найти AI-продукт, который использует реальные API авиа, отелей, поездов и автобусов, повышает GMV и cross-sell и не сводится к ещё одному чату с результатами поиска.

---

## 1. Executive summary

### Главный вывод

Conversational search уже стал рыночной гигиеной. Сам по себе сценарий «напиши, куда и когда хочешь, — получи несколько билетов или отелей» больше не создаёт устойчивого отличия. KAYAK, Booking.com, Expedia, Google, Skyscanner, Agoda, авиакомпании и десятки стартапов уже умеют интерпретировать свободный запрос и показывать подходящие варианты.

Следующая продуктовая граница — **AI, который создаёт и поддерживает исполнимую модель всей поездки**:

1. понимает неполный замысел и ограничения;
2. собирает транспорт, проживание и досуг в согласованный план;
3. проверяет расписание, стыковки, доступность и полный бюджет;
4. показывает компромиссы не списком, а на живой карте, таймлайне и бюджетной панели;
5. после подтверждения совершает бронирования;
6. продолжает следить за зависимостями и предлагает согласованное перепланирование при сбоях.

Рекомендуемый флагман — **«Компилятор поездки»**: AI превращает намерение пользователя в 2–3 полностью покупаемых, логистически проверенных варианта всей поездки и позволяет интерактивно менять цену, темп, комфорт и насыщенность. После покупки тот же объект становится «автопилотом» поездки.

### Почему это сильнее обычного ассистента

- **Максимально использует собственный supply.** Чем больше категорий подключено, тем выше качество результата и барьер для чат-обёрток без инвентаря.
- **Увеличивает корзину, а не только CTR.** Основная единица результата — не билет или отель, а подтверждённая мультикатегорийная поездка.
- **Сокращает не ввод запроса, а работу принятия решения.** Пользователь получает несколько согласованных решений вместо десятков независимых выдач.
- **Создаёт накопительный moat.** Система учится на принятых компромиссах: ради чего конкретный человек доплачивает, какой темп выбирает и что считает недопустимым.
- **Естественно расширяется.** Group Negotiator, Reel-to-Real, Total Cost Optimizer и Trip Autopilot становятся модулями одной платформы, а не разрозненными AI-фичами.

### Пять выводов из рынка

1. **Интерфейсом становится поездка, а не чат.** Priceline строит Penny вокруг интерактивной карты, Google — вокруг Canvas, Mindtrip и Wanderlog — вокруг карты, таймлайна и совместного плана.
2. **Live inventory и право совершать действие важнее выбранной LLM.** Priceline прямо связывает преимущество с контекстом, инвентарём и deals; MakeMyTrip использует специализированных агентов по категориям; Navan соединяет AI с правилами, билетными структурами и обслуживанием.
3. **Самая доказанная бизнес-ценность находится около транзакции и post-sale.** Trip.com сообщал о двукратной конверсии заказов у пользователей TripGenie; Expedia и Navan автоматизируют более половины обращений в поддержку.
4. **Пользователь хочет помощи, но не бесконтрольной автономии.** В глобальном исследовании Booking.com 89% хотели бы использовать AI в будущем планировании поездок, но лишь 12% готовы к самостоятельным решениям AI и только 6% полностью ему доверяют.
5. **Чистая генерация маршрута недостаточно надёжна.** Исследования TravelPlanner, TRIP-PAL, ATLAS и TREK показывают, что реальный план требует формальных ограничений, актуальных инструментов, верификации и повторного расчёта — одного LLM недостаточно.

---

## 2. Методика и правила чтения

### Что исследовано

Рассмотрены 34 продукта и продуктовых набора:

- 13 OTA, поисковиков и airline-решений;
- 12 AI-first планировщиков и консьержей;
- 9 мультимодальных, fintech, servicing и adjacent-продуктов.

Основой служат официальные продуктовые страницы, пресс-релизы, help-центры, investor materials и исследовательские публикации. Маркетинговые заявления компаний не трактуются как независимая оценка качества. Если продукт объявлен, находится в beta или ограничен рынком, это отмечено отдельно.

### Обозначения

**Этапы:** Вд — вдохновение; Пл — планирование; Б — бронирование; По — подготовка; Вп — во время поездки; Пс — после поездки.

**Глубина транзакции:**

- **T0** — рекомендации без live inventory;
- **T1** — актуальный поиск или цена, завершение вне продукта;
- **T2** — переход в собственный стандартный checkout;
- **T3** — выбор и бронирование внутри AI-сценария с подтверждением;
- **T4** — обслуживание, обмен или перебронирование после подтверждения пользователя.

### Ограничения исследования

- У быстро меняющихся beta-продуктов публичное описание может отставать от фактического интерфейса.
- Компании редко раскрывают абсолютную конверсию и сравнимые retention-метрики.
- «AI-powered» иногда означает ML-ранжирование или суммаризацию, а не агент, способный планировать и действовать. В таблицах эти случаи разделены.
- Rome2Rio, TripIt, Kiwi.com, Hopper и Allyz включены как adjacent-референсы: не все являются GenAI-планировщиками, но они решают наиболее ценные задачи, которые будущий AI должен уметь оркестрировать.

### Принятые продуктовые предпосылки

- Доступны собственные full-cycle API поиска, repricing, бронирования и обслуживания как минимум для отелей, авиа, поездов и автобусов.
- Для персонализации можно использовать явный профиль, прошлые поиски и историю travel-бронирований; доступ к банковским транзакциям не предполагается.
- Допустимы внешние API карт, POI, ресторанов, событий, погоды, визовых правил и экскурсий.
- AI может самостоятельно исследовать, считать и готовить действия, но покупка, обмен и отмена всегда подтверждаются пользователем.
- Концепции не ограничены одним сегментом или фиксированным горизонтом реализации; для каждой указаны наиболее сильная аудитория и относительная сложность.

---

## 3. Сигналы спроса, бизнеса и доверия

### Пользовательский спрос

- В исследовании Booking.com среди 37 325 респондентов из 33 рынков **67% уже использовали AI в каком-либо аспекте путешествия**, а **89% хотели бы применять его в будущем планировании**. Наиболее частые planning-задачи: выбор направления и времени, локальные активности и рестораны. При этом лишь **6% полностью доверяют AI**, а только **12% комфортно относятся к самостоятельным решениям AI.** Источник: [Booking.com Global AI Sentiment Report, 23.07.2025](https://news.booking.com/bookingcom-releases-the-global-ai-sentiment-report/).
- Expedia указывает, что **80% миллениалов используют социальные медиа при принятии travel-решений**; на этом основании компания запустила преобразование Instagram Reels в бронируемые поездки. Источник: [Expedia Trip Matching, 12.06.2025](https://www.expedia.com/newsroom/now-live-expedia-launches-industry-first-feature-that-turns-reels-on-instagram-into-bookable-travel-itineraries/).
- Исследование Agoda в Индии показало интерес не только к маршрутам, но и к локальным активностям, dining и **управлению бюджетом**. Это региональный, а не глобальный сигнал, но он подтверждает ширину ожидаемой задачи. Источник: [Agoda Travel Outlook, 08.05.2026](https://www.agoda.com/press/68-of-indian-travelers-likely-to-use-ai-for-their-next-trip-agoda/).

### Подтверждённая бизнес-ценность

- Trip.com сообщал, что пользователи рекомендаций TripGenie были на **30–40% вероятнее склонны вернуться**, проводили примерно на 20 минут больше в приложении и имели **вдвое большую конверсию заказов**. Это корреляция продуктового использования, а не опубликованный randomized experiment. Источник: [Trip.com, 06.06.2024](https://www.trip.com/newsroom/tripgenie-new-features-2/).
- AI-service Expedia обрабатывает более **143 млн разговоров в год**, позволяет более чем 50% путешественников решить вопрос самостоятельно, а заявленная удовлетворённость self-service вдвое выше звонков. Источник: [Expedia Group, 12.05.2025](https://www.expedia.com/newsroom/expedia-group-sets-the-standard-with-ai-powered-service-agent/).
- Navan заявляет, что Ava решает AI около **54% запросов** с CSAT 78; система меняет рейсы и работает со сбоями, а не только отвечает на FAQ. Источник: [Navan Intelligence, проверено 16.08.2026](https://navan.com/intelligence).
- Air India сообщала, что её support-агент AI.g автономно отвечал на **97%** из более чем 7 млн запросов; eZ Booking затем перенёс agentic-паттерн в покупку билета голосом или текстом. Источник: [Air India, 22.01.2025](https://www.airindia.com/in/en/newsroom/press-release/Air-India-launches-AI-driven-eZ-Booking.html).

### Технический сигнал

- Оригинальный benchmark TravelPlanner показал, насколько плохо монолитные языковые агенты соблюдают одновременно бюджет, доступность, географию и расписание. Источник: [TravelPlanner, 2024](https://arxiv.org/abs/2402.01622).
- TRIP-PAL предлагает разделять роли: LLM переводит намерение в структуру, а формальный planner гарантирует соблюдение ограничений и оптимизирует utility. Источник: [TRIP-PAL, 2024](https://arxiv.org/abs/2406.10196).
- ATLAS улучшает результат за счёт специализированных агентов, реестра динамических ограничений, критика плана и повторного поиска. Источник: [Google Research ATLAS, 2025](https://research.google/pubs/atlas-constraints-aware-multi-agent-collaboration-for-real-world-travel-planning/).
- TREK формулирует практический стандарт: каждый объект должен существовать и быть доступен, день — быть физически выполнимым, бюджет — сходиться, а неполные предпочтения — корректно уточняться. Источник: [TREK, июль 2026](https://arxiv.org/abs/2607.26977).

**Следствие:** продукт должен использовать LLM для диалога, извлечения намерения и объяснения, но расчёт цен, стыковок, бюджета, доступности и последствий изменений должен выполняться детерминированными сервисами и проверяемыми tools.

---

## 4. Карта рынка: OTA, поисковики и авиакомпании

| Продукт | Позиционирование и этапы | Ввод и интерфейс | Inventory / действие | Персонализация и wow | Доказательства и ограничения | Источник |
|---|---|---|---|---|---|---|
| **Priceline Penny** | Agentic OTA: Вд → Пл → Б → поддержка | Текст, voice, карта, результаты меняются вместе с разговором | Live flights, hotels, cars; **T3**, заявлена покупка без выхода из разговора | Preference layer разделяет устойчивое поведение и контекст текущей поездки; Penny’s Pick и Penny’s Take объясняют выбор | Система из 10+ специализированных агентов; у engaged-пользователей выше engagement и conversion, но абсолютные цифры не раскрыты | [Priceline, 03.06.2026](https://press.priceline.com/pricelines-penny-goes-fully-agentic/) |
| **Expedia Romie + Trip Matching** | Компаньон от группового обсуждения до сбоев; Вд → Вп | SMS group chat, email import, app, Instagram Reel, ChatGPT app | Dynamic prices; собственный checkout, **T2–T4** в отдельных сценариях | Участие в групповом чате, импорт писем, Reel → bookable itinerary, мониторинг погоды и сбоев | Romie был alpha в EG Labs; фактическая доступность отдельных функций различается. В 2026 объявлены Activity Planner, Property Compare и Package Price Insights | [Romie, 14.05.2024](https://www.expedia.com/newsroom/spring-product-release-2024/), [Trip Matching, 12.06.2025](https://www.expedia.com/newsroom/now-live-expedia-launches-industry-first-feature-that-turns-reels-on-instagram-into-bookable-travel-itineraries/), [Explore 26](https://www.expedia.com/newsroom/companies/expedia-group/) |
| **Booking.com AI Trip Planner** | Раннее вдохновение и accommodation conversion; Вд → Пл → Б | Chat плюс визуальные карточки; Smart Filter, Property Q&A, Review Summaries | Live property prices и deep link в собственное бронирование, **T2** | Natural-language discovery и ответы на вопросы по данным объекта и отзывам | Сильнее всего вокруг проживания; исходный beta был географически ограничен. Connected Trip остаётся стратегическим направлением | [Booking.com, 27.06.2023](https://news.booking.com/bookingcom-launches-new-ai-trip-planner-to-enhance-travel-planning-experience/), [OpenAI case study, проверено 16.08.2026](https://openai.com/index/booking-com/) |
| **Trip.com TripGenie** | AI-advisor и общий itinerary; Вд → Пл → Б → По → Вп | Chat, редактируемый план, collaboration | Flights, hotels и другие категории Trip.com; добавление броней; **T2–T3** | Multi-destination, темп поездки, совместное редактирование, статусы рейса и check-in alerts | Один из немногих продуктов с опубликованным коммерческим сигналом: 2× order conversion у использующих рекомендации | [Trip.com, 06.06.2024](https://www.trip.com/newsroom/tripgenie-new-features-2/) |
| **KAYAK Ask AI / AI Mode** | Conversational metasearch; Вд → Пл → Б | Текст, интерактивная выдача и карта; voice объявлен как следующее расширение | Real-time flights, hotels, cars, activities из сотен источников; в основном **T1** | Сильное понимание сложного запроса, fare rules, baggage, layovers и flexible destination | Главный предел — метапоиск: покупка и обслуживание чаще остаются у поставщика | [KAYAK AI Mode, 15.10.2025](https://www.kayak.com/news/ai-mode/), [KAYAK Help, проверено 16.08.2026](https://www.kayak.com/c/help/search/) |
| **Google AI Mode Canvas + Gemini** | Универсальная среда исследования и планирования; Вд → Пл → Б | Chat, Canvas, Maps, photos, reviews; opt-in Personal Intelligence из Gmail/Photos | Real-time Flights и Hotels; restaurant booking; hotel booking внутри AI Mode через merchant уже доступен в США на английском, **T1–T3** по категории | Сопоставляет отель, рестораны и активности по travel time; сильный cross-web grounding и личный контекст под контролем пользователя | Flights остаются в основном search/click-out; hotel post-sale ведёт merchant; ряд agentic-функций географически ограничен | [Google travel Canvas, 17.11.2025](https://blog.google/products-and-platforms/products/search/agentic-plans-booking-travel-canvas-ai-mode/), [Hotel booking help, проверено 16.08.2026](https://support.google.com/travel/answer/17216079), [Personal Intelligence, 22.01.2026](https://blog.google/products-and-platforms/products/search/personal-intelligence-ai-mode-search/) |
| **MakeMyTrip Myra** | Multi-agent journey от discovery до post-sales; Вд → Вп | Text, voice, image, video; continuous dialogue | Flights, stays, holidays, ground transport, visas, forex; заявлен confirmed booking в одном voice journey, **T3–T4** | Специализированные агенты и мультиязычность; может строить сложный маршрут без самолётов | На запуске beta на английском и хинди; независимых метрик качества нет | [MakeMyTrip, 07.08.2025](https://investors.mmtcdn.com/Press_Release_Gen_AI_Trip_Planning_Assistant_07_08_2025_404cc1872a.pdf) |
| **Tripadvisor Trips + AI ecosystem** | Guidance на базе отзывов; Вд → Пл → Б | Prompted itinerary, save/edit/share; интеграции Claude и Alexa+ | Hotels и experiences с ценами; завершение на Tripadvisor/Viator, **T1–T2** | Более 1 млрд reviews/opinions и community grounding; голосовой planning через Alexa+ | Лучше отвечает «что действительно стоит делать», чем решает сквозную логистику и post-sale | [Tripadvisor Trips](https://www.tripadvisor.com/Trips), [AI partnerships, 23.04.2026](https://tripadvisor.mediaroom.com/2026-04-23-How-AI-Is-Changing-the-Way-We-Plan-Travel) |
| **Skyscanner Savvy Search** | AI-discovery поверх metasearch; Вд → Пл → Б | Свободный prompt и традиционная выдача | Цены Skyscanner и переход к партнёрам, **T1** | Совмещает web-информацию с pricing/destination data; перспективный Vibes discovery | Это обогащённый поиск, а не сохраняемый исполнимый план или servicing agent | [Skyscanner, проверено 16.08.2026](https://www.skyscanner.net/media/how-skyscanner-works), [AI strategy, 2025](https://www.partners.skyscanner.net/news-case-studies/phocuswright-europe-ai) |
| **Agoda AI suite** | AI в точках booking friction и support; Пл → Б → Вп | Property AMA, Booking Form Bot, free-text support, summaries | Контекст выбранного property/room/rate; **T2–T4** | Bot знает текущую сессию и условия тарифа, не заставляет повторять данные | Property AMA отвечает более чем на 30 000 вопросов в день; это набор вертикальных агентов, а не единый trip planner | [Agoda, 12.01.2026](https://www.agoda.com/press/agoda-launches-ai-powered-booking-bot-to-help-travelers-book-with-confidence/), [cross-device support, 25.02.2026](https://www.agoda.com/press/never-miss-a-message-agodas-customer-support-now-travels-with-you/) |
| **HomeToGo AI Mode / Sunny** | AI-подбор vacation rental; Вд → Пл → Б | Conversational AI, summaries | Vacation homes в HomeToGo; **T1–T2** | Запрос по типу отдыха, Smart AI Reviews и Offer Summaries | Узкая вертикаль проживания; не решает транспорт и целостный бюджет | [HomeToGo features, проверено 16.08.2026](https://www.hometogo.com/about/product-features/), [2025 trends](https://www.hometogo.com/summer-2025-travel/) |
| **Air India eZ Booking** | Agentic direct airline booking; Пл → Б | Text, voice и визуальная корректировка | Только Air India; итоговая оплата и билет, **T3** | Сокращает многоэкранный booking flow до разговора и подтверждения | Сильный transaction proof, но одна авиакомпания и без целой поездки | [Air India, 22.01.2025](https://www.airindia.com/in/en/newsroom/press-release/Air-India-launches-AI-driven-eZ-Booking.html) |
| **Qatar Airways Sama** | AI cabin-crew persona и booking assistant; Вд → Б | Voice, chat, app/web, QVerse и демонстрационный hologram | Qatar Airways itinerary; **T2–T3** | Эмоциональный Dream Destination и персонифицированный брендовый интерфейс | Вау в embodiment и discovery, но supply ограничен одной авиакомпанией | [Qatar Airways, 24.02.2025](https://www.qatarairways.com/press-releases/en-WW/247237-a-first-in-aviation-qatar-airways-reinvents-travel-bookings-with-sama-at-web-summit-qatar-2025/) |

---

## 5. Карта рынка: AI-first планировщики и консьержи

| Продукт | Основной сценарий | Интерфейс и данные | Транзакция | Сильная сторона | Ограничение / незакрытая задача | Источник |
|---|---|---|---|---|---|---|
| **Mindtrip** | Универсальный trip workspace от вдохновения до поездки | Chat, map, reviews, collections, group chat; импорт Google Pins, email confirmations, фото, screenshot, PDF и URL | Real-time airfares; hotels, restaurants и experiences; преимущественно **T1–T2** | Start Anywhere превращает почти любой артефакт в план; сильная совместная работа и хранение подтверждений | Публичное описание не доказывает единый checkout и coordinated post-sale для всех категорий | [Mindtrip, проверено 16.08.2026](https://mindtrip.ai/home) |
| **Layla** | AI + human travel expert для полного отпуска | Chat, визуальный day-by-day plan, creator video content | Live pricing для flights, hotels, activities; human-assisted booking/management, **T2–T4** | Комбинация мгновенного AI и ответственного человека для сложных поездок | Неясно, насколько все категории бронируются нативно и насколько масштабируется human layer | [Layla, проверено 16.08.2026](https://layla.ai/) |
| **Airial** | Детальное планирование сложной поездки и Reel-to-real | Prompt или TikTok/Reel link; карта, day phases, alternatives, transfer/wait time | Checkout-ready itineraries; публичная детализация глубины booking ограничена, **T1–T2** | Делает упор на logistics reasoning, multi-city, proximity и транспорт, а не только список POI | Нет публичных quality/conversion метрик; post-sale не выглядит ядром | [Airial](https://www.home.airial.travel/), [обзор продукта, 30.06.2025](https://techcrunch.com/2025/06/30/former-meta-engineers-airial-travel-tool-helps-travelers-solve-logistics-planning-with-ai/) |
| **Wanderlog** | Полноценное ручное и AI-assisted управление поездкой | Itinerary, map, route optimization, reservations, collaboration, budget, offline, checklist | Hotel comparison и booking links; в основном **T1** | Самый зрелый workspace-паттерн: план, документы, карта, расходы и группа в одном месте | AI не является транзакционным оркестратором всей поездки; значительная часть организации остаётся ручной | [Wanderlog, проверено 16.08.2026](https://wanderlog.com/home) |
| **GuideGeek** | Travel advice там, где уже общается пользователь | WhatsApp, Instagram, Messenger, website; destination content indexing | Рекомендации и partner promotion, **T0–T1** | Нулевой installation friction, 50+ языков, B2B white-label для destinations | Chat-first; слабый сохраняемый trip object, бюджет и сквозное servicing | [GuideGeek About](https://guidegeek.com/about), [GuideGeek for Destinations](https://guidegeek.com/destinations) |
| **Alike Eia** | Social inspiration → bookable trip → сопровождение → creator income | TikTok/Reels/YouTube, chat, social trip stories, trip plan, memory album | Hotels, experiences, transport, visas, eSIMs и 50+ services; **T2–T4** с human backup | Самый широкий публично заявленный цикл, включая post-trip album и revenue share для creator itinerary | Многие claims принадлежат самому продукту; нужны независимые данные о качестве и repeat use | [Alike, проверено 16.08.2026](https://alike.io/), [release, 14.04.2026](https://www.newsfilecorp.com/release/292389/From-a-Saved-Reel-to-a-Booked-Trip-Alike-Unveils-AIDriven-Upgrade-to-Simplify-Travel) |
| **Wonderplan** | Быстрый персональный city itinerary | Форма: место, даты, бюджет, состав, интересы, food preferences; editable plan и PDF | Accommodation recommendations, но преимущественно **T0–T1** | Очень низкий порог старта и offline export | Бюджет явно относится лишь к activities и dining; не оптимизирует полную стоимость поездки | [Wonderplan planner](https://wonderplan.ai/v2/trip-planner), [features](https://wonderplan.ai/) |
| **Tripplanner.ai** | Генерация day-by-day trip с flights, hotels и activities | AI builder, список и персонализация | Поиск вариантов и внешнее завершение, **T0–T1** | Понятный быстрый outcome для простых запросов | Трудно отличим от множества itinerary generators; нет доказанного post-sale или constraint engine | [Tripplanner.ai, проверено 16.08.2026](https://tripplanner.ai/) |
| **iPlan.ai** | Персональный itinerary за минуту | Structured onboarding, editable and collaborative itinerary | Публично не подтверждён live transactional inventory, **T0** | Быстрота, time-at-place и collaboration | Типичный «готовый план», а не проверенная корзина и не агент действий | [iPlan.ai, проверено 16.08.2026](https://iplan.ai/how-it-works/) |
| **Vacay AI** | Semantic discovery и AI travel advisors | General chatbot, itinerary planner, destination-specific bots и guides | Direct links к hotels, packages, experiences, events, cruises; **T0–T1** | Несколько специализированных discovery-интерфейсов вместо одного общего prompt | Нет единого живого itinerary с транзакциями и изменениями зависимостей | [Vacay AI, проверено 16.08.2026](https://www.usevacay.com/) |
| **Copilot2Trip** | B2B/white-label AI-planning для travel brands | Voice-to-text, multiple chats, map + curated POIs, sharing, multilingual | Зависит от интеграции партнёра, **T0–T2** | Можно встроить branded planner и соединить AI creativity с проверенными POI | Это capability platform; конечный UX и transaction depth не гарантированы | [Copilot2Trip, проверено 16.08.2026](https://business.copilot2trip.com/) |
| **Tripful** | Mobile trip plan с AI, ценовым мониторингом и множеством add-ons | AI assistant, itinerary, multi-city map, group collaboration | Flights, stays, tours, car, insurance, eSIM; one-tap/deep-link model, **T1–T2** | Связывает price alerts и travel ancillaries с планом | Публичные сведения в основном из store listing; мало проверяемых бизнес- и quality-метрик | [Google Play listing, обновлено 02.07.2026](https://play.google.com/store/apps/details?id=app.tripful.android) |

### Вывод по AI-first категории

Большинство стартапов умеют быстро создать красивый day-by-day plan. Гораздо реже одновременно присутствуют:

- реальная доступность и полные условия тарифа;
- логистическая проверка всего плана;
- единый бюджет с taxes, fees, baggage и локальными расходами;
- согласованные изменения уже купленных частей;
- accountable fallback, когда API или AI не справляется.

Именно эти элементы превращают генератор контента в travel product с устойчивой коммерческой ценностью.

---

## 6. Карта рынка: multimodal, fintech, servicing и adjacent-референсы

| Продукт | Что решает | AI / алгоритмический паттерн | Действие | Почему это важно для будущего продукта | Источник |
|---|---|---|---|---|---|
| **Hopper / HTS** | Price prediction, watch, Price Freeze, flexible/cancel products, disruption rebooking | Риск-модели динамически оценивают и прайсят защиту; AI/ML предсказывает цену | **T3–T4**: покупка защиты, rebook на другую авиакомпанию в пределах условий | Показывает, что пользователь платит не за рекомендацию, а за снижение ценовой неопределённости и гарантированный outcome | [Hopper overview](https://media.hopper.com/articles/welcome-to-hopper), [HTS](https://hts.hopper.com/) |
| **Kiwi.com Nomad + Guarantee** | Multi-city и self-transfer itineraries, disruption protection | Алгоритм переставляет города и соединяет flights, trains, buses; AI-chat support | **T3–T4**: booking, check-in, instant credit/replacement flow | Референс для графа зависимостей и защиты маршрута, который не покрывается одним перевозчиком | [Nomad](https://www.kiwi.com/en/nomad/), [Kiwi.com Guarantee](https://www.kiwi.com/us/guarantee/) |
| **Tryp.com** | Dynamic trip packages across cities and modes | AI-driven engine сканирует маршруты и accommodation, собирая оптимизированный пакет | **T3**: itinerary, adjustments и checkout на одной платформе | Ближайший референс к «компилятору»: оптимизирует не выдачу одного продукта, а комбинацию | [Tryp.com How it works](https://www.tryp.com/en/help/how-it-works), [app, 2025](https://www.tryp.com/en/blog/trypcom-app-smart-travel-booking-at-your-fingertips) |
| **Omio in ChatGPT** | Real-time comparison trains, buses, flights и ferries | Conversational layer поверх сети 3 000+ transport partners | **T1–T2**: live multimodal options, дальнейшее booking flow | Доказывает, что ground transport становится first-class tool для AI, а не справочной припиской к авиапоиску | [Omio, 14.04.2026](https://www.omio.com/corporate/newsroom/press-releases/omio-launches-in-chatgpt-bringing-its-real-time-multimodal-travel-search-to-900-million-users/) |
| **Rome2Rio** | Глобальный A→B multimodal discovery | Большой route graph самолётов, поездов, автобусов, ferry и car; не GenAI-first | **T1–T2** через ticketing partners | Слой глобальной достижимости и first/last mile; показывает ценность mode-neutral route graph | [Rome2Rio](https://www.rome2rio.com/), [booking model](https://help.rome2rio.com/en/support/solutions/articles/22000280965-bookings-and-rome2rio) |
| **TripIt Pro** | Автоматический trip wallet и in-trip awareness | Парсит emails, photo/PDF; alerts, fare tracking, alternate flights, risk signals | **T1/T4-assist**: предлагает альтернативы и сообщает о refund eligibility, но не всегда действует сам | Референс для универсального ingestion и «единой правды» о поездке независимо от места покупки | [TripIt vs Pro, проверено 16.08.2026](https://help.tripit.com/en/support/solutions/articles/103000063396-tripit-or-tripit-pro-) |
| **Navan Ava** | Business travel booking, policy, expenses и disruptions | Agentic framework соединяет profile, history, policy, inventory и human agents | **T3–T4**: booking, flight changes, disruption handling, supplier calls | Наиболее доказанный паттерн «AI там, где можно; человек там, где необходимо» и интеграция за пределами chat box | [Navan Intelligence](https://navan.com/intelligence), [Hotel Concierge](https://investors.navan.com/news-releases/news-release-details/navan-introduces-hotel-concierge-ava) |
| **Amex GBT AI Assistant** | Corporate booking, change, cancel и support | Conversational AI с handoff специалисту и контекстом поездки | **T3–T4** | Подтверждает необходимость seamless human escalation для дорогих и срочных исключений | [Amex GBT mobile](https://www.amexglobalbusinesstravel.com/business-travel/select/mobile-app/), [AI release, 28.05.2025](https://www.amexglobalbusinesstravel.com/press-releases/american-express-global-business-travel-introduces-new-ai-powered-solutions/) |
| **Allianz Allyz** | Страхование, документы, safety/health alerts, claims и assistance | Персональные trip updates и digital assistance; не GenAI-first | **T2–T4** для policies, claims и services | Показывает post-booking white space: здоровье, безопасность, страховой claim и помощь должны жить в том же trip object | [Allianz launch, 24.01.2024](https://www.allianz.com/en/mediacenter/news/media-releases/240124-allianz-partners-announces-the-launch-of-the-allyz-mobile-app.result.html/5.html), [Allyz US](https://www.allyz.com/us) |

---

## 7. Таксономия AI travel-возможностей

### 7.1. Вдохновение и выбор направления

| Возможность | Статус рынка | Сильные референсы | Что должно быть в новом продукте |
|---|---|---|---|
| Свободный запрос по vibe, составу и интересам | **Гигиена** | KAYAK, Booking, Google, Priceline, Layla | Не отдельный чат, а вход в структурированный trip brief |
| Flexible destination и flexible dates | **Гигиена для metasearch** | Google Flight Deals, KAYAK Explore, Skyscanner | Оптимизировать полный trip cost, а не только fare |
| Фото, screenshot, PDF, URL → идеи | **Растущий стандарт** | Mindtrip Start Anywhere | Извлекать места и ограничения, затем проверять их реальность и доступность |
| Reel/TikTok/YouTube → поездка | **Дифференциатор 2025–2026** | Expedia Trip Matching, Airial, Alike | Сохранять source attribution и превращать inspiration в проверенный план |
| Эмоциональный / promptless discovery | **Эксперимент** | Qatar Dream Destination | Использовать как acquisition delight, не как ядро ценности |
| Персональная память travel style | **Новая гигиена для лидеров** | Penny, Romie, Navan, Layla | Отделять устойчивую память от требований конкретной поездки; дать пользователю контроль |

### 7.2. Планирование и оптимизация

| Возможность | Статус рынка | Проблема текущих решений | Opportunity |
|---|---|---|---|
| Day-by-day itinerary | **Commodity** | Часто представляет правдоподобный текст, а не выполнимый schedule | Генерировать из проверенных nodes с hours, duration, travel time и reservation windows |
| Карта и timeline | **Гигиена хорошего UX** | Карта часто только визуализирует уже выбранное | Сделать карту и timeline интерактивным constraint editor |
| Route optimization внутри дня | **Средняя зрелость** | Не учитывает весь trip, усталость, багаж, check-in и разные modes | Multi-day solver с first/last mile, buffers и сменой города |
| Multi-city / multimodal | **Редкий сильный паттерн** | Вертикали считают каждый segment отдельно | Один mode-neutral graph: air, rail, bus, transfer, walking |
| Полный бюджет | **Большой white space** | У многих planner «budget» относится лишь к activities или грубой категории | Live ledger: fare, baggage, taxes, stay, local transport, activities, food envelope и protection |
| Trade-off explanation | **Формирующийся стандарт** | Пользователь видит рейтинг, но не понимает цену выбора | Pareto-варианты и объяснение: «+8 000 ₽ экономят 5 часов и одну пересадку» |
| Feasibility / constraint validation | **Критический white space** | LLM забывает hard constraints и использует устаревшие POI | Deterministic validator и visible confidence/provenance |

### 7.3. Совместное планирование

| Возможность | Статус | Референсы | Opportunity |
|---|---|---|---|
| Share, comments, likes | **Гигиена у planners** | Mindtrip, Wanderlog, TripGenie | Не путать collaboration с consensus |
| AI в групповом чате | **Редко** | Expedia Romie | Извлекать только явно разрешённые предпочтения |
| Индивидуальные бюджеты и private constraints | **White space** | Публично почти не реализовано | Каждый участник задаёт must-have, veto и приватный лимит |
| Разрешение конфликтов | **White space** | Есть академические эксперименты, но мало production evidence | Показывать Pareto-компромиссы и цену каждого решения |
| Split payment / coordinated hold | **White space** | Финтех и group apps решают части задачи отдельно | Удерживать согласованный inventory до индивидуальных подтверждений |

### 7.4. Поиск, решение и покупка

| Возможность | Статус | Наблюдение |
|---|---|---|
| Natural-language filters | **Гигиена** | Не является самостоятельной продуктовой концепцией |
| Live price и availability | **Обязательная база доверия** | Cached или hallucinated price разрушает весь сценарий |
| Q&A по property/fare | **Гигиена около checkout** | Agoda и Booking показывают, что вопросы об отмене и цене тормозят покупку |
| Сравнение нескольких направлений и категорий | **Сильный emerging pattern** | Penny сравнивает destination alternatives, Expedia развивает package insights |
| Recommendation with a point of view | **Emerging** | Лучший результат должен быть объяснён, а не просто поднят в ranking |
| One-conversation booking | **Редко, но уже production** | Air India, Priceline, MakeMyTrip и airline assistants показывают техническую реализуемость |
| Пакетная покупка с отдельными подтверждениями | **White space** | Нужен transaction plan: что hold, что repricing, что подтверждается и в каком порядке |

### 7.5. Подготовка

- Автоматически собирать подтверждения из собственных заказов, email, PDF, screenshot и календаря.
- Проверять документы, визовые и entry-требования с датой актуальности и официальным источником.
- Считать baggage rules не справкой, а ограничением всего маршрута.
- Давать check-in, terminal, transfer, cancellation-deadline и packing reminders.
- Предлагать eSIM, insurance, transfer, lounge, валюту и билеты в POI в контексте конкретного пробела плана.

**Статус рынка:** itinerary wallet и alerts зрелы у TripIt, Kiwi и airline apps, но редко связаны с AI-планом и cross-sell в нужный момент.

### 7.6. Во время поездки

- Live statuses для всех segments.
- Impact analysis: задержка рейса влияет не только на connection, но и на hotel check-in, train, transfer, restaurant и prepaid activity.
- Один пакет альтернатив вместо пяти независимых уведомлений.
- Day replan по погоде, закрытию POI, усталости или изменившемуся желанию.
- Перевод, локальный transport guidance, health/safety и supplier communication.
- Явное подтверждение обмена, отмены, доплаты или новой покупки.

**Статус рынка:** alerts — гигиена; cross-category recovery — практически незанятое поле.

### 7.7. После поездки

- Проверка неиспользованных услуг, refund/compensation eligibility и незакрытых claims.
- Итог план-факт бюджета и разделение расходов.
- Сбор фото в timeline без обязательной публикации.
- Извлечение preference signals только с согласия: что понравилось, где пользователь переоценил темп, за что был готов доплатить.
- Shareable/bookable itinerary и creator revenue — опциональный acquisition loop.

**Статус рынка:** Alike наиболее явно соединяет memories, publishing и commerce; у большинства OTA post-trip заканчивается review request.

### 7.8. Доверие и контроль

Обязательные механики:

1. цена и availability имеют timestamp;
2. каждый внешний факт имеет provenance;
3. hard constraints показываются и редактируются;
4. memory разделена на «всегда» и «только эта поездка»;
5. денежные действия всегда требуют явного подтверждения;
6. repricing показывает, что изменилось;
7. пользователь видит cancellation/refund consequences до действия;
8. при низкой уверенности или конфликте API система передаёт задачу человеку с полным контекстом.

---

## 8. Что стало гигиеной, а где заканчивается «красивый чат»

### Рыночная гигиена к августу 2026

Нельзя строить позиционирование только на следующих возможностях:

- поиск билета или отеля свободной фразой;
- генерация общего day-by-day itinerary;
- ответы «куда поехать» и «что посмотреть»;
- суммаризация отзывов;
- карта рекомендованных мест;
- сохранение и ручное редактирование плана;
- простая персонализация по составу, бюджету и интересам;
- базовые flight alerts;
- голос как замена клавиатуре.

Это необходимые составляющие современного продукта, но каждая уже реализована множеством игроков.

### Тест на «чат-обёртку»

Продукт остаётся чат-обёрткой, если после ответа пользователь должен:

1. заново вводить даты и пассажиров в обычный поиск;
2. самостоятельно проверять, существует ли рекомендация и открыта ли она в нужное время;
3. вручную понимать, успевает ли он между точками;
4. отдельно собирать flight, hotel, rail/bus и activities;
5. пересчитывать полный бюджет;
6. вручную переносить изменения в остальные части плана;
7. выяснять у нескольких поставщиков, что делать при сбое.

### Где лидеры уже выходят за рамки чата

- **Penny:** conversation управляет картой и реальным inventory, а выбор можно завершить в том же контексте.
- **MakeMyTrip:** специализированные агенты по travel-категориям и post-sales.
- **TripGenie:** брони попадают в общий itinerary, есть collaboration и in-trip alerts.
- **Navan:** AI выполняет изменения и передаёт исключения человеку с контекстом.
- **Kiwi/Hopper:** пользователь получает финансово обеспеченный outcome при ценовой неопределённости или сбое.
- **Mindtrip/Wanderlog:** поездка существует как долговечный объект, а не исчезающий ответ.
- **Alike/Expedia/Airial:** social inspiration превращается в структуру, которую можно дальше планировать и покупать.

### Незакрытые пользовательские задачи

| Незакрытая задача | Почему рынок пока решает её плохо | Коммерческий эффект решения |
|---|---|---|
| «Собери лучший отпуск целиком в 250 000 ₽» | Вертикали оптимизируют собственную цену; activities и local mobility часто не входят в бюджет | Рост attach rate и GMV на одну поездку |
| «Покажи не 200 вариантов, а три осмысленных компромисса» | Ranking не объясняет trade-offs между городом, отелем, временем и комфортом | Быстрее решение, выше conversion |
| «Проверь, что этот маршрут физически возможен» | LLM создаёт plausible text, а inventory APIs не видят весь план | Доверие и меньше post-booking проблем |
| «Если рейс задержался, спаси всю поездку» | Поставщики видят только собственную бронь | Servicing differentiation, loyalty и новые protection products |
| «Договори группу до покупки» | Comments и likes не разрешают конфликт бюджетов и veto | Больше групповых заказов и высокая корзина |
| «Сделай из этого Reel реальную поездку, но не копируй бессмысленно» | Извлечь POI легко; проверить сезонность, логистику и цену сложно | Новый acquisition channel и creator commerce |
| «Помни мои привычки, но не делай пугающих выводов» | Персонализация либо поверхностна, либо непрозрачна | Повторные поездки и defensible relevance |
| «Скажи, почему это лучший вариант именно для меня» | Recommendation score скрыт, а sponsored inventory создаёт конфликт | Booking confidence и снижение abandonment |

---

## 9. Где максимальна ценность собственных API

### Сценарии, требующие связи категорий

1. **Destination optimization.** Выбор города зависит одновременно от стоимости дороги, проживания, local mobility и доступных впечатлений.
2. **Multi-city compiler.** Порядок городов меняет цену транспорта, количество hotel nights и полезное время.
3. **Night-train / early-flight trade-off.** Более дешёвый перелёт может создать лишнюю ночь, transfer или потерянный день.
4. **Family and group constraints.** Нужны соседние места, rooms configuration, baggage, arrival time и общий/индивидуальный бюджет.
5. **Disruption recovery.** Один delay меняет connection, check-in, transfer и prepaid activity.
6. **Dynamic packaging.** Небольшое изменение дат может одновременно снизить fare и hotel rate, увеличив доступный budget для activities.
7. **Ancillary completion.** Багаж, места, страховка, eSIM, transfer и экскурсия предлагаются как закрытие реальной потребности, а не общий upsell.

### Приоритетные внешние интеграции

| Приоритет | Интеграция | Зачем нужна | Минимальный контракт |
|---|---|---|---|
| **P0** | Карты, geocoding, routing и transit | Feasibility, first/last mile, карта и travel time | Coordinates, route alternatives, duration, mode, live disruptions |
| **P0** | POI / restaurants / attractions | Реальные места вместо hallucinations | Stable ID, hours by date, closure, duration, rating provenance, booking URL/API |
| **P0** | Events | Концерты, спорт и фестивали часто определяют даты и направление | Date/time, venue, availability, ticket price |
| **P0** | Weather and hazard feeds | Day replan и risk-aware recommendations | Forecast, alert severity, location/time window |
| **P0** | Fare/rate rules и servicing APIs | Правильный checkout, cancel/exchange и replan | Reprice, hold, confirm, cancel, exchange, refundability, deadline |
| **P0** | Payments, loyalty и identity vault | Покупка нескольких компонентов после подтверждения | Tokenized passenger/profile data, points/cash split, SCA/3DS, receipts |
| **P1** | Visa, entry, health and official advisories | Подготовка и допустимость поездки | Nationality-aware rules, official source, effective date |
| **P1** | Restaurant reservations | Убирает разрыв между itinerary и реальным столом | Slots, party size, hold/book/cancel |
| **P1** | Tours and experiences | Cross-sell и насыщенный plan | Availability, duration, meeting point, cancellation terms |
| **P1** | Taxi, transfer, car rental | Закрывает first/last mile | Quote, capacity, baggage, pickup constraints |
| **P1** | Insurance, protection, eSIM, lounge | Contextual ancillary revenue | Eligibility, dynamic quote, coverage, fulfillment |
| **P1** | Supplier messaging / voice agent | Решает late check-in и исключения без API | Consent, call/message audit, structured outcome |
| **P2** | Social-content ingestion | Acquisition из Reels, TikTok, YouTube и blogs | Media metadata, creator attribution, extracted entities |
| **P2** | Expense and split-pay services | Group settlement и plan/fact | Multi-currency ledger, participant shares, reconciliation |
| **P2** | Photo timeline / creator publishing | Post-trip loop | User-controlled album, rights, publish consent, referral attribution |

---

## 10. Общая продуктовая основа: Trip Graph

Пять концепций ниже должны строиться не как пять независимых чат-ботов, а как интерфейсы к общей модели поездки.

### Ключевые сущности

- **Trip brief:** участники, даты и flexibility, origin, destination candidates, budget, pace, interests, must-have, veto.
- **Trip node:** flight, train, bus, hotel night, transfer, restaurant, POI, activity, document task или protection product.
- **Dependency:** «успеть после», «нужно до», «та же локация», «требует ночёвку», «отменить вместе», «затрагивает участника».
- **Constraint:** время, деньги, visa, accessibility, baggage, rooming, cancellation, loyalty, risk.
- **Quote:** цена, валюта, timestamp, expiry, source и условия.
- **Commitment:** held, pending confirmation, booked, changed, canceled, refunded.
- **Preference signal:** явный выбор или подтверждённый вывод; scope — current trip либо persistent.
- **Event:** delay, cancellation, gate, weather, closure, price change, missed connection risk.

### Разделение ответственности

- **LLM:** понимает запрос, задаёт минимальные уточнения, переводит intent в constraints, объясняет варианты и изменения.
- **Search tools:** получают live inventory и факты.
- **Solver:** строит допустимые комбинации и Pareto-front по цене, времени, комфорту и preference utility.
- **Verifier:** повторно проверяет цены, расписание, часы работы, buffers и полноту.
- **Transaction orchestrator:** управляет holds, repricing, порядком подтверждений и compensation steps.
- **Event engine:** следит за уже купленной поездкой и пересчитывает impact graph.
- **Human service:** принимает исключения с собранным контекстом и журналом выполненных действий.

### Необходимый интерфейс

Чат остаётся одним из способов управления, но главным экраном должен быть **Trip Canvas**:

- карта + вертикальный timeline;
- карточки транспорта, ночей, мест и бронирований;
- общий live budget и price expiry;
- sliders «дешевле ↔ комфортнее», «спокойнее ↔ насыщеннее», «популярное ↔ необычное»;
- locked items, которые AI не меняет;
- side-by-side сравнение 2–3 целостных вариантов;
- impact preview перед применением любого изменения.

---

## 11. Пять продуктовых концепций

## 11.1. Концепция A — «Компилятор поездки»

**Коротко:** из неполного замысла — в несколько целостных, проверенных и покупаемых вариантов всей поездки.

**Сильнейший сегмент:** массовый leisure с высоким выбором и сложные самостоятельные multi-city поездки; ценность растёт с числом категорий и ограничений.

### JTBD

> Когда я понимаю, какого отдыха хочу, но не знаю лучшего направления, дат и комбинации транспорта с отелем, собери несколько реалистичных вариантов в мой общий бюджет, объясни разницу и помоги купить выбранный план без повторной сборки.

### Ключевой сценарий

Пользователь говорит: «Хотим вдвоём на 8–10 дней в октябре, море плюс красивый город, не больше 260 000 ₽ целиком, без ночных перелётов, можно поезд между городами».

Компилятор:

1. превращает запрос в редактируемый brief;
2. параллельно исследует направления, dates, air/rail/bus, hotels, local transit и activities;
3. возвращает не сотни выдач, а три решения:
   - **дешевле:** 224 000 ₽, две пересадки, 9 дней;
   - **сбалансированно:** 248 000 ₽, прямой рейс туда и поезд между городами;
   - **комфортнее:** 278 000 ₽, лучше hotel location и меньше 7 часов в дороге;
4. показывает, какие расходы подтверждены live quote, а какие являются envelope;
5. позволяет закрепить отель или рейс и пересчитать остальное;
6. перед каждой покупкой делает reprice и показывает отдельное подтверждение;
7. после покупки превращает план в живой itinerary.

### Wow-момент

Пользователь двигает slider «меньше дороги», и на карте с таймлайном за секунды меняются порядок городов, вид транспорта, отель и общий бюджет. AI объясняет diff: «+11 400 ₽, зато на 6 ч 20 мин меньше в пути и без заезда после полуночи». Это не новый ответ в чате, а компиляция всей поездки.

### Интерфейс вне чата

- Trip Canvas с map + timeline + budget;
- три целостных варианта side-by-side;
- locks, sliders и constraint chips;
- live/estimated badges и price expiry;
- «почему выбран» и «что потеряем при замене»;
- единый transaction checklist.

### Необходимые API и данные

Собственные search/reprice/book/cancel APIs для air, hotels, rail и bus; maps/routing; POI/activities; weather; visa/entry; fare rules; payments; profile и history; alerts и servicing. Нужен solver, работающий поверх общего Trip Graph.

### Монетизация

- рост конверсии из inspiration в booking;
- attach rate hotel + transport + activities;
- dynamic packages;
- contextual baggage, seats, transfer, insurance, eSIM и protection;
- loyalty redemption и персональные offers.

### Риски и доверие

- combinatorial latency и быстро устаревающие цены;
- partial booking: один компонент подтвердился, другой уже недоступен;
- ложная полнота бюджета;
- preference overreach.

Контрмеры: holds, transaction ordering, mandatory reprice, rollback/compensation policy, visible estimate ranges, явные confirmations и user-controlled memory.

### Защитимость

Собственный cross-category inventory, история реальных выборов, graph of accepted trade-offs, performance transaction orchestration и данные об outcome после поездки. Общий LLM без этих слоёв не сможет воспроизвести качество.

### North-star metric

**Количество подтверждённых мультикатегорийных поездок на 1 000 AI planning starts.**

Supporting metrics: time-to-confident-plan, hard-constraint pass rate, booking conversion, category attach rate, GMV per trip, reprice abandonment и post-booking contact rate.

### Путь к north star

- **Первый полезный релиз:** один destination, round trip + hotel, полный live budget, три Pareto-варианта и locks.
- **Расширение:** rail/bus, multi-city, activities, flexible destination/date.
- **North star:** mode-neutral global trip compiler, group constraints, coordinated booking и continuous replan.

**Относительная сложность:** очень высокая.

---

## 11.2. Концепция B — «Автопилот поездки»

**Коротко:** AI следит за купленной поездкой как за системой зависимостей и готовит согласованный recovery plan.

**Сильнейший сегмент:** частые путешественники, семьи и владельцы дорогих или сложных маршрутов, где один сбой создаёт цепочку потерь.

### JTBD

> Когда что-то изменилось до или во время поездки, покажи, что именно пострадает, и предложи безопасный вариант восстановления всего маршрута, чтобы мне не связываться с каждым поставщиком отдельно.

### Ключевой сценарий

Рейс задерживается на три часа. Система понимает, что пользователь:

- пропустит последний train;
- приедет после hotel check-in cutoff;
- потеряет prepaid transfer;
- рискует не попасть на утреннюю экскурсию.

Вместо четырёх alerts она предлагает два recovery packages: другой рейс + сохранение исходного hotel либо ночь около аэропорта + утренний поезд + перенос экскурсии. Пользователь видит доплату, refund/credit, новые времена и подтверждает каждое денежное действие.

### Wow-момент

Уведомление приходит не «рейс задержан», а «поездка спасена: вот два проверенных варианта, поставщики и деньги уже просчитаны».

### Интерфейс

- impact map с затронутыми nodes;
- recovery packages side-by-side;
- deadline для решения;
- refund/credit ledger;
- кнопки подтверждения по действиям;
- бесшовный handoff человеку.

### API и данные

Live flight/rail/bus status, schedule changes, exchange/cancel/refund, hotel messaging, activity reservations, weather/hazards, alternative inventory, payment/credit, supplier communication.

### Монетизация

- paid protection или premium servicing;
- сохранённый GMV вместо полного refund;
- rebooking commissions;
- insurance/assistance;
- retention и loyalty.

### Риски

Самый высокий operational risk: неверное автоматическое изменение дорого обходится. Нужны strict approval boundaries, audit log, policy engine, human fallback и заранее определённая ответственность за partial failure.

### Защитимость и метрики

Moat создают собственные servicing APIs, event history и recovery outcomes. North star: **доля disruption cases, в которых пользователь принял согласованный recovery package до обращения в поддержку**. Дополнительно: saved trip GMV, resolution time, CSAT, human escalation и compensation cost.

### Путь

- **Первый релиз:** impact analysis и альтернативы без автоматического действия.
- **Расширение:** exchange/cancel после подтверждения для одной категории.
- **North star:** cross-category recovery с supplier calls, refunds и human exception desk.

**Относительная сложность:** очень высокая; особенно высока операционная ответственность.

---

## 11.3. Концепция C — «Из вдохновения в бронирование»

**Коротко:** любое travel-видео, фото, статья или screenshot становится не копией чужого маршрута, а адаптированной и покупаемой поездкой.

**Сильнейший сегмент:** social-first аудитория и пользователи на раннем этапе вдохновения, ещё не сформулировавшие направление и маршрут.

### JTBD

> Когда я увидел поездку, которая мне нравится, распознай, что именно меня зацепило, и преврати это в реалистичный вариант под мои даты, город вылета, бюджет и стиль.

### Ключевой сценарий

Пользователь делится Reel про Японию. AI:

1. распознаёт города, POI, сезон и визуальный vibe;
2. отделяет реальные места от montage/b-roll;
3. спрашивает, что важно сохранить;
4. строит feasible trip с live transport и hotels;
5. предупреждает, что часть мест закрыта или находится далеко;
6. предлагает максимально похожий и более бюджетный варианты;
7. сохраняет attribution creator и ведёт к бронированию.

### Wow-момент

На экране появляется diff «видео vs ваша поездка»: сохранены атмосфера и ключевые места, но логистика адаптирована под реальные даты и бюджет.

### Интерфейс

Share extension, visual storyboard, extracted-place chips, map, «сохранить / заменить / исключить», live trip preview.

### API и данные

Media understanding, social metadata, maps/POI, rights/attribution, live travel inventory, events, weather/seasonality и creator/referral ledger.

### Монетизация

Новый acquisition funnel, creator affiliate/revenue share, conversion в transport/hotel/activity и sponsored-but-labelled collections.

### Риски, moat и метрики

Риски: copyright, private/deleted content, неверное распознавание, overtourism, sponsored bias. Moat: dataset «какие элементы контента конвертируются в реальные trips» и creator network. North star: **confirmed trip GMV на 1 000 imported inspiration items**.

### Путь

- **Первый релиз:** public URL/photo → extracted places → hotel/flight suggestions.
- **Расширение:** feasibility rewrite и creator attribution.
- **North star:** любой media artifact → полный Trip Graph → booking → bookable post-trip story.

**Относительная сложность:** средне-высокая.

---

## 11.4. Концепция D — «Групповой переговорщик»

**Коротко:** AI не просто даёт группе comments и likes, а находит устраивающий всех покупаемый компромисс.

**Сильнейший сегмент:** друзья, большие семьи и event-группы с несколькими плательщиками, rooms и разными городами вылета.

### JTBD

> Когда у участников разные бюджеты, графики и интересы, собери ограничения приватно, объясни реальные компромиссы и доведи группу до решения и оплаты.

### Ключевой сценарий

Организатор создаёт ссылку. Каждый участник указывает даты, свой budget ceiling, must-have, veto и room/seat needs. Часть ответов может быть скрыта от группы. AI показывает три Pareto-варианта:

- минимальная общая цена;
- максимальное совпадение дат;
- лучший баланс интересов.

Для каждого видно, кто и чем жертвует, но приватные суммы не раскрываются. После голосования система держит доступные компоненты и собирает отдельные подтверждения/платежи.

### Wow-момент

AI говорит: «Если сдвинуть вылет на вечер пятницы, участвуют все шесть человек; общая поездка дешевеет на 9%, но двое теряют по полдня. Вот вариант без этой жертвы».

### Интерфейс

Group room, private preference inbox, consensus map, anonymous veto, scenario voting, split ledger и confirmation tracker.

### API и данные

Inventory для нескольких пассажиров и rooms, seat/room availability, holds, split payment, messaging, identity/passenger profiles и consent.

### Монетизация

Высокая group basket, несколько rooms/tickets, activities, transfers, group insurance и снижение брошенных групповых планов.

### Риски, moat и метрики

Риски: privacy, false consensus, изменение цены до последнего подтверждения, отказ одного участника. Moat: group preference graph и hold/payment orchestration. North star: **доля активированных group rooms, завершившихся мультикатегорийным бронированием**.

### Путь

- **Первый релиз:** сбор constraints + три объяснимых варианта + voting.
- **Расширение:** private budgets и AI mediation.
- **North star:** live holds, split payment, изменения состава и group servicing.

**Относительная сложность:** высокая.

---

## 11.5. Концепция E — «Оптимизатор полной стоимости»

**Коротко:** travel-CFO, который управляет не самой дешёвой ценой одной позиции, а ценностью всей поездки.

**Сильнейший сегмент:** budget-sensitive и flexible travelers, а также пользователи, готовые менять даты, modes и районы ради лучшего total value.

### JTBD

> Когда у меня ограниченный общий бюджет, помоги распределить его между дорогой, жильём и впечатлениями и предупреждай, когда небольшое изменение даёт непропорционально большую экономию.

### Ключевой сценарий

Пользователь выбрал направление, но trip total выше лимита. Оптимизатор предлагает:

- сместить вылет на день и сохранить hotel;
- взять поезд вместо перелёта между городами и убрать hotel night;
- переехать в район на 12 минут дальше, освободив бюджет на две activities;
- купить сейчас один компонент, а другой поставить на watch;
- добавить protection там, где volatility/risk действительно высоки.

### Wow-момент

Не «мы нашли билет на 5 000 ₽ дешевле», а «мы снизили полную стоимость на 23 400 ₽, сохранив все must-have и добавив один полезный день».

### Интерфейс

Live budget waterfall, plan/actual, price confidence, opportunity cards, what-if toggles и savings attribution.

### API и данные

Historical/live prices, fees, baggage, exchange rules, hotel nights, local transport, activities, FX, loyalty, alerts, price freeze/protection quotes.

### Монетизация

Рост completed trips за счёт budget fit; attach rate; price lock/protection; loyalty burn; targeted bundles. Риск каннибализации take rate нужно сравнивать с ростом конверсии и корзины.

### Риски, moat и метрики

Риски: неполная стоимость, сомнительные «сбережения», incentive conflict. Нужны all-in price и прозрачная baseline methodology. Moat: cross-category price curves и observed value trade-offs. North star: **доля поездок, приведённых в budget и купленных после принятой AI-оптимизации**.

### Путь

- **Первый релиз:** flight + hotel total, flexible-date what-if и price watch.
- **Расширение:** rail/bus, baggage, activities, loyalty и FX.
- **North star:** непрерывная оптимизация до cancellation deadlines и during-trip plan/actual.

**Относительная сложность:** высокая.

---

## 12. Сравнительная оценка концепций

Оценка по шкале 1–10. Для «доверия и операционного риска» более высокий балл означает более безопасную и управляемую модель.

| Концепция | GMV и cross-sell 30% | Сквозная ценность 20% | Дифференциация 20% | Использование API 15% | Защитимость 10% | Доверие / риск 5% | Итог |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A. Компилятор поездки** | 10 | 9 | 9 | 10 | 9 | 6 | **9,3** |
| **E. Оптимизатор полной стоимости** | 9 | 9 | 8 | 9 | 9 | 7 | **8,7** |
| **B. Автопилот поездки** | 7 | 10 | 9 | 9 | 9 | 5 | **8,4** |
| **D. Групповой переговорщик** | 8 | 9 | 8 | 8 | 8 | 7 | **8,2** |
| **C. Из вдохновения в бронирование** | 8 | 7 | 7 | 8 | 6 | 8 | **7,4** |

### Интерпретация

- **Компилятор** выигрывает, потому что непосредственно соединяет discovery с крупной мультикатегорийной корзиной и максимально использует имеющиеся API.
- **Оптимизатор стоимости** — не лучший отдельный бренд продукта, но обязательный decision engine внутри Компилятора.
- **Автопилот** создаёт самую сильную эмоциональную ценность после покупки и должен стать второй крупной волной; его сдерживают servicing и liability.
- **Group Negotiator** — сильный high-basket wedge, который следует строить поверх того же constraint solver.
- **Reel-to-Real** — хороший acquisition surface, но быстро копируется без собственного Trip Graph и transactional supply.

---

## 13. Проверка на пяти сценариях

Обозначения: **●●** — решает сценарий как ядро; **●** — помогает; **○** — косвенная ценность; **—** — почти не решает.

| Сценарий | Компилятор | Автопилот | Inspiration → booking | Group Negotiator | Total Cost |
|---|---:|---:|---:|---:|---:|
| Гибкий отпуск в заданный полный бюджет | ●● | ○ | ● | ● | ●● |
| Сложная multi-city / multimodal поездка | ●● | ●● | ○ | ● | ●● |
| Групповое путешествие с конфликтами | ● | ● | ● | ●● | ● |
| Сбой в уже купленном маршруте | ● | ●● | — | ○ | ● |
| Поездка из Reel, фото или статьи | ● | — | ●● | ○ | ● |

### Сквозные acceptance-сценарии

1. **Flexible budget:** система должна найти минимум два допустимых направления и объяснить полную цену, не выдавая estimate за live quote.
2. **Multimodal:** между каждым segment есть реалистичный transfer buffer; проверены nights, check-in и baggage.
3. **Group:** ни один private budget/veto не раскрывается; покупка не начинается без согласия соответствующего участника.
4. **Disruption:** impact graph называет все затронутые commitments; до подтверждения не совершается обмен или отмена.
5. **Social input:** извлечённые места имеют stable IDs и проверенные dates/hours; creator/source сохраняется.

### Нефункциональные quality gates

- 100% денежных действий имеют явное, журналируемое подтверждение.
- 100% bookable components проходят reprice непосредственно перед подтверждением.
- Ни один failed/expired quote не маркируется как доступный.
- Каждый hard constraint либо соблюдён, либо явно показан как конфликт.
- Каждый внешний факт, влияющий на покупку, имеет source и актуальность.
- Partial booking имеет заранее определённый rollback или manual recovery path.
- Low-confidence и policy exceptions передаются человеку вместе с Trip Graph, а не пустым новым диалогом.

---

## 14. Рекомендация: строить Trip Compiler как новый центр travel-продукта

### Формулировка продукта

**«Опишите поездку, которую хотите получить, — AI соберёт несколько полностью просчитанных вариантов, объяснит компромиссы, поможет купить выбранный и сохранит его работоспособным до возвращения».**

Это принципиально отличается от прежнего ассистента:

| Прежний паттерн | Новый паттерн |
|---|---|
| Запрос → несколько результатов | Намерение → исполнимый Trip Graph |
| Один вертикальный поиск | Air + hotel + rail + bus + external travel layer |
| Ответ в чате | Canvas, map, timeline и budget |
| Пользователь соединяет части | Solver оптимизирует комбинацию |
| Нет состояния после ответа | Living trip с commitments и events |
| Alert о проблеме | Impact analysis и recovery package |
| Общие предпочтения | Память принятых trade-offs с контролем пользователя |

### Почему ставка подтверждена минимум двумя независимыми сигналами

1. **Потребность и граница доверия:** глобальное исследование Booking.com показывает высокий спрос на AI travel при низкой готовности к бесконтрольной автономии. Это поддерживает модель «AI делает тяжёлую работу, пользователь подтверждает». [Booking.com, 23.07.2025](https://news.booking.com/bookingcom-releases-the-global-ai-sentiment-report/).
2. **Коммерческий сигнал:** Trip.com связывает использование destination/itinerary recommendations с двукратной order conversion и более высоким return rate. [Trip.com, 06.06.2024](https://www.trip.com/newsroom/tripgenie-new-features-2/).
3. **Production proof транзакции:** Priceline, Air India и MakeMyTrip уже показывают, что conversational/agentic flow можно соединить с live inventory и подтверждённой покупкой. [Priceline, 03.06.2026](https://press.priceline.com/pricelines-penny-goes-fully-agentic/), [Air India, 22.01.2025](https://www.airindia.com/in/en/newsroom/press-release/Air-India-launches-AI-driven-eZ-Booking.html), [MakeMyTrip, 07.08.2025](https://investors.mmtcdn.com/Press_Release_Gen_AI_Trip_Planning_Assistant_07_08_2025_404cc1872a.pdf).
4. **Архитектурный сигнал:** исследования планирования показывают преимущество constraint-aware multi-agent / solver-подходов над монолитной генерацией. [ATLAS, 2025](https://research.google/pubs/atlas-constraints-aware-multi-agent-collaboration-for-real-world-travel-planning/), [TRIP-PAL, 2024](https://arxiv.org/abs/2406.10196).

### Рекомендуемая последовательность capability-волн

Последовательность не привязана к календарному сроку; каждая волна должна давать самостоятельную пользовательскую ценность.

1. **Trip Graph foundation.** Общий brief, constraints, nodes, quotes, provenance, карта, timeline и budget.
2. **Compiler v1.** Flexible flight + hotel, три целостных варианта, locks, sliders, live total и checkout confirmations.
3. **Multimodal expansion.** Rail, bus, multi-city, transfer feasibility, activities и external POI.
4. **Total Cost Intelligence.** What-if, price watch, loyalty, fees, protection и contextual cross-sell.
5. **Group Negotiator и Inspiration inputs.** Один solver получает новые способы входа и более сложные constraints.
6. **Autopilot.** Event graph, impact analysis, servicing APIs, recovery packages и human exception desk.

### Метрики флагмана

**North star:** confirmed multi-category trips per 1 000 AI planning starts.

**Funnel:**

- brief completion;
- first feasible plan rate;
- time to first accepted variant;
- share reaching reprice;
- purchase conversion;
- category attach rate;
- GMV and margin per completed trip.

**Качество и доверие:**

- hard-constraint pass rate;
- quote expiry/reprice failure;
- unsupported fact rate;
- user corrections to extracted constraints;
- monetary confirmation violations;
- manual recovery rate;
- post-booking contact rate и CSAT.

**Learning loop:**

- доля пользователей, включивших travel memory;
- reuse of learned preferences;
- acceptance lift from preference-informed ranking;
- repeat AI-planned trips.

### Главные продуктовые риски

1. **Слишком ранняя генерация.** Система строит красивый план до фиксации ключевых constraints. Решение: progressive brief и visible assumptions.
2. **Ложная оптимальность.** «Лучший» вариант зависит от скрытых коммерческих стимулов. Решение: отделить sponsored eligibility от user utility и маркировать рекламу.
3. **Неполный бюджет.** Food и local expenses неизбежно приблизительны. Решение: разделять live commitments, researched estimates и user envelopes.
4. **Latency.** Полный search graph может быть медленным. Решение: progressive results, cached discovery, параллельный tool use и deep verification только shortlist.
5. **Partial failure при checkout.** Решение: holds, order planning, repricing и compensation runbook.
6. **Over-autonomy.** Решение: подтверждение каждого денежного действия, preview последствий и журнал.
7. **Нет операционного владельца исключений.** Решение: проектировать human service как часть продукта с первого transactional release.

### Kill criteria

Ставку следует пересмотреть, если после контролируемых экспериментов:

- AI-plan не повышает мультикатегорийный attach относительно обычного funnel;
- time-to-confident-plan не сокращается;
- пользователи массово пересобирают результат вручную;
- hard-constraint или reprice failures делают поддержку дороже дополнительной маржи;
- users предпочитают отдельные вертикальные выдачи даже после знакомства с Canvas.

---

## 15. Итоговая продуктовая позиция

Рынок уже доказал ценность natural-language travel search. Копировать этот слой поздно. Наиболее сильная возможность для компании с собственными API полного цикла — занять слой **между намерением и несколькими вертикальными движками**.

Флагманом должен стать не «AI-ассистент по путешествиям», а **операционная система конкретной поездки**:

- **Compiler** создаёт целостное решение;
- **Total Cost Engine** распределяет бюджет;
- **Group Negotiator** согласует людей;
- **Inspiration Import** приводит новый спрос;
- **Autopilot** сохраняет outcome при изменениях.

Внешне это один Trip Canvas и один понятный promise. Внутри — Trip Graph, специализированные tools, solver, verifier, transaction orchestrator и human exception layer.

Именно такая конструкция одновременно создаёт wow-эффект, увеличивает GMV/cross-sell и формирует преимущество, которое нельзя воспроизвести одной более новой языковой моделью.

---

## 16. Краткий реестр ключевых источников

Последняя проверка ссылок: 16 августа 2026 года.

- [Priceline Penny Goes Fully Agentic, 03.06.2026](https://press.priceline.com/pricelines-penny-goes-fully-agentic/)
- [Google AI Mode travel Canvas and agentic booking, 17.11.2025](https://blog.google/products-and-platforms/products/search/agentic-plans-booking-travel-canvas-ai-mode/)
- [Google: hotel booking in AI Mode, проверено 16.08.2026](https://support.google.com/travel/answer/17216079)
- [MakeMyTrip Myra, 07.08.2025](https://investors.mmtcdn.com/Press_Release_Gen_AI_Trip_Planning_Assistant_07_08_2025_404cc1872a.pdf)
- [Trip.com TripGenie, 06.06.2024](https://www.trip.com/newsroom/tripgenie-new-features-2/)
- [Booking.com Global AI Sentiment Report, 23.07.2025](https://news.booking.com/bookingcom-releases-the-global-ai-sentiment-report/)
- [Expedia Romie, 14.05.2024](https://www.expedia.com/newsroom/spring-product-release-2024/)
- [Expedia Trip Matching, 12.06.2025](https://www.expedia.com/newsroom/now-live-expedia-launches-industry-first-feature-that-turns-reels-on-instagram-into-bookable-travel-itineraries/)
- [KAYAK AI Mode, 15.10.2025](https://www.kayak.com/news/ai-mode/)
- [Mindtrip product page](https://mindtrip.ai/home)
- [Air India eZ Booking, 22.01.2025](https://www.airindia.com/in/en/newsroom/press-release/Air-India-launches-AI-driven-eZ-Booking.html)
- [Navan Intelligence](https://navan.com/intelligence)
- [Omio in ChatGPT, 14.04.2026](https://www.omio.com/corporate/newsroom/press-releases/omio-launches-in-chatgpt-bringing-its-real-time-multimodal-travel-search-to-900-million-users/)
- [TravelPlanner benchmark, 2024](https://arxiv.org/abs/2402.01622)
- [TRIP-PAL, 2024](https://arxiv.org/abs/2406.10196)
- [Google Research ATLAS, 2025](https://research.google/pubs/atlas-constraints-aware-multi-agent-collaboration-for-real-world-travel-planning/)
- [TREK, июль 2026](https://arxiv.org/abs/2607.26977)
