import { useTranslation } from "react-i18next";

interface Conversation {
  id: string;
  title: string | null;
  updated_at: string | null;
}

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

export default function ConversationSidebar({ conversations, activeId, onSelect, onDelete, onNewChat }: Props) {
  const { t } = useTranslation("common");

  return (
    <div className="flex flex-col h-full" style={{ borderRight: "1px solid var(--color-border)" }}>
      <button
        onClick={onNewChat}
        className="m-2 px-3 py-2 rounded-lg text-sm font-medium"
        style={{ background: "var(--color-primary)", color: "white" }}
      >
        + {t("newChat", "New Chat")}
      </button>
      <div className="flex-1 overflow-y-auto">
        {conversations.map((c) => (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            className="flex items-center justify-between px-3 py-2 mx-1 rounded cursor-pointer text-sm"
            style={{
              background: c.id === activeId ? "var(--bg-active)" : "transparent",
              color: "var(--color-text)",
            }}
          >
            <span className="truncate flex-1">
              {c.title || t("untitledChat", "Untitled chat")}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
              className="ml-2 text-xs opacity-50 hover:opacity-100"
              title={t("delete", "Delete")}
            >
              x
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
