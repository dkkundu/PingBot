from flask_restful import Api
from .auth import RegisterAPI, LoginAPI

def initialize_routes(app):
    api = Api(app)
    api.add_resource(RegisterAPI, '/api/register')  #post
    api.add_resource(LoginAPI, '/api/login')      #post
