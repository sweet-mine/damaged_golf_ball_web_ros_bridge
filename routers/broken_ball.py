import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db, BrokenBall
from ws_manager import manager, app_state

router = APIRouter(prefix="/api/broken_ball", tags=["broken_ball"])

class LocationSchema(BaseModel):
    room: int = Field(..., ge=1, le=4, description="Room number, must be an integer between 1 and 4")

class BrokenBallReport(BaseModel):
    location: LocationSchema
    image: str | None = Field(None, description="Base64 encoded 320x320 image")

class BrokenBallUpdate(BaseModel):
    location: LocationSchema
    image: str | None = Field(None, description="Base64 encoded 320x320 image")

@router.post("/")
async def create_broken_ball(report: BrokenBallReport, db: Session = Depends(get_db)):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    location_str = json.dumps(report.location.dict())
    
    db_item = BrokenBall(timestamp=now, location=location_str, image=report.image)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    new_id = db_item.id
    
    # 웹소켓 브로드캐스트
    notification = {
        'type': 'broken_ball_notification',
        'data': {
            'id': new_id,
            'timestamp': now,
            'location': report.location.dict(),
            'image': report.image
        }
    }
    
    loop = app_state.get("loop") or asyncio.get_running_loop()
    if loop:
        asyncio.run_coroutine_threadsafe(manager.broadcast(notification), loop)
        
    return {"status": "success", "message": "Broken ball reported successfully", "id": new_id}

@router.get("/")
async def get_all_broken_balls(db: Session = Depends(get_db)):
    items = db.query(BrokenBall).order_by(BrokenBall.id.desc()).all()
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "timestamp": item.timestamp,
            "location": json.loads(item.location),
            "image": item.image
        })
    return {"status": "success", "data": results}

@router.get("/{item_id}")
async def get_broken_ball(item_id: int, db: Session = Depends(get_db)):
    item = db.query(BrokenBall).filter(BrokenBall.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Broken ball not found")
        
    return {
        "status": "success", 
        "data": {
            "id": item.id,
            "timestamp": item.timestamp,
            "location": json.loads(item.location),
            "image": item.image
        }
    }

@router.put("/{item_id}")
async def update_broken_ball(item_id: int, report: BrokenBallUpdate, db: Session = Depends(get_db)):
    item = db.query(BrokenBall).filter(BrokenBall.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Broken ball not found")
        
    item.location = json.dumps(report.location.dict())
    if report.image:
        item.image = report.image
    db.commit()
    
    return {"status": "success", "message": "Broken ball updated successfully"}

@router.delete("/{item_id}")
async def delete_broken_ball(item_id: int, db: Session = Depends(get_db)):
    item = db.query(BrokenBall).filter(BrokenBall.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Broken ball not found")
        
    db.delete(item)
    db.commit()
    
    return {"status": "success", "message": "Broken ball deleted successfully"}
