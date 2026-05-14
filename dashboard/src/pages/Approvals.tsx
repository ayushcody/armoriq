import { useState, useEffect, useCallback } from 'react';
import { fetchApprovals, approveRequest, denyRequest } from '../api';

export default function Approvals() {
  const [approvals, setApprovals] = useState<any[]>([]);

  const load = useCallback(async () => {
    try { setApprovals(await fetchApprovals()); } catch {}
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load]);

  const handleApprove = async (id: string) => {
    await approveRequest(id);
    load();
  };

  const handleDeny = async (id: string) => {
    await denyRequest(id);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h2>Pending Approvals</h2>
        <p>Review and approve or deny tool execution requests (auto-refreshes every 3s)</p>
      </div>

      {approvals.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>No pending approvals. All clear!</p>
          </div>
        </div>
      ) : (
        approvals.map(a => (
          <div key={a.approval_id} className="approval-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div className="tool-name">{a.tool_name || 'Tool Call'}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  ID: {a.approval_id.slice(0, 12)}...
                </div>
              </div>
              <span className="badge pending">PENDING</span>
            </div>
            {a.arguments && (
              <div className="args-preview">
                {JSON.stringify(a.arguments, null, 2)}
              </div>
            )}
            <div className="actions">
              <button id={`approve-${a.approval_id}`} className="btn btn-success" onClick={() => handleApprove(a.approval_id)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
                Approve
              </button>
              <button id={`deny-${a.approval_id}`} className="btn btn-danger" onClick={() => handleDeny(a.approval_id)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                Deny
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
