# ... (RecommendationService и CartService без изменений, код ниже) ...
from sqlalchemy.orm import Session
from backend.repositories import ProductRepository, InteractionRepository, CartRepository, ReportRepository
from backend.strategies import MLStrategy, StatisticalStrategy
from backend.models import Client, Cart, CartItem, Interaction, Report, ActionType, Order, OrderStatus
from datetime import datetime

class RecommendationService:
    def __init__(self, db: Session):
        self.product_repo = ProductRepository(db)
        self.interaction_repo = InteractionRepository(db)
        self.ml = MLStrategy()
        self.stat = StatisticalStrategy()

    def get_recommendations(self, client: Client, limit=6):
        history = self.interaction_repo.get_history(client.id)
        products = self.product_repo.get_all()
        all_interactions = self.interaction_repo.get_all()
        strategy = self.ml if history else self.stat
        scores = strategy.analyze(client, history, products, all_interactions)
        recommended = sorted(products, key=lambda p: scores.get(p.id, 0), reverse=True)
        return recommended[:limit]

class CartService:
    def __init__(self, db: Session):
        self.cart_repo = CartRepository(db)
        self.db = db

    def add_to_cart(self, client_id: str, product_id: str):
        cart = self.cart_repo.get_by_client(client_id)
        if not cart:
            cart = Cart(client_id=client_id)
            self.cart_repo.save(cart)
        
        item = next((i for i in cart.items if i.product_id == product_id), None)
        if item:
            item.quantity += 1
        else:
            item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            self.db.add(item)
        self.db.commit()

    def checkout(self, client_id: str):
        cart = self.cart_repo.get_by_client(client_id)
        if cart and cart.items:
            total_amount = 0.0
            snapshot = []
            for item in cart.items:
                total_amount += item.product.price * item.quantity
                snapshot.append({
                    "product_name": item.product.name,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.product.price
                })
                inter = Interaction(client_id=client_id, product_id=item.product_id, type=ActionType.PURCHASE)
                self.db.add(inter)
                self.db.delete(item)
            
            delivery = 15.0 
            total_amount += delivery
            order = Order(
                client_id=client_id, 
                total_amount=round(total_amount, 2),
                items_snapshot=snapshot,
                status=OrderStatus.PROCESSING
            )
            self.db.add(order)
            self.db.commit()

class ManagerService:
    def __init__(self, db: Session):
        self.report_repo = ReportRepository(db)
        self.interaction_repo = InteractionRepository(db)

    def generate_report(self, manager_id: str):
        # Собираем статистику по ВСЕМ покупкам (PURCHASE)
        purchases = [i for i in self.interaction_repo.get_all() if i.type == ActionType.PURCHASE]
        stats = {}
        
        for p in purchases:
            if not p.product: continue
            # Если нужно фильтровать только товары этого менеджера:
            if p.product.manager_id != manager_id and p.product.manager_id is not None:
                continue

            name = p.product.name
            if name not in stats: stats[name] = {"sold": 0, "revenue": 0}
            stats[name]["sold"] += 1
            stats[name]["revenue"] += p.product.price
        
        content = [{"product": k, **v} for k, v in stats.items()]
        # Если пусто - все равно создаем
        report = Report(name=f"Report {len(self.report_repo.get_all())+1}", manager_id=manager_id, content=content)
        return self.report_repo.save(report)