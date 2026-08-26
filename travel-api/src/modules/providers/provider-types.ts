import type { City, DataMode, ImageAsset, PreferenceProfile, TripBrief } from "@travel-growth-inspiration/contracts";

export type ProviderResult<T> = {
  data: T;
  warnings: string[];
  isFallback: boolean;
  source: string;
  checkedAt: string;
};

export type FlightInventoryItem = {
  offerId?: string;
  summary: string;
  priceRub: number;
  departureTime?: string;
  arrivalTime?: string;
  source: string;
  live: boolean;
  checkedAt: string;
};

export type HotelInventoryItem = {
  hotelId: string;
  name: string;
  stars: number;
  priceRub: number;
  address?: string;
  rating?: number;
  meal?: string;
  latitude?: number;
  longitude?: number;
  image?: ImageAsset;
  source: string;
  live: boolean;
  checkedAt: string;
};

export type EventInventoryItem = {
  eventId: string;
  name: string;
  kind: string;
  genres?: string[];
  ageRestriction?: string;
  rating?: number;
  dateTime?: string;
  venue?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  priceRub?: number;
  image?: ImageAsset;
  source: string;
  checkedAt: string;
};

export type NearbyPlace = {
  osmId: string;
  type: "restaurant" | "poi";
  name: string;
  latitude: number;
  longitude: number;
  cuisine?: string;
  category?: string;
  openingHours?: string;
  address?: string;
  rating?: number;
  reviewCount?: number;
  averageCheck?: string;
  attributes?: string[];
  delivery?: boolean;
  sourceUrl?: string;
  image?: ImageAsset;
  distanceMeters: number;
  source: string;
  checkedAt: string;
};

export type NearbyAnchor = {
  id: string;
  type: "hotel" | "event";
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
};

export type NearbySearchOptions = {
  includePointsOfInterest?: boolean;
  placeKinds?: Array<"culture" | "nature" | "nightlife">;
};

export interface NearbyPlacesProvider {
  nearby(
    city: City,
    anchor: NearbyAnchor,
    options?: NearbySearchOptions,
  ): Promise<ProviderResult<NearbyPlace[]>>;
}

export type DateWindow = {
  startDate: string;
  endDate: string;
};

export interface PlannerDataProvider {
  readonly dataMode: DataMode;
  profile(): Promise<ProviderResult<PreferenceProfile>>;
  flights(
    from: City,
    to: City,
    date: string,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<FlightInventoryItem[]>>;
  hotels(
    city: City,
    window: DateWindow,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<HotelInventoryItem[]>>;
  events(
    city: City,
    window: DateWindow,
    interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>>;
  nearby(
    city: City,
    anchor: NearbyAnchor,
    options?: NearbySearchOptions,
  ): Promise<ProviderResult<NearbyPlace[]>>;
  close(): Promise<void>;
}
