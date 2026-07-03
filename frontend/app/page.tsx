"use client";

import type { ChangeEvent, KeyboardEvent, PointerEvent as ReactPointerEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  MessageSquare,
  User,
  Link2,
  Route,
  Zap,
  Database,
  Clock,
  Settings,
  BarChart3,
  FileText,
  Inbox,
  Wrench,
  Heart,
  Monitor,
  AlertTriangle,
  Download,
  RefreshCw,
  LogOut,
  Send,
  Keyboard,
  Bell,
  Code,
  Sidebar,
  Sun,
  Moon,
  Plus,
  Trash2
} from "lucide-react";

type AgentResult = {
  agent: string;
  output: string;
  metadata: Record<string, unknown>;
};

type ChatResponse = {
  conversation_id: string;
  route: string;
  answer: string;
  agents_used: string[];
  agent_results: AgentResult[];
  cached: boolean;
  context_messages?: number;
};

type Message = {
  role: "user" | "assistant";
  content: string;
};

type AuthMode = "login" | "register";

type ConversationSession = {
  id: string;
  conversation_id: string;
  title: string;
  file_ids?: string[];
  created_at: string;
  last_active_at: string;
};

type AuthResponse = {
  access_token: string;
  token_type: string;
  email: string;
};

type HealthResponse = {
  status: string;
  app: string;
  environment: string;
  llm_provider: string;
  redis_connected: boolean;
  supabase_connected: boolean;
};

type StatusTone = "online" | "offline" | "neutral";

type ActivityLog = {
  id: string;
  time: string;
  level: "INFO" | "WARN" | "ERROR";
  message: string;
};

type ViewMode = "desktop" | "tablet" | "mobile";

type UserFile = {
  id: string;
  file_name: string;
  file_type: string;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  file_size?: number;
  suggested_questions?: string[];
  conversation_id?: string;
  created_at: string;
  error_message?: string;
};

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

const TOKEN_STORAGE_KEY = "multi-agent-starter-token";
const EMAIL_STORAGE_KEY = "multi-agent-starter-email";

const quickPrompts = [
  "How does LangGraph work?",
  "Explain Redis caching",
  "What is Langfuse observability?",
];

const MAX_ACTIVITY_LOGS = 28;

export default function Home() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "✓ Ready. Test summary, search & multi-agent flows.",
    },
  ]);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [loggedInEmail, setLoggedInEmail] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState("Session offline.");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [files, setFiles] = useState<UserFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [conversations, setConversations] = useState<ConversationSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState("");
  const [lastHealthCheck, setLastHealthCheck] = useState("");
  const [clock, setClock] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("desktop");
  const [leftPanelWidth, setLeftPanelWidth] = useState(260);
  const [rightPanelWidth, setRightPanelWidth] = useState(340);
  const [hideLeftPanel, setHideLeftPanel] = useState(false);
  const [hideRightPanel, setHideRightPanel] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const profileMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!showProfileMenu) return;
    function handleClickOutside(event: Event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [showProfileMenu]);
  
  const resizeStateRef = useRef<{
    target: "left" | "right" | null;
    startX: number;
    startWidth: number;
  }>({
    target: null,
    startX: 0,
    startWidth: 0,
  });

  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);

  useEffect(() => {
    const storedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? "";
    const storedEmail = window.localStorage.getItem(EMAIL_STORAGE_KEY) ?? "";
    if (storedToken) {
      setToken(storedToken);
      setLoggedInEmail(storedEmail);
      setAuthMessage(`Session live for ${storedEmail || "saved user"}.`);
      appendLog("INFO", `Recovered saved session for ${storedEmail || "saved user"}.`);
    } else {
      appendLog("WARN", "No saved session detected. Login required.");
    }
  }, []);

  useEffect(() => {
    const updateClock = () => {
      setClock(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };

    updateClock();
    const interval = window.setInterval(updateClock, 1000);

    return () => window.clearInterval(interval);
  }, []);

  // Update theme class on document body
  useEffect(() => {
    if (typeof window !== "undefined") {
      document.body.classList.remove("light-mode", "dark-mode");
      document.body.classList.add(`${theme}-mode`);
    }
  }, [theme]);

  // Scroll to bottom when messages or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const updateViewMode = () => {
      const width = window.innerWidth;
      if (width <= 640) {
        setViewMode("mobile");
      } else if (width <= 1180) {
        setViewMode("tablet");
      } else {
        setViewMode("desktop");
      }
    };

    updateViewMode();
    window.addEventListener("resize", updateViewMode);

    return () => window.removeEventListener("resize", updateViewMode);
  }, []);

  useEffect(() => {
    void fetchHealth("Initial health probe");
  }, []);

  // Fetch conversations when token changes
  useEffect(() => {
    if (token) {
      void fetchConversations();
    } else {
      setConversations([]);
      setActiveSessionId(null);
    }
  }, [token]);

  // Fetch user files when token changes
  useEffect(() => {
    if (token) {
      void fetchUserFiles();
    } else {
      setFiles([]);
    }
  }, [token]);

  // Smart polling for processing files
  useEffect(() => {
    if (!token || files.length === 0) return;

    const hasProcessing = files.some((f) => f.status === "processing");
    if (!hasProcessing) return;

    const interval = window.setInterval(() => {
      void fetchUserFiles();
    }, 3000);

    return () => window.clearInterval(interval);
  }, [files, token]);

  // Auto-select files by default when they are loaded or added
  useEffect(() => {
    if (files.length > 0) {
      setSelectedFileIds((prev) => {
        const newIds = [...prev];
        files.forEach((file) => {
          if (!newIds.includes(file.id) && file.status !== "failed") {
            newIds.push(file.id);
          }
        });
        return newIds.filter((id) => files.some((f) => f.id === id));
      });
    } else {
      setSelectedFileIds([]);
    }
  }, [files]);

  const historyPayload = useMemo(
    () =>
      messages.map((message: Message) => ({
        role: message.role,
        content: message.content,
      })),
    [messages]
  );

  // Calculate dynamic quick prompts based on selected/active documents
  const activeQuickPrompts = useMemo(() => {
    const selectedFiles = files.filter(
      (f) => selectedFileIds.includes(f.id) && f.suggested_questions && f.suggested_questions.length > 0
    );
    
    if (selectedFiles.length > 0) {
      const allQuestions = selectedFiles.flatMap((f) => f.suggested_questions || []);
      const uniqueQuestions = Array.from(new Set(allQuestions));
      if (uniqueQuestions.length > 0) {
        return uniqueQuestions.slice(0, 4);
      }
    }
    return quickPrompts;
  }, [files, selectedFileIds]);

  const hasUploadedDocs = useMemo(() => {
    return files.some(
      (f) =>
        f.conversation_id === activeSessionId ||
        selectedFileIds.includes(f.id) ||
        f.id.startsWith("temp-")
    );
  }, [files, activeSessionId, selectedFileIds]);

  const isAuthenticated = Boolean(token);
  const messageCount = Math.max(messages.length - 1, 0);
  const isMobile = viewMode === "mobile";
  const isTablet = viewMode === "tablet";
  const supportsResizablePanels = !isTablet && !isMobile;

  useEffect(() => {
    if (!supportsResizablePanels) {
      return;
    }

    const onPointerMove = (event: PointerEvent) => {
      const activeResize = resizeStateRef.current;
      if (!activeResize.target) {
        return;
      }

      if (activeResize.target === "left") {
        const nextWidth = Math.min(Math.max(activeResize.startWidth + (event.clientX - activeResize.startX), 220), 360);
        setLeftPanelWidth(nextWidth);
        return;
      }

      const nextWidth = Math.min(Math.max(activeResize.startWidth - (event.clientX - activeResize.startX), 280), 460);
      setRightPanelWidth(nextWidth);
    };

    const stopResize = () => {
      resizeStateRef.current = {
        target: null,
        startX: 0,
        startWidth: 0,
      };
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopResize);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopResize);
    };
  }, [supportsResizablePanels]);

  function appendLog(level: ActivityLog["level"], message: string) {
    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    const logEntry: ActivityLog = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      time,
      level,
      message,
    };

    setActivityLogs((current) => [logEntry, ...current].slice(0, MAX_ACTIVITY_LOGS));
  }

  async function fetchHealth(reason: string) {
    setHealthLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/health`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Health endpoint unavailable.");
      }

      const data: HealthResponse = await response.json();
      setHealth(data);
      setHealthError("");
      const checkedAt = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      setLastHealthCheck(checkedAt);
      appendLog(
        "INFO",
        `${reason}: backend=${data.status}, redis=${data.redis_connected ? "online" : "offline"}, supabase=${data.supabase_connected ? "online" : "offline"}, provider=${data.llm_provider}.`
      );
    } catch (error) {
      setHealth(null);
      const nextError =
        error instanceof Error ? error.message : "Failed to load backend health.";
      setHealthError(nextError);
      setLastHealthCheck(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
      appendLog("ERROR", `${reason}: ${nextError}`);
    } finally {
      setHealthLoading(false);
    }
  }

  function startResize(
    target: "left" | "right",
    event: ReactPointerEvent<HTMLDivElement>
  ) {
    if (!supportsResizablePanels) {
      return;
    }

    resizeStateRef.current = {
      target,
      startX: event.clientX,
      startWidth: target === "left" ? leftPanelWidth : rightPanelWidth,
    };
  }

  function persistSession(nextToken: string, nextEmail: string) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
    window.localStorage.setItem(EMAIL_STORAGE_KEY, nextEmail);
    setToken(nextToken);
    setLoggedInEmail(nextEmail);
  }

  function logout() {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(EMAIL_STORAGE_KEY);
    setToken("");
    setLoggedInEmail("");
    setConversationId(null);
    setLastResponse(null);
    setInput("");
    setAuthMessage("Session offline.");
    setMessages([
      {
        role: "assistant",
        content: "Session cleared. Login again to reopen the chat workspace.",
      },
    ]);
    appendLog("WARN", "User logged out and local session storage was cleared.");
  }

  function handleAuthError(error: unknown, response?: Response): boolean {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const isTokenExpired =
      errorMessage.includes("Invalid token") ||
      errorMessage.includes("Signature has expired") ||
      errorMessage.includes("Token has expired") ||
      (response && response.status === 401);
    
    if (isTokenExpired) {
      logout();
      appendLog("ERROR", "Session expired. Please login again.");
      return true;
    }
    return false;
  }

  async function handleAuth() {
    if (!email.trim() || !password.trim() || authLoading) {
      appendLog("WARN", "Auth attempt blocked because email or password is empty.");
      return;
    }

    setAuthLoading(true);
    setAuthMessage(authMode === "login" ? "Authorizing..." : "Creating identity...");
    appendLog(
      "INFO",
      authMode === "login"
        ? `Login requested for ${email.trim()}.`
        : `Registration requested for ${email.trim()}.`
    );

    try {
      if (authMode === "register") {
        const registerResponse = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            password,
          }),
        });

        if (!registerResponse.ok) {
          const errorText = await registerResponse.text();
          throw new Error(errorText || "Registration failed.");
        }

        appendLog("INFO", `Registration completed for ${email.trim()}.`);
      }

      const loginResponse = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      if (!loginResponse.ok) {
        const errorText = await loginResponse.text();
        throw new Error(errorText || "Login failed.");
      }

      const data: AuthResponse = await loginResponse.json();
      persistSession(data.access_token, data.email);
      setAuthMessage(`Session live for ${data.email}.`);
      setPassword("");
      appendLog("INFO", `Authentication successful for ${data.email}.`);
    } catch (error) {
      const nextMessage =
        error instanceof Error ? error.message : "Authentication request failed.";
      setAuthMessage(nextMessage);
      appendLog("ERROR", `Authentication failure: ${nextMessage}`);
    } finally {
      setAuthLoading(false);
    }
  }

  async function fetchConversations() {
    if (!token) return;
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/conversations`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) return;
        throw new Error(errorText || "Failed to fetch conversations.");
      }
      const data = await response.json();
      setConversations(data);
    } catch (error) {
      appendLog("ERROR", `Fetch conversations failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function loadConversation(session: ConversationSession) {
    if (!token) return;
    setActiveSessionId(session.id);
    setConversationId(session.conversation_id);
    
    // Restore associated document check-states
    if (session.file_ids && Array.isArray(session.file_ids)) {
      setSelectedFileIds(session.file_ids);
    } else {
      setSelectedFileIds([]);
    }
    
    appendLog("INFO", `Loading conversation: ${session.title}`);
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/conversations/${session.id}/messages`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) return;
        throw new Error(errorText || "Failed to load messages.");
      }
      const data = await response.json();
      const loadedMessages: Message[] = data.messages.map((m: { role: string; content: string }) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      if (loadedMessages.length > 0) {
        setMessages(loadedMessages);
      } else {
        setMessages([{ role: "assistant", content: "\u2713 Ready. Continue this conversation." }]);
      }
      setLastResponse(null);
    } catch (error) {
      appendLog("ERROR", `Load conversation failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  function createNewChat() {
    setConversationId(null);
    setActiveSessionId(null);
    setMessages([{ role: "assistant", content: "\u2713 Ready. Test summary, search & multi-agent flows." }]);
    setLastResponse(null);
    appendLog("INFO", "New chat created.");
  }

  async function deleteConversation(sessionId: string, title: string) {
    if (!token) return;
    appendLog("INFO", `Deleting conversation: ${title}...`);
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/conversations/${sessionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) return;
        throw new Error(errorText || "Deletion failed.");
      }
      // If we deleted the active conversation, reset to new chat
      if (activeSessionId === sessionId) {
        createNewChat();
      }
      void fetchConversations();
      appendLog("INFO", `Deleted conversation: ${title}`);
    } catch (error) {
      appendLog("ERROR", `Delete conversation failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function fetchUserFiles() {
    if (!token) return;
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/files`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) {
          return;
        }
        throw new Error(errorText || "Failed to fetch files.");
      }

      const data = await response.json();
      setFiles(data);
    } catch (error) {
      appendLog("ERROR", `Fetch files failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function uploadFile(file: File) {
    if (!token || uploading) return;
    setUploading(true);

    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        appendLog("INFO", "Pre-creating a new conversation session to link this document...");
        const convRes = await fetch(`${BACKEND_URL}/api/v1/conversations`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title: `Chat with ${file.name.slice(0, 30)}`,
          }),
        });
        if (convRes.ok) {
          const sessionData = await convRes.json();
          currentSessionId = sessionData.id;
          setActiveSessionId(sessionData.id);
          setConversationId(sessionData.conversation_id);
          // Refresh list
          void fetchConversations();
        }
      } catch (e) {
        appendLog("ERROR", "Failed to pre-create conversation session.");
      }
    }

    // Quick-show file representation in list as processing
    const tempFileId = `temp-${Date.now()}`;
    const tempFile: UserFile = {
      id: tempFileId,
      file_name: file.name,
      file_type: file.name.split('.').pop() || "",
      status: "processing",
      chunk_count: 0,
      conversation_id: currentSessionId || undefined,
      created_at: new Date().toISOString()
    };
    setFiles((prev) => [tempFile, ...prev]);
    appendLog("INFO", `Starting upload for ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadUrl = currentSessionId
        ? `${BACKEND_URL}/api/v1/ingest/upload?conversation_id=${currentSessionId}`
        : `${BACKEND_URL}/api/v1/ingest/upload`;

      const response = await fetch(uploadUrl, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) {
          return;
        }
        throw new Error(errorText || "Upload failed.");
      }

      const data = await response.json();
      appendLog("INFO", `Upload success: ${file.name} indexed into ${data.chunks_created} chunks.`);
      setAuthMessage(`Uploaded ${file.name} successfully.`);
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      appendLog("ERROR", `Upload failed: ${errMsg}`);
      setAuthMessage(`Upload error: ${errMsg}`);
      // Mark local temp file as failed
      setFiles((prev) => prev.map((f) => f.id === tempFileId ? { ...f, status: "failed", error_message: errMsg } : f));
    } finally {
      setUploading(false);
      void fetchUserFiles();
    }
  }

  async function deleteFile(fileId: string, fileName: string) {
    if (!token) return;
    appendLog("INFO", `Deleting file: ${fileName}...`);
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/files/${fileId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) {
          return;
        }
        throw new Error(errorText || "Deletion failed.");
      }

      appendLog("INFO", `Deleted file: ${fileName}`);
      setAuthMessage(`Deleted ${fileName} successfully.`);
      void fetchUserFiles();
    } catch (error) {
      appendLog("ERROR", `Delete failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function ingestSampleData() {
    if (!token || ingestLoading) {
      appendLog("WARN", "Ingest request skipped because session is offline or a job is already running.");
      return;
    }

    setIngestLoading(true);
    setAuthMessage("Indexing sample documents...");
    appendLog("INFO", "Sample ingest triggered.");

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/ingest/batch`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) {
          return;
        }
        throw new Error(errorText || "Ingest failed.");
      }

      const data = (await response.json()) as {
        total_files_processed: number;
        total_documents_indexed: number;
        index_name: string;
        files_summary: Array<{
          file_path: string;
          documents_processed: number;
          documents_indexed: number;
          status: string;
        }>;
        errors?: string[];
      };

      setAuthMessage(
        `Indexed ${data.total_documents_indexed} docs from ${data.total_files_processed} files into ${data.index_name}.`
      );
      appendLog(
        "INFO",
        `Batch ingest completed: ${data.total_documents_indexed} documents indexed from ${data.total_files_processed} files.`
      );
      void fetchHealth("Post-ingest health probe");
    } catch (error) {
      if (handleAuthError(error)) {
        return;
      }
      const nextMessage = error instanceof Error ? error.message : "Ingest failed.";
      setAuthMessage(nextMessage);
      appendLog("ERROR", `Ingest failure: ${nextMessage}`);
    } finally {
      setIngestLoading(false);
    }
  }

  async function sendMessage(promptOverride?: string) {
    if (loading || !token) {
      appendLog("WARN", "Message send skipped because session is offline or request is already running.");
      return;
    }

    const nextMessage = (promptOverride ?? input).trim();
    if (!nextMessage) {
      appendLog("WARN", "Message send skipped because the prompt was empty.");
      return;
    }

    setMessages((current: Message[]) => [
      ...current,
      { role: "user", content: nextMessage },
    ]);
    setInput("");
    setLoading(true);
    appendLog("INFO", `Chat request started: ${nextMessage.slice(0, 72)}${nextMessage.length > 72 ? "..." : ""}`);

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: nextMessage,
          conversation_id: conversationId,
          history: historyPayload,
          file_ids: selectedFileIds.length > 0 ? selectedFileIds : undefined,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        if (handleAuthError(errorText, response)) {
          return;
        }
        throw new Error(errorText || "Backend request failed.");
      }

      const data: ChatResponse = await response.json();
      setConversationId(data.conversation_id);
      setLastResponse(data);
      // Refresh conversations list to show new/updated conversation
      void fetchConversations();
      setMessages((current: Message[]) => [
        ...current,
        { role: "assistant", content: data.answer },
      ]);
      appendLog(
        "INFO",
        `Chat response complete: route=${data.route}, agents=${data.agents_used.join(", ") || "none"}, cached=${String(data.cached)}.`
      );
    } catch (error) {
      if (handleAuthError(error)) {
        return;
      }
      const nextMessageText =
        error instanceof Error
          ? error.message
          : "Request failed. Make sure the backend is running and you are logged in.";

      setMessages((current: Message[]) => [
        ...current,
        {
          role: "assistant",
          content: nextMessageText,
        },
      ]);
      appendLog("ERROR", `Chat failure: ${nextMessageText}`);
    } finally {
      setLoading(false);
    }
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void sendMessage();
    }
  }

  const backendTone: StatusTone = healthError
    ? "offline"
    : health?.status === "ok"
      ? "online"
      : "neutral";

  const redisTone: StatusTone = health?.redis_connected ? "online" : "offline";
  const supabaseTone: StatusTone = health?.supabase_connected ? "online" : "offline";
  const modelTone: StatusTone =
    health?.llm_provider === "ollama" || health?.llm_provider === "huggingface"
      ? healthError
        ? "offline"
        : "online"
      : health?.llm_provider
        ? "neutral"
        : "offline";

  // Compute dynamic grid template columns based on panel toggles
  const gridTemplate = useMemo(() => {
    if (!supportsResizablePanels) return undefined;
    
    const cols = [];
    if (!hideLeftPanel) {
      cols.push(`${leftPanelWidth}px`, "10px");
    }
    cols.push("minmax(0, 1fr)");
    if (!hideRightPanel) {
      cols.push("10px", `${rightPanelWidth}px`);
    }
    
    return {
      gridTemplateColumns: cols.join(" ")
    };
  }, [supportsResizablePanels, hideLeftPanel, hideRightPanel, leftPanelWidth, rightPanelWidth]);

  return (
    <main className="page-container">
      {!isAuthenticated ? (
        <section className="auth-shell">
          <div className="auth-frame">
            <div className="auth-topbar">
              <div className="brand-mono">
                <Bot size={16} />
                multi-agent
              </div>
              <div className="corner-meta">
                <span>{clock || "--:--:--"}</span>
                <span>health: {healthError ? "offline" : "online"}</span>
              </div>
            </div>

            <div className="auth-grid">
              <div className="auth-intro">
                <div className="section-kicker">multi agent starter</div>
                <h1 className="auth-title">workspace</h1>
                <p className="auth-text">
                  Test agents, routing, cache & retrieval
                </p>

                <div className="corner-card">
                  <StatusDot label="backend" tone={backendTone} />
                  <StatusDot label="redis" tone={redisTone} />
                  <StatusDot label="supabase" tone={supabaseTone} />
                  <StatusDot label="model" tone={modelTone} />
                </div>

                <div className="quick-info-grid">
                  <InfoMiniCard label="provider" value={health?.llm_provider ?? "unknown"} />
                  <InfoMiniCard
                    label="last check"
                    value={lastHealthCheck || "--:--:--"}
                  />
                </div>
              </div>

              <form
                className="auth-panel"
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleAuth();
                }}
              >
                <div className="mode-switch">
                  <button
                    type="button"
                    onClick={() => setAuthMode("login")}
                    className={`mode-button ${authMode === "login" ? "mode-button-active" : ""}`}
                  >
                    login
                  </button>
                  <button
                    type="button"
                    onClick={() => setAuthMode("register")}
                    className={`mode-button ${authMode === "register" ? "mode-button-active" : ""}`}
                  >
                    register
                  </button>
                </div>

                <label className="field-label">
                  email
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    value={email}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      setEmail(event.target.value)
                    }
                    placeholder="you@example.com"
                    className="input-field"
                  />
                </label>

                <label className="field-label">
                  password
                  <input
                    type="password"
                    name="password"
                    autoComplete={authMode === "login" ? "current-password" : "new-password"}
                    autoCapitalize="none"
                    autoCorrect="off"
                    spellCheck={false}
                    value={password}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      setPassword(event.target.value)
                    }
                    placeholder="Enter password"
                    className="input-field"
                  />
                </label>

                <button type="submit" className="btn-primary" disabled={authLoading}>
                  {authLoading
                    ? authMode === "login"
                      ? "authorizing..."
                      : "creating..."
                    : authMode === "login"
                      ? "enter workspace"
                      : "create and enter"}
                </button>

                <div className="auth-footer-text">{authMessage}</div>
              </form>
            </div>

            <div className="bottom-hints">
              {quickPrompts.map((prompt) => (
                <div key={prompt} className="hint-chip">
                  {prompt}
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : (
        <>
          <header className="top-nav">
            <div className="nav-left">
              <button
                type="button"
                className="nav-icon-btn"
                onClick={() => setHideLeftPanel(prev => !prev)}
                title={hideLeftPanel ? "Show left sidebar" : "Hide left sidebar"}
              >
                <Sidebar size={13} />
              </button>
              <div className="nav-brand">
                <Bot size={16} />
                <span>Agentic Platform</span>
              </div>
              <div className="project-selector">
                <span>agentic-workspace</span>
                <Settings size={11} />
              </div>
            </div>

            <div className="nav-right">
              <button
                type="button"
                className="nav-icon-btn"
                onClick={() => setTheme(prev => prev === "dark" ? "light" : "dark")}
                title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              >
                {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
              </button>
              <button
                type="button"
                className="nav-icon-btn"
                onClick={() => setHideRightPanel(prev => !prev)}
                title={hideRightPanel ? "Show right sidebar" : "Hide right sidebar"}
              >
                <Sidebar size={13} style={{ transform: "scaleX(-1)" }} />
              </button>
              <button type="button" className="nav-icon-btn" title="System alerts">
                <Bell size={13} />
                <span className="nav-icon-badge" />
              </button>
              <button
                type="button"
                className="nav-icon-btn"
                onClick={() => void fetchHealth("Manual health refresh")}
                disabled={healthLoading}
                title="Refresh health indicators"
              >
                <RefreshCw size={13} className={healthLoading ? "animate-spin" : ""} />
              </button>
              <div ref={profileMenuRef} style={{ position: "relative" }}>
                <div
                  className="user-profile-avatar"
                  title={`Logged in as ${loggedInEmail}`}
                  onClick={() => setShowProfileMenu(prev => !prev)}
                >
                  {loggedInEmail ? loggedInEmail.charAt(0).toUpperCase() : "A"}
                </div>
                {showProfileMenu && (
                  <div style={{
                    position: "absolute",
                    right: 0,
                    top: "38px",
                    width: "200px",
                    background: "rgba(10, 10, 15, 0.98)",
                    border: "1px solid var(--border-glass)",
                    borderRadius: "8px",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
                    padding: "12px",
                    zIndex: 1000,
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px"
                  }}>
                    <div style={{ fontSize: "11px", opacity: 0.6, wordBreak: "break-all" }}>
                      {loggedInEmail}
                    </div>
                    <hr style={{ border: "0", borderTop: "1px solid var(--border-glass)", margin: "4px 0" }} />
                    <button
                      type="button"
                      onClick={() => {
                        void fetchHealth("Manual health refresh");
                        setShowProfileMenu(false);
                      }}
                      className="btn-secondary"
                      disabled={healthLoading}
                      style={{
                        padding: "8px",
                        fontSize: "11px",
                        justifyContent: "flex-start",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        width: "100%"
                      }}
                    >
                      <RefreshCw size={12} className={healthLoading ? "animate-spin" : ""} />
                      {healthLoading ? "checking..." : "refresh status"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        logout();
                        setShowProfileMenu(false);
                      }}
                      className="btn-secondary"
                      style={{
                        padding: "8px",
                        fontSize: "11px",
                        justifyContent: "flex-start",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        width: "100%",
                        color: "var(--color-error)"
                      }}
                    >
                      <LogOut size={12} />
                      logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          <section
            className="app-shell"
            style={gridTemplate}
          >
            {!hideLeftPanel && (
              <aside className="sidebar-panel">
                {/* Chat History Panel */}
                <div className="panel-card">
                  <div className="panel-header">
                    <div>
                      <div className="section-kicker">
                        <MessageSquare size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        history
                      </div>
                      <div className="panel-title">conversations</div>
                    </div>
                    <button
                      type="button"
                      onClick={createNewChat}
                      style={{
                        background: "var(--color-primary)",
                        border: "none",
                        borderRadius: "6px",
                        color: "#fff",
                        cursor: "pointer",
                        padding: "4px 10px",
                        fontSize: "10px",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        transition: "opacity 0.2s",
                      }}
                      title="Start a new conversation"
                    >
                      <Plus size={12} />
                      new
                    </button>
                  </div>

                  <div style={{
                    maxHeight: "200px",
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}>
                    {conversations.length === 0 ? (
                      <div style={{ fontSize: "11px", opacity: 0.5, textAlign: "center", padding: "12px 0" }}>
                        No conversations yet. Send a message to start.
                      </div>
                    ) : (
                      conversations.map((conv) => {
                        const isActive = activeSessionId === conv.id || conversationId === conv.conversation_id;
                        const timeAgo = (() => {
                          const diff = Date.now() - new Date(conv.last_active_at).getTime();
                          const mins = Math.floor(diff / 60000);
                          if (mins < 1) return "now";
                          if (mins < 60) return `${mins}m`;
                          const hrs = Math.floor(mins / 60);
                          if (hrs < 24) return `${hrs}h`;
                          const days = Math.floor(hrs / 24);
                          return `${days}d`;
                        })();

                        return (
                          <div
                            key={conv.id}
                            onClick={() => void loadConversation(conv)}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "8px 10px",
                              borderRadius: "6px",
                              background: isActive ? "rgba(99, 102, 241, 0.12)" : "rgba(255, 255, 255, 0.03)",
                              border: isActive ? "1px solid var(--color-primary)" : "1px solid var(--border-glass)",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                              fontSize: "11px",
                            }}
                          >
                            <div style={{ display: "flex", flexDirection: "column", gap: "2px", overflow: "hidden", flex: 1 }}>
                              <span style={{
                                fontWeight: isActive ? 600 : 500,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                color: isActive ? "var(--color-primary)" : "inherit",
                              }}>
                                {conv.title || "Untitled"}
                              </span>
                              <span style={{ fontSize: "9px", opacity: 0.5 }}>
                                {timeAgo} ago
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                void deleteConversation(conv.id, conv.title || "Untitled");
                              }}
                              style={{
                                background: "transparent",
                                border: "none",
                                cursor: "pointer",
                                color: "var(--color-error)",
                                opacity: 0.6,
                                padding: "2px",
                                display: "flex",
                                alignItems: "center",
                                flexShrink: 0,
                                marginLeft: "8px",
                              }}
                              title="Delete conversation"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Session Console Panel */}
                <div className="panel-card">
                  <div className="panel-header">
                    <div>
                      <div className="section-kicker">
                        <MessageSquare size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        session
                      </div>
                      <div className="panel-title">console</div>
                    </div>
                    <div className="panel-header-mono">●</div>
                  </div>

                  <div className="metric-stack">
                    <div className="metric-row">
                      <span className="metric-key">
                        <User size={11} style={{ display: "inline-block", verticalAlign: "middle" }} />
                        user
                      </span>
                      <span className="metric-value">{loggedInEmail}</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-key">
                        <Link2 size={11} style={{ display: "inline-block", verticalAlign: "middle" }} />
                        id
                      </span>
                      <span className="metric-value">{conversationId ?? "new"}</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-key">
                        <MessageSquare size={11} style={{ display: "inline-block", verticalAlign: "middle" }} />
                        messages
                      </span>
                      <span className="metric-value">{String(messageCount)}</span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-key">
                        <Route size={11} style={{ display: "inline-block", verticalAlign: "middle" }} />
                        route
                      </span>
                      <span className="metric-value">{lastResponse?.route ?? "--"}</span>
                    </div>
                  </div>
                </div>

                {/* Documents Panel Card */}
                <div className="panel-card">
                   <div className="panel-header">
                     <div>
                       <div className="section-kicker">
                         <FileText size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                         retrieval
                       </div>
                       <div className="panel-title">documents</div>
                     </div>
                   </div>

                   <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                     <label style={{
                       display: "flex",
                       flexDirection: "column",
                       alignItems: "center",
                       justifyContent: "center",
                       padding: "16px",
                       borderRadius: "8px",
                       border: "1px dashed var(--border-glass)",
                       background: "rgba(255, 255, 255, 0.02)",
                       cursor: uploading ? "not-allowed" : "pointer",
                       textAlign: "center",
                       transition: "all 0.2s ease"
                     }}>
                       <input
                         type="file"
                         onChange={(e) => {
                           const file = e.target.files?.[0];
                           if (file) void uploadFile(file);
                         }}
                         style={{ display: "none" }}
                         disabled={uploading}
                         accept=".pdf,.docx,.txt,.csv,.xlsx,.pptx,.html,.json,.md"
                       />
                       <Download size={16} style={{ marginBottom: "6px", opacity: 0.7 }} />
                       <span style={{ fontSize: "11px", fontWeight: 500 }}>
                         {uploading ? "Uploading file..." : "Upload local document"}
                       </span>
                       <span style={{ fontSize: "9px", opacity: 0.5, marginTop: "2px" }}>
                         PDF, DOCX, TXT, CSV, XLSX, PPTX, HTML, JSON, MD
                       </span>
                     </label>

                     <div style={{ 
                       maxHeight: "180px", 
                       overflowY: "auto", 
                       display: "flex", 
                       flexDirection: "column", 
                       gap: "6px",
                       marginTop: "4px"
                     }}>
                       {(() => {
                          const conversationFiles = files.filter(
                            (file) => 
                              !file.conversation_id || 
                              file.conversation_id === activeSessionId || 
                              file.id.startsWith("temp-")
                          );

                          if (conversationFiles.length === 0) {
                            return (
                              <div style={{ fontSize: "11px", opacity: 0.5, textAlign: "center", padding: "8px 0" }}>
                                No documents uploaded in this conversation.
                              </div>
                            );
                          }

                          return conversationFiles.map((file) => {
                            const isProcessing = file.status === "processing";
                            const isReady = file.status === "ready";
                            const isFailed = file.status === "failed";
                            const isSelected = selectedFileIds.includes(file.id);
                            
                            return (
                             <div key={file.id} style={{
                               display: "flex",
                               alignItems: "center",
                               justifyContent: "space-between",
                               padding: "8px",
                               borderRadius: "6px",
                               background: "rgba(255, 255, 255, 0.03)",
                               border: isSelected ? "1px solid var(--color-primary)" : "1px solid var(--border-glass)",
                               fontSize: "11px",
                               transition: "all 0.2s ease"
                             }}>
                               <div style={{ display: "flex", alignItems: "center", maxWidth: "70%" }}>
                                 <input
                                   type="checkbox"
                                   checked={isSelected}
                                   onChange={() => {
                                     setSelectedFileIds(prev =>
                                       prev.includes(file.id)
                                         ? prev.filter(id => id !== file.id)
                                         : [...prev, file.id]
                                     );
                                   }}
                                   style={{
                                     marginRight: "8px",
                                     cursor: isFailed ? "not-allowed" : "pointer",
                                     accentColor: "var(--color-primary)"
                                   }}
                                   disabled={isFailed}
                                   title={isFailed ? "Cannot query failed document" : "Select/Deselect for RAG search"}
                                 />
                                 <div style={{ display: "flex", flexDirection: "column", gap: "2px", overflow: "hidden" }}>
                                   <span style={{ 
                                     fontWeight: 500, 
                                     overflow: "hidden", 
                                     textOverflow: "ellipsis", 
                                     whiteSpace: "nowrap" 
                                   }} title={file.file_name}>
                                     {file.file_name}
                                   </span>
                                   <span style={{ fontSize: "9px", opacity: 0.5 }}>
                                     {file.file_type.toUpperCase()} • {file.chunk_count} chunks
                                   </span>
                                 </div>
                               </div>
                               <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                 {isProcessing && (
                                   <span style={{ 
                                     color: "var(--color-warning)", 
                                     fontSize: "9px",
                                     display: "inline-flex",
                                     alignItems: "center",
                                     gap: "4px"
                                   }}>
                                     <RefreshCw size={10} className="animate-spin-custom" />
                                     indexing
                                   </span>
                                 )}
                                 {isReady && (
                                   <span style={{ color: "var(--color-success)", fontSize: "9px" }}>
                                     ✓ ready
                                   </span>
                                 )}
                                 {isFailed && (
                                   <span style={{ color: "var(--color-error)", fontSize: "9px" }} title={file.error_message || "Ingestion failed"}>
                                     ✗ error
                                   </span>
                                 )}
                                 <button
                                   type="button"
                                   onClick={() => void deleteFile(file.id, file.file_name)}
                                   style={{
                                     background: "transparent",
                                     border: "none",
                                     cursor: "pointer",
                                     color: "var(--color-error)",
                                     opacity: 0.8,
                                     padding: "2px",
                                     display: "flex",
                                     alignItems: "center",
                                     justifyContent: "center",
                                     marginLeft: "4px"
                                   }}
                                   title="Delete document"
                                 >
                                   ✗
                                 </button>
                               </div>
                             </div>
                           );
                         });
                       })()}
                     </div>
                   </div>
                 </div>

                 <div className="panel-card">
                  <div className="panel-header">
                    <div>
                      <div className="section-kicker">
                        <Zap size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        status
                      </div>
                      <div className="panel-title">services</div>
                    </div>
                    <div className="panel-header-mono">{clock || "--:--:--"}</div>
                  </div>

                  <div className="status-card-grid">
                    <ServiceStatusCard label="backend" tone={backendTone} icon={<Bot size={13} />} />
                    <ServiceStatusCard label="redis" tone={redisTone} icon={<Database size={13} />} />
                    <ServiceStatusCard label="supabase" tone={supabaseTone} icon={<Database size={13} />} />
                    <ServiceStatusCard label="model" tone={modelTone} icon={<Zap size={13} />} />
                  </div>

                  <div className="card-footer-info">
                    <span>
                      <Clock size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                      {lastHealthCheck || "--:--:--"}
                    </span>
                    <span>
                      cached: {lastResponse ? String(lastResponse.cached) : "--"}
                    </span>
                  </div>
                </div>

                {authMessage && (
                  <div className="card-footer-info" style={{ marginTop: 8, textAlign: "center" }}>
                    {authMessage}
                  </div>
                )}
              </aside>
            )}

            {!hideLeftPanel && supportsResizablePanels && (
              <div
                className="resize-divider"
                onPointerDown={(event) => startResize("left", event)}
              />
            )}

            <section className="chat-column">
              <div className="chat-header">
                <div className="chat-header-left">
                  <div className="chat-header-brand">
                    <MessageSquare size={14} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 6 }} />
                    workspace
                  </div>
                  <div className="chat-header-meta">
                    <Bot size={12} style={{ display: "inline-block", verticalAlign: "middle" }} />
                    {health?.llm_provider ?? "unknown"}
                  </div>
                </div>
                <div className="chat-header-right">
                  <span>
                    <FileText size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                    context size: {lastResponse?.context_messages ?? 0}
                  </span>
                </div>
              </div>

              <div className="chat-window">
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`message-row ${message.role === "user" ? "message-row-user" : "message-row-assistant"}`}
                  >
                    <div className="avatar-badge">{message.role === "user" ? "U" : "AI"}</div>
                    <div className="message-bubble">
                      <div className="message-meta">
                        {message.role === "user" ? "user" : "assistant"}
                      </div>
                      <div className="message-content">
                        {renderRichText(message.content)}
                      </div>
                    </div>
                  </div>
                ))}

                {loading ? (
                  <div className="message-row message-row-assistant">
                    <div className="avatar-badge">AI</div>
                    <div className="message-bubble">
                      <div className="message-meta">assistant</div>
                      <div className="typing-dots">
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                      </div>
                    </div>
                  </div>
                ) : null}
                <div ref={messagesEndRef} />
              </div>

              <div className="prompt-dock">
                {hasUploadedDocs && (
                  <>
                    <div className="prompt-dock-header">
                      <span className="prompt-dock-title">
                        <Zap size={11} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        quick prompts
                      </span>
                      <span className="prompt-dock-meta">tap to load</span>
                    </div>

                    <div className="prompt-scroll">
                      <div className="prompt-row">
                        {activeQuickPrompts.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            onClick={() => setInput(prompt)}
                            className="prompt-chip-btn"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}

                <div className="composer-box">
                  <textarea
                    value={input}
                    onChange={(event: ChangeEvent<HTMLTextAreaElement>) =>
                      setInput(event.target.value)
                    }
                    onKeyDown={onComposerKeyDown}
                    placeholder="Type message... Cmd/Ctrl+Enter to send"
                    className="composer-textarea"
                    rows={3}
                  />
                  <div className="composer-footer">
                    <div className="composer-tools-group">
                      <button
                        type="button"
                        className="composer-tool-btn"
                        title="Attach files (mock)"
                        onClick={() => appendLog("INFO", "Mock attachment clicked.")}
                      >
                        <Link2 size={13} />
                      </button>
                      <button
                        type="button"
                        className="composer-tool-btn"
                        title="Add code snippet"
                        onClick={() => setInput((prev) => prev + "\n```\n\n```")}
                      >
                        <Code size={13} />
                      </button>
                      <button
                        type="button"
                        className="composer-tool-btn"
                        title="Force routes"
                        onClick={() => appendLog("INFO", "Force route settings triggered.")}
                      >
                        <Route size={13} />
                      </button>
                    </div>
                    <div className="composer-hint">
                      <Keyboard size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                      Cmd+Enter
                    </div>
                    <button
                      type="button"
                      onClick={() => void sendMessage()}
                      className="composer-send-btn"
                      disabled={loading}
                    >
                      {loading ? (
                        <Clock size={14} />
                      ) : (
                        <Send size={14} />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </section>

            {!hideRightPanel && supportsResizablePanels && (
              <div
                className="resize-divider"
                onPointerDown={(event) => startResize("right", event)}
              />
            )}

            {!hideRightPanel && (
              <aside className="sidebar-panel">
                <div className="terminal-card">
                  <div className="terminal-header">
                    <div className="terminal-title">
                      <BarChart3 size={12} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 6 }} />
                      activity
                    </div>
                    <div className="panel-header-mono">{clock || "--:--:--"}</div>
                  </div>

                  <div className="terminal-body">
                    <div className="terminal-block">
                      <div className="terminal-block-title">
                        <FileText size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        events timeline
                      </div>
                      {activityLogs.length ? (
                        <div className="timeline-container">
                          {activityLogs.map((log) => (
                            <div key={log.id} className="timeline-item">
                              <div className={`timeline-dot timeline-dot-${log.level.toLowerCase()}`} />
                              <div className="timeline-item-meta">
                                <span className="timeline-time">{log.time}</span>
                                <span className={`timeline-level-badge level-${log.level.toLowerCase()}`}>
                                  {log.level}
                                </span>
                              </div>
                              <div className="timeline-message">{log.message}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="empty-placeholder">No events yet.</div>
                      )}
                    </div>

                    <div className="terminal-block">
                      <div className="terminal-block-title">
                        <Inbox size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        response routing
                      </div>
                      <TerminalLine
                        label={<Route size={11} />}
                        value={lastResponse?.route ?? "--"}
                      />
                      <TerminalLine
                        label={<Bot size={11} />}
                        value={
                          lastResponse?.agents_used?.length
                            ? lastResponse.agents_used.join(", ")
                            : "--"
                        }
                      />
                      <TerminalLine
                        label={<Database size={11} />}
                        value={lastResponse ? String(lastResponse.cached) : "--"}
                      />
                      <TerminalLine
                        label={<Link2 size={11} />}
                        value={conversationId ?? "new"}
                      />
                    </div>

                    <div className="terminal-block">
                      <div className="terminal-block-title">
                        <Wrench size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        output execution
                      </div>
                      {lastResponse?.agent_results?.length ? (
                        lastResponse.agent_results.map((result) => (
                          <div key={result.agent} className="agent-output-card">
                            <div className="agent-output-header">
                              <span>{result.agent}</span>
                              <span className="panel-header-mono">●</span>
                            </div>
                            <pre className="agent-pre">{result.output}</pre>
                          </div>
                        ))
                      ) : (
                        <div className="empty-placeholder">No outputs yet</div>
                      )}
                    </div>

                    <div className="terminal-block">
                      <div className="terminal-block-title">
                        <Heart size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
                        health check
                      </div>
                      <TerminalLine
                        label={<Monitor size={11} />}
                        value={healthError ? "offline" : "online"}
                      />
                      <TerminalLine
                        label={<Clock size={11} />}
                        value={lastHealthCheck || "--:--:--"}
                      />
                      <TerminalLine
                        label={<Bot size={11} />}
                        value={health?.llm_provider ?? "unknown"}
                      />
                      <TerminalLine
                        label={<AlertTriangle size={11} />}
                        value={healthError || "--"}
                      />
                    </div>
                  </div>
                </div>
              </aside>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function StatusDot({
  label,
  tone,
  compact = false,
}: {
  label: string;
  tone: StatusTone;
  compact?: boolean;
}) {
  const isOnline = tone === "online";
  const isOffline = tone === "offline";

  return (
    <div className={compact ? "status-row status-row-compact" : "status-row"}>
      <span
        className={`status-dot-pulse ${
          isOnline ? "status-online" : isOffline ? "status-offline" : "status-neutral"
        }`}
      />
      <span className="status-label">{label}</span>
      <span
        className={`status-text ${
          isOnline
            ? "status-text-online"
            : isOffline
              ? "status-text-offline"
              : "status-text-neutral"
        }`}
      >
        {isOnline ? "online" : isOffline ? "offline" : "idle"}
      </span>
    </div>
  );
}

function ServiceStatusCard({
  label,
  tone,
  icon,
}: {
  label: string;
  tone: StatusTone;
  icon: React.ReactNode;
}) {
  const isOnline = tone === "online";
  const isOffline = tone === "offline";

  return (
    <div className="status-card">
      <div className="status-card-header">
        <span className="status-card-title">
          {icon}
          {label}
        </span>
        <span
          className={`status-dot-pulse ${
            isOnline ? "status-online" : isOffline ? "status-offline" : "status-neutral"
          }`}
        />
      </div>
      <span
        className={`status-card-value ${
          isOnline
            ? "status-text-online"
            : isOffline
              ? "status-text-offline"
              : "status-text-neutral"
        }`}
      >
        {isOnline ? "online" : isOffline ? "offline" : "idle"}
      </span>
    </div>
  );
}

function InfoMiniCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-mini-card">
      <div className="info-mini-label">
        {label === "provider" ? (
          <Bot size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
        ) : (
          <Clock size={10} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 4 }} />
        )}
        {label}
      </div>
      <div className="info-mini-value">{value}</div>
    </div>
  );
}

function TerminalLine({
  label,
  value,
}: {
  label: React.ReactNode;
  value: string;
}) {
  return (
    <div className="terminal-kv-row">
      <span className="terminal-kv-key">{label}</span>
      <span className="terminal-kv-val">{value}</span>
    </div>
  );
}

function renderRichText(text: string) {
  const lines = text.split("\n");

  return (
    <div className="rich-text-container">
      {lines.map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={`space-${index}`} className="rich-spacer" style={{ height: 3 }} />;
        }

        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={`bullet-${index}`} className="rich-bullet-row">
              <span className="rich-bullet">▸</span>
              <span>{trimmed.slice(2)}</span>
            </div>
          );
        }

        if (/^\d+\.\s/.test(trimmed)) {
          const [marker, ...rest] = trimmed.split(" ");
          return (
            <div key={`number-${index}`} className="rich-bullet-row">
              <span className="rich-number">{marker}</span>
              <span>{rest.join(" ")}</span>
            </div>
          );
        }

        return (
          <p key={`paragraph-${index}`} className="rich-paragraph">
            {renderInlineFormatting(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function renderInlineFormatting(text: string) {
  const parts = text.split(/(`[^`]+`)/g);

  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={`code-${index}`} className="inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }

    return <span key={`text-${index}`}>{part}</span>;
  });
}
