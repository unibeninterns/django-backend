# DRID USER API: Robust User Management & Authentication

## Overview
This project serves as a comprehensive backend API built with **Django** and **Django REST Framework**, designed for secure and efficient user management, including robust authentication through **JWT (JSON Web Tokens)** and seamless **Google OAuth2** integration.

## Features
- **Django**: Provides a high-level Python web framework for rapid development and clean design.
- **Django REST Framework (DRF)**: Enables building powerful and flexible Web APIs quickly and efficiently.
- **Django Simple JWT**: Implements stateless, token-based authentication for enhanced security and scalability.
- **Django Allauth**: Offers a comprehensive set of Django applications for authentication, including local user accounts and social authentication providers.
- **Google OAuth2**: Facilitates quick and easy social logins via Google.
- **CORS Headers**: Manages Cross-Origin Resource Sharing to allow secure requests from different origins.
- **SQLite**: Utilized as the default lightweight database for development environments.

## Getting Started
To set up and run the DRID API backend on your local machine, follow these step-by-step instructions.

### Installation
🚀 First, clone the repository to your local machine:
```bash
git clone https://github.com/unibeninterns/django-backend.git
cd backend
```

📦 Next, create and activate a virtual environment to manage dependencies:
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

⚙️ Install the necessary project dependencies. These are derived from the `INSTALLED_APPS` and other configurations in `settings.py`:
```bash
pip install Django djangorestframework djangorestframework-simplejwt django-cors-headers django-allauth dj-rest-auth
```

🔄 Apply all pending database migrations to set up the database schema:
```bash
python manage.py migrate
```

🔐  Create a superuser (admin account) automatically using a script:
This will generate a default admin account using credentials stored in your .env file.

# .env.example (DO NOT COMMIT your real .env)
💡 Create a .env file in the project root by copying .env.example, then replace the values with your desired admin account credentials.

✅ Ensure your .env includes:
```ini
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=Testing_123
DJANGO_SUPERUSER_FIRST_NAME=Admin
DJANGO_SUPERUSER_LAST_NAME=User
```

Then run:
```bash
python manage.py runscript createsuperuser
```

▶️ Finally, start the Django development server:
```bash
python manage.py runserver
```
The API will be accessible at `http://127.0.0.1:8000/`.

### Environment Variables
The application relies on specific environment variables for configuration. It's recommended to store these in a `.env` file in the project root or configure them directly in your deployment environment.

- `SECRET_KEY`: A unique string used for cryptographic signing. **Mandatory**.
  Example: `django-insecure-fk5hmq=yg%4o%afyvk(8qc)96dpy6_&$obopb_*c$#q&5f9(4k` (For production, generate a strong, unique key).
- `DEBUG`: Boolean indicating if debug mode is active. `True` enables detailed error pages. **Mandatory**.
  Example: `True`
- `ALLOWED_HOSTS`: A list of strings representing the host/domain names that this Django site can serve. **Mandatory**.
  Example: `['localhost', '127.0.0.1']`
- `FRONTEND_URL`: The base URL of the client-side application. Used for constructing email verification and password reset links. **Mandatory**.
  Example: `http://localhost:5173`
- `SITE_URL`: The base URL of the Django backend itself. Used for social login callbacks and other internal absolute URL constructions. **Mandatory**.
  Example: `http://127.0.0.1:8000`


## Technologies Used

| Technology | Purpose |
| :--------- | :------------------------------------------- |
| ![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat&logo=python&logoColor=white) | Primary programming language |
| ![Django](https://img.shields.io/badge/Django-~5.0-092E20?style=flat&logo=django&logoColor=white) | High-level web framework |
| ![Django REST Framework](https://img.shields.io/badge/DRF-Framework-darkgreen?style=flat&logo=django&logoColor=white) | Building Web APIs |
| ![JWT](https://img.shields.io/badge/JWT-Authentication-black?style=flat&logo=json-web-tokens&logoColor=white) | Secure token-based authentication |
| ![Django Allauth](https://img.shields.io/badge/Allauth-Auth-purple?style=flat) | Comprehensive authentication solution |
| ![Google OAuth](https://img.shields.io/badge/Google%20OAuth2-Login-red?style=flat&logo=google&logoColor=white) | Social authentication integration |
| ![CORS Headers](https://img.shields.io/badge/CORS-Middleware-orange?style=flat) | Cross-Origin Resource Sharing |
| ![SQLite](https://img.shields.io/badge/SQLite-Database-blue?style=flat&logo=sqlite&logoColor=white) | Lightweight development database |

## Contributing
We welcome contributions to enhance this project! If you're looking to contribute, please follow these guidelines:

✨ Fork the repository and create your feature branch (`git checkout -b feature/AmazingFeature`).
🐛 Ensure all existing tests pass and add new tests for your features.
💡 Adhere to the project's coding style and best practices.
🚀 Commit your changes (`git commit -m 'feat: Add new amazing feature'`).
⬆️ Push to the branch (`git push origin feature/AmazingFeature`).
📝 Open a pull request describing your changes and their benefits.

## License
This project is open-sourced. Details will be provided in a dedicated `LICENSE` file.

