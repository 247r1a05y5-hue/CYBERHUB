import { describe, it, expect } from "vitest";
import React from "react";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { CinematicScrollVideo } from "./CinematicScrollVideo";

describe("CinematicScrollVideo Component", () => {
  it("renders the 400vh tall scroll section and sticky frame container", () => {
    const html = renderToString(
      <MemoryRouter>
        <CinematicScrollVideo />
      </MemoryRouter>
    );

    expect(html).toContain('class="cinematic-scroll-section"');
    expect(html).toContain('class="cinematic-sticky-frame"');
  });

  it("renders video element with muted, playsinline, preload='auto' and without autoplay or controls", () => {
    const html = renderToString(
      <MemoryRouter>
        <CinematicScrollVideo videoSrc="/assets/cyberhub-hero.mp4" />
      </MemoryRouter>
    );

    expect(html).toContain('src="/assets/cyberhub-hero.mp4"');
    expect(html).toContain("playsinline");
    expect(html).toContain('preload="auto"');
    expect(html).not.toContain("autoplay");
    expect(html).not.toContain("controls");
    expect(html).not.toContain("loop");
  });

  it("renders brand-level hero copy in separate DOM overlay", () => {
    const html = renderToString(
      <MemoryRouter>
        <CinematicScrollVideo />
      </MemoryRouter>
    );

    expect(html).toContain("Digital Exposure");
    expect(html).toContain("Investigation");
    expect(html).toContain("Understand where your digital presence appears across public sources.");
    expect(html).toContain("Start Investigation");
  });

  it("renders timeline scrub progress indicator", () => {
    const html = renderToString(
      <MemoryRouter>
        <CinematicScrollVideo />
      </MemoryRouter>
    );

    expect(html).toContain("cinematic-timeline-indicator");
    expect(html).toContain("Scroll to Scrub Timeline");
  });
});
