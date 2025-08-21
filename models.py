from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime,
                           default=datetime.now,
                           onupdate=datetime.now)
    
    # User preferences
    preferred_participation = db.Column(db.String, default='all')  # 'online', 'in_person', 'hybrid', 'all'
    notification_preferences = db.Column(db.String, default='email')  # 'email', 'none'

    # Relationship to subscriptions
    subscriptions = db.relationship('EventSubscription', backref='user', lazy=True, cascade='all, delete-orphan')

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class EventSubscription(db.Model):
    __tablename__ = 'event_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.String, nullable=False)  # Hash-based ID from scraper
    event_title = db.Column(db.String, nullable=False)
    event_link = db.Column(db.String, nullable=False)
    event_start_date = db.Column(db.String, nullable=True)
    event_end_date = db.Column(db.String, nullable=True)
    
    # When the user subscribed
    subscribed_at = db.Column(db.DateTime, default=datetime.now)
    
    # Notification preferences for this specific event
    notify_before_start = db.Column(db.Boolean, default=True)
    notify_on_changes = db.Column(db.Boolean, default=True)
    
    # Unique constraint to prevent duplicate subscriptions
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='uq_user_event_subscription'),)
    
    def __repr__(self):
        return f'<EventSubscription {self.user_id} -> {self.event_title}>'

class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    
    # Event filtering preferences
    preferred_countries = db.Column(db.Text)  # JSON string of preferred countries
    preferred_event_types = db.Column(db.Text)  # JSON string of preferred event types
    preferred_topics = db.Column(db.Text)  # JSON string of preferred topics
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    daily_digest = db.Column(db.Boolean, default=False)
    weekly_digest = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Ensure one preference record per user
    __table_args__ = (UniqueConstraint('user_id', name='uq_user_preferences'),)