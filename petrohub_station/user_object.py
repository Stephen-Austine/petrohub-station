# user_object.py
class UserObject:
    def __init__(self, user_id, first_name, last_name, email, role, username=None):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.role = role
        self.username = username
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.user_id)
    
    @property
    def fname(self):
        """Return username for employees/admins, first_name for regular users"""
        if self.role != 'customer' and self.username:
            return self.username
        return self.first_name
    
    @property
    def full_name(self):
        """Return full display name"""
        if self.role != 'customer' and self.username:
            return f"{self.first_name} {self.last_name} ({self.username})"
        return f"{self.first_name} {self.last_name}"