import { z } from "zod";

export const tripPresetSchema = z.enum(["weekend", "vacation", "event"]);
export type TripPreset = z.infer<typeof tripPresetSchema>;

export const travelersSchema = z.object({
  adults: z.number().int().min(1).max(6),
  childrenAges: z.array(z.number().int().min(0).max(17)).max(5),
});

export const constraintStrengthSchema = z.enum(["soft", "hard"]);
export type ConstraintStrength = z.infer<typeof constraintStrengthSchema>;

export const preferencePolaritySchema = z.enum(["prefer", "avoid"]);
export type PreferencePolarity = z.infer<typeof preferencePolaritySchema>;

export const tripPreferenceConstraintSchema = z.object({
  value: z.string().trim().min(1).max(80),
  polarity: preferencePolaritySchema,
  strength: constraintStrengthSchema,
}).strict();
export type TripPreferenceConstraint = z.infer<typeof tripPreferenceConstraintSchema>;

export const tripPaceSchema = z.enum(["relaxed", "balanced", "active"]);
export type TripPace = z.infer<typeof tripPaceSchema>;

export const tripPreferencesSchema = z.object({
  destinationTags: z.array(tripPreferenceConstraintSchema).max(16).default([]),
  activities: z.array(tripPreferenceConstraintSchema).max(16).default([]),
  pace: z.object({
    value: tripPaceSchema,
    strength: constraintStrengthSchema,
  }).strict().optional(),
  climate: z.object({
    minDayTemperatureC: z.number().int().min(-50).max(60).optional(),
    maxDayTemperatureC: z.number().int().min(-50).max(60).optional(),
    precipitation: z.enum(["low", "any", "high"]).optional(),
    strength: constraintStrengthSchema,
  }).strict().refine(
    (value) => value.minDayTemperatureC === undefined ||
      value.maxDayTemperatureC === undefined ||
      value.minDayTemperatureC <= value.maxDayTemperatureC,
    { message: "Minimum climate temperature must not exceed maximum" },
  ).optional(),
  other: z.array(tripPreferenceConstraintSchema).max(12).default([]),
}).strict();
export type TripPreferences = z.infer<typeof tripPreferencesSchema>;

export const tripIntentContextSchema = z.object({
  summary: z.string().trim().min(1).max(240),
  understood: z.array(z.string().trim().min(1).max(120)).max(16),
  assumptions: z.array(z.string().trim().min(1).max(160)).max(16),
  unverified: z.array(z.string().trim().min(1).max(160)).max(16),
}).strict();
export type TripIntentContext = z.infer<typeof tripIntentContextSchema>;

const exactTimeSchema = z
  .object({
    mode: z.literal("exact"),
    startDate: z.iso.date(),
    endDate: z.iso.date(),
  })
  .refine((value) => value.endDate > value.startDate, {
    message: "endDate must be later than startDate",
    path: ["endDate"],
  });

const flexibleTimeSchema = z
  .object({
    mode: z.literal("flexible"),
    windowStart: z.iso.date(),
    windowEnd: z.iso.date(),
    nights: z.number().int().min(1).max(30),
  })
  .refine((value) => value.windowEnd >= value.windowStart, {
    message: "windowEnd must not be earlier than windowStart",
    path: ["windowEnd"],
  });

export const tripBriefSchema = z.object({
  preset: tripPresetSchema,
  originCityId: z.string().min(1),
  destinationCityId: z.string().min(1).optional(),
  travelers: travelersSchema,
  time: z.discriminatedUnion("mode", [exactTimeSchema, flexibleTimeSchema]),
  budgetRub: z.number().int().positive().max(10_000_000).optional(),
  interests: z.array(z.string().trim().min(1).max(60)).max(12).optional(),
  preferences: tripPreferencesSchema.optional(),
  intent: tripIntentContextSchema.optional(),
});
export type TripBrief = z.infer<typeof tripBriefSchema>;

export const tripBriefInterpretationRequestSchema = z.object({
  text: z.string().trim().min(1).max(4_000),
  defaultOriginCityId: z.string().trim().min(1),
}).strict();
export type TripBriefInterpretationRequest = z.infer<typeof tripBriefInterpretationRequestSchema>;

export const tripBriefInterpretationResponseSchema = z.object({
  brief: tripBriefSchema,
  interpretation: tripIntentContextSchema,
}).strict();
export type TripBriefInterpretationResponse = z.infer<typeof tripBriefInterpretationResponseSchema>;

export const citySchema = z.object({
  id: z.string(),
  name: z.string(),
  iata: z.string().length(3),
  latitude: z.number(),
  longitude: z.number(),
  tags: z.array(z.string()),
  accent: z.string(),
});
export type City = z.infer<typeof citySchema>;

export const priceSchema = z.object({
  amount: z.number().nonnegative(),
  currency: z.literal("RUB").default("RUB"),
  kind: z.enum(["live", "estimated"]),
  source: z.string(),
  checkedAt: z.string(),
  expiresAt: z.string().optional(),
});
export type Price = z.infer<typeof priceSchema>;

export const dataModeSchema = z.enum(["demo", "real"]);
export type DataMode = z.infer<typeof dataModeSchema>;

export const completenessSchema = z.enum(["complete", "partial", "failed"]);
export type Completeness = z.infer<typeof completenessSchema>;

export const sourceStatusSchema = z.object({
  component: z.enum(["profile", "flights", "hotel", "event", "nearby", "weather", "editorial"]),
  availability: z.enum(["available", "unavailable"]),
  required: z.boolean(),
  source: z.string(),
  checkedAt: z.string(),
  message: z.string().optional(),
});
export type SourceStatus = z.infer<typeof sourceStatusSchema>;

const httpsUrlSchema = z
  .string()
  .url()
  .refine((value) => /^https:\/\//iu.test(value), "Image URLs must use HTTPS");

export const imageAssetSchema = z.object({
  url: httpsUrlSchema,
  source: z.string().min(1),
  sourceUrl: httpsUrlSchema.optional(),
});
export type ImageAsset = z.infer<typeof imageAssetSchema>;

export const mapPointSchema = z.object({
  id: z.string(),
  type: z.enum(["hotel", "restaurant", "event", "poi"]),
  name: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  subtitle: z.string().optional(),
  image: imageAssetSchema.optional(),
});
export type MapPoint = z.infer<typeof mapPointSchema>;

export const flightOptionSchema = z.object({
  offerId: z.string().optional(),
  direction: z.enum(["outbound", "return"]),
  fromCode: z.string(),
  toCode: z.string(),
  date: z.string(),
  summary: z.string(),
  departureTime: z.string().optional(),
  arrivalTime: z.string().optional(),
  price: priceSchema,
  availability: sourceStatusSchema,
});
export type FlightOption = z.infer<typeof flightOptionSchema>;

export const hotelOptionSchema = z.object({
  hotelId: z.string(),
  name: z.string(),
  stars: z.number().int().min(0).max(5),
  address: z.string().optional(),
  rating: z.number().optional(),
  meal: z.string().optional(),
  image: imageAssetSchema.optional(),
  price: priceSchema,
  mapPoint: mapPointSchema,
  availability: sourceStatusSchema,
});
export type HotelOption = z.infer<typeof hotelOptionSchema>;

export const eventOptionSchema = z.object({
  eventId: z.string(),
  name: z.string(),
  kind: z.string(),
  genres: z.array(z.string()).optional(),
  ageRestriction: z.string().optional(),
  rating: z.number().optional(),
  dateTime: z.string().optional(),
  venue: z.string().optional(),
  address: z.string().optional(),
  image: imageAssetSchema.optional(),
  price: priceSchema.optional(),
  mapPoint: mapPointSchema.optional(),
  availability: sourceStatusSchema,
});
export type EventOption = z.infer<typeof eventOptionSchema>;

export const restaurantSchema = z.object({
  osmId: z.string(),
  name: z.string(),
  cuisine: z.string().optional(),
  openingHours: z.string().optional(),
  address: z.string().optional(),
  rating: z.number().min(0).max(5).optional(),
  reviewCount: z.number().int().nonnegative().optional(),
  averageCheck: z.string().optional(),
  attributes: z.array(z.string()).optional(),
  delivery: z.boolean().optional(),
  sourceUrl: httpsUrlSchema.optional(),
  distanceMeters: z.number().int().nonnegative(),
  matchReasons: z.array(z.string()),
  mapPoint: mapPointSchema,
  availability: sourceStatusSchema,
});
export type Restaurant = z.infer<typeof restaurantSchema>;

export const restaurantGroupSchema = z.object({
  id: z.string(),
  anchorType: z.enum(["hotel", "event"]),
  anchorId: z.string(),
  anchorName: z.string(),
  anchorMapPointId: z.string().optional(),
  availability: sourceStatusSchema,
  restaurants: z.array(restaurantSchema).max(3),
});
export type RestaurantGroup = z.infer<typeof restaurantGroupSchema>;

export const itineraryItemSchema = z.object({
  id: z.string(),
  day: z.number().int().positive(),
  time: z.string(),
  title: z.string(),
  description: z.string(),
  mapPointId: z.string().optional(),
});
export type ItineraryItem = z.infer<typeof itineraryItemSchema>;

const weatherTemperatureSchema = z.object({
  date: z.iso.date(),
  temperatureMinC: z.number(),
  temperatureMaxC: z.number(),
});

export const forecastWeatherDaySchema = weatherTemperatureSchema.extend({
  kind: z.literal("forecast"),
  precipitationProbabilityPct: z.number().int().min(0).max(100),
  weatherCode: z.number().int().nonnegative(),
});
export type ForecastWeatherDay = z.infer<typeof forecastWeatherDaySchema>;

export const climateWeatherDaySchema = weatherTemperatureSchema.extend({
  kind: z.literal("climate"),
  precipitationFrequencyPct: z.number().int().min(0).max(100),
  sampleSize: z.number().int().positive(),
});
export type ClimateWeatherDay = z.infer<typeof climateWeatherDaySchema>;

export const weatherDaySchema = z.discriminatedUnion("kind", [
  forecastWeatherDaySchema,
  climateWeatherDaySchema,
]);
export type WeatherDay = z.infer<typeof weatherDaySchema>;

export const weatherReportSchema = z.object({
  days: z.array(weatherDaySchema),
});
export type WeatherReport = z.infer<typeof weatherReportSchema>;

export const priceBreakdownItemSchema = z.object({
  label: z.string(),
  price: priceSchema,
});

export const tripProposalSchema = z.object({
  id: z.string(),
  runId: z.string(),
  title: z.string(),
  tagline: z.string(),
  tier: z.enum([
    // Legacy values remain readable for trips saved before cohort pricing.
    "economy",
    "balanced",
    "comfort",
    "cohort_floor",
    "cohort_typical",
    "cohort_ceiling",
    "within_budget",
    "closest_over_budget",
  ]),
  destination: citySchema,
  startDate: z.string(),
  endDate: z.string(),
  travelers: travelersSchema,
  flights: z.object({
    outbound: flightOptionSchema,
    return: flightOptionSchema,
  }),
  hotel: hotelOptionSchema,
  events: z.array(eventOptionSchema),
  restaurantGroups: z.array(restaurantGroupSchema),
  itinerary: z.array(itineraryItemSchema),
  weather: weatherReportSchema,
  mapPoints: z.array(mapPointSchema),
  priceBreakdown: z.array(priceBreakdownItemSchema),
  totalPrice: priceSchema,
  liveSubtotalRub: z.number().nonnegative(),
  estimatedSubtotalRub: z.number().nonnegative(),
  fitReasons: z.array(z.string()),
  warnings: z.array(z.string()),
  generatedAt: z.string(),
  dataMode: dataModeSchema,
  completeness: completenessSchema,
  sources: z.array(sourceStatusSchema),
});
export type TripProposal = z.infer<typeof tripProposalSchema>;

export const incomeCohortSchema = z.enum([
  "unknown",
  "up_to_50k",
  "50k_to_100k",
  "100k_to_200k",
  "200k_to_500k",
  "500k_to_1m",
  "1m_plus",
]);
export type IncomeCohort = z.infer<typeof incomeCohortSchema>;

export const spendingCategoryProfileSchema = z.object({
  name: z.string(),
  monthlySpendRub: z.number().nonnegative(),
  sharePct: z.number().min(0).max(100),
  averageCheckRub: z.number().nonnegative(),
  transactionCount: z.number().int().nonnegative(),
});
export type SpendingCategoryProfile = z.infer<typeof spendingCategoryProfileSchema>;

export const diningProfileSchema = z.object({
  averageCheckRub: z.number().nonnegative(),
  medianCheckRub: z.number().nonnegative(),
  preferredCuisines: z.array(z.string()),
  preferredVenueTypes: z.array(z.string()),
});
export type DiningProfile = z.infer<typeof diningProfileSchema>;

export const shoppingProfileSchema = z.object({
  averageCheckRub: z.number().nonnegative(),
  medianCheckRub: z.number().nonnegative(),
  preferredStoreTypes: z.array(z.string()),
});
export type ShoppingProfile = z.infer<typeof shoppingProfileSchema>;

export const rankedPreferenceSchema = z.object({
  value: z.string(),
  evidenceCount: z.number().int().nonnegative(),
  lastObservedAt: z.string().optional(),
});
export type RankedPreference = z.infer<typeof rankedPreferenceSchema>;

export const audienceProfileSchema = z.object({
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
  source: z.enum(["bank", "unknown"]),
});
export type AudienceProfile = z.infer<typeof audienceProfileSchema>;

export const eventBehaviorProfileSchema = z.object({
  purchaseCount: z.number().int().nonnegative(),
  kindAffinities: z.array(rankedPreferenceSchema),
  genreAffinities: z.array(rankedPreferenceSchema),
  venueAffinities: z.array(rankedPreferenceSchema),
  preferredWeekdays: z.array(rankedPreferenceSchema),
  preferredDayParts: z.array(rankedPreferenceSchema),
  averageOrderRub: z.number().nonnegative(),
  medianOrderRub: z.number().nonnegative(),
  averagePartySize: z.number().nonnegative(),
});
export type EventBehaviorProfile = z.infer<typeof eventBehaviorProfileSchema>;

export const leisureSpendingProfileSchema = z.object({
  transactionCount: z.number().int().nonnegative(),
  monthlySpendRub: z.number().nonnegative(),
  averageCheckRub: z.number().nonnegative(),
  medianCheckRub: z.number().nonnegative(),
  preferredWeekdays: z.array(rankedPreferenceSchema),
  preferredDayParts: z.array(rankedPreferenceSchema),
});
export type LeisureSpendingProfile = z.infer<typeof leisureSpendingProfileSchema>;

export const travelBehaviorProfileSchema = z.object({
  orderCount: z.number().int().nonnegative(),
  flightOrderCount: z.number().int().nonnegative(),
  trainOrderCount: z.number().int().nonnegative(),
  hotelOrderCount: z.number().int().nonnegative(),
  averageOrderRub: z.number().nonnegative(),
  preferredHotelStars: z.array(rankedPreferenceSchema),
  preferredMealTypes: z.array(rankedPreferenceSchema),
  averageHotelNights: z.number().nonnegative(),
  averageHotelGuests: z.number().nonnegative(),
});
export type TravelBehaviorProfile = z.infer<typeof travelBehaviorProfileSchema>;

export const behavioralInsightsSchema = z.object({
  audience: audienceProfileSchema,
  events: eventBehaviorProfileSchema,
  leisureSpending: leisureSpendingProfileSchema,
  travel: travelBehaviorProfileSchema,
});
export type BehavioralInsights = z.infer<typeof behavioralInsightsSchema>;

export const preferenceProfileSchema = z.object({
  profileVersion: z.number().int().positive().optional(),
  generatedAt: z.string(),
  source: z.enum(["bank", "fallback"]),
  analysisWindowDays: z.number().int().positive(),
  transactionCount: z.number().int().nonnegative(),
  estimatedMonthlyIncomeRub: z.number().nonnegative(),
  incomeCohort: incomeCohortSchema,
  incomeConfidence: z.enum(["unavailable", "low", "medium", "high"]),
  monthlySpendRub: z.number().nonnegative(),
  diningSpendRub: z.number().nonnegative(),
  weekendAverageDailySpendRub: z.number().nonnegative(),
  weekdayAverageDailySpendRub: z.number().nonnegative(),
  weekendSpendSharePct: z.number().min(0).max(100),
  averageCheckRub: z.number().nonnegative(),
  medianCheckRub: z.number().nonnegative(),
  categoryBreakdown: z.array(spendingCategoryProfileSchema),
  diningProfile: diningProfileSchema,
  shoppingProfile: shoppingProfileSchema,
  preferredCategories: z.array(z.string()),
  favoriteMerchants: z.array(z.string()),
  favoriteDiningMerchants: z.array(z.string()),
  eventInterests: z.array(z.string()),
  previousDestinations: z.array(z.string()),
  behavioralInsights: behavioralInsightsSchema.optional(),
  llmSummary: z.string(),
  notes: z.array(z.string()),
});
export type PreferenceProfile = z.infer<typeof preferenceProfileSchema>;

export const jobStatusSchema = z.enum(["queued", "running", "completed", "failed", "interrupted"]);
export type JobStatus = z.infer<typeof jobStatusSchema>;

export const jobEventTypeSchema = z.enum([
  "job.started",
  "profile.ready",
  "shortlist.ready",
  "candidate.progress",
  "trip.partial",
  "trip.ready",
  "job.completed",
  "job.failed",
]);
export type JobEventType = z.infer<typeof jobEventTypeSchema>;

export type JobEvent = {
  id: number;
  jobId: string;
  type: JobEventType;
  data: Record<string, unknown>;
  createdAt: string;
};

export type TripRunSnapshot = {
  id: string;
  status: JobStatus;
  brief: TripBrief;
  profile?: PreferenceProfile;
  trips: TripProposal[];
  warnings: string[];
  dataMode: DataMode;
  completeness: Completeness;
  sources: SourceStatus[];
  createdAt: string;
  updatedAt: string;
};

export type TripRevision = {
  id: string;
  tripId: string;
  revision: number;
  brief: TripBrief;
  proposal: TripProposal;
  changeSummary?: string[];
  createdAt: string;
};

export type ChatMessage = {
  id: string;
  tripId: string;
  role: "user" | "assistant";
  content: string;
  revisionId?: string;
  createdAt: string;
};

export const tripMessageSchema = z.object({
  text: z.string().trim().min(1).max(4_000),
  baseRevisionId: z.string().min(1),
});

export type TripMessageInput = z.infer<typeof tripMessageSchema>;

export type TripDetail = {
  id: string;
  runId: string;
  preparationStatus: "preparing" | "ready" | "failed";
  latestRevision: TripRevision;
  revisionCount: number;
  createdAt: string;
};

export type AsyncJobAccepted = {
  jobId: string;
  runId?: string;
  tripId?: string;
  messageId?: string;
};

export type SystemReadiness = {
  status: "ready" | "degraded";
  dataMode: DataMode;
  checkedAt: string;
  sources: Array<{
    id: "mcp" | "bankSession" | "llmProxy" | "openai" | "2gis" | "overpass" | "nominatim" | "weather";
    status: "ready" | "not_configured" | "disconnected";
    required: boolean;
    message: string;
  }>;
};
