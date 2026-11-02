"use strict";
/* Local user-initiated voice preview. No agent runtime, accounts or network. */
(() => {
  const byId = id => document.getElementById(id);
  const profiles = Object.freeze({
    architect: {
      style: "Calm · professional", language: "English", locale: "en-US",
      sample: "Good evening. I have reviewed the mission proposal. The next action requires verified approval before execution."
    },
    researcher: {
      style: "Warm · professional", language: "Russian", locale: "ru-RU",
      sample: "Добрый вечер. Я подготовил краткий обзор данных. Источники и результаты проверки доступны для независимой оценки."
    },
    guardian: {
      style: "Technical · precise", language: "English", locale: "en-GB",
      sample: "Guardian status: verification is required. No external action will proceed without a valid authorization."
    }
  });
  const avatar = byId("avatar");
  const status = byId("speech-status");
  const avatarState = byId("avatar-state");
  const select = byId("agent-select");
  const textArea = byId("utterance");
  const voiceSelect = byId("voice-select");
  const engine = "speechSynthesis" in window ? window.speechSynthesis : null;
  let voices = [];
  let currentUtterance = null;

  function setStatus(message, speaking) {
    status.textContent = message;
    avatarState.textContent = speaking ? "SPEAKING / LOCAL VOICE" : "IDLE / LOCAL DEMO";
    avatar.classList.toggle("speaking", Boolean(speaking));
  }

  function stopSpeech() {
    if (engine) engine.cancel();
    currentUtterance = null;
    setStatus("Voice stopped. No background audio is active.", false);
  }

  function renderVoices() {
    voiceSelect.replaceChildren();
    if (!engine) {
      const option = new Option("Speech synthesis not available", "");
      voiceSelect.add(option);
      voiceSelect.disabled = true;
      byId("speak").disabled = true;
      setStatus("This browser does not provide speech synthesis. Text remains available.", false);
      return;
    }
    voices = engine.getVoices();
    const currentLanguage = profiles[select.value].locale.split("-")[0];
    const options = voices.filter(v => v.lang.toLowerCase().startsWith(currentLanguage.toLowerCase()));
    if (!options.length) {
      voiceSelect.add(new Option("System default voice", "default"));
    } else {
      options.forEach(v => voiceSelect.add(new Option(
        v.name + " (" + v.lang + (v.localService ? ", local" : "") + ")",
        v.voiceURI
      )));
    }
    voiceSelect.disabled = false;
  }

  select.addEventListener("change", () => {
    stopSpeech();
    const p = profiles[select.value];
    if (!p) return;
    byId("persona").textContent = p.style;
    byId("language").textContent = p.language;
    textArea.value = p.sample;
    renderVoices();
  });

  byId("speak").addEventListener("click", () => {
    if (!engine || !("SpeechSynthesisUtterance" in window)) {
      setStatus("Speech synthesis is not available. Use the written transcript.", false);
      return;
    }
    const value = textArea.value.trim();
    if (!value || value.length > 500) {
      setStatus("Enter no more than 500 characters of preview text.", false);
      return;
    }
    stopSpeech();
    const utterance = new SpeechSynthesisUtterance(value);
    const p = profiles[select.value];
    utterance.lang = p.locale;
    utterance.rate = p.style.startsWith("Technical") ? 0.93 : 0.98;
    utterance.pitch = 0.95;
    const chosen = voices.find(v => v.voiceURI === voiceSelect.value);
    if (chosen) utterance.voice = chosen;
    currentUtterance = utterance;
    utterance.onstart = () => { if (currentUtterance === utterance) setStatus("Speaking with a device-provided voice.", true); };
    utterance.onend = () => { if (currentUtterance === utterance) { currentUtterance = null; setStatus("Preview finished.", false); } };
    utterance.onerror = () => { if (currentUtterance === utterance) { currentUtterance = null; setStatus("Voice unavailable on this device. Text preview remains available.", false); } };
    engine.speak(utterance);
  });

  byId("stop").addEventListener("click", stopSpeech);
  document.addEventListener("visibilitychange", () => { if (document.hidden) stopSpeech(); });
  window.addEventListener("pagehide", stopSpeech);
  if (engine) {
    if (typeof engine.addEventListener === "function") engine.addEventListener("voiceschanged", renderVoices);
    renderVoices();
  } else renderVoices();
})();