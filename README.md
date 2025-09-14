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

## API Documentation
### Base URL
All API endpoints are accessible relative to the base URL: `http://127.0.0.1:8000/api`

### Endpoints

#### POST /api/auth/registration/
Registers a new user account with first name, last name, email, and password. An email verification link will be sent.
**Request**:
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@example.com",
  "password": "StrongPassword123"
}
```
**Response**:
```json
{
  "detail": "Registration successful. Please verify your email with the OTP."
}
```
**Errors**:
- `400 Bad Request`: Occurs if the email already exists, or if provided data is invalid (e.g., missing fields, password validation failure).

#### POST /api/auth/verify-otp/
Verifies the 6-digit OTP sent to the user's email. Returns JWT tokens on success.
**Request**:
```json
{
  "email": "newuser@example.com",
  "otp_code": "123456"
}
```
**Response**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJh...",
  "access": "eyJ0eXAiOiJKV1QiLCJh..."
}
```
**Errors**:
- `400 Bad Request`: Invalid or expired OTP, OTP not found or Missing email or code.
- `404 Not Found`: User or OTP record not found.

#### POST /api/auth/resend-otp/
Resends a new 6-digit OTP to a user who hasn’t verified yet.
**Request**:
```json
{
  "email": "user@example.com"
}
```
**Response**:
```json
{
  "detail": "A new OTP has been sent."
}
```
**Errors**:
- `400 Bad Request`: Email is missing or User is already verified.
- `404 Not Found`: User with provided email does not exist.

#### POST /api/auth/login/
Authenticates a user using their email and password, returning JWT access and refresh tokens upon success.
**Request**:
```json
{
  "email": "user@example.com",
  "password": "UserPassword123"
}
```
**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1Ni...",
  "refresh": "eyJhbGciOiJIUzI1Ni...",
  "user": {
    "pk": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```
**Errors**:
- `400 Bad Request`: Typically due to missing credentials or invalid input format.
- `401 Unauthorized`: Indicates incorrect email or password, or if the user account is disabled.

### POST api/token/refresh/
Refreshes the JWT access token using a valid refresh token. This endpoint does not return a new refresh token unless you have rotation enabled.
**Request**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1Ni...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1Ni..."
}
```
**Errors**:
- `400 Bad Request`: The refresh token is missing, expired, or malformed.
- `401 Unauthorized`: The refresh token is invalid or blacklisted (e.g., if BLACKLIST_AFTER_ROTATION is enabled and it's already used).
- `401 Forbidden`: The user associated with the token is inactive or deleted.

#### POST /api/admin-login/
Authenticates an admin user using their email and password. Only users with the "admin" role can successfully log in through this route. Returns JWT tokens upon successful authentication.
**Request**:
```json
{
  "email": "admin@example.com",
  "password": "YourAdminPassword123"
}
```
**Response**:
```json
{
  "refresh": "your-refresh-token",
  "access": "your-access-token",
  "user": {
    "email": "admin@example.com",
    "role": "admin",
    "first_name": "Admin",
    "last_name": "User",
    "cohort": null
  }
}
```
**Errors**:
- `400 Bad Request`: Typically due to missing credentials or invalid input format.
- `401 Unauthorized`: Indicates incorrect email or password, or if the user account is disabled.
- `403 Forbidden`: Access denied if the user is not an admin..



#### POST /api/auth/logout/
Logs out the authenticated user by blacklisting their refresh token, invalidating current sessions.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{}
```
**Response**:
```json
{
  "detail": "Successfully logged out."
}
```
**Errors**:
- `401 Unauthorized`: No valid authentication credentials or an invalid token is provided.

#### POST /api/auth/password/change/
Allows an authenticated user to change their password.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{
  "old_password": "OldPassword123",
  "new_password1": "NewStrongPassword123",
  "new_password2": "NewStrongPassword123"
}
```
**Response**:
```json
{
  "detail": "New password has been saved."
}
```
**Errors**:
- `400 Bad Request`: Occurs if the old password doesn't match, new passwords don't match, or the new password fails validation.
- `401 Unauthorized`: No valid authentication credentials or an invalid token is provided.

#### POST /api/auth/password/reset/
Initiates the password reset process by sending an email with a reset link to the user's registered email address.
**Request**:
```json
{
  "email": "user@example.com"
}
```
**Response**:
```json
{
  "detail": "Password reset e-mail has been sent."
}
```
**Errors**:
- `400 Bad Request`: Indicates that no user was found with the provided email address.

#### POST /api/auth/password/reset/confirm/
Confirms the password reset using the UID and token obtained from the reset email, setting a new password.
**Request**:
```json
{
  "uid": "user_uid_from_email",
  "token": "reset_token_from_email",
  "new_password1": "NewStrongPassword123",
  "new_password2": "NewStrongPassword123"
}
```
**Response**:
```json
{
  "detail": "Password has been reset with the new password."
}
```
**Errors**:
- `400 Bad Request`: Occurs if the UID or token is invalid, or new passwords do not match/fail validation.

#### GET /api/auth/user/
Retrieves the profile details of the currently authenticated user.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```
GET /api/auth/user/
```
**Response**:
```json
{
  "pk": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```
**Errors**:
- `401 Unauthorized`: No valid authentication credentials or an invalid token is provided.

#### PUT /api/auth/user/
Fully updates the profile details of the authenticated user.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@example.com"
}
```
**Response**:
```json
{
  "pk": 1,
  "email": "jane.smith@example.com",
  "first_name": "Jane",
  "last_name": "Smith"
}
```
**Errors**:
- `400 Bad Request`: Invalid data provided (e.g., email already taken).
- `401 Unauthorized`: No valid authentication credentials or an invalid token is provided.

#### PATCH /api/auth/user/
Partially updates the profile details of the authenticated user.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{
  "first_name": "Joanna"
}
```
**Response**:
```json
{
  "pk": 1,
  "email": "user@example.com",
  "first_name": "Joanna",
  "last_name": "Doe"
}
```
**Errors**:
- `400 Bad Request`: Invalid data provided.
- `401 Unauthorized`: No valid authentication credentials or an invalid token is provided.

#### POST /api/auth/google/
Authenticates or registers a user using a Google OAuth2 access token.
**Request**:
```json
{
  "access_token": "your_google_access_token_here"
}
```
**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1Ni...",
  "refresh": "eyJhbGciOiJIUzI1Ni...",
  "user": {
    "pk": 1,
    "email": "google_user@gmail.com",
    "first_name": "Google",
    "last_name": "User"
  }
}
```
**Errors**:
- `400 Bad Request`: Occurs if the provided Google access token is invalid or expired.

#### GET /api/accounts/users/
Retrieves a list of all user profiles.
**Request**: (Requires `Authorization: Bearer <access_token>` header for authenticated access)
```
GET /api/accounts/users/
```
**Response**:
```json
[
  {
    "id": 1,
    "url": "http://127.0.0.1:8000/api/accounts/users/1/",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "is_verified": true,
    "username": "john_doe",
    "role": "admin",
    "cohort": null
  }
]
```
#### GET /api/accounts/users/{id}/
Retrieves the detailed profile of a specific user by their ID.
**Request**: (Requires `Authorization: Bearer <access_token>` header for authenticated access)
```
GET /api/accounts/users/1/
```
**Response**:
```json
{
  "id": 1,
  "url": "http://127.0.0.1:8000/api/accounts/users/1/",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "is_verified": true,
  "username": "john_doe"
}
```
**Errors**:
- `401 Unauthorized`: No authentication credentials provided.
- `403 Forbidden`: Authenticated user lacks permission to view this specific user's profile.
- `404 Not Found`: No user exists with the specified ID.

#### PUT /api/accounts/users/{id}/
Fully updates the profile details of a specific user.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{
  "first_name": "Updated",
  "last_name": "Name",
  "email": "updated.email@example.com"
}
```
**Response**:
```json
{
  "id": 1,
  "first_name": "Updated",
  "last_name": "Name",
  "email": "updated.email@example.com",
  "is_verified": true,
  "username": "updated_name"
}
```
**Errors**:
- `400 Bad Request`: Invalid data provided.
- `401 Unauthorized`: No authentication credentials provided.
- `403 Forbidden`: Authenticated user lacks permission to update this specific user's profile.
- `404 Not Found`: No user exists with the specified ID.

#### PATCH /api/accounts/users/{id}/
Partially updates the profile details of a specific user.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```json
{
  "first_name": "Partial"
}
```
**Response**:
```json
{
  "id": 1,
  "first_name": "Partial",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "is_verified": true,
  "username": "john_doe"
}
```
**Errors**:
- `400 Bad Request`: Invalid data provided.
- `401 Unauthorized`: No authentication credentials provided.
- `403 Forbidden`: Authenticated user lacks permission to update this specific user's profile.
- `404 Not Found`: No user exists with the specified ID.

#### DELETE /api/accounts/users/{id}/
Deletes a specific user profile from the system.
**Request**: (Requires `Authorization: Bearer <access_token>` header)
```
DELETE /api/accounts/users/1/
```
**Response**:
`204 No Content` (Successful deletion, no content returned)
**Errors**:
- `401 Unauthorized`: No authentication credentials provided.
- `403 Forbidden`: Authenticated user lacks permission to delete this specific user's profile.
- `404 Not Found`: No user exists with the specified ID.

## Usage
Once the backend is running, you can interact with the API endpoints using tools like Postman, Insomnia, curl, or integrate it with a frontend application.

Here's an example using `curl` to register a new user:
```bash
curl -X POST \
  http://127.0.0.1:8000/api/auth/registration/ \
  -H 'Content-Type: application/json' \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test.user@example.com",
    "password": "SecurePassword789!"
  }'
```

After registration, you would receive an email verification link (if `ACCOUNT_EMAIL_VERIFICATION` is set to `mandatory`). Upon verification, you can log in:
```bash
curl -X POST \
  http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test.user@example.com",
    "password": "SecurePassword789!"
  }'
```
This will return `access` and `refresh` tokens, which you should include in the `Authorization` header (`Authorization: Bearer <access_token>`) for subsequent protected requests.

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

