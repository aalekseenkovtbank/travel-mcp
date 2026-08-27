import { useState } from "react";
import { Link } from "react-router-dom";

type EventKind = "Все" | "Театр" | "Кино" | "Музыка";

type WeekendEvent = {
  id: string;
  title: string;
  kind: Exclude<EventKind, "Все">;
  date: string;
  time: string;
  venue: string;
  address: string;
  price: string;
  age: string;
  match: number;
  image: string;
  description: string;
  reason: string;
};

const events: WeekendEvent[] = [
  {
    id: "dog-heart",
    title: "Собачье сердце",
    kind: "Театр",
    date: "29 августа",
    time: "14:00",
    venue: "Театр комедии",
    address: "Суворовская площадь, 1/52",
    price: "1 200–6 000 ₽",
    age: "18+",
    match: 98,
    image: "https://media.ticketland.ru/images/250x250/a0/88/a088539103251c7c89e3770a8884be3a.jpg",
    description: "Булгаковская сатира о человеке, власти и опасной уверенности в том, что природу можно исправить по плану.",
    reason: "Продолжает вашу линию классических постановок — от «Ревизора» до «Преступления и наказания».",
  },
  {
    id: "interstellar",
    title: "Киномикс: Интерстеллар",
    kind: "Музыка",
    date: "30 августа",
    time: "13:00",
    venue: "Концертный зал «Москва»",
    address: "проспект Андропова, 1",
    price: "2 500–12 000 ₽",
    age: "6+",
    match: 94,
    image: "https://kassa.rambler.ru/s/StaticContent/P/Aimg/2604/21/260421173949825.jpg",
    description: "Оркестровая программа по мотивам «Интерстеллара»: масштабная киномузыка, свет и эффект большого экрана без самого фильма.",
    reason: "Редкое пересечение двух ваших интересов — фантастики и живой музыки.",
  },
  {
    id: "algernon",
    title: "Цветы для Элджернона",
    kind: "Театр",
    date: "29 или 30 августа",
    time: "16:00 / 19:00",
    venue: "Intact",
    address: "Сущёвский Вал, 43",
    price: "1 800–3 500 ₽",
    age: "18+",
    match: 91,
    image: "https://kassa.rambler.ru/s/StaticContent/P/Aimg/2602/12/260212232913315.jpg",
    description: "Камерная психологическая драма по роману Дэниела Киза — про интеллект, одиночество и цену быстрого чуда.",
    reason: "Литературная постановка с сильным сюжетом — ваш устойчивый театральный паттерн.",
  },
  {
    id: "terminator",
    title: "Терминатор 2: Судный день",
    kind: "Кино",
    date: "29 августа",
    time: "с 17:00",
    venue: "25 кинотеатров Москвы",
    address: "ближайший — ЦДМ, 0,7 км от центра",
    price: "от 440 ₽",
    age: "18+",
    match: 89,
    image: "https://kassa.rambler.ru/s/StaticContent/P/Aimg/2507/17/250717201414504.jpg",
    description: "Большое возвращение классики научной фантастики на экран — погоня, технотриллер и один из лучших сиквелов в истории кино.",
    reason: "В истории заказов у вас много фантастики и экшена: «Дюна», «Матрица», «Майор Гром».",
  },
  {
    id: "dream-code",
    title: "Код сна",
    kind: "Кино",
    date: "29 августа",
    time: "с 12:00",
    venue: "36 кинотеатров Москвы",
    address: "ГУМ, ЦДМ, «Октябрь», «Зотов» и другие",
    price: "от 550 ₽",
    age: "18+",
    match: 84,
    image: "https://kassa.rambler.ru/s/StaticContent/P/Aimg/2607/23/260723121126008.jpg",
    description: "Новая фантастическая история на стыке боевика и психологического триллера — хороший выбор, если хочется премьеры.",
    reason: "Совпадает с вашим любимым жанровым сочетанием: фантастика, напряжение и динамичный сюжет.",
  },
];

const kinds: EventKind[] = ["Все", "Театр", "Кино", "Музыка"];
const hotelCheckoutUrl = "https://www.tbank.ru/travel/hotels/new/checkout/?guests=2&locationCode=hotel&dateFrom=2026-08-29&dateTo=2026-08-30&destinationId=1422275&hotelId=1422275&bookHash=now-multi-4f8c779e-485f-4fde-ab85-92878522b3c5";

export function WeekendMoscow() {
  const [kind, setKind] = useState<EventKind>("Все");
  const [selected, setSelected] = useState<string>(events[0].id);
  const visible = kind === "Все" ? events : events.filter((event) => event.kind === kind);
  const chosen = events.find((event) => event.id === selected) ?? events[0];

  return (
    <main className="weekend-page">
      <header className="weekend-nav">
        <Link className="weekend-brand" to="/" aria-label="Travel Nova, на главную">
          <span>TN</span>
          <strong>travel nova</strong>
        </Link>
        <div className="weekend-nav-meta">
          <span>Москва</span>
          <span>29–30 августа</span>
        </div>
      </header>

      <section className="weekend-hero">
        <div className="weekend-hero-copy">
          <p className="weekend-kicker">Персональная афиша · 5 вариантов</p>
          <h1>Ваши выходные<br /><em>в Москве</em></h1>
          <p className="weekend-lede">
            Классическая драматургия, умная фантастика и музыка из кино — подборка по вашим заказам Афиши и привычкам последних двух месяцев.
          </p>
        </div>
        <aside className="weekend-profile" aria-label="Профиль интересов">
          <span>Основа подбора</span>
          <strong>13</strong><small>заказов в кино</small>
          <strong>4</strong><small>театральных заказа</small>
          <strong>1</strong><small>альтернативный концерт</small>
        </aside>
      </section>

      <section className="weekend-hotel" aria-labelledby="weekend-hotel-title">
        <div className="weekend-hotel-photo-wrap">
          <img
            className="weekend-hotel-photo"
            src="https://continental-hotel.ru/upload/iblock/e8d/lftawfc475dp2yybk6m23ixhf32u1duf.jpeg"
            alt="Фасад пятизвёздочного отеля Continental на Тверской улице"
          />
          <span>Ваш отель</span>
        </div>
        <div className="weekend-hotel-copy">
          <div className="weekend-hotel-heading">
            <div>
              <p>5 звёзд · Тверская, 22</p>
              <h2 id="weekend-hotel-title">Continental</h2>
            </div>
            <strong>13 427,25 ₽</strong>
          </div>
          <p className="weekend-hotel-description">
            Пятизвёздочный отель на главной улице Москвы, в пешей доступности от Красной площади, Большого театра и Патриарших прудов. Современный интерьер с мотивами русского авангарда — спокойная база для насыщенных выходных.
          </p>
          <div className="weekend-hotel-facts">
            <div><span>Номер</span><strong>Делюкс, King Size · 38 м²</strong></div>
            <div><span>Даты</span><strong>29–30 августа · 2 взрослых</strong></div>
            <div><span>Тариф</span><strong>Без завтрака · оплата сейчас</strong></div>
            <div><span>Отмена</span><strong>Бесплатно до 28 августа, 13:30</strong></div>
          </div>
          <div className="weekend-hotel-actions">
            <a href={hotelCheckoutUrl} target="_blank" rel="noreferrer">
              Перейти к оформлению <span aria-hidden="true">↗</span>
            </a>
            <small>Бронь ещё не создана. Итоговые условия проверьте на странице T‑Bank.</small>
          </div>
        </div>
      </section>

      <div className="weekend-toolbar">
        <p>От более точного совпадения — к экспериментальному</p>
        <div className="weekend-filters" role="group" aria-label="Фильтр событий">
          {kinds.map((item) => (
            <button key={item} className={kind === item ? "active" : ""} onClick={() => setKind(item)}>{item}</button>
          ))}
        </div>
      </div>

      <section className="weekend-grid" aria-label="Рекомендованные события">
        {visible.map((event, index) => (
          <article className={`weekend-card ${selected === event.id ? "selected" : ""}`} key={event.id}>
            <div className="weekend-poster-wrap">
              <img src={event.image} alt={`Постер события «${event.title}»`} className="weekend-poster" />
              <span className="weekend-rank">0{events.indexOf(event) + 1}</span>
              <span className="weekend-match">{event.match}% совпадение</span>
            </div>
            <div className="weekend-card-body">
              <div className="weekend-card-meta"><span>{event.kind}</span><span>{event.age}</span></div>
              <h2>{event.title}</h2>
              <p>{event.description}</p>
              <dl>
                <div><dt>Когда</dt><dd>{event.date}, {event.time}</dd></div>
                <div><dt>Где</dt><dd>{event.venue}</dd></div>
                <div><dt>Цена</dt><dd>{event.price}</dd></div>
              </dl>
              <button className="weekend-select" onClick={() => setSelected(event.id)}>
                {selected === event.id ? "Выбрано" : "Выбрать"}<span aria-hidden="true">→</span>
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="weekend-choice" aria-live="polite">
        <p>Ваш выбор</p>
        <div>
          <h2>{chosen.title}</h2>
          <span>{chosen.date} · {chosen.time} · {chosen.price}</span>
        </div>
        <p>{chosen.reason}</p>
      </section>

      <footer className="weekend-footer">
        <span>Цены и наличие проверены 27 августа 2026</span>
        <span>Источник: T‑Bank Афиша</span>
      </footer>
    </main>
  );
}
