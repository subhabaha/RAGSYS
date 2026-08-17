import React, { useState } from 'react';

const API = '/api';

export default function App() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const r = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      if (!r.ok) {
        setError(`Query failed: ${await r.text()}`);
      } else {
        setResult(await r.json());
      }
    } catch (e) {
      setError(`Query failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      ask();
    }
  };

  return (
    <div className="container">
      <nav>
        <a href="/">Upload</a>
        <a href="/query/">Query</a>
      </nav>
      <h1>Ask a question</h1>

      <div className="ask-card">
        <textarea
          rows="3"
          placeholder="Ask a question about your documents…  (⌘/Ctrl + Enter to send)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="ask-row">
          <button onClick={ask} disabled={loading || !question.trim()}>
            {loading ? (
              <>Thinking<span className="dots"><span></span><span></span><span></span></span></>
            ) : 'Ask'}
          </button>
        </div>
      </div>

      {error && <div className="answer error">{error}</div>}

      {result && (
        <>
          <h2>Answer</h2>
          <div className="answer">{result.answer}</div>

          <h2>Sources</h2>
          {result.sources.length === 0 && <div className="no-sources">No sources found.</div>}
          {result.sources.map((s, i) => (
            <div className="source" key={i} style={{ animationDelay: `${i * 80}ms` }}>
              <div className="meta">
                <strong>{s.document_name}</strong>
                <span>· page {s.page}</span>
                <span className="score">score {s.score.toFixed(3)}</span>
              </div>
              <div className="text">{s.text}</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
