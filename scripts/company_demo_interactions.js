(() => {
    "use strict";

    const panels = Array.from(document.querySelectorAll("[data-demo-page]"));
    const panelByPage = new Map(panels.map((panel) => [panel.dataset.demoPage, panel]));
    const steps = document.querySelectorAll("nav [data-demo-go]");
    const companyHeading = document.querySelector("[data-demo-company-heading]");
    const evidencePair = document.querySelector("#demo-evidence-pair");
    let openPeerEvidence = false;

    function showCurrentPage(moveFocus) {
        const requested = location.hash.slice(1);
        const reviewingEvidence = requested === evidencePair.id;
        if (moveFocus && requested && !reviewingEvidence && !panelByPage.has(requested)) {
            return;
        }
        const page = reviewingEvidence ? "notes" : panelByPage.has(requested) ? requested : "discover";
        companyHeading.hidden = page === "discover" || page === "monitor";
        for (const panel of panels) {
            panel.hidden = panel.dataset.demoPage !== page;
        }
        for (const step of steps) {
            if (step.dataset.demoGo === page) {
                step.setAttribute("aria-current", "page");
            } else {
                step.removeAttribute("aria-current");
            }
        }
        if (moveFocus) {
            window.scrollTo(0, 0);
            const panel = panelByPage.get(page);
            if (reviewingEvidence) {
                evidencePair.querySelector("h3").focus({preventScroll: true});
                evidencePair.scrollIntoView({block: "start"});
            } else if (page === "valuation" && openPeerEvidence) {
                const state = panel.querySelector("#demo-withheld").checked ? "withheld" : "available";
                const evidence = panel.querySelector(`.demo-state--${state} .peer-evidence`);
                evidence.open = true;
                evidence.querySelector("summary").focus();
            } else {
                panel.querySelector("[data-demo-title]").focus({preventScroll: true});
            }
            openPeerEvidence = false;
        }
    }

    for (const link of document.querySelectorAll("[data-demo-go]")) {
        link.addEventListener("click", (event) => {
            const page = link.dataset.demoGo;
            if (event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !panelByPage.has(page)) {
                return;
            }
            event.preventDefault();
            openPeerEvidence = link.hasAttribute("data-demo-peer-evidence");
            if (location.hash === `#${page}`) {
                showCurrentPage(true);
            } else {
                location.hash = page;
            }
        });
    }
    window.addEventListener("hashchange", () => showCurrentPage(true));
    showCurrentPage(false);

    const search = document.querySelector("[data-demo-search]");
    const query = search.querySelector("[data-demo-query]");
    const searchStatus = document.querySelector("[data-demo-search-status]");
    const result = document.querySelector("[data-demo-result]");
    const companyName = search.dataset.demoCompanyName.toLowerCase();
    const companyTicker = search.dataset.demoCompanyTicker.toLowerCase();
    search.addEventListener("submit", (event) => {
        event.preventDefault();
        const term = query.value.trim().toLowerCase();
        const matched = term !== "" && (term === companyTicker || companyName.includes(term));
        result.hidden = !matched;
        searchStatus.textContent = matched ? "One fictional company found."
            : term ? "No fictional company matches that search." : "Enter a company name or ticker.";
    });
    search.addEventListener("reset", () => {
        result.hidden = true;
        searchStatus.textContent = "";
        query.focus();
    });

    const scenario = document.querySelector("[data-demo-scenario-values]");
    const scenarioControl = scenario.querySelector("[data-demo-scenario-control]");
    const wacc = scenarioControl.querySelector('input[type="range"]');
    const waccLabel = scenarioControl.querySelector("[data-demo-scenario-rate]");
    const scenarioValue = scenario.querySelector("[data-demo-scenario-value]");
    const scenarioValues = scenario.dataset.demoScenarioValues.split(",");
    function updateScenario() {
        const rate = `${wacc.value}%`;
        wacc.setAttribute("aria-valuetext", rate);
        waccLabel.textContent = rate;
        scenarioValue.value = scenarioValues[wacc.valueAsNumber - Number(wacc.min)];
    }
    wacc.addEventListener("input", updateScenario);
    updateScenario();
    scenario.querySelector("[data-demo-scenario-static]").hidden = true;
    scenarioControl.hidden = false;

    const noteForm = document.querySelector("[data-demo-note-form]");
    const noteInput = noteForm.querySelector("[data-demo-note-input]");
    const noteStatus = document.querySelector("[data-demo-pin-status]");
    const monitorNote = document.querySelector("[data-demo-monitor-note]");
    const monitorItem = document.querySelector("[data-demo-monitor-item]");
    const monitorEmpty = document.querySelector("[data-demo-monitor-empty]");
    noteForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const note = noteInput.value.trim();
        if (!note) {
            noteStatus.textContent = "Enter a follow-up note first.";
            noteInput.focus();
            return;
        }
        monitorNote.textContent = note;
        monitorItem.hidden = false;
        monitorEmpty.hidden = true;
        noteStatus.textContent = "Follow-up added for this page.";
    });

    const reviewForm = document.querySelector("[data-demo-review-form]");
    const reviewReason = reviewForm.querySelector("textarea");
    const reviewFeedback = reviewForm.querySelector("[data-demo-review-feedback]");
    const dispositionLabels = document.querySelectorAll("[data-demo-review-status]");
    const reasonLines = document.querySelectorAll("[data-demo-review-reason-line]");
    reviewForm.reset();
    document.querySelector("[data-demo-review-controls]").hidden = false;
    reviewForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const disposition = new FormData(reviewForm).get("disposition");
        const reason = reviewReason.value.trim();
        if (!reason) {
            reviewReason.setAttribute("aria-invalid", "true");
            reviewFeedback.textContent = "Enter a reason first.";
            reviewReason.focus();
            return;
        }
        if (!disposition) {
            return;
        }
        reviewReason.value = reason;
        reviewReason.removeAttribute("aria-invalid");
        for (const label of dispositionLabels) {
            label.textContent = disposition;
        }
        for (const line of reasonLines) {
            line.querySelector("[data-demo-review-reason]").textContent = reason;
            line.hidden = false;
        }
        reviewFeedback.textContent = "Disposition saved for this page.";
    });
})();
