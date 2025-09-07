# PingBot
PingBot will start with Telegram auto-messaging but may support other messaging platforms in the future

The **PingBot** is a full-stack web application built with Flask, providing a centralized platform for managing and sending automated notifications. It supports user authentication with different roles (admin, employee) and includes an approval workflow for new users. Core functionalities include defining alert services, creating service configurations, generating alert messages, and sending notifications efficiently using **Celery** for background task processing. The application is containerized using **Docker** and **Docker Compose** for easy deployment and environment management.


### Features
 **User Authentication & Authorization:** Secure login, registration, user roles (admin, employee), with admin approval for new users.  
 **User Management:** Admins can view, approve, edit, and delete user accounts.  
 **Profile Management:** Users can view and edit profiles, change passwords, and upload profile pictures.  
 **Alert Service Management:** Define and manage notification services (e.g., Telegram).  
 **Alert Configuration Management:** Create and manage configurations for each service, including group names, IDs, and API tokens.  
 **Alert Sample Creation:** Generate one-time or recurring alert messages with rich content (text, images, documents).  
 **Alert Logging:** Track all sent and scheduled alerts with status and timestamps.  
 **Test Credentials:** Manage separate credentials for testing without affecting live environments.  
 **Telegram Integration:** Send messages, photos, and documents to Telegram groups seamlessly.  
 **Background Task Processing:** Uses Celery and Redis for asynchronous task execution.  
 **Pagination:** Browse large lists efficiently.  
 **Custom CLI Commands:** Includes commands for creating admin users and other management tasks.



### Prerequisites
Before you begin, ensure you have installed the following:

 **Git** – For cloning the repository  
 **Docker & Docker Compose** – For containerized deployment  
 **Python 3.8+** – Required if running outside Docker for development  
 **MySQL Database** – Can be run via Docker or externally  
 **Redis** – For Celery broker and backend, can be run via Docker or externally  

### Configure Environment Variables:

 # Flask Configuration
 ```
APP_IMAGE=notification_app<br>
APP_PORT=5001<br>
APP_CONTAINER_NAME=notification_app_web<br>
FLASK_APP=app.app:create_app<br>
FLASK_ENV=development<br>
SECRET_KEY=your_flask_secret_key<br>
JWT_SECRET_KEY=your_jwt_secret_key<br>
TZ=Asia/Dhaka
```
# MySQL Configuration
```
MYSQL_HOST=db<br>
MYSQL_PORT=3306<br>
MYSQL_DATABASE=notification_db<br>
MYSQL_USER=your_mysql_user<br>
MYSQL_PASSWORD=your_mysql_password
```

# Redis Configuration
```
CELERY_BROKER_URL=redis://redis:6379/0<br>
CELERY_BACKEND_URL=redis://redis:6379/0<br>
```

# Volume Paths
```
LOG_DIR_HOST=./logs<br>
IMAGE_DIR_HOST=./media<br>
```

# Media URL
```
MEDIA_BASE_URL=http://localhost:5001<br>
```

# Telegram Bot API (optional)
```
BOT_GROUP_API=YOUR_BOT_GROUP_API<br>
BOT_PRIVATE_API=YOUR_BOT_PRIVATE_API<br>
```


### Build and Run with Docker Compose:
```
 docker-compose up --build -d
```

### Initialize Database Migrations:
```
docker exec -it notification_app_web flask db init
docker exec -it notification_app_web flask db migrate -m "Initial migration"
docker exec -it notification_app_web flask db upgrade
```
### Create an Admin User :

```
 docker exec -it notification_app_web flask create-admin your_admin_email@example.com your_password "Your Full Name"

  ## or 
 export FLASK_APP=app.app:create_app
 flask create-admin <email>  <password> "<full_name>"
```
### Run this application :
```
  python run.py
or
  flask run
```
 
### Technologies

Backend: Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Celery, Redis, PyMySQL, Pytz, Werkzeug<br>
Frontend: Jinja2, HTML5, Tailwind CSS, JavaScript<br>
Database: MySQL<br>
Containerization: Docker, Docker Compose<br>
Other Libraries: python-dotenv, click, requests

### MIT License

Copyright (c) 2025 Dipto Kumar Kundu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.




