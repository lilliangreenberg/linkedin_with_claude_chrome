/**
 * LinkedIn Profile Scraper - Content Script
 *
 * Extracts profile/company data directly from the LinkedIn page DOM.
 * Communicates with the background script via chrome.runtime messages.
 */

function extractProfileData() {
  const data = {};

  // --- Person Profile ---
  const nameEl =
    document.querySelector("h1.text-heading-xlarge") ||
    document.querySelector("h1.inline.t-24") ||
    document.querySelector(".pv-top-card--list h1") ||
    document.querySelector("h1");

  if (nameEl) {
    data.name = nameEl.innerText.trim();
  }

  // Headline
  const headlineEl =
    document.querySelector("div.text-body-medium.break-words") ||
    document.querySelector(".pv-top-card--list .text-body-medium") ||
    document.querySelector(".ph5 .mt2 .text-body-medium");
  if (headlineEl) {
    data.headline = headlineEl.innerText.trim();
  }

  // Location
  const locationEl =
    document.querySelector("span.text-body-small.inline.t-black--light.break-words") ||
    document.querySelector(".pv-top-card--list-bullet .text-body-small");
  if (locationEl) {
    data.location = locationEl.innerText.trim();
  }

  // About / Summary
  const aboutSection =
    document.querySelector("#about ~ div .inline-show-more-text") ||
    document.querySelector("#about + .display-flex .inline-show-more-text") ||
    document.querySelector("section.pv-about-section .pv-about__summary-text");
  if (aboutSection) {
    data.about = aboutSection.innerText.trim();
  }

  // Connection / follower count
  const connectionsEl =
    document.querySelector("span.t-bold:not(.text-heading-xlarge)") ||
    document.querySelector(".pv-top-card--list-bullet li:last-child span");
  if (connectionsEl) {
    const text = connectionsEl.innerText.trim();
    if (/\d/.test(text) && (text.includes("connection") || text.includes("follower") || /^\d/.test(text))) {
      data.connections = text;
    }
  }

  // Profile photo URL
  const profileImg =
    document.querySelector("img.pv-top-card-profile-picture__image--show") ||
    document.querySelector("img.pv-top-card-profile-picture__image") ||
    document.querySelector(".pv-top-card--photo-resize img") ||
    document.querySelector("img.presence-entity__image");
  if (profileImg) {
    const src = profileImg.getAttribute("src");
    if (src && src.startsWith("http")) {
      data.profile_image_url = src;
    }
  }

  // Experience entries
  const experienceSection = document.getElementById("experience");
  if (experienceSection) {
    const container = experienceSection.closest("section");
    if (container) {
      const entries = container.querySelectorAll("li.artdeco-list__item");
      const experience = [];
      entries.forEach((entry) => {
        const titleEl = entry.querySelector("span.mr1.t-bold span") ||
                        entry.querySelector("span.t-bold span") ||
                        entry.querySelector(".t-bold");
        const companyEl = entry.querySelector("span.t-14.t-normal span") ||
                          entry.querySelector(".t-14.t-normal");
        const datesEl = entry.querySelector("span.t-14.t-normal.t-black--light span") ||
                        entry.querySelector(".t-black--light span");
        // Company LinkedIn URL from within this entry's <li>
        const companyLink = entry.querySelector('a[href*="/company/"]');

        const exp = {};
        if (titleEl) exp.title = titleEl.innerText.trim();
        if (companyEl) exp.company = companyEl.innerText.trim();
        if (datesEl) exp.dates = datesEl.innerText.trim();
        if (companyLink) {
          exp.company_linkedin_url = companyLink.href.split("?")[0].replace(/\/+$/, "");
        }
        if (Object.keys(exp).length > 0) {
          experience.push(exp);
        }
      });
      if (experience.length > 0) {
        data.experience = experience;
      }
    }
  }

  // Education entries
  const educationSection = document.getElementById("education");
  if (educationSection) {
    const container = educationSection.closest("section");
    if (container) {
      const entries = container.querySelectorAll("li.artdeco-list__item");
      const education = [];
      entries.forEach((entry) => {
        const schoolEl = entry.querySelector("span.mr1.hoverable-link-text.t-bold span") ||
                         entry.querySelector("span.t-bold span") ||
                         entry.querySelector(".t-bold");
        const degreeEl = entry.querySelector("span.t-14.t-normal span") ||
                         entry.querySelector(".t-14.t-normal");
        const edu = {};
        if (schoolEl) edu.school = schoolEl.innerText.trim();
        if (degreeEl) edu.degree = degreeEl.innerText.trim();
        if (Object.keys(edu).length > 0) {
          education.push(edu);
        }
      });
      if (education.length > 0) {
        data.education = education;
      }
    }
  }

  // --- Company Page ---
  const companyNameEl =
    document.querySelector("h1.org-top-card-summary__title span") ||
    document.querySelector("h1.org-top-card-summary__title");
  if (companyNameEl && !data.name) {
    data.name = companyNameEl.innerText.trim();
    data.type = "company";
  }

  const companyIndustryEl =
    document.querySelector(".org-top-card-summary-info-list__info-item");
  if (companyIndustryEl) {
    data.industry = companyIndustryEl.innerText.trim();
  }

  // Company tagline
  const companyTagline =
    document.querySelector("h4.org-top-card-summary__tagline") ||
    document.querySelector("p.org-top-card-summary__tagline");
  if (companyTagline) {
    data.tagline = companyTagline.innerText.trim();
  }

  // Company logo URL
  const companyLogo =
    document.querySelector("img.org-top-card-primary-content__logo") ||
    document.querySelector("img.artdeco-entity-image--square");
  if (companyLogo) {
    const src = companyLogo.getAttribute("src");
    if (src && src.startsWith("http")) {
      data.logo_url = src;
    }
  }

  // Company follower count
  const followerEls = document.querySelectorAll(".org-top-card-summary-info-list__info-item");
  followerEls.forEach((el) => {
    const text = el.innerText.trim();
    if (text.includes("follower") || text.includes("employee")) {
      if (!data.company_info) data.company_info = [];
      data.company_info.push(text);
    }
  });

  // Current page URL
  data.profile_url = window.location.href;

  return data;
}

// Close common LinkedIn popups
function closePopups() {
  const selectors = [
    'button[aria-label="Dismiss"]',
    'button[aria-label="Close"]',
    "button.msg-overlay-bubble-header__control--close",
    'button[action-type="DENY"]',
    ".artdeco-modal__dismiss",
    ".artdeco-toast-item__dismiss",
    "#artdeco-global-alert-container button",
  ];
  let closed = 0;
  selectors.forEach((sel) => {
    try {
      document.querySelectorAll(sel).forEach((btn) => {
        if (btn.offsetParent !== null) {
          btn.click();
          closed++;
        }
      });
    } catch (e) {
      // ignore
    }
  });
  return closed;
}

// Listen for messages from the background script / CDP
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "extractProfile") {
    closePopups();
    const data = extractProfileData();
    sendResponse({ success: true, data: data });
  } else if (message.action === "closePopups") {
    const closed = closePopups();
    sendResponse({ success: true, closed: closed });
  }
  return true; // keep channel open for async response
});
