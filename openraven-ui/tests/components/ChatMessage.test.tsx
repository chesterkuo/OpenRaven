/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect } from "bun:test";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import ChatMessage from "../../src/components/ChatMessage";

describe("ChatMessage", () => {
  describe("user messages", () => {
    it("renders user message content", () => {
      render(<ChatMessage role="user" content="Hello, world!" />);
      expect(screen.getByText("Hello, world!")).toBeDefined();
    });

    it("applies right-alignment for user messages", () => {
      const { container } = render(<ChatMessage role="user" content="Hi" />);
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper.className).toContain("justify-end");
    });

    it("applies gradient background for user messages", () => {
      const { container } = render(<ChatMessage role="user" content="Hi" />);
      const bubble = container.querySelector("[style]") as HTMLElement;
      expect(bubble?.style.background).toContain("linear-gradient");
    });

    it("does not parse source citations in user messages", () => {
      const { container } = render(
        <ChatMessage role="user" content="[Source: document.md]" />
      );
      // Should render as plain text, not as a SourceCitation span
      expect(screen.getByText("[Source: document.md]")).toBeDefined();
      const citation = container.querySelector("span.cursor-help");
      expect(citation).toBeNull();
    });
  });

  describe("assistant messages", () => {
    it("renders assistant message content", () => {
      render(<ChatMessage role="assistant" content="I can help you with that." />);
      expect(screen.getByText("I can help you with that.")).toBeDefined();
    });

    it("applies left-alignment for assistant messages", () => {
      const { container } = render(<ChatMessage role="assistant" content="Hi" />);
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper.className).toContain("justify-start");
    });

    it("applies surface background for assistant messages", () => {
      const { container } = render(<ChatMessage role="assistant" content="Hi" />);
      const bubble = container.querySelector("[style]") as HTMLElement;
      expect(bubble?.style.background).toContain("var(--bg-surface)");
    });

    it("parses [Source: document.md] into a SourceCitation component", () => {
      const { container } = render(
        <ChatMessage role="assistant" content="See [Source: document.md] for details." />
      );
      // SourceCitation renders as a span with the document name
      const citation = container.querySelector("span.cursor-help");
      expect(citation).not.toBeNull();
      expect(citation?.textContent).toContain("document.md");
    });

    it("parses [Source: document.md:100-200] with char range into SourceCitation", () => {
      const { container } = render(
        <ChatMessage role="assistant" content="Details at [Source: report.pdf:100-200]." />
      );
      const citation = container.querySelector("span.cursor-help");
      expect(citation).not.toBeNull();
      expect(citation?.textContent).toContain("report.pdf");
      // The title attribute should include the char range
      const titleAttr = citation?.getAttribute("title");
      expect(titleAttr).toContain("chars 100-200");
    });

    it("renders surrounding text alongside source citations", () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Before text [Source: file.md] after text"
        />
      );
      // Check that the surrounding text is rendered (whitespace-exact spans)
      expect(container.textContent).toContain("Before text");
      expect(container.textContent).toContain("after text");
    });

    it("handles multiple source citations in one message", () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="See [Source: first.md] and [Source: second.md:10-20]."
        />
      );
      // Citation spans have cursor-help class from SourceCitation
      const citations = container.querySelectorAll("span.cursor-help");
      expect(citations.length).toBe(2);
      expect(citations[0].textContent).toContain("first.md");
      expect(citations[1].textContent).toContain("second.md");
    });

    it("renders plain assistant content without citations unchanged", () => {
      render(<ChatMessage role="assistant" content="No citations here." />);
      expect(screen.getByText("No citations here.")).toBeDefined();
    });
  });
});
