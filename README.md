# DRID Learning Platform API

## Overview
This project is a robust backend API for a learning management system, built with Django and Django REST Framework. It provides comprehensive functionalities for user management, course delivery, assessments, and administrative operations, leveraging JWT for secure authentication and a custom user model.

## Features
- **User Authentication & Authorization**: Implements a custom user model with secure registration, login, password management, and social login (Google OAuth2) via `dj-rest-auth` and `django-allauth`. Utilizes JSON Web Tokens (JWT) for stateless authentication.
- **Role-Based Access Control**: Differentiates user permissions (Admin, Student) to control access to various API resources, ensuring data integrity and security.
- **Course Management**: Full CRUD operations for managing courses, modules, lessons, and diverse content items (video, PDF, quiz, text).
- **Assessment System**: Supports creation and submission of quizzes, including multiple-choice, true/false, and essay questions. Tracks student scores and submissions.
- **Payment & Enrollment**: Manages user enrollments into courses and tracks payment information, allowing for secure and organized course access.
- **Capstone Projects**: Facilitates the submission and grading of capstone projects by students.
- **Live Sessions**: Enables scheduling and management of live online sessions linked to specific course modules.
- **CORS Handling**: Configured to manage Cross-Origin Resource Sharing for seamless frontend integration.
- **Database**: Uses SQLite for development, easily configurable for production databases like PostgreSQL.

## Getting Started
To set up the DRID Learning Platform API backend locally for development:

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
**Create a Superuser (Admin Account)**:
This project includes a custom management command to create a superuser using environment variables.
Set the following environment variables (e.g., in a `.env` file):
```
DJANGO_SUPERUSER_EMAIL=your_admin_email@example.com
DJANGO_SUPERUSER_PASSWORD=your_admin_password
DJANGO_SUPERUSER_FIRSTNAME=Admin
DJANGO_SUPERUSER_LASTNAME=User
```
Then run:
```bash
python manage.py createsuper
```
Alternatively, for interactive creation:
```bash
python manage.py createsuperuser
```
Follow the prompts.
**Run the Development Server**:
```bash
python manage.py runserver
```

### Environment Variables
The following environment variables are required for proper application functionality. It is recommended to use a `.env` file for local development.

-   `SECRET_KEY`: Django secret key for cryptographic signing. (Currently hardcoded in `settings.py` for simplicity, should be moved to env for production).
-   `FRONTEND_URL`: URL of your frontend application (e.g., `http://localhost:5173`). Used for password reset confirmation links.
-   `SITE_URL`: Base URL of the Django backend (e.g., `http://127.0.0.1:8000`). Used for `allauth` callbacks.
-   `DJANGO_SUPERUSER_EMAIL`: Email for the default superuser.
-   `DJANGO_SUPERUSER_PASSWORD`: Password for the default superuser.
-   `DJANGO_SUPERUSER_FIRSTNAME`: First name for the default superuser.
-   `DJANGO_SUPERUSER_LASTNAME`: Last name for the default superuser.

For Google OAuth2 integration (`allauth.socialaccount.providers.google`):
-   `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`: Google OAuth Client ID.
-   `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET`: Google OAuth Client Secret.

## API Documentation
### Base URL
`http://127.00.1:8000/api/`

### Authentication
JWT tokens are used for authentication. After successful login, `access` and `refresh` tokens are returned. The `access` token should be included in the `Authorization` header as `Bearer <access_token>` for protected endpoints.

#### POST /api/auth/login/
Authenticates a user and provides JWT tokens.
**Permissions**: AllowAny
**Request**:
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```
**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "pk": 1,
    "email": "user@example.com",
    "role": "student",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```
**Errors**:
- 400 Bad Request: Missing `email` or `password`.
- 401 Unauthorized: Invalid credentials.
- 403 Forbidden: User account is disabled.

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
    "last_name": "User"
  }
}
```
**Errors**:
- `400 Bad Request`: Typically due to missing credentials or invalid input format.
- `401 Unauthorized`: Indicates incorrect email or password, or if the user account is disabled.
- `403 Forbidden`: Access denied if the user is not an admin..


#### POST /api/auth/token/refresh/
Obtains a new access token using a refresh token.
**Permissions**: AllowAny
**Request**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Errors**:
- 401 Unauthorized: Invalid or expired refresh token.

#### POST /api/auth/token/verify/
Verifies an access token.
**Permissions**: AllowAny
**Request**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Response**:
- 200 OK (Empty response if valid)
**Errors**:
- 401 Unauthorized: Invalid or expired token.

#### POST /api/auth/logout/
Blacklists the current refresh token, effectively logging the user out.
**Permissions**: IsAuthenticated
**Request**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Response**:
- 200 OK (Empty response upon successful logout)
**Errors**:
- 401 Unauthorized: Not authenticated or invalid token.

#### POST /api/auth/registration/
Registers a new user.
**Permissions**: AllowAny
**Request**:
```json
{
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "password": "StrongPassword123",
  "password2": "StrongPassword123"
}
```
**Response**:
```json
{
  "pk": 2,
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "username": "jane_doe"
}
```
**Errors**:
- 400 Bad Request: Invalid or missing fields, email already exists, passwords do not match.

#### GET /api/auth/user/
Retrieves details of the authenticated user.
**Permissions**: IsAuthenticated
**Request**: (No body)
**Response**:
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "is_verified": true,
  "username": "john_doe",
  "role": "student",
}
```
**Errors**:
- `400 Bad Request`: Typically due to missing credentials or invalid input format.
- `401 Unauthorized`: Indicates incorrect email or password, or if the user account is disabled.

#### POST /api/auth/password/reset/
Initiates a password reset process, sending a reset email to the user.
**Permissions**: AllowAny
**Request**:
```json
{
  "email": "user@example.com"
}
```
**Response**:
- 200 OK: {"detail": "Password reset e-mail has been sent."}
**Errors**:
- 400 Bad Request: Invalid email.

#### POST /api/auth/password/reset/confirm/
Confirms password reset with UID and token from the email.
**Permissions**: AllowAny
**Request**:
```json
{
  "uid": "...",
  "token": "...",
  "new_password1": "NewStrongPassword123",
  "new_password2": "NewStrongPassword123"
}
```
**Response**:
- 200 OK: {"detail": "Password has been reset with the new password."}
**Errors**:
- 400 Bad Request: Invalid UID/token, passwords do not match.

#### POST /api/auth/password/change/
Changes the password of the authenticated user.
**Permissions**: IsAuthenticated
**Request**:
```json
{
  "old_password": "OldPassword123",
  "new_password1": "NewStrongPassword123",
  "new_password2": "NewStrongPassword123"
}
```
**Response**:
- 200 OK: {"detail": "New password has been set."}
**Errors**:
- 400 Bad Request: Invalid old password, passwords do not match, or weak new password.
- 401 Unauthorized: Not authenticated.

#### POST /api/auth/google/
Performs Google OAuth2 login. The frontend should handle the initial OAuth redirect and then send the `code` to this endpoint.
**Permissions**: AllowAny
**Request**:
```json
{
  "access_token": "YOUR_GOOGLE_ACCESS_TOKEN",
  "code": "YOUR_GOOGLE_AUTH_CODE"
}
```
**Response**:
(Same as `POST /api/auth/login/` with `access` and `refresh` tokens, and user details.)
**Errors**:
- 400 Bad Request: Invalid `access_token` or `code`.

#### GET /api/account/users/
Lists all users.
**Permissions**: IsAdminUser
**Request**: (No body)
**Response**:
```json
[
  {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "is_verified": true,
    "username": "john_doe",
    "role": "student",
  },
  {
    "id": 2,
    "first_name": "Admin",
    "last_name": "User",
    "email": "admin@example.com",
    "is_verified": true,
    "username": "admin_user",
    "role": "admin",
  }
]
```
**Errors**:
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: User is not an admin.

#### GET /api/account/users/<int:pk>/
Retrieves details for a specific user.
**Permissions**: IsAuthenticated (AdminUser can view all, Owner can view their own)
**Request**: (No body)
**Response**:
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "is_verified": true,
  "username": "john_doe",
  "role": "student",
}
```
**Errors**:
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not authorized to view this user's details.
- 404 Not Found: User with specified ID does not exist.

#### PUT /api/account/users/<int:pk>/
Updates all details for a specific user.
**Permissions**: IsAuthenticated (AdminUser can update all, Owner can update their own)
**Request**:
```json
{
  "first_name": "Jonathan",
  "last_name": "Smith"
  // Email, username, is_verified, role, are read-only for non-admin updates
}
```
**Response**: (Updated user object)
**Errors**:
- 400 Bad Request: Invalid or missing fields.
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not authorized to update this user's details.
- 404 Not Found: User with specified ID does not exist.

#### PATCH /api/account/users/<int:pk>/
Partially updates details for a specific user.
**Permissions**: IsAuthenticated (AdminUser can update all, Owner can update their own)
**Request**:
```json
{
  "first_name": "Jon"
}
```
**Response**: (Updated user object)
**Errors**:
- 400 Bad Request: Invalid fields.
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not authorized to update this user's details.
- 404 Not Found: User with specified ID does not exist.

#### DELETE /api/account/users/<int:pk>/
Deletes a specific user.
**Permissions**: IsAuthenticated (AdminUser can delete all, Owner can delete their own)
**Request**: (No body)
**Response**:
- 204 No Content (Empty response upon successful deletion)
**Errors**:
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not authorized to delete this user.
- 404 Not Found: User with specified ID does not exist.

### Module Endpoints

#### Courses
**Permissions**:
- `GET /api/module/courses/`: AllowAny
- `POST /api/module/courses/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/courses/<int:pk>/`: IsAdminUser
**GET /api/module/courses/**: List all courses.
**POST /api/module/courses/**: Create a new course.
**Request**:
```json
{
  "title": "Introduction to Python",
  "description": "A comprehensive course on Python programming.",
  "duration_weeks": 12,
  "start_date": "2024-09-01",
  "end_date": "2024-11-24"
}
```
**Response**:
```json
{
  "id": 1,
  "title": "Introduction to Python",
  "description": "A comprehensive course on Python programming.",
  "duration_weeks": 12,
  "start_date": "2024-09-01",
  "end_date": "2024-11-24"
}
```
**Errors**:
- 400 Bad Request: Invalid data.
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not an admin user for POST/PUT/PATCH/DELETE.
- 404 Not Found: For specific course operations.

#### Modules
**Permissions**:
- `GET /api/module/modules/`: AllowAny
- `POST /api/module/modules/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/modules/<int:pk>/`: IsAdminUser
**GET /api/module/modules/**: List all modules.
**POST /api/module/modules/**: Create a new module.
**Request**:
```json
{
  "course": 1,
  "title": "Module 1: Python Basics",
  "week_number": 1,
  "description": "Covers Python syntax, variables, and data types."
}
```
**Response**:
```json
{
  "id": 1,
  "course": 1,
  "title": "Module 1: Python Basics",
  "week_number": 1,
  "description": "Covers Python syntax, variables, and data types."
}
```
**Errors**: (Same as Courses)

#### Lessons
**Permissions**:
- `GET /api/module/lessons/`: AllowAny
- `POST /api/module/lessons/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/lessons/<int:pk>/`: IsAdminUser
**GET /api/module/lessons/**: List all lessons.
**POST /api/module/lessons/**: Create a new lesson.
**Request**:
```json
{
  "module": 1,
  "title": "Lesson 1.1: Hello World",
  "order": 1
}
```
**Response**:
```json
{
  "id": 1,
  "module": 1,
  "title": "Lesson 1.1: Hello World",
  "order": 1
}
```
**Errors**: (Same as Courses)

#### Content Items
**Permissions**:
- `GET /api/module/content-items/`: AllowAny
- `POST /api/module/content-items/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/content-items/<int:pk>/`: IsAdminUser
**GET /api/module/content-items/**: List all content items.
**POST /api/module/content-items/**: Create a new content item.
**Request**:
```json
{
  "lesson": 1,
  "type": "video",
  "title": "Introductory Video",
  "external_url": "https://example.com/video.mp4",
  "duration": "PT0H10M0S"
}
```
**Response**:
```json
{
  "id": 1,
  "lesson": 1,
  "type": "video",
  "title": "Introductory Video",
  "file": null,
  "external_url": "https://example.com/video.mp4",
  "duration": "PT0H10M0S",
  "content": null
}
```
**Errors**: (Same as Courses)

#### Quizzes
**Permissions**:
- `POST /api/module/quizzes/`: IsStudent
- `GET /api/module/quizzes/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/quizzes/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/quizzes/**: List all quizzes.
**POST /api/module/quizzes/**: Create a new quiz.
**Request**: (Choose one of `lesson`, `module`, or `course`)
```json
{
  "lesson": 1,
  "title": "Lesson 1 Quiz"
}
```
**Response**:
```json
{
  "id": 1,
  "lesson": 1,
  "module": null,
  "course": null,
  "title": "Lesson 1 Quiz"
}
```
**Errors**:
- 400 Bad Request: Invalid data (e.g., associating with multiple parents).
- 401 Unauthorized: Not authenticated for list/retrieve/update/delete.
- 403 Forbidden: Not a student for create, or not owner/admin for retrieve/update/delete.
- 404 Not Found: For specific quiz operations.

#### Questions
**Permissions**:
- `GET /api/module/questions/`: AllowAny
- `POST /api/module/questions/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/questions/<int:pk>/`: IsAdminUser
**GET /api/module/questions/**: List all questions.
**POST /api/module/questions/**: Create a new question.
**Request**:
```json
{
  "quiz": 1,
  "text": "What is the capital of France?",
  "type": "multiple_choice",
  "options": {"A": "Berlin", "B": "Paris", "C": "Rome"},
  "correct_answer": "B"
}
```
**Response**:
```json
{
  "id": 1,
  "quiz": 1,
  "text": "What is the capital of France?",
  "type": "multiple_choice",
  "options": {"A": "Berlin", "B": "Paris", "C": "Rome"},
  "correct_answer": "B"
}
```
**Errors**: (Same as Courses)

#### Quiz Submissions
**Permissions**:
- `GET /api/module/quiz-submissions/`: IsAuthenticated
- `POST /api/module/quiz-submissions/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/quiz-submissions/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/quiz-submissions/**: List all quiz submissions (admin sees all, student sees their own).
**POST /api/module/quiz-submissions/**: Create a new quiz submission. `student` field is automatically set to the authenticated user.
**Request**:
```json
{
  "quiz": 1,
  "score": 85.5
}
```
**Response**:
```json
{
  "id": 1,
  "student": 1,
  "quiz": 1,
  "score": 85.5,
  "submitted_at": "2024-07-30T10:00:00Z"
}
```
**Errors**:
- 400 Bad Request: Invalid data.
- 401 Unauthorized: Not authenticated.
- 403 Forbidden: Not owner or admin for retrieve/update/delete.
- 404 Not Found: For specific submission operations.

#### Answers
**Permissions**:
- `POST /api/module/answers/`: IsStudent
- `GET /api/module/answers/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/answers/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/answers/**: List all answers (admin sees all, student sees their own).
**POST /api/module/answers/**: Create a new answer. `student` field for `perform_create` seems incorrect here, should be `submission` from `quiz_submission` context, but the serializer takes `submission` directly.
**Request**:
```json
{
  "submission": 1,
  "question": 1,
  "answer_text": "Paris"
}
```
**Response**:
```json
{
  "id": 1,
  "submission": 1,
  "question": 1,
  "answer_text": "Paris"
}
```
**Errors**: (Similar to Quiz Submissions)

#### Payments
**Permissions**:
- `POST /api/module/payments/`: IsStudent
- `GET /api/module/payments/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/payments/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/payments/**: List all payments (admin sees all, user sees their own).
**POST /api/module/payments/**: Record a new payment. `user` field is automatically set to the authenticated user.
**Request**:
```json
{
  "amount": "99.99",
  "payment_option": "Credit Card",
  "transaction_id": "TXN123456789",
  "status": "completed"
}
```
**Response**:
```json
{
  "id": 1,
  "user": 1,
  "amount": "99.99",
  "payment_option": "Credit Card",
  "transaction_id": "TXN123456789",
  "status": "completed",
  "created_at": "2024-07-30T10:00:00Z"
}
```
**Errors**: (Similar to Quiz Submissions)

#### Enrollments
**Permissions**:
- `POST /api/module/enrollments/`: IsStudent
- `GET /api/module/enrollments/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/enrollments/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/enrollments/**: List all enrollments (admin sees all, user sees their own).
**POST /api/module/enrollments/**: Enroll a user in a course. `user` field is automatically set to the authenticated user.
**Request**:
```json
{
  "course": 1,
  "payment": null,
  "status": "active"
}
```
**Response**:
```json
{
  "id": 1,
  "user": 1,
  "course": 1,
  "payment": null,
  "enrolled_at": "2024-07-30T10:00:00Z",
  "status": "active"
}
```
**Errors**: (Similar to Quiz Submissions)

#### Capstone Projects
**Permissions**:
- `POST /api/module/capstone-projects/`: IsStudent
- `GET /api/module/capstone-projects/`: IsAuthenticated
- `GET/PUT/PATCH/DELETE /api/module/capstone-projects/<int:pk>/`: IsAuthenticated, IsOwnerOrAdmin
**GET /api/module/capstone-projects/**: List all capstone projects (admin sees all, student sees their own).
**POST /api/module/capstone-projects/**: Submit a new capstone project. `student` field is automatically set to the authenticated user. Note: `submission_file` would be a file upload.
**Request**: (Multipart/form-data for `submission_file`)
```json
{
  "title": "My Final Project",
  "description": "A detailed description of my capstone project.",
  "submission_file": "<file_upload>"
}
```
**Response**:
```json
{
  "id": 1,
  "student": 1,
  "title": "My Final Project",
  "description": "A detailed description of my capstone project.",
  "submission_file": "/media/capstone_projects/my_project.pdf",
  "submitted_at": "2024-07-30T10:00:00Z",
  "grade": null
}
```
**Errors**: (Similar to Quiz Submissions)

#### Live Sessions
**Permissions**:
- `GET /api/module/live-sessions/`: AllowAny
- `POST /api/module/live-sessions/`: IsAdminUser
- `GET/PUT/PATCH/DELETE /api/module/live-sessions/<int:pk>/`: IsAdminUser
**GET /api/module/live-sessions/**: List all live sessions.
**POST /api/module/live-sessions/**: Schedule a new live session.
**Request**:
```json
{
  "module": 1,
  "title": "Weekly Q&A Session",
  "meeting_url": "https://zoom.us/j/123456789",
  "scheduled_time": "2024-08-05T14:00:00Z",
  "duration": "PT1H30M0S"
}
```
**Response**:
```json
{
  "id": 1,
  "module": 1,
  "title": "Weekly Q&A Session",
  "meeting_url": "https://zoom.us/j/123456789",
  "scheduled_time": "2024-08-05T14:00:00Z",
  "duration": "PT1H30M0S"
}
```
**Errors**: (Same as Courses)

## Usage
Once the server is running, you can interact with the API using a tool like Postman, Insomnia, `curl`, or by integrating it with a frontend application.

For instance, to register a new user:
```bash
curl -X POST \
  http://127.0.0.1:8000/api/auth/registration/ \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "password": "Password123",
    "password2": "Password123"
  }'
```

To log in:
```bash
curl -X POST \
  http://127.00.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'
```
This will return `access` and `refresh` tokens, which you can then use to authenticate subsequent requests by adding a `Authorization: Bearer <access_token>` header.

## Technologies Used

| Technology                    | Version | Purpose                                              |
| :---------------------------- | :------ | :--------------------------------------------------- |
| Django                        | 5.2.4   | Web Framework for rapid development                  |
| Django REST Framework         | 3.16.0  | Building robust RESTful APIs                         |
| djangorestframework-simplejwt | 5.5.1   | JWT authentication for secure API access             |
| dj-rest-auth                  | 7.0.1   | REST API endpoints for authentication and registration |
| django-allauth                | 65.10.0 | Comprehensive authentication features                |
| django-cors-headers           | 4.7.0   | Handling Cross-Origin Resource Sharing               |
| SQLite                        | N/A     | Default database for development                     |
| Python                        | 3.x     | Primary programming language                         |

## Contributing
We welcome contributions to enhance this project! If you're interested in contributing, please follow these guidelines:

*   Fork the repository.
*   Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`.
*   Make your changes and ensure tests pass.
*   Write clear, concise commit messages.
*   Push your branch and open a pull request.
*   Describe your changes in detail and include any relevant information.

## License
This project is open-sourced. Details will be provided in a dedicated `LICENSE` file.

## Author Info
**Odafe Peter**
*   Portfolio: [My Portfolio Website](https://www.umunufolio.online)

