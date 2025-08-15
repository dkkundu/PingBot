from flask import request
from flask_restful import Resource
from .models import User
from . import db

class Response:
    @staticmethod
    def success(message="Success", data=None):
        return {"status": "success", "message": message, "data": data}, 200

    @staticmethod
    def error(message="Error", data=None):
        return {"status": "error", "message": message, "data": data}, 400

class RegisterAPI(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return Response.error("All fields are required")

        if User.query.filter_by(email=email).first():
            return Response.error("Email already exists")

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return Response.success("User registered successfully", {"username": username, "email": email})

class LoginAPI(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response.error("Email and password are required")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return Response.error("Invalid credentials")

        return Response.success("Login successful", {"username": user.username, "email": user.email})
