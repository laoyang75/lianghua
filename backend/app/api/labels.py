"""
标签管理API路由
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.label_calculator import get_label_calculator
from loguru import logger

router = APIRouter()


class LabelRequest(BaseModel):
    """标签计算请求"""
    rule: str
    start_date: str
    end_date: str
    params: Dict[str, Any] = {}


class LabelResponse(BaseModel):
    """标签响应"""
    name: str
    status: str
    date_range: str
    record_count: int = 0


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    label_name: str


@router.get("/list", summary="获取标签列表")
async def get_labels():
    """获取所有标签列表"""
    try:
        calculator = get_label_calculator()
        labels = await calculator.get_labels_list()
        return {"labels": labels}
    except Exception as e:
        logger.error(f"获取标签列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=TaskResponse, summary="运行标签计算")
async def run_label_calculation(request: LabelRequest, background_tasks: BackgroundTasks):
    """启动标签计算任务"""
    try:
        # 验证规则名称
        valid_rules = [
            "涨幅最大TOP20",
            "跌幅最大TOP20",
            "市值涨幅最大TOP20",
            "市值跌幅最大TOP20",
            "成交量最大TOP20",
            "换手率最高TOP20"
        ]
        
        if request.rule not in valid_rules:
            raise HTTPException(status_code=400, detail=f"无效的规则名称: {request.rule}")
        
        # 验证日期格式
        try:
            datetime.strptime(request.start_date, '%Y-%m-%d')
            datetime.strptime(request.end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
        
        # 生成任务ID和标签名称
        import uuid
        task_id = f"label_{uuid.uuid4().hex[:8]}"
        label_name = f"{request.rule}_{request.start_date}_{request.end_date}"
        
        # 启动后台计算任务
        calculator = get_label_calculator()
        
        async def run_calculation():
            try:
                await calculator.calculate_label(
                    request.rule,
                    request.start_date,
                    request.end_date,
                    request.params,
                    task_id
                )
            except Exception as e:
                logger.error(f"标签计算任务失败: {e}")
        
        background_tasks.add_task(run_calculation)
        
        logger.info(f"标签计算任务已启动: {task_id}, 规则: {request.rule}")
        
        return TaskResponse(
            task_id=task_id,
            label_name=label_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动标签计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/available", summary="获取可用规则")
async def get_available_rules():
    """获取可用的标签计算规则列表"""
    return {
        "rules": [
            {
                "name": "涨幅最大TOP20",
                "description": "选择在指定时间段内涨幅最大的20只股票",
                "parameters": ["top_k", "min_market_cap"]
            },
            {
                "name": "跌幅最大TOP20", 
                "description": "选择在指定时间段内跌幅最大的20只股票",
                "parameters": ["top_k", "min_market_cap"]
            },
            {
                "name": "市值涨幅最大TOP20",
                "description": "按市值加权选择涨幅最大的20只股票",
                "parameters": ["top_k", "min_market_cap"]
            },
            {
                "name": "市值跌幅最大TOP20",
                "description": "按市值加权选择跌幅最大的20只股票", 
                "parameters": ["top_k", "min_market_cap"]
            },
            {
                "name": "成交量最大TOP20",
                "description": "选择平均成交量最大的20只股票",
                "parameters": ["top_k", "min_market_cap"]
            },
            {
                "name": "换手率最高TOP20",
                "description": "选择换手率最高的20只股票",
                "parameters": ["top_k", "min_market_cap"]
            }
        ]
    }


@router.get("/stocks/{label_name}", summary="获取标签的股票列表")
async def get_label_stocks(label_name: str):
    """获取指定标签的股票列表"""
    try:
        calculator = get_label_calculator()
        stocks = await calculator.get_label_stocks(label_name)
        return {"stocks": stocks}
    except Exception as e:
        logger.error(f"获取标签股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{label_name}", summary="删除标签")
async def delete_label(label_name: str):
    """删除指定的标签"""
    try:
        calculator = get_label_calculator()
        success = await calculator.delete_label(label_name)
        if success:
            return {"message": "标签删除成功"}
        else:
            raise HTTPException(status_code=500, detail="标签删除失败")
    except Exception as e:
        logger.error(f"删除标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))