//it will be used in google appscript  google_appscript.js

const WEBHOOK_URL = "https://9e33eb09ac27.ngrok-free.app/start-orders"; 

function triggerProcessing() {
  try {
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ sheet: SpreadsheetApp.getActive().getId() }),
      muteHttpExceptions: true
    };
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const result = JSON.parse(response.getContentText());
    SpreadsheetApp.getUi().alert("Automation Result: " + result.status + "\n" + result.message);
  } catch (e) {
    SpreadsheetApp.getUi().alert("Error calling automation: " + e.message);
  }
}

function onOpen() {
  SpreadsheetApp.getUi().createMenu("Order Automation")
    .addItem("Process Orders Now", "triggerProcessing")
    .addToUi();
}
