import uvicorn
import random
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.controllers import router
from backend.models import Product, Admin, Manager, UserRole, SystemModule

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
app.include_router(router)

@app.on_event("startup")
def seed():
    db = SessionLocal()
    try:
        if not db.query(Admin).filter(Admin.username == "admin@market.com").first():
            db.add(Admin(username="admin@market.com", password_hash="admin", role=UserRole.ADMIN))
            db.commit()
            print(">>> Admin created.")
        
        main_manager = db.query(Manager).filter(Manager.username == "manager@market.com").first()
        if not main_manager:
            main_manager = Manager(
                username="manager@market.com", 
                password_hash="manager", 
                role=UserRole.MANAGER, 
                organization_name="Global Tech"
            )
            db.add(main_manager)
            db.commit()
            print(">>> Main Manager created.")

        if not db.query(SystemModule).first():
            db.add(SystemModule(name="RecEngine", is_active=True))

        if db.query(Product).count() == 0:
            print(">>> Seeding 60 products...")
            categories = ["Creativity", "Entertainment", "Food", "Games", "Pets", "Beauty"]
            for i in range(1, 61):
                cat = random.choice(categories)
                color = f"{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}"
                p = Product(
                    name=f"{cat} Product {i}", 
                    category=cat, 
                    price=float(random.randint(10, 200)), 
                    sku=f"SKU-{1000+i}",
                    description=f"Item {i}. Excellent choice for {cat} lovers.",
                    image_url=f"https://placehold.co/400x400/{color}/ffffff?text={cat}+{i}",
                    manager_id=main_manager.id 
                )
                db.add(p)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
