// app.jsx - the chat UI (React). Prepared for you; you don't need to edit it.
//
// It only talks to OUR backend (/chat and /health). The Groq API key is never
// in this file or in the browser.

const { useState, useEffect, useRef, useCallback } = React;

// Same server that serves this page. Change it if your UI runs elsewhere.
const API_URL = "";

// ---------------------------------------------------------------------------
// App data
// ---------------------------------------------------------------------------

// The three tools you build in Steps 3, 4 and 5.
const CORE_TOOLS = [
  { name: "search_products", step: 3, label: "Product search" },
  { name: "check_order", step: 4, label: "Order lookup" },
  { name: "calculate_discount", step: 5, label: "Discount calculator" },
];

const EXAMPLES = [
  { emoji: "🎧", text: "Find wireless headphones under ₹3,000." },
  { emoji: "📦", text: "Where is my order ORD1024?" },
  { emoji: "💻", text: "Find the cheapest laptop under ₹50,000 and show its price after 10% off." },
  { emoji: "🔎", text: "Where is order ORD9999?" },
  { emoji: "🌙", text: "Write me a poem about the moon." },
  { emoji: "🏏", text: "Who won the cricket match yesterday?" },
];

const CATEGORIES = [
  { id: "headphones", emoji: "🎧", label: "Headphones" },
  { id: "laptops", emoji: "💻", label: "Laptops" },
  { id: "smartphones", emoji: "📱", label: "Phones" },
  { id: "smartwatches", emoji: "⌚", label: "Watches" },
  { id: "speakers", emoji: "🔊", label: "Speakers" },
  { id: "accessories", emoji: "🖱️", label: "Accessories" },
];
const CATEGORY_EMOJI = Object.fromEntries(CATEGORIES.map((c) => [c.id, c.emoji]));

const ORDER_STEPS = ["Placed", "Processing", "Shipped", "Out for delivery", "Delivered"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

function money(value) {
  const n = Number(value);
  if (value === null || value === undefined || !Number.isFinite(n)) return String(value ?? "");
  return inr.format(n).replace(/\.00$/, "");
}

function niceDate(text) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text || "");
  if (!m) return text || "";
  return new Date(+m[1], +m[2] - 1, +m[3]).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

// Small line icons (drawn with SVG, so no icon library is needed).
const ICONS = {
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  trash: <><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></>,
  bolt: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  check: <path d="M20 6 9 17l-5-5" />,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  package: <><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><path d="M3.3 7 12 12l8.7-5" /><path d="M12 22V12" /></>,
  tag: <><path d="M12 2H2v10l9.3 9.3a1 1 0 0 0 1.4 0l8.6-8.6a1 1 0 0 0 0-1.4Z" /><circle cx="7" cy="7" r="1.5" /></>,
  sparkles: <><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /><path d="M19 3v4M17 5h4M5 17v4M3 19h4" /></>,
  alert: <><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>,
};

function Icon({ name, size = 18 }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

// ShopBot's animated "orb" avatar.
function Orb({ size = 34, busy = false }) {
  return <span className={`orb ${busy ? "busy" : ""}`} style={{ "--s": `${size}px` }} aria-hidden="true"><span /></span>;
}

// A tiny Markdown renderer: paragraphs, bullet/numbered lists, simple tables and **bold**.
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.length > 4 && part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part
  );
}

function Markdown({ text }) {
  const lines = (text || "").replace(/\r/g, "").split("\n");
  const isBullet = (l) => /^\s*([-*•]|\d+[.)])\s+/.test(l);
  const isTable = (l) => l.trim().startsWith("|");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    if (!lines[i].trim()) { i++; continue; }

    if (isBullet(lines[i])) {
      const items = [];
      while (i < lines.length && isBullet(lines[i])) items.push(lines[i++].trim().replace(/^([-*•]|\d+[.)])\s+/, ""));
      blocks.push(<ul key={blocks.length}>{items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>);
    } else if (isTable(lines[i])) {
      const rows = [];
      while (i < lines.length && isTable(lines[i])) {
        const row = lines[i++].trim();
        if (!/^\|[\s:|-]+\|?$/.test(row)) rows.push(row.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
      }
      blocks.push(
        <div className="md-table" key={blocks.length}>
          <table><tbody>{rows.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{inline(c)}</td>)}</tr>)}</tbody></table>
        </div>
      );
    } else {
      const para = [];
      while (i < lines.length && lines[i].trim() && !isBullet(lines[i]) && !isTable(lines[i])) {
        para.push(lines[i++].trim().replace(/^#{1,6}\s+/, ""));
      }
      blocks.push(<p key={blocks.length}>{para.map((p, j) => <React.Fragment key={j}>{j > 0 && <br />}{inline(p)}</React.Fragment>)}</p>);
    }
  }
  return <div className="md">{blocks}</div>;
}

// If a card can't be drawn (e.g. a tool returned an unexpected shape), hide it instead of crashing the page.
class SafeBoundary extends React.Component {
  constructor(props) { super(props); this.state = { failed: false }; }
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? null : this.props.children; }
}

// ---------------------------------------------------------------------------
// Cards drawn from tool results
// ---------------------------------------------------------------------------
function ProductGrid({ products }) {
  return (
    <div className="product-grid">
      {products.map((p, i) => (
        <div key={p.id || i} className={`product ${p.in_stock === false ? "sold-out" : ""}`} style={{ "--i": i }}>
          <div className={`product-art art-${p.category}`}>
            <span>{CATEGORY_EMOJI[p.category] || "🛍️"}</span>
            {Number.isFinite(Number(p.rating)) && <span className="product-rating">★ {Number(p.rating).toFixed(1)}</span>}
          </div>
          <div className="product-info">
            <div className="product-name">{p.name}</div>
            <div className="product-row">
              <span className="product-price">{money(p.price)}</span>
              {p.in_stock !== undefined && (
                <span className={`badge ${p.in_stock ? "badge-green" : "badge-red"}`}>{p.in_stock ? "In stock" : "Out of stock"}</span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function OrderTracker({ order }) {
  if (order.found === false) {
    return (
      <div className="card card-missing">
        <span className="card-icon red"><Icon name="search" size={20} /></span>
        <div>
          <div className="card-title">Order {order.order_id} not found</div>
          <div className="card-sub">No order exists with this ID. Check the number and try again.</div>
        </div>
      </div>
    );
  }

  const status = String(order.status || "");
  const current = ORDER_STEPS.findIndex((s) => s.toLowerCase() === status.toLowerCase());
  const stopped = current === -1; // e.g. Cancelled or Returned
  const items = String(order.items || "").split(";").map((s) => s.trim()).filter(Boolean);
  const pct = stopped ? 0 : (current / (ORDER_STEPS.length - 1)) * 100;

  return (
    <div className="card order">
      <div className="order-head">
        <div className="order-title">
          <span className="card-icon"><Icon name="package" size={20} /></span>
          <div>
            <div className="card-title">Order {order.order_id}</div>
            {order.order_date && <div className="card-sub">Placed on {niceDate(order.order_date)}</div>}
          </div>
        </div>
        <span className={`badge ${stopped ? "badge-red" : status.toLowerCase() === "delivered" ? "badge-green" : "badge-blue"}`}>{status}</span>
      </div>

      {!stopped && (
        <ol className="tracker" style={{ "--pct": `${pct}%` }}>
          {ORDER_STEPS.map((step, i) => (
            <li key={step} className={i < current ? "done" : i === current ? "current" : ""}>
              <span className="tracker-dot">{i < current ? <Icon name="check" size={12} /> : ""}</span>
              <span className="tracker-label">{step}</span>
            </li>
          ))}
        </ol>
      )}

      <div className="order-foot">
        {items.length > 0 && <div className="order-items">{items.map((it, i) => <div key={i}>{it}</div>)}</div>}
        <div className="order-facts">
          {order.estimated_delivery && <div><span>{status.toLowerCase() === "delivered" ? "Delivered" : "Arriving"}</span><strong>{niceDate(order.estimated_delivery)}</strong></div>}
          {order.total !== undefined && <div><span>Total</span><strong>{money(order.total)}</strong></div>}
        </div>
      </div>
    </div>
  );
}

function PriceReceipt({ d }) {
  return (
    <div className="card receipt">
      <div className="receipt-head">
        <span className="card-icon gold"><Icon name="tag" size={18} /></span>
        <span className="receipt-title">Discount applied</span>
      </div>
      <div className="receipt-row"><span>Original price</span><span className="strike">{money(d.original_price)}</span></div>
      <div className="receipt-row saving"><span>Discount ({d.discount_percent}%)</span><span>−{money(d.discount_amount)}</span></div>
      <div className="receipt-total"><span>You pay</span><span>{money(d.final_price)}</span></div>
    </div>
  );
}

function ToolCards({ calls }) {
  if (!calls || calls.length === 0) return null;
  const cards = calls.map((call, i) => {
    const r = call.result || {};
    if (r.error) return null;
    if (call.name === "search_products" && Array.isArray(r.products) && r.products.length) return <ProductGrid key={i} products={r.products} />;
    if (call.name === "check_order" && "found" in r) return <OrderTracker key={i} order={r} />;
    if (call.name === "calculate_discount" && r.final_price !== undefined) return <PriceReceipt key={i} d={r} />;
    return null;
  }).filter(Boolean);
  return cards.length ? <div className="cards">{cards}</div> : null;
}

// The "Used N tools" panel: what the model asked for, and what our Python returned.
function ToolCalls({ calls }) {
  if (!calls || calls.length === 0) return null;
  return (
    <details className="trace">
      <summary>
        <span className="trace-lead"><span className="trace-emoji">🔧</span> Used {calls.length} tool{calls.length > 1 ? "s" : ""}:</span>
        {calls.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="trace-arrow">→</span>}
            <code className="trace-chip">{c.name}</code>
          </React.Fragment>
        ))}
        <span className="trace-caret"><Icon name="chevron" size={14} /></span>
      </summary>
      <div className="trace-body">
        {calls.map((call, i) => (
          <div key={i} className="trace-call">
            <div className="trace-name"><span className="trace-step">{i + 1}</span><code>{call.name}({JSON.stringify(call.arguments)})</code></div>
            <pre>{JSON.stringify(call.result, null, 2)}</pre>
          </div>
        ))}
      </div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Progress: backend status + which tools are loaded
// ---------------------------------------------------------------------------
function toolState(health) {
  const loaded = new Set(health?.tools || []);
  const extras = (health?.tools || []).filter((t) => !CORE_TOOLS.some((c) => c.name === t));
  const count = CORE_TOOLS.filter((t) => loaded.has(t.name)).length;
  return { loaded, extras, count };
}

function BackendStatus({ health }) {
  if (!health) return <div className="backend"><span className="dot" />Backend: connecting…</div>;
  if (!health.online) return <div className="backend offline"><span className="dot" />Backend: offline. Is the server running? Check its terminal.</div>;
  return (
    <div className="backend online">
      <div><span className="dot" />Backend: <b>connected</b> · Model: <code>{health.model}</code></div>
      {health.provider === "groq" && !health.api_key_configured && <div className="note">⚠ no GROQ_API_KEY in .env</div>}
    </div>
  );
}

function ProgressRing({ count, total }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <div className="ring">
      <svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#3D7BFF" />
            <stop offset="100%" stopColor="#8FD3FF" />
          </linearGradient>
        </defs>
        <circle cx="32" cy="32" r={r} className="ring-track" />
        <circle cx="32" cy="32" r={r} className="ring-fill" strokeDasharray={c} strokeDashoffset={c * (1 - count / total)} />
      </svg>
      <span className="ring-text">{count}<small>/{total}</small></span>
    </div>
  );
}

function ProgressPanel({ health }) {
  const { loaded, extras, count } = toolState(health);
  return (
    <aside className="panel">
      <section className="panel-card">
        <h3>Progress</h3>
        <BackendStatus health={health} />
        <div className="tools-summary">
          <ProgressRing count={count} total={CORE_TOOLS.length} />
          <div>
            <div className="tools-head">Tools ({count}/{CORE_TOOLS.length})</div>
            <div className="tools-sub">{count === CORE_TOOLS.length ? "All tools live" : "Build each tool to unlock it"}</div>
          </div>
        </div>
        <ul className="tool-list">
          {CORE_TOOLS.map((t) => {
            const on = loaded.has(t.name);
            return (
              <li key={t.name} className={on ? "on" : ""}>
                <span className="tool-mark">{on ? "✓" : "○"}</span>
                <span className="tool-text"><code>{t.name}</code><small>{on ? t.label : `${t.label} · step ${t.step}`}</small></span>
              </li>
            );
          })}
          {extras.map((name) => (
            <li key={name} className="on">
              <span className="tool-mark">✓</span>
              <span className="tool-text"><code>{name}</code><small>Bonus tool</small></span>
            </li>
          ))}
        </ul>
        <p className="hint">A tool turns green once its registration is saved in <code>tool_registry.py</code>.</p>
      </section>
    </aside>
  );
}

// Compact version for small screens (the side panel is hidden there).
function ProgressStrip({ health }) {
  const { loaded, extras, count } = toolState(health);
  return (
    <div className="strip">
      <BackendStatus health={health} />
      <div className="strip-tools">
        <span>Tools ({count}/{CORE_TOOLS.length}):</span>
        {CORE_TOOLS.map((t) => (
          <span key={t.name} className={`pill ${loaded.has(t.name) ? "on" : ""}`}>
            {loaded.has(t.name) ? "✓" : "○"} {t.name}{!loaded.has(t.name) && ` (step ${t.step})`}
          </span>
        ))}
        {extras.map((name) => <span key={name} className="pill on">✓ {name}</span>)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat pieces
// ---------------------------------------------------------------------------
function Welcome({ onPick }) {
  return (
    <div className="welcome">
      <div className="hero">
        <div className="hero-orb"><Orb size={76} /></div>
        <h1>Hi, I'm <span className="grad-text">ShopBot</span></h1>
        <p>Powered by the Python tools <em>you</em> build.</p>
      </div>

      <div className="section-label">Try a question</div>
      <div className="examples">
        {EXAMPLES.map((e) => (
          <button key={e.text} className="example" onClick={() => onPick(e.text)}>
            <span className="example-emoji">{e.emoji}</span><span>{e.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Message({ m }) {
  if (m.role === "user") {
    return <div className="msg user"><div className="bubble">{m.content}</div></div>;
  }
  return (
    <div className="msg bot">
      <Orb />
      <div className="msg-body">
        {m.error ? (
          <div className="bubble error"><Icon name="alert" size={16} /><span>{m.content}</span></div>
        ) : (
          <>
            <div className="bubble"><Markdown text={m.content} /></div>
            <SafeBoundary><ToolCards calls={m.toolCalls} /></SafeBoundary>
            <ToolCalls calls={m.toolCalls} />
          </>
        )}
      </div>
    </div>
  );
}

function Thinking() {
  return (
    <div className="msg bot">
      <Orb busy />
      <div className="msg-body">
        <div className="bubble typing">
          <span className="typing-text">ShopBot is thinking</span>
          <span className="typing-dots"><span /><span /><span /></span>
        </div>
      </div>
    </div>
  );
}

function Composer({ onSend, disabled }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  // Grow the box with the text, up to about 5 lines.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  }, [text]);

  useEffect(() => {
    if (!disabled) ref.current?.focus();
  }, [disabled]);

  function submit(e) {
    if (e) e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  }

  return (
    <form className="composer" onSubmit={submit}>
      <span className="composer-icon"><Icon name="sparkles" size={18} /></span>
      <textarea
        ref={ref}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e); }}
        placeholder="Ask ShopBot about products, orders or discounts…"
        maxLength={1000}
        aria-label="Message"
      />
      <button type="submit" disabled={disabled || !text.trim()} aria-label="Send">
        <span>Send</span><Icon name="send" size={16} />
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// The app
// ---------------------------------------------------------------------------
function App() {
  const [messages, setMessages] = useState([]); // {role, content, toolCalls?, error?}
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const bottomRef = useRef(null);

  // Check the backend every few seconds, so the Tools list updates when tool_registry.py is saved.
  const loadHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setHealth({ ...(await response.json()), online: true });
    } catch {
      setHealth((prev) => ({ ...(prev || { tools: [] }), online: false }));
    }
  }, []);

  useEffect(() => {
    loadHealth();
    const id = setInterval(loadHealth, 4000);
    return () => clearInterval(id);
  }, [loadHealth]);

  // Keep the newest message in view, but leave the welcome page at the top.
  // (Braces matter: an effect must not return a value.)
  useEffect(() => {
    if (messages.length > 0 || loading) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function send(text) {
    const message = text.trim();
    if (!message || loading) return;

    // Earlier user/assistant messages, so the assistant remembers the conversation.
    const history = messages.filter((m) => !m.error).map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `Server error ${response.status}`);
      }
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply, toolCalls: data.tool_calls }]);
    } catch (err) {
      const text = err instanceof TypeError ? "Cannot reach the backend. Is the server running?" : err.message;
      setMessages((prev) => [...prev, { role: "assistant", content: text, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  const online = health?.online;

  return (
    <div className="layout">
      <div className="backdrop" aria-hidden="true"><span /><span /><span /></div>

      <header className="topbar">
        <div className="brand">
          <Orb size={38} busy={loading} />
          <div>
            <div className="brand-name">Demo Bazaar</div>
            <div className="brand-sub">ShopBot · AI shopping assistant</div>
          </div>
        </div>
        <div className="topbar-right">
          <span className={`conn ${online ? "on" : health ? "off" : ""}`}>
            <span className="dot" />{online ? "Connected" : health ? "Offline" : "Connecting…"}
          </span>
          <button className="clear" onClick={() => !loading && setMessages([])}><Icon name="trash" size={15} />Clear chat</button>
        </div>
      </header>

      <ProgressStrip health={health} />

      <div className="body">
        <main className="chat">
          <div className="scroll">
            <div className="thread">
              {messages.length === 0 ? <Welcome onPick={send} /> : messages.map((m, i) => <Message key={i} m={m} />)}
              {loading && <Thinking />}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="composer-wrap">
            <Composer onSend={send} disabled={loading} />
            <p className="footnote">Product, order and price facts come from your Python tools, not from the AI's memory.</p>
          </div>
        </main>

        <ProgressPanel health={health} />
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
