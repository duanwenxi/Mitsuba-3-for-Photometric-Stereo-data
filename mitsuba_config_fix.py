
# Mitsuba 修复配置
# 使用此配置替换原有的 Mitsuba 初始化代码

import mitsuba as mi

# 推荐的变体设置
RECOMMENDED_VARIANT = "cuda_ad_rgb"
RECOMMENDED_INTEGRATOR = "direct"

try:
    mi.set_variant(RECOMMENDED_VARIANT)
    print(f"成功设置 Mitsuba 变体: {RECOMMENDED_VARIANT}")
except Exception as e:
    print(f"设置变体失败: {e}")
    # 回退到默认变体
    try:
        mi.set_variant('scalar_rgb')
        print("回退到 scalar_rgb 变体")
    except:
        raise Exception("无法设置任何 Mitsuba 变体")

# 在场景配置中使用推荐的积分器
# 将 'integrator': {'type': 'path'} 替换为:
# 'integrator': {'type': RECOMMENDED_INTEGRATOR}
