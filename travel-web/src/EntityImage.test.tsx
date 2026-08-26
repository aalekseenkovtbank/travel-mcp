import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EntityImage } from "./EntityImage";

afterEach(cleanup);

describe("EntityImage", () => {
  it("renders no empty area without an image and removes a broken image", () => {
    const { container, rerender } = render(<EntityImage alt="Нет фото" />);
    expect(container.querySelector("figure")).toBeNull();

    rerender(
      <EntityImage
        alt="Отель"
        image={{ url: "https://cdn.tbank.ru/broken.jpg", source: "T-Bank Hotels" }}
      />,
    );
    const image = screen.getByRole("img", { name: "Отель" });
    expect(image).toHaveAttribute("loading", "lazy");
    fireEvent.error(image);
    expect(container.querySelector("figure")).toBeNull();
  });
});
