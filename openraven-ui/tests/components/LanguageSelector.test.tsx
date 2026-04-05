/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect } from "bun:test";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import "../../tests/i18n-setup";
import { LanguageSelector } from "../../src/components/LanguageSelector";

describe("LanguageSelector", () => {
  it("renders a select element with 12 locale options", () => {
    render(<LanguageSelector />);
    const select = screen.getByRole("combobox");
    expect(select).toBeDefined();
    const options = select.querySelectorAll("option");
    expect(options.length).toBe(12);
  });

  it("shows native language names", () => {
    render(<LanguageSelector />);
    expect(screen.getByText("繁體中文")).toBeDefined();
    expect(screen.getByText("日本語")).toBeDefined();
    expect(screen.getByText("Русский")).toBeDefined();
  });

  it("selects the current i18n language", () => {
    render(<LanguageSelector />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("en");
  });
});
