import { useEffect, useState } from "react";
import type { ImageAsset } from "@travel-growth-inspiration/contracts";

type EntityImageProps = {
  image?: ImageAsset;
  alt: string;
  className?: string;
  eager?: boolean;
};

export function EntityImage({ image, alt, className = "", eager = false }: EntityImageProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [image?.url]);

  if (!image || failed) return null;

  return (
    <figure className={`entity-image ${className}`.trim()}>
      <img
        src={image.url}
        alt={alt}
        loading={eager ? "eager" : "lazy"}
        decoding="async"
        onError={() => setFailed(true)}
      />
      {image.sourceUrl ? (
        <figcaption>
          <a href={image.sourceUrl} target="_blank" rel="noreferrer">Фото: {image.source}</a>
        </figcaption>
      ) : null}
    </figure>
  );
}
