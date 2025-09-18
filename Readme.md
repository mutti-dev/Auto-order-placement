<!-- Readme.md -->

Steps to Get the private_key

Go to Google Cloud Console → Service Accounts page
.

Select your project (the one where you enabled the API, e.g., Google Sheets API).

Find the service account you created (or create a new one with + Create Service Account).

Click on the service account → go to the Keys tab.

Click Add Key → Create New Key.

Choose JSON.

Google will generate a JSON key file and download it to your computer.

This file contains your private_key along with all the other required fields (client_email, project_id, token_uri, etc.).

🔹 Example: What You’ll See in the JSON

Inside the file, you’ll see something like:

{
  "type": "service_account",
  "project_id": "my-project-123",
  "private_key_id": "abcdef1234567890abcdef1234567890abcdef12",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhki...\n-----END PRIVATE KEY-----\n",
  "client_email": "my-service@my-project-123.iam.gserviceaccount.com",
  "client_id": "123456789012345678901",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/my-service%40my-project-123.iam.gserviceaccount.com",
   "universe_domain": "googleapis.com",
  "client_secret": ""
}


👉 The private_key field is already included there.

⚠️ Important

Never paste the private key in public places (like GitHub, StackOverflow, or chat).

If your private key ever leaks, go back to the Keys tab and delete it, then generate a new one.