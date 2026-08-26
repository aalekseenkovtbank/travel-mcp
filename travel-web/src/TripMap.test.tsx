import type { ReactNode } from "react";
import type { MapPoint } from "@travel-growth-inspiration/contracts";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}));

import { TripMap } from "./TripMap";

afterEach(cleanup);

describe("TripMap", () => {
  it("shows a point photo and its Wikimedia source in the popup", () => {
    const points: MapPoint[] = [{
      id: "poi-1",
      type: "poi",
      name: "Главный музей",
      latitude: 55.75,
      longitude: 37.61,
      image: {
        url: "https://upload.wikimedia.org/museum.jpg",
        source: "Wikimedia Commons",
        sourceUrl: "https://commons.wikimedia.org/wiki/File:Museum.jpg",
      },
    }];
    render(<TripMap points={points} />);
    expect(screen.getByRole("img", { name: "Главный музей" }).closest("figure")).toHaveClass("map-popup-photo");
    expect(screen.getByRole("link", { name: "Фото: Wikimedia Commons" })).toHaveAttribute(
      "href",
      points[0]!.image!.sourceUrl,
    );
  });
});
