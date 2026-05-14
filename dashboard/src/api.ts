const API = import.meta.env.VITE_API_URL || '';

export async function fetchHealth() {
  const res = await fetch(`${API}/api/health`);
  return res.json();
}

export async function fetchRules() {
  const res = await fetch(`${API}/api/rules`);
  return res.json();
}

export async function createRule(rule: any) {
  const res = await fetch(`${API}/api/rules`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  return res.json();
}

export async function deleteRule(id: string) {
  const res = await fetch(`${API}/api/rules/${id}`, { method: 'DELETE' });
  return res.json();
}

export async function toggleRule(id: string, enabled: boolean) {
  const res = await fetch(`${API}/api/rules/${id}/toggle`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  return res.json();
}

export async function fetchLogs(params?: { limit?: number; offset?: number; tool_name?: string; action?: string }) {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set('limit', String(params.limit));
  if (params?.offset) sp.set('offset', String(params.offset));
  if (params?.tool_name) sp.set('tool_name', params.tool_name);
  if (params?.action) sp.set('action', params.action);
  const res = await fetch(`${API}/api/logs?${sp}`);
  return res.json();
}

export async function fetchApprovals() {
  const res = await fetch(`${API}/api/approvals`);
  return res.json();
}

export async function approveRequest(id: string) {
  const res = await fetch(`${API}/api/approvals/${id}/approve`, { method: 'POST' });
  return res.json();
}

export async function denyRequest(id: string) {
  const res = await fetch(`${API}/api/approvals/${id}/deny`, { method: 'POST' });
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API}/api/stats`);
  return res.json();
}

export async function sendChat(message: string, conversationId?: string) {
  const res = await fetch(`${API}/api/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  return res.json();
}

export function getWSUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws/logs`;
}
