import type { City, PreferenceProfile, TripBrief } from "@travel-growth-inspiration/contracts";

import type {
  DateWindow,
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  NearbySearchOptions,
  PlannerDataProvider,
  ProviderResult,
} from "./provider-types.js";
import { emptyBehavioralInsights } from "./behavioral-profile.js";

function seedOf(...values: string[]): number {
  return values.join(":").split("").reduce((sum, character) => sum + character.charCodeAt(0), 0);
}

function offset(latitude: number, longitude: number, index: number): [number, number] {
  const angle = (index * 1.7 + 0.4) % (Math.PI * 2);
  const amount = 0.003 + index * 0.0007;
  return [latitude + Math.sin(angle) * amount, longitude + Math.cos(angle) * amount];
}

export class DemoPlannerProvider implements PlannerDataProvider {
  readonly dataMode = "demo" as const;

  async profile(): Promise<ProviderResult<PreferenceProfile>> {
    const checkedAt = new Date().toISOString();
    return {
      data: {
        profileVersion: 2,
        generatedAt: new Date().toISOString(),
        source: "fallback",
        analysisWindowDays: 90,
        transactionCount: 0,
        estimatedMonthlyIncomeRub: 0,
        incomeCohort: "unknown",
        incomeConfidence: "unavailable",
        monthlySpendRub: 110_000,
        diningSpendRub: 18_000,
        weekendAverageDailySpendRub: 0,
        weekdayAverageDailySpendRub: 0,
        weekendSpendSharePct: 0,
        averageCheckRub: 0,
        medianCheckRub: 0,
        categoryBreakdown: [],
        diningProfile: {
          averageCheckRub: 0,
          medianCheckRub: 0,
          preferredCuisines: [],
          preferredVenueTypes: [],
        },
        shoppingProfile: {
          averageCheckRub: 0,
          medianCheckRub: 0,
          preferredStoreTypes: [],
        },
        preferredCategories: ["Рестораны", "Развлечения", "Транспорт"],
        favoriteMerchants: [],
        favoriteDiningMerchants: [],
        eventInterests: ["концерты", "театр"],
        previousDestinations: [],
        behavioralInsights: emptyBehavioralInsights(),
        llmSummary: "Нейтральный демонстрационный профиль без банковских транзакций.",
        notes: ["Банковский профиль недоступен — используются нейтральные предпочтения."],
      },
      warnings: ["Персонализация работает в нейтральном режиме без банковских данных."],
      isFallback: true,
      source: "Демо-профиль",
      checkedAt,
    };
  }

  async flights(
    from: City,
    to: City,
    date: string,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<FlightInventoryItem[]>> {
    const checkedAt = new Date().toISOString();
    const passengers = travelers.adults + travelers.childrenAges.length * 0.7;
    const seed = seedOf(from.iata, to.iata, date);
    const distanceFactor = Math.max(1, Math.abs(from.longitude - to.longitude) / 8);
    return {
      data: Array.from({ length: 5 }, (_, index) => {
        const hour = 7 + index * 3;
        return {
          offerId: `demo-${from.iata}-${to.iata}-${date}-${index}`,
          summary: `Прямой рейс ${from.iata} → ${to.iata}, ${hour}:20`,
          priceRub: Math.round(
            (4_200 + (seed % 2_200) + distanceFactor * 2_700 + index * 1_800) * passengers,
          ),
          departureTime: `${String(hour).padStart(2, "0")}:20`,
          arrivalTime: `${String((hour + 2 + Math.floor(distanceFactor)) % 24).padStart(2, "0")}:10`,
          source: "Демо-данные авиа",
          live: false,
          checkedAt,
        };
      }),
      warnings: ["Цены на перелёт демонстрационные: живой авиа-провайдер недоступен."],
      isFallback: true,
      source: "Демо-данные авиа",
      checkedAt,
    };
  }

  async hotels(
    city: City,
    window: DateWindow,
    _travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<HotelInventoryItem[]>> {
    const checkedAt = new Date().toISOString();
    const nights = Math.max(
      1,
      Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
    );
    const seed = seedOf(city.id, window.startDate);
    const names = ["Городские истории", "Локаль", "Панорама", "Северный свет", "Гранд маршрут"];
    return {
      data: names.map((name, index) => {
        const [latitude, longitude] = offset(city.latitude, city.longitude, index);
        return {
          hotelId: `demo-${city.id}-${index}`,
          name: `${name} · ${city.name}`,
          stars: Math.min(5, 3 + Math.floor(index / 2)),
          priceRub: Math.round((3_200 + (seed % 900) + index * 2_100) * nights),
          address: `Центральный район, ${city.name}`,
          rating: 8.1 + index * 0.25,
          ...(index > 0 ? { meal: "Завтрак включён" } : {}),
          latitude,
          longitude,
          source: "Демо-данные отелей",
          live: false,
          checkedAt,
        };
      }),
      warnings: ["Цены на отели демонстрационные: живой отельный провайдер недоступен."],
      isFallback: true,
      source: "Демо-данные отелей",
      checkedAt,
    };
  }

  async events(
    city: City,
    window: DateWindow,
    interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>> {
    const checkedAt = new Date().toISOString();
    const interest = interests[0] ?? city.tags[0] ?? "культура";
    const [latitude, longitude] = offset(city.latitude, city.longitude, 6);
    return {
      data: [
        {
          eventId: `demo-event-${city.id}`,
          name: `Вечер про ${interest}: специальная программа`,
          kind: "событие",
          dateTime: `${window.startDate} 19:00`,
          venue: `Городская сцена · ${city.name}`,
          address: `Центральный район, ${city.name}`,
          latitude,
          longitude,
          source: "Демо-афиша",
          checkedAt,
        },
      ],
      warnings: ["Событие показано как пример: живая афиша недоступна."],
      isFallback: true,
      source: "Демо-афиша",
      checkedAt,
    };
  }

  async nearby(
    city: City,
    anchor: NearbyAnchor,
    options: NearbySearchOptions = {},
  ): Promise<ProviderResult<NearbyPlace[]>> {
    const checkedAt = new Date().toISOString();
    const latitude = anchor.latitude ?? city.latitude;
    const longitude = anchor.longitude ?? city.longitude;
    const names = [
      "Локальная кухня",
      "Городское кафе",
      "Бистро у площади",
      "Семейная траттория",
      "Кафе во дворе",
      ...(options.includePointsOfInterest
        ? [
            ...((options.placeKinds?.includes("culture") ?? true) ? ["Главный музей"] : []),
            ...(options.placeKinds?.includes("nature") ? ["Городской парк", "Смотровая точка"] : []),
            ...(options.placeKinds?.includes("nightlife") ? ["Бар с локальной сценой"] : []),
          ]
        : []),
    ];
    return {
      data: names.map((name, index) => {
        const [placeLatitude, placeLongitude] = offset(latitude, longitude, index + 2);
        const restaurant = index < 5;
        return {
          osmId: `demo-place-${city.id}-${anchor.type}-${anchor.id}-${index}`,
          type: restaurant ? "restaurant" : "poi",
          name: `${name} · демо`,
          latitude: placeLatitude,
          longitude: placeLongitude,
          ...(restaurant ? { cuisine: index === 0 ? "regional" : "international" } : {}),
          ...(!restaurant
            ? {
                category: name.includes("музей")
                  ? "museum"
                  : name.includes("парк")
                    ? "park"
                    : name.includes("Смотровая")
                      ? "viewpoint"
                      : name.includes("Бар")
                        ? "bar"
                        : "attraction",
              }
            : {}),
          distanceMeters: 350 + index * 210,
          source: "Демо-места",
          checkedAt,
        };
      }),
      warnings: ["Места рядом показаны в демонстрационном режиме без данных OSM."],
      isFallback: true,
      source: "Демо-места",
      checkedAt,
    };
  }

  async close(): Promise<void> {}
}
