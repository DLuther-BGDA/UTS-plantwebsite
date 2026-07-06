## Setup Instructions

1. Clone the Repository

2.  **Set up Environment Variables:**
    Your application requires several environment variables for configuration and security.
    Create a `.env` file in the root of your project by copying the example:
    ```bash
    cp .env.example .env
    ```
    Now, open `.env` and fill in the necessary values:
    * **`POSTGRES_USER` / `POSTGRES_PASSWORD` / `DATABASE_URL`**: For local development, these should match your `docker-compose.yml` `db` service. For deployment (e.g., Render), the `DATABASE_URL` will be the `Internal Connection String` provided by your cloud database.
    * **`SECRET_KEY` / `SECURITY_PASSWORD_SALT`**: Generate long, random strings for these for security.
    * **`MAIL_*` variables**: Configure your email sending service details. For Gmail, you might need an App Password.
    * **`SECRET_INITIAL_PASSWORD`**: A temporary password for initial user creation. **Change this immediately after use!**

    **Important:** The `.env` file is excluded from Git for security reasons.

3.  **Run with Docker Compose (Local Development):**
    ```bash
    docker-compose up --build
    ```
