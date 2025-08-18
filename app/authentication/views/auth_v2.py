from flask import request, render_template, redirect, url_for, flash
from flask_restful import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import timedelta
# from app import db
from app.authentication.models import User
from helper.response import Response
from app.extensions import db
from flask import request, jsonify




# -------------------- Registration --------------------
class RegisterAPI(Resource):
    def post(self):
        data = request.get_json() or {}
        errors = {}

        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')

        if not full_name:
            errors['full_name'] = ["This field is required."]
        if not email:
            errors['email'] = ["This field is required."]
        if not password:
            errors['password'] = ["This field is required."]

        if errors:
            return Response.error("Invalid data for registration.", errors)

        if User.query.filter_by(email=email).first():
            return Response.error("Registration already exists.", {"email": ["Email already exists."]})

        user = User(
            full_name=full_name,
            email=email,
            role="employee",
            is_superuser=False,
            is_approved=False,
            phone=data.get('phone'),
            address=data.get('address'),
            bio=data.get('bio'),
            profile_pic=data.get('profile_pic')
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return Response.success(
            "User registered successfully! Waiting for admin approval.",
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "is_approved": user.is_approved
            },
            status=201
        )

# -------------------- Login --------------------
class LoginAPI(Resource):
    def post(self):
        data = request.get_json() or {}
        errors = {}

        email = data.get('email')
        password = data.get('password')

        if not email:
            errors['email'] = ["This field is required."]
        if not password:
            errors['password'] = ["This field is required."]

        if errors:
            return Response.error("Invalid login data.", errors)

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return Response.error("Invalid credentials.", {"email": ["Invalid email or password."]})

        if user.role != "admin" and not user.is_approved:
            return Response.error("Your account is pending approval by admin.", {})

        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role},
            expires_delta=timedelta(days=1)
        )

        return Response.success(
            "Login successful",
            {"token": token}
        )

# -------------------- Profile --------------------
class ProfileAPI(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user = User.query.get(int(identity))
        if not user:
            return Response.error("User not found")

        return Response.success(
            "Profile fetched successfully",
            {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "phone": user.phone,
                "address": user.address,
                "bio": user.bio,
                "profile_pic": user.profile_pic
            }
        )

# -------------------- Admin Only APIs --------------------
def admin_required(func):
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return Response.error("Unauthorized access")
        return func(*args, **kwargs)
    return wrapper

class PendingUsersAPI(Resource):
    @admin_required
    def get(self):
        pending_users = User.query.filter_by(is_approved=False).all()
        data = [{"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role} for u in pending_users]
        return Response.success("Pending users fetched successfully", data)

class ApproveUserAPI(Resource):
    @admin_required
    def post(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return Response.error("User not found")

        # Approve the user
        user.is_approved = True
        db.session.commit()

        # Prepare full user data to return
        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser,
            "is_approved": user.is_approved,
            "phone": user.phone,
            "address": user.address,
            "bio": user.bio,
            "profile_pic": user.profile_pic
        }

        return Response.success(
            f"User {user.email} approved successfully",
            user_data
        )


class RejectUserAPI(Resource):
    @admin_required
    def post(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return Response.error("User not found")
        
        # Mark user as rejected instead of deleting
        user.is_rejected = True
        user.is_approved = False  # optional: ensure rejected users are not approved
        db.session.commit()
        
        # Prepare full user data to return
        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser,
            "is_approved": user.is_approved,
            "is_rejected": user.is_rejected,
            "phone": user.phone,
            "address": user.address,
            "bio": user.bio,
            "profile_pic": user.profile_pic
        }

        return Response.success(
            f"User {user.email} rejected successfully",
            user_data
        )


class ApprovedUsersAPI(Resource):
    @admin_required
    def get(self):
        approved_users = User.query.filter_by(is_approved=True).all()

        data = []
        for u in approved_users:
            user_data = {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "is_superuser": u.is_superuser,
                "is_approved": u.is_approved,
                "phone": u.phone,
                "address": u.address,
                "bio": u.bio,
                "profile_pic": u.profile_pic
            }
            data.append(user_data)

        return Response.success("Approved users fetched successfully", data)









# from flask import request
# from flask_restful import Resource
# from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
# from datetime import timedelta
# from app import db
# from app.authentication.models import User
# from helper.response import Response

# # -------------------- Registration --------------------
# class RegisterAPI(Resource):
#     def post(self):
#         data = request.get_json() or {}
#         errors = {}

#         full_name = data.get('full_name')
#         email = data.get('email')
#         password = data.get('password')

#         if not full_name:
#             errors['full_name'] = ["This field is required."]
#         if not email:
#             errors['email'] = ["This field is required."]
#         if not password:
#             errors['password'] = ["This field is required."]

#         if errors:
#             return Response.error("Invalid data for registration.", errors)

#         if User.query.filter_by(email=email).first():
#             return Response.error("Registration already exists.", {"email": ["Email already exists."]})

#         user = User(
#             full_name=full_name,
#             email=email,
#             role="employee",
#             is_superuser=False,
#             is_approved=False,
#             phone=data.get('phone'),
#             address=data.get('address'),
#             bio=data.get('bio'),
#             profile_pic=data.get('profile_pic')
#         )
#         user.set_password(password)

#         db.session.add(user)
#         db.session.commit()

#         return Response.success(
#             "User registered successfully! Waiting for admin approval.",
#             {
#                 "id": user.id,
#                 "full_name": user.full_name,
#                 "email": user.email,
#                 "role": user.role,
#                 "is_approved": user.is_approved
#             },
#             status=201
#         )

# # -------------------- Login --------------------
# class LoginAPI(Resource):
#     def post(self):
#         data = request.get_json() or {}
#         errors = {}

#         email = data.get('email')
#         password = data.get('password')

#         if not email:
#             errors['email'] = ["This field is required."]
#         if not password:
#             errors['password'] = ["This field is required."]

#         if errors:
#             return Response.error("Invalid login data.", errors)

#         user = User.query.filter_by(email=email).first()
#         if not user or not user.check_password(password):
#             return Response.error("Invalid credentials.", {"email": ["Invalid email or password."]})

#         if user.role != "admin" and not user.is_approved:
#             return Response.error("Your account is pending approval by admin.", {})

#         token = create_access_token(
#             identity=str(user.id),
#             additional_claims={"role": user.role},
#             expires_delta=timedelta(days=1)
#         )

#         return Response.success(
#             "Login successful",
#             {"token": token}
#         )

# # -------------------- Profile --------------------
# class ProfileAPI(Resource):
#     @jwt_required()
#     def get(self):
#         identity = get_jwt_identity()
#         user = User.query.get(int(identity))
#         if not user:
#             return Response.error("User not found")

#         return Response.success(
#             "Profile fetched successfully",
#             {
#                 "id": user.id,
#                 "full_name": user.full_name,
#                 "email": user.email,
#                 "role": user.role,
#                 "phone": user.phone,
#                 "address": user.address,
#                 "bio": user.bio,
#                 "profile_pic": user.profile_pic
#             }
#         )

# # -------------------- Admin Only APIs --------------------
# def admin_required(func):
#     @jwt_required()
#     def wrapper(*args, **kwargs):
#         claims = get_jwt()
#         if claims.get("role") != "admin":
#             return Response.error("Unauthorized access")
#         return func(*args, **kwargs)
#     return wrapper

# class PendingUsersAPI(Resource):
#     @admin_required
#     def get(self):
#         pending_users = User.query.filter_by(is_approved=False).all()
#         data = [{"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role} for u in pending_users]
#         return Response.success("Pending users fetched successfully", data)

# class ApproveUserAPI(Resource):
#     @admin_required
#     def post(self, user_id):
#         user = User.query.get(user_id)
#         if not user:
#             return Response.error("User not found")

#         # Approve the user
#         user.is_approved = True
#         db.session.commit()

#         # Prepare full user data to return
#         user_data = {
#             "id": user.id,
#             "full_name": user.full_name,
#             "email": user.email,
#             "role": user.role,
#             "is_superuser": user.is_superuser,
#             "is_approved": user.is_approved,
#             "phone": user.phone,
#             "address": user.address,
#             "bio": user.bio,
#             "profile_pic": user.profile_pic
#         }

#         return Response.success(
#             f"User {user.email} approved successfully",
#             user_data
#         )


# class RejectUserAPI(Resource):
#     @admin_required
#     def post(self, user_id):
#         user = User.query.get(user_id)
#         if not user:
#             return Response.error("User not found")
        
#         # Mark user as rejected instead of deleting
#         user.is_rejected = True
#         user.is_approved = False  # optional: ensure rejected users are not approved
#         db.session.commit()
        
#         # Prepare full user data to return
#         user_data = {
#             "id": user.id,
#             "full_name": user.full_name,
#             "email": user.email,
#             "role": user.role,
#             "is_superuser": user.is_superuser,
#             "is_approved": user.is_approved,
#             "is_rejected": user.is_rejected,
#             "phone": user.phone,
#             "address": user.address,
#             "bio": user.bio,
#             "profile_pic": user.profile_pic
#         }

#         return Response.success(
#             f"User {user.email} rejected successfully",
#             user_data
#         )


# class ApprovedUsersAPI(Resource):
#     @admin_required
#     def get(self):
#         approved_users = User.query.filter_by(is_approved=True).all()

#         data = []
#         for u in approved_users:
#             user_data = {
#                 "id": u.id,
#                 "full_name": u.full_name,
#                 "email": u.email,
#                 "role": u.role,
#                 "is_superuser": u.is_superuser,
#                 "is_approved": u.is_approved,
#                 "phone": u.phone,
#                 "address": u.address,
#                 "bio": u.bio,
#                 "profile_pic": u.profile_pic
#             }
#             data.append(user_data)

#         return Response.success("Approved users fetched successfully", data)




# # from flask import request
# # from flask_restful import Resource
# # from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# # from datetime import timedelta
# # from functools import wraps
# # from app import db
# # from app.models import User
# # from app.response.response import Response

# # # -------------------- Registration --------------------
# # class RegisterAPI(Resource):
# #     def post(self):
# #         data = request.get_json() or {}
# #         full_name = data.get('full_name')
# #         email = data.get('email')
# #         password = data.get('password')
# #         errors = {}

# #         if not full_name:
# #             errors["full_name"] = ["This field is required."]
# #         if not email:
# #             errors["email"] = ["This field is required."]
# #         if not password:
# #             errors["password"] = ["This field is required."]
# #         if errors:
# #             return Response.error("Invalid data for registration.", errors)

# #         if User.query.filter_by(email=email).first():
# #             return Response.error("Registration already exists.", {"email": ["Email already exists."]})

# #         user = User(
# #             full_name=full_name,
# #             email=email,
# #             role="employee",
# #             is_superuser=False,
# #             is_approved=False,
# #             phone=data.get('phone'),
# #             address=data.get('address'),
# #             bio=data.get('bio'),
# #             profile_pic=data.get('profile_pic')
# #         )
# #         user.set_password(password)
# #         db.session.add(user)
# #         db.session.commit()

# #         return Response.success(
# #             "User registered successfully! Waiting for admin approval.",
# #             {
# #                 "id": user.id,
# #                 "full_name": user.full_name,
# #                 "email": user.email,
# #                 "role": user.role,
# #                 "is_approved": user.is_approved
# #             },
# #             status=201
# #         )

# # # -------------------- Login --------------------
# # class LoginAPI(Resource):
# #     def post(self):
# #         data = request.get_json() or {}
# #         email = data.get('email')
# #         password = data.get('password')
# #         errors = {}

# #         if not email:
# #             errors["email"] = ["This field is required."]
# #         if not password:
# #             errors["password"] = ["This field is required."]
# #         if errors:
# #             return Response.error("Invalid login data.", errors)

# #         user = User.query.filter_by(email=email).first()
# #         if not user or not user.check_password(password):
# #             return Response.error("Invalid credentials.", {"email": ["Invalid email or password."]})

# #         if not user.is_approved:
# #             return Response.error("Your account is pending approval by admin.", {})

# #         token = create_access_token(
# #             identity={
# #                 "id": user.id,
# #                 "email": user.email,
# #                 "role": user.role,
# #                 "is_superuser": user.is_superuser
# #             },
# #             expires_delta=timedelta(days=1)
# #         )

# #         return Response.success(
# #             "Login successful",
# #             {
# #                 "token": token,
# #                 "user": {
# #                     "id": user.id,
# #                     "full_name": user.full_name,
# #                     "email": user.email,
# #                     "role": user.role,
# #                     "is_superuser": user.is_superuser
# #                 }
# #             }
# #         )

# # # -------------------- Profile --------------------
# # class ProfileAPI(Resource):
# #     @jwt_required()
# #     def get(self):
# #         identity = get_jwt_identity()
# #         user = User.query.get(identity["id"])
# #         if not user:
# #             return Response.error("User not found")

# #         return Response.success(
# #             "Profile fetched successfully",
# #             {
# #                 "id": user.id,
# #                 "full_name": user.full_name,
# #                 "email": user.email,
# #                 "role": user.role,
# #                 "phone": user.phone,
# #                 "address": user.address,
# #                 "bio": user.bio,
# #                 "profile_pic": user.profile_pic
# #             }
# #         )

# # # -------------------- Admin-only APIs --------------------
# # def admin_required(fn):
# #     @wraps(fn)
# #     @jwt_required()
# #     def wrapper(*args, **kwargs):
# #         identity = get_jwt_identity()
# #         if not identity.get("is_superuser"):
# #             return Response.error("Admin access required.", status=403)
# #         return fn(*args, **kwargs)
# #     return wrapper

# # class PendingUsersAPI(Resource):
# #     @admin_required
# #     def get(self):
# #         pending_users = User.query.filter_by(is_approved=False).all()
# #         data = [
# #             {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role}
# #             for u in pending_users
# #         ]
# #         return Response.success("Pending users fetched successfully", data)

# # class ApproveUserAPI(Resource):
# #     @admin_required
# #     def post(self, user_id):
# #         user = User.query.get(user_id)
# #         if not user:
# #             return Response.error("User not found", status=404)
# #         user.is_approved = True
# #         db.session.commit()
# #         return Response.success(f"User {user.email} approved successfully")

# # class RejectUserAPI(Resource):
# #     @admin_required
# #     def post(self, user_id):
# #         user = User.query.get(user_id)
# #         if not user:
# #             return Response.error("User not found", status=404)
# #         db.session.delete(user)
# #         db.session.commit()
# #         return Response.success(f"User {user.email} rejected and deleted successfully")

# # class ApprovedUsersAPI(Resource):
# #     @admin_required
# #     def get(self):
# #         approved_users = User.query.filter_by(is_approved=True).all()
# #         data = [
# #             {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role}
# #             for u in approved_users
# #         ]
# #         return Response.success("Approved users fetched successfully", data)
