class Response:
    @staticmethod
    def success(message="Success", data=None, status=200):
        return {
            "status": status,
            "message": message,
            "success": True,
            "data": data
        }, status

    @staticmethod
    def error(message="Error", errors=None, status=400):
        if errors is None:
            errors = {}
        return {
            "status": status,
            "message": message,
            "success": False,
            "errors": errors
        }, status
