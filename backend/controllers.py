from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.database import get_db
from backend.repositories import UserRepository, ProductRepository, ReportRepository
from backend.services import RecommendationService, CartService, ManagerService
from backend.models import Client, Manager, Admin, Profile, UserRole, Interaction, ActionType, SystemModule, CartItem, Product, Report
import backend.models
import random
from backend.config import settings
from datetime import datetime 
from backend.models import AppConfig
import json

templates = Jinja2Templates(directory=str(settings.TEMPLATE_DIR))
router = APIRouter()

class BaseController:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_current_user(self, request: Request):
        user_id = request.cookies.get("user_id")
        if not user_id: return None
        return self.user_repo.get_by_id(user_id)

class AuthController(BaseController):
    async def login(self, request: Request, username: str, password: str):
        user = self.user_repo.get_by_username(username)
        if user and user.password_hash == password:
            url = "/client/home" if user.role == UserRole.CLIENT else "/manager/cabinet" if user.role == UserRole.MANAGER else "/admin/panel"
            resp = RedirectResponse(url, status_code=303)
            resp.set_cookie(key="user_id", value=user.id)
            return resp
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login or password"})

@router.get("/", response_class=HTMLResponse)
async def root(): return RedirectResponse("/login")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request, "hide_header": True})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    return await AuthController(db).login(request, username, password)

@router.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("user_id")
    return resp

@router.get("/register", response_class=HTMLResponse)
async def reg_page(request: Request): return templates.TemplateResponse("register.html", {"request": request, "hide_header": True})

@router.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...), full_name: str = Form(...), gender: str = Form(...), interests: list = Form([]), db: Session = Depends(get_db)):
    if UserRepository(db).get_by_username(username):
        return templates.TemplateResponse("register.html", {"request": request, "hide_header": True, "error": "Email exists"})
    client = Client(username=username, password_hash=password, role=UserRole.CLIENT, full_name=full_name, gender=gender)
    db.add(client)
    db.commit()
    db.add(Profile(client_id=client.id, interests=interests))
    db.commit()
    resp = RedirectResponse("/client/home", status_code=303)
    resp.set_cookie("user_id", client.id)
    return resp

@router.get("/register/manager", response_class=HTMLResponse)
async def reg_manager_page(request: Request): return templates.TemplateResponse("register_manager.html", {"request": request, "hide_header": True})

@router.post("/register/manager")
async def register_manager(request: Request, username: str = Form(...), password: str = Form(...), organization: str = Form(...), name: str = Form(None), gender: str = Form(None), db: Session = Depends(get_db)):
    mgr = Manager(
        username=username, 
        password_hash=password, 
        role=UserRole.MANAGER, 
        organization_name=organization
    )
    db.add(mgr)
    db.commit()
    resp = RedirectResponse("/manager/cabinet", status_code=303)
    resp.set_cookie("user_id", mgr.id)
    return resp

@router.get("/client/home", response_class=HTMLResponse)
async def client_home(request: Request, search: str = "", db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    products = RecommendationService(db).get_recommendations(user, limit=50)
    if search:
        search = search.lower()
        products = [p for p in products if search in p.name.lower()]
    return templates.TemplateResponse("client/home.html", {"request": request, "user": user, "products": products})

@router.get("/client/category/{cat}", response_class=HTMLResponse)
async def cat_products(request: Request, cat: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    products = db.query(Product).filter(Product.category == cat).all()
    return templates.TemplateResponse("client/category_products.html", {"request": request, "user": user, "products": products, "category_name": cat})

@router.get("/client/product/{pid}", response_class=HTMLResponse)
async def product_detail(request: Request, pid: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    product = ProductRepository(db).get_by_id(pid)
    if not product: raise HTTPException(status_code=404)
    db.add(Interaction(client_id=user.id, product_id=pid, type=ActionType.VIEW))
    db.commit()
    similar = db.query(Product).filter(Product.category == product.category, Product.id != product.id).limit(4).all()
    return templates.TemplateResponse("client/product.html", {"request": request, "user": user, "product": product, "similar": similar})

@router.post("/client/cart/add/{pid}")
async def add_to_cart(request: Request, pid: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    
    CartService(db).add_to_cart(user.id, pid)
    db.add(Interaction(client_id=user.id, product_id=pid, type=ActionType.ADD_TO_CART))
    db.commit()
    
    referer = request.headers.get("referer", "/client/home")
    if "#" in referer: referer = referer.split("#")[0]
    redirect_url = f"{referer}#product-{pid}"
    
    return RedirectResponse(redirect_url, status_code=303)

@router.post("/client/cart/update/{item_id}")
async def update_cart_item(request: Request, item_id: int, action: str = Form(...), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if item:
        if action == "increase": item.quantity += 1
        elif action == "decrease": 
            item.quantity -= 1
            if item.quantity <= 0: db.delete(item)
        db.commit()
    return RedirectResponse("/client/cart", status_code=303)

@router.get("/client/cart", response_class=HTMLResponse)
async def view_cart(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    cart = CartService(db).cart_repo.get_by_client(user.id)
    items = cart.items if cart else []
    subtotal = sum(i.product.price * i.quantity for i in items)
    delivery = 15.0 if subtotal > 0 else 0.0
    total = subtotal + delivery
    return templates.TemplateResponse("client/cart.html", {"request": request, "user": user, "items": items, "subtotal": round(subtotal,2), "delivery": delivery, "total": round(total,2)})

@router.get("/client/payment", response_class=HTMLResponse)
async def payment_page(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    cart = CartService(db).cart_repo.get_by_client(user.id)
    if not cart or not cart.items: return RedirectResponse("/client/home")
    subtotal = sum(i.product.price * i.quantity for i in cart.items)
    delivery = 15.0
    total = subtotal + delivery
    return templates.TemplateResponse("client/payment.html", {"request": request, "user": user, "subtotal": round(subtotal,2), "delivery": delivery, "total": round(total,2)})

@router.post("/client/checkout")
async def checkout(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    CartService(db).checkout(user.id)
    return templates.TemplateResponse("client/result.html", {"request": request, "user": user})

@router.get("/client/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("client/profile.html", {"request": request, "user": user})

@router.post("/client/profile/update")
async def update_profile(request: Request, full_name: str = Form(...), gender: str = Form(...), interests: list = Form([]), password: str = Form(...), db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    user.full_name = full_name
    user.gender = gender
    user.password_hash = password
    if user.profile:
        user.profile.interests = interests
        flag_modified(user.profile, "interests")
    else:
        db.add(Profile(client_id=user.id, interests=interests))
    db.commit()
    return RedirectResponse("/client/profile", status_code=303)

@router.get("/client/orders", response_class=HTMLResponse)
async def orders(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    
    user_orders = db.query(backend.models.Order).filter(backend.models.Order.client_id == user.id).order_by(backend.models.Order.created_at.desc()).all()
    
    TIME_STEP = 5
    
    current_time = datetime.utcnow()
    
    for order in user_orders:
        if order.status == backend.models.OrderStatus.CANCELLED:
            continue
            
        delta = (current_time - order.created_at).total_seconds()
                
        if delta < TIME_STEP:
            new_status = backend.models.OrderStatus.PROCESSING
        elif delta < (TIME_STEP * 2):
            new_status = backend.models.OrderStatus.SHIPPING
        else:
            new_status = backend.models.OrderStatus.COMPLETED

        if order.status != new_status:
            order.status = new_status
            db.commit()

    return templates.TemplateResponse("client/orders.html", {"request": request, "user": user, "orders": user_orders})

@router.get("/manager/cabinet")
async def mgr_cab(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    return templates.TemplateResponse("manager/cabinet.html", {"request": request, "user": user})

@router.get("/manager/products")
async def mgr_products(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    products = db.query(Product).filter(Product.manager_id == user.id).all()
    return templates.TemplateResponse("manager/products_list.html", {"request": request, "products": products, "user": user})

@router.get("/manager/products/add", response_class=HTMLResponse)
async def add_product_page(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    return templates.TemplateResponse("manager/product_form.html", {"request": request, "user": user, "product": None})

@router.post("/manager/products/add")
async def add_product(
    request: Request, 
    name: str = Form(...), category: str = Form(...), price: float = Form(...), 
    description: str = Form(...), image_url: str = Form(...),
    db: Session = Depends(get_db)
):
    user = BaseController(db).get_current_user(request)
    new_product = Product(
        name=name, category=category, price=price, description=description, image_url=image_url,
        manager_id=user.id, sku=f"SKU-{random.randint(1000,9999)}"
    )
    db.add(new_product)
    db.commit()
    return RedirectResponse("/manager/products", status_code=303)

@router.get("/manager/products/edit/{pid}", response_class=HTMLResponse)
async def edit_product_page(request: Request, pid: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    product = db.query(Product).filter(Product.id == pid, Product.manager_id == user.id).first()
    if not product: return RedirectResponse("/manager/products")
    return templates.TemplateResponse("manager/product_form.html", {"request": request, "user": user, "product": product})

@router.post("/manager/products/edit/{pid}")
async def edit_product(
    request: Request, pid: str,
    name: str = Form(...), category: str = Form(...), price: float = Form(...), 
    description: str = Form(...), image_url: str = Form(...),
    db: Session = Depends(get_db)
):
    user = BaseController(db).get_current_user(request)
    product = db.query(Product).filter(Product.id == pid, Product.manager_id == user.id).first()
    if product:
        product.name = name
        product.category = category
        product.price = price
        product.description = description
        product.image_url = image_url
        db.commit()
    return RedirectResponse("/manager/products", status_code=303)

@router.post("/manager/products/delete/{pid}")
async def delete_product(request: Request, pid: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    product = db.query(Product).filter(Product.id == pid, Product.manager_id == user.id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse("/manager/products", status_code=303)

@router.post("/manager/reports/create")
async def create_rep(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    report = ManagerService(db).generate_report(user.id)
    return RedirectResponse(f"/manager/report/{report.id}", status_code=303)

@router.get("/manager/report/{rid}")
async def view_rep(request: Request, rid: str, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    report = db.query(Report).filter(Report.id == rid, Report.manager_id == user.id).first()
    if not report: return RedirectResponse("/manager/reports")
    return templates.TemplateResponse("manager/report_view.html", {"request": request, "report": report})

@router.get("/manager/reports")
async def list_rep(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    reps = db.query(Report).filter(Report.manager_id == user.id).all()
    return templates.TemplateResponse("manager/reports_list.html", {"request": request, "reports": reps})

@router.post("/manager/reports/delete/{rid}")
async def delete_rep(rid: str, db: Session = Depends(get_db)):
    report = ReportRepository(db).get_by_id(rid)
    if report:
        db.delete(report)
        db.commit()
    return RedirectResponse("/manager/reports", status_code=303)

@router.get("/admin/panel")
async def admin_pan(request: Request, db: Session = Depends(get_db)):
    user = BaseController(db).get_current_user(request)
    if not user: return RedirectResponse("/login")
    mods = db.query(SystemModule).all()
    
    config_obj = db.query(AppConfig).filter(AppConfig.key == "algo_weights").first()
    if config_obj:
        current_weights = json.dumps(config_obj.value, indent=4)
    else:
        current_weights = json.dumps({
            "view": 1.0,
            "add_to_cart": 3.0,
            "review": 4.0,
            "purchase": 5.0
        }, indent=4)

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, 
        "user": user, 
        "modules": mods,
        "weights_json": current_weights 
    })

@router.post("/admin/config/update")
async def update_config(request: Request, weights: str = Form(...), db: Session = Depends(get_db)):
    try:
        new_data = json.loads(weights)
        
        conf = db.query(AppConfig).filter(AppConfig.key == "algo_weights").first()
        if not conf:
            conf = AppConfig(key="algo_weights", value=new_data)
            db.add(conf)
        else:
            conf.value = new_data
            flag_modified(conf, "value")
        
        db.commit()
    except Exception as e:
        print("Error saving config:", e)
    
    return RedirectResponse("/admin/panel", status_code=303)

@router.post("/admin/module/toggle/{mod_id}")
async def toggle_module(mod_id: int, db: Session = Depends(get_db)):
    module = db.query(SystemModule).filter(SystemModule.id == mod_id).first()
    if module:
        module.is_active = not module.is_active
        db.commit()

    return RedirectResponse("/admin/panel", status_code=303)
