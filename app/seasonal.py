"""Seasonal ingredient recommendations based on the current month."""

from datetime import datetime

SEASONAL = {
    1: {"season": "冬季", "ingredients": ["白萝卜", "白菜", "菠菜", "羊肉", "牛肉", "山药", "莲藕", "冬笋", "韭菜", "香菇"]},
    2: {"season": "冬季→初春", "ingredients": ["春笋", "韭菜", "菠菜", "芹菜", "生菜", "鲫鱼", "带鱼", "鸡肉", "豆腐", "鸡蛋"]},
    3: {"season": "春季", "ingredients": ["春笋", "芦笋", "韭菜", "荠菜", "菠菜", "香椿", "蚕豆", "草莓", "鳜鱼", "河虾"]},
    4: {"season": "春季", "ingredients": ["春笋", "豌豆", "韭菜", "荠菜", "马兰头", "莴笋", "蒜苗", "鲈鱼", "河虾", "猪肉"]},
    5: {"season": "春末夏初", "ingredients": ["蒜苗", "蚕豆", "豌豆", "黄瓜", "苋菜", "枇杷", "樱桃", "草鱼", "鲫鱼", "鸭肉"]},
    6: {"season": "夏季", "ingredients": ["黄瓜", "番茄", "茄子", "苦瓜", "空心菜", "丝瓜", "毛豆", "西瓜", "荔枝", "鳊鱼"]},
    7: {"season": "夏季", "ingredients": ["苦瓜", "丝瓜", "冬瓜", "茄子", "莲藕", "毛豆", "绿豆", "西瓜", "桃", "鸭肉"]},
    8: {"season": "夏末初秋", "ingredients": ["冬瓜", "丝瓜", "莲藕", "茄子", "玉米", "花生", "葡萄", "梨", "螃蟹", "鸡肉"]},
    9: {"season": "秋季", "ingredients": ["莲藕", "山药", "芋头", "芹菜", "菜花", "南瓜", "红薯", "螃蟹", "鲤鱼", "牛肉"]},
    10: {"season": "秋季", "ingredients": ["山药", "芋头", "南瓜", "白菜", "芹菜", "板栗", "桔子", "螃蟹", "羊肉", "鸡肉"]},
    11: {"season": "秋末冬初", "ingredients": ["白菜", "白萝卜", "山药", "菠菜", "莲藕", "板栗", "桔子", "羊肉", "牛肉", "鲫鱼"]},
    12: {"season": "冬季", "ingredients": ["白菜", "白萝卜", "菠菜", "冬笋", "山药", "羊肉", "牛肉", "带鱼", "鲢鱼", "豆腐"]},
}


def get_seasonal_context() -> str:
    now = datetime.now()
    month = now.month
    data = SEASONAL.get(month, {"season": "全年", "ingredients": []})
    ingredients = "、".join(data["ingredients"])
    return f"当前季节: {data['season']}（{month}月），当季食材: {ingredients}。推荐菜谱时优先考虑当季食材。"
