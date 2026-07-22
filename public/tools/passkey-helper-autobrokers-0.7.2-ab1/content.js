/* AutoBrokers Passkey Helper 0.7.2-ab1
 * Runs only on https://web.whatsapp.com and talks only to the pinned
 * AutoBrokers Evolution Go origin. It never reads chats or requests secrets.
 */
(function () {
  'use strict';

  var API_ORIGIN = 'https://autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host';
  var STORAGE_KEY = '__autobrokers_wapk_ceremony__';
  var POLL_MS = 2000;
  var timer = null;
  var busy = false;
  var panel = null;

  function b64urlToBytes(value) {
    var raw = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
    while (raw.length % 4) raw += '=';
    var binary = atob(raw);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  function bytesToB64url(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = '';
    for (var i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function decodePayload(value) {
    try {
      var text = new TextDecoder().decode(b64urlToBytes(value));
      var decoded = JSON.parse(text);
      var supplied = new URL(String(decoded.b || ''));
      if (supplied.origin !== API_ORIGIN || (supplied.pathname && supplied.pathname !== '/')) return null;
      if (!/^[A-Za-z0-9_-]{20,256}$/.test(String(decoded.t || ''))) return null;
      return { t: String(decoded.t), b: API_ORIGIN };
    } catch (_) {
      return null;
    }
  }

  function ceremonyFromLocation() {
    var match = String(location.hash || '').match(/(?:#|&)wapk=([^&]+)/);
    var current = match ? decodePayload(match[1]) : null;
    if (current) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(current));
      history.replaceState(null, '', location.pathname + location.search);
      return current;
    }
    try {
      var saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
      return saved && saved.b === API_ORIGIN ? saved : null;
    } catch (_) {
      return null;
    }
  }

  function endpoint(ceremony, suffix) {
    return API_ORIGIN + '/passkey-ceremony/' + encodeURIComponent(ceremony.t) + (suffix || '');
  }

  async function request(ceremony, suffix, options) {
    var response = await fetch(endpoint(ceremony, suffix), options || { method: 'GET' });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) throw new Error(data.error || ('Falha HTTP ' + response.status));
    return data.data || data;
  }

  function publicKeyOptions(value) {
    return {
      challenge: b64urlToBytes(value.challenge),
      timeout: value.timeout || 60000,
      rpId: value.rpId || 'whatsapp.com',
      allowCredentials: (value.allowCredentials || []).map(function (credential) {
        return {
          type: credential.type || 'public-key',
          id: b64urlToBytes(credential.id),
          transports: credential.transports,
        };
      }),
      userVerification: value.userVerification || 'required',
    };
  }

  function assertionBody(credential) {
    var result = {
      id: credential.id,
      rawId: bytesToB64url(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON: bytesToB64url(credential.response.clientDataJSON),
        authenticatorData: bytesToB64url(credential.response.authenticatorData),
        signature: bytesToB64url(credential.response.signature),
      },
    };
    if (credential.response.userHandle && credential.response.userHandle.byteLength) {
      result.response.userHandle = bytesToB64url(credential.response.userHandle);
    }
    return result;
  }

  function createPanel() {
    if (panel) return panel;
    var root = document.createElement('section');
    root.id = 'autobrokers-passkey-helper';
    root.style.cssText = [
      'position:fixed', 'z-index:2147483647', 'top:18px', 'right:18px',
      'width:350px', 'max-width:calc(100vw - 36px)', 'box-sizing:border-box',
      'padding:18px', 'border:1px solid #25d366', 'border-radius:14px',
      'background:#111b21', 'color:#e9edef', 'box-shadow:0 12px 34px rgba(0,0,0,.35)',
      'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif',
    ].join(';');
    root.innerHTML = [
      '<div style="font-size:15px;font-weight:800">🔑 Confirmação de segurança</div>',
      '<p data-ab-desc style="font-size:13px;line-height:1.5;color:#aebac1"></p>',
      '<div data-ab-code style="display:none;margin:12px 0;padding:10px;border-radius:9px;',
      'background:#202c33;text-align:center;font:800 22px ui-monospace;letter-spacing:3px"></div>',
      '<button data-ab-action style="display:none;width:100%;padding:11px;border:0;border-radius:9px;',
      'background:#25d366;color:#04391f;font-weight:800;cursor:pointer"></button>',
      '<div data-ab-status style="margin-top:10px;font-size:12px;color:#aebac1"></div>',
      '<p style="margin:12px 0 0;font-size:11px;color:#8696a0">O AutoBrokers não solicita senha, PIN ou passkey.</p>',
    ].join('');
    document.body.appendChild(root);
    panel = {
      root: root,
      desc: root.querySelector('[data-ab-desc]'),
      code: root.querySelector('[data-ab-code]'),
      action: root.querySelector('[data-ab-action]'),
      status: root.querySelector('[data-ab-status]'),
    };
    return panel;
  }

  function render(description, status, actionLabel, action, code, isError) {
    var ui = createPanel();
    ui.desc.textContent = description || '';
    ui.status.textContent = status || '';
    ui.status.style.color = isError ? '#ff6b6b' : '#aebac1';
    ui.code.textContent = code || '';
    ui.code.style.display = code ? 'block' : 'none';
    ui.action.textContent = actionLabel || '';
    ui.action.style.display = actionLabel ? 'block' : 'none';
    ui.action.disabled = busy;
    ui.action.onclick = action || null;
  }

  function schedule(ceremony) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () { void poll(ceremony); }, POLL_MS);
  }

  async function authenticate(ceremony, options) {
    if (busy) return;
    busy = true;
    render('Confirme com a biometria ou bloqueio do seu dispositivo.', 'Aguardando confirmação…');
    try {
      var credential = await navigator.credentials.get({ publicKey: publicKeyOptions(options) });
      if (!credential) throw new Error('Confirmação cancelada.');
      await request(ceremony, '/response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assertionBody(credential)),
      });
      render('Assinatura recebida.', 'Concluindo o pareamento…');
    } catch (error) {
      render('A confirmação não terminou.', error.message || String(error), 'Tentar novamente',
        function () { void authenticate(ceremony, options); }, '', true);
    } finally {
      busy = false;
      schedule(ceremony);
    }
  }

  async function confirm(ceremony) {
    if (busy) return;
    busy = true;
    render('Confirmando o código mostrado…', 'Aguarde.');
    try {
      await request(ceremony, '/confirm', { method: 'POST' });
      render('Código confirmado.', 'Concluindo o pareamento…');
    } catch (error) {
      render('O código não foi confirmado.', error.message || String(error), 'Tentar novamente',
        function () { void confirm(ceremony); }, '', true);
    } finally {
      busy = false;
      schedule(ceremony);
    }
  }

  async function poll(ceremony) {
    if (busy) return schedule(ceremony);
    try {
      var state = await request(ceremony, '', { method: 'GET', headers: { Accept: 'application/json' } });
      if (state.error || state.stage === 'error') {
        render('A confirmação foi encerrada.', state.error || 'Tente gerar um novo QR.', '', null, '', true);
        return;
      }
      if (state.stage === 'challenge') {
        render('O WhatsApp pediu uma chave de acesso para vincular este dispositivo.', '',
          'Autenticar com chave de acesso', function () { void authenticate(ceremony, state.publicKey); });
      } else if (state.stage === 'confirmation') {
        render('Confira se o código é igual ao exibido no celular.', '', 'Confirmar código',
          function () { void confirm(ceremony); }, state.code || '');
      } else if (state.stage === 'confirmed') {
        sessionStorage.removeItem(STORAGE_KEY);
        render('Confirmação concluída.', 'Volte ao AutoBrokers.');
        return;
      } else {
        render('Assinatura enviada ao WhatsApp.', 'Aguardando a confirmação no dispositivo…');
      }
      schedule(ceremony);
    } catch (error) {
      render('Não foi possível consultar a confirmação.', error.message || String(error), '', null, '', true);
    }
  }

  var ceremony = ceremonyFromLocation();
  if (ceremony) void poll(ceremony);
})();
