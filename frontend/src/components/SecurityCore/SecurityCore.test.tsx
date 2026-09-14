import { describe, it, expect, vi } from "vitest";
import React from "react";
import { renderToString } from "react-dom/server";
import { SecurityCore } from "./SecurityCore";
import { SecurityCoreState, SecurityCoreSize } from "./SecurityCore.types";
import { coreColors } from "./SecurityCore.variants";

describe("SecurityCore Component — Phase 1 Specification", () => {
  it("renders with default props (state: idle, size: section)", () => {
    const html = renderToString(<SecurityCore state="idle" />);
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Security aperture status: idle"');
    expect(html).toContain("width:64px");
    expect(html).toContain("height:52px");
  });

  const sizes: { size: SecurityCoreSize; width: string; height: string }[] = [
    { size: "hero", width: "width:120px", height: "height:96px" },
    { size: "section", width: "width:64px", height: "height:52px" },
    { size: "nav", width: "width:28px", height: "height:22px" },
    { size: "inline", width: "width:18px", height: "height:14px" },
  ];

  sizes.forEach(({ size, width, height }) => {
    it(`renders correct proportional bounding box for size="${size}"`, () => {
      const html = renderToString(<SecurityCore state="idle" size={size} />);
      expect(html).toContain(width);
      expect(html).toContain(height);
    });
  });

  const states: SecurityCoreState[] = [
    "idle",
    "observing",
    "analyzing",
    "high-risk",
    "investigating",
    "secure",
  ];

  states.forEach((st) => {
    it(`renders valid SVG geometry for state="${st}"`, () => {
      const html = renderToString(<SecurityCore state={st} />);
      expect(html).toContain(`aria-label="Security aperture status: ${st}"`);
      expect(html).toContain('viewBox="0 0 120 96"');
      // Verify central core is colored
      expect(html).toContain(coreColors[st]);
    });
  });

  it("omits technical tick marks on nav and inline sizes to avoid visual noise", () => {
    const heroHtml = renderToString(<SecurityCore state="idle" size="hero" />);
    const navHtml = renderToString(<SecurityCore state="idle" size="nav" />);
    const inlineHtml = renderToString(<SecurityCore state="idle" size="inline" />);

    // Tick lines (x1="60" y1="18") present on hero, absent on nav and inline
    expect(heroHtml).toContain('x1="60" y1="18"');
    expect(navHtml).not.toContain('x1="60" y1="18"');
    expect(inlineHtml).not.toContain('x1="60" y1="18"');
  });
});
