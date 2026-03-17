const AUTH_TOKEN_STORAGE_KEY = "bavarianRoboTasteAuthToken";

const revealItems = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 }
  );

  revealItems.forEach((item) => {
    revealObserver.observe(item);
  });
} else {
  revealItems.forEach((item) => {
    item.classList.add("is-visible");
  });
}

const getAuthToken = () => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
const setAuthToken = (token) => window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
const clearAuthToken = () => window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);

const apiFetch = async (url, options = {}) => {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token && options.auth !== false) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body,
  });

  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const detail = payload?.detail || payload?.error || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return payload;
};

const profileLabel = (profile) => profile?.firstName || "Gast";

const renderAuthRail = (profile) => {
  const existingRail = document.querySelector(".auth-rail");
  if (existingRail) {
    existingRail.remove();
  }

  document.body.classList.add("has-auth-rail");

  const rail = document.createElement("div");
  rail.className = "auth-rail";

  if (profile) {
    rail.innerHTML = `
      <div class="auth-rail-card">
        <span class="auth-rail-name">Hallo, ${profileLabel(profile)}</span>
        <a class="auth-rail-link" href="/profile.html">Profil</a>
        <a class="auth-rail-link" href="/docs.html" target="_blank" rel="noopener noreferrer">Doku</a>
        <button class="auth-rail-button" type="button" data-auth-logout>Logout</button>
      </div>
    `;
  } else {
    rail.innerHTML = `
      <div class="auth-rail-card">
        <a class="auth-rail-link" href="/register.html">Registrierung</a>
        <a class="auth-rail-link is-primary" href="/login.html">Login</a>
        <a class="auth-rail-link" href="/docs.html" target="_blank" rel="noopener noreferrer">Doku</a>
      </div>
    `;
  }

  document.body.prepend(rail);

  const logoutButton = rail.querySelector("[data-auth-logout]");
  logoutButton?.addEventListener("click", async () => {
    try {
      await apiFetch("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch (_) {
      // ignore logout API errors and clear client state anyway
    }

    clearAuthToken();
    renderAuthRail(null);
    if (window.location.pathname.endsWith("/profile.html") || window.location.pathname.endsWith("profile.html")) {
      window.location.href = "/login.html";
    }
  });
};

const loadCurrentProfile = async () => {
  const token = getAuthToken();
  if (!token) {
    renderAuthRail(null);
    return null;
  }

  try {
    const payload = await apiFetch("/api/auth/me");
    renderAuthRail(payload.guestProfile);
    return payload.guestProfile;
  } catch (_) {
    clearAuthToken();
    renderAuthRail(null);
    return null;
  }
};

const authReady = loadCurrentProfile();

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character] || character;
  });

const productPageRoot = document.querySelector("[data-product-page]");

const buildProductCard = (product, page) => {
  const classes = ["menu-item"];
  if (page === "drinks") {
    classes.push("drink-item");
  }
  if (product.featured) {
    classes.push("menu-item-featured");
  }

  const imageMarkup = product.imagePath
    ? `<img class="menu-item-media" src="${escapeHtml(product.imagePath)}" alt="${escapeHtml(product.title)}" />`
    : "";
  const textClass = page === "drinks" ? "drink-name" : "";
  const descriptionClass = page === "drinks" ? "drink-description" : "";

  return `
    <article
      class="${classes.join(" ")} dish-trigger"
      tabindex="0"
      role="button"
      data-dish-category="${escapeHtml(product.category)}"
      data-dish-title="${escapeHtml(product.title)}"
      data-dish-price="${escapeHtml(product.price)}"
      data-dish-copy="${escapeHtml(product.ingredients)}"
      data-dish-image="${escapeHtml(product.imagePath)}"
      data-dish-quote="${escapeHtml(product.quote.text)}"
      data-dish-author="${escapeHtml(product.quote.author)}"
      data-dish-special-heading-1="${escapeHtml(product.specialSections[0]?.heading || "")}"
      data-dish-special-content-1="${escapeHtml(product.specialSections[0]?.content || "")}"
      data-dish-special-heading-2="${escapeHtml(product.specialSections[1]?.heading || "")}"
      data-dish-special-content-2="${escapeHtml(product.specialSections[1]?.content || "")}"
    >
      ${imageMarkup}
      <div>
        <h3 class="${textClass}">${escapeHtml(product.title)}</h3>
        <p class="${descriptionClass}">${escapeHtml(product.teaser)}</p>
      </div>
      <span class="price-tag">${escapeHtml(product.price)}</span>
    </article>
  `;
};

const renderProductPage = async () => {
  if (!productPageRoot) {
    return;
  }

  const page = productPageRoot.dataset.productPage || "";
  try {
    const payload = await apiFetch(`/api/products?page=${encodeURIComponent(page)}`, { auth: false });
    productPageRoot.innerHTML = payload.sections
      .map(
        (section) => `
          <section class="section menu-section reveal">
            <div class="section-heading">
              <p class="section-tag">${escapeHtml(section.tag)}</p>
              <h2>${escapeHtml(section.title)}</h2>
            </div>
            <div class="menu-list">
              ${section.products.map((product) => buildProductCard(product, payload.page)).join("")}
            </div>
          </section>
        `
      )
      .join("");

    const dynamicRevealItems = productPageRoot.querySelectorAll(".reveal");
    dynamicRevealItems.forEach((item) => item.classList.add("is-visible"));
    bindDishTriggers();
  } catch (error) {
    productPageRoot.innerHTML = `
      <section class="section menu-section reveal is-visible">
        <div class="section-heading">
          <p class="section-tag">Produktdaten</p>
          <h2>Die Produktdaten konnten gerade nicht geladen werden.</h2>
        </div>
        <p>${escapeHtml(error.message)}</p>
      </section>
    `;
  }
};

const dishModal = document.querySelector("#dish-modal");
let bindDishTriggers = () => {};

if (dishModal) {
  const modalCategory = dishModal.querySelector("#dish-modal-category");
  const modalTitle = dishModal.querySelector("#dish-modal-title");
  const modalPrice = dishModal.querySelector("#dish-modal-price");
  const modalCopy = dishModal.querySelector("#dish-modal-copy");
  const modalOrigin = dishModal.querySelector("#dish-modal-origin");
  const modalQuality = dishModal.querySelector("#dish-modal-quality");
  const modalSpecialHeading1 = dishModal.querySelector("#dish-modal-special-heading-1");
  const modalSpecialHeading2 = dishModal.querySelector("#dish-modal-special-heading-2");
  const modalQuote = dishModal.querySelector("#dish-modal-quote");
  const modalAuthor = dishModal.querySelector("#dish-modal-author");
  const modalImageWrap = dishModal.querySelector(".dish-modal-image-wrap");
  const modalImage = dishModal.querySelector("#dish-modal-image");
  const imageOpenButton = dishModal.querySelector("[data-dish-image-open]");
  const closeButtons = dishModal.querySelectorAll("[data-dish-close]");
  const imageLightbox = document.querySelector("#image-lightbox");
  const imageLightboxImage = imageLightbox?.querySelector("#image-lightbox-image");
  const imageCloseButtons = imageLightbox?.querySelectorAll("[data-image-close]");

  const openDishModal = (trigger) => {
    modalCategory.textContent = trigger.dataset.dishCategory || "Gericht";
    modalTitle.textContent = trigger.dataset.dishTitle || "Gericht";
    modalPrice.textContent = trigger.dataset.dishPrice || "";
    modalCopy.textContent = trigger.dataset.dishCopy || "";
    modalOrigin.textContent = trigger.dataset.dishSpecialContent1 || "";
    modalQuality.textContent = trigger.dataset.dishSpecialContent2 || "";
    if (modalSpecialHeading1) {
      modalSpecialHeading1.textContent = trigger.dataset.dishSpecialHeading1 || "Details";
    }
    if (modalSpecialHeading2) {
      modalSpecialHeading2.textContent = trigger.dataset.dishSpecialHeading2 || "Mehr";
    }
    modalQuote.textContent = `"${trigger.dataset.dishQuote || ""}"`;
    modalAuthor.textContent = trigger.dataset.dishAuthor || "";

    if (modalImageWrap && modalImage) {
      const dishImage = trigger.dataset.dishImage || "";
      if (dishImage) {
        modalImage.src = dishImage;
        modalImage.alt = trigger.dataset.dishTitle || "Gericht";
        modalImageWrap.hidden = false;
      } else {
        modalImage.removeAttribute("src");
        modalImage.alt = "";
        modalImageWrap.hidden = true;
      }
    }

    dishModal.hidden = false;
    document.body.style.overflow = "hidden";
  };

  const closeDishModal = () => {
    dishModal.hidden = true;
    document.body.style.overflow = "";
  };

  const openImageLightbox = () => {
    if (!imageLightbox || !imageLightboxImage || !modalImage?.getAttribute("src")) {
      return;
    }

    imageLightboxImage.src = modalImage.src;
    imageLightboxImage.alt = modalImage.alt;
    imageLightbox.hidden = false;
  };

  const closeImageLightbox = () => {
    if (!imageLightbox || !imageLightboxImage) {
      return;
    }

    imageLightbox.hidden = true;
    imageLightboxImage.removeAttribute("src");
    imageLightboxImage.alt = "";
  };

  bindDishTriggers = () => {
    const dishTriggers = document.querySelectorAll(".dish-trigger");
    dishTriggers.forEach((trigger) => {
      if (trigger.dataset.dishBound === "true") {
        return;
      }

      trigger.dataset.dishBound = "true";
      trigger.addEventListener("click", () => openDishModal(trigger));
      trigger.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDishModal(trigger);
        }
      });
    });
  };

  bindDishTriggers();

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeDishModal);
  });

  if (imageOpenButton) {
    imageOpenButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openImageLightbox();
    });
  }

  imageCloseButtons?.forEach((button) => {
    button.addEventListener("click", closeImageLightbox);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && imageLightbox && !imageLightbox.hidden) {
      closeImageLightbox();
      return;
    }

    if (event.key === "Escape" && !dishModal.hidden) {
      closeDishModal();
    }
  });
}

renderProductPage();

const docsTabs = Array.from(document.querySelectorAll("[data-docs-tab]"));
const docsPanels = Array.from(document.querySelectorAll("[data-docs-panel]"));

if (docsTabs.length > 0 && docsPanels.length > 0) {
  const activateDocsSection = (sectionId, updateUrl = true) => {
    const nextId = sectionId || docsPanels[0]?.id || "";

    docsTabs.forEach((tab) => {
      const isActive = tab.getAttribute("aria-controls") === nextId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });

    docsPanels.forEach((panel) => {
      const isActive = panel.id === nextId;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });

    if (updateUrl && nextId) {
      window.history.replaceState(null, "", `#${nextId}`);
    }
  };

  docsTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      activateDocsSection(tab.getAttribute("aria-controls") || "");
    });
  });

  const initialId = window.location.hash.replace("#", "") || docsPanels[0]?.id || "";
  activateDocsSection(initialId, Boolean(window.location.hash));
}

const registrationApp = document.querySelector("[data-registration-app]");

if (registrationApp) {
  const stages = registrationApp.querySelectorAll("[data-stage]");
  const statusBox = registrationApp.querySelector("[data-registration-status]");
  const indicators = registrationApp.querySelectorAll("[data-step-indicator]");
  const registrationForm = registrationApp.querySelector("[data-registration-form]");
  const verificationForm = registrationApp.querySelector("[data-verification-form]");
  const passwordForm = registrationApp.querySelector("[data-password-form]");
  const resendButton = registrationApp.querySelector("[data-resend-code]");
  const codePreview = registrationApp.querySelector("[data-code-preview]");
  const successSummary = registrationApp.querySelector("[data-success-summary]");

  const state = {
    step: 1,
    profile: null,
    verified: false,
  };

  const showStatus = (message, kind = "success") => {
    if (!statusBox) {
      return;
    }

    statusBox.textContent = message;
    statusBox.className = `registration-status is-visible is-${kind}`;
  };

  const clearStatus = () => {
    if (!statusBox) {
      return;
    }

    statusBox.textContent = "";
    statusBox.className = "registration-status";
  };

  const setStep = (step) => {
    state.step = step;

    stages.forEach((stage) => {
      const isVisible = Number(stage.dataset.stage) === step;
      stage.hidden = !isVisible;
      stage.classList.toggle("is-active", isVisible);
    });

    indicators.forEach((indicator) => {
      const indicatorStep = Number(indicator.dataset.stepIndicator);
      indicator.classList.toggle("is-active", indicatorStep === step);
    });
  };

  const getValue = (form, name) => form?.elements?.namedItem(name)?.value?.trim() || "";

  registrationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const firstName = getValue(registrationForm, "firstName");
    const email = getValue(registrationForm, "email");
    const phone = getValue(registrationForm, "phone");

    if (!firstName || !email) {
      showStatus("Bitte Vorname und E-Mail ausfüllen.", "error");
      return;
    }

    state.profile = { firstName, email, phone };
    state.verified = false;

    try {
      await apiFetch("/api/register/request-code", {
        method: "POST",
        body: JSON.stringify({
          firstName,
          email,
          phone,
        }),
        auth: false,
      });

      if (codePreview) {
        codePreview.hidden = false;
        codePreview.textContent = `Wir haben einen Bestätigungscode an ${email} gesendet.`;
      }

      setStep(2);
      showStatus("Der Bestätigungscode wurde per E-Mail versendet.", "success");
    } catch (error) {
      showStatus(`Der Bestätigungscode konnte nicht gesendet werden: ${error.message}`, "error");
    }
  });

  verificationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const code = getValue(verificationForm, "verificationCode").replace(/\s+/g, "");

    if (!code) {
      showStatus("Bitte den 6-stelligen Code eingeben.", "error");
      return;
    }

    if (!state.profile?.email) {
      showStatus("Bitte starte die Registrierung erneut.", "error");
      setStep(1);
      return;
    }

    try {
      await apiFetch("/api/register/verify-code", {
        method: "POST",
        body: JSON.stringify({
          email: state.profile.email,
          verificationCode: code,
        }),
        auth: false,
      });

      state.verified = true;
      setStep(3);
      showStatus("Code bestätigt. Jetzt kannst du dein Passwort setzen.", "success");
    } catch (error) {
      showStatus(`Die Code-Prüfung ist fehlgeschlagen: ${error.message}`, "error");
    }
  });

  resendButton?.addEventListener("click", async () => {
    clearStatus();

    if (!state.profile?.email) {
      showStatus("Bitte zuerst die Registrierungsdaten erfassen.", "error");
      setStep(1);
      return;
    }

    try {
      await apiFetch("/api/register/request-code", {
        method: "POST",
        body: JSON.stringify(state.profile),
        auth: false,
      });

      state.verified = false;
      if (codePreview) {
        codePreview.hidden = false;
        codePreview.textContent = `Wir haben einen neuen Bestätigungscode an ${state.profile.email} gesendet.`;
      }

      showStatus("Ein neuer Bestätigungscode wurde per E-Mail versendet.", "success");
    } catch (error) {
      showStatus(`Der neue Bestätigungscode konnte nicht gesendet werden: ${error.message}`, "error");
    }
  });

  passwordForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const password = getValue(passwordForm, "password");
    const passwordConfirm = getValue(passwordForm, "passwordConfirm");

    if (password.length < 8) {
      showStatus("Das Passwort muss mindestens 8 Zeichen lang sein.", "error");
      return;
    }

    if (password !== passwordConfirm) {
      showStatus("Die Passwörter stimmen nicht überein.", "error");
      return;
    }

    if (!state.profile?.email || !state.verified) {
      showStatus("Bitte bestätige zuerst deinen E-Mail-Code.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/register/complete", {
        method: "POST",
        body: JSON.stringify({
          email: state.profile.email,
          password,
          passwordConfirm,
        }),
        auth: false,
      });

      setAuthToken(result.token);
      renderAuthRail(result.guestProfile);

      if (successSummary) {
        successSummary.innerHTML = `
          <p><strong>Vorname</strong><br />${result.guestProfile.firstName}</p>
          <p><strong>E-Mail</strong><br />${result.guestProfile.email}</p>
          <p><strong>Telefon</strong><br />${result.guestProfile.phone || "nicht angegeben"}</p>
        `;
      }

      stages.forEach((stage) => {
        const isFinal = Number(stage.dataset.stage) === 4;
        stage.hidden = !isFinal;
        stage.classList.toggle("is-active", isFinal);
      });

      indicators.forEach((indicator) => {
        indicator.classList.remove("is-active");
      });

      showStatus("Die Registrierung wurde erfolgreich abgeschlossen.", "success");
    } catch (error) {
      showStatus(`Die Registrierung konnte nicht abgeschlossen werden: ${error.message}`, "error");
    }
  });
}

const contactForm = document.querySelector("[data-contact-form]");

if (contactForm) {
  const submitButton = contactForm.querySelector("[data-contact-submit]");
  const feedbackBox = contactForm.querySelector("[data-contact-feedback]");
  const requiredFields = Array.from(contactForm.querySelectorAll("[required]"));

  const setContactFeedback = (message, kind = "success") => {
    if (!feedbackBox) {
      return;
    }

    feedbackBox.textContent = message;
    feedbackBox.className = `form-feedback field-span is-visible is-${kind}`;
  };

  const clearContactFeedback = () => {
    if (!feedbackBox) {
      return;
    }

    feedbackBox.textContent = "";
    feedbackBox.className = "form-feedback field-span";
  };

  const isContactFormComplete = () => requiredFields.every((field) => field.value.trim().length > 0);
  const getSelectedTopic = () => contactForm.querySelector('input[name="topic"]:checked')?.value?.trim() || "";

  const updateContactSubmitState = () => {
    if (submitButton) {
      submitButton.disabled = !(isContactFormComplete() && getSelectedTopic());
    }
  };

  requiredFields.forEach((field) => {
    field.addEventListener("input", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });

    field.addEventListener("change", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });
  });

  contactForm.querySelectorAll('input[name="topic"]').forEach((field) => {
    field.addEventListener("change", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });
  });

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearContactFeedback();

    if (!(isContactFormComplete() && getSelectedTopic())) {
      setContactFeedback("Bitte alle Pflichtfelder ausfüllen, bevor du die Nachricht sendest.", "error");
      updateContactSubmitState();
      return;
    }

    const payload = {
      name: contactForm.elements.namedItem("name")?.value.trim() || "",
      email: contactForm.elements.namedItem("email")?.value.trim() || "",
      topic: getSelectedTopic(),
      message: contactForm.elements.namedItem("message")?.value.trim() || "",
      createdAt: new Date().toISOString(),
    };

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {
      await apiFetch("/api/contact", {
        method: "POST",
        body: JSON.stringify(payload),
        auth: false,
      });

      contactForm.reset();
      const defaultTopic = contactForm.querySelector('input[name="topic"][value="Allgemeine Anfrage"]');
      if (defaultTopic) {
        defaultTopic.checked = true;
      }

      setContactFeedback("Die Nachricht wurde erfolgreich versendet. Wir haben dir außerdem eine Bestätigung per E-Mail geschickt.", "success");
    } catch (error) {
      setContactFeedback(`Der Mailversand ist fehlgeschlagen: ${error.message}`, "error");
    } finally {
      updateContactSubmitState();
    }
  });

  updateContactSubmitState();
}

const loginForm = document.querySelector("[data-login-form]");

if (loginForm) {
  const statusBox = document.querySelector("[data-login-status]");

  const showLoginStatus = (message, kind = "success") => {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.className = `registration-status is-visible is-${kind}`;
  };

  authReady.then((profile) => {
    if (profile) {
      window.location.href = "/profile.html";
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = loginForm.elements.namedItem("email")?.value.trim() || "";
    const password = loginForm.elements.namedItem("password")?.value.trim() || "";

    if (!email || !password) {
      showLoginStatus("Bitte gib deine E-Mail-Adresse und dein Passwort ein.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        auth: false,
      });

      setAuthToken(result.token);
      renderAuthRail(result.guestProfile);
      window.location.href = "/profile.html";
    } catch (error) {
      showLoginStatus(`Der Login ist fehlgeschlagen: ${error.message}`, "error");
    }
  });
}

const profileForm = document.querySelector("[data-profile-form]");
const changePasswordForm = document.querySelector("[data-change-password-form]");

if (profileForm && changePasswordForm) {
  const profileStatus = document.querySelector("[data-profile-status]");
  const passwordStatus = document.querySelector("[data-password-status]");

  const setBoxStatus = (box, message, kind = "success") => {
    if (!box) {
      return;
    }
    box.textContent = message;
    box.className = `registration-status is-visible is-${kind}`;
  };

  const fillProfileForm = (profile) => {
    profileForm.elements.namedItem("firstName").value = profile.firstName || "";
    profileForm.elements.namedItem("email").value = profile.email || "";
    profileForm.elements.namedItem("phone").value = profile.phone || "";
  };

  authReady.then((profile) => {
    if (!profile) {
      window.location.href = "/login.html";
      return;
    }

    fillProfileForm(profile);
  });

  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const firstName = profileForm.elements.namedItem("firstName")?.value.trim() || "";
    const phone = profileForm.elements.namedItem("phone")?.value.trim() || "";

    if (!firstName) {
      setBoxStatus(profileStatus, "Bitte gib einen Vornamen an.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/profile", {
        method: "POST",
        body: JSON.stringify({ firstName, phone }),
      });

      fillProfileForm(result.guestProfile);
      renderAuthRail(result.guestProfile);
      setBoxStatus(profileStatus, "Dein Profil wurde erfolgreich gespeichert.", "success");
    } catch (error) {
      setBoxStatus(profileStatus, `Das Profil konnte nicht gespeichert werden: ${error.message}`, "error");
    }
  });

  changePasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const currentPassword = changePasswordForm.elements.namedItem("currentPassword")?.value.trim() || "";
    const newPassword = changePasswordForm.elements.namedItem("newPassword")?.value.trim() || "";
    const newPasswordConfirm = changePasswordForm.elements.namedItem("newPasswordConfirm")?.value.trim() || "";

    if (!currentPassword || !newPassword || !newPasswordConfirm) {
      setBoxStatus(passwordStatus, "Bitte fülle alle Passwort-Felder aus.", "error");
      return;
    }

    try {
      await apiFetch("/api/profile/change-password", {
        method: "POST",
        body: JSON.stringify({
          currentPassword,
          newPassword,
          newPasswordConfirm,
        }),
      });

      changePasswordForm.reset();
      setBoxStatus(passwordStatus, "Dein Passwort wurde erfolgreich geändert.", "success");
    } catch (error) {
      setBoxStatus(passwordStatus, `Das Passwort konnte nicht geändert werden: ${error.message}`, "error");
    }
  });
}
