from flask_restful import Api

# v1 APIs
from app.authentication.views.auth_v1 import (
    RegisterAPI as RegisterV1,
    LoginAPI as LoginV1,
    ProfileAPI as ProfileV1,
    PendingUsersAPI as PendingUsersV1,
    ApproveUserAPI as ApproveUserV1,
    RejectUserAPI as RejectUserV1,
    ApprovedUsersAPI as ApprovedUsersV1
)

# v2 APIs
from app.authentication.views.auth_v2 import (
    RegisterAPI as RegisterV2,
    LoginAPI as LoginV2,
    ProfileAPI as ProfileV2,
    PendingUsersAPI as PendingUsersV2,
    ApproveUserAPI as ApproveUserV2,
    RejectUserAPI as RejectUserV2,
    ApprovedUsersAPI as ApprovedUsersV2
)

def initialize_routes(app):
    api = Api(app)  # <-- create Api instance here once

    # ------------------ v1 Routes ------------------
    api.add_resource(RegisterV1, '/api/v1/register', endpoint='register_v1')
    api.add_resource(LoginV1, '/api/v1/login', endpoint='login_v1')
    api.add_resource(ProfileV1, '/api/v1/profile', endpoint='profile_v1')
    api.add_resource(PendingUsersV1, '/api/v1/users/pending', endpoint='pending_users_v1')
    api.add_resource(ApproveUserV1, '/api/v1/users/approve/<int:user_id>', endpoint='approve_user_v1')
    api.add_resource(RejectUserV1, '/api/v1/users/reject/<int:user_id>', endpoint='reject_user_v1')
    api.add_resource(ApprovedUsersV1, '/api/v1/users/approved', endpoint='approved_users_v1')

    # ------------------ v2 Routes ------------------
    api.add_resource(RegisterV2, '/api/v2/register', endpoint='register_v2')
    api.add_resource(LoginV2, '/api/v2/login', endpoint='login_v2')
    api.add_resource(ProfileV2, '/api/v2/profile', endpoint='profile_v2')
    api.add_resource(PendingUsersV2, '/api/v2/users/pending', endpoint='pending_users_v2')
    api.add_resource(ApproveUserV2, '/api/v2/users/approve/<int:user_id>', endpoint='approve_user_v2')
    api.add_resource(RejectUserV2, '/api/v2/users/reject/<int:user_id>', endpoint='reject_user_v2')
    api.add_resource(ApprovedUsersV2, '/api/v2/users/approved', endpoint='approved_users_v2')


