import { z } from "zod";

const nullableNumber = z.number().nullable().optional();
const httpsImageUrl = z.string().url().refine((value) => /^https:\/\//iu.test(value));

export const accountsDataSchema = z.object({
  accounts: z.array(
    z.object({
      id: z.string(),
      accountType: z.string(),
      name: z.string(),
      balance: z.union([z.number(), z.string()]).nullable().optional(),
      currency: z.string(),
      cards: z.array(
        z.object({
          id: z.string(),
          ucid: z.string(),
          name: z.string(),
          status: z.string(),
        }),
      ),
    }),
  ),
});

export const operationsDataSchema = z.object({
  accountId: z.string(),
  days: z.number(),
  total: z.number(),
  operations: z.array(
    z.object({
      id: z.string(),
      occurredAt: z.string(),
      type: z.string(),
      amount: z.union([z.number(), z.string()]).nullable().optional(),
      currency: z.string(),
      description: z.string(),
      category: z.string().optional(),
    }),
  ),
});

export const spendingDataSchema = z.object({
  accountId: z.string(),
  days: z.number(),
  totalSpent: z.number(),
  totalEarned: z.number(),
  currency: z.string(),
  categories: z.array(
    z.object({
      name: z.string(),
      amount: z.number(),
      sharePct: z.number(),
    }),
  ),
});

export const ordersDataSchema = z.object({
  kind: z.string(),
  total: z.number(),
  orders: z.array(
    z.object({
      orderId: z.string(),
      objectType: z.string(),
      status: z.string(),
      amount: z.union([z.number(), z.string()]).nullable().optional(),
      createdAt: z.string(),
      title: z.string(),
      eventName: z.string(),
      hotelName: z.string(),
      destination: z.string(),
    }),
  ),
});

export const eventOrderDetailsDataSchema = z.object({
  orderId: z.string(),
  status: z.string(),
  createdAt: z.string(),
  eventName: z.string(),
  genres: z.array(z.string()),
  venue: z.string(),
  address: z.string(),
  startDateTime: z.string(),
  hallName: z.string(),
  seatCount: z.number().int().nonnegative(),
  ticketPricesRub: z.array(z.union([z.number(), z.string()])),
  totalAmountRub: z.union([z.number(), z.string()]),
});
export type EventOrderDetailsData = z.infer<typeof eventOrderDetailsDataSchema>;

export const travelOrderDetailsDataSchema = z.object({
  orderId: z.string(),
  kind: z.string(),
  status: z.string(),
  amountRub: z.union([z.number(), z.string()]),
  createdAt: z.string(),
  title: z.string(),
  destination: z.string(),
  detailsAvailable: z.boolean(),
  checkInDate: z.string().optional(),
  checkOutDate: z.string().optional(),
  hotelName: z.string().optional(),
  hotelStars: z.number().int().min(0).max(5).optional(),
  mealTypes: z.array(z.string()).optional(),
  roomCount: z.number().int().nonnegative().optional(),
  guestCount: z.number().int().nonnegative().optional(),
});
export type TravelOrderDetailsData = z.infer<typeof travelOrderDetailsDataSchema>;

export const audienceProfileDataSchema = z.object({
  ageBand: z.enum([
    "unknown",
    "under_16",
    "16_17",
    "18_24",
    "25_34",
    "35_44",
    "45_54",
    "55_64",
    "65_plus",
  ]),
  adultContentAllowed: z.boolean().nullable(),
});
export type AudienceProfileData = z.infer<typeof audienceProfileDataSchema>;

const placeSchema = z.object({ name: z.string(), code: z.string() });

export const flightHistoryDataSchema = z.object({
  searches: z.array(
    z.object({
      searchedAt: z.string(),
      from: placeSchema,
      to: placeSchema,
      passengers: z.record(z.string(), z.unknown()),
    }),
  ),
});

export const flightSearchDataSchema = z.object({
  fromCode: z.string(),
  toCode: z.string(),
  date: z.string(),
  searchId: z.string(),
  complete: z.boolean(),
  offers: z.array(
    z.object({
      offerId: z.string(),
      price: z.number(),
      currency: z.string(),
      summary: z.string(),
      departureAt: z.string(),
      arrivalAt: z.string(),
      withBaggage: z.boolean(),
      refundable: z.boolean(),
      vendor: z.string(),
      legs: z.array(
        z.object({
          carrier: z.string(),
          fromAirport: z.string(),
          toAirport: z.string(),
          departureAt: z.string(),
          arrivalAt: z.string(),
          durationMinutes: z.union([z.number(), z.string()]),
          stops: z.number(),
        }),
      ),
    }),
  ),
});

export const hotelAutocompleteDataSchema = z.object({
  query: z.string(),
  suggestions: z.array(
    z.object({
      kind: z.enum(["location", "hotel"]),
      id: z.string(),
      name: z.string(),
      signature: z.string(),
      type: z.string(),
    }),
  ),
});

export const hotelSearchDataSchema = z.object({
  destinationId: z.number(),
  checkinDate: z.string(),
  checkoutDate: z.string(),
  isLoadingCompleted: z.boolean(),
  total: z.number(),
  hotels: z.array(
    z.object({
      hotelId: z.string(),
      name: z.string(),
      stars: z.number(),
      price: z.number(),
      currency: z.string(),
      address: z.string(),
      rating: nullableNumber,
      meal: z.string(),
      availableRooms: nullableNumber,
      latitude: nullableNumber,
      longitude: nullableNumber,
      imageUrl: httpsImageUrl.optional(),
    }),
  ),
});

export const hotelDetailsDataSchema = z.object({
  hotelId: z.string(),
  name: z.string(),
  stars: z.number(),
  address: z.string(),
  description: z.string(),
  checkInTime: z.string(),
  checkOutTime: z.string(),
  latitude: nullableNumber,
  longitude: nullableNumber,
  facilities: z.array(z.string()),
});

const eventSlotSchema = z.object({
  startDateTime: z.string(),
  slotId: z.string(),
  priceFix: nullableNumber,
  priceMin: nullableNumber,
  priceMax: nullableNumber,
});

export const afishaCatalogDataSchema = z.object({
  kind: z.string(),
  city: z.string(),
  dateFrom: z.string(),
  dateTo: z.string(),
  scanned: z.number(),
  total: z.number(),
  events: z.array(
    z.object({
      eventId: z.string(),
      name: z.string(),
      kind: z.string(),
      genres: z.array(z.string()),
      ageRestriction: z.string(),
      rating: nullableNumber,
      imageUrl: httpsImageUrl.optional(),
      slots: z.array(eventSlotSchema),
    }),
  ),
});

export const afishaPlacesDataSchema = z.object({
  kind: z.string(),
  city: z.string(),
  total: z.number(),
  places: z.array(
    z.object({
      objectId: z.string(),
      name: z.string(),
      address: z.string(),
      latitude: nullableNumber,
      longitude: nullableNumber,
      subways: z.array(z.string()),
    }),
  ),
});

export const concertScheduleDataSchema = z.object({
  eventId: z.string(),
  kind: z.string(),
  showings: z.array(
    z.object({
      eventId: z.string(),
      objectId: z.string(),
      venue: z.string(),
      address: z.string(),
      latitude: nullableNumber,
      longitude: nullableNumber,
      startDateTime: z.string(),
      slotId: z.string(),
      priceFix: nullableNumber,
      priceMin: nullableNumber,
      priceMax: nullableNumber,
    }),
  ),
});
