import random
from typing import List, Dict, Counter
from backend.models import Client, Interaction, Product, ActionType, AppConfig
from backend.database import SessionLocal

class AnalysisStrategy:
    def analyze(self, client: Client, history: List[Interaction], products: List[Product], all_interactions: List[Interaction]) -> Dict[str, float]:
        raise NotImplementedError

    def _get_global_popularity(self, products: List[Product], all_interactions: List[Interaction]) -> Dict[str, float]:
        """
        Считает общую популярность товаров по всей системе
        """
        scores = {p.id: 0.0 for p in products}
        weights = {
            "view": 1.0,
            "add_to_cart": 3.0,
            "review": 4.0,
            "purchase": 5.0
        }
        db = SessionLocal()
        try:
            config = db.query(AppConfig).filter(AppConfig.key == "algo_weights").first()
            if config and config.value:
                weights.update(config.value)
        finally:
            db.close()
        
        for action in all_interactions:
            if action.product_id in scores:
                weight = weights.get(action.type.value, 1.0)
                scores[action.product_id] += weight
        
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            for pid in scores:
                scores[pid] /= max_score
        
        return scores

class StatisticalStrategy(AnalysisStrategy):
    """
    Для холодных пользователей (Global Popularity + Explicit Interests).
    """
    def analyze(self, client: Client, history: List[Interaction], products: List[Product], all_interactions: List[Interaction]) -> Dict[str, float]:
        scores = self._get_global_popularity(products, all_interactions)
        
        if client.profile and client.profile.interests:
            for p in products:
                if p.category in client.profile.interests:
                    scores[p.id] += 0.5  

        for pid in scores:
            scores[pid] += random.random() * 0.05  
        return scores

class MLStrategy(AnalysisStrategy):
    """
    Content-Based (User Vector) + Collaborative Elements (Global Pop).
    """
    def analyze(self, client: Client, history: List[Interaction], products: List[Product], all_interactions: List[Interaction]) -> Dict[str, float]:
        scores = {p.id: 0.0 for p in products}
        
        user_category_vector = Counter()
        
        if client.profile and client.profile.interests:
            for interest in client.profile.interests:
                user_category_vector[interest] += 2.0
        
        purchased_ids = set() 
        
        for action in history:
            if not action.product: continue
            
            if action.type == ActionType.PURCHASE:
                purchased_ids.add(action.product_id)
            
            cat = action.product.category
            weight = 0
            if action.type == ActionType.VIEW: weight = 1.0
            elif action.type == ActionType.ADD_TO_CART: weight = 2.5
            elif action.type == ActionType.PURCHASE: weight = 5.0
            
            user_category_vector[cat] += weight

        total_weight = sum(user_category_vector.values())
        if total_weight > 0:
            for cat in user_category_vector:
                user_category_vector[cat] /= total_weight

        product_quality = self._get_global_popularity(products, all_interactions)

        for p in products:
            if p.id in purchased_ids:
                scores[p.id] = -1.0
                continue


            category_relevance = user_category_vector.get(p.category, 0.0) * 5.0 
            
            quality_score = product_quality.get(p.id, 0.0)
            
            scores[p.id] = category_relevance + quality_score
            
            scores[p.id] += random.random() * 0.01


        return scores
