(() => {
    "use strict";

    const panels = Array.from(document.querySelectorAll("[data-demo-page]"));
    const panelByPage = new Map(panels.map((panel) => [panel.dataset.demoPage, panel]));
    const steps = document.querySelectorAll("nav [data-demo-go]");

    function showCurrentPage(moveFocus) {
        const requested = location.hash.slice(1);
        if (moveFocus && requested && !panelByPage.has(requested)) {
            return;
        }
        const page = panelByPage.has(requested) ? requested : "discover";
        for (const panel of panels) {
            panel.hidden = panel.dataset.demoPage !== page;
        }
        for (const step of steps) {
            if (step.dataset.demoGo === page) {
                step.setAttribute("aria-current", "step");
            } else {
                step.removeAttribute("aria-current");
            }
        }
        if (moveFocus) {
            window.scrollTo(0, 0);
            panelByPage.get(page).querySelector("[data-demo-title]").focus({preventScroll: true});
        }
    }

    for (const link of document.querySelectorAll("[data-demo-go]")) {
        link.addEventListener("click", (event) => {
            const page = link.dataset.demoGo;
            if (event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !panelByPage.has(page)) {
                return;
            }
            event.preventDefault();
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
})();
