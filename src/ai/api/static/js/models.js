/* === models.js — Provider/Model modal CRUD === */

const providers = window.__providers || [];
const models = window.__models || [];

const providerModal = document.getElementById("providerModal");
const modelModal = document.getElementById("modelModal");
const providerForm = document.getElementById("providerForm");
const modelForm = document.getElementById("modelForm");

// Provider modal
document.getElementById("addProviderBtn").addEventListener("click", () => {
  document.getElementById("providerEditId").value = "";
  document.getElementById("providerModalTitle").textContent = "Add Provider";
  providerForm.provider_key.value = "";
  providerForm.provider_key.disabled = false;
  providerForm.display_name.value = "";
  providerForm.base_url.value = "";
  providerForm.api_key.value = "";
  providerForm.enabled.checked = true;
  providerModal.showModal();
});

window.editProvider = function (id) {
  const p = providers.find((x) => x.id === id);
  if (!p) return;
  document.getElementById("providerEditId").value = id;
  document.getElementById("providerModalTitle").textContent = "Edit Provider";
  providerForm.provider_key.value = p.provider_key;
  providerForm.provider_key.disabled = true;
  providerForm.display_name.value = p.display_name || "";
  providerForm.base_url.value = p.base_url || "";
  providerForm.api_key.value = "";
  providerForm.api_key.placeholder = p.has_api_key ? "configured (leave empty to keep)" : "";
  providerForm.enabled.checked = p.enabled;
  providerModal.showModal();
};

document.getElementById("providerCancel").addEventListener("click", () => providerModal.close());

providerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("providerEditId").value;
  const fd = new FormData(providerForm);
  const body = {
    provider_key: fd.get("provider_key"),
    display_name: fd.get("display_name") || null,
    base_url: fd.get("base_url") || null,
    api_key: fd.get("api_key") || null,
    enabled: providerForm.enabled.checked,
  };

  try {
    if (id) {
      await api("PUT", "/providers/" + id, {
        display_name: body.display_name,
        base_url: body.base_url,
        api_key: body.api_key,
        enabled: body.enabled,
      });
    } else {
      await api("POST", "/providers", body);
    }
    window.location.href = "/models?msg=" + encodeURIComponent(id ? "Provider updated" : "Provider created") + "&msg_type=success";
  } catch (err) {
    alert(err.message);
  }
});

// Model modal
document.getElementById("addModelBtn").addEventListener("click", () => {
  if (!providers.length) { alert("Please add a provider first."); return; }
  document.getElementById("modelEditId").value = "";
  document.getElementById("modelModalTitle").textContent = "Add Model";
  modelForm.model_key.value = "";
  modelForm.display_name.value = "";
  modelForm.context_window.value = "";
  modelForm.max_output_tokens.value = "";
  modelForm.input_price.value = "";
  modelForm.output_price.value = "";
  modelForm.supports_streaming.checked = true;
  modelForm.supports_tools.checked = false;
  modelForm.enabled.checked = true;
  modelModal.showModal();
});

window.editModel = function (id) {
  const m = models.find((x) => x.id === id);
  if (!m) return;
  document.getElementById("modelEditId").value = id;
  document.getElementById("modelModalTitle").textContent = "Edit Model";
  document.getElementById("modelProviderSelect").value = m.provider_id;
  modelForm.model_key.value = m.model_key;
  modelForm.display_name.value = m.display_name || "";
  modelForm.model_type.value = m.model_type;
  modelForm.request_type.value = m.request_type;
  modelForm.context_window.value = m.context_window || "";
  modelForm.max_output_tokens.value = m.max_output_tokens || "";
  modelForm.supports_streaming.checked = m.supports_streaming;
  modelForm.supports_tools.checked = m.supports_tools;
  modelForm.enabled.checked = m.enabled;
  modelModal.showModal();
};

document.getElementById("modelCancel").addEventListener("click", () => modelModal.close());

modelForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("modelEditId").value;
  const fd = new FormData(modelForm);
  const body = {
    provider_id: Number(fd.get("provider_id")),
    model_key: fd.get("model_key"),
    display_name: fd.get("display_name") || null,
    model_type: fd.get("model_type"),
    request_type: fd.get("request_type"),
    supports_streaming: modelForm.supports_streaming.checked,
    supports_tools: modelForm.supports_tools.checked,
    context_window: fd.get("context_window") ? Number(fd.get("context_window")) : null,
    max_output_tokens: fd.get("max_output_tokens") ? Number(fd.get("max_output_tokens")) : null,
    input_price: fd.get("input_price") ? Number(fd.get("input_price")) : null,
    output_price: fd.get("output_price") ? Number(fd.get("output_price")) : null,
    enabled: modelForm.enabled.checked,
  };

  try {
    if (id) {
      const updates = { ...body };
      delete updates.provider_id;
      delete updates.model_key;
      await api("PUT", "/models/" + id, updates);
    } else {
      await api("POST", "/models", body);
    }
    window.location.href = "/models?msg=" + encodeURIComponent(id ? "Model updated" : "Model created") + "&msg_type=success";
  } catch (err) {
    alert(err.message);
  }
});
