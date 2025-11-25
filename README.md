# blockchain_file_integrity

This is a simple Flask-backed project for file integrity tracking using an internal blockchain.

## Added: MongoDB support

The backend now supports MongoDB for:
- storing user accounts (hashed passwords) in `users` collection
- storing registered file metadata in `files` collection

By default the backend attempts to connect to `mongodb://localhost:27017` and uses database `blockchain_app`.

### Environment variables
- `MONGO_URI` — MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB` — Database name (default: `blockchain_app`)

### Run locally
1. Ensure MongoDB is running locally or set `MONGO_URI` to a valid host.
2. Install Python deps:

```powershell
pip install -r requirements.txt
```

3. Run the backend:

```powershell
python backend/server.py
```

When the server runs it will migrate users from `backend/users.json` into MongoDB automatically if the `users` collection is empty.

If you want me to push this repo to GitHub next, tell me which repository to use or whether I should create one for you.