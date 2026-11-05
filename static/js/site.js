/* Toast pop-ups, cart badge, AJAX add-to-cart and the home announcement */

const TOAST_ICONS = {
  success: "bi-check-circle-fill",
  danger: "bi-exclamation-triangle-fill",
  warning: "bi-exclamation-circle-fill",
  info: "bi-info-circle-fill",
};

/**
 * Show a toast in the bottom-right corner.
 * level: "success" | "danger" | "warning" | "info"
 */
function showToast(message, level = "success") {
  const container = document.getElementById("toast-container");
  if (!container || !message) return;

  if (!TOAST_ICONS[level]) level = "info"; // unknown levels (e.g. "debug") look like info

  const toastEl = document.createElement("div");
  toastEl.className = `toast align-items-center text-bg-${level} border-0`;
  toastEl.setAttribute("role", level === "danger" ? "alert" : "status");
  toastEl.setAttribute("aria-live", level === "danger" ? "assertive" : "polite");
  toastEl.setAttribute("aria-atomic", "true");

  const row = document.createElement("div");
  row.className = "d-flex";

  const body = document.createElement("div");
  body.className = "toast-body";

  const icon = document.createElement("i");
  icon.className = `bi ${TOAST_ICONS[level]} me-2`;

  // textContent (not innerHTML) so messages can never inject HTML
  body.append(icon, document.createTextNode(message));

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "btn-close me-2 m-auto" + (level === "warning" ? "" : " btn-close-white");
  closeBtn.setAttribute("data-bs-dismiss", "toast");
  closeBtn.setAttribute("aria-label", "Close");

  row.append(body, closeBtn);
  toastEl.append(row);
  container.append(toastEl);

  const toast = new bootstrap.Toast(toastEl, { delay: level === "danger" ? 7000 : 4000 });
  toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
  toast.show();
}

/** Update every cart badge in the navbar (mobile and desktop). */
function updateCartBadge(count) {
  document.querySelectorAll("[data-cart-badge]").forEach((el) => {
    el.textContent = count;
    el.classList.toggle("d-none", !count);
  });
}

/** Turn the Django messages rendered in the page into toasts. */
function showServerMessages() {
  document.querySelectorAll("#server-messages [data-level]").forEach((el) => {
    showToast(el.textContent.trim(), el.dataset.level);
  });
}

/** "Add to Cart" without leaving the page. "Order Now" still submits normally. */
function setupAddToCart() {
  document.querySelectorAll("form.js-add-to-cart").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      const button = event.submitter;
      if (!button || button.value !== "add") return; // let "Order Now" submit normally

      event.preventDefault();

      const data = new FormData(form); // includes the CSRF token from the form
      data.set("action", "add");
      button.disabled = true;

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: data,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (!response.ok) {
          showToast("Sorry, this product could not be added to your cart.", "danger");
          return;
        }

        const result = await response.json();
        updateCartBadge(result.cart_count);
        showToast(result.message, "success");
      } catch (error) {
        showToast("Network problem. Please check your connection and try again.", "danger");
      } finally {
        button.disabled = false;
      }
    });
  });
}

/**
 * Home page announcement pop-up.
 *
 * How often it shows is chosen by the staff for each announcement:
 *   session - once per browser tab/visit (default)
 *   daily   - at most once every 24 hours
 *   always  - every time the home page loads
 *
 * "Don't show this again" hides it for good. The data-key changes whenever the
 * announcement is edited, so an edited announcement counts as new.
 */
function setupAnnouncement() {
  const modalEl = document.getElementById("announcementModal");
  if (!modalEl) return;

  const key = modalEl.dataset.key;
  const frequency = modalEl.dataset.frequency || "session";
  const hideKey = `announcement-hide-${key}`;
  const seenKey = `announcement-seen-${key}`;
  const lastKey = `announcement-last-${key}`;
  const ONE_DAY = 24 * 60 * 60 * 1000;

  try {
    if (localStorage.getItem(hideKey)) return; // visitor chose "Don't show again"

    if (frequency === "session" && sessionStorage.getItem(seenKey)) return;

    if (frequency === "daily") {
      const last = Number(localStorage.getItem(lastKey));
      if (last && Date.now() - last < ONE_DAY) return;
    }
  } catch (error) {
    // Storage blocked by the browser: just show the pop-up
  }

  const modal = new bootstrap.Modal(modalEl);

  // Remember that it was shown as soon as it opens, so clicking its button doesn't bring it back
  modalEl.addEventListener("show.bs.modal", () => {
    try {
      sessionStorage.setItem(seenKey, "1");
      localStorage.setItem(lastKey, String(Date.now()));
    } catch (error) { /* ignore */ }
  });

  modalEl.addEventListener("hidden.bs.modal", () => {
    const dontShow = modalEl.querySelector("#announcementDontShow");
    if (dontShow && dontShow.checked) {
      try { localStorage.setItem(hideKey, "1"); } catch (error) { /* ignore */ }
    }
  });

  setTimeout(() => modal.show(), 1200); // short delay so the page loads first
}

showServerMessages();
setupAddToCart();
setupAnnouncement();