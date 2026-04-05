import { useState, useCallback, useEffect } from "react";

interface Conversation {
  id: string;
  title: string | null;
  updated_at: string | null;
}

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: { document: string; excerpt: string; char_start: number; char_end: number }[];
}

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) setConversations(await res.json());
    } catch { /* ignore */ }
    finally { setLoadingList(false); }
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  const createConversation = useCallback(async (title?: string): Promise<string> => {
    const res = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to create conversation" }));
      throw new Error(err.detail || "Failed to create conversation");
    }
    const data = await res.json();
    setActiveId(data.id);
    setMessages([]);
    await fetchConversations();
    return data.id;
  }, [fetchConversations]);

  const loadConversation = useCallback(async (id: string) => {
    const res = await fetch(`/api/conversations/${id}`);
    if (res.ok) {
      const data = await res.json();
      setActiveId(id);
      setMessages(data.messages || []);
    }
  }, []);

  const deleteConversation = useCallback(async (id: string) => {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
    await fetchConversations();
  }, [activeId, fetchConversations]);

  const newChat = useCallback(() => {
    setActiveId(null);
    setMessages([]);
  }, []);

  return {
    conversations,
    activeId,
    messages,
    setMessages,
    loadingList,
    createConversation,
    loadConversation,
    deleteConversation,
    newChat,
  };
}
