from app.database import get_db
from app.models import AssemblyStep, WeldingRequirement

db = next(get_db())

# 查看步骤13的详细信息
step = db.query(AssemblyStep).filter(AssemblyStep.id == 13).first()
if step:
    print('=== 步骤13的信息 ===')
    print(f'步骤ID: {step.id}')
    print(f'步骤号: {step.step_number}')
    print(f'组件名称: {step.component}')
    print(f'步骤描述: {step.description}')
    print()

# 查看步骤号5的所有步骤
print('=== 步骤号5的所有步骤 ===')
steps = db.query(AssemblyStep).filter(AssemblyStep.step_number == 5).all()
for s in steps:
    print(f'步骤ID={s.id}, 组件={s.component}, 描述={s.description[:50] if len(s.description) > 50 else s.description}')
print()

# 查看步骤号5的所有焊接要求
print('=== 步骤号5的所有焊接要求 ===')
weldings = db.query(WeldingRequirement).filter(WeldingRequirement.step_number == 5).all()
if weldings:
    for w in weldings:
        print(f'焊接ID={w.id}, 组件={w.component}, 焊点数={w.weld_point_count}')
else:
    print('没有焊接要求')

