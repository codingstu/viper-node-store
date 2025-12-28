import secrets
import string
import os
from supabase import create_client, Client

# --- 配置区域 ---
# 如果你在本地运行，可以直接填入，或者设置环境变量
SUPABASE_URL = "你的_SUPABASE_URL"
SUPABASE_KEY = "你的_SERVICE_ROLE_KEY"  # 注意：写入数据需要 service_role key

# 链接 Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_random_code(length=16):
    """生成16位数字和字母混合的卡密"""
    # 排除容易混淆的字符如 o, O, 0, i, I, 1 (可选)
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def batch_insert_kamis(count=50, days=30):
    """
    批量生成并插入卡密
    :param count: 生成数量
    :param days: 该批次卡密对应的有效天数
    """
    print(f"正在生成 {count} 个卡密...")

    kami_data = []
    generated_codes = []

    for _ in range(count):
        code = generate_random_code(16)
        generated_codes.append(code)
        kami_data.append({
            "code": code,
            "days": days,
            "is_used": False
        })

    # 批量插入数据库
    try:
        # 使用 upsert 防止极小概率的重复
        result = supabase.table("kamis").upsert(kami_data).execute()
        print(f"成功存入数据库！")
        print("-" * 20)
        print("以下是生成的卡密列表（请保存）：")
        for c in generated_codes:
            print(c)
        print("-" * 20)
    except Exception as e:
        print(f"存入失败: {e}")


if __name__ == "__main__":
    # 示例：生成 20 个 30 天有效的卡密
    batch_insert_kamis(count=20, days=30)