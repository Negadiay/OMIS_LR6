import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base

class UserRole(enum.Enum):
    CLIENT = "client"
    MANAGER = "manager"
    ADMIN = "admin"

class ActionType(enum.Enum):
    VIEW = "view"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    REVIEW = "review"

class OrderStatus(enum.Enum):
    PROCESSING = "processing"
    SHIPPING = "shipping"  
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    discriminator = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'user', 'polymorphic_on': discriminator}

class Client(User):
    __tablename__ = 'clients'
    id = Column(String, ForeignKey('users.id'), primary_key=True)
    full_name = Column(String)
    gender = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'client'}
    
    profile = relationship("Profile", uselist=False, back_populates="client", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="client", cascade="all, delete-orphan")
    cart = relationship("Cart", uselist=False, back_populates="client", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="client")
    feedbacks = relationship("Feedback", back_populates="client")

class Manager(User):
    __tablename__ = 'managers'
    id = Column(String, ForeignKey('users.id'), primary_key=True)
    organization_name = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'manager'}
    reports = relationship("Report", back_populates="manager")
    products = relationship("Product", back_populates="manager")

class Admin(User):
    __tablename__ = 'admins'
    id = Column(String, ForeignKey('users.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'admin'}

class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey('clients.id'))
    interests = Column(JSON, default=list)
    client = relationship("Client", back_populates="profile")

class Product(Base):
    __tablename__ = 'products'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    manager_id = Column(String, ForeignKey('managers.id'), nullable=True)
    
    name = Column(String)
    category = Column(String)
    price = Column(Float)
    description = Column(Text)
    sku = Column(String)
    image_url = Column(String)
    
    manager = relationship("Manager", back_populates="products")
    interactions = relationship("Interaction", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="product", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = 'interactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String, ForeignKey('clients.id'))
    product_id = Column(String, ForeignKey('products.id'))
    type = Column(Enum(ActionType))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    client = relationship("Client", back_populates="interactions")
    product = relationship("Product", back_populates="interactions")

class Feedback(Base):
    __tablename__ = 'feedbacks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String, ForeignKey('clients.id'))
    product_id = Column(String, ForeignKey('products.id'))
    text = Column(Text)
    rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="feedbacks")
    product = relationship("Product", back_populates="feedbacks")

class Cart(Base):
    __tablename__ = 'carts'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(String, ForeignKey('carts.id'))
    product_id = Column(String, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)
    
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", back_populates="cart_items")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey('clients.id'))
    
    status = Column(Enum(OrderStatus), default=OrderStatus.PROCESSING)
    total_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    items_snapshot = Column(JSON) 

    client = relationship("Client", back_populates="orders")

class Report(Base):
    __tablename__ = 'reports'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    manager_id = Column(String, ForeignKey('managers.id'))
    name = Column(String)
    content = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    manager = relationship("Manager", back_populates="reports")

class SystemModule(Base):
    __tablename__ = 'system_modules'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    
class AppConfig(Base):
    __tablename__ = 'app_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, index=True)

    value = Column(JSON)
