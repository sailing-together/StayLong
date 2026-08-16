const form = document.querySelector("#concern-form");
const statusMessage = document.querySelector("#form-status");
const caseStatus = document.querySelector("#case-status");
const caseSummary = document.querySelector("#case-summary");
const concernList = document.querySelector("#case-concerns");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = document.querySelector("#api-token").value;
  const summary = document.querySelector("#concern-summary").value.trim();
  statusMessage.textContent = "Creating a case…";
  try {
    const response = await fetch("/v1/cases", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ summary }),
    });
    if (!response.ok) throw new Error("The case could not be created. Check the access token.");
    const created = await response.json();
    caseStatus.textContent = "Open";
    caseSummary.textContent = summary;
    concernList.innerHTML = `<li>${escapeHtml(summary)}</li>`;
    statusMessage.textContent = `Case ${created.case_id} is ready for coordination.`;
    form.reset();
  } catch (error) {
    statusMessage.textContent = error.message;
  }
});

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}
