"use client";

import { useMemo, useRef, useState } from "react";

type ChatMessage = { 
  role: "user" | "assistant"; 
  content: string; 
  attachments?: { name: string; size: number }[];
  processing?: boolean;
  // RAG metadata
  confidence?: "high" | "medium" | "low";
  drawings_referenced?: string[];
  sources?: Array<{
    drawing_name: string;
    page_number: number;
    score: number;
  }>;
};

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [namespace, setNamespace] = useState("default");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const apiBase = useMemo(() => process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000", []);

  async function sendQuery(query: string) {
    const trimmed = query.trim();
    if (!trimmed) return;
    const next = [...messages, { role: "user", content: trimmed } as ChatMessage];
    setMessages(next);
    setInput("");
    
    // Build conversation history (last 10 messages, excluding attachments for API)
    const conversationHistory = messages.slice(-10).map(m => ({
      role: m.role,
      content: m.content
    }));
    
    const res = await fetch(`${apiBase}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        query: trimmed, 
        top_k: 6, 
        namespace,
        conversation_history: conversationHistory
      }),
    });
    if (!res.ok) {
      setMessages([...next, { role: "assistant", content: `Error: ${res.status}` }]);
      return;
    }
    const data = await res.json();
    
    // Extract RAG metadata for drawing highlighting
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: data.answer,
      confidence: data.confidence,
      drawings_referenced: data.drawings_referenced,
      sources: data.sources?.map((s: any) => ({
        drawing_name: s.drawing_name,
        page_number: s.page_number,
        score: s.score,
      })),
    };
    
    setMessages([...next, assistantMessage]);
  }

  async function sendMessage() {
    const question = input.trim();
    if (!question && selectedFiles.length === 0) return;

    // Create user message with attachments
    const attachments = selectedFiles.map(f => ({ name: f.name, size: f.size }));
    const userMessage: ChatMessage = {
      role: "user",
      content: question || "Analyze these documents",
      attachments: attachments.length > 0 ? attachments : undefined,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");

    // Show processing message if files need to be uploaded
    if (selectedFiles.length > 0) {
      const processingMessage: ChatMessage = {
        role: "assistant",
        content: "Processing attachments...",
        processing: true,
      };
      setMessages(prev => [...prev, processingMessage]);
      
      // Upload files silently
      await onUpload(selectedFiles, true);
      setSelectedFiles([]);
      
      // Remove processing message
      setMessages(prev => prev.filter(m => !m.processing));
    }

    // Send the query
    await sendQuery(question || "What information can you extract from these documents?");
  }

  async function onUpload(files: FileList | File[], silent: boolean = false) {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      form.append("namespace", namespace);
      const res = await fetch(`${apiBase}/upload`, { method: "POST", body: form });
      if (!res.ok) {
        if (!silent) alert(`Upload failed: ${res.status}`);
        return;
      }
      const data = await res.json();
      if (!silent) {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: `Ingested ${data.files_ingested} files, ${data.chunks_indexed} chunks into namespace '${data.namespace}'.` },
        ]);
        if (input.trim()) {
          await sendQuery(input);
        }
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleFileSelect(files: FileList | null) {
    if (!files) return;
    setSelectedFiles(Array.from(files));
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b p-4 flex items-center justify-between">
        <h1 className="font-semibold">Construction RAG</h1>
        <div />
      </header>
      <main className="flex-1 max-w-3xl w-full mx-auto p-4 flex flex-col gap-4">
        <div className="flex-1 border rounded p-4 overflow-auto bg-white">
          <div className="flex flex-col gap-3">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                <div className={`inline-block rounded px-3 py-2 ${m.role === "user" ? "bg-black text-white" : "bg-gray-100"}`}>
                  {m.attachments && (
                    <div className="mb-2 space-y-1">
                      {m.attachments.map((att, j) => (
                        <div key={j} className="flex items-center gap-1 text-xs opacity-80">
                          <span>📎</span>
                          <span>{att.name}</span>
                          <span className="text-xs">({(att.size / 1024).toFixed(0)}KB)</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {m.processing ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin w-3 h-3 border border-gray-400 border-t-transparent rounded-full"></div>
                      <span>{m.content}</span>
                    </div>
                  ) : (
                    <>
                      {m.content}
                      {/* Drawing Highlighting for Assistant Messages */}
                      {m.role === "assistant" && (m.drawings_referenced || m.confidence || m.sources) && (
                        <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                          {/* Confidence Badge */}
                          {m.confidence && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium">Confidence:</span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                m.confidence === "high" ? "bg-green-100 text-green-800" :
                                m.confidence === "medium" ? "bg-yellow-100 text-yellow-800" :
                                "bg-red-100 text-red-800"
                              }`}>
                                {m.confidence.toUpperCase()}
                              </span>
                            </div>
                          )}
                          
                          {/* Referenced Drawings */}
                          {m.drawings_referenced && m.drawings_referenced.length > 0 && (
                            <div>
                              <span className="text-xs font-medium">Referenced Drawings:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {m.drawings_referenced.map((drawing, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                                    📋 {drawing}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Source Details */}
                          {m.sources && m.sources.length > 0 && (
                            <div>
                              <span className="text-xs font-medium">Sources:</span>
                              <div className="space-y-1 mt-1">
                                {m.sources.slice(0, 3).map((source, idx) => (
                                  <div key={idx} className="flex items-center gap-2 text-xs">
                                    <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                                    <span className="font-medium">{source.drawing_name}</span>
                                    <span className="text-gray-500">Page {source.page_number}</span>
                                    <span className="text-gray-400">({(source.score * 100).toFixed(0)}% match)</span>
                                  </div>
                                ))}
                                {m.sources.length > 3 && (
                                  <div className="text-xs text-gray-500">
                                    +{m.sources.length - 3} more sources
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            className="border rounded px-2 py-1 text-sm w-32"
            placeholder="namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="rounded-full w-10 h-10 flex items-center justify-center bg-black text-white text-xl"
            title="Upload PDFs"
            disabled={uploading}
          >
            +
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
          <div className="flex-1 relative">
            {selectedFiles.length > 0 && (
              <div className="absolute -top-8 left-0 flex gap-1 flex-wrap">
                {selectedFiles.map((file, i) => (
                  <div key={i} className="flex items-center gap-1 bg-gray-100 rounded px-2 py-1 text-xs">
                    <span>📎</span>
                    <span>{file.name}</span>
                    <button
                      onClick={() => setSelectedFiles(files => files.filter((_, idx) => idx !== i))}
                      className="text-gray-500 hover:text-red-500"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              placeholder={uploading ? "Processing..." : "Ask a question about the drawings"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={uploading}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage();
              }}
            />
          </div>
          <button
            onClick={sendMessage}
            className="px-4 py-2 bg-black text-white rounded"
            disabled={uploading}
          >
            Send
          </button>
        </div>
      </main>
    </div>
  );
}
