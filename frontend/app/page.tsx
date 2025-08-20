"use client";

import { useMemo, useRef, useState } from "react";

type ChatMessage = { 
  role: "user" | "assistant"; 
  content: string; 
  attachments?: { name: string; size: number }[];
  processing?: boolean;
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
    const res = await fetch(`${apiBase}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: trimmed, top_k: 6, namespace }),
    });
    if (!res.ok) {
      setMessages([...next, { role: "assistant", content: `Error: ${res.status}` }]);
      return;
    }
    const data = await res.json();
    setMessages([...next, { role: "assistant", content: data.answer }]);
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
                    m.content
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
