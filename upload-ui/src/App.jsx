import React, { useCallback, useEffect, useRef, useState } from 'react';

const API = '/api';

function formatSize(n) {
  if (!n && n !== 0) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [drag, setDrag] = useState(false);
  const [status, setStatus] = useState('');
  const inputRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API}/documents`);
      if (r.ok) setDocs(await r.json());
    } catch (e) {
      // ignore transient errors during polling
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  const upload = async (file) => {
    if (!file) return;
    setStatus(`Uploading ${file.name}...`);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(`${API}/upload`, { method: 'POST', body: fd });
      if (!r.ok) {
        const err = await r.text();
        setStatus(`Upload failed: ${err}`);
        return;
      }
      setStatus(`Uploaded ${file.name}, processing...`);
      refresh();
    } catch (e) {
      setStatus(`Upload failed: ${e.message}`);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const files = Array.from(e.dataTransfer.files || []);
    files.forEach(upload);
  };

  const onDelete = async (id) => {
    if (!confirm('Delete this document?')) return;
    await fetch(`${API}/documents/${id}`, { method: 'DELETE' });
    refresh();
  };

  return (
    <div className="container">
      <nav>
        <a href="/">Upload</a>
        <a href="/query/">Query</a>
      </nav>
      <h1>Upload documents</h1>
      <div
        className={`dropzone ${drag ? 'drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div>Drag &amp; drop PDFs here, or click to select</div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => Array.from(e.target.files || []).forEach(upload)}
        />
      </div>
      {status && <div className="status">{status}</div>}

      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Status</th>
            <th>Chunks</th>
            <th>Uploaded</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {docs.length === 0 && (
            <tr><td colSpan="6" style={{ textAlign: 'center', color: '#888' }}>No documents yet</td></tr>
          )}
          {docs.map((d) => (
            <tr key={d.id}>
              <td>{d.filename}</td>
              <td>{formatSize(d.file_size)}</td>
              <td><span className={`badge ${d.status}`}>{d.status}</span>{d.error ? ` — ${d.error}` : ''}</td>
              <td>{d.chunks_count}</td>
              <td>{d.uploaded_at ? new Date(d.uploaded_at).toLocaleString() : ''}</td>
              <td><button className="danger" onClick={() => onDelete(d.id)}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
