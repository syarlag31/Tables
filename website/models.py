from sqlalchemy.dialects.postgresql import UUID
from flask_sqlalchemy import SQLAlchemy
from flask import flash
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    signup_time = db.Column(db.DateTime, default=datetime.utcnow)
    strikes = db.Column(db.Integer, default=0)
    pfp_url = db.Column(db.String(300), nullable=False, default='/static/user.svg')
    
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='author', lazy=True, cascade="all, delete-orphan")
    karma = db.relationship('Karma', backref='author', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, handle, name, email, password, description=None, signup_time=None):
        self.handle = handle
        self.name = name
        self.description = description
        self.email = email
        self.password = password

class Post(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_url = db.Column(db.String(300), nullable=False)
    post_title = db.Column(db.String(150), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    contains_chair = db.Column(db.Boolean, default=False)
    
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, image_url, user_id, post_title=None, timestamp=None, contains_chair=False):
        self.image_url = image_url
        self.user_id = user_id
        self.post_title = post_title
        if timestamp is not None:
            self.timestamp = timestamp
        self.contains_chair = contains_chair
        
        if not contains_chair:
            author = User.query.filter_by(id=user_id).first()
            author.strikes += 1  # increment strikes for post author if contains chair
            flash(f'You have {3 - author.strikes} strikes left.', category='error')

class Comment(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = db.Column(db.String(300), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('post.id'), nullable=False)
    
    def __init__(self, text, user_id, post_id, timestamp=None):
        self.text = text
        self.user_id = user_id
        self.post_id = post_id
        
class Karma(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    karma = db.Column(db.Integer, nullable=False, default=0)
    object_uuid = db.Column(db.String, nullable=False)
    object_type = db.Column(db.String, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    
    def __init__(self, karma, object_uuid, object_type, user_id):
        self.karma = karma
        self.object_uuid = object_uuid
        self.object_type = object_type
        self.user_id = user_id