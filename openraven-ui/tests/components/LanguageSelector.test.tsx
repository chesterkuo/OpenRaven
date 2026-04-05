/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect, afterEach } from "bun:test";
import { render, cleanup } from "@testing-library/react";
import "@testing-library/jest-dom";
import "../../tests/i18n-setup";
import { LanguageSelector } from "../../src/components/LanguageSelector";

afterEach(cleanup);

describe("LanguageSelector", () => {
  it("renders a select element with 12 locale options", () => {
    const { container } = render(<LanguageSelector />);
    const select = container.querySelector("select")!;
    expect(select).toBeDefined();
    const options = select.querySelectorAll("option");
    expect(options.length).toBe(12);
  });

  it("shows native language names", () => {
    const { container } = render(<LanguageSelector />);
    const text = container.textContent!;
    expect(text).toContain("繁體中文");
    expect(text).toContain("日本語");
    expect(text).toContain("Русский");
  });

  it("selects the current i18n language", () => {
    const { container } = render(<LanguageSelector />);
    const select = container.querySelector("select") as HTMLSelectElement;
    expect(select.value).toBe("en");
  });
});
