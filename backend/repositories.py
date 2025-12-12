from sqlalchemy.orm import Session
from typing import Type, TypeVar, List, Optional
from backend.database import Base
from backend.models import User, Client, Product, Interaction, Report, Cart

# ИСПРАВЛЕНИЕ: Убрали bound=Base, чтобы IDE не ругалась на динамический тип
T = TypeVar('T')

class BaseRepository:
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> List[T]:
        return self.db.query(self.model).all()

    def save(self, entity: T) -> T:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def delete(self, entity: T):
        self.db.delete(entity)
        self.db.commit()

class UserRepository(BaseRepository):
    def __init__(self, db: Session): super().__init__(db, User)
    def get_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

class ProductRepository(BaseRepository):
    def __init__(self, db: Session): super().__init__(db, Product)

class InteractionRepository(BaseRepository):
    def __init__(self, db: Session): super().__init__(db, Interaction)
    def get_history(self, client_id: str):
        return self.db.query(Interaction).filter(Interaction.client_id == client_id).all()

class ReportRepository(BaseRepository):
    def __init__(self, db: Session): super().__init__(db, Report)

class CartRepository(BaseRepository):
    def __init__(self, db: Session): super().__init__(db, Cart)
    def get_by_client(self, client_id: str):
        return self.db.query(Cart).filter(Cart.client_id == client_id).first()