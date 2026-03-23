from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Session
from datetime import datetime
import uvicorn

# ── Database setup ──────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./rfid.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

class Base(DeclarativeBase):
    pass

class Card(Base):
    __tablename__ = "cards"
    id          = Column(Integer, primary_key=True, index=True)
    rfid_number = Column(String, unique=True, index=True, nullable=False)
    name        = Column(String, nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

class ScanLog(Base):
    __tablename__ = "scan_logs"
    id          = Column(Integer, primary_key=True, index=True)
    rfid_number = Column(String, nullable=False)
    user_name   = Column(String, nullable=True)   # null = unknown card
    access      = Column(Boolean, nullable=False)
    scanned_at  = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="RFID Access Control")
templates = Jinja2Templates(directory="templates")

def get_db():
    with Session(engine) as db:
        yield db

# ── Pydantic model for ESP32 ─────────────────────────────────────────────────
class RFIDCheckRequest(BaseModel):
    rfid_number: str

# ══════════════════════════════════════════════════════════════════════════════
#  API ENDPOINT  –  called by the ESP32
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/functions/v1/rfid-api/check")
async def check_rfid(payload: RFIDCheckRequest):
    rfid = payload.rfid_number.upper().strip()
    with Session(engine) as db:
        card = db.query(Card).filter(
            Card.rfid_number == rfid,
            Card.is_active == True
        ).first()

        access_granted = card is not None
        log = ScanLog(
            rfid_number = rfid,
            user_name   = card.name if card else None,
            access      = access_granted,
        )
        db.add(log)
        db.commit()

    if access_granted:
        return {
            "access_granted": True,
            "user": {"name": card.name}
        }
    return {"access_granted": False}


# ══════════════════════════════════════════════════════════════════════════════
#  WEB DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    with Session(engine) as db:
        cards     = db.query(Card).order_by(Card.created_at.desc()).all()
        logs      = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).limit(50).all()
        total     = db.query(func.count(Card.id)).scalar()
        active    = db.query(func.count(Card.id)).filter(Card.is_active == True).scalar()
        granted   = db.query(func.count(ScanLog.id)).filter(ScanLog.access == True).scalar()
        denied    = db.query(func.count(ScanLog.id)).filter(ScanLog.access == False).scalar()

    return templates.TemplateResponse(request, "dashboard.html", {
        "cards":    cards,
        "logs":     logs,
        "total":    total,
        "active":   active,
        "granted":  granted,
        "denied":   denied,
    })


# ── Cards HTMX partials ──────────────────────────────────────────────────────

@app.post("/cards/add", response_class=HTMLResponse)
async def add_card(request: Request,
                   rfid_number: str = Form(...),
                   name: str = Form(...)):
    rfid = rfid_number.upper().strip()
    with Session(engine) as db:
        existing = db.query(Card).filter(Card.rfid_number == rfid).first()
        if existing:
            # Return an error row
            return HTMLResponse(
                f'<tr id="error-row"><td colspan="5" class="error-msg">'
                f'⚠ Card {rfid} already exists!</td></tr>',
                status_code=200
            )
        card = Card(rfid_number=rfid, name=name.strip())
        db.add(card)
        db.commit()
        db.refresh(card)

    return templates.TemplateResponse(request, "partials/card_row.html",
                                      {"card": card})


@app.delete("/cards/{card_id}", response_class=HTMLResponse)
async def delete_card(card_id: int):
    with Session(engine) as db:
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        db.delete(card)
        db.commit()
    return HTMLResponse("")   # HTMX swaps the row with nothing


@app.patch("/cards/{card_id}/toggle", response_class=HTMLResponse)
async def toggle_card(request: Request, card_id: int):
    with Session(engine) as db:
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        card.is_active = not card.is_active
        db.commit()
        db.refresh(card)

    return templates.TemplateResponse(request, "partials/card_row.html",
                                      {"card": card})


# ── Logs HTMX partial ────────────────────────────────────────────────────────

@app.get("/logs/refresh", response_class=HTMLResponse)
async def refresh_logs(request: Request):
    with Session(engine) as db:
        logs = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).limit(50).all()
    return templates.TemplateResponse(request, "partials/log_rows.html",
                                      {"logs": logs})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
