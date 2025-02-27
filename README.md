# Atlas — Textfully's Messaging Service

Backend messaging service for sending iMessage and SMS.

## Setup

### Prerequisites

- Python 3.11.10 (via pyenv)
- Supabase project
- AWS EC2 instance

### Server Setup

1. Follow AWS EC2 setup instructions in [`EC2_SETUP.md`](./EC2_SETUP.md)

2. Initialize Supabase database by running all SQL scripts in [`sql`](./sql) in your Supabase SQL editor

### Environment Variables

Create `.env` files and retrieve secrets from AWS Secrets Manager

```sh
cp server/.env.example server/.env
```

### Install Dependencies

```sh
pip install -r requirements.txt
```

### Run Server

API Server (for EC2):

```sh
python server/api_server.py
```

Messaging Server (for Atlas):

```sh
python server/messaging_server.py
tailscale serve -bg 1234 # Serve the messaging server on port 1234 via Tailscale
```

### Configuration

API Server Base URL:

```sh
https://api.textfully.dev
```

Messaging Server Base URL:

```sh
{ATLAS_SERVER_ADDRESS}
```

### Authentication

All requests require either a Supabase access token or API token in the header:

Supabase Access Token:

```sh
Authorization: Bearer {ACCESS_TOKEN}
```

API Key:

```sh
Authorization: Bearer {API_KEY}
```
