class Config:
    # needed for sessions, login and flash messages
    SECRET_KEY = 'ihmsecretkey'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///emp.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False