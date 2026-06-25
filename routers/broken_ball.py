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
async def get_all_broken_balls(
    page: int = 1,
    limit: int = 10,
    room: str = "all",
    date: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(BrokenBall)
    
    # Apply room filter
    if room != "all":
        try:
            room_int = int(room)
            query = query.filter(BrokenBall.location.like(f'%"room": {room_int}%'))
        except ValueError:
            pass
            
    # Apply date filter
    if date:
        query = query.filter(BrokenBall.timestamp.like(f"{date}%"))
        
    # Get total count matching the filters
    total_count = query.count()
    
    # Apply pagination and sorting
    items = query.order_by(BrokenBall.id.desc()).offset((page - 1) * limit).limit(limit).all()
    
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "timestamp": item.timestamp,
            "location": json.loads(item.location),
            "image": None  # Omit base64 image data to reduce initial load traffic
        })
        
    return {
        "status": "success",
        "data": {
            "items": results,
            "total_count": total_count,
            "page": page,
            "limit": limit
        }
    }

@router.get("/stats")
async def get_broken_ball_stats(
    date: str | None = None,
    db: Session = Depends(get_db)
):
    # 1. Total count of all records in the database
    total_count = db.query(BrokenBall).count()
    
    # 2. Room counts (filtered by date if provided)
    room_query = db.query(BrokenBall)
    if date:
        room_query = room_query.filter(BrokenBall.timestamp.like(f"{date}%"))
        
    room_items = room_query.all()
    room_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for item in room_items:
        try:
            loc = json.loads(item.location)
            r = loc.get("room")
            if r in room_counts:
                room_counts[r] += 1
        except Exception:
            pass
            
    # 3. Date counts (all history, unfiltered, for trend chart)
    all_items = db.query(BrokenBall.timestamp).all()
    date_counts = {}
    for (ts,) in all_items:
        try:
            d = ts.split(" ")[0]
            date_counts[d] = date_counts.get(d, 0) + 1
        except Exception:
            pass
            
    return {
        "status": "success",
        "data": {
            "total_count": total_count,
            "room_counts": room_counts,
            "date_counts": date_counts
        }
    }


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
